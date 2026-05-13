from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import redirect, url_for, flash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_provisional_para_desarrollo'

# FIX TÉCNICO: Calculamos la ruta absoluta del servidor para SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'fondoslatam.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS DE LA BASE DE DATOS (Las Tablas) ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    es_premium = db.Column(db.Boolean, default=False)
    perfil_interes = db.Column(db.String(50)) 
    region_interes = db.Column(db.String(50))

class Fondo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    perfil = db.Column(db.String(50), nullable=False)
    pais = db.Column(db.String(50), nullable=False)
    region = db.Column(db.String(50), nullable=False)
    comuna = db.Column(db.String(50), nullable=False)
    link = db.Column(db.String(300), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- RUTAS PRINCIPALES ---

@app.route('/')
def index():
    # 1. Filtros capturados de la URL
    perfil_seleccionado = request.args.get('perfil', 'todos')
    region_seleccionada = request.args.get('region', 'todas')
    comuna_seleccionada = request.args.get('comuna', 'todas')
    
    # 2. Búsqueda directa en la Base de Datos SQLAlchemy
    query = Fondo.query

    if perfil_seleccionado != 'todos':
        query = query.filter_by(perfil=perfil_seleccionado)
    
    resultados_brutos = query.all()
    resultados = []
    
    # Filtrado lógico por Región y Comuna en cascada
    for f in resultados_brutos:
        coincide_region = (region_seleccionada == 'todas' or f.region == region_seleccionada or f.region == 'Todas')
        coincide_comuna = (comuna_seleccionada == 'todas' or f.comuna == comuna_seleccionada or f.comuna == 'Todas')
        
        if coincide_region and coincide_comuna:
            resultados.append(f)

    # 3. Lógica de Paywall con usuarios de Base de Datos
    total_disponibles = len(resultados)
    es_premium = False
    
    if current_user.is_authenticated and current_user.es_premium:
        es_premium = True
    elif request.args.get('access') == 'premium': # Mantenemos la puerta trasera para pruebas
        es_premium = True

    if not es_premium:
        resultados = resultados[:3]
    
    return render_template('index.html', 
                           fondos=resultados, 
                           perfil=perfil_seleccionado,
                           region=region_seleccionada,
                           premium=es_premium,
                           total=total_disponibles)
# --- RUTAS DE USUARIOS ---

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    # Si el usuario envía el formulario...
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        perfil = request.form.get('perfil')
        region = request.form.get('region')

        # 1. Verificamos si el correo ya existe en la Base de Datos
        user = User.query.filter_by(email=email).first()
        if user:
            # Aquí idealmente mostraríamos un mensaje de error en pantalla
            return redirect(url_for('registro'))

        # 2. Creamos el nuevo usuario encriptando su contraseña
        nuevo_usuario = User(
            email=email, 
            password=generate_password_hash(password), # Contraseña segura
            perfil_interes=perfil,
            region_interes=region
        )
        
        # 3. Lo guardamos en la Base de Datos
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        # 4. Iniciamos su sesión automáticamente y lo enviamos al inicio
        login_user(nuevo_usuario)
        return redirect(url_for('index'))

    # Si entra a la página normalmente, le mostramos el formulario
    return render_template('registro.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))
    
# --- CREACIÓN E INYECCIÓN DE LA BASE DE DATOS ---
with app.app_context():
    db.create_all() # Crea el archivo fondoslatam.db si no existe
    
    # Si la tabla de fondos está vacía, inyectamos ejemplos para verificar que funciona
    if not Fondo.query.first():
        fondo_1 = Fondo(nombre="Fondecyt de Iniciación en Investigación", perfil="investigacion", pais="Chile", region="Todas", comuna="Todas", link="https://anid.cl")
        fondo_2 = Fondo(nombre="Capital Semilla Emprende (Sercotec)", perfil="emprendimiento", pais="Chile", region="Todas", comuna="Todas", link="https://www.sercotec.cl")
        fondo_3 = Fondo(nombre="Fondo de Desarrollo Vecinal Santiago", perfil="ong", pais="Chile", region="Metropolitana", comuna="Santiago", link="https://munistgo.cl")
        fondo_4 = Fondo(nombre="Subvención I+D Corfo", perfil="privado", pais="Chile", region="Todas", comuna="Todas", link="https://corfo.cl")
        
        db.session.add_all([fondo_1, fondo_2, fondo_3, fondo_4])
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
