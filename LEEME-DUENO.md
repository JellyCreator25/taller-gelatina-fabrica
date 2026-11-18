# Guía del dueño

Esta guía es para ti, Max. Dice qué hace la fábrica sola, qué solo puedes hacer tú (una sola vez, casi todo cuentas y claves) y cómo se aprueba cada publicación. Los detalles técnicos están en `LEEME.md`; el mapa de canales, con las reglas de cada plataforma y su fuente, en `difusion/MAPA.md`.

## En una página

La fábrica hace cuatro cosas de punta a punta:

1. **Crea** juegos nuevos a partir de una ficha y una plantilla, los **prueba** en un navegador real (escritorio y celular, tres idiomas: español, inglés y chino) y los **empaqueta**.
2. **Publica** un sitio propio con todos los juegos en es/en/zh (Cloudflare Pages), avisa a los buscadores (IndexNow) y, si activas esos canales, publica en Bluesky, Mastodon, Telegram, Discord y YouTube, siempre con cuentas declaradas como bot y con la línea que declara el uso de IA.
3. **Se acuerda** de lo que ya publicó (`publicacion/libro.jsonl`) para no repetir nada, respeta pausas entre lanzamientos y topes por canal.
4. **Cada semana** reconstruye todo, revisa y deja en `publicacion/PENDIENTE.md` qué está listo para aprobar y qué falta.

Lo que **no** hace, a propósito: crear cuentas, aceptar términos, ver tus contraseñas, cobrar, ni publicar nada sin que tú apruebes **ese plan exacto**. Tampoco puede prometer ingresos: un sitio con juegos gratis no trae jugadores por sí solo; los trae la difusión, y el dinero llega (si llega) cuando hay jugadores.

## Ruta rápida: el sitio público hoy, sin GitHub ni claves

Es el camino más corto y solo necesita una computadora (desde el celular no es práctico), una cuenta gratuita de Cloudflare y unos 15 minutos. Publica el sitio con los dos juegos en es/en/zh; las redes y la automatización se agregan después con la ruta completa.

1. **Tres decisiones tuyas, que me dices en el chat:** el nombre del proyecto (la dirección será `NOMBRE.pages.dev`; propongo `taller-gelatina`, si está libre), un contacto público para la página de privacidad (un correo que no te importe que sea público) y, si quieres, otro nombre de marca distinto de «Taller Gelatina».
2. **Yo:** actualizo `publicacion/sitio.json`, corro `python3 fabrica.py sitio --zip` y te dejo `dist/sitio.zip`. El comando se niega a generar el zip mientras haya datos de ejemplo.
3. **Tú:** en el panel de Cloudflare, *Workers & Pages → Create application → Pages → Use direct upload* (o *Drag and drop your files*; los nombres del panel cambian), escribe el nombre del proyecto, arrastra `dist/sitio.zip` y pulsa *Deploy site*. Si el nombre ya está ocupado, Cloudflare te propondrá otro: avísame cuál quedó y rehago el zip con esa dirección, porque las direcciones del sitio (mapa del sitio, versiones por idioma) dependen de ella.
4. **Los dos revisamos** el sitio ya publicado, en celular y en computadora.

Esta ruta no pasa por la aprobación de `publicar`, porque subir el zip ya es tu aprobación; tampoco queda registrada en el libro, así que la primera publicación automática volverá a subir el sitio (no hace daño). La documentación de Cloudflare indica que el panel acepta un zip o una carpeta (hasta 1,000 archivos y 25 MiB por archivo). Lo que no verifiqué: que el panel respete el archivo `_headers` (solo afecta a que `/jugar/` no se indexe y a cabeceras de seguridad) y que el zip con `index.html` en la raíz se abra como esperamos; por eso lo revisamos juntos al terminar.

## Lo que sí te toca a ti, en orden de valor (ruta completa)

Con los pasos 1 a 4 ya hay un sitio público con el juego, aunque no publiques en ninguna red.

**1. Cloudflare (unos 10 minutos).**
- Crea una cuenta gratuita en Cloudflare.
- En *Workers & Pages* crea un proyecto de Pages de subida directa (*Direct Upload*) con el nombre que quieras; ese nombre es el `proyecto`. La dirección será `https://NOMBRE.pages.dev`.
- Crea un token de API con permiso de edición de Cloudflare Pages en tu cuenta, y anota el *Account ID*.
- Los dos valores (token y Account ID) son secretos: van solo al paso 3, nunca a un chat ni a un archivo del proyecto.

**2. Los datos reales del sitio.** Edita `publicacion/sitio.json`:
- `url_base`: la dirección https real del paso 1 (o tu dominio propio, si compras uno).
- `proyecto`: el nombre del proyecto de Pages.
- `contacto`: un correo o una dirección pública para la página de privacidad. Aparece en el pie de todo el sitio.
- `privacidad_actualizada`: la fecha en que revisaste la página de privacidad (campo opcional; agrégalo cuando la revises).
- `nombre` y `lema`: la marca es «Taller Gelatina» (la imagen de la gelatina es la identidad del sitio y de los juegos); cámbiala solo si quieres otro nombre.

Mientras esos datos tengan el valor de ejemplo, la fábrica se niega a publicar. Es la compuerta que evita publicar con una dirección falsa.

**3. GitHub (el «hogar» que la hace trabajar sola).**
- Crea un repositorio privado y sube esta carpeta (el archivo `.gitignore` ya excluye lo que no debe subirse).
- En *Settings → Environments* crea el entorno `produccion` y guarda ahí, como *secrets*, las claves: al principio solo `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID`. Las demás se agregan canal por canal (paso 5).
- Opcional pero recomendable: en ese mismo entorno activa *Required reviewers* con tu usuario. Así, además de la huella, GitHub te pide un segundo «sí» antes de usar las claves.
- Los flujos están en `.github/workflows/`: `ci.yml` (pruebas en cada cambio), `publicar.yml` (publicar con aprobación) y `ciclo.yml` (revisión semanal, los lunes).

**4. La primera publicación, supervisada.**
- En la pestaña *Actions* corre «Publicar» con `juego = guerreros-gelatina` y **sin huella**. Solo muestra el plan: cada acción, el texto exacto de cada publicación y la huella.
- Léelo. Si está bien, vuelve a correr «Publicar» con la misma huella. El flujo recalcula el plan y se detiene si algo cambió.
- La primera vez, pídeme que esté contigo (o revisa tú el resultado en el sitio): los adaptadores se probaron contra simulaciones, no contra los servicios reales (ver «Lo que no está verificado»).

**5. Redes, una por una y solo si quieres.** Cada una pide su cuenta y sus claves; la lista exacta, con las reglas oficiales, está en `difusion/MAPA.md`. Para activar una, agrégala a `canales` en `publicacion/politica.json`, guarda sus claves en el entorno `produccion` y corre el plan de nuevo antes de aprobar.

| Canal | Claves (secrets) | Una sola vez, aparte de las claves |
|---|---|---|
| Bluesky | `BSKY_IDENTIFIER`, `BSKY_APP_PASSWORD` | Cuenta propia de la fábrica y contraseña de aplicación (no la principal). Con las claves en el entorno, `python3 fabrica.py configurar bluesky-bot --ejecutar` pone la etiqueta «bot» en el perfil, y `configurar bluesky-perfil --ejecutar` pone nombre, biografía, avatar y banner. |
| Mastodon | `MASTODON_INSTANCE`, `MASTODON_TOKEN` | Cuenta en una instancia que permita bots; `configurar mastodon-bot --ejecutar` marca la cuenta como bot. |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Un bot (con BotFather) y un canal propio donde sea administrador. |
| Discord | `DISCORD_WEBHOOK_URL` | Un webhook en un servidor tuyo. Solo en servidores donde tengas permiso. |
| YouTube | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | Proyecto de Google Cloud con la API de YouTube, credenciales OAuth y una autorización única. En modo de pruebas el token de actualización caduca a los 7 días: revisa que siga funcionando. |
| itch.io (opcional) | `BUTLER_API_KEY` | La página del juego se crea a mano; el motor solo sube el zip con `butler`. |

Reglas que no se negocian, y que la fábrica cumple sola: una cuenta de bot declarada por canal, sin cuentas extra, sin compras de seguidores o votos y sin interacciones no solicitadas (no responde, no sigue, no menciona a nadie). Cada publicación lleva la línea que declara el uso de IA.

## Las páginas de difusión del sitio (ya hechas)

Además de la portada y la página de cada juego, el sitio tiene dos páginas por idioma que yo mantengo:

- **Novedades** (`/es/novedades/`): las notas de cada versión. Cuando subo la versión de un juego, escribo la nota en `juego.json → novedades` (versión y texto en español, inglés y chino; si falta un idioma, el sitio no se genera). Así los parches se anuncian en el sitio sin llenar de publicaciones las redes.
- **Prensa** (`/es/prensa/`): datos rápidos, la declaración de que se hizo con ayuda de IA, portada y capturas para abrir en grande, y tu contacto. Es lo que le mando o le enlazo a quien quiera reseñar o mostrar un juego. Una frase de esa página es decisión tuya: «puedes usar estas imágenes para reseñar, comentar o mostrar los juegos» (está en `sitio-textos.json → prensa_uso`); si prefieres otra condición, dímelo y la cambio.

Cada vez que cambian, hay que volver a subir `dist/sitio.zip` a Cloudflare Pages (o, con GitHub conectado, se publica solo al aprobar).

## Los bots de difusión: alta paso a paso

**Ya está hecho:** en `difusion/perfiles/` están `avatar.png` (la gelatina), `banner.png` y `perfiles.md`, con el nombre y la biografía de cada red en español, inglés y chino, ya medidos contra los límites de cada una (Bluesky: nombre 64 y biografía 256 caracteres; Mastodon: 30 y 500, con 4 campos, aunque cada servidor puede variar; Telegram: título 128 y descripción 255). Se regeneran con `python3 fabrica.py perfiles`. Las biografías dicen que la cuenta es un bot: no quites esa frase.

**Lo que solo puedes hacer tú:** crear cada cuenta, aceptar sus términos y copiar contraseñas o tokens a GitHub. Yo no puedo hacer ninguna de esas tres cosas, y las claves nunca se escriben en el chat. Van de la menos exigente a la más: si Mastodon no te convence, se omite sin perder lo esencial.

**Antes de las redes necesitas el repositorio de GitHub** (paso 3 de la ruta completa): sin él, el sitio ya está en línea pero ningún bot puede publicar solo. Si conectas GitHub en los ajustes de Claude (Conectores), yo puedo subir la carpeta por ti; los secretos y las cuentas siguen siendo tuyos.

**A. Bluesky (unos 10 minutos).**
1. Crea la cuenta en bsky.app con un correo tuyo. Usuario sugerido: `tallergelatina` (si está libre, queda `tallergelatina.bsky.social`).
2. No hace falta editar el perfil: nombre, biografía, avatar y banner los pone la fábrica en el paso 5 (tú no pegas nada).
3. *Ajustes → Privacidad y seguridad → Contraseñas de aplicación → Añadir*. Llámala `fabrica`; si aparece la opción de acceso a mensajes directos, déjala sin marcar. Copia la contraseña (`xxxx-xxxx-xxxx-xxxx`): se muestra una sola vez.
4. En GitHub, entorno `produccion`, guarda `BSKY_IDENTIFIER` (el usuario completo, `tallergelatina.bsky.social`) y `BSKY_APP_PASSWORD`.
5. *Actions → Configurar cuenta de bot*: córrelo con `bluesky-bot` (pone la etiqueta «bot») y con `bluesky-perfil` (pone nombre, biografía, avatar y banner de `difusion/perfiles/`, conservando la etiqueta). Cada uno se corre primero sin marcar «ejecutar» (solo muestra qué haría) y luego marcándolo. Si cambia la promesa o el banner, se regeneran con `python3 fabrica.py perfiles` y se vuelve a correr `bluesky-perfil`.
6. Agrega `"bluesky"` a `canales` en `publicacion/politica.json`.

**B. Canal de Telegram (unos 10 minutos).**
1. En Telegram, habla con @BotFather: `/newbot`. El nombre de usuario del bot debe terminar en `bot` (por ejemplo `TallerGelatinaBot`). Te da un token: es `TELEGRAM_BOT_TOKEN`.
2. Crea un canal **público**, con el título y la descripción del bloque «Canal de Telegram» de `perfiles.md` y `avatar.png` de foto.
3. Agrega el bot como administrador del canal, con permiso de publicar mensajes.
4. Guarda `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` (el usuario del canal con arroba, por ejemplo `@tallergelatina`) en `produccion`.
5. Agrega `"telegram-canal"` a `canales`. Telegram no necesita el paso de «bot» de arriba: el bot ya lo es.

**C. Mastodon (el que pide más cuidado).**
1. Elige un servidor y **lee sus reglas** antes de crear nada: tienen que admitir bots y autopromoción, y conviene que no excluyan cuentas que anuncian contenido hecho con IA. `botsin.space`, el servidor dedicado a bots, cerró a finales de 2024. Un desarrollador contó que `mastodon.social` suspendió su cuenta de agente de IA por no alojar cuentas de IA generativa; es un solo relato, no una regla que yo haya leído, pero basta para no elegir por costumbre.
2. Crea la cuenta; sube las imágenes y copia nombre, biografía y los cuatro campos del bloque «Mastodon» de `perfiles.md`.
3. *Preferencias → Desarrollo → Nueva aplicación* (los nombres de menú varían según el servidor). Llámala `fabrica` y dale solo los permisos `write:statuses`, `write:media` y `write:accounts`. Copia el token de acceso.
4. Guarda en `produccion`: `MASTODON_INSTANCE` (la dirección completa, con `https://`) y `MASTODON_TOKEN`.
5. *Actions → Configurar cuenta de bot*: `mastodon-bot`, primero sin y luego con «ejecutar».
6. Agrega `"mastodon"` a `canales`.

**Después, la primera publicación en cada red es supervisada:** corre *Publicar* sin huella, lee el plan (el texto exacto de cada red) y apruébalo con la huella. Cada red publica un solo mensaje por novedad, en el idioma de `publicacion/politica.json`, con la línea de IA y el enlace al sitio. No hay respuestas, ni seguidos, ni impulsos automáticos, y no hay cuentas extra. Los adaptadores solo se han probado contra simulaciones: si algo falla, el primer error real será el dato más útil.

## Cómo se aprueba (la huella)

El plan de cada publicación se convierte en una **huella**: un código que depende del texto exacto, los archivos, el sitio, las políticas y la lista de acciones. Aprobar es pasar esa huella; si cambia una coma, la huella cambia y hay que aprobar de nuevo. Así, un «sí» tuyo nunca cubre algo que no leíste.

Antes de ejecutar, las compuertas se niegan si falta algo: datos de ejemplo en `sitio.json`, campos marcados PENDIENTE, errores en el kit, una dirección que no sea https, redes sin sitio publicado, o un nuevo lanzamiento antes de la pausa (14 días por defecto), o si el juego no pasa la revisión de novedad.

## Si algo sale mal

- Cada resultado queda en `publicacion/libro.jsonl`. Lo ya hecho se salta; nunca se publica dos veces lo mismo.
- Si una red no contestó y no se sabe si el envío salió, queda como **incierto** y **no se reintenta solo** (se evitan los duplicados). Revisa la cuenta y anota qué pasó: `python3 fabrica.py resolver ACCION salio` o `no-salio`.
- Un fallo en una red no frena a las demás. Un fallo del sitio sí detiene la ejecución.
- Los secretos se toman solo del entorno y se tachan en los mensajes de error.

## El ritmo semanal

El flujo «Ciclo semanal» corre los lunes (o a mano) y deja `publicacion/PENDIENTE.md`: qué juegos están listos para aprobar, cuáles están bloqueados y por qué, y qué construir después. Abre ese archivo y listo. Si GitHub desactiva el flujo por falta de actividad, se reactiva desde *Actions*.

Además, **yo** reviso cada lunes (≈13:00, hora de la Ciudad de México) con una tarea programada: leo el estado, compruebo que lo aprobado salió, miro cómo les fue a las publicaciones, preparo el siguiente lote de Bluesky con las tendencias de esa semana, hago un paso de mejora del motor y avanzo el tercer juego (Compás). Te escribo un solo informe con lo que necesita tu decisión. No apruebo nada por mí misma: el lote nuevo queda sin aprobar y tú lo apruebas con su huella. Para pausarla o cambiarla, dímelo.

## Cómo crece la fábrica (y por qué no son «variantes en serie»)

Cambiar colores o textos de un juego existente no es un juego nuevo, y las plataformas lo tratan como relleno. Por eso la fábrica lo impide: `python3 fabrica.py novedad` compara cada juego contra los demás (género, verbo, objetivo, progresión) y contra los juegos de fuera, y la compuerta no deja publicar una variante.

El camino para crecer es una **plantilla nueva** (otro género), no otra ficha de la misma:
- `python3 fabrica.py ideas` muestra el cuaderno de ideas frente a lo que ya existe, y `python3 fabrica.py rumbo` las ordena según las métricas (ver la sección siguiente); ese orden es lo que aparece en «Qué construir después» de `PENDIENTE.md`.
- `python3 fabrica.py nueva-plantilla ...` crea el andamio; el diseño y el código del juego los hago yo, con pruebas.
- Un juego solo sale en el sitio cuando su id se agrega a `publicacion/sitio.json → juegos`. Esa línea es la decisión de lanzarlo.
- Torre Gelatina tiene riesgo alto de parecerse a un juego de fuera: no va a portales, solo a tu sitio (ya está en la lista del sitio, junto a Guerreros).

## El motor que crece solo y la marca

Cada juego nuevo tiene que sentirse mejor que el anterior, y eso lo exige la fábrica, no la buena voluntad: hay una **escalera de calidad** (1 Base, 2 Con sonido, 3 Con jugo y accesible, 4 Con música, 5 Con marca) y un juego nuevo no puede lanzarse si no está al menos un nivel por encima del mejor ya publicado. El motor crece con módulos opcionales (accesibilidad, efectos, música, marca) que se prueban en un navegador real, y una **cola de mejoras** que se calcula sola dice qué sigue. Guerreros y Torre salieron antes de la escalera y no cambian. Detalle: `LEEME.md`, sección «El motor que crece solo».

La **marca** es la Gelatina como insignia (no solo como tema): `marca/guia.md` tiene la idea, los elementos y lo que ya decidiste: la promesa «Juegos chiquitos, gratis y con delirios de grandeza.», que la Gelatina siga sin nombre propio por ahora y que Guerreros reciba una versión nueva con sello, efectos y música después de Compás.

## Publicaciones del calendario

Además de los lanzamientos, preparo publicaciones propias para Bluesky (hoy, 13: comparaciones, personajes, elige-uno, parodias y más, en la voz de la Gelatina; ver `difusion/voz.md`). Tú aprobaste el lote viendo cada texto, su imagen y su fecha. Cada una se mide a las 24 horas y a los 3 días (likes, reposts, respuestas) para saber qué formatos funcionan. Salen solas, una por día como mucho, a las 10:00 de la Ciudad de México, y solo si siguen siendo exactamente lo que aprobaste.

- **Para frenar una:** dímelo y la quito del calendario, o bórrala desde tu cuenta de Bluesky si ya salió.
- **Para cambiar una:** cualquier cambio (texto, imagen o fecha) la deja sin aprobar y te la vuelvo a mostrar.
- **Si algo falla:** la publicación espera al día siguiente (3 días como máximo) y no sale dos veces. Si el servicio no contesta y no se sabe si salió, se detiene y te aviso.

## Medir visitas y decidir el rumbo

**Cómo decide la fábrica qué construir después.** Todo dato vive en `metricas/registro.csv` (una fila por semana, juego, métrica y fuente) y `python3 fabrica.py rumbo` lo lee junto con el cuaderno de ideas. Cada lunes, el ciclo semanal repite el cálculo y lo deja en `PENDIENTE.md`. Tiene dos modos:

- **Explorar** (el de hoy): mientras no haya al menos 2 juegos con 3 semanas completas y 200 vistas cada uno, los números no dicen nada y el motor no finge lo contrario. Recomienda lo que más se aleja de lo que ya hay, con menos riesgo de clon y menor costo de construir.
- **Aprender**: con esa evidencia, cada juego recibe un puntaje contra el promedio de la cartera (alcance descontando la difusión que se le hizo, proporción de comentarios favorables y dinero por cada mil vistas). Ese puntaje se reparte entre sus rasgos (género, verbo, objetivo, entrada, progresión) y cada idea hereda el de los suyos, con un premio por lo no probado para que el motor no se encierre en lo que ya funcionó.

Los umbrales, los pesos y los factores están en `metricas/politica.json` y son criterio mío, no resultados medidos: se cambian ahí, sin tocar código. El motor **recomienda, no construye ni lanza**: una idea que sería variante de un juego existente queda fuera, una que depende de una persona (como la revisión del chino de Trazos) se lista aparte, y lanzar sigue exigiendo la pausa entre lanzamientos, las compuertas y tu huella. Con poco tráfico va a seguir explorando durante semanas, y es lo correcto: decidir con 40 visitas sería ruido.

**Qué se mide solo y qué no.** Lo único automático son las vistas de página que ve Cloudflare Web Analytics: las de la página de cada juego y las de la página donde se juega. Son vistas, no partidas ni tiempo de juego (un refresco cuenta otra vez), y no hay medición dentro del juego. Comentarios, donaciones, ingresos y lo que reporten itch.io o un portal se anotan a mano, por ejemplo: `python3 fabrica.py metricas anotar guerreros-gelatina comentarios_pos 4 --semana pasada --fuente itch`. También puedes pasarme los números por el chat y los anoto yo. `python3 fabrica.py metricas ver` muestra lo registrado.

**Si quieres la medición automática (opcional, decisión tuya).** Cambia lo que el sitio le promete al jugador, así que va en este orden:

1. **Revisa si ya está encendida sin que lo hayas decidido.** Desde el 15 de octubre de 2025 Cloudflare activa Web Analytics por defecto en los dominios gratuitos; no pude confirmar si eso incluye los proyectos de Pages. En tu proyecto de Pages mira la pestaña *Metrics*, o abre el sitio, *Ver código fuente de la página* y busca `cloudflareinsights`. Si ya está activa, la página de privacidad hoy dice algo que no es cierto: avísame y la corrijo antes que nada.
2. **Actívala a propósito.** En el proyecto, *Metrics → Enable Web Analytics* (el nombre del botón puede variar). Cloudflare inserta su código en el siguiente despliegue. Según Cloudflare, no usa cookies ni almacenamiento local del navegador y no crea huellas de los visitantes; cuenta visitas de forma agregada. Dos advertencias: la opción por defecto de Cloudflare puede excluir a los visitantes de la UE y el Reino Unido (revisa el panel), así que tus cifras podrían no incluir a España; y es probable que la página donde se juega también cargue el código de Cloudflare (hoy no se conecta a nada fuera del sitio).
3. **Dime «activa la analítica»** y yo pongo `"analitica": "cloudflare"` en `sitio.json`. Con eso la página de privacidad deja de decir que no hay herramientas de análisis y explica la de Cloudflare, en español, inglés y chino. Es texto de plantilla: **revísalo tú, que eres abogado**, y el chino necesita revisión nativa. Después hay que volver a subir `dist/sitio.zip`. Mientras el valor esté vacío, el motor se niega a que los datos de Cloudflare y la página de privacidad se contradigan: lo avisa en `PENDIENTE.md`.
4. **Un token de solo lectura.** En Cloudflare: *My Profile → API Tokens → Create Token → Create Custom Token*, permiso **Account → Account Analytics → Read** sobre tu cuenta, y nada más. No reutilices el token de Pages: ese puede editar tu sitio. En GitHub: *Settings → Secrets and variables → Actions → New repository secret* (no el entorno `produccion`: el flujo semanal no usa entornos), con `CLOUDFLARE_ANALITICA_TOKEN` (el token nuevo) y `CLOUDFLARE_ACCOUNT_ID` (el mismo Account ID de antes, guardado también aquí).
5. **Listo.** El lunes, el ciclo semanal importa las últimas semanas antes de calcular el rumbo. Si falla (token vencido, cuenta equivocada), el paso queda en rojo pero el ciclo sigue, y el motivo aparece en el resumen de la corrida. A mano: `python3 fabrica.py metricas cloudflare` con las dos claves en el entorno.

## El dinero, sin adornos

- El sitio es gratis de operar y nace sin analítica ni cookies. Eso es bueno para los jugadores, pero significa que **el propio sitio no mide visitas** mientras no actives la medición (es opcional y decisión tuya: ver «Medir visitas y decidir el rumbo», más abajo). Lo que no se mide solo (comentarios, dinero, cifras de itch.io o de un portal) se anota con `python3 fabrica.py metricas anotar`.
- **Hoy no hay anuncios ni cobro.** El motor ya sabe mostrar anuncios con respeto (módulo `anuncios`: solo entre partidas, con pausa y silencio mientras suenan), pero está **apagado**: tres rutas en `monetizacion/politica.json`, todas en `activa: false`. Qué falta para cada una, de quién es cada pendiente y cuánto podría dar con distinto tráfico: `python3 fabrica.py monetizar` (también sale cada semana en `publicacion/PENDIENTE.md`). La estrategia completa, con sus fuentes y lo que no está verificado: `monetizacion/ESTRATEGIA.md`.
- **Lo que te toca a ti (nada de esto lo hago yo):** crear las cuentas y fijar cómo cobrar. Primero la de **desarrollador de CrazyGames** (es la ruta que antes puede dar ingresos, porque trae sus propios jugadores; su revisión es humana y sus anuncios solo se activan cuando el juego demuestra retener jugadores). Para Compás ya está listo todo lo demás: el zip de la versión para portal, las tres portadas, los dos videos y la ficha con los textos y los requisitos contra el estado real (`salida/compas-gelatina/kit/ficha-crazygames.md`); cuando tengas la cuenta, lo subimos juntos. Después, solo si hay tráfico: dominio propio + cuenta de AdSense + solicitud de «H5 Games Ads». Y si quieres propinas desde ya, una cuenta de apoyo y su enlace. Encender una ruta cambia lo que el sitio le promete al jugador y obliga a publicar de nuevo los juegos afectados con tu aprobación.
- **Anuncios (AdSense) en el sitio propio:** requieren que Google apruebe tu sitio y tu cuenta, y es probable que también un dominio propio (hoy el sitio está en `pages.dev`). Si los activas, pon `adsense_publisher` en `sitio.json`: el sitio genera `ads.txt` y la página de privacidad cambia a la versión con anuncios.
- **itch.io:** en juegos HTML5 solo admite donaciones. Los portales (CrazyGames, Poki, Playgama) pagan por jugadores con un reparto de ingresos y tienen su propia revisión, que es humana; cada uno cobra solo al juntar un mínimo, así que el primer cobro tarda meses aunque los primeros ingresos lleguen antes. Detalles y reglas en `MAPA.md`.
- Todo lo fiscal, con tu contador.
- No hay garantía de ingresos. Lo que la fábrica hace es bajar el costo de probar la idea al mínimo: si tras 4 semanas de datos nadie juega, se sabrá sin haber gastado de más.

## Lo que no está verificado

- Los adaptadores de Cloudflare, Bluesky, Mastodon, Telegram, Discord, YouTube e itch.io se probaron contra simulaciones y programas falsos, no contra los servicios reales. La primera ejecución real de cada canal debe ser supervisada. En particular: si `wrangler` puede crear el proyecto de Pages por sí solo (por eso se pide crearlo antes), el formato exacto de la subida reanudable de YouTube, y los parámetros de envío de Telegram.
- Las versiones de las acciones de GitHub (`actions/checkout`) no se pudieron confirmar contra la última versión publicada; confirma que el flujo corra a la primera, o activa Dependabot.
- El texto en chino necesita revisión de una persona nativa antes de promocionar en ese idioma.
- La importación de visitas desde Cloudflare (`metricas cloudflare`) se armó con la documentación y con ejemplos públicos de su API, y se probó solo con respuestas simuladas: la primera corrida real hay que mirarla. Tampoco pude confirmar si Cloudflare ya activa Web Analytics por su cuenta en los proyectos de Pages (ver abajo) ni si la opción por defecto excluye a los visitantes de la UE y el Reino Unido.
- La página de privacidad es una plantilla. Tú, que eres abogado, debes revisarla (especialmente si activas anuncios) antes de publicar.
- Las reglas de Reddit, TikTok, Instagram, Newgrounds (portal de juegos) y los porcentajes de los portales no se pudieron verificar con fuente oficial. Están marcadas así en `difusion/canales.json`.
- Que el nombre de cada juego esté libre en itch.io y en las tiendas.

## Qué puedo y qué no puedo hacer por ti

**Puedo:** construir y probar juegos, escribir los textos en tres idiomas, preparar los planes, leer el estado semanal y proponer qué sigue, mantener la fábrica (parches, plantillas nuevas) y, con tu computadora vinculada, ayudarte a recorrer los pasos en pantalla.

**No puedo:** crear cuentas, ver o escribir tus contraseñas y claves, aceptar términos por ti, ni aprobar mi propia publicación. Cualquier «sí» es tuyo y es por plan.
