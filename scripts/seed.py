"""Puebla la base de datos con los fondos de data/fondos_seed.json.

Uso:  python -m scripts.seed
Es idempotente: si un fondo ya existe (mismo nombre + institución), no lo duplica.
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from app.models import Fondo


def parse_fecha(valor):
    return datetime.strptime(valor, "%Y-%m-%d").date() if valor else None


def main():
    app = create_app()
    with app.app_context():
        db.create_all()

        ruta = os.path.join(os.path.dirname(__file__), "..", "data", "fondos_seed.json")
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)

        agregados = 0
        for d in datos:
            existe = Fondo.query.filter_by(
                nombre=d["nombre"], institucion=d.get("institucion")
            ).first()
            if existe:
                continue

            db.session.add(Fondo(
                nombre=d["nombre"],
                institucion=d.get("institucion"),
                descripcion=d.get("descripcion"),
                perfil=d["perfil"],
                pais=d.get("pais", "Chile"),
                region=d.get("region", "Todas"),
                comuna=d.get("comuna", "Todas"),
                monto_min=d.get("monto_min"),
                monto_max=d.get("monto_max"),
                moneda=d.get("moneda", "CLP"),
                fecha_apertura=parse_fecha(d.get("fecha_apertura")),
                fecha_cierre=parse_fecha(d.get("fecha_cierre")),
                link=d["link"],
                fuente=d.get("fuente"),
            ))
            agregados += 1

        db.session.commit()
        print(f"Listo: {agregados} fondos nuevos agregados ({len(datos)} en el archivo).")


if __name__ == "__main__":
    main()
