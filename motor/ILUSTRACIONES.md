# Ilustraciones de caricatura

Las imágenes de las publicaciones ya no son capturas del juego: son **escenas de caricatura** con nuestros propios personajes (los sprites reales del juego, dibujados con su mismo código) sobre fondos, efectos y atrezo dibujados en SVG, con el trazo grueso y oscuro de la marca.
Max aprobó este estilo el 23 de noviembre de 2026 tras ver seis muestras, y pidió que **el arte siga mejorando poco a poco** (más trazo, más animación, más técnicas). Esta página es esa hoja de ruta.

## Cómo se usa

```
node herramientas/ilustraciones.js                 # dibuja todas las escenas en contenido/imagenes/ilustracion-<id>.png
node herramientas/ilustraciones.js medusa-mirada   # solo esa
node herramientas/ilustraciones.js --lista         # ids y texto alternativo (es / en)
node herramientas/ilustraciones.js --salida DIR    # a otra carpeta, para muestras
node herramientas/ilustraciones.js --verificar     # revisa las escenas sin abrir navegador (lo corren las pruebas)
```

Necesita Playwright y `salida/guerreros-gelatina/index.html` ya construido. Cada imagen sale igual cada vez (azar con semilla, reloj del juego fijo).

## Cómo está hecho

- `herramientas/ilustraciones.js`: el compositor. Dibuja cada personaje una sola vez (`arte.js` → `dibujarSprites`), lo coloca con posición, radio, giro, filtro y contorno, y lo mezcla con las capas SVG, de atrás hacia adelante.
- `herramientas/ilustraciones/lib.js`: la biblioteca de piezas (fondos, efectos como impacto, rayo, ondas, llamas, nube de polvo; atrezo como trofeo, carrito, reloj, laptop, pizza…).
- `herramientas/ilustraciones/escenas.js`: **las escenas son datos**: un id, el texto alternativo en español y en inglés, y una función que devuelve las capas. Agregar una escena es agregar un bloque ahí.
- El contorno oscuro de los personajes se hace con un filtro SVG que ignora el brillo translúcido de las varitas.

## Reglas del estilo (nivel 1)

1. **Sin texto escrito en la imagen**, salvo cifras (como «-100%»): la misma imagen sirve en español, inglés y chino. `--verificar` lo comprueba.
2. **Alt propio de cada escena**, en español («Ilustración de caricatura: …») y en inglés («Cartoon illustration: …»); el calendario toma el del idioma de la publicación.
3. **Personajes del juego** (sin la mascota nueva de la marca hasta que termine la búsqueda de anterioridades del IMPI).
4. Una escena por tema del texto; solo se reutiliza entre la versión en español y la inglesa de un mismo asunto.
5. Cambiar la imagen o el alt de una publicación **cambia su huella**: vuelve a pedir la aprobación de Max. Nada se aprueba solo.

## Hoja de ruta (un escalón a la vez, dentro del paso semanal de mejora del motor)

| Nivel | Qué suma | Qué hace falta |
|---|---|---|
| 1 (hoy, estilo 1) | Imágenes fijas: sprites del juego + SVG con contorno | — |
| 2 | **Más trazo y detalle**: sombreado de color por zonas, textura de puntos, líneas de acción, expresiones (ojos y bocas distintos según la escena), accesorios (corona, capa, antifaz), fondos con capas de profundidad | Variantes de cara y accesorios en el dibujo del personaje (en la plantilla o como capa encima); mirar cada escena antes de cambiarla |
| 3 | **Animación corta**: cuadros desde un reloj fijo, empaquetados como GIF, WebP animado o video corto | Elegir el formato que cada canal acepte, ampliar el adaptador de publicación (hoy solo sube imágenes), y que la huella incluya el medio |
| 4 | **Más técnicas**: cámara (zoom y paneo), partículas, sombras suaves, paletas por temporada, onomatopeyas por idioma (versiones con texto aparte de las sin texto) | Una variante por idioma cuando lleve texto |
| 5 | **Poses propias**: extremidades que giran, aplastar y estirar, más personajes y la mascota nueva | Cerrar la búsqueda del IMPI y el estudio de marca |

Cada escalón se prueba sobre dos o tres escenas, se muestra a Max y, si le gusta, se aplica al resto. `ESTILO` en `ilustraciones.js` sube cuando el arte cambia de nivel.
