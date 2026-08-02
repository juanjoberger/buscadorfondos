# Brief de diseño — Sabueso · Sabujo · FundHound

> Documento autocontenido para diseñar **exclusivamente la interfaz**. No hay que
> tocar backend ni lógica: el equipo técnico adapta los diseños a las plantillas
> Flask/Jinja existentes. Todo lo que necesitas saber está aquí.

---

## 1. Qué es el producto (léelo primero)

Buscador de convocatorias de financiamiento (fondos públicos y privados) para
América Latina. El usuario declara **qué busca** (uno o varios ámbitos) y **desde
dónde postula** (país → región → comuna/ciudad), y el producto le muestra los
fondos en un **embudo bottom-up: primero los de su comuna, luego regionales,
nacionales, latinoamericanos y globales**. Ese orden es la identidad del producto
y debe sentirse en la interfaz.

**Posición honesta, y es central:** *no entregamos fondos, les damos mejor
difusión*. Somos el que los rastrea y te los trae. Cuando no tenemos información
fidedigna de un país, **lo decimos** en vez de fingir cobertura. Esa honestidad es
parte de la marca, no una nota al pie.

**Modelo de negocio**: buscar es gratis; el servicio de pago (USD 3/mes) son
**alertas y recordatorios por correo**. El usuario ideal se registra, completa su
perfil, paga, y *no vuelve al sitio*: los fondos le llegan al correo.

**Principio rector de diseño**: *muchas suscripciones, pocas interacciones*. La
interfaz empuja a registrarse y activar alertas, no invita a "vivir" en el sitio.
Nada de dashboards ni densidad. Público no técnico (emprendedores, dirigentes
sociales, gestores culturales, investigadores) y **mobile-first**: la mayoría
llega desde el teléfono por redes sociales.

---

## 2. La marca nueva: el sabueso

El nombre es **el mismo animal en tres idiomas**:

| Idioma | Nombre |
| --- | --- |
| Español | **Sabueso** |
| Portugués (BR) | **Sabujo** |
| Inglés / global | **FundHound** |

**El concepto:** un sabueso rastrea. No caza para sí — busca *para ti*, sin
cansarse, y te trae lo que encontró. Sigue el rastro **desde tu puerta hacia
afuera**: exactamente el embudo local → global. Es leal, incansable y tiene un
olfato que tú no tienes (67 sitios oficiales vigilados en toda LATAM).

**Tono:** cercano y confiable. Un compañero, **no un depredador**: nada de
colmillos, agresividad ni estética de caza. El sabueso trabaja para el usuario.
Ni corporativo frío ni startup infantil.

### ⚠️ La decisión de marca que necesitamos que resuelvas

El sitio es **bilingüe** y el nombre **cambia con el idioma**. ¿Qué pasa con el
logotipo cuando el usuario aprieta "PT"?

- **Opción A** — el logotipo (el sabueso) es fijo y **solo cambia la palabra**:
  Sabueso ⇄ Sabujo. Una marca, dos gentilicios.
- **Opción B** — **FundHound** es la marca única y visible en todo el mundo, y
  Sabueso/Sabujo aparecen solo como apodo local en el texto.
- **Opción C** — la que propongas.

Nuestra intuición es la **A** (el usuario chileno debe leer "Sabueso" y el
brasileño "Sabujo"; FundHound queda para el dominio y lo internacional), pero
queremos tu criterio: **muéstranos las dos versiones del wordmark** y cómo conviven.

---

## 3. Identidad visual actual (punto de partida, no camisa de fuerza)

La marca anterior era otra, así que **puedes proponer una dirección nueva
completa**. Esto es solo de dónde venimos:

Tipografías: **Space Grotesk** (títulos) + **Public Sans** (texto).

| Token | Valor | Uso |
| --- | --- | --- |
| `--papel` | `#F7F5F0` | fondo general (crema cálido) |
| `--tinta` | `#0E2233` | texto/encabezados (azul muy oscuro) |
| `--verde` | `#0B6B43` | enlaces / acento accesible |
| `--linea` | `#E5E1D8` | bordes |

**Escala de cercanía (local → global)** — cinco pasos de un mismo color, del más
saturado (local) al más claro (global): `#0B6B43 · #2E9E68 · #6FC49A · #B7E0CB ·
#E7F3EC`.

**Estados de convocatoria:** abierta `#0B6B43` · próxima `#8A5E10` · cerrada
`#5F6B76` · permanente `#3A6485` · urgente (cierra ≤10 días) `#A8420F`.

Restricciones al evolucionar la paleta:
1. Los **5 pasos de la escala de cercanía** deben distinguirse entre sí.
2. Los **5 estados** deben distinguirse entre sí.
3. Los **3 colores del semáforo** (verde/amarillo/rojo, §5-P10) deben ser
   inequívocos — y **no pueden depender solo del color** (daltonismo): necesitan
   forma o etiqueta.
4. Contraste **AA** mínimo en todo.

---

## 4. Restricción clave: el sitio es bilingüe (es / pt-BR)

Esto no es un detalle, condiciona cada pantalla:

- **Todo texto existe en dos idiomas.** El portugués es **~15-20% más largo** que
  el español: los botones, etiquetas y chips no pueden romperse ni truncarse.
  Ejemplo real: "Crear cuenta gratis" → "Criar conta grátis"; "Comuna / ciudad" →
  "Município / cidade"; "Cobertura activa" → "Cobertura ativa".
- Hay un **toggle ES/PT** en la barra superior (hoy es un enlace de texto plano:
  se agradece una solución mejor).
- Los datos de los fondos van **en su idioma original** (un fondo brasileño se
  llama "Lei Paulo Gustavo" aunque el sitio esté en español). La interfaz se
  traduce; el contenido no.
- **Entrega los mocks en español**, pero enséñanos al menos **una pantalla clave
  en portugués** (sugerimos la landing) para probar que el diseño aguanta.

---

## 5. Inventario de pantallas (11 + 4 correos)

### P1. Landing / Buscador (`/`) — LA página. Doble rol:
- **Visitante anónimo**: hero de conversión con los 3 pasos (1 · Crea tu cuenta →
  2 · Activa tus alertas por USD 3/mes → 3 · Recibe y postula, de lo local a lo
  global), CTA "Crear cuenta gratis", y una franja con **el tamaño real de la
  base** (423 convocatorias · 23 vigentes · 19 países) + una línea de urgencia
  ("⏱ 3 cierran esta semana"). Debajo, el buscador con **solo 3 resultados** y el
  **muro de registro** (C4).
- **Usuario con cuenta**: sin hero; una línea de contexto ("Buscando para:
  Cultura + Emprendimiento · Rancagua, O'Higgins, Chile · Editar"), el buscador y
  los resultados **paginados de 20 en 20** (C9).
- Filtros: texto, perfil (5), país (19), región, comuna (dependientes) y chips de
  estado: Abiertas ahora / Próximas / Todas / Cerradas.
- Resultados **agrupados por nivel** ("Tu comuna", "Tu región", "Tu país",
  "Latinoamérica", "Global") con un riel visual que muestre el degradé de cercanía.
  Un nivel sin fondos **igual aparece**, con un mensaje que empuja al siguiente
  ("Aún no hay fondos exclusivos de Rancagua — los regionales aplican para ti").

### P2. Detalle de fondo (`/fondo/<id>`)
Nombre, institución, descripción, perfil, alcance y ubicación, montos, fechas con
urgencia visible, botón principal **"Postular en el sitio oficial ↗"** (link
externo — nosotros no recibimos postulaciones) y la fuente del dato.

### P3. Registro (`/registro`) — EL formulario de conversión
Email, contraseña, **ámbitos del proyecto (C11: casillas, se puede marcar más de
uno)**, país / región / comuna (dependientes; comuna opcional), checkbox de
alertas. Mínima fricción, máxima claridad de valor.

### P4. Login (`/login`) · P5. Recuperar (`/recuperar`) · P6. Nueva contraseña (`/reset/<token>`)
Paneles simples. P4 debe mostrar también el estado de error ("Correo o contraseña
incorrectos").

### P7. Mi perfil (`/mi-perfil`)
(a) **Checklist del perfil de búsqueda** (C5): 3 ítems — ámbito ✓, localidad ✓,
correo verificado ✓/✗ con acción "Reenviar correo"; (b) **línea de estado premium**
en 3 variantes: *activas hasta DD-MM-AAAA* / *inactivas + CTA "Activar por USD
3/mes"* / *bloqueadas (completa el checklist)*; (c) formulario de edición.

### P8. Premium (`/premium`)
Página de venta simple: qué incluye, **USD 3/mes** + su equivalente local
("≈ 2.850 CLP al mes"), un solo botón (Mercado Pago) y una muestra de cómo llega
el correo. Un solo plan, sin tablas comparativas.
**Importante:** si la cobertura del país del usuario no está completa, aquí
aparece una **nota honesta antes de cobrar** ("La cobertura de Perú está en
desarrollo: recibirás lo que tengamos verificado"). Debe verse honesta, no como
una advertencia de error.

### P9. Baja de alertas (`/alertas/baja/<token>`)
Confirmación simple, sin login, tono amable, opción de volver o reactivar.

### P10. 🆕 Mapa de cobertura (`/cobertura`) — la página del manifiesto
El **semáforo (C8)**: los 19 países **rankeados**, cada uno con su luz según **qué
tan fidedigna es nuestra información** (no cuánto dinero hay):
- 🟢 **Cobertura activa** — fuentes propias verificadas (hoy: Brasil, Chile).
- 🟡 **Cobertura parcial** — fuentes identificadas, sin verificar aún (los otros 17).
- 🔴 **Sin cobertura aún** — no tenemos fuentes de ese país.

Cada fila: rango (#1…#19), país, luz, financiamiento vigente aproximado (US$),
sitios monitoreados. Debajo, dos bloques de manifiesto: **"No entregamos fondos.
Les damos mejor difusión."** y **"Una norma técnica abierta para los datos de
financiamiento"** (seguimos los estándares IATI / 360Giving e invitamos a las
instituciones a publicar en ellos). Cierra con una invitación a las instituciones.
Es nuestra página de credibilidad: que se lea como una declaración, no como una tabla.

### P11. 🆕 Páginas de error (404 / 403 / 429 / 500)
Cuatro variantes de un mismo diseño, con la voz de la marca (aquí el sabueso puede
lucirse: *"Aquí no hay nada"* para el 404, *"Demasiados intentos"* para el 429).
Sin jerga técnica. Botón de vuelta al buscador.

### Estados vacíos (dentro de P1)
- Búsqueda sin resultados → sugerir ampliar filtros.
- País con poca cobertura → **banner de aviso (C10)** + mostrar con naturalidad los
  fondos LATAM/globales que sí aplican.

### Correos (HTML, máx 600px, tablas + estilos inline, sin webfonts)
- **E1 Alerta de fondos nuevos**: lista ordenada local → global, cada ítem con
  etiqueta de nivel, nombre, institución, cierre, monto, link. Si la cobertura del
  país está en desarrollo, lleva la **nota honesta**. Pie con baja en un clic.
- **E2 Recordatorio de cierre**: mismos ítems, urgencia ("Cierra en 3 días").
- **E3 Verificación de correo** · **E4 Recuperar contraseña**: un botón cada uno.

---

## 6. Componentes

| # | Componente | Notas |
| --- | --- | --- |
| **C1** | **Tarjeta de fondo** (el más importante) | Badge de estado con urgencia, **etiqueta de alcance**, nombre (~2 líneas), institución, perfil, ubicación, monto, CTA "Ver detalle" |
| C2 | Selects dependientes país → región → comuna | Se pueblan por JS; en los mocks bastan 3-4 opciones |
| C3 | Chips de estado | 4 opciones, una activa |
| C4 | **Muro de registro** | Corta la lista del anónimo. Incluye un **adelanto** de los fondos ocultos (solo nombre + nivel, con candado) y "🔒 Condiciones, montos y fechas al crear tu cuenta — gratis" |
| C5 | Checklist de perfil | 3 ítems, con acción en el pendiente |
| C6 | Mensajes flash | Éxito / error |
| C7 | Nav + footer | Marca, **toggle ES/PT**, Mi perfil / Cerrar sesión o Entrar / Crear cuenta. Footer con enlace al Mapa de cobertura |
| **C8** | 🆕 **Semáforo** | Luz verde/amarillo/rojo + etiqueta. **No puede depender solo del color** |
| **C9** | 🆕 **Paginación** | "← Más cerca / Más lejos →" + "Página 2 de 20". Avanzar = alejarse en el embudo: que se entienda |
| **C10** | 🆕 **Aviso de cobertura** | Banner honesto cuando el país no está en verde. Informativo, no alarmista |
| **C11** | 🆕 **Casillas multi-ámbito** | 5 ámbitos, se marcan varios. Hoy son checkboxes en grilla: se agradece algo mejor |

**Los 5 ámbitos**: Emprendimiento · ONG / Fundación · Investigación / Académico ·
Empresa privada · **Cultura, patrimonio y artes**.
**Los 19 países**: Argentina, Bolivia, Brasil, Chile, Colombia, Costa Rica, Cuba,
Ecuador, El Salvador, Guatemala, Honduras, México, Nicaragua, Panamá, Paraguay,
Perú, República Dominicana, Uruguay, Venezuela.

---

## 7. Datos REALES para los mocks (no usar lorem ipsum)

Todos existen hoy en la base:

```text
ABIERTA · Regional (São Paulo) · Cultura
ProAC Editais — Fomento à Cultura Paulista
Secretaria de Cultura do Estado de São Paulo · Hasta $250.000 BRL · Cierra 20-07-2026

ABIERTA · Nacional (Chile) · Investigación — urgente
Fondecyt de Iniciación en Investigación
ANID · Hasta $40.000.000 CLP · Cierra en 13 días

ABIERTA · Nacional (Chile) · Emprendimiento — urgente
Capital Semilla Emprende
Sercotec · Hasta $3.500.000 CLP · Cierra en 3 días

ABIERTA · Nacional (Brasil) · Cultura
Lei Paulo Gustavo — Editais de Cultura
Ministério da Cultura (MinC) · Hasta $500.000 BRL · Cierra 30-09-2026

PERMANENTE · Nacional (Brasil) · Cultura
Lei Rouanet — Incentivo à Cultura (PRONAC)
Ministério da Cultura (MinC) · Convocatoria permanente

PERMANENTE · Latinoamérica · Emprendimiento
Fondo de Innovación BID Lab
Banco Interamericano de Desarrollo · Convocatoria permanente

PRÓXIMA · Nacional (Chile) · Cultura
Fondart Nacional — Convocatoria 2027
Ministerio de las Culturas, las Artes y el Patrimonio · Hasta $25.000.000 CLP · Abre 01-09-2026

CERRADA · Nacional (Chile) · ONG
Fondo de Fortalecimiento de Organizaciones de Interés Público
Ministerio Secretaría General de Gobierno · $2.000.000 – $20.000.000 CLP · Cerró 15-07-2026
```

**Cifras reales para las franjas y el semáforo:**
- 423 convocatorias en la base · 23 vigentes · 19 países · **67 sitios monitoreados**
- Semáforo hoy: **2 verdes** (Brasil #1, Chile #2) · **17 amarillos** · 0 rojos
- Brasil: 23 fondos / 18 sitios · Chile: 12 fondos / 17 sitios · Argentina: 1 fondo / 16 sitios

---

## 8. Restricciones de entrega (para que podamos integrarlo)

1. **Formato**: HTML + CSS estáticos, **un archivo por pantalla**
   (`p1-landing.html`, `p1-landing-logueado.html`, `p2-detalle.html`, …,
   `p10-cobertura.html`, `p11-errores.html`, `e1-alerta.html`, …) y **un solo
   `styles.css`** con las variables (tokens) al inicio.
2. **Sin frameworks**: nada de Tailwind/Bootstrap/React. CSS plano con variables;
   JS solo si es imprescindible para demostrar una interacción.
3. **Responsive mobile-first** (360px → desktop). La grilla de tarjetas en 1
   columna en móvil. La tabla del semáforo (P10) debe sobrevivir a 360px.
4. **Sin estilos inline en el HTML** (`style="..."`): el sitio tiene una política
   de seguridad estricta (CSP) que los bloquea. Todo va en `styles.css`.
   *(Los correos E1–E4 son la excepción: ahí los estilos inline son obligatorios.)*
5. Los selects de ubicación pueden llevar 3–4 opciones de muestra.
6. Los formularios **conservan sus campos y nombres** (el backend los espera); se
   puede reordenar y rediseñar libremente su presentación.
7. Correos: tablas + inline styles, máx 600px, sin webfonts.
8. **Accesibilidad AA**: contraste, foco visible, labels en todos los campos, y el
   semáforo legible sin depender del color.
9. Dejar los archivos en la carpeta del proyecto y avisar: el equipo técnico los
   adapta a las plantillas Jinja.
