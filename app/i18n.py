"""Sitio bilingüe español / portugués brasileño.

Sin dependencias: un diccionario (es, pt) y el helper t(). El idioma se
resuelve así: ?lang= en la URL (queda en sesión) → sesión → cuenta inscrita
en Brasil → cabecera Accept-Language → español. La declaración es del
usuario, coherente con el principio de localidad declarada.
Los datos de los fondos (nombre, descripción) se muestran en su idioma
original — solo se traduce la interfaz.
"""
from flask import has_request_context, request, session
from flask_login import current_user

IDIOMAS = ("es", "pt")

# clave: (español, portugués brasileño)
TEXTOS = {
    # -- marca / base --
    "lema": ("de tu comuna al mundo", "do seu município ao mundo"),
    "nav_buscador": ("Buscador", "Buscador"),
    "nav_perfil": ("Mi perfil", "Meu perfil"),
    "nav_salir": ("Cerrar sesión", "Sair"),
    "nav_entrar": ("Entrar", "Entrar"),
    "nav_crear": ("Crear cuenta", "Criar conta"),
    "contacto": ("Contacto", "Contato"),

    # -- hero / landing --
    "hero_kicker": ("Fondos para América Latina · {n} países", "Recursos para a América Latina · {n} países"),
    "crear_cuenta_gratis": ("Crear cuenta gratis", "Criar conta grátis"),
    "hero_nota": ("Buscar es gratis · alertas USD {p}/mes", "Buscar é grátis · alertas USD {p}/mês"),
    "dato_vivas": ("abiertas o por abrir hoy", "abertos ou por abrir hoje"),

    # -- buscador --
    "buscando_para": ("Buscando para:", "Buscando para:"),
    "editar_en_perfil": ("Editar en Mi perfil", "Editar em Meu perfil"),
    "buscar_placeholder": ("Busca por nombre o tema…", "Busque por nome ou tema…"),
    "buscar_label": ("Buscar por nombre o tema", "Buscar por nome ou tema"),
    "lbl_perfil": ("Perfil", "Perfil"),
    "lbl_pais": ("País", "País"),
    "lbl_region": ("Región", "Região"),
    "lbl_comuna": ("Comuna / ciudad", "Município / cidade"),
    "todos_perfiles": ("Todos los perfiles", "Todos os perfis"),
    "todos_paises": ("Todos los países", "Todos os países"),
    "todas_regiones": ("Todas las regiones", "Todas as regiões"),
    "todas_comunas": ("Todas las comunas", "Todos os municípios"),
    "chip_abiertas": ("Abiertas ahora", "Abertos agora"),
    "chip_proximas": ("Próximas", "Próximos"),
    "chip_todas": ("Todas", "Todos"),
    "chip_cerradas": ("Cerradas", "Fechados"),
    "buscar_fondos": ("Buscar fondos", "Buscar recursos"),
    "filtrar_estado": ("Filtrar por estado", "Filtrar por status"),

    # -- escala / embudo --
    "escala_titulo": ("De tu comuna al mundo", "Do seu município ao mundo"),
    "escala_aria": ("Los resultados se ordenan de lo local a lo global",
                    "Os resultados são ordenados do local ao global"),
    "nv_local": ("Local", "Local"), "nv_regional": ("Regional", "Regional"),
    "nv_nacional": ("Nacional", "Nacional"), "nv_latam": ("LATAM", "LATAM"),
    "nv_global": ("Global", "Global"),
    "fondo_s": ("fondo", "edital"), "fondos_s": ("fondos", "editais"),
    "g_tu_comuna": ("Tu comuna", "Seu município"),
    "g_tu_region": ("Tu región", "Sua região"),
    "g_tu_pais": ("Tu país", "Seu país"),
    "g_latam": ("Latinoamérica", "América Latina"),
    "g_global": ("Global", "Global"),
    "g_locales": ("Fondos locales", "Recursos locais"),
    "g_regionales": ("Fondos regionales", "Recursos regionais"),
    "g_nacionales": ("Fondos nacionales", "Recursos nacionais"),
    "g_aplican_en": ("aplican en {pais}", "valem para {pais}"),
    "vacio_comuna": ("Aún no hay fondos exclusivos de {lugar} — los de los siguientes niveles aplican para ti.",
                     "Ainda não há editais exclusivos de {lugar} — os dos próximos níveis valem para você."),
    "vacio_region": ("Aún no hay fondos exclusivos de {lugar} — los nacionales de abajo aplican para ti.",
                     "Ainda não há editais exclusivos de {lugar} — os nacionais abaixo valem para você."),
    "vacio_pais": ("Aún no hay fondos nacionales de {lugar} en el buscador — seguimos sumando fuentes. Mientras tanto, estos fondos de Latinoamérica aplican para ti:",
                   "Ainda não há editais nacionais de {lugar} no buscador — seguimos somando fontes. Enquanto isso, estes recursos da América Latina valem para você:"),

    # -- tarjeta de fondo --
    "abierta_cierra": ("● Abierta · cierra el {f}", "● Aberto · encerra em {f}"),
    "cierra_en": ("Cierra en {n} día{s}", "Encerra em {n} dia{s}"),
    "abre_el": ("◐ Abre el {f}", "◐ Abre em {f}"),
    "permanente": ("∞ Convocatoria permanente", "∞ Edital permanente"),
    "cerrada_cerro": ("○ Cerrada · cerró el {f}", "○ Fechado · encerrou em {f}"),
    "cerrada": ("○ Cerrada", "○ Fechado"),
    "ver_detalle": ("Ver detalle", "Ver detalhes"),
    "america_latina": ("América Latina", "América Latina"),
    "todo_el_mundo": ("Todo el mundo", "O mundo todo"),

    # -- muro de registro (preview anónimo) --
    "muro_titulo": ("Hay {n} convocatorias más esperándote", "Há mais {n} editais esperando por você"),
    "muro_baja": ("Dinos dónde estás y te las mostramos en orden: <strong>primero tu comuna, después el mundo.</strong>",
                  "Diga onde você está e mostramos tudo em ordem: <strong>primeiro seu município, depois o mundo.</strong>"),
    "muro_teaser_cab": ("Un adelanto de lo que te estás perdiendo", "Uma prévia do que você está perdendo"),
    "muro_teaser_nota": ("🔒 Condiciones, montos y fechas completas al crear tu cuenta — gratis.",
                         "🔒 Condições, valores e prazos completos ao criar sua conta — grátis."),
    "muro_nota": ("Gratis para buscar · ¿Ya tienes cuenta?", "Grátis para buscar · Já tem conta?"),

    # -- aviso premium --
    "aviso_titulo": ("Que los próximos te lleguen al correo", "Que os próximos cheguem no seu e-mail"),
    "aviso_baja": ("Fondos nuevos de tu comuna al mundo + recordatorios de cierre.",
                   "Editais novos do seu município ao mundo + lembretes de encerramento."),
    "activar_alertas_precio": ("Activar alertas · USD {p}/mes", "Ativar alertas · USD {p}/mês"),

    # -- estado vacío --
    "vacio_titulo": ("No encontramos fondos{q} con esos filtros", "Não encontramos editais{q} com esses filtros"),
    "vacio_para": (" para “{q}”", " para “{q}”"),
    "vacio_sug1": ("Quita alguna palabra o usa un término más general.", "Tire alguma palavra ou use um termo mais geral."),
    "vacio_sug2": ("Cambia el filtro a <strong>Todas</strong> para incluir próximas aperturas.",
                   "Mude o filtro para <strong>Todos</strong> para incluir próximas aberturas."),
    "limpiar_filtros": ("Limpiar filtros", "Limpar filtros"),

    # -- detalle --
    "volver": ("← Volver al buscador", "← Voltar ao buscador"),
    "sobre": ("Sobre esta convocatoria", "Sobre este edital"),
    "perfil_calza": ("Perfil que le calza", "Perfil ideal"),
    "antes_postular": ("Antes de postular", "Antes de se inscrever"),
    "antes_postular_p": ("Revisa siempre las bases en el sitio oficial de la institución: ahí están los requisitos completos, los plazos definitivos y el formulario de postulación.",
                         "Sempre confira o regulamento no site oficial da instituição: lá estão os requisitos completos, os prazos definitivos e o formulário de inscrição."),
    "f_alcance": ("Alcance", "Abrangência"),
    "f_ubicacion": ("Ubicación", "Localização"),
    "f_monto": ("Monto", "Valor"),
    "f_apertura": ("Apertura", "Abertura"),
    "f_cierre": ("Cierre", "Encerramento"),
    "segun_bases": ("Según bases", "Conforme o edital"),
    "quedan_dias": ("⏱ Queda{nplural} {n} día{s} para postular", "⏱ Falta{nplural} {n} dia{s} para se inscrever"),
    "postular_oficial": ("Postular en el sitio oficial ↗", "Inscrever-se no site oficial ↗"),
    "fuente_dato": ("Fuente: {f} · dato actualizado el {d}", "Fonte: {f} · dado atualizado em {d}"),

    # -- auth --
    "hola_de_nuevo": ("Hola de nuevo", "Olá de novo"),
    "correo": ("Correo electrónico", "E-mail"),
    "contrasena": ("Contraseña", "Senha"),
    "entrar": ("Entrar", "Entrar"),
    "olvide": ("Olvidé mi contraseña", "Esqueci minha senha"),
    "primera_vez": ("¿Primera vez aquí?", "Primeira vez aqui?"),
    "crea_tu_cuenta": ("Crea tu cuenta gratis", "Crie sua conta grátis"),
    "min8": ("Mínimo 8 caracteres.", "Mínimo de 8 caracteres."),
    "tu_perfil_busqueda": ("Tu perfil de búsqueda", "Seu perfil de busca"),
    "perfil_proyecto": ("Perfil de tu proyecto", "Perfil do seu projeto"),
    "multi_ambito_nota": ("Puedes marcar más de un ámbito — te mostraremos fondos de todos.",
                          "Você pode marcar mais de uma área — mostraremos editais de todas."),
    "pais_postulas": ("País desde donde postulas", "País de onde você se inscreve"),
    "lbl_region_larga": ("Región / provincia / estado", "Estado / região"),
    "lbl_comuna_larga": ("Comuna o ciudad", "Município ou cidade"),
    "opcional": ("(opcional)", "(opcional)"),
    "afina": ("Afina los fondos locales: municipios y organizaciones de tu zona.",
              "Refina os editais locais: prefeituras e organizações da sua região."),
    "quiero_alertas": ("Quiero recibir <strong>alertas de fondos nuevos</strong> por correo (USD {p}/mes — se activan después con Mercado Pago).",
                       "Quero receber <strong>alertas de editais novos</strong> por e-mail (USD {p}/mês — ativadas depois com o Mercado Pago)."),
    "crear_mi_cuenta": ("Crear mi cuenta", "Criar minha conta"),
    "ya_cuenta": ("¿Ya tienes cuenta?", "Já tem conta?"),
    "recupera": ("Recupera tu contraseña", "Recupere sua senha"),
    "recupera_baja": ("Te enviaremos un enlace para crear una nueva. Revisa también tu carpeta de spam.",
                      "Enviaremos um link para criar uma nova. Confira também sua caixa de spam."),
    "enviame_enlace": ("Enviarme el enlace", "Enviar o link"),
    "volver_entrar": ("← Volver a entrar", "← Voltar a entrar"),
    "crea_nueva": ("Crea una nueva contraseña", "Crie uma nova senha"),
    "sera_tu": ("Será tu contraseña desde ahora.", "Será sua senha a partir de agora."),
    "nueva_contrasena": ("Nueva contraseña", "Nova senha"),
    "evita_anterior": ("Mínimo 8 caracteres. Evita usar la anterior.", "Mínimo de 8 caracteres. Evite usar a anterior."),
    "guardar_entrar": ("Guardar y entrar", "Salvar e entrar"),

    # -- mi perfil --
    "mi_perfil": ("Mi perfil", "Meu perfil"),
    "estado_perfil": ("Estado de tu perfil de búsqueda", "Status do seu perfil de busca"),
    "chk_perfil_ok": ("Perfil de proyecto", "Perfil do projeto"),
    "chk_perfil_pend": ("Perfil de proyecto pendiente", "Perfil do projeto pendente"),
    "chk_eligelo": ("Elígelo en el formulario de abajo.", "Escolha no formulário abaixo."),
    "chk_localidad_ok": ("Localidad declarada", "Localidade declarada"),
    "chk_localidad_pend": ("Localidad pendiente", "Localidade pendente"),
    "chk_declarala": ("Declárala en el formulario de abajo.", "Declare no formulário abaixo."),
    "chk_correo_ok": ("Correo verificado", "E-mail verificado"),
    "chk_correo_pend": ("Correo por verificar", "E-mail a verificar"),
    "chk_enlace": ("Te enviamos un enlace — revisa tu bandeja y el spam.", "Enviamos um link — confira sua caixa de entrada e o spam."),
    "reenviar_correo": ("Reenviar correo", "Reenviar e-mail"),
    "alertas_activas": ("Alertas por correo: activas{hasta}", "Alertas por e-mail: ativas{hasta}"),
    "hasta_el": (" hasta el {f}", " até {f}"),
    "alertas_inactivas": ("Alertas por correo: inactivas", "Alertas por e-mail: inativas"),
    "alertas_bloqueadas": ("Alertas por correo: bloqueadas", "Alertas por e-mail: bloqueadas"),
    "completa_checklist": ("Completa el checklist de arriba para poder activarlas.", "Complete o checklist acima para poder ativá-las."),
    "renovar": ("Renovar", "Renovar"),
    "activar_por": ("Activar por USD {p}/mes", "Ativar por USD {p}/mês"),
    "editar_perfil_busqueda": ("Editar mi perfil de búsqueda", "Editar meu perfil de busca"),
    "mantener_alertas": ("Mantener mis <strong>alertas de fondos nuevos</strong> por correo.",
                         "Manter meus <strong>alertas de editais novos</strong> por e-mail."),
    "guardar_cambios": ("Guardar cambios", "Salvar alterações"),

    # -- premium --
    "premium_baja": ("Activa las alertas y no vuelvas a revisar el sitio: lo importante llega a tu correo.",
                     "Ative os alertas e não volte a checar o site: o importante chega no seu e-mail."),
    "mes": ("/ mes", "/ mês"),
    "precio_aprox": ("≈ {monto} {moneda} al mes, según el tipo de cambio del día.",
                     "≈ {monto} {moneda} por mês, conforme o câmbio do dia."),
    "inc1": ("<strong>Fondos nuevos para tu perfil</strong>, ordenados de tu comuna al mundo, apenas los detectamos.",
             "<strong>Editais novos para o seu perfil</strong>, ordenados do seu município ao mundo, assim que os detectamos."),
    "inc2": ("<strong>Recordatorios de cierre</strong> para que ninguna postulación se te pase.",
             "<strong>Lembretes de encerramento</strong> para nenhuma inscrição passar batida."),
    "inc3": ("<strong>Baja en un clic</strong>, desde cualquier correo. Sin permanencia.",
             "<strong>Cancele com um clique</strong>, de qualquer e-mail. Sem fidelidade."),
    "completa_primero": ("Para activar las alertas primero <a href=\"{url}\">completa tu perfil de búsqueda</a>: perfil de proyecto, localidad declarada y correo verificado.",
                         "Para ativar os alertas, primeiro <a href=\"{url}\">complete seu perfil de busca</a>: perfil do projeto, localidade declarada e e-mail verificado."),
    "pagar_mp": ("Pagar con Mercado Pago", "Pagar com Mercado Pago"),
    "demo_activar": ("(Demo) Activar premium 1 mes", "(Demo) Ativar premium 1 mês"),
    "pagar_usd": ("Pagar USD {p}", "Pagar USD {p}"),
    "renueva_mes": ("Se renueva cada mes. Cancelas cuando quieras.", "Renova a cada mês. Cancele quando quiser."),
    "pagos_no": ("Los pagos aún no están habilitados en este servidor.", "Os pagamentos ainda não estão habilitados neste servidor."),
    "asi_llega": ("Así llega a tu correo", "Assim chega no seu e-mail"),

    # -- baja --
    "baja_titulo": ("Listo, tus alertas quedaron desactivadas", "Pronto, seus alertas foram desativados"),
    "baja_baja": ("No enviaremos más correos de fondos nuevos ni recordatorios de cierre a <strong>{email}</strong>. Puedes reactivarlas cuando quieras — tu perfil de búsqueda queda guardado.",
                  "Não enviaremos mais e-mails de editais novos nem lembretes de encerramento para <strong>{email}</strong>. Você pode reativá-los quando quiser — seu perfil de busca fica salvo."),
    "volver_buscador": ("Volver al buscador", "Voltar ao buscador"),
    "fue_error": ("Fue un error — reactivar alertas", "Foi um erro — reativar alertas"),
    "nos_cuentas": ("¿Nos cuentas por qué te vas?", "Conta pra gente por que você está saindo?"),
    "escribenos": ("Escríbenos", "Escreva pra gente"),
    "leemos_todo": ("— leemos todo.", "— lemos tudo."),

    # -- cobertura / semáforo --
    "nav_cobertura": ("Mapa de fondos", "Mapa de recursos"),
    "cob_baja": ("El semáforo muestra qué tan fidedigna y completa es la información que tenemos de cada país. Somos honestos: si no tenemos fuentes verificadas de un país, no prometemos cobertura de ese país.",
                 "O semáforo mostra o quão confiável e completa é a informação que temos de cada país. Somos honestos: se não temos fontes verificadas de um país, não prometemos cobertura desse país."),
    "cob_resumen": ("{verdes} países con cobertura activa · {amarillos} en desarrollo · {rojos} sin cobertura aún",
                    "{verdes} países com cobertura ativa · {amarillos} em desenvolvimento · {rojos} ainda sem cobertura"),
    "cob_sitios_resumen": ("Monitoreamos {sitios} sitios oficiales de convocatorias en toda América Latina y el Caribe.",
                           "Monitoramos {sitios} sites oficiais de editais em toda a América Latina e o Caribe."),
    "cob_col_rank": ("#", "#"),
    "cob_col_sitios": ("Sitios monitoreados", "Sites monitorados"),
    "cob_en_indicador": ("En el indicador", "No indicador"),
    "cob_sin_fuentes": ("Aún sin fuentes", "Ainda sem fontes"),
    # luces = madurez de datos
    # avisos de calidad de datos por país (buscador, premium, correos)
    "aviso_cob_ver_mapa": ("Ver el mapa de cobertura", "Ver o mapa de cobertura"),
    "premium_cob_nota": ("Nota honesta: la cobertura de {pais} está en desarrollo. Recibirás las alertas de lo que tengamos verificado y sumaremos más apenas completemos sus fuentes.",
                         "Nota honesta: a cobertura de {pais} está em desenvolvimento. Você receberá alertas do que tivermos verificado e somaremos mais assim que completarmos suas fontes."),
    "m_cob_nota": ("La cobertura de {pais} aún está en desarrollo: te enviamos lo que tenemos verificado y seguimos sumando fuentes.",
                   "A cobertura de {pais} ainda está em desenvolvimento: enviamos o que temos verificado e seguimos somando fontes."),
    "cob_manifiesto_t": ("No entregamos fondos. Les damos mejor difusión.",
                         "Não entregamos recursos. Damos a eles melhor difusão."),
    "cob_manifiesto": ("Buscador de Fondos no reparte dinero: indexa convocatorias públicas y privadas que ya existen y las acerca a quien puede postular, de su comuna al mundo. Cuando un país aparece en <strong>rojo</strong> no es que le falte financiamiento: es que todavía hay poca información difundida. Esa es justamente nuestra tarea.",
                       "Buscador de Fondos não distribui dinheiro: indexa editais públicos e privados que já existem e os aproxima de quem pode se inscrever, do seu município ao mundo. Quando um país aparece em <strong>vermelho</strong> não é que falte financiamento: é que ainda há pouca informação difundida. Essa é justamente a nossa tarefa."),
    "cob_norma_t": ("Una norma técnica abierta para los datos de financiamiento",
                    "Uma norma técnica aberta para os dados de financiamento"),
    "cob_norma": ("Estructuramos cada convocatoria siguiendo los principios de las normas abiertas internacionales de datos de financiamiento (IATI · 360Giving): quién financia, qué, cuánto, dónde y hasta cuándo. Publicamos estos datos de forma abierta y con enlace a la fuente oficial. <strong>Esperamos que pronto las instituciones publiquen sus convocatorias en este estándar</strong>: cuando lo hagan, sumarlas a este mapa será automático y cada país podrá ponerse en verde.",
                  "Estruturamos cada edital seguindo os princípios das normas abertas internacionais de dados de financiamento (IATI · 360Giving): quem financia, o quê, quanto, onde e até quando. Publicamos esses dados de forma aberta e com link para a fonte oficial. <strong>Esperamos que em breve as instituições publiquem seus editais nesse padrão</strong>: quando o fizerem, somá-los a este mapa será automático e cada país poderá ficar verde."),
    "cob_col_pais": ("País", "País"),
    "cob_col_monto": ("Financiamiento vigente (aprox. USD)", "Financiamento vigente (aprox. USD)"),
    "cob_col_fondos": ("Convocatorias", "Editais"),
    "cob_nota_montos": ("Montos aproximados, convertidos a USD como referencia para comparar países. El detalle real está en cada convocatoria.",
                        "Valores aproximados, convertidos para USD como referência para comparar países. O detalhe real está em cada edital."),
    "cob_cta": ("Ver las convocatorias", "Ver os editais"),

    # -- paginación --
    "pag_actual": ("Página {n} de {total}", "Página {n} de {total}"),
    "pag_nota": ("Los resultados avanzan de lo más local a lo más global.",
                 "Os resultados avançam do mais local ao mais global."),

    # -- SEO (lo que Google y las redes muestran del sitio) --
    "meta_desc_cobertura": ("Mapa de cobertura: cuánto financiamiento hay indexado y vigente en cada país de América Latina y el Caribe, y qué tan fidedigna es su información.",
                            "Mapa de cobertura: quanto financiamento há indexado e vigente em cada país da América Latina e do Caribe, e o quão confiável é a informação."),

    # -- páginas de error --

    # -- flashes --
    "fl_correo_invalido": ("Ingresa un correo válido.", "Informe um e-mail válido."),
    "fl_pass_corta": ("La contraseña debe tener al menos 8 caracteres.", "A senha deve ter pelo menos 8 caracteres."),
    "fl_elige_perfil": ("Marca al menos un ámbito para tu proyecto.", "Marque pelo menos uma área para o seu projeto."),
    "fl_elige_pais": ("Selecciona tu país.", "Selecione seu país."),
    "fl_ya_registrado": ("Este correo ya está registrado. Inicia sesión.", "Este e-mail já está cadastrado. Faça login."),
    "fl_no_verificacion": ("No pudimos enviar el correo de verificación; reenvíalo desde tu perfil.",
                           "Não conseguimos enviar o e-mail de verificação; reenvie a partir do seu perfil."),
    "fl_cuenta_creada": ("Cuenta creada. Te enviamos un correo para confirmar tu dirección.",
                         "Conta criada. Enviamos um e-mail para confirmar seu endereço."),
    "fl_enlace_invalido": ("El enlace de verificación no es válido o venció. Pide uno nuevo desde tu perfil.",
                           "O link de verificação não é válido ou expirou. Peça um novo no seu perfil."),
    "fl_correo_verificado": ("Correo verificado. Tu perfil de búsqueda quedó completo.",
                             "E-mail verificado. Seu perfil de busca está completo."),
    "fl_ya_verificado": ("Tu correo ya está verificado.", "Seu e-mail já está verificado."),
    "fl_verificacion_enviada": ("Te enviamos un nuevo correo de verificación.", "Enviamos um novo e-mail de verificação."),
    "fl_credenciales": ("Correo o contraseña incorrectos. Inténtalo de nuevo.", "E-mail ou senha incorretos. Tente de novo."),
    "fl_prefs_ok": ("Tus preferencias fueron actualizadas.", "Suas preferências foram atualizadas."),
    "fl_reset_enviado": ("Si el correo existe, te enviamos un enlace para crear una nueva contraseña.",
                         "Se o e-mail existir, enviamos um link para criar uma nova senha."),
    "fl_reset_invalido": ("El enlace no es válido o venció. Pide uno nuevo.", "O link não é válido ou expirou. Peça um novo."),
    "fl_pass_cambiada": ("Contraseña actualizada. Ya puedes entrar.", "Senha atualizada. Você já pode entrar."),
    "fl_completa_perfil": ("Antes de activar las alertas completa tu perfil: qué buscas, desde dónde postulas y tu correo verificado.",
                           "Antes de ativar os alertas, complete seu perfil: o que você busca, de onde se inscreve e seu e-mail verificado."),
    "fl_pago_error": ("No pudimos iniciar el pago. Intenta de nuevo en unos minutos.",
                      "Não conseguimos iniciar o pagamento. Tente de novo em alguns minutos."),
    "fl_demo_premium": ("(Demo) Premium activado por 1 mes.", "(Demo) Premium ativado por 1 mês."),
    "fl_pagos_no_config": ("Los pagos no están configurados todavía (falta MP_ACCESS_TOKEN).",
                           "Os pagamentos ainda não estão configurados (falta MP_ACCESS_TOKEN)."),
    "fl_pago_ok": ("¡Pago recibido! Tus alertas quedarán activas en cuanto Mercado Pago lo confirme (segundos).",
                   "Pagamento recebido! Seus alertas ficarão ativos assim que o Mercado Pago confirmar (segundos)."),
    "fl_pago_pendiente": ("Tu pago quedó pendiente. Activaremos las alertas cuando se confirme.",
                          "Seu pagamento ficou pendente. Ativaremos os alertas quando for confirmado."),
    "fl_pago_fallo": ("El pago no se completó. Puedes intentarlo de nuevo.", "O pagamento não foi concluído. Você pode tentar de novo."),

    # -- correos --
    "m_alerta_kicker": ("Alerta de fondos nuevos", "Alerta de editais novos"),
    "m_alerta_titulo": ("Hay {n} fondo{s} nuevo{s} para tu perfil", "Há {n} edita{ii} novo{s} para o seu perfil"),
    "m_alerta_baja": ("En orden, de lo más cercano a lo más global:", "Em ordem, do mais próximo ao mais global:"),
    "m_alerta_asunto": ("{n} fondo{s} nuevo{s} para tu perfil — Sabueso", "{n} edita{ii} novo{s} para o seu perfil — Sabueso"),
    "m_rec_kicker": ("Recordatorio de cierre", "Lembrete de encerramento"),
    "m_rec_titulo": ("{n} fondo{s} de tu perfil cierra{n2} pronto", "{n} edita{ii} do seu perfil fecha{n2} em breve"),
    "m_rec_baja": ("Si vas a postular, este es el momento de preparar los papeles.",
                   "Se você vai se inscrever, é hora de preparar os documentos."),
    "m_rec_asunto": ("Fondos de tu perfil cierran pronto — Sabueso", "Editais do seu perfil fecham em breve — Sabueso"),
    "m_cierra_en": ("CIERRA EN {n} DÍA{S}", "FECHA EM {n} DIA{S}"),
    "m_abierta_cierra": ("Abierta · cierra el {f}", "Aberto · encerra em {f}"),
    "m_permanente": ("Convocatoria permanente", "Edital permanente"),
    "m_ver_fondo": ("Ver fondo →", "Ver edital →"),
    "m_postular_ahora": ("Postular ahora →", "Inscrever-se agora →"),
    "m_ver_todos": ("Ver todos mis fondos", "Ver todos os meus editais"),
    "m_pie_baja": ("Recibes este correo porque activaste las alertas de Sabueso.",
                   "Você recebe este e-mail porque ativou os alertas do Sabueso."),
    "m_baja_clic": ("Darme de baja en un clic", "Cancelar com um clique"),
    "m_editar_perfil": ("Editar mi perfil", "Editar meu perfil"),
    "m_verif_titulo": ("Confirma tu correo", "Confirme seu e-mail"),
    "m_verif_baja": ("Un clic y tu cuenta queda lista para recibir fondos de tu comuna al mundo.",
                     "Um clique e sua conta fica pronta para receber editais do seu município ao mundo."),
    "m_verif_boton": ("Confirmar mi correo", "Confirmar meu e-mail"),
    "m_verif_asunto": ("Confirma tu correo — Sabueso", "Confirme seu e-mail — Sabueso"),
    "m_verif_pie": ("Si no creaste una cuenta en Sabueso, ignora este correo.",
                    "Se você não criou uma conta no Sabueso, ignore este e-mail."),
    "m_reset_titulo": ("Crea una nueva contraseña", "Crie uma nova senha"),
    "m_reset_baja": ("Pediste restablecer tu contraseña. El enlace vence en 1 hora.",
                     "Você pediu para redefinir sua senha. O link expira em 1 hora."),
    "m_reset_boton": ("Crear nueva contraseña", "Criar nova senha"),
    "m_reset_asunto": ("Recupera tu contraseña — Sabueso", "Recupere sua senha — Sabueso"),
    "m_reset_pie": ("Si no lo pediste, ignora este correo: tu contraseña no cambió.",
                    "Se você não pediu, ignore este e-mail: sua senha não mudou."),
    "m_no_boton": ("Si el botón no funciona, copia este enlace en tu navegador:",
                   "Se o botão não funcionar, copie este link no seu navegador:"),
    "m_pie_lema": ("Sabueso — olfateamos fondos por ti", "Sabujo — farejamos recursos por você"),

    # =================================================================
    #  MARCA SABUESO · SABUJO · FUNDHOUND (rediseño, ago-2026).
    #  Este bloque va AL FINAL a propósito: en un dict de Python la última
    #  clave gana, así que aquí redefinimos la voz de marca y agregamos lo
    #  nuevo sin tener que editar cada clave antigua una por una.
    # =================================================================
    "marca_nombre": ("Sabueso", "Sabujo"),
    "titulo_sitio": ("Sabueso — Olfateamos fondos por ti, de tu comuna al mundo",
                     "Sabujo — Farejamos recursos por você, do seu município ao mundo"),
    "atribucion": ("un emprendimiento de Nuevo Sur Solutions", "um empreendimento da Nuevo Sur Solutions"),
    "nav_inicio": ("inicio", "início"),
    "idioma_cuenta": ("Idioma y cuenta", "Idioma e conta"),
    "meta_desc": ("Olfateamos fondos y convocatorias de financiamiento para tu proyecto en Chile, Brasil y América Latina: cultura, emprendimiento, investigación y ONG. De tu comuna al mundo. Buscar es gratis.",
                  "Farejamos editais e recursos de financiamento para o seu projeto no Brasil, Chile e América Latina: cultura, empreendedorismo, pesquisa e ONGs. Do seu município ao mundo. Buscar é grátis."),

    # -- hero --
    "hero_h1": ("Olfateamos fondos por ti.", "Farejamos recursos por você."),
    "hero_baja": ("No entregamos fondos: los rastreamos en {sitios} sitios oficiales de América Latina y te los traemos al correo, en orden — primero tu comuna, después el mundo.",
                  "Não entregamos recursos: nós os farejamos em {sitios} sites oficiais da América Latina e trazemos para o seu e-mail, em ordem — primeiro seu município, depois o mundo."),
    "hero_nota_corta": ("Buscar es gratis · sin tarjeta", "Buscar é grátis · sem cartão"),
    "paso1": ("<strong>Crea tu cuenta gratis</strong> y dinos qué buscas.", "<strong>Crie sua conta grátis</strong> e diga o que busca."),
    "paso2": ("<strong>Activa tus alertas</strong> por USD {p}/mes.", "<strong>Ative seus alertas</strong> por USD {p}/mês."),
    "paso3": ("<strong>Recibe y postula</strong>, sin volver al sitio.", "<strong>Receba e se inscreva</strong>, sem voltar ao site."),
    "dato_total": ("convocatorias", "editais"),
    "dato_vivas_corto": ("vigentes hoy", "vigentes hoje"),
    "dato_paises": ("países", "países"),
    "dato_semana": ("⏱ {n} convocatorias cierran esta semana", "⏱ {n} editais fecham esta semana"),

    # -- buscador --
    "lbl_ambito": ("Ámbito", "Área"),
    "todos_ambitos": ("Todos los ámbitos", "Todas as áreas"),

    # -- resultados / tarjeta --
    "cerca_de_ti": ("Cerca de ti", "Perto de você"),
    "orden_local_global": ("orden: local → global", "ordem: local → global"),
    "cierra_el": ("Cierra el {f}", "Encerra em {f}"),
    "abre_el_corto": ("Abre {f}", "Abre {f}"),
    "permanente_corto": ("Permanente", "Permanente"),
    "cerro_el": ("Cerró {f}", "Encerrou {f}"),

    # -- muro (adelanto) --
    "muro_titulo_sabueso": ("El sabueso encontró {n} fondos más", "O sabujo encontrou mais {n} editais"),
    "adelanto_mas": ("… y {n} más para tu perfil", "… e mais {n} para o seu perfil"),
    "muro_candado": ("🔒 Condiciones, montos y fechas al crear tu cuenta — gratis",
                     "🔒 Condições, valores e prazos ao criar sua conta — grátis"),

    # -- paginación --
    "pag_anterior": ("← Más cerca", "← Mais perto"),
    "pag_anterior_sub": ("niveles más locales", "níveis mais locais"),
    "pag_tope_local": ("ya estás en lo más local", "você já está no mais local"),
    "pag_siguiente": ("Más lejos →", "Mais longe →"),
    "pag_siguiente_sub": ("LATAM y globales", "LATAM e globais"),

    # -- estado vacío --
    "vacio_titulo_sabueso": ('El sabueso no encontró nada con "{q}"', 'O sabujo não encontrou nada com "{q}"'),
    "vacio_titulo_generico": ("El sabueso no encontró nada con esos filtros", "O sabujo não encontrou nada com esses filtros"),
    "vacio_baja": ("El rastro está frío por ahora. Prueba ampliando la búsqueda — los fondos cambian todas las semanas.",
                   "O rastro está frio por enquanto. Tente ampliar a busca — os editais mudam toda semana."),
    "vacio_sug3": ("Prueba con <strong>Todos los ámbitos</strong> o sin comuna.",
                   "Tente <strong>Todas as áreas</strong> ou sem município."),

    # -- avisos de cobertura (título + cuerpo) --
    "aviso_cob_amarillo_t": ("La cobertura de {pais} está en desarrollo", "A cobertura de {pais} está em desenvolvimento"),
    "aviso_cob_amarillo": ("Tenemos fuentes identificadas pero aún sin verificar. Te mostramos lo comprobado y los fondos de LATAM que sí aplican.",
                           "Temos fontes identificadas mas ainda não verificadas. Mostramos o comprovado e os editais da LATAM que se aplicam."),
    "aviso_cob_rojo_t": ("Aún no rastreamos {pais}", "Ainda não farejamos {pais}"),
    "aviso_cob_rojo": ("Todavía no tenemos fuentes verificadas de este país. Te mostramos los fondos de LATAM que aplican mientras las sumamos.",
                       "Ainda não temos fontes verificadas deste país. Mostramos os editais da LATAM que se aplicam enquanto as somamos."),

    # -- detalle --
    "ambito_calza": ("Ámbito que le calza", "Área ideal"),
    "fuente_sabueso": ("La postulación es en el sitio de la institución — nosotros solo te trajimos el dato. Fuente: {f} · verificado el {d}",
                       "A inscrição é no site da instituição — nós só trouxemos o dado. Fonte: {f} · verificado em {d}"),

    # -- auth --
    "suelta_sabueso": ("Suelta al sabueso", "Solte o sabujo"),
    "registro_baja": ("Dinos qué buscas y desde dónde postulas: ordenamos los fondos <strong>de tu comuna al mundo.</strong>",
                      "Diga o que busca e de onde se inscreve: ordenamos os editais <strong>do seu município ao mundo.</strong>"),
    "que_rastro": ("¿Qué rastro seguimos?", "Que rastro seguimos?"),
    "elige_pais": ("Elige tu país…", "Escolha seu país…"),
    "afina_rastro": ("Afina el rastro local: municipios y organizaciones de tu zona.",
                     "Refina o rastro local: prefeituras e organizações da sua região."),
    "entra_para": ("Entra para ver tu rastro de fondos, de tu comuna al mundo.",
                   "Entre para ver seu rastro de editais, do seu município ao mundo."),

    # -- perfil --
    "chk_ambitos_ok": ("Ámbitos del proyecto", "Áreas do projeto"),

    # -- premium --
    "premium_titulo": ("Que el sabueso trabaje por ti", "Que o sabujo trabalhe por você"),

    # -- baja --
    "baja_baja_sabueso": ("El sabueso descansa: no te enviaremos más correos de fondos nuevos ni recordatorios a <strong>{email}</strong>. Puedes reactivarlas cuando quieras — tu perfil de búsqueda queda guardado.",
                          "O sabujo descansa: não enviaremos mais e-mails de editais novos nem lembretes para <strong>{email}</strong>. Você pode reativá-los quando quiser — seu perfil de busca fica salvo."),

    # -- errores --
    "err_codigo": ("Error {n}", "Erro {n}"),
    "ir_buscador": ("Ir al buscador", "Ir ao buscador"),
    "err_404_t": ("Aquí no hay rastro", "Aqui não há rastro"),
    "err_404": ("La página que buscas no existe o cambió de dirección. Volvamos a terreno conocido.",
                "A página que você procura não existe ou mudou de endereço. Voltemos a terreno conhecido."),
    "err_500_t": ("Algo falló de nuestro lado", "Algo falhou do nosso lado"),
    "err_500": ("No es tu conexión: el problema es nuestro y ya estamos en eso. Prueba de nuevo en unos minutos.",
                "Não é sua conexão: o problema é nosso e já estamos nisso. Tente de novo em alguns minutos."),
    "err_403_t": ("Este rastro no es para ti", "Este rastro não é para você"),
    "err_403": ("No tienes permiso para ver esta página. Si crees que es un error, escríbenos.",
                "Você não tem permissão para ver esta página. Se acha que é um erro, fale com a gente."),
    "err_429_t": ("Demasiados intentos", "Tentativas demais"),
    "err_429": ("Por seguridad pausamos los intentos desde tu conexión por unos minutos. Si olvidaste tu contraseña, usa el enlace de recuperación.",
                "Por segurança pausamos as tentativas da sua conexão por alguns minutos. Se esqueceu sua senha, use o link de recuperação."),

    # -- cobertura (semáforo real) --
    "cob_titulo": ("¿Qué tan bien olfateamos tu país?", "Quão bem farejamos seu país?"),
    "cob_luz_verde": ("Activa", "Ativa"),
    "cob_luz_amarillo": ("En desarrollo", "Em desenvolvimento"),
    "cob_luz_rojo": ("Por abrir", "A abrir"),
    "cob_luz_verde_desc": ("fuentes verificadas, actualización semanal", "fontes verificadas, atualização semanal"),
    "cob_luz_amarillo_desc": ("fuentes identificadas, verificación parcial", "fontes identificadas, verificação parcial"),
    "cob_luz_rojo_desc": ("solo fondos LATAM y globales por ahora", "só editais LATAM e globais por enquanto"),
    "cob_fila_stats": ("{sitios} fuentes · {fondos} convocatorias · {usd} vigente",
                       "{sitios} fontes · {fondos} editais · {usd} vigente"),
    "mani_si_t": ("Lo que sí hacemos", "O que fazemos"),
    "mani_si": ("Revisamos los sitios oficiales, extraemos las convocatorias, las ordenamos por cercanía a tu localidad y te las mandamos al correo. Nada más — y nada menos.",
                "Revisamos os sites oficiais, extraímos os editais, ordenamos por proximidade da sua localidade e enviamos ao seu e-mail. Nada mais — e nada menos."),
    "mani_no_t": ("Lo que no hacemos", "O que não fazemos"),
    "mani_no": ("No entregamos fondos ni somos intermediarios. No revisamos tu postulación, no cobramos comisión y no tenemos relación con las instituciones. Postular siempre es en el sitio oficial.",
                "Não entregamos recursos nem somos intermediários. Não revisamos sua inscrição, não cobramos comissão e não temos relação com as instituições. A inscrição é sempre no site oficial."),
    "mani_datos_t": ("De dónde salen los datos", "De onde vêm os dados"),
    "mani_datos": ("De fuentes públicas: ministerios, gobiernos regionales, municipios, agencias de cooperación y fundaciones. Cada fondo muestra su fuente y la fecha en que lo verificamos.",
                   "De fontes públicas: ministérios, governos regionais, prefeituras, agências de cooperação e fundações. Cada edital mostra sua fonte e a data em que o verificamos."),
    "mani_error_t": ("Si encuentras un error", "Se você achar um erro"),
    "mani_error": ("Escríbenos y lo corregimos. Los sitios oficiales cambian sin avisar; el sabueso es bueno pero no infalible.",
                   "Escreva e corrigimos. Os sites oficiais mudam sem avisar; o sabujo é bom mas não infalível."),
    "cob_invitacion_t": ("¿Falta tu país o una fuente?", "Falta seu país ou uma fonte?"),
    "cob_invitacion": ("Cuéntanos qué convocatorias sigues tú y las sumamos al rastreo.",
                       "Conte quais editais você acompanha e as somamos ao rastreamento."),
    "cob_invitacion_btn": ("Sugerir una fuente", "Sugerir uma fonte"),
}


def idioma_actual():
    if not has_request_context():
        return "es"
    if session.get("lang") in IDIOMAS:
        return session["lang"]
    if current_user.is_authenticated and current_user.pais_interes == "Brasil":
        return "pt"
    acepta = (request.headers.get("Accept-Language") or "").lower()
    return "pt" if acepta.startswith("pt") else "es"


def t(clave, lang=None, **kw):
    par = TEXTOS.get(clave)
    if par is None:
        return clave
    texto = par[1] if (lang or idioma_actual()) == "pt" else par[0]
    return texto.format(**kw) if kw else texto
