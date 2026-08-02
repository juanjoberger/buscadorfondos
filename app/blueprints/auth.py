"""Autenticación, perfil (localidad declarada LATAM), verificación de correo
y recuperación de contraseña."""
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from ..constants import PAISES, UBICACIONES, regiones_de
from ..extensions import db, limiter
from ..i18n import idioma_actual, t
from ..models import PERFILES, User
from ..services.mailer import enviar_correo_reset, enviar_correo_verificacion
from ..services.tokens import (
    SALT_RESET,
    SALT_VERIFICACION,
    generar_token,
    verificar_token,
)

auth_bp = Blueprint("auth", __name__)


def _leer_localidad(form):
    """Valida la localidad declarada contra el catálogo. Sin GPS: lo que el
    usuario declara es la localidad de la cuenta."""
    pais = form.get("pais")
    if pais not in PAISES:
        return None, None, None
    region = form.get("region")
    region = region if region in regiones_de(pais) else None
    comuna = form.get("comuna")
    ciudades = UBICACIONES[pais].get(region, []) if region else []
    comuna = comuna if comuna in ciudades else None
    return pais, region, comuna


def _leer_perfiles(form):
    """Multi-ámbito: uno o más perfiles de PERFILES (la localidad sigue siendo una)."""
    return [p for p in form.getlist("perfil") if p in PERFILES]


def _mandar_verificacion(email, lang=None):
    token = generar_token(email, SALT_VERIFICACION)
    enviar_correo_verificacion(
        email, url_for("auth.verificar", token=token, _external=True),
        lang=lang or idioma_actual(),
    )


@auth_bp.route("/registro", methods=["GET", "POST"])
# Alta masiva de cuentas falsas: 5 por hora desde la misma IP.
@limiter.limit("5 per hour", methods=["POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        perfiles = _leer_perfiles(request.form)
        pais, region, comuna = _leer_localidad(request.form)

        if not email or "@" not in email:
            flash(t("fl_correo_invalido"), "error")
            return render_template("auth/registro.html"), 400

        if len(password) < 8:
            flash(t("fl_pass_corta"), "error")
            return render_template("auth/registro.html"), 400

        if not perfiles:
            flash(t("fl_elige_perfil"), "error")
            return render_template("auth/registro.html"), 400

        if not pais:
            flash(t("fl_elige_pais"), "error")
            return render_template("auth/registro.html"), 400

        if User.query.filter_by(email=email).first():
            flash(t("fl_ya_registrado"), "error")
            return redirect(url_for("auth.login"))

        usuario = User(
            email=email,
            password_hash=generate_password_hash(password),
            perfil_interes=",".join(perfiles),
            pais_interes=pais,
            region_interes=region,
            comuna_interes=comuna,
            recibir_alertas=request.form.get("alertas") == "on",
        )
        db.session.add(usuario)
        db.session.commit()

        try:
            _mandar_verificacion(email, lang=usuario.idioma)
        except Exception:
            flash(t("fl_no_verificacion"), "error")

        login_user(usuario)
        flash(t("fl_cuenta_creada"), "ok")
        return redirect(url_for("main.index"))

    return render_template("auth/registro.html")


@auth_bp.route("/verificar/<token>")
def verificar(token):
    email = verificar_token(token, SALT_VERIFICACION, max_age=60 * 60 * 72)
    usuario = User.query.filter_by(email=email).first() if email else None
    if not usuario:
        flash(t("fl_enlace_invalido"), "error")
        return redirect(url_for("main.index"))
    usuario.email_verificado = True
    db.session.commit()
    flash(t("fl_correo_verificado"), "ok")
    return redirect(url_for("auth.perfil") if current_user.is_authenticated else url_for("auth.login"))


@auth_bp.route("/verificar/reenviar", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
def reenviar_verificacion():
    if current_user.email_verificado:
        flash(t("fl_ya_verificado"), "ok")
    else:
        try:
            _mandar_verificacion(current_user.email, lang=current_user.idioma)
            flash(t("fl_verificacion_enviada"), "ok")
        except Exception:
            flash(t("fl_no_verificacion"), "error")
    return redirect(url_for("auth.perfil"))


@auth_bp.route("/login", methods=["GET", "POST"])
# Fuerza bruta: 10 intentos por minuto y 50 por hora desde una misma IP. Un
# humano que se equivoca de contraseña no llega ni cerca; un robot probando
# claves se topa con el muro al décimo intento.
@limiter.limit("10 per minute; 50 per hour", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            return redirect(request.args.get("next") or url_for("main.index"))

        flash(t("fl_credenciales"), "error")

    return render_template("auth/login.html")


@auth_bp.route("/recuperar", methods=["GET", "POST"])
# Evita que se use este formulario para bombardear de correos a un tercero.
@limiter.limit("5 per hour", methods=["POST"])
def recuperar():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        # Misma respuesta exista o no la cuenta: no revelar correos registrados.
        usuario = User.query.filter_by(email=email).first()
        if usuario:
            try:
                token = generar_token(email, SALT_RESET)
                enviar_correo_reset(
                    email, url_for("auth.reset", token=token, _external=True),
                    lang=usuario.idioma,
                )
            except Exception:
                # No se revela al visitante si el correo existe o si el envío falló
                # (evita enumerar cuentas), pero sí queda registrado para operación.
                current_app.logger.exception("Fallo al enviar el correo de recuperación")
        flash(t("fl_reset_enviado"), "ok")
        return redirect(url_for("auth.login"))
    return render_template("auth/recuperar.html")


@auth_bp.route("/reset/<token>", methods=["GET", "POST"])
# Probar tokens de recuperación al azar.
@limiter.limit("10 per hour", methods=["POST"])
def reset(token):
    email = verificar_token(token, SALT_RESET, max_age=3600)
    usuario = User.query.filter_by(email=email).first() if email else None
    if not usuario:
        flash(t("fl_reset_invalido"), "error")
        return redirect(url_for("auth.recuperar"))

    if request.method == "POST":
        password = request.form.get("password") or ""
        if len(password) < 8:
            flash(t("fl_pass_corta"), "error")
            return render_template("auth/reset.html", token=token), 400
        usuario.password_hash = generate_password_hash(password)
        usuario.email_verificado = True  # llegó por su correo: queda verificado
        db.session.commit()
        flash(t("fl_pass_cambiada"), "ok")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset.html", token=token)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@auth_bp.route("/mi-perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if request.method == "POST":
        perfiles = _leer_perfiles(request.form)
        if perfiles:
            current_user.perfil_interes = ",".join(perfiles)

        pais, region, comuna = _leer_localidad(request.form)
        if pais:
            current_user.pais_interes = pais
            current_user.region_interes = region
            current_user.comuna_interes = comuna

        current_user.recibir_alertas = request.form.get("alertas") == "on"
        db.session.commit()
        flash(t("fl_prefs_ok"), "ok")
        return redirect(url_for("auth.perfil"))

    return render_template("auth/perfil.html")
