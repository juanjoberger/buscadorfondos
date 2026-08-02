# QA — cómo probar Brote Capital

> Todo lo necesario para probar el producto de punta a punta. Las cuentas y datos
> de aquí son **solo para entornos de prueba**.

## 1. Levantar el entorno

```bash
./venv/bin/python -m scripts.migrar      # solo si vienes de una base antigua
./venv/bin/python -m scripts.qa_seed     # cuentas de prueba (idempotente)
./venv/bin/python run.py                 # → http://localhost:5000
```

## 2. Cuentas de prueba

Contraseña común: **`QA-brote-2026`** (el admin tiene la suya).

| Cuenta | Qué representa | ¿Recibe alertas? |
| --- | --- | --- |
| `admin@brote.test` (clave `BroteAdmin2026`) | Admin: premium + verificado + panel `/admin` | ✅ Sí |
| `qa.premium.cl@brote.test` | Premium, Chile (país **verde**), 2 ámbitos, comuna Rancagua | ✅ Sí |
| `qa.premium.br@brote.test` | Premium, Brasil (**verde**) → sitio y correos en **portugués** | ✅ Sí |
| `qa.premium.pe@brote.test` | Premium, Perú (**amarillo**) → debe ver avisos de cobertura parcial | ✅ Sí |
| `qa.gratis@brote.test` | Verificado pero **sin premium** | ❌ No (Ley V) |
| `qa.sinverificar@brote.test` | Premium pero **correo sin verificar** | ❌ No (Ley V) |
| `qa.baja@brote.test` | Premium pero se **dio de baja** | ❌ No |
| `qa.sinperfil@brote.test` | Premium pero **sin ámbito** elegido | ❌ No (Ley V) |

## 3. Verificación automática (antes de cada despliegue)

```bash
./venv/bin/python -m scripts.qa_smoke
```

Comprueba los invariantes que **nunca** deben romperse: el gating de alertas
(Ley V), que ningún usuario sin derecho reciba correo, las rutas públicas en
español y portugués, el gating del panel admin, el muro del visitante anónimo,
los avisos honestos de cobertura (Ley II) y el orden bottom-up (Ley I). Es
repetible: limpia su propio rastro. Sale con código ≠ 0 si algo falla.

## 4. Checklist manual

**Visitante anónimo**
- [ ] La landing muestra el hero, los 3 pasos y la franja con el total de la base.
- [ ] Solo se ven 3 fondos y luego aparece el muro con el adelanto de los ocultos.
- [ ] El toggle **PT** traduce todo el sitio; **ES** lo devuelve.
- [ ] Buscar por texto, perfil, país, región, comuna y los chips de estado.
- [ ] Filtrar por **Perú** muestra el aviso de cobertura parcial; por **Chile**, no.

**Registro y perfil**
- [ ] Crear cuenta marcando **más de un ámbito** (multi-perfil) → se guardan todos.
- [ ] En *Mi perfil*, el checklist muestra los 3 ítems y el estado premium correcto.
- [ ] Cambiar país → los selects de región/ciudad se repueblan solos.

**Premium (pago)**
- [ ] Con `qa.gratis` → `/premium` ofrece el botón de pago; en dev, el modo demo lo activa.
- [ ] `qa.premium.pe` ve la **nota honesta** de cobertura antes de pagar; `qa.premium.cl`, no.
- [ ] El precio muestra USD 3 y el equivalente local (≈ 2.850 CLP).
- [ ] Con `qa.sinverificar` → `/premium` pide completar el perfil (no deja pagar).

**Correos** (en dev se imprimen en la consola del servidor)
```bash
curl -X POST "http://localhost:5000/tareas/enviar-alertas?token=$ALERTS_TOKEN"
```
- [ ] Solo llegan a las 4 cuentas con derecho (3 qa.premium.* + admin).
- [ ] El correo de `qa.premium.br` va en **portugués**.
- [ ] El de `qa.premium.pe` lleva la nota de cobertura en desarrollo.
- [ ] Los fondos van ordenados de lo local a lo global; el pie trae la baja en un clic.

**Mapa de cobertura** (`/cobertura`)
- [ ] Brasil y Chile en **verde**; el resto en amarillo; ranking coherente.
- [ ] Se ven los 67 sitios monitoreados y el manifiesto ("no entregamos fondos").

**Admin** (`/admin`)
- [ ] Con `qa.gratis` da **403**; anónimo redirige a login; con admin, 200.
- [ ] Los totales cuadran y los recolectores muestran su última ejecución.

## 5. Datos

423 fondos (Chile vía `fondos.gob.cl`, Brasil vía el piloto FAPESP + seed) y 67
fuentes. Para recargar convocatorias reales:

```bash
./venv/bin/python -m scripts.ingesta --fuente fapesp.br    # piloto brasileño
./venv/bin/python -m scripts.ingesta --lote 3              # corrida parcelada
```

## 6. Notas

- El **modo demo** de pagos solo existe con `DEBUG=True` y sin `MP_ACCESS_TOKEN`
  (ver `PAGOS.md` para cobrar de verdad).
- Los correos se imprimen en consola mientras no haya credenciales SMTP.
- Antes de dar por buena una tanda de cambios: `scripts.qa_smoke` + la skill `/demo`.
