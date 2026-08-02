# contexto.md — Norte del producto e instrucciones para el asistente (LLM)

> **Este documento manda.** Cualquier LLM que trabaje en este repositorio debe leer este
> archivo antes de proponer o ejecutar cambios, y debe **revisar cada operación que
> realiza contra los principios de este documento** (ver sección "Protocolo de revisión").
> Si una tarea solicitada contradice este contexto, el asistente debe señalarlo antes de
> ejecutarla, no después.

---

## 1. Qué es este producto

**Buscador de Fondos** es un SaaS que conecta a personas y organizaciones con
convocatorias de financiamiento (públicas y privadas), partiendo desde su localidad y
escalando hacia lo global.

### El espíritu: embudo bottom-up

El producto es un **embudo de abajo hacia arriba**: al usuario se le muestran primero
los fondos **más locales** (su comuna/localidad), luego los regionales, luego los
nacionales, luego los latinoamericanos y finalmente los globales — siempre filtrados
por dos condiciones:

1. Coinciden con su **perfil de búsqueda** (emprendimiento, ONG, investigación, etc.).
2. Se puede **postular desde la localidad en la que la cuenta está inscrita**.

La localidad es **la que el usuario declara al registrarse**. No usamos GPS,
geolocalización por IP ni ninguna inferencia de ubicación: la cuenta dice dónde está,
y punto.

### Scope geográfico

- El catálogo parte de Chile, pero **ya incluye convocatorias reales de Brasil**
  (`Fondo.pais` con default `"Chile"`; catálogo LATAM de 19 países).
- El objetivo es que **usuarios de toda América Latina puedan inscribirse**: el
  registro, los catálogos de ubicación (`app/constants.py`, `/api/ubicaciones`) y el
  matching de alertas deben diseñarse para múltiples países, no hardcodeados a las
  regiones/comunas chilenas.

### Idioma (es / pt-BR)

El sitio es **bilingüe español / portugués brasileño** (`app/i18n.py`, helper `t()`).
El idioma se **declara** (coherente con la localidad declarada): `?lang=` → sesión →
cuenta inscrita en Brasil (auto-pt) → Accept-Language → español. Los correos salen en
el idioma de la cuenta (`User.idioma`). Solo se traduce la interfaz: los datos de cada
fondo se muestran en su idioma original. Toda cadena visible nueva va por `t()`, nunca
hardcodeada; agrégala a `TEXTOS` con su par (es, pt).

### Perfiles (multi-ámbito)

Un usuario puede optar a **más de un ámbito de fondos** (`User.perfil_interes` guarda
claves de `PERFILES` separadas por coma; `User.perfiles` las devuelve como lista). El
matching de alertas usa `Fondo.perfil.in_(usuario.perfiles)`. La **localidad sigue
siendo una sola** (multi-perfil sí, multi-territorio no). El ámbito `cultura` cubre
**cultura, patrimonio y promoción de las artes**.

### Cadencia de actualización

El catálogo de fondos se actualiza **semanalmente** (por ahora). Toda lógica de
alertas, ingesta y "fondos nuevos" debe asumir esa cadencia; no construir nada que
dependa de datos en tiempo real.

---

## 2. Modelo de negocio

### Capa gratuita

Buscar y ver fondos. Sin fricción: queremos volumen de cuentas.

### Capa de pago — USD 3

El servicio de pago es un **sistema de alertas y recordatorios**. Un usuario accede a
él solo si cumple **dos condiciones**:

1. Tiene un **perfil de búsqueda válidamente generado** (perfil de interés + localidad
   declarada + correo verificado — ver `User.perfil_valido`).
2. Tiene el **pago de USD 3 vigente** (Mercado Pago activa `es_premium` +
   `premium_hasta`; ver `User.premium_activo`).

Las alertas notifican fondos **nuevos** que calzan con el perfil (la tabla
`alertas_enviadas` ya evita repeticiones), y los recordatorios avisan de cierres
próximos de convocatorias relevantes (`Fondo.dias_para_cierre` ya existe como base).

### El negocio real

Las suscripciones de USD 3 no son el fin. El verdadero negocio es que, con un volumen
grande de usuarios, la plataforma pueda **conectar a las instituciones que promueven
los fondos con este público semicautivo**, integrándose con sus respectivas APIs.
Por eso:

- Cada fondo debe conservar trazabilidad de su institución y fuente
  (`Fondo.institucion`, `Fondo.fuente` ya existen — mantenerlos siempre poblados).
- Los datos de perfil y localidad de los usuarios son el activo: deben ser
  estructurados, consistentes y agregables por institución, perfil y territorio.
- Toda decisión de arquitectura debe dejar la puerta abierta a integraciones B2B
  (APIs de instituciones), aunque no se construyan todavía.

---

## 3. Principios de producto (no negociables)

1. **Interfaz simple.** Buscamos **muchas suscripciones y pocas interacciones** dentro
   del SaaS. El usuario ideal se registra, deja su perfil, paga, y recibe correos. No
   agregar dashboards, configuraciones ni features que inviten a "vivir" en el sitio.
2. **Bottom-up siempre.** Cualquier listado o correo ordena de lo local a lo global.
   Nunca al revés.
3. **La localidad es declarada.** Nada de GPS ni inferencia de ubicación.
4. **Elegibilidad desde la localidad.** Un fondo solo se muestra/alerta si se puede
   postular desde donde la cuenta está inscrita.
5. **Semanal, no tiempo real.** No sobre-ingeniería para frescura que el negocio no
   necesita todavía.
6. **LATAM-ready.** Nada nuevo se hardcodea a Chile.

---

## 4. Protocolo de revisión para el LLM

Antes de dar por terminada **cualquier operación** (crear código, modificar modelos,
tocar plantillas, escribir scripts, configurar servicios), el asistente debe
verificar y reportar:

- [ ] **Alineación con el embudo:** ¿el cambio respeta el orden local → global?
- [ ] **Simplicidad:** ¿agrega interacciones o pantallas innecesarias? Si sí, quitar.
- [ ] **Gating premium correcto:** las alertas/recordatorios solo operan para usuarios
      con perfil válido **y** pago vigente. Ningún cambio debe filtrar contenido
      premium a usuarios gratuitos ni enviar alertas a quien no cumple ambas
      condiciones.
- [ ] **Sin geolocalización:** el cambio no introduce GPS, IP-geolocation ni similares.
- [ ] **Compatibilidad LATAM:** ¿funcionaría con un usuario en Perú o Colombia, o
      asume Chile? (regiones/comunas, moneda, formato de montos, idioma).
- [ ] **Trazabilidad B2B:** los fondos nuevos o modificados conservan `institucion` y
      `fuente`.
- [ ] **Seguridad de lo ya ganado:** no reintroducir problemas resueltos en v2
      (secretos en código, rutas de tareas sin token, CSRF, alertas repetidas).
- [ ] **Cadencia semanal:** los crons, scrapers o tareas nuevas asumen actualización
      semanal, no continua.

Si algún punto falla, el asistente debe corregirlo o explicitar la desviación y su
justificación en su respuesta. **La revisión no es opcional.**

---

## 5. Estado actual vs. lo que falta construir

| Pieza | Estado |
| --- | --- |
| Buscador con filtros por país/perfil/región/comuna/estado/texto | ✅ Existe |
| Preview anónimo: toda la oferta de la base a la vista + gancho de conversión | ✅ Franja con total en base / abiertas / países, urgencia "N cierran esta semana", y muro con adelanto (nombre + nivel) de los fondos ocultos |
| Sitio bilingüe español / portugués brasileño | ✅ `app/i18n.py` + `t()`; toggle en el nav; auto-pt para cuentas de Brasil; correos en el idioma de la cuenta |
| Perfil multi-ámbito (un usuario, varios ámbitos de fondos) | ✅ `User.perfiles`; checkboxes en registro/perfil; alertas con `Fondo.perfil.in_(perfiles)`. `cultura` = cultura, patrimonio y artes |
| Perfil de búsqueda válido (perfil + localidad LATAM declarada + correo verificado) | ✅ `User.perfil_valido`; checklist visible en Mi perfil |
| Alertas por correo de fondos nuevos, con baja en un clic | ✅ Gatilladas SOLO para `puede_recibir_alertas` (perfil válido + premium activo) |
| Recordatorios de cierre de convocatorias | ✅ `REMINDER_DAYS` días antes, tipo `recordatorio` en `alertas_enviadas` |
| Sistema de pago USD 3 | ✅ Mercado Pago Checkout Pro (`/premium`, webhook, tabla `pagos`); modo demo en dev |
| Orden bottom-up (local → global) en listados y correos | ✅ `Fondo.alcance` + `services/embudo.py` |
| Registro multi-país LATAM | ✅ 19 países con catálogo completo región → ciudad (22.600+ ciudades, base countries-states-cities ODbL; Chile curado aparte). API lazy por país. **Brasil ya con convocatorias reales** (`data/fondos_brasil_seed.json`) |
| Verificación de correo y recuperación de contraseña | ✅ Tokens firmados con vencimiento (`services/tokens.py`) |
| Export agregado B2B | ✅ `/tareas/export-b2b.csv?token=…` (solo agregados, nunca correos) |
| Ingesta semanal automática de fondos | ✅ Parcelada e inteligente: registro de 20 fuentes por país/institución (tabla `fuentes`), lotes por corrida, boost estacional según historial de aperturas. Scraper real: fondos.gob.cl (~390 convocatorias). Faltan scrapers de las demás fuentes |
| Integraciones B2B con APIs de instituciones | 🔭 Futuro — no construir aún, pero no bloquearlo con decisiones de diseño |

Estrategia para nutrir la base de fondos de forma exhaustiva, legal y barata:
ver [INGESTA_ESTRATEGIA.md](INGESTA_ESTRATEGIA.md) (somos un índice que enlaza a la
fuente oficial; 4 carriles de origen ordenados por defensibilidad y costo; gobernanza
legal por fuente). Estado: diseño aprobado, implementación por fases pendiente.

Las diez leyes del proyecto y su jerarquía están en [DECALOGO.md](DECALOGO.md); la skill
`/coherencia` revisa que los sistemas no se superpongan ni violen esa jerarquía.

Para probar el producto: [QA.md](QA.md) (cuentas de prueba + checklist manual).
Antes de cada despliegue: `python -m scripts.qa_smoke` verifica automáticamente los
invariantes que nunca deben romperse (gating de alertas, avisos de cobertura, embudo).

Para entender el sistema completo: [ARQUITECTURA.md](ARQUITECTURA.md) (recorrido guiado).
Seguridad, protección del código y respuesta a ataques: [SEGURIDAD.md](SEGURIDAD.md).

Skills disponibles: `/revisar-contexto`, `/coherencia`, `/ingesta-fondos`, `/nuevo-pais`,
`/alerta-preview`, `/kpi`, `/demo` (correr SIEMPRE al final de cualquier cambio),
`/seguridad`, `/pre-lanzamiento` (puerta antes de desplegar), `/desplegar`,
`/estado-produccion`, `/respaldo-bd`.
