"""Orden bottom-up: de lo más local a lo más global (contexto.md §1 y §3).

Todo listado o correo de fondos pasa por aquí. Con actualización semanal y
catálogos de cientos de fondos, ordenar en Python es suficiente.
"""
from datetime import date


def orden_bottom_up(fondos):
    """Local (comuna) → regional → nacional → LATAM → global.
    Dentro de cada nivel, primero lo que cierra antes; permanentes al final."""
    return sorted(
        fondos,
        key=lambda f: (f.alcance, f.fecha_cierre is None, f.fecha_cierre or date.max),
    )
