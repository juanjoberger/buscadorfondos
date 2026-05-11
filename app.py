from flask import Flask, render_template, request
import json # Importamos la librería para leer archivos JSON
import os   # Importamos os para manejar rutas de archivos de forma segura

app = Flask(__name__)

def cargar_fondos():
    """
    Esta función abre el archivo fondos.json, lee su contenido
    y lo convierte en una lista de diccionarios de Python.
    """
    # Buscamos la ruta exacta del archivo en el servidor
    ruta_archivo = os.path.join(app.root_path, 'fondos.json')
    
    # Abrimos el archivo en modo lectura ('r') con codificación UTF-8 para evitar errores con tildes
    with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
        datos = json.load(archivo)
    return datos

@app.route('/')
def index():
    # 1. Cargamos la base de datos externa
    fondos_database = cargar_fondos()
    
    # 2. Obtenemos el perfil de la URL (ej: /?perfil=ong)
    perfil_seleccionado = request.args.get('perfil', 'todos')
    es_premium = request.args.get('access', 'free') == 'premium'
    
    # 3. Filtrado lógico por perfil usando comprensión de listas en Python
    if perfil_seleccionado != 'todos':
        resultados = [f for f in fondos_database if f['perfil'] == perfil_seleccionado]
    else:
        resultados = fondos_database

    # 4. Lógica de Paywall: Si no es premium, cortamos la lista a los primeros 3
    total_disponibles = len(resultados)
    if not es_premium:
        resultados = resultados[:3]
    
    # 5. Enviamos los datos al HTML
    return render_template('index.html', 
                           fondos=resultados, 
                           perfil=perfil_seleccionado, 
                           premium=es_premium,
                           total=total_disponibles)

if __name__ == '__main__':
    app.run(debug=True)
