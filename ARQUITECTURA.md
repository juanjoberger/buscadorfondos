# Cómo funciona Brote Capital — recorrido guiado

> Explicación del sistema completo en lenguaje llano, siguiendo lo que pasa de
> verdad cuando alguien usa el sitio. Si quieres entender **una** cosa, busca su
> sección; si quieres entenderlo **todo**, léelo de corrido: está en orden.

## 0. El mapa en 30 segundos

```
El visitante llega  →  app/blueprints/main.py     (buscador, mapa de cobertura)
Se registra         →  app/blueprints/auth.py     (cuenta, perfil, verificación)
Paga                →  app/blueprints/billing.py  + app/services/pagos.py
Recibe correos      →  app/blueprints/alerts.py   + app/services/mailer.py
Tú administras      →  app/blueprints/admin.py
Los fondos entran   →  scripts/ingesta.py + scripts/scrapers.py
```

Todo lo que se guarda vive en **`app/models.py`** (5 tablas) y todo lo que se ve
vive en **`app/templates/`**. Las reglas del negocio están en `contexto.md` y
`DECALOGO.md`; el código solo las obedece.

---

## 1. Las 5 tablas (app/models.py)

Es el corazón: si entiendes esto, entiendes el resto.

| Tabla | Qué guarda | Lo importante |
| --- | --- | --- |
| `User` | Cada cuenta | `perfil_interes` (ámbitos separados por coma), la localidad **declarada** (país/región/comuna), si verificó su correo, si es premium y hasta cuándo |
| `Fondo` | Cada convocatoria | Nombre, institución, perfil, país/región/comuna, montos, fechas, **link a la ficha oficial** y `fuente` (de dónde salió) |
| `Fuente` | Cada sitio que vigilamos | Su método, su licencia, si verificamos su robots.txt, cuándo corrió por última vez |
| `AlertaEnviada` | Qué correo se mandó a quién | Evita repetir: nadie recibe dos veces el mismo fondo |
| `Pago` | Cada cobro | Trazabilidad del dinero |

**Tres propiedades calculadas que mandan en todo** (no son columnas, se calculan
al vuelo):

- `Fondo.alcance` → 0 local, 1 regional, 2 nacional, 3 LATAM, 4 global. **Sale de
  la ubicación del fondo**: si tiene comuna es local, si tiene región es regional,
  etc. Este número es el que ordena todo el sitio.
- `Fondo.estado` → abierta / próxima / cerrada / permanente. **Sale de las fechas**,
  no se guarda: así nunca queda desactualizado.
- `User.puede_recibir_alertas` → `recibir_alertas Y perfil_valido Y premium_activo`.
  **Esta línea es la Ley V.** Si alguna vez alguien recibe un correo sin cumplirla,
  hay un bug grave.

---

## 2. Qué pasa cuando alguien entra al sitio

Ruta: `main.py → index()`.

1. **¿Desde dónde busca?** Si tiene cuenta, se usa la localidad de su cuenta. Si
   no, lo que venga en los filtros (`?pais=Chile`). Nunca se adivina por GPS ni
   por IP: es la Ley I.
2. **Se filtra en la base** (`_aplicar_filtros`): país, perfil, región, comuna,
   estado y texto. Todo se resuelve en SQL — no traemos 400 fondos a memoria para
   descartarlos después.
   - Truco clave: al filtrar por país se incluyen también los fondos `LATAM` y
     `Global`, porque **también se puede postular a ellos desde ese país**.
3. **Se ordenan de local a global** (`services/embudo.py`): es el embudo, la
   identidad del producto.
4. **Se agrupan por nivel** (`_agrupar_embudo`): "Tu comuna", "Tu región", "Tu
   país", "Latinoamérica", "Global". Si un nivel está vacío, se muestra igual con
   un mensaje que empuja al siguiente ("aún no hay fondos de Rancagua, pero los
   regionales aplican para ti").
5. **Si es un visitante sin cuenta**, se le cortan los resultados a 3
   (`FREE_RESULTS_LIMIT`) y aparece el muro con un adelanto de lo que se pierde.
6. **Si su país no tiene cobertura verificada**, se le avisa (Ley II).

---

## 3. Registro, perfil y el "perfil válido"

Ruta: `auth.py`.

- Al registrarse elige **uno o más ámbitos** (checkboxes) y **una** localidad.
  Multi-perfil sí, multi-territorio no.
- La localidad se **valida contra el catálogo** (`_leer_localidad`): si alguien
  manda "país = Narnia" por el formulario, se descarta. Nunca confíes en lo que
  llega del navegador.
- Se manda un correo con un **token firmado** (`services/tokens.py`). El token no
  se guarda en ninguna tabla: va firmado con la `SECRET_KEY` y lleva fecha de
  vencimiento dentro. Si alguien lo altera, la firma no cuadra y no sirve.
- **`perfil_valido`** = tiene ámbito + tiene país + verificó su correo. Es el
  requisito 1 para las alertas (el 2 es el pago).

---

## 4. El pago (billing.py + services/pagos.py)

**Sí acepta tarjetas.** Usamos *Mercado Pago Checkout Pro*: el usuario sale a la
página de Mercado Pago, paga con **tarjeta de crédito, débito, transferencia o
efectivo**, y vuelve. Nosotros **nunca vemos ni guardamos el número de tarjeta** —
por eso no necesitamos certificación PCI-DSS: ese peso lo carga Mercado Pago. Es
la forma correcta y conforme de cobrar sin ser un banco.

El flujo, paso a paso:

1. `crear_preferencia(user)` le pide a MP una "preferencia" (una orden de cobro)
   con `external_reference = user.id` — así sabremos después de quién era el pago.
   El precio se ancla en **USD 3** y se convierte a la moneda de la cuenta MP
   (CLP, BRL…), porque **MP cobra en moneda local, no en dólares**.
2. El usuario paga en el sitio de Mercado Pago.
3. MP nos avisa por el **webhook** `/webhook/mercadopago`.
4. **Nunca le creemos al webhook.** Se hacen dos comprobaciones:
   - `firma_valida()` verifica que el aviso venga de MP (firma HMAC).
   - `confirmar_pago_mp()` **le pregunta a la API de MP** si ese pago existe y
     está aprobado. Solo entonces se activa premium.
5. Es **idempotente**: si MP avisa dos veces del mismo pago, no se cobra ni se
   activa dos veces.

Para cobrar de verdad falta solo configurar las credenciales: ver `PAGOS.md`.

---

## 5. Los correos (alerts.py + services/mailer.py)

La tarea `/tareas/enviar-alertas` la llama un cron semanal, protegida por un
token secreto (no es una página del sitio).

Por cada usuario:
1. **Se aplica la Ley V**: si no cumple `puede_recibir_alertas`, se salta. Punto.
2. Se buscan los fondos que calzan con **sus ámbitos** y **su localidad**.
3. Se descartan los que ya se le enviaron (tabla `AlertaEnviada`).
4. Se ordenan local → global y se manda el correo, **en su idioma** (portugués si
   su cuenta está en Brasil).
5. Se hace lo mismo con los recordatorios de cierre (`REMINDER_DAYS` días antes).

Los correos se arman con tablas HTML y estilos incrustados (`mailer.py`) porque
los clientes de correo no entienden CSS moderno. En desarrollo no se envía nada:
se imprimen en la consola.

---

## 6. De dónde salen los fondos (scripts/)

- **`scrapers.py`** — un recolector por sitio. Cada uno devuelve diccionarios con
  el mismo formato. Hoy: `fondos_gob_cl` (Chile), `fapesp_br` (Brasil), más dos
  adaptadores genéricos (`adaptador_rss`, `adaptador_opendata`) que permiten
  sumar fuentes **con configuración, sin escribir código**.
- **`ingesta.py`** — el planificador. No actualiza todo de golpe: cada corrida
  toma un **lote** de fuentes vencidas, priorizando las que históricamente abren
  convocatorias en este mes. Con un cron diario, el catálogo se renueva por
  semana sin fundir el servidor.
- **`upsert`** — los fondos se identifican por su **link**. Si ya existe, se
  actualiza; si no, se crea. Así nunca hay duplicados ni se re-alerta.
- Antes de recolectar cualquier sitio se comprueba su `robots.txt`. La estrategia
  legal completa está en `INGESTA_ESTRATEGIA.md`.

---

## 7. El semáforo de cobertura (services/cobertura.py)

Mide **qué tan fidedigna** es nuestra información de cada país (no cuánta plata
suman los fondos):

- **verde**: tiene al menos una fuente propia verificada → Chile y Brasil.
- **amarillo**: tiene fuentes identificadas pero sin verificar → los otros 17.
- **rojo**: no tenemos fuentes de ese país.

`estado_pais()` se usa en tres lugares para ser honestos con el usuario: el
banner del buscador, la nota en `/premium` antes de cobrar, y la nota en el
correo. Es la Ley II hecha código.

---

## 8. Los dos idiomas (app/i18n.py)

No usamos librerías de traducción: hay un diccionario `TEXTOS` donde cada clave
tiene su par `(español, portugués)`, y una función `t("clave")`. El idioma se
resuelve así: `?lang=` → sesión → **cuenta inscrita en Brasil** → cabecera del
navegador → español.

Regla: **toda cadena que ve el usuario pasa por `t()`**. Si escribes texto suelto
en una plantilla, quedará solo en español y romperás la Ley VI.

---

## 9. Seguridad (app/security.py)

Cada respuesta lleva cabeceras que le dicen al navegador qué está permitido
(sobre todo la **CSP**, que bloquea cualquier script que no sea nuestro). Las
cookies de sesión son `HttpOnly` + `SameSite` + `Secure` en producción. Los
errores muestran una página propia, nunca la traza del programa. Ver
`SEGURIDAD.md` para el detalle y para qué hacer si te atacan.

---

## 10. Cómo trabajar con esto sin romperlo

```bash
./venv/bin/ruff check .              # lint: imports muertos, bugs, seguridad
./venv/bin/python -m scripts.qa_smoke  # que no se rompan las leyes (Ley V, II, I)
./venv/bin/python run.py             # levantar y mirar
```

- Regla de oro: **antes de dar por terminado un cambio, corre `qa_smoke` y mira
  el sitio** (skill `/demo`).
- Si un cambio choca con las reglas del proyecto, la skill `/coherencia` lo
  detecta y te consulta a ti antes de torcer ninguna ley.
