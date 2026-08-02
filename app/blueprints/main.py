"""Rutas principales: buscador (orden bottom-up), detalle y catálogo de ubicaciones."""
from datetime import date, timedelta
from math import ceil

from flask import Blueprint, Response, current_app, jsonify, render_template, request
from flask_login import current_user
from sqlalchemy import and_, or_, text

from ..constants import UBICACIONES
from ..extensions import db
from ..i18n import t
from ..models import Fondo, Fuente

main_bp = Blueprint("main", __name__)


def _aplicar_filtros(query, pais, perfil, region, comuna, estado, q):
    """Todos los filtros se resuelven en SQL."""
    if pais and pais != "todos":
        # Fondos del país + los postulables desde toda la región o el mundo.
        query = query.filter(Fondo.pais.in_((pais, "LATAM", "Global")))

    if perfil and perfil != "todos":
        query = query.filter(Fondo.perfil == perfil)

    if region and region != "todas":
        query = query.filter(or_(Fondo.region == region, Fondo.region == "Todas"))

    if comuna and comuna != "todas":
        query = query.filter(or_(Fondo.comuna == comuna, Fondo.comuna == "Todas"))

    hoy = date.today()
    if estado == "abiertas":
        query = query.filter(
            or_(Fondo.fecha_cierre.is_(None), Fondo.fecha_cierre >= hoy),
            or_(Fondo.fecha_apertura.is_(None), Fondo.fecha_apertura <= hoy),
        )
    elif estado == "proximas":
        query = query.filter(Fondo.fecha_apertura > hoy)
    elif estado == "cerradas":
        query = query.filter(and_(Fondo.fecha_cierre.isnot(None), Fondo.fecha_cierre < hoy))

    if q:
        patron = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Fondo.nombre.ilike(patron),
                Fondo.institucion.ilike(patron),
                Fondo.descripcion.ilike(patron),
            )
        )
    return query


def _agrupar_embudo(fondos, pais, region, comuna):
    """Agrupa los resultados por nivel del embudo (local → global) para la
    vista de grupos con riel. Los niveles de la localidad buscada aparecen
    aunque estén vacíos, con un mensaje que empuja al nivel siguiente."""
    por_nivel = {n: [] for n in range(5)}
    for f in fondos:
        por_nivel[f.alcance].append(f)

    grupos = []
    if comuna:
        grupos.append({
            "nivel": 0, "titulo": t("g_tu_comuna"), "sub": comuna, "fondos": por_nivel[0],
            "vacio": t("vacio_comuna", lugar=comuna),
        })
    elif por_nivel[0]:
        grupos.append({"nivel": 0, "titulo": t("g_locales"), "sub": "", "fondos": por_nivel[0]})

    if region:
        grupos.append({"nivel": 1, "titulo": t("g_tu_region"), "sub": region, "fondos": por_nivel[1],
                       "vacio": t("vacio_region", lugar=region)})
    elif por_nivel[1]:
        grupos.append({"nivel": 1, "titulo": t("g_regionales"), "sub": "", "fondos": por_nivel[1]})

    if pais:
        grupos.append({"nivel": 2, "titulo": t("g_tu_pais"), "sub": pais, "fondos": por_nivel[2],
                       "vacio": t("vacio_pais", lugar=pais)})
    elif por_nivel[2]:
        grupos.append({"nivel": 2, "titulo": t("g_nacionales"), "sub": "", "fondos": por_nivel[2]})

    if por_nivel[3]:
        sub = t("g_aplican_en", pais=pais) if pais else ""
        grupos.append({"nivel": 3, "titulo": t("g_latam"), "sub": sub, "fondos": por_nivel[3]})
    if por_nivel[4]:
        grupos.append({"nivel": 4, "titulo": t("g_global"), "sub": "", "fondos": por_nivel[4]})

    # No cerrar la lista con avisos de vacío colgantes.
    while grupos and not grupos[-1]["fondos"]:
        grupos.pop()
    return grupos


def _norm(valor):
    """'' o 'todos'/'todas' significan sin filtro."""
    return None if not valor or valor in ("todos", "todas") else valor


@main_bp.route("/")
def index():
    # Por defecto, la localidad de la cuenta: el embudo parte desde ahí.
    if current_user.is_authenticated and "pais" not in request.args:
        pais = current_user.pais_interes
        region = current_user.region_interes
        comuna = current_user.comuna_interes
    else:
        pais = _norm(request.args.get("pais", "Chile"))
        region = _norm(request.args.get("region"))
        comuna = _norm(request.args.get("comuna"))

    perfil = _norm(request.args.get("perfil"))
    estado = request.args.get("estado", "abiertas")  # por defecto, solo lo vigente
    q = request.args.get("q", "")

    # El embudo (local → global) se resuelve EN LA BASE, no en memoria: así da
    # igual que haya 400 fondos o 400.000, solo viaja la página que se muestra.
    query = (_aplicar_filtros(Fondo.query, pais, perfil, region, comuna, estado, q)
             .order_by(*Fondo.orden_bottom_up_sql()))
    total = query.count()  # un COUNT en SQL, sin traer las filas

    bloqueados, teaser = 0, []
    pagina, paginas = 1, 1

    if not current_user.is_authenticated:
        # Visitante sin cuenta: solo un adelanto y el muro (no hay paginación:
        # la Ley IV manda simplicidad, y el objetivo aquí es que se registre).
        limite = current_app.config["FREE_RESULTS_LIMIT"]
        bloqueados = max(0, total - limite)
        resultados = query.limit(limite).all()
        # Adelanto de lo oculto: solo nombre y nivel, el resto tras el registro.
        teaser = [(f.nombre, f.alcance)
                  for f in query.offset(limite).limit(3).all()]
    else:
        por_pagina = current_app.config["RESULTS_PER_PAGE"]
        paginas = max(1, ceil(total / por_pagina))
        pagina = min(max(1, request.args.get("pagina", 1, type=int)), paginas)
        resultados = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    hoy = date.today()
    vivas = Fondo.query.filter(
        or_(Fondo.fecha_cierre.is_(None), Fondo.fecha_cierre >= hoy)
    ).count()
    cierran_semana = Fondo.query.filter(
        Fondo.fecha_cierre.isnot(None),
        Fondo.fecha_cierre >= hoy,
        Fondo.fecha_cierre <= hoy + timedelta(days=7),
    ).count()

    # Aviso honesto de calidad de datos: si el país buscado no tiene cobertura
    # verificada, se avisa al usuario (no prometemos lo que no tenemos).
    from ..services.cobertura import estado_pais
    cobertura_pais = {"pais": pais, "estado": estado_pais(pais)} if pais else None

    return render_template(
        "index.html",
        grupos=_agrupar_embudo(resultados, pais, region, comuna),
        total=total,
        bloqueados=bloqueados,
        teaser=teaser,
        cobertura_pais=cobertura_pais,
        pagina=pagina,
        paginas=paginas,
        stats={"vivas": vivas, "paises": len(UBICACIONES),
               "total_db": Fondo.query.count(), "cierran_semana": cierran_semana,
               "total_sitios": Fuente.query.filter_by(activa=True).count()},
        filtros={"pais": pais or "", "perfil": perfil or "", "region": region or "",
                 "comuna": comuna or "", "estado": estado, "q": q},
    )


@main_bp.route("/fondo/<int:fondo_id>")
def fondo_detalle(fondo_id):
    fondo = db.get_or_404(Fondo, fondo_id)
    return render_template("fondo_detalle.html", fondo=fondo)


@main_bp.route("/cobertura")
def cobertura():
    """Semáforo de disponibilidad de fondos por país (por montos). Explica que
    el producto no entrega fondos: los difunde, siguiendo una norma técnica
    abierta a la que invitamos a sumarse a las instituciones."""
    from ..services.cobertura import resumen_cobertura
    return render_template("cobertura.html", **resumen_cobertura())


@main_bp.route("/health")
def health():
    """Chequeo de salud para monitoreo (UptimeRobot, systemd, balanceadores…).

    Responde 200 solo si la app está viva Y la base de datos contesta. Si algo
    falla devuelve 503, que es lo que un monitor entiende como "está caído".

    A propósito NO dice versiones, rutas ni detalles del error: un endpoint
    público de salud que cuenta de más es un mapa para un atacante.
    """
    try:
        db.session.execute(text("SELECT 1"))
        return {"estado": "ok", "base_de_datos": "ok"}, 200
    except Exception as e:
        current_app.logger.error("Health check falló: %s", e)
        return {"estado": "degradado", "base_de_datos": "sin respuesta"}, 503


@main_bp.route("/robots.txt")
def robots():
    """Le dice a los buscadores qué pueden rastrear. Abrimos todo lo público y
    cerramos lo privado (perfil, admin, pagos, tareas). El sitemap se anuncia
    aquí: es como Google descubre las fichas de los fondos."""
    lineas = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /mi-perfil",
        "Disallow: /admin",
        "Disallow: /premium/",
        "Disallow: /tareas/",
        "Disallow: /webhook/",
        "Disallow: /alertas/baja/",
        "Disallow: /reset/",
        "Disallow: /verificar/",
        "Disallow: /health",
        f"Sitemap: {request.url_root.rstrip('/')}/sitemap.xml",
    ]
    return Response("\n".join(lineas) + "\n", mimetype="text/plain")


@main_bp.route("/sitemap.xml")
def sitemap():
    """Índice para buscadores: la portada, el mapa de cobertura y la ficha de
    CADA fondo vigente. Cada ficha declara sus dos idiomas (hreflang), que es lo
    que nos hace aparecer tanto en búsquedas de Chile como de Brasil."""
    raiz = request.url_root.rstrip("/")
    hoy = date.today()
    fondos = Fondo.query.filter(
        or_(Fondo.fecha_cierre.is_(None), Fondo.fecha_cierre >= hoy)
    ).all()

    urls = [(raiz + "/", "1.0", None), (raiz + "/cobertura", "0.8", None)]
    urls += [(f"{raiz}/fondo/{f.id}", "0.6", f.updated_at.date().isoformat())
             for f in fondos]

    piezas = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
              'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for loc, prioridad, lastmod in urls:
        piezas.append("  <url>")
        piezas.append(f"    <loc>{loc}</loc>")
        if lastmod:
            piezas.append(f"    <lastmod>{lastmod}</lastmod>")
        piezas.append(f'    <xhtml:link rel="alternate" hreflang="es" href="{loc}?lang=es"/>')
        piezas.append(f'    <xhtml:link rel="alternate" hreflang="pt-BR" href="{loc}?lang=pt"/>')
        piezas.append(f"    <priority>{prioridad}</priority>")
        piezas.append("  </url>")
    piezas.append("</urlset>")

    respuesta = Response("\n".join(piezas), mimetype="application/xml")
    respuesta.cache_control.max_age = 3600
    return respuesta


@main_bp.route("/api/ubicaciones")
def ubicaciones():
    """Lista de países. Las regiones/ciudades se piden por país (el catálogo
    completo LATAM pesa ~370 KB; no se envía entero al navegador)."""
    return jsonify({"paises": list(UBICACIONES.keys())})


@main_bp.route("/api/ubicaciones/<pais>")
def ubicaciones_pais(pais):
    """región → [comunas/ciudades] de un país."""
    if pais not in UBICACIONES:
        return jsonify({"error": "país desconocido"}), 404
    respuesta = jsonify(UBICACIONES[pais])
    respuesta.cache_control.max_age = 86400  # el catálogo cambia rara vez
    return respuesta
