# Diseño de la plantilla «rebote»

Estado: **beta** (prototipo jugable para probar con bots; no se publica). Lo que sigue diciendo PENDIENTE se decide si la beta se promueve a juego.

## Núcleo (declarado en `plantilla.json`)

- Género: puzzle-fisico · Verbo: apuntar · Objetivo: llegar-a-la-meta

## Qué hace el jugador, una y otra vez (una frase)

Apunta y lanza una gelatina que rebota para llegar a la meta con el menor número de tiros.

## Por qué es divertido (la tensión o la decisión central)

Cada material cambia el rebote (gelatina firme, trampolín que da energía, miel que detiene): el jugador planea una trayectoria con varios rebotes y la ve cumplirse o fallar por poco. La vista previa del tiro muestra solo el primer tramo, para que el resto sea ensayo y descubrimiento.

## Referencias y qué mejora esta plantilla frente a cada una

- Juegos de lanzamiento con resortera: la física es suave y de pasos fijos (determinista), así que el mismo tiro da siempre el mismo resultado: el puzzle se razona y se comparte; no depende de la suerte.

## Qué la distingue de las plantillas que ya existen (compas, gelatina, torre)

Ninguna usa física de trayectoria ni apuntar y disparar: Compás es ritmo, Guerreros Gelatina es estrategia en tiempo real, Torre es apilar con tiempo.

## Qué puede cambiar entre juegos de esta plantilla sin que sea una variante

Los niveles (`parametros.niveles`: lanzador, meta y bloques de tres materiales), la gravedad, el radio y el número de tiros. Un juego que solo cambie colores no es un juego nuevo.

## Plan de pruebas automáticas (`prueba.js`) y pruebas con bots (`bots.js`)

`prueba.js` juega con entradas reales (teclado y arrastre) y comprueba fases, tiros y estrellas con `window.__rebote.estado()`. `bots.js` define las políticas: «aleatorio» (mide qué tan fácil es acertar a ciegas), «oraculo» (busca por simulación un tiro que gane: demuestra que cada nivel se puede resolver y con cuántos tiros) y «novato» (el tiro del oráculo con el temblor de una mano humana: mide la tolerancia del nivel). Lo que un bot no dice (si es divertido) se deja a jugadores humanos.

## Textos y chino

Todo texto visible va por `X.t()` y existe en español, inglés y chino con las mismas marcas `{n}`. El chino solo usa caracteres de GB2312, y una persona hablante nativa lo revisa antes de publicar.
