"""Migración liviana para bases existentes (SQLite o PostgreSQL).

Uso: python -m scripts.migrar
Agrega las columnas nuevas de esta iteración si faltan y crea las tablas
nuevas (pagos). En bases recién creadas no hace nada (create_all basta).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db

# tabla → {columna: definición SQL}
COLUMNAS = {
    "users": {
        "premium_hasta": "DATE",
        "pais_interes": "VARCHAR(50) DEFAULT 'Chile'",
        "comuna_interes": "VARCHAR(80)",
        "email_verificado": "BOOLEAN NOT NULL DEFAULT 0",
        "es_admin": "BOOLEAN NOT NULL DEFAULT 0",
    },
    "alertas_enviadas": {
        "tipo": "VARCHAR(20) NOT NULL DEFAULT 'nueva'",
    },
    "fuentes": {
        "metodo": "VARCHAR(20)",
        "licencia": "VARCHAR(120)",
        "terminos_url": "VARCHAR(400)",
        "robots_ok": "BOOLEAN NOT NULL DEFAULT 0",
        "atribucion": "VARCHAR(200)",
        "config": "TEXT",
        "http_etag": "VARCHAR(200)",
        "http_last_modified": "VARCHAR(100)",
    },
}


# Backfills tras agregar columnas (idempotentes).
BACKFILLS = [
    # perfil_interes pasó de 50 a 120 (multi-ámbito); solo Postgres necesita ampliar.
    ("postgresql", "ALTER TABLE users ALTER COLUMN perfil_interes TYPE VARCHAR(120)"),
    # metodo por defecto según el tipo previo.
    (None, "UPDATE fuentes SET metodo='scrape' WHERE metodo IS NULL AND tipo='scraper'"),
    (None, "UPDATE fuentes SET metodo='manual' WHERE metodo IS NULL AND tipo='manual'"),
]


def main():
    app = create_app()
    with app.app_context():
        db.create_all()  # crea tablas nuevas (pagos) y las que falten

        inspector = inspect(db.engine)
        agregadas = 0
        for tabla, columnas in COLUMNAS.items():
            if tabla not in inspector.get_table_names():
                continue
            existentes = {c["name"] for c in inspector.get_columns(tabla)}
            for nombre, definicion in columnas.items():
                if nombre in existentes:
                    continue
                db.session.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {definicion}"))
                agregadas += 1
                print(f"+ {tabla}.{nombre}")
        db.session.commit()

        dialecto = db.engine.dialect.name
        for solo_dialecto, sql in BACKFILLS:
            if solo_dialecto and solo_dialecto != dialecto:
                continue
            try:
                db.session.execute(text(sql))
            except Exception as e:
                print(f"  (backfill omitido: {e})")
        db.session.commit()
        print(f"Listo: {agregadas} columna(s) agregada(s).")


if __name__ == "__main__":
    main()
