"""Genera data/ubicaciones_latam.json desde la base countries-states-cities.

Fuente: https://github.com/dr5hn/countries-states-cities-database (licencia
ODbL 1.0 — atribución requerida, ver data/ubicaciones_latam.json "fuente").

Uso:
  python -m scripts.actualizar_ubicaciones [ruta_local.json]
  (sin argumento, descarga el dataset completo ~45 MB desde GitHub)

Chile NO se toma de aquí: su catálogo oficial de comunas curado vive en
app/constants.py y siempre prevalece.
"""
import json
import os
import re
import sys
import urllib.request

URL = ("https://raw.githubusercontent.com/dr5hn/"
       "countries-states-cities-database/master/json/countries%2Bstates%2Bcities.json")

# iso2 → nombre en español usado en toda la app
PAISES_ISO = {
    "AR": "Argentina", "BO": "Bolivia", "BR": "Brasil", "CO": "Colombia",
    "CR": "Costa Rica", "CU": "Cuba", "EC": "Ecuador", "SV": "El Salvador",
    "GT": "Guatemala", "HN": "Honduras", "MX": "México", "NI": "Nicaragua",
    "PA": "Panamá", "PY": "Paraguay", "PE": "Perú", "DO": "República Dominicana",
    "UY": "Uruguay", "VE": "Venezuela",
    # Chile se excluye a propósito: catálogo oficial curado en constants.py
}

# El dataset usa sufijos administrativos en inglés en varios países.
SUFIJOS = re.compile(
    r"\s+(Department|Province|State|Region|Municipality|District|"
    r"Departamento|Provincia)$", re.IGNORECASE,
)


# Nombres que el dataset trae en inglés → forma local
RENOMBRES = {
    "Autonomous City of Buenos Aires": "Ciudad Autónoma de Buenos Aires",
}


def limpiar(nombre):
    nombre = SUFIJOS.sub("", nombre).strip()
    return RENOMBRES.get(nombre, nombre)


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            paises = json.load(f)
    else:
        print(f"Descargando {URL} …")
        with urllib.request.urlopen(URL, timeout=120) as r:
            paises = json.load(r)

    salida = {}
    for pais in paises:
        nombre_pais = PAISES_ISO.get(pais.get("iso2"))
        if not nombre_pais:
            continue
        regiones = {}
        for estado in pais.get("states", []):
            region = limpiar(estado["name"])
            ciudades = sorted({limpiar(c["name"]) for c in estado.get("cities", [])})
            regiones[region] = ciudades
        salida[nombre_pais] = dict(sorted(regiones.items()))

    faltantes = set(PAISES_ISO.values()) - set(salida)
    if faltantes:
        sys.exit(f"ERROR: países no encontrados en el dataset: {faltantes}")

    destino = os.path.join(os.path.dirname(__file__), "..", "data", "ubicaciones_latam.json")
    documento = {
        "fuente": "dr5hn/countries-states-cities-database (ODbL 1.0) — "
                  "https://github.com/dr5hn/countries-states-cities-database",
        "paises": salida,
    }
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(documento, f, ensure_ascii=False, separators=(",", ":"))

    total_ciudades = sum(len(c) for r in salida.values() for c in r.values())
    print(f"OK: {len(salida)} países, "
          f"{sum(len(r) for r in salida.values())} regiones, "
          f"{total_ciudades} ciudades → {os.path.abspath(destino)}")


if __name__ == "__main__":
    main()
