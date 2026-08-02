"""Cobro premium: página, inicio de pago y webhook de Mercado Pago."""
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import csrf
from ..i18n import t
from ..services.pagos import activar_premium, confirmar_pago_mp, crear_preferencia, firma_valida

billing_bp = Blueprint("billing", __name__)


@billing_bp.route("/premium")
@login_required
def premium():
    from ..services.cobertura import estado_pais
    from ..services.pagos import precio_local
    monto_local, moneda_local = precio_local(current_app.config)
    # Honestidad antes de cobrar: si la cobertura del país del usuario está en
    # desarrollo, se le advierte que recibirá lo verificado (contexto.md: si
    # ofrecemos algo, debemos tenerlo y de forma oportuna).
    pais = current_user.pais_interes
    cobertura = estado_pais(pais) if pais else "verde"
    return render_template(
        "premium.html",
        precio=current_app.config["PREMIUM_PRICE_USD"],
        precio_local=monto_local,
        moneda_local=moneda_local,
        cobertura=cobertura,
        pais_usuario=pais,
        pagos_configurados=bool(current_app.config.get("MP_ACCESS_TOKEN")),
        modo_demo=current_app.config.get("DEBUG", False),
    )


@billing_bp.route("/premium/pagar", methods=["POST"])
@login_required
def pagar():
    if not current_user.perfil_valido:
        flash(t("fl_completa_perfil"), "error")
        return redirect(url_for("auth.perfil"))

    if current_app.config.get("MP_ACCESS_TOKEN"):
        try:
            return redirect(crear_preferencia(current_user))
        except Exception:
            flash(t("fl_pago_error"), "error")
            return redirect(url_for("billing.premium"))

    if current_app.config.get("DEBUG"):
        # Modo demo SOLO en desarrollo: permite probar el gating sin pasarela.
        activar_premium(current_user, "demo")
        flash(t("fl_demo_premium"), "ok")
        return redirect(url_for("auth.perfil"))

    flash(t("fl_pagos_no_config"), "error")
    return redirect(url_for("billing.premium"))


@billing_bp.route("/premium/retorno")
@login_required
def retorno():
    estado = request.args.get("estado")
    if estado == "success":
        flash(t("fl_pago_ok"), "ok")
    elif estado == "pending":
        flash(t("fl_pago_pendiente"), "ok")
    else:
        flash(t("fl_pago_fallo"), "error")
    return redirect(url_for("auth.perfil"))


@billing_bp.route("/webhook/mercadopago", methods=["POST"])
@csrf.exempt
def webhook_mercadopago():
    """Mercado Pago notifica aquí; el estado real siempre se consulta a su API
    (nunca se confía en el body del webhook)."""
    if not current_app.config.get("MP_ACCESS_TOKEN"):
        return "", 503

    # 1ª barrera: ¿la notificación viene de verdad de Mercado Pago?
    if not firma_valida(request):
        current_app.logger.warning("Webhook con firma inválida desde %s", request.remote_addr)
        return "", 401

    data = request.get_json(silent=True) or {}
    payment_id = (data.get("data") or {}).get("id") or request.args.get("data.id")
    if data.get("type") != "payment" and request.args.get("type") != "payment":
        return "", 200  # otras notificaciones no nos interesan
    if not payment_id:
        return "", 400

    try:
        resultado = confirmar_pago_mp(payment_id)
    except Exception:
        return "", 500  # MP reintenta si no respondemos 2xx
    return {"resultado": resultado}, 200
