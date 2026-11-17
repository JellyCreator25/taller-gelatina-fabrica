# Mapa de canales: qué puede hacer el motor solo

Verificado el 12 de noviembre de 2026 en las páginas oficiales de cada canal (las fuentes están en `difusion.md` de cada juego y en `investigar/notas-2026-11-12.md`). Las plataformas cambian sus reglas: pasados 30 días, `fabrica.py revisar` pide volver a leerlas.

## Cómo leerlo

- **Total:** tras tus pasos de una sola vez, el motor publica sin pasos manuales en cada ocasión.
- **Parcial:** el motor hace una parte (subir, preparar) y queda un paso humano por juego o por versión.
- **Manual:** no encontré una vía programática en lo que leí; tú publicas y el motor deja el material listo.
- **Bloqueado:** hoy no es viable para este modelo (por requisitos técnicos, de contrato o de cuenta).

## Resumen

| Nivel | Canales |
|---|---|
| Total | Sitio propio multilingüe (Cloudflare Pages); Aviso a buscadores (IndexNow); Bluesky (cuenta dedicada de la fábrica); Mastodon (cuenta de bot en un servidor que lo permita); Canal propio de Telegram (con un bot); Tu propio servidor de Discord (webhook) |
| Parcial | YouTube (subida de video por API); Página del juego en itch.io; Poki (portal de juegos web); Playgama (portal) mediante su MCP; Anuncios en tu sitio (AdSense, anuncios para juegos HTML5) |
| Manual | Tu grupo de clase y tus amigos (WhatsApp, Telegram); Tablero «Release announcements» de itch.io; Devlogs de itch.io; Videos cortos en TikTok e Instagram Reels (Shorts de YouTube: ver el canal de YouTube); Comunidades en Reddit y foros de juegos; CrazyGames (portal de juegos web); Newgrounds |
| Bloqueado | Google Play (juego envuelto como app); App Store de Apple (juego envuelto como app); Google GameSnacks; Yandex Games; GameDistribution |

## Canal por canal

| Canal | Nivel | Vía | Una sola vez (solo tú) | Cada vez (el motor) | Ingresos |
|---|---|---|---|---|---|
| Sitio propio multilingüe (Cloudflare Pages) | Total | wrangler pages deploy desde GitHub Actions | Crear una cuenta gratuita de Cloudflare. · Crear el proyecto de Pages (desde el panel con subida directa, o con `npx wrangler pages project create`) con el nombre que pongas en sitio.json. · Crear un token de API con el permiso Account → Cloudflare Pages → Edit y copiar el ID de la cuenta. · Guardar CLOUDFLARE_API_TOKEN y CLOUDFLARE_ACCOUNT_ID como secretos del entorno «produccion» de tu repositorio de GitHub (nunca en el chat ni en un archivo). · Escribir en sitio.json la dirección real y un contacto para la política de privacidad. | Generar el sitio y comprobar enlaces, idiomas alternos y mapa del sitio. · Desplegar. · Avisar a IndexNow. | anuncios (si Google aprueba tu sitio) o donaciones; ninguno hasta que haya visitas |
| Aviso a buscadores (IndexNow) | Total | HTTP POST con JSON | Nada: la clave la genera el motor y se publica como archivo del sitio. | Enviar las URL nuevas o cambiadas después del despliegue. | ninguno directo (trae visitas) |
| Bluesky (cuenta dedicada de la fábrica) | Total | AT Protocol: createSession con contraseña de aplicación y createRecord | Crear la cuenta (una dedicada a la fábrica) y una contraseña de aplicación en los ajustes de la cuenta. · Guardar BSKY_IDENTIFIER (el identificador de la cuenta) y BSKY_APP_PASSWORD como secretos del entorno «produccion». · Con las dos claves en el entorno, ejecutar una vez `python3 fabrica.py configurar bluesky-bot --ejecutar` para poner la etiqueta «bot» en el perfil (así lo recomienda la guía oficial de bots). | Iniciar sesión, subir la imagen y crear el post con el enlace como faceta. | ninguno directo (trae visitas) |
| Mastodon (cuenta de bot en un servidor que lo permita) | Total | API REST de Mastodon con token de acceso | Elegir un servidor cuya política admita bots y autopromoción, y crear la cuenta. · Crear una aplicación desde el menú de desarrollo de la cuenta con los permisos write:statuses, write:media y write:accounts (los nombres de menú varían según el servidor). · Guardar MASTODON_INSTANCE (la dirección del servidor) y MASTODON_TOKEN como secretos del entorno «produccion». · Con las dos claves en el entorno, ejecutar una vez `python3 fabrica.py configurar mastodon-bot --ejecutar` para marcar la cuenta como bot (también se puede en los ajustes del perfil). | Subir la imagen, esperar su procesamiento y publicar el estado con Idempotency-Key. | ninguno directo (trae visitas) |
| Canal propio de Telegram (con un bot) | Total | Bot API de Telegram | Crear un bot con @BotFather y guardar su token como TELEGRAM_BOT_TOKEN. · Crear un canal público y añadir el bot como administrador con permiso para publicar. · Guardar el nombre del canal (por ejemplo @micanal) como TELEGRAM_CHAT_ID. | Enviar el mensaje (con foto si hay imagen). | ninguno directo (trae visitas) |
| Tu propio servidor de Discord (webhook) | Total | Webhook de Discord (HTTP POST con JSON) | Crear el servidor y un canal de novedades. · Crear un webhook en la configuración del canal (integraciones) y guardar su URL como DISCORD_WEBHOOK_URL. | Publicar un mensaje con una tarjeta (título, enlace, imagen). | ninguno directo (trae visitas) |
| YouTube (subida de video por API) | Parcial | YouTube Data API v3 (videos.insert) con OAuth | Crear el canal y un proyecto de Google Cloud con la API de YouTube Data v3 activada. · Configurar la pantalla de consentimiento y crear credenciales OAuth; autorizar una vez con el permiso youtube.upload. · Guardar YT_CLIENT_ID, YT_CLIENT_SECRET y YT_REFRESH_TOKEN como secretos del entorno «produccion». · Comprobar a los 8 días que el token sigue funcionando. · Decidir las declaraciones del video (hecho para niños, contenido sintético) en politica.json. | Cambiar el token de actualización por uno de acceso y subir el clip con título, descripción y visibilidad. | ninguno directo (trae visitas) |
| Página del juego en itch.io (opcional) | Parcial | butler (la herramienta oficial de itch.io) para subir el zip; la página y su marcado se hacen a mano | Crear la cuenta de itch.io y los cobros. · Crear la página de cada juego a mano (borrador). · Instalar butler, ejecutar `butler login` y guardar la clave API como secreto (BUTLER_API_KEY). · La primera vez que sube el archivo: marcarlo como HTML5 en «Edit game». | `butler push` del zip al canal del juego, con el número de versión. | donaciones (en HTML5, itch.io solo admite donaciones) |
| Poki (portal de juegos web) | Parcial | CLI oficial `@poki/cli`: sube el juego; pedir la revisión es manual | Crear la cuenta de desarrollador y dar de alta el juego en developers.poki.com (da el game_id). · Iniciar sesión con la CLI en el navegador (una vez). · Pedir la revisión desde su panel y aceptar el trato. | `poki upload` de la versión nueva (con nombre y notas). | reparto del portal: 100 % si el jugador llega por ti y 50 % si lo trae Poki (según su página de tratos); calendario y umbral de pago no publicados |
| Playgama (portal) mediante su MCP | Parcial | MCP oficial (un agente sube builds y portadas y publica un enlace «sandbox»); el catálogo y los cobros los gestiona una persona | Crear tu cuenta de Playgama. · Conectar su MCP al cliente e iniciar sesión en el navegador (tú escribes tu contraseña, nunca en el chat). · Enviar el juego al catálogo público y configurar el cobro. | Integrar el Bridge SDK, subir la build y las portadas, leer métricas. | anuncios mediante el portal; porcentaje, calendario y mínimo de pago: sin cita oficial |
| Anuncios en tu sitio (AdSense, anuncios para juegos HTML5) | Parcial | Solicitud y aprobación por Google; después, código en el sitio | Pedir la cuenta de AdSense y la aprobación del sitio, y configurar el cobro a tu cuenta. · Pedir acceso a la API Ad Placement si Google lo exige. | Integrar el código aprobado y actualizar la política de privacidad y ads.txt. | anuncios (porcentaje no publicado) |
| Tu grupo de clase y tus amigos (WhatsApp, Telegram) | Manual | Mensaje en tus chats (el motor no tiene acceso a ellos) | Mandar el mensaje a quien quieras. | Dejar el texto escrito y con el enlace real. | ninguno directo |
| Tablero «Release announcements» de itch.io (opcional) | Manual | Publicación a mano en el sitio de itch.io | Publicar el texto listo desde tu cuenta. | Dejar el texto, el título y los medios a la vista. | ninguno directo |
| Devlogs de itch.io (opcional) | Manual | Publicación a mano en el sitio de itch.io | Publicar el texto listo desde tu cuenta. | Dejar el texto, el título y los medios a la vista. | ninguno directo |
| Videos cortos en TikTok e Instagram Reels (Shorts de YouTube: ver el canal de YouTube) | Manual | App de cada red (TikTok sin auditar solo publica en privado; Instagram no se verificó) | Publicar el clip vertical desde tu cuenta. | Dejar `clip-vertical.mp4`, la descripción y la línea de IA listos. | ninguno directo |
| Comunidades en Reddit y foros de juegos | Manual | Cada comunidad fija sus reglas; no pude leer Reddit | Leer las reglas de cada comunidad y publicar tú. | Dejar el texto y señalar qué comprobar. | ninguno directo |
| CrazyGames (portal de juegos web) | Manual | Herramienta web de desarrolladores (la documentación que leí no describe una API de subida) | Crear la cuenta de desarrollador, aceptar sus términos y enviar el juego con sus materiales. | Preparar el paquete, la descripción, los controles y las portadas. | reparto del portal (desde el lanzamiento completo; el porcentaje no está en lo que leí) |
| Newgrounds | Manual | Sin vía programática verificada | Leer las reglas del portal de juegos antes de decidir. | — | no verificado |
| Google Play (juego envuelto como app) | Bloqueado | Consola de Google Play (sin vía automática verificada) | Reunir los testers y pasar la prueba cerrada, si algún día decides ir. | — | no verificado |
| App Store de Apple (juego envuelto como app) | Bloqueado | Revisión de Apple (por persona) | — | — | no verificado |
| Google GameSnacks | Bloqueado | No descrito: la página menciona una API de socios sin detalle | — | — | no verificado |
| Yandex Games | Bloqueado | Panel de desarrolladores (sin vía automática verificada) | — | — | no verificado |
| GameDistribution | Bloqueado | Sin información verificada sobre el envío | — | — | no verificado |

## Secretos que usa el motor

Solo existen en el entorno «produccion» de tu repositorio de GitHub (Settings → Environments), con revisores obligatorios. Nunca van en el chat, en `juego.json` ni en ningún archivo del repositorio. Nombres: `BSKY_APP_PASSWORD`, `BSKY_IDENTIFIER`, `BUTLER_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `DISCORD_WEBHOOK_URL`, `MASTODON_INSTANCE`, `MASTODON_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

## Lo que siempre queda en manos de una persona

- Crear cuentas, aceptar términos y configurar cobros: son tuyos y de tu identidad; el motor no los hace por ti.
- **Página del juego en itch.io:** La página de cada proyecto se crea a mano: un administrador de itch.io respondió en el foro (2021) que no ofrecen una forma programática de crearla; puede haber cambiado. ([fuente](https://itch.io/t/1262867/new-game-page-programatically-using-server-api-or-butler))
- **Página del juego en itch.io:** El canal HTML5 se marca a mano en «Edit game» y la página debe estar en el tipo «HTML». ([fuente](https://itch.io/docs/butler/pushing.html))
- **Videos cortos en TikTok e Instagram Reels (Shorts de YouTube: ver el canal de YouTube):** En TikTok, todo lo que publiquen clientes sin auditar queda en modo privado hasta pasar su auditoría. ([fuente](https://developers.tiktok.com/doc/content-posting-api-get-started))
- **Poki (portal de juegos web):** Pedir la revisión del juego es un paso manual; la CLI solo sube. ([fuente](https://github.com/poki/poki-cli))
- **Playgama (portal) mediante su MCP:** Publicar un juego deja un enlace de prueba («sandbox»); entrar al catálogo público es un paso aparte. ([fuente](https://playgama.com/mcp/))
- **Anuncios en tu sitio (AdSense, anuncios para juegos HTML5):** Google aprueba o rechaza cada sitio a su discreción. ([fuente](https://adsense.google.com/start/h5-games-ads/))
- **Google Play (juego envuelto como app):** Una cuenta personal creada después del 13 de noviembre de 2023 necesita 12 testers reales durante 14 días antes de producción. ([fuente](https://support.google.com/googleplay/android-developer/answer/14151465))
- **App Store de Apple (juego envuelto como app):** Las apps hechas con plantilla o generador se rechazan salvo que las envíe el dueño del contenido, y no se admiten duplicados (4.2.6 y 4.3). ([fuente](https://developer.apple.com/app-store/review/guidelines/))
- **Yandex Games:** El contrato de pago se firma con una persona jurídica o un empresario individual en Rusia; para otros países, la página solo describe a personas jurídicas. ([fuente](https://yandex.com/dev/games/doc/en/payments))

## Ingresos: lo que sí y lo que no se puede decir

- Ningún canal de esta lista garantiza ingresos. Un sitio o una cuenta nueva no tiene visitas, y sin visitas no hay anuncios ni donaciones.
- Los porcentajes de reparto de Poki, CrazyGames y Playgama no están en páginas oficiales que haya podido leer completas (ver `investigar/notas-2026-11-12.md`).
- Lo fiscal (cobrar desde México, facturar, impuestos) se ve con tu contador antes de activar cualquier cobro.
