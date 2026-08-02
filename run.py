"""Punto de entrada.

Desarrollo:  python run.py
Producción:  gunicorn "run:app"
"""
import os

from dotenv import load_dotenv

load_dotenv()  # carga .env en desarrollo local

from app import create_app
from app.extensions import db

app = create_app()

# Crea las tablas si no existen (para el primer arranque).
# Para cambios de esquema posteriores usa Flask-Migrate: flask db migrate / upgrade.
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_ENV") != "production")
