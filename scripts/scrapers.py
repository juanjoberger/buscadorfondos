"""Scrapers de portales de convocatorias.

Cada scraper es una función sin argumentos que hace yield de dicts
normalizados (mismo formato que data/fondos_seed.json). Se registran en
SCRAPERS y el registro de fuentes (tabla `fuentes`) los referencia por clave.

Reglas: User-Agent identificable, pausas entre requests, y NUNCA inventar
datos: si un campo no está en el portal, va vacío y la validación decide.
"""
import csv
import html as html_lib
import io
import json as _json
import re
import time
import unicodedata
import urllib.parse
import urllib.robotparser

import defusedxml.ElementTree as ET  # parser endurecido: evita XXE/billion-laughs
import requests

UA_NOMBRE = "BuscadorDeFondos"
UA = {"User-Agent": "BuscadorDeFondos/1.0 (agregador de convocatorias LATAM)"}
PAUSA = 0.6  # segundos entre requests al mismo sitio


def _get(url, timeout=30):
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    time.sleep(PAUSA)
    return r.text


# --------------------------------------------- cumplimiento y ahorro de energía
_ROBOTS_CACHE = {}


def robots_permite(url):
    """True si robots.txt del dominio permite recolectar esta URL con nuestro UA.
    Si no hay robots.txt (404) o no es legible, se asume permitido. Cacheado por
    dominio (INGESTA_ESTRATEGIA.md §3/§4: nunca scrapear contra un Disallow).

    Se descarga robots.txt con NUESTRO User-Agent (requests), no con el de
    urllib.robotparser, porque varios portales le responden 403 a ese y eso daría
    un falso 'prohibido'."""
    partes = urllib.parse.urlparse(url)
    base = f"{partes.scheme}://{partes.netloc}"
    if base not in _ROBOTS_CACHE:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = requests.get(base + "/robots.txt", headers=UA, timeout=15)
            if r.status_code == 404:
                rp.allow_all = True
            elif r.status_code >= 400:
                rp.disallow_all = True  # 401/403 → el sitio no nos quiere: respetar
            else:
                rp.parse(r.text.splitlines())
        except Exception:
            rp = None  # red caída / robots ilegible → permitido (sin bloqueo explícito)
        _ROBOTS_CACHE[base] = rp
    rp = _ROBOTS_CACHE[base]
    return True if rp is None else rp.can_fetch(UA_NOMBRE, url)


def get_condicional(url, etag=None, last_modified=None, timeout=30):
    """GET con If-None-Match/If-Modified-Since. Devuelve
    (texto | None, etag, last_modified). texto=None significa 304 (sin cambios):
    casi sin costo de red ni de CPU."""
    headers = dict(UA)
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    r = requests.get(url, headers=headers, timeout=timeout)
    time.sleep(PAUSA)
    if r.status_code == 304:
        return None, etag, last_modified
    r.raise_for_status()
    return r.text, r.headers.get("ETag", etag), r.headers.get("Last-Modified", last_modified)


def _limpiar(texto):
    return html_lib.unescape(texto).replace("´", "'").strip()


def _sin_acentos(texto):
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


# ---------------------------------------------------------------- fondos.gob.cl
FGC_BASE = "https://fondos.gob.cl"

# categoría del portal → perfil del buscador (orden = prioridad si hay varias)
FGC_PERFILES = [
    ("cultura", ("arte y cultura", "patrimonio y memoria", "comunicacion y difusion")),
    ("investigacion", ("investigacion y desarrollo", "ciencia y tecnologia")),
    ("emprendimiento", ("emprendimiento e innovacion", "inversion productiva",
                        "energias renovables", "agricultura y desarrollo rural",
                        "pesca artesanal y acuicultura de pequena escala")),
]

# nuestras regiones, normalizadas, para detectarlas en el nombre de la institución
from app.constants import REGIONES  # noqa: E402

_REGIONES_NORM = {_sin_acentos(r): r for r in REGIONES}
_REGIONES_NORM["metropolitano"] = "Metropolitana"
_REGIONES_NORM["higgins"] = "OHiggins"


def _region_de(institucion):
    inst = _sin_acentos(institucion)
    for clave, region in _REGIONES_NORM.items():
        if clave in inst:
            return region
    return "Todas"


def _monto(texto):
    numeros = [int(n.replace(".", "")) for n in re.findall(r"\$\s*([\d\.]+)", texto)]
    numeros = [n for n in numeros if n > 1000]  # descarta ruido tipo "$0"
    if not numeros:
        return None, None
    if len(numeros) == 1:
        return None, numeros[0]
    return min(numeros), max(numeros)


def _fecha_iso(ddmmyyyy):
    d, m, a = ddmmyyyy.split("/")
    return f"{a}-{m}-{d}"


def fondos_gob_cl(fuente=None):
    """Portal oficial de fondos concursables del Estado de Chile (~400 fichas).

    1. /searchernew/ lista TODAS las convocatorias (server-rendered).
    2. Las páginas por categoría dan la temática → perfil del buscador.
    """
    home = _get(f"{FGC_BASE}/")
    categorias = sorted(set(re.findall(r'href="/searchernew/([^"/]+)/"', home)))

    # ficha → categorías normalizadas a las que pertenece
    pertenencia = {}
    for cat in categorias:
        pagina = _get(f"{FGC_BASE}/searchernew/{cat}/")
        cat_norm = _sin_acentos(requests.utils.unquote(cat))
        for ficha in set(re.findall(r'href="(/ficha/[^"]+)"', pagina)):
            pertenencia.setdefault(ficha, set()).add(cat_norm)

    listado = _get(f"{FGC_BASE}/searchernew/")
    tarjetas = re.split(r'<a href="(/ficha/[^"]+)">', listado)[1:]

    for ficha, cuerpo in zip(tarjetas[0::2], tarjetas[1::2], strict=False):
        cuerpo = cuerpo.split("</a>")[0]

        # Las CERRADAS también se ingieren: sus fechas de apertura alimentan
        # la inteligencia estacional del planificador (scripts/ingesta.py), y
        # el buscador igual las oculta por defecto (filtro "abiertas").
        inst = re.search(r'<small class="text-uppercase[^"]*">([^<]+)</small>', cuerpo)
        nombre = re.search(r"<h6[^>]*>([^<]+)</h6>", cuerpo)
        if not (inst and nombre):
            continue
        institucion = _limpiar(inst.group(1))

        beneficiarios = re.search(r"Beneficiarios/as:\s*</b></span>\s*<p>([^<]+)</p>", cuerpo)
        fechas = re.search(r"Inicio:\s*(\d{2}/\d{2}/\d{4}).*?Fin:\s*(\d{2}/\d{2}/\d{4})",
                           cuerpo, re.S)
        bloque_montos = re.search(r"Montos?:\s*</b></span>\s*<p>([^<]*)</p>", cuerpo)
        monto_min, monto_max = _monto(bloque_montos.group(1)) if bloque_montos else (None, None)

        perfil = "ong"  # lo social/comunitario es el grueso del portal
        cats = pertenencia.get(ficha, set())
        for perfil_bf, temas in FGC_PERFILES:
            if any(t in c for c in cats for t in temas):
                perfil = perfil_bf
                break

        yield {
            "nombre": _limpiar(nombre.group(1)),
            "institucion": institucion,
            "descripcion": (f"Beneficiarios/as: {_limpiar(beneficiarios.group(1))}"
                            if beneficiarios else None),
            "perfil": perfil,
            "pais": "Chile",
            "region": _region_de(institucion),
            "comuna": "Todas",
            "monto_min": monto_min,
            "monto_max": monto_max,
            "moneda": "CLP",
            "fecha_apertura": _fecha_iso(fechas.group(1)) if fechas else None,
            "fecha_cierre": _fecha_iso(fechas.group(2)) if fechas else None,
            "link": f"{FGC_BASE}{ficha}",
            "fuente": "fondos.gob.cl",
        }


# ============================================================================
# Adaptadores GENÉRICOS (carriles A/B de INGESTA_ESTRATEGIA.md): dar de alta una
# fuente nueva de datos abiertos o RSS es CONFIGURACIÓN, no código. La fuente
# guarda sus parámetros en Fuente.config (JSON); estos adaptadores los leen.
# ============================================================================

def _config(fuente):
    return _json.loads(fuente.config or "{}") if fuente else {}


def _guardar_estado_http(fuente, etag, last_modified):
    if fuente is not None:
        fuente.http_etag = etag
        fuente.http_last_modified = last_modified


def adaptador_rss(fuente):
    """Feed RSS/Atom de novedades (carril B). config:
    {feed_url, institucion, perfil, pais?, region?, comuna?, moneda?}
    Guarda solo HECHOS (título + enlace a la ficha oficial); no copia la prosa
    de la descripción (INGESTA_ESTRATEGIA.md §3)."""
    cfg = _config(fuente)
    url = cfg["feed_url"]
    if not robots_permite(url):
        raise RuntimeError(f"robots.txt no permite recolectar {url}")
    texto, etag, lm = get_condicional(url, fuente.http_etag, fuente.http_last_modified)
    _guardar_estado_http(fuente, etag, lm)
    if texto is None:
        return  # 304: sin cambios, nada que hacer

    raiz = ET.fromstring(texto)
    # RSS usa <item>; Atom usa <entry> con namespace.
    items = raiz.iter("item")
    for item in items:
        titulo = _limpiar(item.findtext("title") or "")
        link = (item.findtext("link") or "").strip()
        if not (titulo and link):
            continue
        yield {
            "nombre": titulo,
            "institucion": cfg["institucion"],
            "perfil": cfg["perfil"],
            "pais": cfg.get("pais", "Chile"),
            "region": cfg.get("region", "Todas"),
            "comuna": cfg.get("comuna", "Todas"),
            "moneda": cfg.get("moneda", "CLP"),
            "link": link,
            "fuente": fuente.nombre,
        }


def _filas_tabular(texto, formato, json_path=None):
    if formato == "csv":
        return list(csv.DictReader(io.StringIO(texto)))
    datos = _json.loads(texto)
    for clave in (json_path or "").split(".") if json_path else []:
        datos = datos.get(clave, []) if isinstance(datos, dict) else datos
    return datos if isinstance(datos, list) else []


def adaptador_opendata(fuente):
    """Portal de datos abiertos / API con licencia (carril A). config:
    {data_url, formato: 'json'|'csv', json_path?, mapping:{campo_fondo: columna},
     defaults:{perfil, pais, institucion, ...}}
    Es la vía más limpia y barata: estructurado, licenciado, sin parsear HTML."""
    cfg = _config(fuente)
    url = cfg["data_url"]
    if not robots_permite(url):
        raise RuntimeError(f"robots.txt no permite recolectar {url}")
    texto, etag, lm = get_condicional(url, fuente.http_etag, fuente.http_last_modified)
    _guardar_estado_http(fuente, etag, lm)
    if texto is None:
        return

    mapping = cfg.get("mapping", {})
    defaults = cfg.get("defaults", {})
    for fila in _filas_tabular(texto, cfg.get("formato", "json"), cfg.get("json_path")):
        d = dict(defaults)
        for campo, columna in mapping.items():
            valor = fila.get(columna)
            if valor not in (None, ""):
                d[campo] = valor
        d.setdefault("fuente", fuente.nombre)
        yield d


# -------------------------------------------------------------- FAPESP (piloto BR)
FAPESP_URL = "https://fapesp.br/chamadas"

# Área declarada por FAPESP → perfil del buscador. Por defecto, investigación
# (FAPESP financia mayormente ciencia).
_FAPESP_PERFIL = [
    ("emprendimiento", ("inova", "empreend", "tecno", "centelha", "pipe")),
    ("cultura", ("cultura", "arte", "patrim")),
]


def _fapesp_perfil(area):
    a = _sin_acentos(area)
    for perfil, claves in _FAPESP_PERFIL:
        if any(k in a for k in claves):
            return perfil
    return "investigacion"


def _fapesp_cierre(bloque):
    """'Prazo: DD/MM' → fecha ISO infiriendo el año; flujo continuo → None."""
    m = re.search(r"Prazo:\s*(\d{2})/(\d{2})", bloque)
    if not m:
        return None  # flujo continuo / sin fecha declarada → permanente
    from datetime import date
    dd, mm = int(m.group(1)), int(m.group(2))
    hoy = date.today()
    try:
        f = date(hoy.year, mm, dd)
    except ValueError:
        return None
    if f < hoy:  # ya pasó este año → es del próximo
        f = date(hoy.year + 1, mm, dd)
    return f.isoformat()


def fapesp_br(fuente=None):
    """Piloto Brasil: chamadas abiertas de la FAPESP (estado de São Paulo).

    Fuente verificada (robots.txt con Disallow vacío). Guarda solo hechos
    (título, área, plazo, enlace a la ficha oficial); no copia la prosa de la
    convocatoria (Ley III del DECALOGO: índice, no espejo)."""
    if not robots_permite(FAPESP_URL):
        raise RuntimeError(f"robots.txt no permite {FAPESP_URL}")
    txt = _get(FAPESP_URL)
    for bloque in re.split(r"<h3", txt):
        m = re.search(r'<a href="(https://fapesp\.br/\d+)">(.*?)</a>', bloque, re.S)
        area = re.search(r"Área:\s*([^<\n]+)", bloque)
        if not (m and area):  # solo bloques que son una chamada real (tienen Área)
            continue
        titulo = _limpiar(re.sub(r"<[^>]+>", "", m.group(2)))
        if len(titulo) < 8:
            continue
        yield {
            "nombre": titulo,
            "institucion": "FAPESP",
            "perfil": _fapesp_perfil(area.group(1)),
            "pais": "Brasil",
            "region": "São Paulo",
            "comuna": "Todas",
            "moneda": "BRL",
            "fecha_cierre": _fapesp_cierre(bloque),
            "link": m.group(1),
            "fuente": fuente.nombre if fuente else "fapesp.br",
        }


SCRAPERS = {
    "fondos_gob_cl": fondos_gob_cl,
    "fapesp_br": fapesp_br,
    "adaptador_rss": adaptador_rss,
    "adaptador_opendata": adaptador_opendata,
}
