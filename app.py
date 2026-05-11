from flask import Flask, render_template, request

app = Flask(__name__)

# Base de datos de ejemplo (Simulando lo que recolectarás)
FONDOS_DATABASE = [
    {"nombre": "Capital Abeja", "perfil": "emprendimiento", "pais": "Chile", "link": "https://www.sercotec.cl"},
    {"nombre": "Fondo de Fortalecimiento ONG", "perfil": "ong", "pais": "Chile", "link": "#"},
    {"nombre": "Subvención I+D Privada", "perfil": "privado", "pais": "LATAM", "link": "#"},
    {"nombre": "Fondo Innovación Social", "perfil": "ong", "pais": "Chile", "link": "#"},
    {"nombre": "Startup Chile", "perfil": "emprendimiento", "pais": "Chile", "link": "#"},
    {"nombre": "Fondo Protección Ambiental", "perfil": "ong", "pais": "Chile", "link": "#"},
]

@app.route('/')
def index():
    # Obtenemos el perfil de la URL (ej: /?perfil=ong)
    perfil_seleccionado = request.args.get('perfil', 'todos')
    es_premium = request.args.get('access', 'free') == 'premium'
    
    # Filtrado por perfil
    if perfil_seleccionado != 'todos':
        resultados = [f for f in FONDOS_DATABASE if f['perfil'] == perfil_seleccionado]
    else:
        resultados = FONDOS_DATABASE

    # Lógica de Paywall: Si no es premium, solo mostramos 3
    total_disponibles = len(resultados)
    if not es_premium:
        resultados = resultados[:3]
    
    return render_template('index.html', 
                           fondos=resultados, 
                           perfil=perfil_seleccionado, 
                           premium=es_premium,
                           total=total_disponibles)

if __name__ == '__main__':
    app.run(debug=True)
