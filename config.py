"""Configuración central de la aplicación.

Todos los secretos viven en variables de entorno, nunca en el código.
En desarrollo puedes usar un archivo .env (ver .env.example).
"""
import os

basedir = os.path.abspath(os.path.dirname(__file__))


def _database_url() -> str:
    """Devuelve la URL de la base de datos.

    - En producción (Render, Railway, etc.) define DATABASE_URL apuntando a PostgreSQL.
    - Render entrega URLs con el esquema antiguo 'postgres://', que SQLAlchemy
      ya no acepta; aquí se corrige automáticamente.
    - Sin DATABASE_URL, usa SQLite local (solo para desarrollo: en Render el
      disco es efímero y la base se borra en cada deploy).
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    return "sqlite:///" + os.path.join(basedir, "instance", "fondos.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---- Seguridad de las cookies de sesión ----
    # HTTPONLY: JavaScript no puede leer la cookie (si alguien logra inyectar un
    #   script, aun así no puede robar la sesión).
    # SAMESITE Lax: la cookie no viaja en peticiones que vengan de otro sitio,
    #   lo que corta los ataques CSRF por enlace.
    # SECURE se activa solo en producción (en local no hay HTTPS): ver ProdConfig.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    # Tamaño máximo de una petición (16 KB): nuestros formularios son diminutos,
    # así que esto corta de raíz los envíos gigantes que buscan tumbar el servidor.
    MAX_CONTENT_LENGTH = 16 * 1024

    # Token que protege la tarea de envío de alertas (antes era una URL "secreta" pública).
    ALERTS_TOKEN = os.environ.get("ALERTS_TOKEN")

    # SMTP (Brevo u otro proveedor)
    SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp-relay.brevo.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
    MAIL_FROM = os.environ.get("MAIL_FROM") or os.environ.get("SMTP_USER")

    # URL pública del sitio, usada en los correos (links de fondos y de baja).
    SITE_URL = os.environ.get("SITE_URL", "http://localhost:5000")

    # Cuántos resultados ve un visitante sin cuenta antes del muro de registro.
    FREE_RESULTS_LIMIT = int(os.environ.get("FREE_RESULTS_LIMIT", "3"))
    # Fondos por página para usuarios con cuenta. La búsqueda se pagina en la
    # base de datos: sin esto, un catálogo grande se traería entero a memoria.
    RESULTS_PER_PAGE = int(os.environ.get("RESULTS_PER_PAGE", "20"))

    # ---- Servicio premium (alertas y recordatorios), contexto.md §2 ----
    PREMIUM_PRICE_USD = float(os.environ.get("PREMIUM_PRICE_USD", "3"))
    PREMIUM_DIAS = int(os.environ.get("PREMIUM_DIAS", "31"))
    # Días de anticipación con que se recuerda el cierre de una convocatoria.
    REMINDER_DAYS = int(os.environ.get("REMINDER_DAYS", "7"))
    # Access token de Mercado Pago (cobertura LATAM). Vacío = pagos desactivados
    # (en desarrollo existe un modo demo para probar el gating).
    MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")
    # Moneda en que cobra la cuenta de Mercado Pago. Una cuenta MP está ligada a
    # UN país, así que cobra en su moneda local (CLP para una cuenta chilena, BRL
    # para una brasileña, etc.), NO en USD. El precio se muestra anclado en USD y
    # se convierte a esta moneda al crear la preferencia (ver services/pagos.py).
    MP_CURRENCY = os.environ.get("MP_CURRENCY", "CLP")
    # Clave secreta con la que Mercado Pago firma sus webhooks (panel → Webhooks).
    # Si está vacía no se valida la firma, pero el pago igual se verifica contra
    # la API de MP antes de activar premium.
    MP_WEBHOOK_SECRET = os.environ.get("MP_WEBHOOK_SECRET")


class DevConfig(Config):
    DEBUG = True
    # Fallback SOLO para desarrollo local; en producción SECRET_KEY es obligatoria.
    SECRET_KEY = Config.SECRET_KEY or "dev-solo-local-cambia-esto"


class ProdConfig(Config):
    DEBUG = False
    # En producción todo va por HTTPS: las cookies solo viajan cifradas y los
    # enlaces que generamos (correos, webhook) usan https://.
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    if env == "production":
        if not Config.SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY no está definida. Configúrala en las variables "
                "de entorno antes de correr en producción."
            )
        return ProdConfig
    return DevConfig
