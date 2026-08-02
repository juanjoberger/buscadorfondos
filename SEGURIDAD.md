# Seguridad — estado, protección del código y qué hacer ante un ataque

## 1. Lo que ya está puesto

| Defensa | Dónde | Qué evita |
| --- | --- | --- |
| Cabeceras de seguridad (CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy) | `app/security.py` | Scripts inyectados (XSS), clickjacking, filtración de URLs. Es lo que miran los filtros de navegadores y los escáneres |
| HSTS en producción | `app/security.py` | Que alguien fuerce la conexión a HTTP para espiarla |
| Cookies `HttpOnly` + `SameSite=Lax` + `Secure` (prod) | `config.py` | Robo de sesión desde JavaScript y ataques CSRF por enlace |
| CSRF en todos los formularios | Flask-WTF | Que otro sitio haga acciones en nombre de tu usuario |
| Contraseñas con hash (Werkzeug/scrypt) | `auth.py` | Que un robo de base exponga contraseñas |
| Tokens firmados con vencimiento | `services/tokens.py` | Enlaces de verificación/reset falsificados |
| Verificación del pago contra la API de MP + firma HMAC del webhook | `services/pagos.py` | Que alguien active premium con un webhook falso |
| Páginas de error propias | `app/security.py` | Que un error muestre rutas, SQL o la traza del programa |
| Límite de 16 KB por petición | `config.py` | Envíos gigantes que buscan tumbar el servidor |
| `defusedxml` para leer RSS | `scripts/scrapers.py` | Ataques XML (XXE, billion laughs) desde una fuente externa |
| Rate limiting (10 login/min, 5 registros/h por IP) | `app/extensions.py` + `auth.py` | Fuerza bruta de contraseñas y alta masiva de cuentas falsas |
| No se guardan datos de tarjetas | Checkout Pro | El riesgo (y la certificación PCI) los carga Mercado Pago |
| `.gitignore` con `.env`, `instance/`, `respaldos/` | raíz | Subir secretos o correos de usuarios al repositorio |
| Sin geolocalización | Ley I + `Permissions-Policy` | Recolectar datos sensibles que no necesitamos |

## 2. Lo que falta antes de abrir al público

1. **HTTPS con certificado** (certbot) — obligatorio: sin esto las cookies
   `Secure` no viajan y Mercado Pago no acepta el webhook. Ver `DESPLIEGUE.md`.
2. **`SECRET_KEY` y `ALERTS_TOKEN` aleatorios y largos** en el `.env` de la VM
   (`python3 -c "import secrets; print(secrets.token_hex(32))"`). Nunca los del
   ejemplo.
3. **Cambiar la contraseña del admin de pruebas** (`BroteAdmin2026`) y crear el
   admin real con `scripts/crear_admin.py`.
4. **`limit_req` de Nginx** — la app ya limita (flask-limiter), pero cada worker
   de gunicorn lleva su propia cuenta; el freno único para todos es el de Nginx.
   El bloque está listo en `DESPLIEGUE.md` §8: solo hay que copiarlo.
5. **Respaldos automáticos** (`/respaldo-bd`) — un ataque no siempre roba: a veces
   borra.
6. **Cortafuegos**: en la VM de Oracle deja abiertos solo 22, 80 y 443.
7. **`git init` + repositorio privado** — el `.gitignore` está listo, pero el
   proyecto aún no está bajo control de versiones: la protección solo se activa
   cuando exista el repo.

## 3. Sobre proteger el código de que te lo copien

Te lo digo derecho, porque aquí es fácil gastar esfuerzo en lo que no protege:

**El código de este sistema no es visible para tus usuarios.** Es Python que corre
en tu servidor: el navegador solo recibe HTML, CSS y un JavaScript mínimo. Nadie
puede "ver el código fuente" del buscador, del embudo ni de la ingesta. Lo único
que se expone es la apariencia, y eso se copia mirando la pantalla — ofuscar no
lo impide.

Lo que **sí** puede filtrar tu código, y ya está cubierto o hay que cuidar:

- Modo debug encendido en producción → mostraría la traza y permitiría ejecutar
  código. **Cubierto**: `FLASK_ENV=production` apaga debug y hay páginas de error
  propias.
- Subir el repositorio con `.env` o exponer la carpeta `.git` en el servidor.
  **Cubierto** por `.gitignore`; en la VM no se sirve `.git` porque Nginx solo
  publica `/static/`.
- Repositorio público en GitHub. **Acción tuya**: mantenlo **privado**.

**Y ahora lo importante:** tu negocio no está en el código. Este sistema es Flask
estándar; un buen programador lo replica en semanas. Lo que **no** se copia fácil
es:

1. **La base de fuentes verificadas** y el trabajo legal detrás (qué sitio permite
   qué, con qué licencia).
2. **Los usuarios y sus perfiles declarados** — el activo que hace posible el
   negocio B2B.
3. **La relación con las instituciones** y que adopten la norma técnica.
4. **La marca y ser el primero** en LATAM haciendo esto en serio y en dos idiomas.

Mi recomendación honesta: no gastes energía en esconder el código (mantén el repo
privado y ya). Gasta esa energía en **acumular fuentes, usuarios y acuerdos**, que
es el foso de verdad. Y protege lo legal: registra la marca y pon términos de uso.

## 4. Si te atacan

**Ataque de fuerza bruta al login** (muchos intentos):
```bash
sudo journalctl -u fondos --since "1 hour ago" | grep -c "POST /login"
```
→ Instala rate limiting (punto 2.4) y, si viene de pocas IPs, bloquéalas:
`sudo iptables -A INPUT -s IP_ATACANTE -j DROP`

**Saturación / caída del sitio**:
```bash
systemctl status fondos          # ¿el servicio vive?
df -h && free -h                 # ¿disco o memoria llenos?
sudo journalctl -u fondos -n 100 # ¿qué dice el error?
sudo systemctl restart fondos    # reinicio limpio
```
(La skill `/estado-produccion` hace todo esto de una vez.)

**Sospecha de robo de datos**: cambia `SECRET_KEY` (invalida todas las sesiones y
todos los tokens en circulación), rota `ALERTS_TOKEN` y `MP_ACCESS_TOKEN`, obliga
a cambiar contraseñas, y avisa a los usuarios si sus correos quedaron expuestos
(en Chile y Brasil hay obligación de notificar: Ley 21.719 y LGPD).

**Cobros falsos**: no deberían poder — el webhook valida firma y además pregunta a
la API de MP. Verifica la tabla `pagos` contra tu panel de Mercado Pago.

## 5. Rutina recomendada

- **Antes de cada despliegue**: `ruff check .` + `scripts/qa_smoke` + `/coherencia`.
- **Semanal**: `/estado-produccion` (salud, certificado, crons) y `/respaldo-bd`.
- **Mensual**: `pip list --outdated` y actualizar dependencias con parches.
- **Siempre**: si algo huele raro, mira `journalctl -u fondos` antes de tocar nada.
