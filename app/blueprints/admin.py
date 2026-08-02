"""Panel interno de administración (solo lectura).

Herramienta de operación, NO parte del producto para el usuario final (por eso no
choca con la Ley IV del DECALOGO: la simplicidad rige la experiencia del usuario,
no las herramientas internas). Requiere `User.es_admin`.
"""
from datetime import date

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from ..extensions import db
from ..models import PERFILES, Fondo, Fuente, Pago, User
from ..services.cobertura import resumen_cobertura

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@login_required
def panel():
    if not current_user.es_admin:
        abort(403)

    hoy = date.today()

    def por(col, modelo=User, filtro=None):
        q = db.session.query(col, func.count()).group_by(col).order_by(func.count().desc())
        if filtro is not None:
            q = q.filter(filtro)
        return [(k or "—", n) for k, n in q.all()]

    usuarios = {
        "total": User.query.count(),
        "verificados": User.query.filter_by(email_verificado=True).count(),
        "premium": User.query.filter_by(es_premium=True).count(),
        "por_pais": por(User.pais_interes),
        "admins": User.query.filter_by(es_admin=True).count(),
    }

    vivas = Fondo.query.filter(or_(Fondo.fecha_cierre.is_(None), Fondo.fecha_cierre >= hoy)).count()
    fondos = {
        "total": Fondo.query.count(),
        "vigentes": vivas,
        "por_pais": por(Fondo.pais, Fondo),
        "por_fuente": por(Fondo.fuente, Fondo)[:12],
    }

    fuentes = {
        "total": Fuente.query.count(),
        "verificadas": Fuente.query.filter_by(robots_ok=True).count(),
        "scrapers": Fuente.query.filter_by(tipo="scraper").count(),
        "por_metodo": por(Fuente.metodo, Fuente),
        "activas": Fuente.query.filter_by(tipo="scraper").order_by(Fuente.ultima_ejecucion.desc().nullslast()).all(),
    }

    pagos = {
        "total": Pago.query.count(),
        "aprobados": Pago.query.filter_by(estado="aprobado").count(),
    }

    return render_template(
        "admin.html",
        usuarios=usuarios, fondos=fondos, fuentes=fuentes, pagos=pagos,
        cobertura=resumen_cobertura(),
        perfiles=PERFILES,
    )
