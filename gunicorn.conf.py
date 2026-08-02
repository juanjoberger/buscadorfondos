"""Configuración del servidor de producción (Gunicorn).

Se usa así en la VM:  gunicorn -c gunicorn.conf.py "run:app"
(el servicio systemd de DESPLIEGUE.md ya apunta aquí).

¿Por qué no `python run.py` en producción? Porque ese es el servidor de pruebas
de Flask: atiende de a una petición, no se recupera de errores y él mismo avisa
"no usar en producción". Gunicorn atiende en paralelo, reinicia procesos que se
cuelgan y aguanta el tráfico real.
"""
import multiprocessing
import os

# ---- Dónde escucha ----
# Solo local: Nginx es quien habla con Internet y nos pasa las peticiones.
bind = "127.0.0.1:8000"

# ---- Cuántos procesos ----
# Regla habitual: (2 × núcleos) + 1 → en la VM Free (1 OCPU) da 3, que es lo justo.
# Pero se capa en 5: cada worker es una copia de la app en memoria (~150 MB), y
# esta aplicación espera a la base de datos, no quema CPU — más workers no la
# hacen más rápida, solo se comen la RAM. WEB_CONCURRENCY lo fuerza desde el .env.
workers = int(os.environ.get(
    "WEB_CONCURRENCY", min(multiprocessing.cpu_count() * 2 + 1, 5)
))
worker_class = "sync"          # nuestras peticiones son cortas: no hace falta async
threads = 2

# ---- Aguante y reciclaje ----
timeout = 30                   # una petición que tarda más de 30 s está colgada
graceful_timeout = 30
keepalive = 5
# Reinicia cada worker tras N peticiones: si hubiera una fuga de memoria, se
# limpia sola y la VM Free nunca se queda sin RAM. El jitter evita que todos
# reinicien a la vez.
max_requests = 1000
max_requests_jitter = 100

# ---- Registro ----
# A stdout/stderr para que systemd los recoja: `journalctl -u fondos -f`.
accesslog = "-"
errorlog = "-"
loglevel = "info"
# Formato con tiempo de respuesta (%(D)s en microsegundos) para detectar lentitud.
# NO se registra el user-agent completo ni cookies: menos datos personales guardados.
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)sus'

# ---- Seguridad ----
# Confía en las cabeceras X-Forwarded-* solo si vienen de Nginx (localhost).
forwarded_allow_ips = "127.0.0.1"
# Corta peticiones con líneas o cabeceras absurdamente largas (intentos de abuso).
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# ---- Nombre visible en `ps` / `htop` ----
proc_name = "brote-capital"
