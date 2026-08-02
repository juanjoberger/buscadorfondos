"""Alertas y recordatorios por correo — el servicio premium (contexto.md §2).

Gating: solo usuarios con perfil de búsqueda válido Y premium activo reciben
correos. Dos tipos de notificación, ninguna se repite (AlertaEnviada.tipo):
- 'nueva': fondos que aparecieron y calzan con el perfil y la localidad.
- 'recordatorio': fondos ya vigentes que cierran dentro de REMINDER_DAYS.

Incluye además el export agregado B2B (mismo token del cron).
"""
import csv
import io
from datetime import date, timedelta

from flask import Blueprint, Response, abort, current_app, render_template, request
from sqlalchemy import func, or_

from ..extensions import db
from ..models import (
    ALERTA_NUEVA,
    ALERTA_RECORDATORIO,
    AlertaEnviada,
    Fondo,
    User,
)
from ..services.embudo import orden_bottom_up
from ..services.mailer import enviar_correo_alerta, enviar_correo_recordatorio

alerts_bp = Blueprint("alerts", __name__)


def _requiere_token():
    token_esperado = current_app.config.get("ALERTS_TOKEN")
    if not token_esperado:
        abort(503, "ALERTS_TOKEN no está configurado en el servidor.")
    token_recibido = request.args.get("token") or request.headers.get("X-Alerts-Token")
    if token_recibido != token_esperado:
        abort(403)


def _query_perfil(usuario):
    """Fondos vigentes que calzan con perfil y localidad declarada del usuario."""
    hoy = date.today()
    query = Fondo.query.filter(
        or_(Fondo.fecha_cierre.is_(None), Fondo.fecha_cierre >= hoy),
        or_(Fondo.fecha_apertura.is_(None), Fondo.fecha_apertura <= hoy),
        Fondo.perfil.in_(usuario.perfiles),
        Fondo.pais.in_((usuario.pais_interes, "LATAM", "Global")),
    )
    if usuario.region_interes:
        query = query.filter(or_(Fondo.region == usuario.region_interes, Fondo.region == "Todas"))
    if usuario.comuna_interes:
        query = query.filter(or_(Fondo.comuna == usuario.comuna_interes, Fondo.comuna == "Todas"))
    return query


def _sin_notificar(query, usuario, tipo):
    ya = db.session.query(AlertaEnviada.fondo_id).filter_by(user_id=usuario.id, tipo=tipo)
    return query.filter(Fondo.id.notin_(ya))


def _registrar(usuario, fondos, tipo):
    for f in fondos:
        db.session.add(AlertaEnviada(user_id=usuario.id, fondo_id=f.id, tipo=tipo))
    db.session.commit()


@alerts_bp.route("/tareas/enviar-alertas", methods=["GET", "POST"])
def enviar_alertas():
    """Cron semanal (la base se actualiza semanalmente, contexto.md §1):
    curl -X POST "https://tusitio.cl/tareas/enviar-alertas?token=XXXX"
    """
    _requiere_token()
    dias_recordatorio = current_app.config["REMINDER_DAYS"]

    usuarios = User.query.filter_by(recibir_alertas=True).all()
    alertas, recordatorios, omitidos, errores = 0, 0, 0, []

    for usuario in usuarios:
        # Gating premium: perfil válido + pago vigente (contexto.md §2).
        if not usuario.puede_recibir_alertas:
            omitidos += 1
            continue

        base = _query_perfil(usuario)

        # 1) Fondos nuevos, ordenados de lo local a lo global.
        nuevos = orden_bottom_up(_sin_notificar(base, usuario, ALERTA_NUEVA).all())
        if nuevos:
            try:
                enviar_correo_alerta(usuario, nuevos)
                _registrar(usuario, nuevos, ALERTA_NUEVA)
                alertas += 1
            except Exception as e:  # un correo fallido no debe frenar al resto
                errores.append(f"{usuario.email}: {e}")

        # 2) Recordatorios de cierre próximo.
        por_cerrar = base.filter(
            Fondo.fecha_cierre.isnot(None),
            Fondo.fecha_cierre <= date.today() + timedelta(days=dias_recordatorio),
        )
        recordar = orden_bottom_up(
            _sin_notificar(por_cerrar, usuario, ALERTA_RECORDATORIO).all()
        )
        if recordar:
            try:
                enviar_correo_recordatorio(usuario, recordar)
                _registrar(usuario, recordar, ALERTA_RECORDATORIO)
                recordatorios += 1
            except Exception as e:
                errores.append(f"{usuario.email}: {e}")

    return {
        "correos_alertas": alertas,
        "correos_recordatorios": recordatorios,
        "usuarios_omitidos_por_gating": omitidos,
        "errores": errores,
    }, 200


@alerts_bp.route("/tareas/export-b2b.csv")
def export_b2b():
    """Agregados para conversar con instituciones: cuánto público hay por
    perfil y territorio, y cuántos fondos aporta cada institución.
    Solo datos agregados: nunca correos ni datos individuales."""
    _requiere_token()

    salida = io.StringIO()
    w = csv.writer(salida)
    w.writerow(["seccion", "pais", "region", "perfil_o_institucion", "usuarios", "premium", "fondos"])

    usuarios = (
        db.session.query(
            User.pais_interes, User.region_interes, User.perfil_interes,
            func.count(User.id),
            func.sum(db.case((User.es_premium, 1), else_=0)),
        )
        .group_by(User.pais_interes, User.region_interes, User.perfil_interes)
        .all()
    )
    for pais, region, perfil, total, premium in usuarios:
        w.writerow(["usuarios", pais or "", region or "Todas", perfil or "", total, int(premium or 0), ""])

    fondos = (
        db.session.query(Fondo.institucion, Fondo.pais, func.count(Fondo.id))
        .group_by(Fondo.institucion, Fondo.pais).all()
    )
    for institucion, pais, total in fondos:
        w.writerow(["fondos", pais, "", institucion or "(sin institución)", "", "", total])

    return Response(
        salida.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=export-b2b.csv"},
    )


@alerts_bp.route("/alertas/baja/<token>")
def baja(token):
    """Baja de alertas en un clic desde el correo, sin pedir login."""
    usuario = User.query.filter_by(unsubscribe_token=token).first()
    if not usuario:
        abort(404)
    usuario.recibir_alertas = False
    db.session.commit()
    return render_template("alertas_baja.html", email=usuario.email)
