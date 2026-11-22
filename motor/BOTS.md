# Pruebas con bots: el contrato

Este es el órgano de pruebas con bots del motor (`motor/modulos/bots.js`). Sirve para que algo que **no es una persona** (un bot de la fábrica, un script o una
plataforma externa que simula jugadores) juegue un juego del Taller de forma **reproducible** y **mucho más rápido que el tiempo real**.

## Qué dice un bot y qué no

Dice: si el juego se puede ganar, qué tan ancho es el margen para ganar, qué tan fácil es a ciegas, cuánto tarda cada paso, si se rompe, si se atasca y si es
determinista (misma semilla y mismas acciones, mismo resultado).

**No dice** si a la gente le va a gustar, si es divertido ni cuántos van a venir. Eso lo dicen las visitas (rumbo) y los jugadores. Por eso las banderas de
los bots se muestran junto a cada idea del ranking pero **no cambian su puntaje**: nadie sabe todavía qué peso darles, y habrá que calibrarlas con datos reales
(por ejemplo, ver si los juegos con bandera «trivial» retienen menos que los demás cuando haya visitas suficientes).

## Cómo se activa

1. El juego declara el módulo en `juego.json`: `"motor": ["bots"]`.
2. El juego registra un adaptador con `GGX.bots.registrar({...})` (ver abajo).
3. Quien lo prueba abre la página con `?bot=1` (y opcionalmente `&semilla=N`). **Sin `?bot=1` el módulo está inerte**: una persona normal no ve ni activa nada, y no
   existe `window.__bot`. (Una plataforma que no pueda cambiar la dirección puede fijar `window.__GGX_BOT__ = true` antes de cargar la página.)

## El adaptador que registra el juego

Todo opcional salvo lo marcado. El tiempo es **simulado**: el bot decide cuánto avanza el mundo; el reloj real no cuenta, y el juego no debe usar
`requestAnimationFrame` ni `Date.now()` dentro de `avanzar`.

| Función | Para qué |
| --- | --- |
| `reiniciar(semilla, opciones)` **(obligatorio)** | Empieza un episodio nuevo y determinista. |
| `estado()` **(obligatorio)** | Lo que ve quien juega, como datos simples (JSON). |
| `actuar(accion)` **(obligatorio)** | Aplica una acción; devuelve `{valida: true\|false, motivo}`. |
| `avanzar(ms)` **(obligatorio)** | Hace pasar `ms` milisegundos de juego en pasos fijos. |
| `terminado()` **(obligatorio)** | `{fin, exito, motivo}`. |
| `acciones()` | Describe las acciones posibles, para quien no conoce el juego. |
| `puntaje()` | Un número (por omisión 0). |
| `simular(accion)` | Qué pasaría con esa acción **sin cambiar el estado real**; `{exito, puntaje, ms, …}`. Para bots que planean. |
| `invariantes()` | Lista de reglas rotas (vacía si todo está bien): masa que se conserva, sin NaN, dentro de los límites. |
| `resumen()` | Datos propios del juego para el informe (números sueltos o diccionarios de números). |

## Lo que ofrece la página con `?bot=1`

`window.__bot` con: `info()`, `reiniciar(semilla, opciones)`, `estado()`, `acciones()`, `actuar(a)`, `avanzar(ms)`, `terminado()`, `puntaje()`, `simular(a)`,
`metricas()` y `correr(politica, semilla, opciones)`.

Una plataforma externa puede manejar `reiniciar` / `estado` / `actuar` / `avanzar` paso a paso desde afuera. `correr` juega un episodio entero **dentro de la página**
(mucho más rápido: no hay un viaje de ida y vuelta por decisión). La política recibe `(api, rng, ctx)`, donde `api = {estado, acciones, simular, puntaje, terminado}`,
`rng` es un generador con semilla y `ctx = {paso, ms, dt}` (el número de decisión, los ms de juego transcurridos y los ms entre decisiones); devuelve una acción, `{tipo: 'esperar'}` para dejar pasar el tiempo, o `null` para rendirse.
Opciones: `max_pasos` (2000), `dt` (50 ms de juego entre decisiones), `max_ms` (600000), `cada_invariantes` (25); lo demás se pasa a `reiniciar()`.

El resultado de un episodio es `{semilla, pasos, ms_simulados, exito, terminado, motivo, puntaje, invalidas, violaciones, errores, resumen, politica_info, ms_reales}`.
**`ms_reales` es lo único no reproducible**; todo lo demás es idéntico si la semilla y la política lo son.

## Cómo lo corre la fábrica

```
python3 fabrica.py nuevo ID PLANTILLA --beta       # ficha de prueba: "estado": "beta", declara el módulo «bots»
python3 fabrica.py bots [ID|todos] [--partidas F] [--semilla N] [--politica P] [--sin-fallar]
```

La plantilla define sus políticas en `plantillas/NOMBRE/bots.js`: una política **base** (la más débil: si gana casi siempre, el juego es trivial), una
**solucionadora** (demuestra que se puede ganar) y una **humana** (con imprecisión: su tasa de éxito es la dificultad que sentiría una persona), además de las
escenas, los límites de cada episodio y cuántas partidas jugar con cada política. El informe queda en `metricas/bots/ID.json`.

Banderas (nivel `falla` = algo está roto y el comando termina con error; `aviso` = que lo mire una persona):

- `falla` · `no-determinista`: la misma semilla dio otro resultado.
- `falla` · `fallas-de-pagina`: errores de consola o excepciones en la página.
- `falla` · `errores-del-juego`: el juego o una política lanzó un error durante un episodio.
- `falla` · `violaciones`: se rompió una regla que el juego declara intocable (`invariantes`).
- `falla` · `imposible`: la política solucionadora no ganó ni una vez en una escena.
- `aviso` · `trivial`: la política más débil gana casi siempre (se gana a ciegas).
- `aviso` · `dificil`: el solucionador gana, pero la política humana casi nunca.
- `aviso` · `se-corta`: muchos episodios (de una política que no sea la débil) terminan por límite o abandono en vez de ganar o perder (¿se atasca?).

## Betas

Una **beta** es un juego con `"estado": "beta"` en su ficha: se construye y se prueba con bots (y con `probar`), pero **nunca se publica**. La compuerta de publicación la
frena, el sitio se niega a listarla, el kit y la revisión de lanzamiento la saltan y no cuenta en la comparación de novedad ni en la cola del motor. Su idea sigue en
el ranking de `rumbo`, con una línea que muestra la beta y el resumen de sus bots. Para pasar de beta a juego hay que quitar el estado, completar la ficha (lo que
diga PENDIENTE), correr `todo` y pedir la aprobación de siempre con la huella.

## Si una plataforma externa va a correr las pruebas

Necesita una **dirección a la que pueda llegar** (y, si no puede añadir `?bot=1`, la variable `window.__GGX_BOT__`). Publicar una beta en una dirección pública es
publicar: lo decide Max con su aprobación y su huella, igual que cualquier otra cosa pública. Mientras tanto la fábrica corre estas mismas pruebas en su propio
Chromium, sin red.
