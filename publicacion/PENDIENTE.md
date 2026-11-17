# Estado de la fábrica

Lo escribe `python3 fabrica.py ciclo`. No contiene claves ni fechas; lo que sale en el libro está en `publicacion/libro.jsonl`.

## guerreros-gelatina (v1.4.0)

- Novedad: distinto
- **Listo para aprobar** (2 acciones pendientes: indexnow, sitio-propio).
  Lee el plan con `python3 fabrica.py publicar guerreros-gelatina` y, si está bien: `python3 fabrica.py publicar guerreros-gelatina --ejecutar --aprobar 1134151cdd93e93a`

## torre-gelatina (v1.1.0)

- Novedad: distinto — Riesgo «alto» de ser visto como clon de un juego de fuera (Stack): no se envía a portales.
- **Listo para aprobar** (2 acciones pendientes: indexnow, sitio-propio).
  Lee el plan con `python3 fabrica.py publicar torre-gelatina` y, si está bien: `python3 fabrica.py publicar torre-gelatina --ejecutar --aprobar 9b224091b5246ea0`

## Qué construir después

- `trazos` · Trazos (puzzle de palabras y caracteres en tres idiomas) · puzzle-palabras / conectar / aprender · riesgo de clon bajo. Crearla: `python3 fabrica.py nueva-plantilla NOMBRE --genero puzzle-palabras --verbo conectar --objetivo aprender`
- `arena` · Arena (sandbox de materiales que caen) · sandbox-creativo / dibujar / descubrir · riesgo de clon medio. Crearla: `python3 fabrica.py nueva-plantilla NOMBRE --genero sandbox-creativo --verbo dibujar --objetivo descubrir`
- `compas` · Compás (ritmo de un botón con sonido sintetizado) · ritmo / cronometrar / puntaje-maximo · riesgo de clon medio. Crearla: `python3 fabrica.py nueva-plantilla NOMBRE --genero ritmo --verbo cronometrar --objetivo puntaje-maximo`

Canales y qué hace cada uno solo: `difusion/MAPA.md`. Canales activos hoy: sitio-propio, indexnow.
