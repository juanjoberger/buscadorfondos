# Despliegue en Oracle Cloud Free Tier (VPS)

Guía para dejar el sitio corriendo en una VM Always Free de Oracle con
PostgreSQL local, Gunicorn, Nginx, HTTPS y el cron semanal de ingesta+alertas.

## 0. Requisitos previos

- Cuenta en [Oracle Cloud](https://cloud.oracle.com) (Free Tier).
- Un **dominio o subdominio** apuntando a la VM (necesario para HTTPS, y el
  webhook de Mercado Pago exige HTTPS). Si no tienes dominio, un subdominio
  gratuito de DuckDNS sirve para partir.
- Credenciales SMTP de Brevo y (cuando actives pagos) el `MP_ACCESS_TOKEN`.

## 1. Crear la VM

1. Console → **Compute → Instances → Create instance**.
2. Imagen: **Ubuntu 24.04**. Shape: **Ampere A1.Flex** (Always Free: hasta 4
   OCPU / 24 GB — con 1 OCPU / 6 GB sobra). Si no hay capacidad A1 en tu
   región, usa `VM.Standard.E2.1.Micro`.
3. Sube tu llave SSH pública y guarda la **IP pública**.

## 2. Abrir puertos 80 y 443 (dos capas, ambas obligatorias)

**a) En la nube** — VCN → subnet → Security List → *Add Ingress Rules*:
`0.0.0.0/0`, TCP, destination ports `80,443`.

**b) En la VM** — las imágenes Ubuntu de Oracle traen iptables restrictivo
(esta es la trampa clásica: abriste la Security List y "no responde"):

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

Apunta tu dominio (registro A) a la IP pública.

## 3. Software base

```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install python3-venv python3-dev build-essential libpq-dev \
                    nginx postgresql certbot python3-certbot-nginx rsync
```

## 4. Base de datos PostgreSQL

```bash
sudo -u postgres psql -c "CREATE USER fondos WITH PASSWORD 'CAMBIA-ESTA-CLAVE';"
sudo -u postgres psql -c "CREATE DATABASE fondos OWNER fondos;"
```

## 5. Subir el código

Opción A (recomendada): repositorio GitHub privado y `git clone` en la VM.
Opción B (directo desde tu PC, sin repo):

```bash
rsync -av --exclude venv --exclude instance --exclude .env \
  "/home/juan-jose/Escritorio/Buscador de fondos/buscadorfondos-v2/" \
  ubuntu@IP_PUBLICA:/home/ubuntu/buscadorfondos
```

En la VM:

```bash
cd ~/buscadorfondos
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## 6. Variables de entorno

`nano ~/buscadorfondos/.env`:

```bash
FLASK_ENV=production
SECRET_KEY=            # python3 -c "import secrets; print(secrets.token_hex(32))"
DATABASE_URL=postgresql://fondos:CAMBIA-ESTA-CLAVE@localhost/fondos
ALERTS_TOKEN=          # otro token aleatorio (protege cron y export B2B)
SMTP_SERVER=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
MAIL_FROM=alertas@tudominio.com
SITE_URL=https://tudominio.com
MP_ACCESS_TOKEN=       # vacío hasta activar Mercado Pago
PREMIUM_PRICE_USD=3
REMINDER_DAYS=7
```

`chmod 600 .env`. Luego crea tablas y carga datos:

```bash
cd ~/buscadorfondos && ./venv/bin/python -m scripts.seed
# si migras una base que ya existía: ./venv/bin/python -m scripts.migrar
```

> Los fondos del seed son datos de ejemplo: antes de lanzar, carga
> convocatorias reales con `python -m scripts.ingesta archivo.json`.

## 7. Gunicorn como servicio (systemd)

`sudo nano /etc/systemd/system/fondos.service`:

```ini
[Unit]
Description=Buscador de Fondos
After=network.target postgresql.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/buscadorfondos
EnvironmentFile=/home/ubuntu/buscadorfondos/.env
ExecStart=/home/ubuntu/buscadorfondos/venv/bin/gunicorn -c gunicorn.conf.py "run:app"
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fondos
systemctl status fondos        # debe decir "active (running)"
```

## 8. Nginx + HTTPS

`sudo nano /etc/nginx/sites-available/fondos`:

```nginx
# Freno de fuerza bruta, ANTES del bloque server (va en el contexto http).
# La app también limita (flask-limiter), pero cada worker de gunicorn lleva su
# propia cuenta; este límite es único para todos y además frena el ataque antes
# de que llegue a gastar Python. Los dos juntos es lo recomendado.
limit_req_zone $binary_remote_addr zone=login:10m rate=10r/m;
limit_req_status 429;

server {
    listen 80;
    server_name tudominio.com;

    location /static/ { alias /home/ubuntu/buscadorfondos/app/static/; }

    # Rutas de autenticación: 10 por minuto por IP, con un colchón de 5 ráfagas.
    location ~ ^/(login|registro|recuperar)$ {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

> `X-Forwarded-For` y `X-Forwarded-Proto` no son opcionales: sin ellas la app
> vería todas las peticiones como si vinieran de `127.0.0.1` (y el límite por IP
> bloquearía a todos los usuarios a la vez) y creería que la conexión es HTTP.

```bash
sudo ln -s /etc/nginx/sites-available/fondos /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d tudominio.com   # HTTPS + renovación automática
```

## 9. Cron semanal (ingesta → alertas)

La cadencia del producto es semanal (contexto.md). `crontab -e`:

```cron
# Diario 07:00: ingesta parcelada (cada corrida actualiza un lote de fuentes;
# cada fuente se renueva ~semanalmente, repartido por país/institución)
0 7 * * * cd /home/ubuntu/buscadorfondos && ./venv/bin/python -m scripts.ingesta >> /home/ubuntu/ingesta.log 2>&1
# Lunes 09:00: alertas y recordatorios a los usuarios premium
0 9 * * 1 . /home/ubuntu/buscadorfondos/.env && curl -s -X POST "$SITE_URL/tareas/enviar-alertas?token=$ALERTS_TOKEN" >> /home/ubuntu/alertas.log 2>&1
```

## 10. Verificación final

```bash
curl https://tudominio.com/health                      # {"estado":"ok","base_de_datos":"ok"}
curl -I https://tudominio.com                          # 200, landing
curl -X POST "https://tudominio.com/tareas/enviar-alertas?token=$ALERTS_TOKEN"   # JSON con contadores
```

Y a mano: crear una cuenta → llega el correo de verificación → Mi perfil
muestra el checklist → `/premium` muestra el botón de pago.

## Mantenimiento

- **Actualizar código**: repetir rsync/`git pull` y `sudo systemctl restart fondos`.
- **Logs**: `journalctl -u fondos -f` (app), `/home/ubuntu/alertas.log` (cron).
- **Respaldo BD** (cron diario recomendado):
  `pg_dump -U fondos fondos | gzip > ~/backup/fondos-$(date +%F).sql.gz`
- **Export B2B**: `https://tudominio.com/tareas/export-b2b.csv?token=$ALERTS_TOKEN`.
