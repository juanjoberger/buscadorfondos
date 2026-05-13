from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
    recibir_alertas = db.Column(db.Boolean, default=True)

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
            region_interes=region,
            recibir_alertas=True
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

@app.route('/mi-perfil', methods=['GET', 'POST'])
@login_required
def mi_perfil():
    if request.method == 'POST':
        current_user.perfil_interes = request.form.get('perfil')
        current_user.region_interes = request.form.get('region')
        current_user.recibir_alertas = request.form.get('alertas') == 'on' 
        
        db.session.commit()
        flash('¡Tus preferencias han sido actualizadas!')
        return redirect(url_for('mi_perfil'))
        
    return render_template('perfil.html')

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
    
    if not current_user.is_authenticated:
        resultados = resultados[:3]
    
    return render_template('index.html', fondos=resultados, perfil=perfil_seleccionado, region=region_seleccionada, total=total_disponibles)

# --- MOTOR DE CORREOS: RUTA SECRETA ---
@app.route('/enviar-alertas-secreto-123')
def enviar_alertas():
    SMTP_SERVER = "smtp-relay.brevo.com"
    SMTP_PORT = 587
    SMTP_USER = os.environ.get('SMTP_USER') 
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    REMITENTE = os.environ.get('SMTP_USER')

    if not SMTP_USER or not SMTP_PASSWORD:
        return "Error: Faltan las credenciales SMTP en las variables de entorno de Render."

    usuarios_alertas = User.query.filter_by(recibir_alertas=True).all()
    correos_enviados = 0

    try:
        # Añadimos un timeout de 10 segundos para evitar el colapso del servidor (Error 502)
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls() 
        server.login(SMTP_USER, SMTP_PASSWORD)

        for usuario in usuarios_alertas:
            fondos_match = Fondo.query.filter_by(perfil=usuario.perfil_interes).filter((Fondo.region == usuario.region_interes) | (Fondo.region == 'Todas')).all()

            if fondos_match:
                mensaje = MIMEMultipart("alternative")
                mensaje["Subject"] = "💡 Nuevos fondos disponibles para tu proyecto"
                mensaje["From"] = REMITENTE
                mensaje["To"] = usuario.email

                lista_html = ""
                for f in fondos_match:
                    lista_html += f"<li style='margin-bottom: 10px;'><b>{f.nombre}</b> <br> <a href='{f.link}' style='color: #4f46e5;'>Ver convocatoria</a></li>"

                html = f"""
                <html>
                  <body style="font-family: Arial, sans-serif; background-color: #f9fafb; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 10px; border: 1px solid #e5e7eb;">
                        <h2 style="color: #312e81;">¡Hola! Tenemos fondos para ti.</h2>
                        <p style="color: #4b5563;">Hemos encontrado estas convocatorias según tu perfil:</p>
                        <ul style="color: #1f2937;">{lista_html}</ul>
                    </div>
                  </body>
                </html>
                """
                mensaje.attach(MIMEText(html, "html"))
                server.sendmail(REMITENTE, usuario.email, mensaje.as_string())
                correos_enviados += 1

        server.quit()
        return f"Proceso terminado con éxito. Se enviaron {correos_enviados} correos de alerta."

    except Exception as e:
        # Esto capturará el error de red o autenticación antes de que Render lance el 502
        return f"Atención: Hubo un error técnico al intentar conectar con Brevo. Detalle: {str(e)}" tus contraseñas. Detalle técnico: {str(e)}"

# --- INYECCIÓN AUTOMÁTICA DE LA BASE DE DATOS ---
with app.app_context():
    db.create_all()
    if not Fondo.query.first():
        ruta_json = os.path.join(basedir, 'fondos.json')
        try:
            with open(ruta_json, 'r', encoding='utf-8') as archivo:
                fondos_data = json.load(archivo)
                for f in fondos_data:
                    nuevo_fondo = Fondo(nombre=f['nombre'], perfil=f['perfil'], pais=f['pais'], region=f['region'], comuna=f['comuna'], link=f['link'])
                    db.session.add(nuevo_fondo)
                db.session.commit()
        except FileNotFoundError:
            pass

if __name__ == '__main__':
    app.run(debug=True)
