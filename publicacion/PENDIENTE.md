# Estado de la fábrica

Lo escribe `python3 fabrica.py ciclo`. No contiene claves ni fechas; lo que sale en el libro está en `publicacion/libro.jsonl`.

## guerreros-gelatina (v1.4.0)

- Novedad: distinto
- Al día: todo lo del plan ya salió.

## torre-gelatina (v1.1.0)

- Novedad: distinto — Riesgo «alto» de ser visto como clon de un juego de fuera (Stack): no se envía a portales.
- **Bloqueado:**
  - ritmo: el último lanzamiento fue el 2026-11-17; la política pide al menos 14 días entre juegos nuevos

## Qué construir después

- No hay ninguna métrica registrada. La fuente automática es Cloudflare Web Analytics (ver LEEME-DUENO.md, «Medir visitas»); lo demás se anota con `python3 fabrica.py metricas anotar`.

**Todavía no hay datos para decidir por métricas.** Hacen falta al menos 2 juegos con 3 semanas completas y 200 vistas del juego; mientras tanto el rumbo se elige explorando: lo que más se aleja de lo que ya hay, con menos riesgo de clon y menor costo.

Evidencia por juego (semanas completas, últimas 8):
- `guerreros-gelatina`: 0 semana(s), 0 vistas del juego, 0 de la ficha → sin datos todavía
- `torre-gelatina`: 0 semana(s), 0 vistas del juego, 0 de la ficha → sin datos todavía

Recomendación, en orden:
1. `compas` · Compás (ritmo de un botón con sonido sintetizado) · puntaje 1.12 · riesgo de clon medio · costo bajo
   Por qué: género «ritmo» no se ha probado; verbo «cronometrar» no se ha probado; objetivo «puntaje-maximo» no se ha probado. Crearla: `python3 fabrica.py nueva-plantilla NOMBRE --genero ritmo --verbo cronometrar --objetivo puntaje-maximo`
2. `rebote` · Rebote (puzzle de física con gelatina) · puntaje 1.01 · riesgo de clon medio · costo medio
   Por qué: género «puzzle-fisico» no se ha probado; verbo «apuntar» no se ha probado; objetivo «llegar-a-la-meta» no se ha probado. Crearla: `python3 fabrica.py nueva-plantilla NOMBRE --genero puzzle-fisico --verbo apuntar --objetivo llegar-a-la-meta`
3. `arena` · Arena (sandbox de materiales que caen) · puntaje 1.01 · riesgo de clon medio · costo medio
   Por qué: género «sandbox-creativo» no se ha probado; verbo «dibujar» no se ha probado; objetivo «descubrir» no se ha probado. Crearla: `python3 fabrica.py nueva-plantilla NOMBRE --genero sandbox-creativo --verbo dibujar --objetivo descubrir`

En espera (algo que solo una persona puede resolver):
- `trazos`: Revisión del contenido en chino por una persona hablante nativa: sin ella el juego no debe salir.

Recomendar no es lanzar: un juego nuevo sigue sujeto a la revisión de novedad, a la pausa entre lanzamientos y a tu aprobación con la huella.

## Motor: calidad y qué sigue

Techo del motor hoy: nivel 4 de 5. Mejor juego publicado: nivel 2. Pruebas del motor: al día.

Niveles: 1 Base · 2 Con sonido · 3 Con jugo y accesible · 4 Con música · 5 Con marca

- guerreros-gelatina: nivel 2 (Con sonido) — falta: Módulo «accesible»: menos movimiento, alto contraste y anuncios para lector de pantalla (declarado en «motor» y llamado por el código del juego).
- torre-gelatina: nivel 2 (Con sonido) — falta: Módulo «accesible»: menos movimiento, alto contraste y anuncios para lector de pantalla (declarado en «motor» y llamado por el código del juego).

Lo que sigue para el motor:
1. Construir el módulo «marca» (nivel 5) — Convierte la gelatina en insignia: cualquiera reconoce un juego del Taller en los primeros segundos (decisión del dueño, 17 nov).
2. Actualizar «guerreros-gelatina» del nivel 2 al 4 — Una versión nueva con lo que le falta (accesible, efectos, musica) mejora el juego y da una novedad que anunciar.

## Bluesky: qué ha funcionado

Todavía no hay publicaciones medidas: se miden a las 24 horas y a los 3 días de salir.

Canales y qué hace cada uno solo: `difusion/MAPA.md`. Canales activos hoy: sitio-propio, indexnow, bluesky.
