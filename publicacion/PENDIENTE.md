# Estado de la fábrica

Lo escribe `python3 fabrica.py ciclo`. No contiene claves ni fechas; lo que sale en el libro está en `publicacion/libro.jsonl`.

## compas-gelatina (v1.0.0)

- Novedad: distinto
- **Fuera del sitio.** Para lanzarlo: agrégalo a `publicacion/sitio.json` → `juegos`, corre `python3 fabrica.py ciclo` y vuelve a leer este archivo.

## guerreros-gelatina (v1.4.0)

- Novedad: distinto
- **Listo para aprobar** (1 acciones pendientes: sitio-propio).
  Lee el plan con `python3 fabrica.py publicar guerreros-gelatina` y, si está bien: `python3 fabrica.py publicar guerreros-gelatina --ejecutar --aprobar ef8a8864d76e24c2`

## torre-gelatina (v1.1.0)

- Novedad: distinto — Riesgo «alto» de ser visto como clon de un juego de fuera (Stack): no se envía a portales.
- **Bloqueado:**
  - ritmo: el último lanzamiento fue el 2026-11-17; la política pide al menos 14 días entre juegos nuevos

## Qué construir después

- No hay ninguna métrica registrada. La fuente automática es Cloudflare Web Analytics (ver LEEME-DUENO.md, «Medir visitas»); lo demás se anota con `python3 fabrica.py metricas anotar`.

**Todavía no hay datos para decidir por métricas.** Hacen falta al menos 2 juegos con 3 semanas completas y 200 vistas del juego; mientras tanto el rumbo se elige explorando: lo que más se aleja de lo que ya hay, con menos riesgo de clon y menor costo.

Evidencia por juego (semanas completas, últimas 8):
- `compas-gelatina`: 0 semana(s), 0 vistas del juego, 0 de la ficha → sin datos todavía
- `guerreros-gelatina`: 0 semana(s), 0 vistas del juego, 0 de la ficha → sin datos todavía
- `torre-gelatina`: 0 semana(s), 0 vistas del juego, 0 de la ficha → sin datos todavía

Recomendación, en orden:
1. `rebote` · Rebote (puzzle de física con gelatina) · puntaje 1.01 · riesgo de clon medio · costo medio
   Por qué: género «puzzle-fisico» no se ha probado; verbo «apuntar» no se ha probado; objetivo «llegar-a-la-meta» no se ha probado. Crearla: `python3 fabrica.py nueva-plantilla NOMBRE --genero puzzle-fisico --verbo apuntar --objetivo llegar-a-la-meta`
2. `arena` · Arena (sandbox de materiales que caen) · puntaje 1.01 · riesgo de clon medio · costo medio
   Por qué: género «sandbox-creativo» no se ha probado; verbo «dibujar» no se ha probado; objetivo «descubrir» no se ha probado. Crearla: `python3 fabrica.py nueva-plantilla NOMBRE --genero sandbox-creativo --verbo dibujar --objetivo descubrir`
3. `colonia` · Colonia (incremental con decisiones) · puntaje 1.00 · riesgo de clon medio · costo medio
   Por qué: género «idle-incremental» no se ha probado; verbo «elegir» no se ha probado; objetivo «construir-algo» no se ha probado. Crearla: `python3 fabrica.py nueva-plantilla NOMBRE --genero idle-incremental --verbo elegir --objetivo construir-algo`

En espera (algo que solo una persona puede resolver):
- `trazos`: Revisión del contenido en chino por una persona hablante nativa: sin ella el juego no debe salir.

Excluidas: `compas` (detalle: `python3 fabrica.py rumbo --detalle`).

Recomendar no es lanzar: un juego nuevo sigue sujeto a la revisión de novedad, a la pausa entre lanzamientos y a tu aprobación con la huella.

## Motor: calidad y qué sigue

Techo del motor hoy: nivel 5 de 5. Mejor juego publicado: nivel 2. Pruebas del motor: al día.

Niveles: 1 Base · 2 Con sonido · 3 Con jugo y accesible · 4 Con música · 5 Con marca

- compas-gelatina: nivel 5 (Con marca)
- guerreros-gelatina: nivel 2 (Con sonido) — falta: Módulo «accesible»: menos movimiento, alto contraste y anuncios para lector de pantalla (declarado en «motor» y llamado por el código del juego).
- torre-gelatina: nivel 2 (Con sonido) — falta: Módulo «accesible»: menos movimiento, alto contraste y anuncios para lector de pantalla (declarado en «motor» y llamado por el código del juego).

Lo que sigue para el motor:
1. Actualizar «guerreros-gelatina» del nivel 2 al 5 — Una versión nueva con lo que le falta (accesible, efectos, musica, marca) mejora el juego y da una novedad que anunciar.

## Monetización: qué falta para cobrar

Hoy no se muestra ningún anuncio ni se cobra nada: todas las rutas están apagadas.

### Portales con revenue share (apagada)
- Listo: módulo «anuncios» v1.0.0 con 25 pruebas del motor vigentes
- Listo: juegos con anuncios en cortes naturales: compas-gelatina
- Listo: SDK confirmado en la documentación del portal: crazygames
- Listo: paquete de envío a CrazyGames (ficha, tres portadas y dos videos de vista previa): compas-gelatina (salida/compas-gelatina/kit/ficha-crazygames.md)
- Falta (dueño): crear la cuenta de desarrollador del portal (primero CrazyGames) y fijar cómo cobrar; el portal pide los datos de pago antes de recibir un juego
- Falta (dueño): subir el zip de la versión para portal, las portadas y los videos ya preparados y pegar los textos de la ficha (el zip lo mando por el chat; se rearma con `python3 fabrica.py monetizar variantes ID crazygames`)

### AdSense en el sitio propio (apagada)
- Listo: módulo «anuncios» v1.0.0 con 25 pruebas del motor vigentes
- Listo: juegos con anuncios en cortes naturales: compas-gelatina
- Falta (fábrica): el sitio muestra 2 juego(s); con pocos juegos AdSense puede rechazarlo por contenido escaso
- Falta (dueño): un dominio propio: hoy el sitio vive en taller-gelatina.pages.dev, y los reportes de editores indican que AdSense no aprueba subdominios gratuitos
- Falta (dueño): cuenta de AdSense aprobada para ese dominio, la solicitud aparte de «H5 Games Ads» y el identificador pub-… en publicacion/sitio.json
- Falta (dueño): configurar en la cuenta de AdSense el mensaje de consentimiento (obligatorio para tráfico del EEE, el Reino Unido y Suiza) y marcar consentimiento_listo en la política
- Falta (dueño): decidir la analítica de visitas (Cloudflare Web Analytics): sin ella no hay forma de saber cuántas sesiones hay ni de medir ingresos por visita

### Donaciones y pago libre (apagada)
- Listo: el botón de apoyo ya existe en el motor y se muestra solo cuando hay enlace
- Falta (dueño): crear la cuenta en un servicio de propinas o pago libre y darme el enlace (lo pongo en `apoyo_url` de cada juego y se publica cada juego con tu aprobación)

### Cuentas con la fórmula (supuestos en monetizacion/politica.json)

| Sesiones por día | eCPM supuesto | Por mes (US$) | Días para juntar 50 (el pago mínimo más bajo de los portales) |
|---|---|---|---|
| 100 | US$2 | 8.40 | 179 |
| 100 | US$5 | 21.00 | 71 |
| 1,000 | US$2 | 84.00 | 18 |
| 1,000 | US$5 | 210.00 | 7 |
| 10,000 | US$2 | 840.00 | 2 |
| 10,000 | US$5 | 2,100.00 | 1 |


## Bluesky: qué ha funcionado

1 publicación(es) medida(s). Puntaje = likes + 3 × reposts + 2 × respuestas + 2 × citas.

- Más movida: «guerreros-gelatina:1.4.0:bluesky:post» (sin formato, ?) → 3 (3 likes, 0 reposts, 0 respuestas, 0 citas, a 24 h)

Todavía son pocas (1 de 8): no saco conclusiones sobre formatos, solo las anoto.

Canales y qué hace cada uno solo: `difusion/MAPA.md`. Canales activos hoy: sitio-propio, indexnow, bluesky.
