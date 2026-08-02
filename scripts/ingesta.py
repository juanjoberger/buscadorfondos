"""Ingesta parcelada de convocatorias (contexto.md §1: cadencia semanal).

La actualización completa NO ocurre de una vez: cada corrida procesa un LOTE
de fuentes (tabla `fuentes`), eligiendo inteligentemente cuáles tocan:

1. Están vencidas (pasaron más de `frecuencia_dias` desde su última corrida).
2. Se ordenan por prioridad, y con boost ESTACIONAL: si históricamente esa
   fuente publica convocatorias en este mes o el próximo (según las
   fechas de apertura ya ingeridas), sube en la cola.
3. Se toman las primeras N (--lote, default 3). Con un cron DIARIO y
   frecuencia semanal por fuente, el catálogo completo se renueva cada
   semana repartiendo la carga por país e institución.

Uso:
  python -m scripts.ingesta                     # corrida parcelada
  python -m scripts.ingesta --lote 5            # lote más grande
  python -m scripts.ingesta --fuente fondos.gob.cl   # forzar una fuente
  python -m scripts.ingesta archivo.json [...]  # cargar archivos a mano

Reglas (contexto.md §4): institucion y fuente obligatorios (trazabilidad
B2B); pais del catálogo o LATAM/Global; upsert por link (no duplica ni
re-alerta: AlertaEnviada se conserva).
"""
import argparse
import json
import os
import sys
from collections import Counter
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.constants import PAISES
from app.extensions import db
from app.models import PERFILES, Fondo, Fuente
from scripts.scrapers import SCRAPERS

OBLIGATORIOS = ("nombre", "link", "perfil", "institucion", "fuente")
PAISES_VALIDOS = set(PAISES) | {"LATAM", "Global"}


def _parse_fecha(valor):
    if isinstance(valor, date):
        return valor
    return datetime.strptime(valor, "%Y-%m-%d").date() if valor else None


def validar(d):
    """Devuelve la lista de problemas del registro (vacía si está OK)."""
    problemas = [f"falta '{c}'" for c in OBLIGATORIOS if not d.get(c)]
    if d.get("perfil") and d["perfil"] not in PERFILES:
        problemas.append(f"perfil desconocido: {d['perfil']}")
    pais = d.get("pais", "Chile")
    if pais not in PAISES_VALIDOS:
        problemas.append(f"país fuera del catálogo: {pais}")
    for campo in ("fecha_apertura", "fecha_cierre"):
        try:
            _parse_fecha(d.get(campo))
        except ValueError:
            problemas.append(f"{campo} inválida: {d[campo]}")
    return problemas


def upsert(d):
    """Inserta o actualiza por link. Devuelve 'nuevo' o 'actualizado'."""
    campos = dict(
        nombre=d["nombre"],
        institucion=d["institucion"],
        descripcion=d.get("descripcion"),
        perfil=d["perfil"],
        pais=d.get("pais", "Chile"),
        region=d.get("region", "Todas"),
        comuna=d.get("comuna", "Todas"),
        monto_min=d.get("monto_min"),
        monto_max=d.get("monto_max"),
        moneda=d.get("moneda", "CLP"),
        fecha_apertura=_parse_fecha(d.get("fecha_apertura")),
        fecha_cierre=_parse_fecha(d.get("fecha_cierre")),
        fuente=d["fuente"],
    )
    existente = Fondo.query.filter_by(link=d["link"]).first()
    if existente:
        for k, v in campos.items():
            setattr(existente, k, v)
        return "actualizado"
    db.session.add(Fondo(link=d["link"], **campos))
    return "nuevo"


def cargar_registros(registros, etiqueta):
    nuevos, actualizados, rechazados = 0, 0, []
    for d in registros:
        problemas = validar(d)
        if problemas:
            rechazados.append(f"{d.get('nombre', '(sin nombre)')}: {'; '.join(problemas)}")
            continue
        if upsert(d) == "nuevo":
            nuevos += 1
        else:
            actualizados += 1
    db.session.commit()
    resumen = f"{nuevos} nuevos, {actualizados} actualizados, {len(rechazados)} rechazados"
    print(f"[{etiqueta}] {resumen}")
    for r in rechazados[:10]:
        print(f"  RECHAZADO → {r}")
    return resumen, len(rechazados)


# ------------------------------------------------ planificador parcelado

def bootstrap_fuentes():
    """Sincroniza la tabla `fuentes` con data/fuentes_seed.json (idempotente).

    Inserta las fuentes nuevas y actualiza los campos de catálogo/gobernanza de
    las existentes (institución, url, método, licencia, prioridad…), preservando
    el estado de ejecución (ultima_ejecucion, http_etag, ultimo_resultado). Así el
    catálogo de sitios de LATAM y el Caribe se amplía sin perder el historial."""
    ruta = os.path.join(os.path.dirname(__file__), "..", "data", "fuentes_seed.json")
    with open(ruta, encoding="utf-8") as f:
        catalogo = json.load(f)

    existentes = {fu.nombre: fu for fu in Fuente.query.all()}
    catalogo_cols = ("institucion", "pais", "tipo", "metodo", "scraper", "url",
                     "frecuencia_dias", "prioridad", "licencia", "terminos_url", "robots_ok")
    nuevas = 0
    for d in catalogo:
        fu = existentes.get(d["nombre"])
        if fu is None:
            db.session.add(Fuente(**d))
            nuevas += 1
        else:
            for col in catalogo_cols:
                if col in d:
                    setattr(fu, col, d[col])
    db.session.commit()
    print(f"Fuentes sincronizadas: {nuevas} nuevas, {Fuente.query.count()} en total.")


def meses_historicos(nombre_fuente):
    """Meses en que esa fuente históricamente abre convocatorias."""
    aperturas = (db.session.query(Fondo.fecha_apertura)
                 .filter(Fondo.fuente == nombre_fuente,
                         Fondo.fecha_apertura.isnot(None)).all())
    return Counter(f.month for (f,) in aperturas)


def elegir_lote(lote):
    """Fuentes scrapeables vencidas, ordenadas por prioridad + estacionalidad + atraso."""
    hoy = datetime.now(timezone.utc).replace(tzinfo=None)
    mes_actual, mes_prox = hoy.month, hoy.month % 12 + 1

    candidatas = []
    for f in Fuente.query.filter_by(activa=True, tipo="scraper").all():
        if f.scraper not in SCRAPERS:
            continue
        atraso = (hoy - f.ultima_ejecucion).days - f.frecuencia_dias if f.ultima_ejecucion else 999
        if atraso < 0:
            continue  # aún fresca
        meses = meses_historicos(f.nombre)
        estacional = meses.get(mes_actual, 0) + meses.get(mes_prox, 0)
        candidatas.append((f.prioridad, -estacional, -atraso, f))

    candidatas.sort(key=lambda t: t[:3])
    return [f for *_, f in candidatas[:lote]]


def correr_fuente(fuente):
    print(f"→ {fuente.nombre} ({fuente.pais}, prioridad {fuente.prioridad})")
    try:
        registros = list(SCRAPERS[fuente.scraper](fuente))
        resumen, _ = cargar_registros(registros, fuente.nombre)
        fuente.ultimo_resultado = resumen
    except Exception as e:
        fuente.ultimo_resultado = f"ERROR: {e}"
        print(f"[{fuente.nombre}] ERROR: {e}")
    fuente.ultima_ejecucion = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivos", nargs="*", help="archivos JSON a cargar directamente")
    parser.add_argument("--lote", type=int, default=3, help="máx. fuentes por corrida")
    parser.add_argument("--fuente", help="forzar una fuente específica (ignora frecuencia)")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        db.create_all()
        bootstrap_fuentes()

        # Modo archivo: carga directa (p. ej. fondos levantados a mano)
        for ruta in args.archivos:
            with open(ruta, encoding="utf-8") as f:
                registros = json.load(f)
            for d in registros:
                d.setdefault("fuente", os.path.basename(ruta))
            cargar_registros(registros, os.path.basename(ruta))
        if args.archivos:
            return

        if args.fuente:
            fuente = Fuente.query.filter_by(nombre=args.fuente).first()
            if not fuente or fuente.scraper not in SCRAPERS:
                sys.exit(f"Fuente desconocida o sin scraper: {args.fuente}")
            correr_fuente(fuente)
            return

        lote = elegir_lote(args.lote)
        if not lote:
            print("Ninguna fuente vencida: nada que actualizar en esta corrida.")
        for fuente in lote:
            correr_fuente(fuente)

        pendientes = Fuente.query.filter_by(activa=True, tipo="manual").count()
        if pendientes:
            print(f"({pendientes} fuentes registradas aún sin scraper — "
                  f"ver tabla fuentes; skill /ingesta-fondos para implementarlas)")


if __name__ == "__main__":
    main()
