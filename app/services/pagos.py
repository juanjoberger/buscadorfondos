"""Cobro del servicio premium (USD 3/mes) vía Mercado Pago.

Mercado Pago por su cobertura LATAM (contexto.md: nada hardcodeado a Chile).
Flujo Checkout Pro:
1. crear_preferencia(user) → URL de pago (init_point) con external_reference=user.id
2. El usuario paga en Mercado Pago.
3. Mercado Pago llama al webhook /webhook/mercadopago con el id del pago.
4. confirmar_pago_mp() consulta el pago a la API (nunca se confía en el body
   del webhook) y, si está aprobado, activa premium por PREMIUM_DIAS.

Sin MP_ACCESS_TOKEN y en desarrollo, existe un modo demo que activa premium
directo para poder probar el gating de alertas.
"""
import hashlib
import hmac
from datetime import date, timedelta

import requests
from flask import current_app

from ..constants import FX_USD
from ..extensions import db
from ..models import Pago, User

MP_API = "https://api.mercadopago.com"

# Monedas sin decimales en Mercado Pago (el precio se redondea a entero).
_SIN_DECIMALES = {"CLP", "PYG", "COP"}


def precio_local(cfg):
    """Convierte el precio ancla (USD) a la moneda de cobro de la cuenta MP.
    Devuelve (monto, moneda) listos para la preferencia de Checkout Pro."""
    moneda = cfg["MP_CURRENCY"]
    tasa = FX_USD.get(moneda, 1)
    monto = float(cfg["PREMIUM_PRICE_USD"]) * tasa
    monto = round(monto) if moneda in _SIN_DECIMALES else round(monto, 2)
    return monto, moneda


def activar_premium(user, proveedor, referencia=None):
    dias = current_app.config["PREMIUM_DIAS"]
    base = user.premium_hasta if user.premium_activo and user.premium_hasta else date.today()
    user.es_premium = True
    user.premium_hasta = base + timedelta(days=dias)
    db.session.add(Pago(
        user_id=user.id, proveedor=proveedor, referencia_externa=referencia,
        monto_usd=current_app.config["PREMIUM_PRICE_USD"], estado="aprobado",
    ))
    db.session.commit()


def _headers():
    return {"Authorization": f"Bearer {current_app.config['MP_ACCESS_TOKEN']}"}


def firma_valida(request):
    """Comprueba que la notificación venga de verdad de Mercado Pago.

    MP firma cada webhook: manda las cabeceras `x-signature` (con un timestamp y
    un hash) y `x-request-id`. Rehacemos el hash con la clave secreta que MP nos
    da en su panel; si coincide, el aviso es auténtico.

    Es defensa en profundidad: aunque alguien nos falsifique un webhook, igual
    consultamos el pago a la API de MP antes de activar nada (ver
    confirmar_pago_mp). La firma solo evita que nos hagan trabajar en vano.

    Si no hay MP_WEBHOOK_SECRET configurado, no se puede validar y se deja pasar
    (la verificación contra la API sigue protegiendo el dinero).
    """
    secreto = current_app.config.get("MP_WEBHOOK_SECRET")
    if not secreto:
        return True

    firma = request.headers.get("x-signature", "")
    partes = dict(
        p.strip().split("=", 1) for p in firma.split(",") if "=" in p
    )
    ts, hash_recibido = partes.get("ts"), partes.get("v1")
    data_id = request.args.get("data.id") or request.args.get("id") or ""
    if not (ts and hash_recibido):
        return False

    # El "manifiesto" es la plantilla exacta que exige Mercado Pago.
    manifiesto = f"id:{data_id.lower()};request-id:{request.headers.get('x-request-id', '')};ts:{ts};"
    esperado = hmac.new(
        secreto.encode(), manifiesto.encode(), hashlib.sha256
    ).hexdigest()
    # compare_digest evita filtrar información por el tiempo que tarda la comparación.
    return hmac.compare_digest(esperado, hash_recibido)


def crear_preferencia(user):
    """Crea la preferencia de Checkout Pro y devuelve la URL de pago."""
    cfg = current_app.config
    site = cfg["SITE_URL"]
    monto, moneda = precio_local(cfg)
    payload = {
        "items": [{
            "title": "Buscador de Fondos — Alertas y recordatorios (1 mes)",
            "quantity": 1,
            "unit_price": monto,
            "currency_id": moneda,
        }],
        "external_reference": str(user.id),
        "back_urls": {estado: f"{site}/premium/retorno?estado={estado}"
                      for estado in ("success", "pending", "failure")},
        "auto_return": "approved",
        "notification_url": f"{site}/webhook/mercadopago",
    }
    r = requests.post(f"{MP_API}/checkout/preferences", json=payload,
                      headers=_headers(), timeout=15)
    r.raise_for_status()
    return r.json()["init_point"]


def confirmar_pago_mp(payment_id):
    """Consulta el pago a la API de MP y activa premium si está aprobado.
    Idempotente: un pago ya registrado no se procesa dos veces."""
    if Pago.query.filter_by(proveedor="mercadopago",
                            referencia_externa=str(payment_id)).first():
        return "ya_procesado"

    r = requests.get(f"{MP_API}/v1/payments/{payment_id}", headers=_headers(), timeout=15)
    r.raise_for_status()
    pago = r.json()

    if pago.get("status") != "approved":
        return f"estado={pago.get('status')}"

    user = db.session.get(User, int(pago["external_reference"]))
    if not user:
        return "usuario_desconocido"

    activar_premium(user, "mercadopago", str(payment_id))
    return "aprobado"
