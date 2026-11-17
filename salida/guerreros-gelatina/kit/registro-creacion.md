# Registro de creación · Guerreros Gelatina (v1.4.0)

Para qué sirve: algunas plataformas piden poder enseñar cómo se hizo un juego con IA (Poki pide las herramientas usadas y, si lo solicitan, un resumen del proceso, los prompts y las iteraciones), e itch.io no acepta proyectos con poca intervención humana. Este archivo deja constancia, con hechos, de quién decidió qué. Se mantiene al día con cada versión. Dónde queda la línea lo decide cada plataforma, no este archivo.

Estado: borrador redactado por Claude a partir de la conversación de creación. El dueño lo revisa y lo corrige antes de enseñárselo a cualquier plataforma.

## Herramientas

- Claude (Anthropic): programación, gráficos vectoriales, textos y sonido sintetizado del juego, y sus pruebas automáticas.

## Qué se hizo con IA

- Código: con IA
- Gráficos: con IA
- Texto: con IA
- Sonido: con IA

## Decisiones del dueño

- Pidió un juego gratis de navegador, sin descargas, de los que se encuentran en rincones poco conocidos de internet y no solo en itch.io; descartó las opciones que ya conocía.
- Orientó la búsqueda: le encantó Battle Draw de Neal.fun y aclaró que el tipo de juego que le interesa es como Totally Accurate Battle Simulator.
- Pidió que el juego mejorara a sus referencias («siempre el punto deberá ser un upgrade») e incluyera personajes célebres con poderes: de ahí las 8 Leyendas.
- Pidió dejar el código abierto para poder añadir DLC y parchar con facilidad: de ahí la API abierta y los paquetes.
- Pidió ver cómo se veía el juego durante las pruebas, para seguir el avance.
- Pidió pensar en monetizarlo y construir una fábrica que genere y prepare juegos; eligió «varios géneros» y que Claude actúe como creador y distribuidor, con su intervención al mínimo.

## Decisiones de Claude dentro de esas instrucciones

- El diseño concreto de cada Leyenda y de su poder, el balance, el estilo visual de la gelatina, el sonido sintetizado y las pruebas.

## Cómo se prueba

- Pruebas automáticas en un navegador real (escritorio y celular simulado): `salida/guerreros-gelatina/informe-pruebas.txt`.
- Las pruebas demuestran que el juego funciona, no que sea divertido: eso lo dicen los jugadores.

## Qué falta registrar

- Las decisiones nuevas del dueño sobre este juego (cambios pedidos, ideas aceptadas o rechazadas) se añaden aquí cuando ocurran, con la fecha.
