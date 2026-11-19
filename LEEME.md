# Fábrica de juegos

Una carpeta que convierte una **ficha** (`juegos/<id>/juego.json`) en un juego web completo en tres idiomas (español, inglés y chino), lo prueba en un navegador real, lo empaqueta, genera un **sitio propio** con todos los juegos y lo publica —junto con las redes que actives— cuando un humano aprueba el plan exacto. Cada semana revisa su propio estado y deja dicho qué sigue.

**Lo que NO hace, a propósito:** crear cuentas, aceptar términos, ver contraseñas, cobrar, ni publicar nada sin la aprobación de un plan exacto (la «huella», ver «Publicación»). Tampoco garantiza ingresos: publicar no trae jugadores por sí solo, así que el dinero depende de que alguien encuentre el juego. **La guía para el dueño, con los pasos de una sola vez, está en `LEEME-DUENO.md`.**

Esta carpeta también es la memoria del proyecto. Quien la abra (tú o una sesión nueva de Claude) debería poder seguir desde aquí sin recordar ninguna conversación.

## Qué hay hoy

| Juego | Plantilla (género) | Idiomas | Estado |
|---|---|---|---|
| `guerreros-gelatina` v1.4.0 | `gelatina` — simulador de batallas sandbox con 8 «Leyendas» (mitología y folclor), modo Reto con oro que crece por nivel; paquete `audio` | es, en, zh | Probado. Sin publicar. |
| `torre-gelatina` v1.1.0 | `torre` — apilar bloques con timing, un solo toque | es, en, zh | Probado. Sin publicar. Riesgo «alto» de parecerse a un juego de fuera: solo para el sitio propio. |
| `compas-gelatina` v1.0.0 | `compas` — ritmo de tres carriles con música que el motor compone solo (alegre, tensión, calma); nivel 5 de la escalera | es, en, zh | Probado. Todavía fuera del sitio y del plan de publicación: su lanzamiento es una decisión aparte (no antes del 4 de diciembre de 2026, con plan nuevo y tu aprobación). Riesgo «medio». |

Cada juego sale en `salida/<id>/`:

- `index.html` — el juego completo en un solo archivo (sin conexiones externas; las tipografías van incrustadas).
- `<id>-web.zip` — el mismo archivo, listo para subir a itch.io (con `index.html` en la raíz).
- `informe-pruebas.txt` — resultado de las pruebas automáticas.
- `medios/` — capturas de escritorio y celular, `portada.png`, `clip.mp4`, `clip.gif`, `clip-vertical.mp4`.
- `kit/` — `plan-lanzamiento.md` (camino automático y caminos opcionales), `publicaciones.md`, `difusion.md` (canales, reglas verificadas, calendario y banco de respuestas), `registro-creacion.md` (quién decidió qué), `ficha-itch.md` (solo para quien use itch.io) y `metricas.csv`.

## Cómo se usa

```
python3 fabrica.py lista                  # fichas y plantillas disponibles
python3 fabrica.py construir [id|todos]   # genera index.html y el zip
python3 fabrica.py probar [id|todos]      # prueba en Chromium real, capturas, portada y clips
python3 fabrica.py kit [id|todos]         # genera los textos y los planes de lanzamiento y de difusión
python3 fabrica.py revisar [id|todos]     # comprueba que el kit esté completo y coherente (marcas, fuentes, medios) y avisa si las reglas tienen más de 30 días
python3 fabrica.py todo [id|todos]        # construir, probar, kit y revisar, en orden
python3 fabrica.py novedad [id|todos]     # ¿es un juego distinto o una variante? (la compuerta contra la producción en serie)
python3 fabrica.py ideas                  # el cuaderno de ideas frente a los juegos que ya existen
python3 fabrica.py nueva-plantilla NOMBRE --genero G --verbo V --objetivo O   # andamio de un género nuevo
python3 fabrica.py nuevo ID PLANTILLA     # ficha nueva sobre una plantilla existente (lo que falte dice PENDIENTE)
python3 fabrica.py sitio                  # genera dist/sitio (es/en/zh) con los juegos de publicacion/sitio.json
python3 fabrica.py sitio --zip            # además deja dist/sitio.zip para arrastrarlo a Cloudflare Pages (se niega con datos de ejemplo)
python3 fabrica.py perfiles             # avatar, banner y textos (es/en/zh) de las cuentas de bot en difusion/perfiles/ (--texto: sin navegador)
python3 fabrica.py metricas ver [ID]      # lo que hay en metricas/registro.csv por juego y semana
python3 fabrica.py metricas anotar ID METRICA VALOR [--semana esta|pasada|AAAA-MM-DD] [--fuente F] [--nota T]   # agrega un dato al registro
python3 fabrica.py metricas cloudflare [--dias N] [--opcional]   # importa las vistas de Cloudflare Web Analytics (necesita CLOUDFLARE_ANALITICA_TOKEN y CLOUDFLARE_ACCOUNT_ID)
python3 fabrica.py rumbo [--detalle]      # qué construir después según las métricas (con pocos datos, explora); no construye ni publica
python3 fabrica.py publicar ID            # muestra el plan, la huella y las compuertas; NO publica nada
python3 fabrica.py publicar ID --ejecutar --aprobar HUELLA   # publica exactamente lo que esa huella cubre
python3 fabrica.py resolver ACCION salio|no-salio            # anota qué pasó con un envío que quedó en duda
python3 fabrica.py resolver --auto [ACCION]                  # lo intenta aclarar solo leyendo la cuenta pública (sin claves); corre cada día (comprobar.yml)
python3 fabrica.py resolver --verificar                      # solo lectura: comprueba que esa lectura funciona
python3 fabrica.py administrador flujos [--reactivar]        # lista los flujos programados y, si se pide, vuelve a encender los que GitHub apagó por inactividad
python3 fabrica.py configurar bluesky-bot|bluesky-perfil|mastodon-bot [--ejecutar]   # marca la cuenta como bot; bluesky-perfil pone bio, nombre, avatar y banner
python3 fabrica.py ciclo [--probar]       # el latido semanal: reconstruye, revisa y escribe publicacion/PENDIENTE.md (incluye la recomendación de rumbo)
python3 -I -m unittest discover -s pruebas   # 162 pruebas de la fábrica (texto, plan, aprobación, compuertas, ritmo, libro, sitio, páginas de difusión, métricas, importador de Cloudflare, rumbo)
node herramientas/probar.js <id> --rapido # solo las pruebas funcionales (sin portada ni clips)
node herramientas/probar.js <id> --portada # solo vuelve a componer la portada (útil al retocar herramientas/portada.html o portada-heroes.html)
```

Requisitos: Python 3 (con `pillow` para la imagen de las publicaciones), Node, el paquete `playwright` de Node con su Chromium (`npm i playwright` y `npx playwright install chromium`) y `ffmpeg` para los clips. Publicar el sitio usa `npx wrangler` (Cloudflare) dentro del flujo de GitHub. Se probó con Python 3.13, Node 22 y Playwright 1.63.

## Qué prueba la fábrica (en escritorio 1280×800 y en celular 390×844)

- El motor común carga, las tipografías incrustadas cargan sin error y no hay desplazamiento horizontal.
- No hay errores de consola ni de página, y no se hace ninguna conexión externa.
- El escenario propio de cada plantilla (`plantillas/<nombre>/prueba.js`), por ejemplo en Torre: rachas de aciertos perfectos, ensanchado de la torre, cortes, caída, récord guardado, cambio de idioma que se recuerda al recargar, y entradas reales (clic, toque, barra espaciadora). En Guerreros Gelatina: colocación con el ratón o el dedo, batalla completa y sonidos. En Compás: una canción entera tocada con precisión de milisegundos (perfecto, bien, casi, pifia y fallo, multiplicador por racha), clic o toque, flechas, letras y barra espaciadora, cambio de ánimo y ventana de acierto amplia.
- Los medios se generan en la misma pasada: capturas, portada (630×500 px CSS a doble densidad, 1260×1000) y clips.
- La portada tiene dos estilos. El de siempre (`herramientas/portada.html`) usa un recorte de la batalla. El de héroes (`"estilo": "heroes"` en `portada` de juego.json, `herramientas/portada-heroes.html`) dibuja a los personajes grandes con el propio código del juego y los reparte según `portada.reparto`: `[unidad, equipo (0 azul, 1 rojo), x, y, escala, dirección (1 o -1), golpe (0 a 1)]` sobre un lienzo de 630×500. Solo funciona con plantillas que dejen `drawJelly` a mano (la de gelatina). Cambiar la portada cambia la huella del plan de publicación.

Una prueba que falla deja el comando con error y la línea `FALLA` en `informe-pruebas.txt`. Que pase todo prueba que el juego funciona, no que sea divertido: eso lo dicen los jugadores.

## La ficha `juego.json`

Campos principales: `id`, `plantilla`, `version`, `idiomas`, `paquetes`, `fuentes`, `parametros` (los datos propios de la plantilla), `textos` (por idioma, los de dentro del juego), `portada` (colores, lema, `vertical: true` si el juego es vertical), `ia` (qué se hizo con IA: `codigo`, `graficos`, `sonido`, `texto`), `precio` (`donar`, `pagar` o `gratis`, con `sugerido_usd`), `etiquetas`, `clasificacion`, `ficha` (título, descripción corta, controles y descripción larga por idioma), `difusion` (textos listos por idioma), `lanzamiento` (orden y espera entre juegos), `originalidad` (referencias, riesgo para los portales y qué lo distingue: es una evaluación de la casa, no de una plataforma), `creacion` (herramientas y decisiones del dueño y de Claude), `prueba.escenario` y, solo si el juego integra anuncios, `anuncios: true` (el banco de respuestas deja de afirmar que no tiene).

En los textos de `difusion` se usan dos marcas: `{ia}` (la frase que declara el uso de IA, sale sola de `ia`) y `{enlace}` (el enlace real del juego, que se pone al publicar).

**Un juego nuevo con una plantilla existente** = copiar una carpeta de `juegos/`, cambiar `id`, textos y parámetros, y correr `python3 fabrica.py todo <id>`. Por ejemplo, otra «Torre» con otro cielo y otros colores no necesita código.

### Parámetros de `torre`

`colores` (la paleta por la que van pasando los bloques), `cielo` (de 2 a 4 colores, de abajo hacia arriba), `acento`, `ancho_inicial`, `alto_bloque`, `velocidad` (px/s al empezar), `aceleracion` (px/s extra por piso), `vmax`, `tolerancia` (px de margen para que cuente como perfecto), `meta_perfectos` (perfectos seguidos para que la torre empiece a ensancharse), `crecimiento` (px que recupera por acierto). El escenario mide 360 px de ancho.

### Parámetros de `compas`

`animos` (cada ánimo con su `semilla`: cambiar la semilla es otra canción; los ánimos válidos son los del módulo `musica`), `caida_ms` (cuánto tarda una gota en caer hasta la línea), `previo_ms`, `ventanas` (`perfecto`, `bien` y `casi`, en milisegundos a cada lado del instante justo), `ventana_amplia` (multiplicador de esas ventanas cuando el jugador activa la opción), `vueltas` (cuántas veces suena la partitura de ocho compases), `compases_demo` (largo de la canción con `?demo=1`, que usan las pruebas y los clips), `puntos`, `racha_por_nivel` (aciertos seguidos por cada escalón del multiplicador), `multiplicador_max`, `colores` (uno por carril) y `fondo`. Las gotas salen de la melodía que compone el motor, repartida entre los tres carriles según la altura de cada nota.

## Una plantilla nueva (otro género)

Una plantilla es una carpeta en `plantillas/<nombre>/`:

1. `plantilla.html` — empieza con un único bloque `<style>` (sin `<html>`, `<head>` ni `<title>`), sigue con el marcado y termina con uno o más `<script>`. La fábrica inyecta la configuración y el motor común justo antes del primer `<script` que empiece una línea.
2. `prueba.js` — exporta `{ listo: selector, async jugar(page, ctx) }` y, si hace falta, `clip: { ancho, alto }` y `gif: { ultimos, duracion }`. `ctx.modo` es `'prueba'` (con comprobaciones) o `'video'` (a ritmo normal, sin comprobaciones). Si el escenario guarda `medios/portada-fuente.png`, de ahí sale la portada.
3. Una forma de leer el estado desde fuera para que la prueba no dependa de adivinar (en Torre: `window.__torre.estado()`).
4. Opcional: `paquetes/<pack>.js` con extensiones (ver el paquete `audio` de `gelatina`).

El motor común (`motor/ggx.js`, expuesto como `GGX`) ofrece: `store` (localStorage con prefijo del juego y respaldo en memoria), `t`/`setLang`/`onLang` (textos por idioma), `sfx` (efectos sintetizados con WebAudio; sin archivos de audio), botones de silencio, idioma y apoyo, `ads` (adaptador vacío), `rng(semilla)` y la gelatina de la casa (`draw.jelly`). No hay analítica, cookies ni red.

## El motor que crece solo

Cada juego nuevo debe sentirse con más presupuesto que el anterior, y el motor común crece para que eso sea posible sin reescribir nada:

- **Módulos opcionales** (`motor/modulos/`, lista y orden de carga en `motor/modulos.json`): `accesible` (menos movimiento, alto contraste, anuncios para lector de pantalla), `efectos` (partículas, textos flotantes, sacudida, destellos), `musica` (música de fondo compuesta por semilla, con intensidad por capas) y `marca` (la Gelatina como insignia: sello de entrada, «blup» y distintivo; ver `marca/guia.md`). Un juego los declara en `juego.json → motor` y su código los llama con el nombre completo (`GGX.fx…`, `GGX.music…`). El núcleo (`motor/ggx.js`) no cambia: un juego sin `motor` se construye byte por byte como siempre (hay una prueba que lo comprueba).
- **Escalera de calidad** (`motor/escalera.json`): niveles con requisitos medibles (1 Base · 2 Con sonido · 3 Con jugo y accesible · 4 Con música · 5 Con marca). Un módulo solo cuenta si el juego lo declara, su código lo llama y el motor tiene pruebas vigentes de él. `python3 fabrica.py calidad [id|todos]` dice en qué nivel está cada juego y qué le falta.
- **Piso que solo sube** (`motor/piso.json`): el juego nuevo debe llegar al menos un nivel por encima del mejor ya publicado, sin pasar del techo del motor; si no, la compuerta de publicación lo frena con el motivo. Guerreros Gelatina y Torre Gelatina salieron antes de la escalera: no tienen mínimo, pero no pueden bajar. `ciclo` actualiza el piso desde el libro de publicación.
- **Pruebas del motor** (`python3 fabrica.py motor probar`): corren el núcleo y cada módulo en un Chromium real y guardan `motor/informe.json`, atado a la huella del código. Si el motor, un módulo o el guion de pruebas cambian y no se vuelven a correr, el informe deja de estar vigente: las pruebas unitarias fallan y ningún juego que use módulos sale.
- **Cola de mejoras** (`python3 fabrica.py motor`, y sección «Motor» de `PENDIENTE.md`): se calcula sola — pruebas vencidas, juegos por debajo de su nivel, módulos que faltan para el siguiente nivel, pedidos de los juegos (`necesidades_motor`) y, al llegar al techo, la primera idea sin construir de `motor/ideas.json`. Subir una actualización de calidad a un juego ya publicado es también una novedad que anunciar.

Un juego nuevo (`nuevo ID PLANTILLA`) parte con todos los módulos declarados; declararlos no basta para subir de nivel.

## Autonomía y el administrador del motor

Objetivo secundario del motor (después de la calidad): que la fábrica necesite cada vez menos de Max sin cruzar sus límites.

- **Inventario** (`motor/autonomia.json`): cada paso del ciclo de vida, quién lo hace (fábrica, agente o dueño) y, si es del dueño, por qué y de qué clase es: *obligatoria* (la política o la ley lo reservan a Max: cuentas, claves, términos, pagos, aprobar lo que se publica), *reducible* (sigue siendo suya, pero una regla que él autorice permite pedírsela menos veces) o *automatizable* (no necesita su decisión: falta construirlo). Trae también las autorizaciones que Max ya dio, los límites que no cambian y las **propuestas** de reglas, que no valen nada hasta que él las autorice (una prueba lo vigila: una propuesta no puede pasar por autorización).
- **Medición** (`python3 fabrica.py autonomia`, y sección «Autonomía» de `PENDIENTE.md`): tres números, sin mezclarlos en un puntaje inventado. Pasos del ciclo que corren sin Max; toques de Max por mes (estimado del inventario, no medido); y los **días que la fábrica corre sola** con el contenido ya aprobado (este sí se mide, con el calendario). `ciclo` anota una fila por semana en `metricas/autonomia.csv` y avisa si los toques de Max suben o los pasos autónomos bajan.
- **Reglas autorizadas por Max** (`autorizaciones_vigentes`, con su origen; una propuesta solo pasa a «autorizada» si hay su autorización registrada, y una prueba lo vigila). Hoy: la **reserva perenne** y construir el siguiente juego sin preguntar. Reserva perenne: en `contenido/calendario.json`, una publicación con `"perenne": true` (y `"orden"` opcional) no lleva `no_antes_de`, no menciona años ni fechas y se aprueba una sola vez con la huella del lote como cualquier otra; su huella no depende del día. Estados: `en reserva` (aprobada, esperando turno) y `lista` (le toca hoy). Le toca solo si ninguna publicación con fecha está lista, ninguna está en duda y no salió ya hoy otra del calendario; solo una a la vez, la de menor `orden`. `autonomia.dias_aprobados` las cuenta llenando los días sin nada.
- **Cola del motor**: lo *automatizable* y construible entra a la cola (`motor.cola_con_autonomia`), después de lo de calidad. Lo *reducible* nunca entra: depende de que Max autorice una regla.
- **Administrador del motor** (`motor/ADMINISTRADOR.md`): una tarea programada de Claude que corre cada día, sin nadie delante, con una carta de funciones y límites. No es un proceso encendido: lo que le da continuidad es lo escrito en el repositorio, sobre todo la **bitácora** (`motor/bitacora.jsonl`, solo se agrega). `python3 fabrica.py administrador` hace el chequeo (calendario por agotarse, envíos en duda, publicaciones fallidas, pruebas del motor vencidas, ciclo semanal parado, siguiente paso de autonomía) con tres niveles: *avisar* a Max, *resolver* sin él, *info*. `administrador anotar` escribe la bitácora y `administrador guardia` falla si algún commit firmado como `administrador-del-motor` tocó una ruta protegida (aprobaciones, política, libro, sitio, flujos que publican, núcleo del motor, la carta o un juego ya publicado); corre en cada cambio (`ci.yml`) y es red de seguridad, no un candado contra quien pueda escribir en el repositorio.

## La marca

La gelatina es la insignia del Taller, no solo el tema de un juego: `marca/guia.md` explica la idea, los elementos (emblema en cuatro versiones, sello, «blup», distintivo, firma y voz) y las reglas de uso. El emblema se dibuja una sola vez en `herramientas/marca.py` (`python3 herramientas/marca.py` regenera `marca/*.svg`); el módulo `marca` del motor y el ícono del sitio llevan el mismo dibujo, y una prueba lo verifica.

## Monetización

Todo empieza apagado. `monetizacion/politica.json` tiene tres rutas (`portales`, `adsense-sitio`, `donaciones`) en `activa: false`, las reglas de anuncios y los supuestos para hacer cuentas; `monetizacion/ESTRATEGIA.md` explica la estrategia con sus fuentes y lo que no está verificado.

- **Módulo `anuncios`** (`motor/modulos/anuncios.js`, se declara en `motor` como cualquier otro): completa el `GGX.ads` del núcleo (que no se toca) con `intermedio(momento, al_terminar)`, `recompensa(motivo, {ok, no})`, `recompensaDisponible()`, `jugando(bool)`, `alPausar/alReanudar` y `estado()`. Sin proveedor no carga nada y `al_terminar` corre siempre; los anuncios solo van en cortes naturales y después de una interacción; el juego se pausa y se silencia solo mientras suena el anuncio; con un portal no hay temporizadores propios (los prohíben). Proveedores: `adsense`, `crazygames`, `poki` (borrador). Sus 22 pruebas con navegador y simulaciones corren con `python3 fabrica.py motor probar`.
- **Qué se le inyecta a un juego**: nada mientras ninguna ruta esté encendida (el juego sale byte por byte como antes); con `adsense-sitio` encendida y `adsense_publisher` puesto, AdSense en modo de prueba; para un portal, una versión aparte.
- **Ganchos**: el juego llama al módulo en sus cortes naturales (hoy solo Compás, en `otra()`); los juegos ya publicados no se tocan sin versión nueva y aprobación.
- `python3 fabrica.py monetizar [estado|escenarios [N…]|variantes ID [portal]|envio ID]`: qué falta por ruta (y de quién), cuentas con la fórmula sesiones × anuncios por sesión × relleno × eCPM / 1000, la versión de un juego para un portal en `dist/portales/` (hoy solo CrazyGames, cuyo SDK está confirmado; revisa que no traiga anuncios ajenos ni llamadas de salida) y, con `envio`, el paquete para enviarlo a CrazyGames: las tres portadas (1920×1080, 800×1200, 800×800) y los dos videos de vista previa en `salida/ID/medios/crazygames/` y la ficha `salida/ID/kit/ficha-crazygames.md` (necesita Chromium y ffmpeg; solo hay plantilla de envío para Compás).
- El estado entra a `publicacion/PENDIENTE.md` cada semana.

## Idiomas

Cada juego declara `idiomas` (hoy es, en y zh) y trae sus textos por idioma en `juego.json → textos`. El motor común ofrece el selector, recuerda la elección y respeta `?lang=xx`; el sitio genera una página por idioma (`/es/`, `/en/`, `/zh/`, con `hreflang`, el chino como `zh-Hans`). La prueba de cada plantilla revisa los tres idiomas en pantalla. El chino lo escribió Claude: necesita revisión de una persona nativa antes de promocionar en ese idioma.

## Sitio propio

`python3 fabrica.py sitio` escribe `dist/sitio` a partir de `publicacion/sitio.json` (nombre, `url_base`, `proyecto`, `contacto`, juegos que aparecen y textos en `sitio-textos.json`). Es estático y determinista (sin fechas y sin código de analítica propio: si se activa la medición de Cloudflare, la inserta Cloudflare; ver «Métricas y rumbo»; mismo resultado en cada corrida): portada y página de cada juego por idioma, el juego en `/jugar/`, `404.html`, `sitemap.xml`, `robots.txt`, `_headers`, datos estructurados (`VideoGame`), clave de IndexNow, y `ads.txt` solo si pones `adsense_publisher`. Incluye una página de privacidad que es una plantilla: debe revisarla el dueño.

También genera dos páginas por idioma para la difusión: **Novedades** (`/es/novedades/`, `/en/novedades/`, `/zh/novedades/`), con las notas de cada versión de cada juego, y **Prensa** (`/es/prensa/`…), con los datos rápidos (plataforma, precio, idiomas, versión, cómo se hizo —con la declaración de que se usó IA—), portada y capturas en grande y el contacto, para quien quiera reseñar o mostrar los juegos. Ambas salen en el pie y en la portada, con `hreflang` y en el `sitemap.xml`. Las notas de versión se escriben en `juego.json → novedades`: una lista de `{"version", "es", "en", "zh"}`; si falta un idioma o la versión, el sitio se niega a generarse. Los parches se anuncian aquí y no en redes (ver «Parches» abajo).

## Calendario de contenido

Publicaciones propias que no son lanzamientos (por ejemplo «Conoce a las Leyendas», una tarjeta por personaje) viven en `contenido/calendario.json`: juego, canal (hoy solo Bluesky), `no_antes_de`, `texto` con `{enlace}` y `{ia}`, `imagen` (dentro de `contenido/`) y `alt`.

```
python3 fabrica.py calendario                              # estado de cada publicación y huella del lote pendiente
python3 fabrica.py calendario --aprobar HUELLA_DEL_LOTE    # el dueño aprueba el lote: anota la huella de cada publicación en contenido/aprobaciones.json
python3 fabrica.py calendario --ejecutar                   # publica lo que cumple las tres condiciones (lo corre a diario .github/workflows/calendario.yml)
node herramientas/tarjetas.js <id-del-juego> [idioma]      # regenera las tarjetas de Leyenda (contenido/imagenes/), con el código del propio juego
```

Sale solo lo que está aprobado **con su huella actual** (texto ya resuelto, imagen, texto alternativo y fecha), ya llegó su fecha y no pasaron más de 3 días. Si algo cambia después de aprobar, esa publicación vuelve a pedir aprobación. Pasa por las barreras de siempre: compuertas, ritmo del canal, libro de registro, «incierto» sin reintentos. Una publicación por canal y corrida. La tarea diaria nunca aprueba nada.

## Métricas y rumbo

Dos piezas pequeñas, sin dependencias fuera de la biblioteca estándar: `herramientas/metricas.py` (el registro y el importador de Cloudflare) y `herramientas/rumbo.py` (la recomendación). Los parámetros están en `metricas/politica.json`.

**Registro.** `metricas/registro.csv`, que solo crece por el final y se versiona en git: `semana,juego,metrica,valor,fuente,nota`. La semana es el lunes (UTC); la métrica, una de las de `politica.json` (`vistas_juego`, `vistas_ficha`, `comentarios_pos`, `comentarios_neg`, `donaciones_usd`, `ingresos_usd`); la fuente, de dónde salió el número. Si un dato (semana, juego, métrica, fuente) aparece dos veces vale la última fila; fuentes distintas de la misma métrica se suman. Se valida todo al leer (lunes, juego existente, conteos enteros, dinero con dos decimales, nota de una línea) y un registro dañado detiene el cálculo con el número de línea en vez de leerse a medias. Las notas que empiezan por `= + - @` se neutralizan para que no sean fórmulas en una hoja de cálculo.

**Importador de Cloudflare.** `metricas cloudflare` consulta la API GraphQL (`rumPageloadEventsAdaptiveGroups`: vistas de página HTML por día y ruta, filtradas por el dominio de `sitio.json → url_base` y sin bots) y agrega filas con fuente `cloudflare`: `/jugar/<id>/` → `vistas_juego`; `/<idioma>/juegos/<id>/` → `vistas_ficha`. La ventana empieza siempre en lunes y no pasa de 27 días (el conjunto de datos limita el rango de cada consulta), así que el ciclo semanal vuelve a cubrir las últimas semanas y las cifras se corrigen solas; las semanas sin visitas se escriben como cero (para distinguirlas de «no medido») y no se agrega nada si el valor no cambió. Si el esquema rechazara el filtro de bots, reintenta sin él y deja `sin filtro de bots` en la nota. El token es de solo lectura (`Account Analytics: Read`), distinto del de Pages, y nunca se escribe en el registro ni en los mensajes. **Sin verificar contra el servicio real:** se probó con respuestas simuladas.

**Rumbo.** Es determinista y sin azar. *Evidencia*: solo semanas completas (la en curso no cuenta), dentro de una ventana de 8 semanas y desde la primera semana con vistas del juego; un juego es «medible» con ≥3 semanas y ≥200 vistas del juego. *Modo*: con menos de 2 juegos medibles, **explorar** (efecto neutro y premio por rasgos que ningún juego de la fábrica tiene); con 2 o más, **aprender**. *Puntaje de un juego* (cociente contra el promedio de la cartera, suavizado hacia 1): alcance = vistas del juego por unidad de exposición, donde cada semana cuenta 1 más una por cada publicación del motor en redes (del libro; el sitio y IndexNow no cuentan) para no premiar a un juego solo por haberse anunciado más; aceptación = proporción de comentarios favorables (solo con ≥10 comentarios y al menos 2 juegos que comparar); apoyo = dólares por mil vistas (solo si alguien pagó algo en la cartera). Los pesos son 0.5, 0.3 y 0.2, renormalizados sobre lo disponible. *Idea*: cada valor de cada eje (género, verbo, objetivo, entrada, progresión) hereda el promedio suavizado del puntaje de los juegos medibles que lo tienen; la idea promedia sus ejes con pesos y suma un premio `0.25/√(n+1)` por lo poco probado; el resultado se multiplica por los factores de riesgo de clon, de costo estimado (`costo_estimado` en `ideas/ideas.json`) y de novedad. Una variante de un juego existente queda fuera; una idea con `bloqueada_por` se lista aparte; una idea cuyo id ya es plantilla o juego se omite. Todos esos números son criterio de diseño, no resultados medidos, y por eso están en `politica.json`.

**Límites.** Con pocos juegos casi todos los rasgos tienen una sola observación; con poco tráfico, ruido. Las vistas de Cloudflare no son partidas ni tiempo de juego, y con la configuración por defecto pueden excluir a la UE y el Reino Unido. El rumbo no construye ni publica y no se salta la compuerta de novedad, la pausa entre lanzamientos ni la huella.

**Flujo semanal.** `ciclo.yml` importa de Cloudflare (solo si hay token; un fallo no lo detiene), calcula el rumbo, escribe `PENDIENTE.md` y guarda también `metricas/registro.csv`. **Analítica en el sitio:** `publicacion/sitio.json → analitica` (vacío o `cloudflare`) solo decide qué dice la página de privacidad (en es/en/zh); activar la medición en sí se hace en el panel de Cloudflare. Con datos de Cloudflare en el registro y el valor vacío, el rumbo avisa de la contradicción.

## Publicación (con aprobación)

El código vive en `publicacion/` (`nucleo.py`, `texto.py`, `red.py` y un adaptador por canal en `adaptadores/`). El flujo es siempre el mismo:

1. **Plan.** `publicar ID` arma, sin ejecutar nada, la lista de acciones de cada canal activo (`politica.json → canales`) con el texto exacto y los archivos.
2. **Huella.** El plan se resume en un SHA-256 (texto, medios, política, sitio y acciones). Cualquier cambio cambia la huella.
3. **Aprobación.** `--ejecutar --aprobar HUELLA` (mínimo 12 caracteres) solo corre si la huella coincide con el plan recalculado.
4. **Compuertas.** Se niega si: hay datos de ejemplo en `sitio.json`, campos PENDIENTE, errores en el kit, una dirección no https, redes sin sitio publicado, un lanzamiento antes de la pausa (`min_dias_entre_lanzamientos`), o un juego que la revisión de novedad no considera apto para ese tipo de canal.
5. **Ejecución.** Las claves salen solo del entorno y se tachan de los mensajes. Cada resultado va a `publicacion/libro.jsonl`; lo ya hecho se salta; el ritmo por canal (`max_por_dia`, `min_horas_entre`) se respeta. Un resultado dudoso queda «incierto» (con el hash del texto y, en Bluesky, la cuenta), no se reintenta solo y se resuelve con `resolver`: `resolver --auto` (flujo `comprobar.yml`, cada día antes del calendario) lee el registro público de la cuenta y concluye con cautela: «salió» solo si el texto exacto aparece en la ventana de tiempo; «no salió» solo si se cumplen condiciones estrictas (hay un envío anterior que sí salió y se ve, y es la primera vez); en cualquier otro caso la duda sigue. Un fallo de una red no frena a las demás; un fallo del sitio sí detiene todo.
6. **Parches.** Subir la versión de un juego ya publicado actualiza el sitio sin volver a publicar en redes, salvo que `avisar_parches` sea verdadero.

Un contrato simple para añadir canales: cada adaptador declara `canal`, `categoria` (`sitio`, `redes` o `portales`) y `secretos`, devuelve sus acciones con `acciones(ctx)` y las ejecuta con `ejecutar(accion, ent, ctx)`. Hoy: Cloudflare Pages, IndexNow, Bluesky, Mastodon, Telegram, Discord, YouTube e itch.io (butler). Las cuentas de bot van declaradas como bot (Bluesky: etiqueta propia; Mastodon: marca de bot) y la fábrica no responde, no sigue y no menciona a nadie.

Los flujos de GitHub (`.github/workflows/`) ejecutan esto con las claves en el entorno `produccion`: `ci.yml` (pruebas), `publicar.yml` (dos pasos: sin huella solo muestra el plan; con huella publica y guarda el libro) y `ciclo.yml` (semanal).

## Cuentas de difusión (bots)

`python3 fabrica.py perfiles` escribe en `difusion/perfiles/` el avatar (una gelatina dibujada por la fábrica), el banner y un `perfiles.md` con nombre, biografía y campos de Bluesky, Mastodon y el canal de Telegram en tres idiomas; se niega a escribir si algún texto no cabe en su red o si `sitio.json` tiene datos de ejemplo. Las cuentas son de bot y lo dicen; el correo de contacto vive solo en el sitio. Las cuentas las crea el dueño (guía en `LEEME-DUENO.md`); el flujo de GitHub «Configurar cuenta de bot» pone después la etiqueta de bot en Bluesky o Mastodon.

## Cómo se evita la producción en serie

`novedad` compara las fichas entre sí por tres ejes (género, verbo y objetivo; ver `catalogo/vocabulario.json`): si los tres coinciden con otro juego, es una **variante** y no sale como juego aparte (sus cambios van como modo o paquete del original); si cambian el género y otro eje, es **distinto**; el resto es **parecido** (sitio y redes sí, portales no). Cambiar colores, personajes o textos no cuenta. No sustituye el criterio de cada plataforma ni compara con juegos de fuera: eso lo cubren `originalidad.referencias` y `originalidad.riesgo_portales`, escritos a mano. Para crecer, `ideas` propone géneros nuevos y `nueva-plantilla` crea el andamio.

## Ciclo semanal

`python3 fabrica.py ciclo` reconstruye, revisa kits, mide novedad, genera el sitio y escribe `publicacion/PENDIENTE.md`: por juego, qué está listo para aprobar o qué lo bloquea, las tres ideas siguientes, el estado del motor (techo, niveles y cola de mejoras) y qué ha funcionado en Bluesky. No usa claves ni publica. `--probar` añade las pruebas en navegador.

## Difusión

Hay dos archivos de datos: `difusion/canales.json` (cada canal con sus reglas, sus riesgos y lo que no se pudo verificar; **cada regla lleva el enlace de la página oficial de donde sale y la fecha en que se leyó**) y `difusion/respuestas.json` (banco de respuestas a comentarios, en español e inglés). Con ellos, `python3 fabrica.py kit <id>` escribe en `salida/<id>/kit/`:

- `difusion.md` — qué canales, en qué orden y para qué; las reglas de cada uno; el texto que le toca; un calendario de 4 semanas (D0 es el día en que la página queda pública); el banco de respuestas y cómo leer las métricas.
- `registro-creacion.md` — quién decidió qué. Es un borrador que el dueño revisa: Poki pide poder enseñar el proceso e itch.io no acepta proyectos con poca intervención humana.

Orden de los canales: primero el sitio propio, tu grupo y las redes con cuenta de bot (Bluesky, Mastodon, Telegram, Discord) y el video en YouTube, que la fábrica puede publicar con aprobación; itch.io es opcional y su página se crea a mano; después de 4 semanas de datos, CrazyGames, Poki y Playgama (este último mediante su MCP; la revisión de los portales es humana); a mano y solo por el dueño, las comunidades como Reddit y los videos en TikTok e Instagram; y Newgrounds, no por ahora. El mapa completo, canal por canal, está en `difusion/MAPA.md` (`python3 fabrica.py mapa` lo regenera).

**Cómo se mantiene:** las reglas de las plataformas cambian. Antes de publicar en un canal se vuelve a leer su fuente y se actualiza `canales.json` (texto, fuente y la fecha `verificado`). `revisar` avisa cuando han pasado más de 30 días.

**Lo que esto implica para la fábrica:** itch.io desaconseja varias páginas para proyectos esencialmente iguales, los «reskins» de cambios mínimos y la producción en masa de páginas con IA, y no acepta proyectos hechos casi por completo por una IA con poca intervención humana. La fábrica no publica variantes en serie: cada juego que sale aparte tiene que ser otro juego (compuerta `novedad`), con decisiones humanas reales anotadas en `registro-creacion.md`, y siempre se declara el uso de IA. La fábrica no esquiva esas reglas, las cumple: escala con géneros nuevos, no con copias. CrazyGames rechaza los clones y Poki puede rechazar los juegos que dependan de plantillas o de IA sin personalidad; cada juego trae su evaluación en `originalidad`.

## Quién hace qué

**Claude:** diseñar, programar, probar y empaquetar los juegos; escribir fichas y publicaciones en tres idiomas; sacar capturas, portada y clips; mantener el sitio, los adaptadores y las plantillas; leer el estado semanal y preparar el plan de cada lanzamiento; leer métricas y comentarios y preparar parches; y, si el equipo está vinculado, ayudar a recorrer los pasos en pantalla.

**Tú, una sola vez:** la cuenta de Cloudflare y su token, el repositorio de GitHub con el entorno `produccion` y sus claves, los datos reales de `sitio.json`, las cuentas de bot de cada red que quieras activar, y, si usas itch.io o anuncios, la cuenta y el cobro. Lo fiscal, con tu contador. Todo, paso a paso, en `LEEME-DUENO.md`. Nadie más puede aceptar esos términos ni dar esos datos por ti, y las claves nunca van en archivos del proyecto ni en el chat.

**Tú, en cada lanzamiento:** un «sí» con la huella del plan que leíste. Las respuestas públicas a comentarios también pasan por tu «sí».

El paso a paso por juego está en `salida/<id>/kit/plan-lanzamiento.md`; los comandos de `butler` (itch.io), ahí mismo.

## Reglas de la casa

- Promoción honesta: solo se dice lo que el juego hace. Nada de cuentas falsas, reseñas inventadas, votos comprados ni respuestas fingidas.
- El uso de IA siempre se declara (en la ficha de itch.io y en cada publicación).
- Cada comunidad tiene sus reglas de autopromoción: se leen antes y, si no permiten promocionar, no se publica ahí.
- No se lanza el siguiente juego hasta tener 2 a 4 semanas de datos del anterior. Más juegos no traen más jugadores por sí solos; lo que decide es que alguien los encuentre.
- Una sola página por juego (en el sitio y en itch.io): las versiones nuevas van a la misma página. Nada de reskins ni de páginas en serie.
- Nada se publica sin la aprobación de un plan exacto (la huella), y no hay cuentas extra: una cuenta de bot declarada por canal.
- No se anuncia el juego en los comentarios ni en las comunidades de otros proyectos de itch.io (sus pautas lo prohíben).
- No se compran visitas, seguidores, reseñas ni votos, y no se usan cuentas falsas ni extra.
- Antes de publicar en un canal se vuelve a leer su fuente (`difusion/canales.json`), y las respuestas públicas a comentarios pasan por el «sí» del dueño.

## Lo que no está verificado

- Las reglas de Reddit y de cada comunidad (Reddit no se pudo leer), las reglas de etiquetado de IA y de enlaces de YouTube, TikTok e Instagram, y las reglas del portal de juegos de Newgrounds (solo se leyó la de su portal de arte).
- De los portales: la postura de CrazyGames sobre juegos hechos con IA, el plazo de su revisión y su porcentaje de ingresos; el porcentaje, los plazos y los límites de tamaño y de carga de Poki; el porcentaje, los pagos y la moderación de Playgama. Está todo en «Sin verificar» de cada canal en `difusion.md`.
- Los adaptadores de publicación (Cloudflare Pages, Bluesky, Mastodon, Telegram, Discord, YouTube, itch.io) se probaron solo contra simulaciones y programas falsos, no contra los servicios reales: la primera ejecución real de cada canal debe ser supervisada. Detalles puntuales sin confirmar: si `wrangler` puede crear el proyecto de Pages por sí solo, el formato de la subida reanudable de YouTube, los parámetros de envío de Telegram y la última versión de las acciones de GitHub.
- Los SDK de los portales: el módulo `anuncios` trae adaptadores para AdSense, CrazyGames y Poki, escritos según la documentación disponible y probados **solo con simulaciones**; la prueba real es la herramienta de vista previa de cada portal, con la cuenta del dueño. El de Poki es un borrador hasta que Poki entregue su documentación (lo hace después de aceptar el juego); el Bridge SDK de Playgama no está integrado. Poki además pide cubrir un lienzo 16:9 en escritorio, algo que Torre (vertical) todavía no hace. Detalle en `monetizacion/ESTRATEGIA.md`.
- Cómo pondera itch.io la visibilidad en explorar y búsqueda, y cuánto pesa en ella la declaración de IA.
- Que el nombre de cada juego esté libre en itch.io y en las tiendas: búscalo antes de publicar.
- Los datos de itch.io, butler y la declaración de IA salen de su documentación al momento de escribir el kit; si su panel cambió, manda el panel.

Ya verificado el 12 de noviembre de 2026, cada punto con su fuente en `difusion/canales.json`: la proporción de la portada de itch.io (315:250; las portadas de la fábrica miden 1260×1000), sus pautas de calidad y de IA, las reglas del tablero Release announcements y los requisitos que publican CrazyGames, Poki y Playgama.

## Estado y pendientes

- El sitio está en línea en https://taller-gelatina.pages.dev (subido a mano a Cloudflare Pages con `sitio --zip`; las páginas Novedades y Prensa llegan con la siguiente subida). Todavía no hay ninguna red activa: `publicacion/politica.json → canales` solo tiene `sitio-propio` e `indexnow`, y los adaptadores de las redes solo se han probado contra simulaciones. Lo que está bloqueado en cada momento lo dice `publicacion/PENDIENTE.md`.
- Decisiones tuyas pendientes: qué redes activar (guía en `LEEME-DUENO.md → Los bots de difusión`), el repositorio de GitHub que las hace trabajar solas y confirmar o corregir el `registro-creacion.md` de cada juego.
- Los dos juegos están en la lista del sitio (`publicacion/sitio.json → juegos`): saldrán juntos al publicar el sitio. Las publicaciones en redes siguen la pausa entre lanzamientos (14 días por defecto), así que el segundo juego se anuncia después del primero. La marca es «Taller Gelatina».
- Siguiente paso técnico recomendado: la primera plantilla nueva del cuaderno de ideas, la que diga `python3 fabrica.py rumbo` (sin datos, hoy es `compas`; `trazos` está en espera hasta que alguien nativo revise el chino). Una plantilla nueva es lo que hace crecer la fábrica sin caer en variantes.
- Revisión humana pendiente: el chino de ambos juegos y del sitio, y la página de privacidad.
- Con el sitio público: fijar `apoyo_url` (si quieres un enlace de apoyo dentro del juego) y alimentar el registro de métricas (`python3 fabrica.py metricas anotar`; las vistas entran solas si se activa la medición de Cloudflare, ver `LEEME-DUENO.md → Medir visitas y decidir el rumbo`). El sitio nace sin analítica.
