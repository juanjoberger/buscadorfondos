# Decálogo de Brote Capital — las diez leyes del proyecto

> Set de reglas de acceso rápido que gobiernan los sistemas del software y su
> jerarquía. **El orden importa:** cuando dos leyes entran en conflicto, gana la
> de número menor. La skill `/coherencia` revisa el proyecto contra este decálogo
> y, ante discrepancia, consulta al chamán (el programador). Ninguna ley se cambia
> sola (ver Ley X).

---

**I. La localidad manda y es declarada.**
El usuario dice dónde está; nunca la máquina (sin GPS ni inferencia). Todo listado
y todo correo se ordena desde su comuna hacia el mundo (embudo bottom-up). Es la
identidad del producto: no se negocia.

**II. No prometerás lo que no tienes.**
Solo se ofrece información verificada y oportuna. Si la cobertura de un país no es
fidedigna, se avisa al usuario (buscador, premium y correos). *La honestidad del
dato vence al crecimiento.*

**III. Serás índice, no espejo.**
Guardas hechos y enlazas a la fuente oficial; respetas robots.txt, Términos y
licencias; solo activas una fuente tras verificarla. *La legalidad vence a la
exhaustividad.*

**IV. Simplicidad ante todo.**
Muchas suscripciones, pocas interacciones. Ninguna pantalla que invite a "vivir"
en el sitio. Ante la duda, quitar. *La simplicidad vence a la funcionalidad.*

**V. El muro premium es sagrado.**
Las alertas y recordatorios solo van a quien tiene perfil válido **y** pago
vigente. Nunca filtrar contenido premium a gratuitos ni alertar a quien no cumple
ambas condiciones.

**VI. Un solo pueblo, muchas lenguas.**
Nada se hardcodea a Chile: el producto es de toda América Latina y el Caribe, y
bilingüe (español / portugués). Toda cadena visible pasa por la capa de traducción.

**VII. Cada fondo recuerda su origen.**
Institución y fuente siempre pobladas (trazabilidad B2B). Ninguna decisión de
diseño cierra la puerta a integraciones B2B futuras.

**VIII. La cadencia es semanal y el gasto es medido.**
Nada en tiempo real. Se prefiere siempre la vía más barata en energía:
API > datos abiertos > RSS > sitemap > scraping. Fetch condicional cuando se pueda.

**IX. La norma técnica es el norte.**
Los datos siguen el estándar abierto de financiamiento (IATI / 360Giving). Se
invita a las instituciones a publicar en él para que incorporarlas sea automático.

**X. Ante la duda, se consulta al chamán.**
Ninguna ley se cambia sola. Toda incoherencia entre sistemas se eleva al programador
(el chamán), que decide qué ley cambia y de qué forma. La skill `/coherencia` es el
rito de esta consulta.

---

*Cuando agregues un sistema nuevo, pregúntate: ¿persigue un objetivo que otro
sistema ya cubre (superposición)? ¿Contradice una ley de mayor jerarquía
(violación)? Si algo no calza, no improvises la ley: consulta al chamán.*
