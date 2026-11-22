# Diseño de la plantilla «arena»

Estado: **beta** (prototipo jugable para probar con bots; no se publica). Lo que siga diciendo PENDIENTE se decide si la beta se promueve a juego.

## Núcleo (declarado en `plantilla.json`)

- Género: sandbox-creativo · Verbo: dibujar · Objetivo: descubrir

## Qué hace el jugador, una y otra vez (una frase)

Vierte materiales sobre el lienzo y mira cómo caen, se mezclan y se acomodan, buscando combinaciones nuevas.

## Por qué es divertido (la tensión o la decisión central)

Un sandbox sin objetivo suele aburrir; aquí hay una cadena corta de descubrimientos (montaña de arena → barro → estanque → isla de gelatina) y cada uno desbloquea un material, con una pista para el siguiente. La gelatina flota sobre el agua: lo propio de la casa.

## Referencias y qué mejora esta plantilla frente a cada una

- Sandbox de materiales que caen: aquí la libertad tiene un hilo de descubrimientos con pistas y desbloqueos, y la simulación es determinista (mismo orden de vertido, mismo resultado), así que se puede probar y compartir.

## Qué la distingue de las plantillas que ya existen (compas, gelatina, torre)

Ninguna es un sandbox ni usa una rejilla de celdas con reglas locales.

## Qué puede cambiar entre juegos de esta plantilla sin que sea una variante

Los umbrales de cada descubrimiento, el tamaño de la rejilla y, a futuro, más materiales y reglas de mezcla. Un juego que solo cambie colores no es un juego nuevo.

## Plan de pruebas automáticas (`prueba.js`) y pruebas con bots (`bots.js`)

`prueba.js` juega con entradas reales (arrastre y teclado) y comprueba materiales, desbloqueos y descubrimientos con `window.__arena.estado()`. `bots.js` define las políticas: «aleatorio» (¿se descubre algo a ciegas?), «explorador» (sabe qué hacer: demuestra que todo se puede descubrir y cuánto tarda cada paso) y «torpe» (el mismo plan con imprecisión humana). Revisan además que la materia se conserve y que no haya valores imposibles. Lo que un bot no dice (si es divertido) se deja a jugadores humanos.

## Textos y chino

Todo texto visible va por `X.t()` y existe en español, inglés y chino con las mismas marcas `{n}`. El chino solo usa caracteres de GB2312, y una persona hablante nativa lo revisa antes de publicar.
