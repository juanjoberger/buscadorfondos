# Estrategia de ingesta — cómo nutrir la base de fondos de forma exhaustiva, legal y barata

> Documento de diseño. Complementa `contexto.md` (§1 cadencia semanal, §4 trazabilidad
> B2B) y describe **cómo pasar de ~400 fondos de un solo portal a una base LATAM
> exhaustiva** sin exponerse legalmente y sin fundir la VM Free de Oracle.

---

## 1. Diagnóstico (julio 2026)

- **409 fondos** en base, pero **~390 vienen de un único portal** (fondos.gob.cl).
- **24 fuentes registradas**, **1 sola con scraper** implementado. Las otras 23 están
  en la tabla `fuentes` como `tipo="manual"`: reconocidas pero sin recolector.
- El **motor ya es bueno**: `scripts/ingesta.py` reparte la carga (planificador
  parcelado con boost estacional), hace upsert por `link` (no duplica ni re-alerta) y
  valida cada registro. **No hay que rehacerlo: hay que alimentarlo bien.**

El problema no es técnico de fondo, es de **origen de datos**: de dónde sacamos las
convocatorias, con qué derecho, y a qué costo de energía.

---

## 1b. La norma técnica: datos de financiamiento abiertos

Estructuramos cada convocatoria siguiendo los principios de las **normas abiertas
internacionales de datos de financiamiento** —**IATI** (International Aid Transparency
Initiative) y **360Giving**—: *quién financia, qué, cuánto, dónde y hasta cuándo*.
Nuestro modelo `Fondo` ya es esencialmente ese esquema (institución, perfil, montos,
localidad, fechas, enlace).

Por qué importa para este documento:
- **Legitima el índice:** publicar en un estándar abierto y enlazar a la fuente es la
  práctica que la comunidad de transparencia considera correcta.
- **Habilita el carril D:** cuando una institución publica sus convocatorias en el
  estándar, ingerirlas es automático (adaptador de datos abiertos, cero scraping). Por
  eso el mensaje público (página `/cobertura`) invita a las instituciones a sumarse: es
  literalmente el camino más barato y limpio de crecer.
- **Narrativa del semáforo:** un país en rojo no carece de fondos; carece de *difusión
  estandarizada*. El estándar es la meta que pone a todos en verde.

## 2. Principio rector: somos un ÍNDICE, no un espejo

Buscador de Fondos **no aloja el contenido** de las convocatorias: guarda **hechos**
(nombre, institución, fechas, montos, perfil, localidad) y **enlaza a la ficha oficial**
(`Fondo.link`, `Fondo.fuente` — ya obligatorios). Le mandamos **tráfico calificado** a
la institución; no la reemplazamos.

Esta postura —la de un buscador/directorio— es la más defendible que existe y define
todas las reglas de abajo. Todo lo que hagamos debe poder resumirse en: *"indexamos un
dato público y derivamos al usuario a la fuente oficial para que postule ahí"*.

---

## 3. Marco legal (por qué cada método es defendible)

Cuatro fundamentos, aplicables a la mayoría de las jurisdicciones LATAM (leyes de autor
de tradición Berna + leyes de transparencia/datos abiertos):

1. **Los hechos no tienen derecho de autor.** Que exista una convocatoria, su fecha de
   cierre, su monto y la institución que la abre son *hechos*. Lo protegido es la
   *expresión creativa* (la redacción exacta de las bases). → **Ingerimos hechos y
   campos cortos; NUNCA copiamos descripciones largas verbatim.** Si necesitamos texto,
   lo resumimos con palabras propias o guardamos una línea factual (p. ej.
   "Beneficiarios: …"), como ya hace el scraper de fondos.gob.cl.

2. **No hay derecho *sui generis* de base de datos en LATAM.** Ese derecho (copiar la
   estructura+contenido de una base ajena) es propio de la UE; la región no lo tiene.
   Aun así, por higiene: no volcamos una base entera de un tercero — tomamos ítems y
   enlazamos.

3. **Datos abiertos y transparencia.** Casi todos los países tienen portales de datos
   abiertos y leyes de transparencia con **licencias de reutilización explícitas**
   (CC-BY o equivalente). Los datos que vienen de ahí son de uso incuestionable, basta
   citar la fuente.

4. **Atribución + enlace de vuelta.** Siempre mostramos la institución y enlazamos a su
   sitio oficial. No hay competencia desleal ni aprovechamiento parasitario: generamos
   valor para la institución (más postulantes), que es justo el negocio B2B del producto.

**Datos personales (LGPD Brasil, leyes de protección LATAM):** las convocatorias son
información institucional, no personal. **No almacenamos personas de contacto** ni
ningún dato personal de terceros. Riesgo prácticamente nulo.

**La línea roja:** no scrapear contra una prohibición explícita (robots.txt `Disallow` o
Términos que veten la reutilización automatizada), no saltar autenticación/paywalls, no
copiar prosa protegida. Todo lo demás, dentro de los 4 fundamentos, es defendible.

---

## 4. Los cuatro carriles de origen (ordenados por defensibilidad y por costo de energía)

De más limpio y barato a menos. **Siempre preferir el carril más alto disponible para
cada institución.**

### Carril A — Datos abiertos y APIs oficiales  ⭐ (máxima prioridad)
Portales de datos abiertos y APIs con licencia de reutilización. Estructurado (JSON/CSV),
sin parsear HTML, incremental. Es lo más barato en CPU y lo más sólido en derecho.
- Portales nacionales: datos.gob.cl, datos.gob.mx, datos.gov.co, dados.gov.br,
  datos.gob.ar, datosabiertos.gob.pe, etc. → buscar datasets de "convocatorias /
  subsidios / fondos concursables / editais".
- Multilaterales con datos abiertos/API: BID, CAF, Banco Mundial, UE (portal Funding &
  Tenders), PNUD.
- Ciencia/cultura: agencias con API o export (ANID, FAPESP, etc. donde exista).

### Carril B — Feeds y sitemaps públicos (RSS/Atom, sitemap.xml)
Muchos portales publican RSS de "novedades/convocatorias": están **hechos para ser
consumidos por máquinas** (invitación explícita). El `sitemap.xml` con `lastmod` permite
saber qué cambió sin recorrer el sitio. Barato e incremental. Respetar robots.txt.

### Carril C — Scraping respetuoso de HTML público (último recurso)
Solo cuando A y B no existen. Reglas duras (ya parcialmente implementadas en
`scripts/scrapers.py`):
- **Respetar robots.txt** (comprobarlo antes de recolectar; hoy falta — ver §5).
- **User-Agent identificable** con URL de contacto (ya está: `BuscadorDeFondos/1.0`).
- **Pausa entre requests** y backoff ante `429/Retry-After` (pausa ya está).
- **Solo hechos**, nunca prosa larga. Enlace de vuelta siempre.
- **Fetch condicional** (`If-Modified-Since`/`ETag`) para no re-descargar lo igual.

### Carril D — Aportes de las instituciones (consentimiento, costo cero)  ⭐
El producto ya apunta a B2B. Ofrecer a las instituciones un **canal para publicar sus
propias convocatorias** (formulario estructurado o, más adelante, una API de entrada).
Legalmente impecable (nos dan el dato con consentimiento), sin scraping, y siembra la
relación comercial. Es la vía que mejor escala a largo plazo.

---

## 5. Arquitectura técnica (encima de lo que ya existe)

### 5.1 Taxonomía de adaptadores
Hoy `Fuente.tipo` es `scraper | manual`. Proponer sustituirlo/ampliarlo por `metodo`:

| metodo     | carril | adaptador                                  | costo |
|------------|--------|--------------------------------------------|-------|
| `api`      | A      | cliente HTTP JSON por institución          | muy bajo |
| `opendata` | A      | descarga CSV/JSON de portal de datos        | bajo  |
| `rss`      | B      | parser de feed (feedparser)                 | bajo  |
| `sitemap`  | B      | lee sitemap.xml + fetch condicional de ítems| bajo  |
| `scrape`   | C      | parser HTML dedicado (como fondos_gob_cl)   | alto  |
| `aportada` | D      | alta por formulario/API de la institución   | nulo  |

Cada adaptador sigue el **mismo contrato que hoy**: una función que hace `yield` de
dicts normalizados (formato de `data/fondos_seed.json`). El planificador parcelado y el
`upsert` no cambian.

### 5.2 Campos de gobernanza legal en `fuentes` (trazabilidad del PERMISO)
Añadir a la tabla `fuentes` (migración) para poder **probar, por cada fondo, con qué
derecho lo tenemos**:
- `metodo` (ver tabla) — reemplaza a `tipo`.
- `licencia` — p. ej. "CC-BY 4.0", "datos abiertos gob.cl", "hecho público (índice)".
- `terminos_url` — enlace a los Términos/robots.txt revisados.
- `robots_ok` (bool) — se verificó que robots.txt permite la recolección.
- `atribucion` — texto de crédito a mostrar si la licencia lo exige.

Con esto, cada `Fondo` hereda de su `Fuente` la base legal, y una auditoría se responde
en una consulta. Esto es lo que blinda el "no se puede decir que tomamos datos de modo
indebido": **cada registro tiene una razón jurídica registrada.**

### 5.3 Energía y recursos (la VM Free es chica: 1 OCPU / 6 GB)
- **Preferir siempre el carril más alto** → menos parseo, menos CPU.
- **Fetch condicional**: guardar `ETag`/`Last-Modified` por fuente y mandar
  `If-None-Match`/`If-Modified-Since`; un `304 Not Modified` cuesta casi nada.
- **Hash de contenido por fondo**: si el registro no cambió, no reescribir la fila
  (ahorra I/O de BD y evita `updated_at` espurio).
- **El planificador parcelado ya reparte** por semana con boost estacional: mantener el
  cron **diario** con lotes chicos en vez de una corrida pesada. Es lo más eficiente
  energéticamente (picos bajos, sin recargar la VM).
- **robots.txt cacheado** por dominio (24 h) para no pedirlo en cada corrida.

---

## 6. Plan de cobertura exhaustiva (matriz país × sector)

Meta: pasar de "1 país bien, 18 apenas" a **cobertura real en los mercados prioritarios**.

**Fase 1 — profundizar donde ya hay usuarios (Chile + Brasil).**
- Chile: sumar carril A/B de ANID, Corfo, Sercotec, Fondos de Cultura (varios ya
  registrados como `manual`). Muchos tienen datos abiertos o RSS.
- Brasil: gov.br/cultura, Funarte, FINEP, FAPESP — priorizar sus APIs/editais abiertos.

**Fase 2 — cabeceras regionales de alto volumen.** México (CONAHCYT, datos.gob.mx),
Colombia (Minciencias, datos.gov.co), Argentina, Perú.

**Fase 3 — multilaterales (cubren toda LATAM de una).** BID/BID Lab, CAF, PNUD, UE,
Banco Mundial. Un puñado de fuentes de carril A que rinden convocatorias para 19 países.

**Fase 4 — canal de aportes B2B (carril D).** Formulario de alta para instituciones +
export/relación comercial. Escala sin límite de scraping.

**Transversal:** para cada institución, registrar la fuente con su `metodo`, `licencia`
y `robots_ok` ANTES de recolectar. Priorizar por volumen esperado × facilidad de carril.

---

## 7. Qué implementar primero (si se aprueba esta estrategia)

1. ✅ **Migración de `fuentes`**: campos de gobernanza (§5.2) + `metodo`, `config`,
   `http_etag`/`http_last_modified`. Hecho (`scripts/migrar.py`).
2. ✅ **Adaptadores genéricos reutilizables**: `adaptador_rss` y `adaptador_opendata`
   (CSV/JSON) en `scripts/scrapers.py`. Dar de alta una fuente de carril A/B es
   **configuración** (`Fuente.config` JSON), no código. Falta `sitemap` (carril B).
3. ✅ **robots.txt + fetch condicional** (`robots_permite`, `get_condicional`): respeta
   `Disallow` y usa `If-None-Match`/`If-Modified-Since` (304 barato).
4. 🟡 **Cargar el catálogo de fuentes**: hecho el registro de **67 fuentes** de toda
   LATAM y el Caribe (`data/fuentes_seed.json`: agencias de ciencia, fondos de cultura,
   agencias de emprendimiento por país + BID/CAF/PNUD/UE/OEI + Caribe: CDB, CARICOM,
   OECS). Todas como `tipo="manual"` (registradas como cobertura, **sin auto-scrapear**),
   `robots_ok=False`, `licencia="por verificar"`. `bootstrap_fuentes` ahora **sincroniza**
   (upsert) el catálogo. **Falta por fuente:** revisar robots.txt/Términos → marcar
   `robots_ok`, elegir carril (config del adaptador genérico o scraper propio) y activar.
   El semáforo `/cobertura` ya rankea los países y señala cuáles están en el indicador
   por su nº de sitios monitoreados.
5. ⏳ **Canal de aportes (carril D)** como pieza de producto, alineado con el B2B de
   `contexto.md` y con la norma técnica (§1b).

**Piloto brasileño (14-07-2026):** `fapesp_br` en `scripts/scrapers.py` recolecta en
vivo las chamadas de la FAPESP (São Paulo) — fuente verificada, ~37 convocatorias
reales (14 únicas), guardando solo hechos + enlace (Ley III). De paso se corrigió
`robots_permite` para leer robots.txt con nuestro User-Agent (varios portales
responden 403 al UA de urllib, lo que daba un falso "prohibido"). Es la plantilla para
activar las demás fuentes verificadas.

> Ninguna de estas piezas altera el gating premium, el orden bottom-up ni el modelo de
> negocio: solo cambian de dónde y cómo entran los fondos. Revisar cada cambio contra el
> checklist de `contexto.md` §4.
