# Captación de pago — puesta en marcha (Mercado Pago)

> Cómo pasar del modo demo a **cobrar de verdad** los USD 3/mes del servicio de
> alertas. El software ya está completo (`app/services/pagos.py`,
> `app/blueprints/billing.py`); esto es lo que falta configurar por fuera.

## Cómo funciona (Checkout Pro)

1. El usuario con perfil válido entra a `/premium` y aprieta pagar.
2. `crear_preferencia()` crea una preferencia en Mercado Pago con
   `external_reference = user.id` y devuelve la URL de pago (`init_point`).
3. El usuario paga en Mercado Pago.
4. MP llama a nuestro **webhook** `/webhook/mercadopago` con el id del pago.
5. `confirmar_pago_mp()` **consulta el pago a la API de MP** (nunca confía en el
   body del webhook), y si está `approved` activa premium por `PREMIUM_DIAS` y
   registra el cobro en la tabla `pagos`. Es **idempotente**: un mismo pago no se
   procesa dos veces.

Trazabilidad: cada cobro queda en `pagos` (proveedor, referencia externa, monto,
estado) — insumo del pitch B2B y de la contabilidad.

## Moneda: se cobra en local, no en USD

Una cuenta de Mercado Pago está ligada a **un país** y cobra en su **moneda local**
(CLP para una cuenta chilena, BRL para una brasileña…), no en USD. El precio se
**ancla en USD 3** en la interfaz y se **convierte a la moneda local** al crear la
preferencia, con la tabla `FX_USD` de `app/constants.py`.

- Configura `MP_CURRENCY` con la moneda de tu cuenta MP (default `CLP`).
- La página `/premium` muestra el equivalente local aproximado bajo el precio USD.
- Revisa `FX_USD` de vez en cuando (es una referencia, no cotización en vivo).

## Pasos para activar (una vez)

1. **Crear cuenta de Mercado Pago** del país de cobro y activar **Checkout Pro**.
2. En el panel de MP → *Credenciales de producción*, copiar el **Access Token**.
3. En el `.env` del servidor (ver `DESPLIEGUE.md`):
   ```bash
   MP_ACCESS_TOKEN=APP_USR-...     # token de producción
   MP_CURRENCY=CLP                 # moneda de tu cuenta MP
   PREMIUM_PRICE_USD=3
   SITE_URL=https://tudominio.com  # DEBE ser HTTPS: MP exige webhook HTTPS público
   ```
4. Reiniciar el servicio (`sudo systemctl restart fondos`).
5. En el panel de MP, configurar la **URL de notificaciones/webhook** apuntando a
   `https://tudominio.com/webhook/mercadopago` (también se envía en cada
   preferencia como `notification_url`, pero conviene registrarla).

## Verificación

- `/premium` muestra el botón "Pagar con Mercado Pago" (no el de demo).
- Pago de prueba con las **tarjetas de test** de MP (usuarios de prueba
  comprador/vendedor del panel): al aprobar, el webhook activa premium y aparece
  una fila en `pagos` con estado `aprobado`.
- Si el webhook no llega: revisar que el puerto 443 esté abierto (ver
  `DESPLIEGUE.md` §2, la trampa del iptables de Oracle) y que `SITE_URL` sea HTTPS.

## Modo demo (solo desarrollo)

Sin `MP_ACCESS_TOKEN` y con `DEBUG=True`, `/premium` ofrece "(Demo) Activar premium
1 mes" que llama a `activar_premium(user, "demo")` sin pasarela. Sirve para probar el
gating de alertas en local. En producción (`DEBUG=False`) el modo demo no existe: sin
token, los pagos quedan desactivados con un aviso claro.

## Posicionamiento (importante para el cobro)

Cobramos por el **servicio de difusión** (alertas y recordatorios), no por entregar
fondos. La página `/cobertura` deja explícito que no repartimos dinero: indexamos y
difundimos. Mantener ese mensaje evita malentendidos con quien paga los USD 3.
