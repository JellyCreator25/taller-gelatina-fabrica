# Ficha de envío a CrazyGames · Jelly Tempo (v1.0.0)

Esto se prepara aquí y lo envía el dueño con su cuenta de desarrollador de CrazyGames: crear la cuenta y aceptar sus términos no lo hace la fábrica. Los requisitos salen de la documentación de CrazyGames leída el 2026-11-18; donde algo no estaba escrito, está en «Lo que no está verificado».

## Qué se sube

- **El juego**: la versión para portal, no la del sitio propio (trae el SDK de CrazyGames y no tiene enlaces de salida). Se arma con `python3 fabrica.py monetizar variantes compas-gelatina crazygames` y queda en `dist/portales/compas-gelatina/crazygames/` (el zip pesa unos 204 KB; el límite inicial es de 50 MB). En el chat te lo mando como archivo.

- **Portada horizontal 16:9 (1920×1080)**: `medios/crazygames/portada-16x9-1920x1080.png` (1756 KB)
- **Portada vertical 2:3 (800×1200)**: `medios/crazygames/portada-2x3-800x1200.png` (824 KB)
- **Portada cuadrada 1:1 (800×800)**: `medios/crazygames/portada-1x1-800x800.png` (575 KB)
- **Video de vista previa horizontal (1080p, 19 s, sin sonido)**: `medios/crazygames/vista-previa-16x9-1920x1080.mp4` (5857 KB)
- **Video de vista previa vertical 2:3 (1080×1620, 19 s, sin sonido)**: `medios/crazygames/vista-previa-2x3-1080x1620.mp4` (4723 KB)

Las portadas y los videos se rehacen con `python3 fabrica.py monetizar envio compas-gelatina` (necesita Chromium y ffmpeg).

## Textos (en inglés, que es lo que exige CrazyGames)

**Título:** Jelly Tempo

**Descripción corta:** Three jelly drums and a song that composes itself: tap each drop right on the line and build up the multiplier. Runs under a minute.

**Controles:** Tap the left, middle or right lane of the screen, click, or use the left, down and right arrow keys (also A, S and D, or the space bar for the middle lane).

**Descripción larga** (se quitó la línea «sin anuncios»: en CrazyGames el juego puede mostrar los anuncios de su SDK):

```
A rhythm game that plays right in your browser, with no downloads or sign-up. Jelly drops fall along the melody of a song and you tap them just as they reach the line, on one of the three jelly drums.

**How it works**

- Three lanes, one per jelly drum: each one carries its own notes of the melody, so as the tune climbs or falls you hop from one drum to the next.
- Each tap is graded perfect, good or almost, depending on how close it was to the exact moment. A drop that slips past counts as a miss and breaks your streak.
- Every ten hits in a row raises the score multiplier, up to ×4.
- You pick the mood of the song (happy, tense or calm). The music is composed in your browser, with no audio files: each mood has its own scale, tempo and melody, and the drops come from that melody.
- The better you play, the more instruments join the song.
- Your best score for each mood is saved on your own device.

**Details**

- Works on phones and computers.
- Wider hit window option and an accessibility panel (reduced motion and high contrast).
- Synthesized sound you can mute with a button.
- Spanish, English and Chinese.

Made with the help of AI (code, graphics, text and sound).
```

**Categorías y etiquetas:** se eligen de la lista del formulario, que solo se ve con la cuenta. Las más cercanas a este juego: ritmo (Rhythm), música (Music), casual. No se marca nada que el juego no sea.

## Requisitos de CrazyGames contra este juego

| Requisito | Estado | Detalle |
|---|---|---|
| Descarga inicial ≤ 50 MB, total ≤ 250 MB con SDK, ≤ 1 500 archivos | Cumple | Un solo archivo `index.html` de unos 204 KB |
| Inglés obligatorio y tomar el idioma del jugador del SDK | Cumple | El juego trae es, en y zh; con el SDK usa su idioma (`user.systemInfo.locale`) y, si no hay, el del navegador o el inglés. Probado con una simulación del SDK |
| Legible entre 800×450 y 1920×1080 en un cuadro 16:9 | Probado con reservas | El escenario es vertical (9:16) y se centra en el cuadro; a 800×450 mide unos 240×425 px y el texto se lee, pero queda pequeño. Un revisor puede pedir ajustes |
| Sin botón propio de pantalla completa | Cumple | El juego no tiene uno |
| Sin promoción de otros juegos o plataformas ni enlaces de salida | Cumple, con una duda | La versión para portal no tiene enlaces (se revisa en cada armado). Sí muestra la insignia «Taller Gelatina» al empezar y en la tarjeta de inicio; no enlaza a nada y no promueve otro juego, pero la regla de marca no está en las páginas leídas |
| Contenido apto para PEGI 12 | Cumple | Sin violencia, sin lenguaje fuerte, sin compras |
| Sin datos personales propios | Cumple | Solo guarda el mejor puntaje y los ajustes en el dispositivo; no pide registro |
| Controles intuitivos | Cumple | Toque o clic en el carril, flechas, A/S/D y barra espaciadora. La lista de teclas restringidas está en sus Quality Guidelines (no leídas) |
| Si trae anuncios, que funcione con ellos desactivados (Basic Launch) | Cumple | Probado: ante `adError` el juego sigue sin trabarse |
| Anuncios solo del SDK, entre niveles, nunca desde botones de navegación | Cumple | Un anuncio al pulsar «Otra canción igual» en la pantalla final; nunca durante la partida ni desde menús. El SDK limita a uno cada 3 minutos |
| Silencio solo mientras suena el anuncio y pausa del juego | Cumple | Probado con una simulación del SDK |
| Full Launch: SDK con `gameplayStart`, y entrar al juego en un clic o menos | Cumple | Se llaman al empezar y terminar la partida. Hoy hay una tarjeta de inicio con el ánimo ya elegido: un clic en «Play» |
| Portadas 1920×1080, 800×1200 y 800×800, sin bordes y sin más texto que el título | Cumple | Generadas por la fábrica con captura real del juego; el único otro texto es el del propio juego dentro de la captura (puntos, «Perfect!») |
| Videos de 15 a 20 s, hasta 50 MB, 1080p horizontal y vertical, sin sonido ni pantallas negras | Cumple | Generados por la fábrica jugando el juego de verdad; se recortan para que no salga la tarjeta de inicio, la insignia ni la cuenta regresiva |

## Lo que sigue (lo hace el dueño)

1. Crear la cuenta de desarrollador de CrazyGames y completar su perfil de pagos (el pago mínimo que reportan terceros es de 100 €, y no se cobra nada hasta el Full Launch).
2. Subir el zip, las portadas y los videos, y pegar los textos de arriba. El portal tiene un entorno de vista previa: conviene probar ahí el juego antes de enviarlo.
3. Pasar la revisión inicial de calidad (Basic Launch). En esa etapa no hay anuncios ni ingresos; el paso a Full Launch lo decide CrazyGames con las métricas del juego.

## Lo que no está verificado

- Los umbrales del paso a Full Launch, el reparto de ingresos y los formatos de imagen y video aceptados: no están en las páginas públicas leídas.
- Si CrazyGames acepta juegos hechos con IA: su documentación pública no trae una regla específica; solo lo dice un tercero. La línea de transparencia va al final de la descripción.
- Si el revisor objeta la insignia del estudio o el escenario vertical, hay que ajustar la versión para portal (se puede apagar la insignia solo ahí).
- La forma exacta de las llamadas del SDK está probada con simulaciones; la prueba real es la vista previa del portal.

## Fuentes

- Requisitos generales: https://docs.crazygames.com/requirements/intro/
- Anuncios: https://docs.crazygames.com/requirements/ads/
- Juego: https://docs.crazygames.com/requirements/gameplay/
- Portadas y videos: https://docs.crazygames.com/requirements/game-covers/
- Preguntas frecuentes: https://docs.crazygames.com/faq/
