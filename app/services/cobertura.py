"""Semáforo de cobertura por país — por MADUREZ DE DATOS.

El semáforo ya no mide cuánta plata suman los fondos, sino **qué tan fidedigna y
completa es la información que tenemos de cada país**. Es honesto: si no tenemos
fuentes verificadas de un país, no prometemos cobertura de ese país.

- verde   = cobertura activa: al menos una fuente propia verificada (robots/Términos
            revisados y lista para recolectar). Datos fidedignos y mantenibles.
- amarillo= cobertura parcial: identificamos fuentes oficiales pero aún no están
            verificadas/automatizadas. La información puede estar incompleta o ser
            menos fiable — y así se le avisa al usuario.
- rojo    = sin cobertura aún: no tenemos fuentes propias de ese país.

Los montos (en USD) se conservan como dato informativo, no como criterio de la luz.
"""
from datetime import date

from sqlalchemy import func, or_

from ..constants import FX_USD, PAISES
from ..extensions import db
from ..models import Fondo, Fuente

ESTADOS = ("verde", "amarillo", "rojo")
_ORDEN = {"verde": 0, "amarillo": 1, "rojo": 2}


def _monto_referencia(f):
    monto = f.monto_max or f.monto_min
    if monto is None:
        return 0
    return (monto / FX_USD[f.moneda]) if f.moneda in FX_USD else 0


def _resumen_fuentes():
    """Por país: (nº fuentes propias, nº fuentes propias verificadas)."""
    total = dict(
        db.session.query(Fuente.pais, func.count(Fuente.id))
        .filter(Fuente.activa.is_(True)).group_by(Fuente.pais).all()
    )
    verif = dict(
        db.session.query(Fuente.pais, func.count(Fuente.id))
        .filter(Fuente.activa.is_(True), Fuente.robots_ok.is_(True))
        .group_by(Fuente.pais).all()
    )
    return total, verif


def _estado(total_propias, verificadas):
    if verificadas > 0:
        return "verde"
    if total_propias > 0:
        return "amarillo"
    return "rojo"


def estado_pais(pais):
    """Nivel de cobertura de un país (verde/amarillo/rojo). Se usa en el buscador,
    el premium y las alertas para ser honestos sobre la calidad del dato."""
    total = Fuente.query.filter_by(pais=pais, activa=True).count()
    verif = Fuente.query.filter_by(pais=pais, activa=True, robots_ok=True).count()
    return _estado(total, verif)


def cobertura_por_pais():
    """Lista de países ordenada por madurez de datos (verde→amarillo→rojo) y,
    dentro de cada nivel, por financiamiento indexado. Los fondos LATAM/Global se
    reparten a todos (aplican en todos)."""
    hoy = date.today()
    vigentes = Fondo.query.filter(
        or_(Fondo.fecha_cierre.is_(None), Fondo.fecha_cierre >= hoy)
    ).all()
    transversales = [f for f in vigentes if f.pais in ("LATAM", "Global")]
    usd_transversal = sum(_monto_referencia(f) for f in transversales)
    n_transversal = len(transversales)

    total_f, verif_f = _resumen_fuentes()
    sitios_regionales = total_f.get("LATAM", 0) + total_f.get("Global", 0)

    filas = []
    for pais in PAISES:
        propios = [f for f in vigentes if f.pais == pais]
        usd = sum(_monto_referencia(f) for f in propios) + usd_transversal
        estado = _estado(total_f.get(pais, 0), verif_f.get(pais, 0))
        filas.append({
            "pais": pais,
            "fondos": len(propios) + n_transversal,
            "usd": usd,
            "luz": estado,
            "sitios": total_f.get(pais, 0) + sitios_regionales,
            "verificadas": verif_f.get(pais, 0),
            "en_indicador": total_f.get(pais, 0) > 0,
        })

    filas.sort(key=lambda r: (_ORDEN[r["luz"]], -r["usd"], -r["sitios"]))
    for i, r in enumerate(filas, 1):
        r["rank"] = i
    return filas


def resumen_cobertura():
    filas = cobertura_por_pais()
    hoy = date.today()
    usd_total = sum(
        _monto_referencia(f) for f in Fondo.query.filter(
            or_(Fondo.fecha_cierre.is_(None), Fondo.fecha_cierre >= hoy)
        ).all()
    )
    return {
        "paises": filas,
        "verdes": sum(1 for r in filas if r["luz"] == "verde"),
        "amarillos": sum(1 for r in filas if r["luz"] == "amarillo"),
        "rojos": sum(1 for r in filas if r["luz"] == "rojo"),
        "total_paises": len(filas),
        "total_sitios": Fuente.query.filter(Fuente.activa.is_(True)).count(),
        "usd_total": usd_total,
    }
