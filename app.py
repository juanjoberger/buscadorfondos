from flask import Flask, render_template, request
import json
import os

app = Flask(__name__)

def cargar_fondos():
    ruta_archivo = os.path.join(app.root_path, 'fondos.json')
    with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
        return json.load(archivo)

@app.route('/')
def index():
    fondos_database = cargar_fondos()
    
    # 1. Capturamos todos los filtros de la URL
    perfil_seleccionado = request.args.get('perfil', 'todos')
    region_seleccionada = request.args.get('region', 'todas')
    comuna_seleccionada = request.args.get('comuna', 'todas')
    es_premium = request.args.get('access', 'free') == 'premium'
    
    # 2. Iniciamos con todos los fondos
    resultados = fondos_database

    # 3. Filtramos por Perfil
    if perfil_seleccionado != 'todos':
        resultados = [f for f in resultados if f.get('perfil') == perfil_seleccionado]
        
    # 4. Filtramos por Región
    if region_seleccionada != 'todas':
        resultados = [f for f in resultados if f.get('region') == region_seleccionada or f.get('region') == 'Todas']

    # 5. Filtramos por Comuna
    if comuna_seleccionada != 'todas':
        resultados = [f for f in resultados if f.get('comuna') == comuna_seleccionada or f.get('comuna') == 'Todas']
    # 6. Lógica de Paywall
    total_disponibles = len(resultados)
    if not es_premium:
        resultados = resultados[:3]
    
    # 7. Enviamos variables al HTML
    return render_template('index.html', 
                           fondos=resultados, 
                           perfil=perfil_seleccionado,
                           region=region_seleccionada,
                           premium=es_premium,
                           total=total_disponibles)

if __name__ == '__main__':
    app.run(debug=True)
