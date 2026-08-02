# Buscador de Fondos — v2

Plataforma para encontrar convocatorias públicas y privadas para proyectos en Chile, con filtros por perfil, región, comuna, estado y texto, cuentas de usuario y alertas por correo de fondos nuevos.

Esta versión reemplaza al piloto con una arquitectura lista para crecer.

## Qué cambió respecto al piloto (v1)

| Área | v1 (piloto) | v2 |
| --- | --- | --- |
| Estructura | Un solo `app.py` | App factory + blueprints (`main`, `auth`, `alerts`) |
| Modelo de fondo | nombre, perfil, ubicación, link | + institución, descripción, montos, fechas de apertura/cierre, fuente, estado calculado |
| Filtros | Parcialmente en Python | 100% en SQL, + filtro de estado y búsqueda de texto |
| Plantillas | Faltaban `registro.html` y `perfil.html` (error 500) | Completas: registro, perfil, detalle de fondo, baja de alertas |
| Seguridad | `SECRET_KEY` en el código, sin CSRF, ruta de correos pública | Secretos por variables de entorno, CSRF global, tarea de alertas protegida por token |
| Alertas | Enviaba siempre todos los fondos coincidentes | Solo fondos **nuevos** (tabla `alertas_enviadas`) + link de baja en un clic |
| Base de datos | SQLite (se borra en cada deploy de Render) | Soporta PostgreSQL vía `DATABASE_URL` + Flask-Migrate |
| Catálogo comunas | Duplicado dentro del HTML | Un solo catálogo en Python, servido por `/api/ubicaciones` |

## Correr en local

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # opcional en desarrollo
python -m scripts.seed        # crea tablas y carga datos de ejemplo
python run.py                 # http://localhost:5000
```

> Los fondos de `data/fondos_seed.json` son **datos de ejemplo** con fechas y montos referenciales. Antes de lanzar, verifica cada convocatoria en su fuente oficial.

## Desplegar en Render

1. Crea una base **PostgreSQL** en Render y copia su `DATABASE_URL` (sin PostgreSQL, la base SQLite se borra en cada deploy).
2. Crea un **Web Service** desde este repo:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn "run:app"`
3. Variables de entorno del servicio:
   - `FLASK_ENV=production`
   - `SECRET_KEY` → genera una: `python -c "import secrets; print(secrets.token_hex(32))"`
   - `DATABASE_URL` → la de PostgreSQL
   - `ALERTS_TOKEN` → otro token aleatorio (protege la tarea de alertas)
   - `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM` → credenciales de Brevo
   - `SITE_URL` → URL pública del sitio (para los links de los correos)
4. Corre el seed una vez desde la Shell del servicio: `python -m scripts.seed`

## Alertas y recordatorios (servicio premium, cron semanal)

Las alertas son el beneficio de pago (USD 3/mes, ver `contexto.md`): solo las reciben usuarios con **perfil de búsqueda válido** (perfil + localidad declarada + correo verificado) y **premium activo**. `POST /tareas/enviar-alertas` requiere el token y envía dos tipos de correo sin repetir ninguno: fondos **nuevos** (ordenados de lo local a lo global) y **recordatorios** de cierres dentro de `REMINDER_DAYS`. Prográmala semanal (la base se actualiza semanalmente), idealmente después de la ingesta:

```bash
python -m scripts.ingesta        # corrida parcelada (ver sección Ingesta)
curl -X POST "https://tusitio.onrender.com/tareas/enviar-alertas?token=TU_ALERTS_TOKEN"
```

Cada correo incluye un link de baja individual (`/alertas/baja/<token>`), sin pedir login.

## Ingesta parcelada de convocatorias

La tabla `fuentes` registra cada portal/institución (20 sembradas en
`data/fuentes_seed.json`, por país y prioridad). `python -m scripts.ingesta`
elige en cada corrida un **lote** de fuentes vencidas, priorizando por
importancia y por **estacionalidad histórica** (los meses en que cada fuente
suele publicar, según las fechas de apertura ya ingeridas). Con un cron diario
y frecuencia semanal por fuente, el catálogo se renueva completo cada semana
repartiendo la carga por país e institución.

- Scraper implementado: **fondos.gob.cl** (~390 convocatorias del Estado de
  Chile, con institución, fechas, montos y región). Los demás portales están
  registrados como `tipo=manual` a la espera de scraper (ver `scripts/scrapers.py`).
- Forzar una fuente: `python -m scripts.ingesta --fuente fondos.gob.cl`
- Cargar un archivo a mano: `python -m scripts.ingesta archivo.json`
- El upsert es por `link`: re-ingerir no duplica ni vuelve a alertar.

## Pagos premium (Mercado Pago)

`/premium` inicia un Checkout Pro de Mercado Pago (cobertura LATAM) por `PREMIUM_PRICE_USD`; el webhook `/webhook/mercadopago` confirma el pago contra la API de MP y activa `es_premium` por `PREMIUM_DIAS`. Define `MP_ACCESS_TOKEN` en el entorno. Sin token y en desarrollo hay un **modo demo** que activa premium directo para probar el gating.

## Export B2B

`GET /tareas/export-b2b.csv?token=TU_ALERTS_TOKEN` entrega agregados (usuarios por país/región/perfil con conteo premium, fondos por institución) para conversar con las instituciones. Nunca incluye correos ni datos individuales.

## Bases existentes

Si ya tenías una base de la versión anterior: `python -m scripts.migrar` agrega las columnas nuevas sin borrar datos.

## Migraciones de esquema

El primer arranque crea las tablas automáticamente. Para cambios posteriores al modelo:

```bash
flask --app run.py db init      # solo la primera vez
flask --app run.py db migrate -m "descripcion del cambio"
flask --app run.py db upgrade
```

## Estructura

```text
├── run.py                  # punto de entrada (dev y gunicorn)
├── config.py               # configuración por variables de entorno
├── app/
│   ├── __init__.py         # app factory
│   ├── extensions.py       # db, login, csrf, migrate
│   ├── models.py           # User, Fondo (estado calculado), AlertaEnviada
│   ├── constants.py        # regiones y comunas de Chile
│   ├── blueprints/
│   │   ├── main.py         # buscador, detalle, /api/ubicaciones
│   │   ├── auth.py         # login, registro, perfil
│   │   └── alerts.py       # tarea de alertas + baja
│   ├── services/mailer.py  # envío de correos
│   ├── templates/          # base, index, detalle, auth/, baja
│   └── static/             # styles.css, ubicaciones.js
├── data/fondos_seed.json   # datos de ejemplo enriquecidos
└── scripts/seed.py         # carga idempotente de datos
```

## Próximos pasos sugeridos

1. **Ingesta automática**: scrapers de fondos.gob.cl, Corfo, ANID y Sercotec que escriban al modelo `Fondo` (el campo `fuente` ya existe para trazar el origen). Es lo que mantiene la base fresca sin trabajo manual.
2. **Capa de IA**: un agente con la API de Anthropic que lea las bases de cada convocatoria y complete `descripcion`, montos y requisitos de elegibilidad; y en el buscador, "describe tu proyecto" → fondos recomendados.
3. **Premium**: el campo `es_premium` existe pero no gatilla nada aún. Candidatos: análisis de elegibilidad con IA, exportación, alertas instantáneas.
4. **Recuperación de contraseña** y verificación de correo.
