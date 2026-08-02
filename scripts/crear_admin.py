"""Crea o promueve una cuenta de administrador.

Un admin es un usuario normal con `es_admin=True`, correo verificado y premium
activo (para poder probar TODOS los flujos, incluidos los premium). Da acceso al
panel interno `/admin`.

Uso:
  python -m scripts.crear_admin correo@ejemplo.com                 # genera clave
  python -m scripts.crear_admin correo@ejemplo.com MiClaveSegura   # clave elegida

Si el correo ya existe, lo promueve a admin (no cambia su clave salvo que se
indique una nueva). La contraseña nunca se guarda en el código: la eliges tú o se
genera al azar y se imprime una sola vez.
"""
import os
import secrets
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import User


def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: python -m scripts.crear_admin <correo> [contraseña]")
    email = sys.argv[1].strip().lower()
    password = sys.argv[2] if len(sys.argv) > 2 else secrets.token_urlsafe(9)
    generada = len(sys.argv) <= 2

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User.query.filter_by(email=email).first()
        accion = "promovido" if user else "creado"
        if not user:
            user = User(email=email, pais_interes="Chile", perfil_interes="cultura")
            db.session.add(user)
        if len(sys.argv) > 2 or not user.password_hash:
            user.password_hash = generate_password_hash(password)
        user.es_admin = True
        user.email_verificado = True
        user.es_premium = True
        user.premium_hasta = date.today() + timedelta(days=365)
        db.session.commit()

        print(f"\n✅ Admin {accion}: {email}")
        if generada or len(sys.argv) > 2:
            print(f"   Contraseña: {password}")
        print("   Entra en /login y verás el enlace 'Admin' en el menú.")
        if generada:
            print("   (Anota la contraseña: no se vuelve a mostrar.)\n")


if __name__ == "__main__":
    main()
