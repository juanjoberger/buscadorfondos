"""Envío de correos: alertas, recordatorios, verificación y recuperación.

Separado de las rutas para poder testearlo y, más adelante, reemplazarlo por
la API HTTP de Brevo o una cola de tareas sin tocar los blueprints.
En desarrollo sin credenciales SMTP, los correos se imprimen en consola.

Diseño: sistema Sabueso (E1–E4) — tablas + estilos inline, máx 600px,
sin webfonts, por compatibilidad de clientes de correo.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app

from ..i18n import t

FUENTE = "font-family:Arial,Helvetica,sans-serif;"

# (fondo, texto) del badge de alcance, indexado por Fondo.alcance (0=local … 4=global)
NIVEL_COLORES = [
    ("#0B6B43", "#FFFFFF"),
    ("#2E9E68", "#06281B"),
    ("#6FC49A", "#06281B"),
    ("#B7E0CB", "#0E3B26"),
    ("#E7F3EC", "#0E3B26"),
]


def _enviar(destinatario, asunto, html):
    cfg = current_app.config
    if not cfg.get("SMTP_USER") or not cfg.get("SMTP_PASSWORD"):
        if cfg.get("DEBUG"):
            # En desarrollo no se envía nada: el correo queda en el log para poder
            # revisarlo (consola + logs/sabueso.log).
            current_app.logger.debug(
                "[mailer/dev] Para: %s | Asunto: %s\n%s", destinatario, asunto, html
            )
            return
        raise RuntimeError("Faltan credenciales SMTP (SMTP_USER / SMTP_PASSWORD).")

    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = asunto
    mensaje["From"] = cfg["MAIL_FROM"]
    mensaje["To"] = destinatario
    mensaje.attach(MIMEText(html, "html"))

    with smtplib.SMTP(cfg["SMTP_SERVER"], cfg["SMTP_PORT"], timeout=15) as server:
        server.starttls()
        server.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        server.sendmail(cfg["MAIL_FROM"], destinatario, mensaje.as_string())
    # Nunca se registra el contenido del correo enviado: solo el hecho de enviarlo.
    current_app.logger.info("Correo enviado a %s (%s)", destinatario, asunto)


def _envoltura(contenido, pie, lang="es"):
    """Marco Sabueso: cabecera tinta con marca, cuerpo blanco, pie tinta."""
    return f"""<!DOCTYPE html>
<html lang="es"><body style="margin:0;padding:0;background-color:#F6F1E7;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#F6F1E7">
<tr><td align="center" style="padding:24px 12px;">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;">
    <tr><td bgcolor="#2B1D10" style="border-radius:10px 10px 0 0;padding:18px 24px;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
        <td width="16" height="16" bgcolor="#D98A55" style="border-radius:8px 8px 8px 0;font-size:0;line-height:0;">&nbsp;</td>
        <td style="padding-left:9px;{FUENTE}font-size:16px;font-weight:bold;color:#FFFFFF;">Sabueso</td>
      </tr></table>
    </td></tr>
    <tr><td bgcolor="#FFFFFF" style="padding:26px 24px;border-left:1px solid #E8DFCE;border-right:1px solid #E8DFCE;">
      {contenido}
    </td></tr>
    <tr><td bgcolor="#2B1D10" style="border-radius:0 0 10px 10px;padding:16px 24px;">
      <p style="margin:0;{FUENTE}font-size:12px;line-height:1.6;color:#B59F84;">{pie}</p>
    </td></tr>
  </table>
  <p style="margin:14px 0 0;{FUENTE}font-size:11px;color:#8A94A0;">{t("m_pie_lema", lang=lang)}</p>
</td></tr>
</table>
</body></html>"""


def _boton(url, texto):
    return f"""
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center"><tr>
        <td bgcolor="#2B1D10" style="border-radius:999px;">
          <a href="{url}" style="display:inline-block;padding:13px 30px;{FUENTE}font-size:14px;font-weight:bold;color:#FFFFFF;text-decoration:none;">{texto}</a>
        </td>
      </tr></table>"""


def _item_fondo(f, site_url, lang="es", urgencia=False):
    """Ítem de fondo para E1/E2. Los fondos llegan ya ordenados local → global."""
    bg, color = NIVEL_COLORES[f.alcance] if 0 <= f.alcance < 5 else NIVEL_COLORES[4]
    url = f"{site_url}/fondo/{f.id}"

    if urgencia and f.dias_para_cierre is not None:
        dias = f.dias_para_cierre
        cierra = t("m_cierra_en", lang=lang, n=dias, S="S" if dias != 1 else "")
        badge = (f'<td bgcolor="#A8420F" style="border-radius:5px;padding:3px 9px;{FUENTE}'
                 f'font-size:11px;font-weight:bold;color:#FFFFFF;">{cierra}</td>'
                 f'<td style="padding-left:10px;{FUENTE}font-size:12px;color:#5C4B36;">{f.alcance_label}</td>')
        accion = t("m_postular_ahora", lang=lang)
    else:
        if f.fecha_cierre:
            estado = t("m_abierta_cierra", lang=lang, f=f.fecha_cierre.strftime("%d-%m-%Y"))
            color_estado = "#0B6B43"
        else:
            estado = t("m_permanente", lang=lang)
            color_estado = "#3A6485"
        badge = (f'<td bgcolor="{bg}" style="border-radius:5px;padding:3px 8px;{FUENTE}'
                 f'font-size:11px;font-weight:bold;color:{color};">{f.alcance_label.upper()}</td>'
                 f'<td style="padding-left:10px;{FUENTE}font-size:12px;font-weight:bold;color:{color_estado};">{estado}</td>')
        accion = t("m_ver_fondo", lang=lang)

    meta = f.institucion or ""
    if f.monto_texto:
        meta += f" · {f.monto_texto}"

    return f"""
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid #E8DFCE;">
        <tr><td style="padding:16px 0 14px;">
          <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>{badge}</tr></table>
          <p style="margin:9px 0 3px;{FUENTE}font-size:16px;font-weight:bold;line-height:1.3;"><a href="{url}" style="color:#2B1D10;text-decoration:none;">{f.nombre}</a></p>
          <p style="margin:0 0 8px;{FUENTE}font-size:13px;color:#5C4B36;">{meta}</p>
          <p style="margin:0;{FUENTE}font-size:13px;font-weight:bold;"><a href="{url}" style="color:#0B6B43;text-decoration:underline;">{accion}</a></p>
        </td></tr>
      </table>"""


def _pie_baja(usuario, site_url, lang="es"):
    baja_url = f"{site_url}/alertas/baja/{usuario.unsubscribe_token}"
    return (f'{t("m_pie_baja", lang=lang)}<br>'
            f'<a href="{baja_url}" style="color:#D8C7B2;text-decoration:underline;">{t("m_baja_clic", lang=lang)}</a> · '
            f'<a href="{site_url}/mi-perfil" style="color:#D8C7B2;text-decoration:underline;">{t("m_editar_perfil", lang=lang)}</a>')


def _nota_cobertura(usuario, lang):
    """Nota honesta si la cobertura del país del usuario aún está en desarrollo:
    no prometer una lista completa cuando no la tenemos (contexto.md)."""
    from .cobertura import estado_pais
    if not usuario.pais_interes or estado_pais(usuario.pais_interes) == "verde":
        return ""
    texto = t("m_cob_nota", lang=lang, pais=usuario.pais_interes)
    return (f'<p style="margin:0 0 14px;{FUENTE}font-size:12.5px;line-height:1.5;'
            f'color:#8A5E10;background:#FCF3E2;border-radius:8px;padding:10px 12px;">{texto}</p>')


def enviar_correo_alerta(usuario, fondos):
    site_url = current_app.config["SITE_URL"]
    lang = usuario.idioma
    n = len(fondos)
    plur = {"n": n, "s": "s" if n != 1 else "", "ii": "is" if n != 1 else "l"}
    items = "".join(_item_fondo(f, site_url, lang) for f in fondos)
    contenido = f"""
      <p style="margin:0 0 6px;{FUENTE}font-size:12px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;color:#0B6B43;">{t("m_alerta_kicker", lang=lang)}</p>
      <h1 style="margin:0 0 8px;{FUENTE}font-size:23px;line-height:1.25;color:#2B1D10;">{t("m_alerta_titulo", lang=lang, **plur)}</h1>
      <p style="margin:0 0 18px;{FUENTE}font-size:14px;line-height:1.55;color:#5C4B36;">{t("m_alerta_baja", lang=lang)}</p>
      {items}
      {_nota_cobertura(usuario, lang)}
      <div style="padding:18px 0 6px;">{_boton(site_url, t("m_ver_todos", lang=lang))}</div>"""
    _enviar(usuario.email, t("m_alerta_asunto", lang=lang, **plur),
            _envoltura(contenido, _pie_baja(usuario, site_url, lang), lang))


def enviar_correo_recordatorio(usuario, fondos):
    site_url = current_app.config["SITE_URL"]
    lang = usuario.idioma
    n = len(fondos)
    plur = {"n": n, "s": "s" if n != 1 else "", "ii": "is" if n != 1 else "l",
            "n2": ("n" if lang == "es" else "m") if n != 1 else ""}
    items = "".join(_item_fondo(f, site_url, lang, urgencia=True) for f in fondos)
    contenido = f"""
      <p style="margin:0 0 6px;{FUENTE}font-size:12px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;color:#A8420F;">{t("m_rec_kicker", lang=lang)}</p>
      <h1 style="margin:0 0 8px;{FUENTE}font-size:23px;line-height:1.25;color:#2B1D10;">{t("m_rec_titulo", lang=lang, **plur)}</h1>
      <p style="margin:0 0 18px;{FUENTE}font-size:14px;line-height:1.55;color:#5C4B36;">{t("m_rec_baja", lang=lang)}</p>
      {items}
      <div style="padding:18px 0 6px;">{_boton(site_url, t("m_ver_todos", lang=lang))}</div>"""
    _enviar(usuario.email, t("m_rec_asunto", lang=lang),
            _envoltura(contenido, _pie_baja(usuario, site_url, lang), lang))


def _correo_boton(titulo, baja, url, texto_boton, lang):
    return f"""
      <div align="center" style="text-align:center;padding:8px 4px;">
        <h1 style="margin:0 0 10px;{FUENTE}font-size:23px;line-height:1.25;color:#2B1D10;">{titulo}</h1>
        <p style="margin:0 0 22px;{FUENTE}font-size:14px;line-height:1.6;color:#5C4B36;">{baja}</p>
        {_boton(url, texto_boton)}
        <p style="margin:22px 0 0;{FUENTE}font-size:12px;line-height:1.6;color:#8A94A0;">{t("m_no_boton", lang=lang)}<br>
          <a href="{url}" style="color:#0B6B43;text-decoration:underline;word-break:break-all;">{url}</a></p>
      </div>"""


def enviar_correo_verificacion(email, url, lang="es"):
    contenido = _correo_boton(t("m_verif_titulo", lang=lang), t("m_verif_baja", lang=lang),
                              url, t("m_verif_boton", lang=lang), lang)
    _enviar(email, t("m_verif_asunto", lang=lang),
            _envoltura(contenido, t("m_verif_pie", lang=lang), lang))


def enviar_correo_reset(email, url, lang="es"):
    contenido = _correo_boton(t("m_reset_titulo", lang=lang), t("m_reset_baja", lang=lang),
                              url, t("m_reset_boton", lang=lang), lang)
    _enviar(email, t("m_reset_asunto", lang=lang),
            _envoltura(contenido, t("m_reset_pie", lang=lang), lang))
