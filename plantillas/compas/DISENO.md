# Diseño de la plantilla «compas»

Estado: v1.0.0, primera versión jugable (la usa `compas-gelatina`).

## Núcleo (declarado en `plantilla.json`)

- Género: ritmo · Verbo: cronometrar · Objetivo: puntaje-maximo · Entrada: toque y teclado · Progresión: puntaje-infinito

## Qué hace el jugador, una y otra vez (una frase)

Toca el carril correcto justo cuando una gota de gelatina llega a la línea, siguiendo la melodía de una canción que se compone sola.

## Por qué es divertido (la tensión o la decisión central)

La tensión es el tiempo: cada gota pide un toque en un instante preciso y la calificación (perfecto, bien, casi) se lee de inmediato, con luces y sonido. La racha sube el multiplicador y también la música (entran la melodía, los platillos y la caja), así que jugar bien se oye mejor; fallar rompe la racha y la canción se aligera. Las gotas salen de la propia melodía, por lo que acertar se siente como tocarla. La decisión central de cada partida es el ánimo de la canción (alegre, tensión o calma), que cambia el tempo y el patrón.

## Referencias y qué mejora esta plantilla frente a cada una

La regla de la casa es que cada juego sea una mejora respecto de lo que lo inspira, no una copia con otro tema.

- «Guitar Hero» / juegos de notas que caen: la canción no es un archivo ni un mapa hecho a mano; el motor la compone en el navegador (semilla por ánimo) y las notas se derivan de su melodía, así que no hay licencias ni descargas y cada ánimo trae su propio patrón. La música gana capas con la racha.
- «Piano Tiles» / ritmo de una mano: tres carriles con tres gelatinas tambor, calificación en tres grados y multiplicador, más ventana de acierto más amplia como opción y panel de accesibilidad (menos movimiento, alto contraste).

## Qué la distingue de las plantillas que ya existen (gelatina, torre)

`gelatina` es acción por oleadas y `torre` es un apilador de un solo toque con timing continuo; `compas` es el primer juego donde el tiempo lo marca una canción: tres carriles, entradas discretas contra una partitura. Es también el primero que usa a fondo los cuatro módulos del motor (accesible, efectos, musica, marca).

## Qué puede cambiar entre juegos de esta plantilla sin que sea una variante

Varía lo que está en `juego.json → parametros`: ánimos y semillas (canciones nuevas), duración (`vueltas`), tamaño de las ventanas de acierto, puntos, escalones del multiplicador, colores y fondo, y los textos. No varía el núcleo: tres carriles, gotas derivadas de la melodía generada y calificación por cercanía al tiempo justo. Un juego que solo cambie los colores o la semilla no es un juego nuevo: va como ánimo o modo dentro de Compás.

## Plan de pruebas automáticas (`prueba.js`)

Con `?demo=1` la canción dura 6 compases, para que la prueba sea corta. Se juega con entradas calculadas a partir de `window.__compas.estado()` (las gotas pendientes con su tiempo y carril):

- Pantalla de inicio, botón Jugar, sello de la marca y arranque de la música a su hora (el motor la reporta sonando).
- Racha de perfectos: 100 puntos cada uno hasta el multiplicador ×2 a los 10 seguidos, con el aviso para lector de pantalla.
- Un acierto «bien» y uno «casi» con los puntos y la calificación que corresponden a su ventana; un toque sin gota cerca (pifia) rompe la racha; una gota que se pasa es un fallo y también la rompe.
- Entradas reales: clic o toque en el carril y teclado (flechas, A S D, barra espaciadora).
- Fin de la canción: tarjeta final, récord guardado por ánimo, sonidos disparados, volver a jugar y cambiar de ánimo (el tempo cambia).
- Ventana de acierto amplia, idiomas (los tres, con el chino dibujado de verdad), récord e idioma tras recargar y `?lang=en`.

Queda para jugadores humanos: la sensación de justicia de las ventanas, la latencia de audio en cada dispositivo (las gotas se alinean con el reloj del juego, no con la salida de sonido) y el gusto por cada ánimo.

## Textos y chino

Todo texto visible va por `X.t()` y existe en español, inglés y chino con las mismas marcas `{n}`. El chino solo usa caracteres de GB2312, y una persona hablante nativa lo revisa antes de publicar.
