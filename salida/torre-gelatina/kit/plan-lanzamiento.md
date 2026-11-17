# Plan de lanzamiento · Torre Gelatina

Quién hace qué: **Yo** = Claude; **Tú** = el dueño de las cuentas; **Ambos** = yo preparo, tú apruebas.
El camino principal es el **sitio propio** más las redes con cuenta de bot declarada: lo prepara y lo ejecuta la fábrica (`python3 fabrica.py publicar`), y nada sale sin tu aprobación de un plan exacto. itch.io y los portales son caminos opcionales y, en buena parte, manuales.
Los canales, sus reglas, el calendario y el banco de respuestas están en `difusion.md`; el mapa de todos los canales, en `difusion/MAPA.md`; cómo se creó el juego, en `registro-creacion.md`.

## Una sola vez (la primera vez que publicas)

| Paso | Quién | Detalle |
|---|---|---|
| Cuenta de Cloudflare y proyecto de Pages | Tú | Es el sitio. Con su token de API como secreto (nunca en archivos del proyecto). Pasos exactos en `LEEME-DUENO.md`. |
| Fijar los datos reales del sitio | Ambos | `publicacion/sitio.json`: dirección (`url_base`), `proyecto` y `contacto`. Mientras tengan el valor de ejemplo, la fábrica se niega a publicar. |
| Cuentas de redes (opcional) | Tú | Bluesky, Mastodon, Telegram, Discord, YouTube: una cuenta de bot por canal, declarada como bot. Los secretos van al entorno de GitHub, no al chat. |
| Cobros (solo si usas itch.io o anuncios) | Tú | PayPal o Stripe directo, o cobro por itch.io; AdSense si activas anuncios. Lo fiscal, con tu contador. |

## Por cada juego

| Paso | Quién | Detalle |
|---|---|---|
| Construir y probar | Yo | `python3 fabrica.py todo torre-gelatina` → informe-pruebas.txt, medios y este kit. |
| Agregarlo al sitio | Ambos | Añadir el id a `publicacion/sitio.json → juegos` (si ya hay otro lanzado, respetar la pausa entre lanzamientos). |
| Ver el plan | Yo | `python3 fabrica.py publicar`: muestra cada acción, el texto exacto de cada publicación y una huella del plan. No ejecuta nada. |
| Aprobar | Tú | Un «sí» con la huella del plan que leíste. Si algo del plan cambia, la huella cambia y hay que aprobar de nuevo. |
| Ejecutar | Yo | `python3 fabrica.py publicar --ejecutar --aprobar <huella>`: sitio, aviso a buscadores y publicaciones en los canales que tengan secretos. Cada resultado queda en `publicacion/libro.jsonl`. |
| Probar la página como visitante | Yo | Celular y computadora, con una ventana limpia. |
| Itch.io o portales (opcional) | Ambos | Texto y archivos listos en `ficha-itch.md` y el zip; la página se crea a mano. Con butler: `butler push salida/torre-gelatina/torre-gelatina-web.zip tuusuario/tujuego:html5` y marcar HTML5 en «Edit game». |

## Después del lanzamiento

| Cuándo | Quién | Qué |
|---|---|---|
| Cada 3 días, 2 semanas | Yo | Leer métricas y comentarios; anotar en metricas.csv; proponer respuestas (tú apruebas). |
| Semana 2 | Yo | Parche con lo que repita la gente (error, balance, claridad). Subir la versión y volver a pasar por «publicar»: un parche actualiza el sitio sin volver a publicar en redes. |
| Semana 3-4 | Ambos | Paquete nuevo si hay interés. |
| Semana 4 | Tú | Decidir con datos: seguir, cambiar de enfoque o lanzar el siguiente juego. |

## Reglas para no gastar de más ni de menos

No se lanza el siguiente juego hasta tener 2 a 4 semanas de datos del anterior (la fábrica lo hace cumplir con la pausa entre lanzamientos). Más juegos no traen más jugadores por sí solos; lo que decide es que alguien los encuentre.
