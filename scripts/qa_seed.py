"""Prepara la base para QA: cuentas de prueba que cubren toda la matriz de casos.

Idempotente: se puede correr las veces que haga falta. Reemplaza a las cuentas
ad-hoc de desarrollo por un set canónico y documentado (ver QA.md).

Uso:
  python -m scripts.qa_seed            # crea/actualiza las cuentas QA
  python -m scripts.qa_seed --limpiar  # además borra cuentas ad-hoc antiguas

TODAS las cuentas usan la misma contraseña (QA_PASS) salvo el admin, que
conserva la suya. Solo para entornos de prueba: nunca correr en producción.
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import User

QA_PASS = "QA-brote-2026"

# Cuentas ad-hoc creadas durante el desarrollo, superadas por este set canónico.
OBSOLETAS = ["demo@brote.test", "br@brote.test", "es@brote.test",
             "pe@brote.test", "noadmin@brote.test"]

# email → (perfiles, país, región, comuna, verificado, premium, recibir_alertas, nota)
CUENTAS = {
    "qa.premium.cl@brote.test": (
        "cultura,emprendimiento", "Chile", "OHiggins", "Rancagua",
        True, True, True, "Premium OK · país VERDE · recibe alertas, sin avisos de cobertura"),
    "qa.premium.br@brote.test": (
        "cultura", "Brasil", "São Paulo", None,
        True, True, True, "Premium OK · país VERDE · sitio y correos en PORTUGUÉS"),
    "qa.premium.pe@brote.test": (
        "investigacion", "Perú", None, None,
        True, True, True, "Premium OK · país AMARILLO · debe ver avisos de cobertura parcial"),
    "qa.gratis@brote.test": (
        "cultura", "Chile", None, None,
        True, False, True, "Sin premium → NO debe recibir alertas (Ley V)"),
    "qa.sinverificar@brote.test": (
        "cultura", "Chile", None, None,
        False, True, True, "Correo sin verificar → perfil inválido → NO debe recibir alertas (Ley V)"),
    "qa.baja@brote.test": (
        "cultura", "Chile", None, None,
        True, True, False, "Se dio de baja → NO debe recibir alertas"),
    "qa.sinperfil@brote.test": (
        "", "Chile", None, None,
        True, True, True, "Sin ámbito elegido → perfil inválido → NO debe recibir alertas (Ley V)"),
}


def main():
    limpiar = "--limpiar" in sys.argv
    app = create_app()
    with app.app_context():
        db.create_all()

        if limpiar:
            borradas = User.query.filter(User.email.in_(OBSOLETAS)).delete(
                synchronize_session=False)
            db.session.commit()
            print(f"Cuentas ad-hoc borradas: {borradas}")

        for email, (perfiles, pais, region, comuna, verif, premium, alertas, _nota) in CUENTAS.items():
            u = User.query.filter_by(email=email).first()
            if not u:
                u = User(email=email)
                db.session.add(u)
            u.password_hash = generate_password_hash(QA_PASS)
            u.perfil_interes = perfiles
            u.pais_interes, u.region_interes, u.comuna_interes = pais, region, comuna
            u.email_verificado = verif
            u.es_premium = premium
            u.premium_hasta = date.today() + timedelta(days=90) if premium else None
            u.recibir_alertas = alertas
            u.es_admin = False
        db.session.commit()

        print(f"\n✅ {len(CUENTAS)} cuentas QA listas (contraseña: {QA_PASS})\n")
        for email, datos in CUENTAS.items():
            u = User.query.filter_by(email=email).first()
            recibe = "SÍ recibe" if u.puede_recibir_alertas else "NO recibe"
            print(f"  {email:28} {recibe:9} · {datos[7]}")
        admin = User.query.filter_by(es_admin=True).first()
        print(f"\n  Admin: {admin.email if admin else '(ninguno)'} — ver QA.md\n")


if __name__ == "__main__":
    main()
