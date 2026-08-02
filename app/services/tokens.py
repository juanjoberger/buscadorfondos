"""Tokens firmados con vencimiento (verificación de correo y reset de contraseña).

Usa itsdangerous (dependencia de Flask) firmando con la SECRET_KEY: no hay
que guardar tokens en la base y vencen solos.
"""
from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SALT_VERIFICACION = "verificar-email"
SALT_RESET = "reset-password"


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generar_token(email, salt):
    return _serializer().dumps(email, salt=salt)


def verificar_token(token, salt, max_age=3600):
    """Devuelve el email si el token es válido y no venció; None si no."""
    try:
        return _serializer().loads(token, salt=salt, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
