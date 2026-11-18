# La marca: la Gelatina como insignia

> v1.1 (18 de noviembre de 2026). Nació de tu pedido de que «la gelatina sea una insignia y no solo el tema». El 18 de noviembre decidiste la promesa, que la Gelatina siga sin nombre propio por ahora y que Guerreros reciba una actualización de calidad; todo eso está registrado abajo. Lo que sigue diciendo «Propuesta» espera tu visto bueno.

## La idea

Hasta ahora la gelatina era **el tema**: gelatinas que pelean, bloques de gelatina que se apilan. Un tema se acaba cuando el juego cambia. Una **insignia** no: es lo que firma cada juego, sea del género que sea. La regla es esta:

> Los juegos del Taller pueden tratar de cualquier cosa. Lo que los hace del Taller es la Gelatina que aparece en ellos.

Un juego de ritmo, un puzzle o un juego de cartas pueden no tener ninguna gelatina en su mecánica y aun así abrir con ella, llevar su distintivo y tener una en pantalla con algún papel. Así la marca crece con el catálogo en lugar de depender del primer juego.

**Promesa (decidida el 18 de noviembre):** *Juegos chiquitos, gratis y con delirios de grandeza.* Es un híbrido de dos propuestas: la voz del personaje (`difusion/voz.md`) y lo que ya funciona en las redes (232 KB contra 212 GB). Es una línea para el perfil y el sitio; no se pone dentro de los juegos. Ya está en la biografía y el banner de Bluesky (`difusion/perfiles/perfiles.md`, en español, inglés y chino); la cuenta la administra la fábrica, que los aplica con `python3 fabrica.py configurar bluesky-perfil`. En el sitio entrará con el próximo plan del sitio, para que la veas en su huella antes de que salga.

## Los elementos

| Elemento | Qué es | Dónde vive |
|---|---|---|
| **Emblema** | La Gelatina: domo con base ancha, brillo grande arriba a la izquierda con su puntito, dos ojos grandes con destello. Cuatro versiones: verde (la de casa), rosa, amarilla y de una sola tinta | `marca/*.svg`, dibujado una sola vez en `herramientas/marca.py` |
| **Sello** | Al pulsar «Jugar», la Gelatina cae, se aplasta y saluda con el nombre del Taller (≈1,4 s). Un toque o una tecla lo salta; una vez por visita; con «reducir movimiento» no se anima | `GGX.marca.sello()` (módulo `marca` del motor) |
| **Blup** | El sonido de marca: dos gotas de tono, una sube y otra se asienta. Suena con el aplastón y respeta el silencio del juego | `GGX.marca.blup()` |
| **Distintivo** | El emblema chico, con el nombre si hace falta, para una esquina o un menú. No es enlace ni pide nada | `GGX.marca.distintivo()` |
| **Firma** | En cada juego aparece una Gelatina con un papel propio: en Guerreros son las unidades, en Torre los bloques. En un juego de ritmo podría ser quien marca el compás. Se anota en `juego.json → creacion.decisiones_claude` | Decisión de diseño de cada juego |
| **Voz** | Optimista, dramática por cosas chiquitas, con delirios de grandeza y mucha ternura; se ríe de sí misma, nunca de la gente | `difusion/voz.md` |

**Colores.** Verde de la casa `#15804f` / `#6fe0a6`; rosa `#c2337a` (el del nombre y los titulares); amarilla `#e39a00`; tinta `#14251b`; fondo crema `#fbf8f1` con un velo rosa. **Tipografías.** Fredoka para nombres y titulares, Nunito Sans para el texto (ya vienen incrustadas en cada juego).

**El nombre.** Los juegos se llaman «X Gelatina» (Guerreros Gelatina, Torre Gelatina). Es parte de la marca: el catálogo se lee como una familia. Un juego con otro nombre es una excepción que se decide, no un descuido.

## Cómo se usa (reglas)

1. El color de la Gelatina de un juego se elige entre los tres; la silueta, el brillo y los ojos no cambian nunca. Eso es lo que la hace reconocible con otro color.
2. No se estira, no se gira, no se le cambia la cara ni se le pone texto encima. Zona libre alrededor: el ancho de un ojo. Tamaño mínimo: 16 px.
3. Sobre fondos de color o fotografías se usa la versión de una tinta, en el color del texto que la rodea.
4. El sello nunca retrasa el juego más de lo que dura y siempre se puede saltar. La marca no estorba a quien ya la conoce.
5. La Gelatina no promete lo que el juego no da: nada de «el mejor» ni de cifras sin ficha. La gracia está en el cariño y en los datos exactos.

## Dónde ya está y dónde falta

**Ya está:** el emblema en cuatro versiones; el módulo `marca` del motor, con 16 pruebas en un navegador real (incluido que se salta, que respeta el silencio y que con menos movimiento no se anima); el ícono del sitio (ahora es la Gelatina); el avatar y el banner de las cuentas, que ya usaban esta misma Gelatina; el nivel 5 de la escalera de calidad, «Con marca».

**Falta (en la cola del motor, `python3 fabrica.py motor`):**

- **Compás** (el tercer juego) será el primero en abrir con el sello y llevar distintivo: lo exige la escalera, que pide a cada juego nuevo un nivel más que el mejor ya publicado.
- **Guerreros** (decidido el 18 de noviembre): la versión 1.5.0 con sello, efectos, música y accesibilidad ya está preparada y probada (nivel 5) en la rama `guerreros-1.5.0`, aparte de lo publicado; se une y se publica después de Compás, con plan nuevo y tu aprobación de su huella. **Torre** sigue sin cambios; una actualización suya sería otra decisión tuya.
- **Portadas y tarjetas** con el distintivo: cambian piezas que ya están aprobadas o publicadas, así que esperan tu visto bueno.

## Decisiones

1. **Promesa:** «Juegos chiquitos, gratis y con delirios de grandeza.» (18 de noviembre).
2. **Nombre de la Gelatina:** sin nombre propio por ahora («la Gelatina»). Se retoma después del lanzamiento de Compás, cuando haya aparecido en tres juegos. Un nombre ayudaría a las redes (podría tener opiniones, cumpleaños, rivales), pero es un compromiso largo y hay que revisarlo contra conflictos: «Blup», que era la idea natural por el sonido de la marca, se parece a «Blupi», una mascota que ya existe.
3. **Guerreros Gelatina v1.5.0:** aprobada para prepararse y publicarse después de Compás.
