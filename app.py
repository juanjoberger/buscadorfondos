# 1. Capturamos todos los filtros de la URL
    perfil_seleccionado = request.args.get('perfil', 'todos')
    region_seleccionada = request.args.get('region', 'todas')
    comuna_seleccionada = request.args.get('comuna', 'todas') # <-- ¡Nueva línea!
    es_premium = request.args.get('access', 'free') == 'premium'
    
    # 2. Iniciamos con todos los fondos
    resultados = fondos_database

    # 3. Filtramos por Perfil
    if perfil_seleccionado != 'todos':
        resultados = [f for f in resultados if f.get('perfil') == perfil_seleccionado]
        
    # 4. Filtramos por Región
    if region_seleccionada != 'todas':
        resultados = [f for f in resultados if f.get('region') == region_seleccionada or f.get('region') == 'Todas']

    # 5. Filtramos por Comuna <-- ¡Nuevo bloque!
    if comuna_seleccionada != 'todas':
        resultados = [f for f in resultados if f.get('comuna') == comuna_seleccionada or f.get('comuna') == 'Todas']
