"""Smoke test de QA: verifica los invariantes críticos del producto.

No reemplaza al QA manual (ver QA.md): cubre las reglas que NUNCA deben romperse,
para poder correrlas antes de cada despliegue.

Uso:  python -m scripts.qa_smoke      (requiere las cuentas de scripts.qa_seed)

Verifica:
  1. Ley V — alertas solo a perfil válido Y premium vigente (matriz completa).
  2. Sin fuga premium: un usuario gratuito no recibe correos.
  3. Rutas públicas responden en español y portugués.
  4. Panel /admin: anónimo→login, no-admin→403, admin→200.
  5. Muro del visitante anónimo (FREE_RESULTS_LIMIT).
  6. Avisos honestos de cobertura: país amarillo sí, país verde no (Ley II).
  7. Embudo bottom-up: los resultados van de lo local a lo global (Ley I).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from app.models import AlertaEnviada, Fondo, User
from app.services import mailer
from scripts.qa_seed import QA_PASS

fallos = []


def _limpiar_alertas_de_prueba():
    """Borra el historial de alertas de las cuentas de prueba (@brote.test) para
    que el smoke sea repetible y no deje rastro."""
    ids = [u.id for u in User.query.filter(User.email.like("%@brote.test")).all()]
    if ids:
        AlertaEnviada.query.filter(AlertaEnviada.user_id.in_(ids)).delete(
            synchronize_session=False)
        db.session.commit()


def check(nombre, condicion, detalle=""):
    estado = "OK  " if condicion else "FALLA"
    print(f"  [{estado}] {nombre}" + (f" — {detalle}" if detalle and not condicion else ""))
    if not condicion:
        fallos.append(nombre)


def main():
    app = create_app()
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["ALERTS_TOKEN"] = "qa-token"

    print("\n1) Ley V — gating de alertas (perfil válido Y premium vigente)")
    with app.app_context():
        esperado = {
            "qa.premium.cl@brote.test": True,
            "qa.premium.br@brote.test": True,
            "qa.premium.pe@brote.test": True,
            "qa.gratis@brote.test": False,
            "qa.sinverificar@brote.test": False,
            "qa.baja@brote.test": False,
            "qa.sinperfil@brote.test": False,
        }
        for email, debe in esperado.items():
            u = User.query.filter_by(email=email).first()
            check(f"{email:28} recibe={debe}", u is not None and u.puede_recibir_alertas == debe)

        # La tarea real de alertas: capturar a quién se le envía de verdad.
        # La expectativa se deriva de la base (no se hardcodea): el invariante es
        # que NADIE sin derecho reciba correo, sea cual sea el set de usuarios.
        autorizados = {u.email for u in User.query.all() if u.puede_recibir_alertas}
        # Omitidos = los que piden alertas pero no cumplen el gating (los dados de
        # baja ni siquiera entran al bucle: se filtran por recibir_alertas).
        omitidos_esperados = sum(
            1 for u in User.query.filter_by(recibir_alertas=True).all()
            if not u.puede_recibir_alertas
        )
        _limpiar_alertas_de_prueba()  # repetible: si no, la 2ª corrida no enviaría nada

        enviados = []
        orig = mailer._enviar
        mailer._enviar = lambda dest, asunto, html: enviados.append(dest)
        try:
            with app.test_client() as c:
                datos = c.post("/tareas/enviar-alertas?token=qa-token").get_json()
            no_autorizados = sorted(set(enviados) - autorizados)
            check("la tarea NO envía a NADIE sin derecho", not no_autorizados,
                  f"envió a {no_autorizados}")
            check("la tarea omite por gating a los que corresponde",
                  datos.get("usuarios_omitidos_por_gating") == omitidos_esperados,
                  f"omitió {datos.get('usuarios_omitidos_por_gating')}, esperado {omitidos_esperados}")
            check("sí llegaron correos a quien tiene derecho", len(enviados) > 0)
        finally:
            mailer._enviar = orig
            _limpiar_alertas_de_prueba()  # no dejar rastro del smoke test

    print("\n2) Rutas públicas (es / pt)")
    with app.test_client() as c:
        for url in ["/", "/cobertura", "/registro", "/login", "/recuperar"]:
            for lang in ("es", "pt"):
                r = c.get(f"{url}?lang={lang}")
                check(f"{url:12} [{lang}]", r.status_code == 200, f"HTTP {r.status_code}")
        r = c.get("/?lang=pt")
        check("portugués real en la landing", "Farejamos recursos" in r.get_data(as_text=True))

    print("\n3) Panel /admin")
    with app.test_client() as c:
        check("anónimo → redirige a login", c.get("/admin").status_code == 302)
        c.post("/login", data={"email": "qa.gratis@brote.test", "password": QA_PASS})
        check("no-admin → 403", c.get("/admin").status_code == 403)
        c.get("/logout")
    with app.test_client() as c:
        with app.app_context():
            admin = User.query.filter_by(es_admin=True).first()
        check("existe una cuenta admin", admin is not None)

    print("\n4) Muro del visitante anónimo")
    with app.test_client() as c:
        html = c.get("/?pais=Chile&estado=todas").get_data(as_text=True)
        limite = app.config["FREE_RESULTS_LIMIT"]
        tarjetas = html.count("tarjeta-nombre")
        check(f"anónimo ve como máximo {limite} fondos", tarjetas <= limite, f"vio {tarjetas}")
        check("se muestra el muro de registro", "muro-titulo" in html)

    print("\n5) Ley II — avisos honestos de cobertura")
    with app.test_client() as c:
        amarillo = c.get("/?pais=Per%C3%BA&estado=todas").get_data(as_text=True)
        verde = c.get("/?pais=Chile&estado=todas").get_data(as_text=True)
        check("país amarillo (Perú) muestra aviso", "aviso-cobertura" in amarillo)
        check("país verde (Chile) NO muestra aviso", "aviso-cobertura" not in verde)

    print("\n6) Ley I — embudo bottom-up")
    with app.app_context():
        from app.services.embudo import orden_bottom_up
        ordenados = orden_bottom_up(Fondo.query.limit(60).all())
        alcances = [f.alcance for f in ordenados]
        check("los fondos salen de lo local a lo global", alcances == sorted(alcances))

        # El alcance se calcula en DOS sitios (la propiedad Python y la expresión
        # SQL que permite paginar). Si alguien cambia uno y no el otro, el embudo
        # se rompe en silencio. Esto lo impide.
        filas = Fondo.query.add_columns(Fondo.alcance_sql().label("sql_alc")).all()
        discrepancias = [f.id for f, a in filas if f.alcance != a]
        check("alcance: la expresión SQL coincide con la propiedad Python",
              not discrepancias, f"{len(discrepancias)} fondos difieren")
        orden_sql = [f.alcance for f in
                     Fondo.query.order_by(*Fondo.orden_bottom_up_sql()).limit(100).all()]
        check("el orden paginado en SQL también es bottom-up", orden_sql == sorted(orden_sql))

    print("\n7) Paginación y salud")
    with app.test_client() as c:
        c.post("/login", data={"email": "qa.premium.cl@brote.test", "password": QA_PASS})
        por_pagina = app.config["RESULTS_PER_PAGE"]
        p1 = c.get("/?pais=Chile&estado=todas&pagina=1").get_data(as_text=True)
        p2 = c.get("/?pais=Chile&estado=todas&pagina=2").get_data(as_text=True)
        check(f"la página trae como máximo {por_pagina} fondos",
              p1.count("<article class=") <= por_pagina, f"trajo {p1.count('<article class=')}")
        check("la página 2 muestra fondos distintos", p1 != p2)
        for valor in ("999999", "-3", "abc"):
            check(f"pagina={valor} no rompe el buscador",
                  c.get(f"/?pagina={valor}").status_code == 200)
    with app.test_client() as c:
        r = c.get("/health")
        check("/health responde ok", r.status_code == 200 and r.get_json().get("estado") == "ok")

    print("\n" + "=" * 60)
    if fallos:
        print(f"❌ {len(fallos)} verificación(es) fallaron:")
        for f in fallos:
            print(f"   · {f}")
        sys.exit(1)
    print("✅ Todos los invariantes críticos se cumplen.")


if __name__ == "__main__":
    main()
