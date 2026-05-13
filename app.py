from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_provisional_para_desarrollo'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'fondoslatam.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS DE LA BASE DE DATOS ---

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

# --- RUTAS DE USUARIOS ---

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        perfil = request.form.get('perfil')
        region = request.form.get('region')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Este correo ya está registrado.')
            return redirect(url_for('registro'))

        nuevo_usuario = User(
            email=email, 
            password=generate_password_hash(password),
            perfil_interes=perfil,
            region_interes=region
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        login_user(nuevo_usuario)
        return redirect(url_for('index'))

    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        # Comparamos la contraseña encriptada
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Correo o contraseña incorrectos.')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- RUTAS PRINCIPALES ---

@app.route('/')
def index():
    perfil_seleccionado = request.args.get('perfil', 'todos')
    region_seleccionada = request.args.get('region', 'todas')
    comuna_seleccionada = request.args.get('comuna', 'todas')
    
    query = Fondo.query
    if perfil_seleccionado != 'todos':
        query = query.filter_by(perfil=perfil_seleccionado)
    
    resultados_brutos = query.all()
    resultados = []
    
    for f in resultados_brutos:
        coincide_region = (region_seleccionada == 'todas' or f.region == region_seleccionada or f.region == 'Todas')
        coincide_comuna = (comuna_seleccionada == 'todas' or f.comuna == comuna_seleccionada or f.comuna == 'Todas')
        
        if coincide_region and coincide_comuna:
            resultados.append(f)

    total_disponibles = len(resultados)
    
    # Lógica estricta de Premium
    es_premium = False
    if current_user.is_authenticated and current_user.es_premium:
        es_premium = True
    elif request.args.get('access') == 'premium': 
        es_premium = True

    if not es_premium:
        resultados = resultados[:3]
    
    return render_template('index.html', 
                           fondos=resultados, 
                           perfil=perfil_seleccionado,
                           region=region_seleccionada,
                           premium=es_premium,
                           total=total_disponibles)

# --- CREACIÓN DE LA BASE DE DATOS ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
