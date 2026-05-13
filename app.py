from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os

app = Flask(__name__)
# Configuración clave para seguridad y base de datos
app.config['SECRET_KEY'] = 'tu_clave_secreta_super_segura_aqui' # Cambia esto luego
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fondoslatam.db' # Aquí se guardará la info
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Si alguien intenta entrar a algo privado, lo manda aquí

# --- MODELOS DE BASE DE DATOS (Las Tablas) ---

# Tabla de Usuarios
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    es_premium = db.Column(db.Boolean, default=False)
    perfil_interes = db.Column(db.String(50)) # Ej: ong, investigacion
    region_interes = db.Column(db.String(50))

# Tabla de Fondos (Reemplaza a tu JSON)
class Fondo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    perfil = db.Column(db.String(50), nullable=False)
    pais = db.Column(db.String(50), nullable=False)
    region = db.Column(db.String(50), nullable=False)
    comuna = db.Column(db.String(50), nullable=False)
    link = db.Column(db.String(300), nullable=False)
    fecha_cierre = db.Column(db.String(20)) # Para las futuras alertas

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- RUTAS PRINCIPALES ---

@app.route('/')
def index():
    # 1. Filtros
    perfil_seleccionado = request.args.get('perfil', 'todos')
    region_seleccionada = request.args.get('region', 'todas')
    comuna_seleccionada = request.args.get('comuna', 'todas')
    
    # 2. Búsqueda en la Base de Datos (Ya no en el JSON)
    query = Fondo.query

    if perfil_seleccionado != 'todos':
        query = query.filter_by(perfil=perfil_seleccionado)
    
    # Obtenemos todos los resultados que cumplen
    resultados_brutos = query.all()
    
    # Filtrado lógico por Región y Comuna (como lo teníamos antes)
    resultados = []
    for f in resultados_brutos:
        coincide_region = region_seleccionada == 'todas' or f.region == region_seleccionada or f.region == 'Todas'
        coincide_comuna = comuna_seleccionada == 'todas' or f.comuna == comuna_seleccionada or f.comuna == 'Todas'
        
        if coincide_region and coincide_comuna:
            resultados.append(f)

    # 3. Lógica de Paywall con usuarios reales
    total_disponibles = len(resultados)
    es_premium = False
    
    if current_user.is_authenticated and current_user.es_premium:
        es_premium = True
    elif request.args.get('access') == 'premium': # Mantenemos la puerta trasera temporal
        es_premium = True

    if not es_premium:
        resultados = resultados[:3]
    
    return render_template('index.html', 
                           fondos=resultados, 
                           perfil=perfil_seleccionado,
                           region=region_seleccionada,
                           premium=es_premium,
                           total=total_disponibles)

# --- CREACIÓN DE LA BASE DE DATOS (Solo la primera vez) ---
with app.app_context():
    db.create_all()
    # Aquí podríamos inyectar los datos del JSON viejo a la DB nueva
    if not Fondo.query.first():
        # Ejemplo: Inyectando un fondo de prueba si la BD está vacía
        fondo_prueba = Fondo(nombre="Fondecyt de Iniciación (Ejemplo BD)", perfil="investigacion", pais="Chile", region="Todas", comuna="Todas", link="https://anid.cl")
        db.session.add(fondo_prueba)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
