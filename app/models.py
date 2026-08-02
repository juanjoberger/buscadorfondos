"""Modelos de la base de datos.

Novedades de esta iteración (ver contexto.md):
- User: localidad declarada completa (país/región/comuna), verificación de
  correo, premium con vencimiento (premium_hasta) y las propiedades que
  definen el gating del servicio de pago: perfil_valido y premium_activo.
- Fondo: propiedad `alcance` (0 local → 4 global) para el orden bottom-up.
- AlertaEnviada: columna `tipo` para distinguir alertas de fondos nuevos y
  recordatorios de cierre sin repetir ninguno.
- Pago: trazabilidad de cada cobro de USD 3.
"""
import secrets
from datetime import date, datetime, timezone

from flask_login import UserMixin
from sqlalchemy import and_, case

from .extensions import db, login_manager

PERFILES = {
    "emprendimiento": "Emprendimiento",
    "ong": "ONG / Fundación",
    "investigacion": "Investigación / Académico",
    "privado": "Empresa privada",
    "cultura": "Cultura, patrimonio y artes",
}

# Etiquetas de perfil en portugués (sitio bilingüe es/pt-BR)
PERFILES_PT = {
    "emprendimiento": "Empreendedorismo",
    "ong": "ONG / Fundação",
    "investigacion": "Pesquisa / Acadêmico",
    "privado": "Empresa privada",
    "cultura": "Cultura, patrimônio e artes",
}

ESTADO_ABIERTA = "abierta"
ESTADO_PROXIMA = "proxima"
ESTADO_CERRADA = "cerrada"
ESTADO_PERMANENTE = "permanente"

# Tipos de notificación (AlertaEnviada.tipo)
ALERTA_NUEVA = "nueva"
ALERTA_RECORDATORIO = "recordatorio"

# Niveles del embudo bottom-up (Fondo.alcance)
ALCANCE_LABELS = {0: "Local", 1: "Regional", 2: "Nacional", 3: "Latinoamérica", 4: "Global"}


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    es_premium = db.Column(db.Boolean, default=False, nullable=False)
    premium_hasta = db.Column(db.Date)  # null + es_premium=True = premium manual sin vencimiento
    # Multi-ámbito: claves de PERFILES separadas por coma. La localidad sigue
    # siendo UNA sola (multi-perfil sí, multi-territorio no).
    perfil_interes = db.Column(db.String(120))
    pais_interes = db.Column(db.String(50), default="Chile")
    region_interes = db.Column(db.String(50))
    comuna_interes = db.Column(db.String(80))
    email_verificado = db.Column(db.Boolean, default=False, nullable=False)
    recibir_alertas = db.Column(db.Boolean, default=True, nullable=False)
    es_admin = db.Column(db.Boolean, default=False, nullable=False)  # panel interno /admin
    unsubscribe_token = db.Column(
        db.String(64), unique=True, nullable=False,
        default=lambda: secrets.token_urlsafe(24),
    )
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    alertas_enviadas = db.relationship(
        "AlertaEnviada", backref="user", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    pagos = db.relationship(
        "Pago", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def perfiles(self) -> list:
        """Ámbitos de fondos elegidos por el usuario (uno o más)."""
        return [p for p in (self.perfil_interes or "").split(",") if p in PERFILES]

    @property
    def idioma(self) -> str:
        """Idioma de los correos: pt para cuentas inscritas en Brasil."""
        return "pt" if self.pais_interes == "Brasil" else "es"

    # ---- Gating del servicio premium (contexto.md §2) ----
    @property
    def perfil_valido(self) -> bool:
        """Perfil de búsqueda válidamente generado: qué busca + desde dónde
        (localidad declarada, sin GPS) + correo verificado (alertas van por correo)."""
        return bool(self.perfiles and self.pais_interes and self.email_verificado)

    @property
    def premium_activo(self) -> bool:
        if not self.es_premium:
            return False
        return self.premium_hasta is None or self.premium_hasta >= date.today()

    @property
    def puede_recibir_alertas(self) -> bool:
        """Las dos condiciones del servicio de pago + no haberse dado de baja."""
        return self.recibir_alertas and self.perfil_valido and self.premium_activo

    def __repr__(self):
        return f"<User {self.email}>"


class Fondo(db.Model):
    __tablename__ = "fondos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(250), nullable=False)
    institucion = db.Column(db.String(200))
    descripcion = db.Column(db.Text)
    perfil = db.Column(db.String(50), nullable=False, index=True)
    # pais: un país concreto, "LATAM" (postulable desde toda la región) o "Global"
    pais = db.Column(db.String(50), nullable=False, default="Chile", index=True)
    region = db.Column(db.String(50), nullable=False, default="Todas", index=True)
    comuna = db.Column(db.String(80), nullable=False, default="Todas")
    monto_min = db.Column(db.Integer)   # en la moneda del fondo; null si no aplica
    monto_max = db.Column(db.Integer)
    moneda = db.Column(db.String(10), default="CLP")
    fecha_apertura = db.Column(db.Date)
    fecha_cierre = db.Column(db.Date)   # null = convocatoria permanente
    link = db.Column(db.String(400), nullable=False)
    fuente = db.Column(db.String(120))  # de dónde salió el dato (trazabilidad B2B)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    # ---- Embudo bottom-up: 0 local → 4 global ----
    @property
    def alcance(self) -> int:
        if self.pais == "Global":
            return 4
        if self.pais == "LATAM":
            return 3
        if self.comuna and self.comuna != "Todas":
            return 0
        if self.region and self.region != "Todas":
            return 1
        return 2

    @classmethod
    def alcance_sql(cls):
        """La MISMA lógica que la propiedad `alcance`, pero como expresión SQL.

        ¿Por qué duplicarla? Porque `alcance` se calcula en Python, y para
        ordenar y paginar en la base de datos (en vez de traer miles de fondos a
        memoria) el motor SQL necesita entender ese orden.

        ⚠️ Si cambias `alcance`, cambia también esto: deben dar siempre el mismo
        número. `scripts/qa_smoke.py` verifica que coincidan en todos los fondos.
        """
        return case(
            (cls.pais == "Global", 4),
            (cls.pais == "LATAM", 3),
            (and_(cls.comuna.isnot(None), cls.comuna != "Todas"), 0),
            (and_(cls.region.isnot(None), cls.region != "Todas"), 1),
            else_=2,
        )

    @classmethod
    def orden_bottom_up_sql(cls):
        """Orden del embudo para consultas paginadas: local → global y, dentro de
        cada nivel, primero lo que cierra antes (las permanentes al final)."""
        return (
            cls.alcance_sql(),
            cls.fecha_cierre.is_(None),  # False(0) antes que True(1): permanentes al final
            cls.fecha_cierre,
        )

    @property
    def alcance_label(self) -> str:
        return ALCANCE_LABELS[self.alcance]

    # ---- Estado calculado a partir de las fechas ----
    @property
    def estado(self) -> str:
        hoy = date.today()
        if self.fecha_cierre and self.fecha_cierre < hoy:
            return ESTADO_CERRADA
        if self.fecha_apertura and self.fecha_apertura > hoy:
            return ESTADO_PROXIMA
        if self.fecha_cierre is None:
            return ESTADO_PERMANENTE
        return ESTADO_ABIERTA

    @property
    def dias_para_cierre(self):
        if self.fecha_cierre is None:
            return None
        return (self.fecha_cierre - date.today()).days

    @property
    def perfil_label(self) -> str:
        return PERFILES.get(self.perfil, self.perfil.capitalize())

    @property
    def monto_texto(self):
        """Formato legible del monto, p. ej. 'Hasta $25.000.000 CLP'."""
        def fmt(n):
            return f"${n:,.0f}".replace(",", ".")

        if self.monto_min and self.monto_max:
            return f"{fmt(self.monto_min)} – {fmt(self.monto_max)} {self.moneda}"
        if self.monto_max:
            return f"Hasta {fmt(self.monto_max)} {self.moneda}"
        if self.monto_min:
            return f"Desde {fmt(self.monto_min)} {self.moneda}"
        return None

    def __repr__(self):
        return f"<Fondo {self.nombre}>"


class AlertaEnviada(db.Model):
    """Registro de notificaciones: nunca se repite el mismo fondo, del mismo
    tipo, al mismo usuario. tipo = 'nueva' (fondo nuevo) o 'recordatorio' (cierre)."""
    __tablename__ = "alertas_enviadas"
    __table_args__ = (
        db.UniqueConstraint("user_id", "fondo_id", "tipo", name="uq_alerta_user_fondo_tipo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    fondo_id = db.Column(db.Integer, db.ForeignKey("fondos.id"), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default=ALERTA_NUEVA)
    enviada_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    fondo = db.relationship("Fondo")


class Fuente(db.Model):
    """Registro de fuentes de convocatorias (una por institución/portal).

    La ingesta parcelada (scripts/ingesta.py) usa este registro para decidir
    qué fuentes actualizar en cada corrida: por frecuencia, prioridad y
    estacionalidad histórica de publicación de cada fuente.
    """
    __tablename__ = "fuentes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), unique=True, nullable=False)  # coincide con Fondo.fuente
    institucion = db.Column(db.String(200), nullable=False)
    pais = db.Column(db.String(50), nullable=False)  # país, "LATAM" o "Global"
    tipo = db.Column(db.String(20), nullable=False, default="manual")  # scraper | manual
    scraper = db.Column(db.String(50))       # clave en scripts.scrapers.SCRAPERS
    url = db.Column(db.String(400))
    frecuencia_dias = db.Column(db.Integer, nullable=False, default=7)
    prioridad = db.Column(db.Integer, nullable=False, default=2)  # 1 alta … 3 baja
    activa = db.Column(db.Boolean, nullable=False, default=True)
    ultima_ejecucion = db.Column(db.DateTime)
    ultimo_resultado = db.Column(db.String(300))

    # ---- Gobernanza legal (INGESTA_ESTRATEGIA.md §5.2): con qué derecho tenemos
    #      los datos de esta fuente. Cada Fondo hereda de aquí su base legal. ----
    metodo = db.Column(db.String(20))        # api|opendata|rss|sitemap|scrape|aportada|manual
    licencia = db.Column(db.String(120))     # p. ej. "CC-BY 4.0", "índice (hecho público)"
    terminos_url = db.Column(db.String(400)) # Términos/robots.txt revisados
    robots_ok = db.Column(db.Boolean, nullable=False, default=False)
    atribucion = db.Column(db.String(200))   # crédito a mostrar si la licencia lo exige
    config = db.Column(db.Text)              # JSON: params de los adaptadores genéricos
    # Estado de fetch condicional (ahorro de energía: 304 Not Modified).
    http_etag = db.Column(db.String(200))
    http_last_modified = db.Column(db.String(100))

    def __repr__(self):
        return f"<Fuente {self.nombre}>"


class Pago(db.Model):
    """Trazabilidad de cada cobro premium (USD 3)."""
    __tablename__ = "pagos"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    proveedor = db.Column(db.String(30), nullable=False)          # mercadopago / demo
    referencia_externa = db.Column(db.String(120), index=True)    # id del pago en el proveedor
    monto_usd = db.Column(db.Numeric(6, 2), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")  # pendiente/aprobado/rechazado
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
