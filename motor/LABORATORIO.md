# Laboratorio de betas: el contrato

Este es el órgano del motor para **probar una beta de forma aislada, extensa y comparable** (`herramientas/laboratorio.py` arma y lee el experimento; `herramientas/laboratorio.js`
lo corre en un Chromium real). Sirve para una beta de juego, pero también para una página, un texto, un cambio de interfaz o una idea de mecánica: lo que se pueda abrir en un
navegador desde un archivo local. Convive con el órgano de bots (`motor/BOTS.md`): los bots dicen si un juego se puede ganar; el laboratorio dice **cómo lo vivirían
personas con condiciones y temples distintos** y qué se rompe en cada aparato.

## Qué dice y qué no

Dice dónde se traba, se confunde o se rinde alguien con *esas* condiciones (aparato, entrada, idioma, ritmo, paciencia, puntería, interrupciones, red, CPU) y *ese* temple;
cuánto tarda en hacer lo primero; qué errores, qué problemas de accesibilidad y qué diferencia hay entre dos variantes o entre dos versiones.

**No dice** si a la gente le va a gustar ni cuántos van a venir. Los perfiles son **arquetipos de condiciones y de conducta** (la mamá ocupada, el cartero en ruta,
quien solo usa teclado), no personas ni una muestra de la población: sirven para encontrar fricción, no para medir demanda. Por eso las banderas se muestran pero **no
cambian el puntaje del ranking** de `rumbo`, igual que las de los bots. Tampoco sustituyen a una persona real: si una prueba pasa, solo se sabe que esos arquetipos no se
trabaron.

## Comandos

```
python3 fabrica.py laboratorio listar                      # experimentos que hay
python3 fabrica.py laboratorio perfiles                    # catálogo de perfiles
python3 fabrica.py laboratorio validar [ID|todos]          # revisa el experimento sin correr nada
python3 fabrica.py laboratorio correr ID [--partidas F] [--semilla N] [--perfil a,b] [--prueba a,b] [--sin-fallar] [--sin-guardar]
python3 fabrica.py laboratorio comparar ID [--con RUTA]    # el último informe contra el anterior (o contra un archivo)
```

`correr` construye antes el juego (si el objeto es un juego), corre todas las celdas, escribe el informe, lo compara con el guardado antes y **sale con error si hay una
bandera de falla** (`--sin-fallar` lo evita). Con `--perfil` o `--prueba` el informe es parcial y **no se guarda**. `--partidas F` multiplica el número de sesiones
(0.25 para una pasada rápida, 4 para estrechar los intervalos). Una pasada completa de los experimentos que trae la fábrica tarda unos minutos.

## El experimento (`laboratorio/experimentos/ID.json`, el nombre es el `id`)

| Clave | Qué es |
| --- | --- |
| `formato` | `1`. |
| `id`, `titulo` | Minúsculas, números y guiones; título legible. |
| `pregunta` | **Obligatoria** (≥ 8 caracteres): qué se quiere saber. Un experimento sin pregunta no se acepta: sin ella los números no sirven para decidir nada. |
| `objeto` | `{"juego": ID}` (usa `salida/ID/index.html`) o `{"html": "ruta/dentro/del/repo.html"}`. Siempre un archivo local. |
| `variantes` | Lista; **la primera es el control**. Cada una: `id`, `nota`, `consulta` (query string), `html` (otra página), `juego` (objeto que se mezcla en `window.JUEGO`: `parametros`, `textos`…), `css` (se inyecta) y `reemplazos` (`[{"buscar","poner","veces"}]`; si no encuentra el texto, la validación falla en voz alta). |
| `perfiles` | Ids del catálogo o perfiles completos en línea. |
| `pruebas` | Lista de pruebas: `auditoria`, `guion` o `bots` (abajo). |
| `umbrales` | `abandono` (0.30) y `bloqueo` (0.50), fracciones. |
| `semilla_base` | Entero (1000 por omisión). |

Una variante que **no se aplica** (la página no lee `window.JUEGO`, un reemplazo que no cambió nada) se denuncia con `error-interno`: un A/B que no cambia nada no puede
leerse como «no hay diferencia».

### Pruebas

- **`auditoria`**: abre la página en cada perfil, la observa `observar_ms` (3000 por omisión, tiempo simulado) y revisa accesibilidad y uso en pantalla. Una sesión por perfil y variante.
- **`guion`**: una persona que sigue los `pasos` en `semillas` sesiones (5 por omisión; cada semilla cambia el azar de la página y el de la persona).
- **`bots`**: reutiliza el órgano de bots sobre el juego (una celda por variante y perfil). Las políticas reciben el temblor y el ritmo del perfil (`ctx.perfil`, ver `BOTS.md`), pero **solo la política humana** actúa más lento (`dt × ritmo`) y más temblorosa: la débil y la solucionadora miden el juego (¿se gana a ciegas?, ¿se puede ganar?) y no cambian de cadencia según el perfil. `partidas` es el factor de partidas.

### Gramática de los pasos

Cada paso lleva **exactamente un verbo**, más las claves comunes `id`, `embudo`, `pausa`, `paciencia`, `opcional` y `si`.

| Verbo | Forma | Qué hace |
| --- | --- | --- |
| `esperar` | selector | Espera a que el elemento exista, se vea y esté habilitado (la paciencia del perfil manda). |
| `esperar_hasta` | expresión JS | Espera a que sea verdadera; `max_ms`, `falla_si_no` (si no, es falla de la beta y no abandono). |
| `tocar` | punto | Toque o clic con la puntería del perfil (temblor, un reintento si falla y, si sigue fallando, abandono `punteria`). Si el elemento está tapado, abandono `cubierto`. |
| `arrastrar` | `{desde, hasta, pasos}` | Presiona, mueve y suelta. El destino se acota a la pantalla. |
| `mantener` | `{en, ms}` | Presiona y sostiene. |
| `tecla` | tecla (`veces`: entero o `{min,max}`) | Teclea. El azar de `veces` sale de la semilla de la sesión. |
| `escribir` | `{selector, texto}` | Toca el campo y teclea. |
| `leer` | `{id, js}` | Guarda un dato de la página (`id` en minúsculas y guion bajo) para el informe: mediana si es número, reparto si es texto o sí/no. |
| `verificar` | `{js, mensaje, espera}` | Si no se cumple, **falla la beta** (`verificacion-fallida`): es un error del juego, no de la persona. |
| `pasar` | ms | Deja pasar tiempo simulado (se multiplica por el ritmo del perfil). |
| `interrumpir` | ms | La página queda oculta ese tiempo y vuelve (`visibilitychange`). |
| `repetir` | `{hasta, maximo, pasos}` | Repite los pasos hasta que `hasta` sea verdadero o llegue al máximo. |

Un **punto** es un selector o `{selector, x, y, js, ref}`: `x` e `y` son fracciones de la caja del elemento; `js` devuelve `{x, y}` en un sistema de coordenadas de tamaño
`ref` (para apuntar a algo dibujado en un canvas, por ejemplo la bola de Rebote).

`embudo` marca la etapa cuando el paso se cumple (el embudo cuenta cuántas sesiones llegaron a cada etapa y cuándo, en tiempo simulado). `si` salta el paso para quien no
cumple `{entrada, dispositivo}`. **Un perfil de teclado que llega a un `tocar`, `arrastrar` o `mantener` sin `si` abandona con `requiere-puntero`**: así se descubre lo que no
tiene alternativa de teclado; quien escribe un guion debe poner el camino de teclado con `si`.

## Perfiles (`laboratorio/perfiles.json`)

Cada perfil: `id`, `nombre`, `descripcion`, `dispositivo` (`ancho`, `alto`, `escala`, `tactil`, `movil`), `entrada` (`raton`, `tactil` o `teclado`; se deduce del dispositivo),
`idioma`, `zona`, `ambiente` (`tema`, `movimiento_reducido`), `cpu` (1 normal a 20 muy lenta), `red` (`latencia_ms`, `bajada_kbps`) y `conducta`:
`ritmo` (multiplica las pausas), `reaccion_ms` (antes de cada acción), `paciencia_ms` (espera por algo), `paciencia_carga_ms` (cuánto aguanta una carga),
`temblor` y `punteria_px` (error al apuntar) e `interrupciones` (`[{"tras_acciones", "ms"}]`). Lo que falta toma el valor base. Hoy hay doce, de «escritorio rápido» a
«mamá ocupada» (ritmo apurado, temblor alto, la interrumpen 20 s tras dos acciones) y «cartero en ruta» (3G, interrupciones frecuentes).

## Cómo se aísla cada sesión

1. **Contexto nuevo por celda**: sin cookies, almacenamiento, caché ni service workers. Se comprueba al abrir; si no está vacío, `contexto-sucio` (falla).
2. **Red cortada**: un servidor local en `127.0.0.1` sirve las variantes desde memoria; todo lo demás se bloquea y se anota (`red-externa`, aviso). Las pruebas del laboratorio no dependen de internet.
3. **Azar fijado**: `Math.random` sale de la semilla de la celda.
4. **Reloj fijo**: el reloj del navegador se instala, se pausa y solo avanza con los pasos (`pasar`), alineado a la rejilla de 16 ms de los fotogramas; una barrera de entrada espera a que la página haya procesado cada evento. Por eso **la misma celda da la misma traza**: se comprueba repitiendo la primera semilla de cada grupo (`no-determinista`) y se verificó repitiendo todas.
5. **Carga modelada**: el tiempo de carga que sufre la persona se calcula con un modelo declarado, `latencia × (1 + ⌈(solicitudes−1)/6⌉) + bytes·8/kbps + 40 × cpu` ms, y se compara con la paciencia de carga del perfil (`carga-lenta`). No es la velocidad real de la computadora; es lo que pasaría con esa red y ese aparato.
6. **Aparato**: tamaño, escala, táctil, idioma, zona, tema y movimiento reducido del perfil; la CPU lenta se aplica con estrangulamiento del navegador (solo afecta lo *medido*).

## Telemetría y banderas

Por grupo (variante × perfil × prueba): sesiones, completaron, abandonaron, fallaron, tasa con intervalo de Wilson al 95 %, embudo (llegaron y mediana del tiempo simulado),
dónde abandonan y por qué, tiempo hasta la primera acción, carga modelada, peso, errores, accesibilidad, determinismo, datos leídos y un ejemplo de fallo con sus últimos eventos.

| Nivel | Bandera | Qué dice |
| --- | --- | --- |
| falla | `no-determinista` | La misma semilla, perfil y variante dieron otra traza. |
| falla | `fallas-de-pagina` | Errores de consola o excepciones (una bandera por variante, con en cuántos grupos salió). |
| falla | `recurso-faltante` | La página pidió un archivo local que no existe (404). |
| falla | `contexto-sucio` | El aislamiento falló. |
| falla | `verificacion-fallida` | Un `verificar` no se cumplió. |
| falla | `error-interno` | El laboratorio no pudo correr la celda, o una variante no se aplicó. |
| falla | `imposible` | Nadie, con ningún perfil, completó un guion en una variante. |
| aviso | `abandono-alto` | Una de cada tres sesiones (o más) de un perfil se rinde (con ≥ 5 sesiones). |
| aviso | `bloqueado-para-perfil` | Un perfil no completa nunca algo que otros sí completan, y dónde se traba. |
| aviso | `carga-lenta` | Se rinden porque la carga modelada pasa su paciencia. |
| aviso | `red-externa` | La beta intentó salir a internet. |
| aviso | `a11y-CÓDIGO` | Accesibilidad y uso: `idioma-falta`, `titulo-falta`, `viewport-falta`, `imagen-sin-alt`, `control-sin-nombre`, `objetivo-chico`, `objetivo-chico-tactil`, `desborde-horizontal`, `texto-chico`, `contraste-bajo`, `ignora-movimiento-reducido`, `teclado-sin-foco`. Una por código y variante, con los perfiles afectados. |
| según el caso | `bots-CÓDIGO` | Las banderas del órgano de bots, vistas con el temple de cada perfil. |

Una bandera de **falla** hace que `correr` termine con error; un **aviso** es para que lo mire una persona.

## El informe: dos mitades

- **`metricas/laboratorio/ID.json`** (determinista, **se guarda en el repositorio**): mismas semillas y misma beta, mismo archivo. Lleva las huellas de lo probado y una `huella_resultado`.
- **`metricas/laboratorio/ID.medido.json`** (local, en `.gitignore`): tiempos reales de esta computadora (carga, ritmo de CPU, pasada más larga, memoria). Es ruido útil para ver órdenes de magnitud; **nunca decide una bandera de falla**.

## Comparar

- **A/B dentro de un informe** (`contrastes`): cada variante contra el control, por perfil y prueba: diferencia de tasa, de abandono y problemas de accesibilidad nuevos o resueltos. `claro` solo si los intervalos de Wilson **no se cruzan**; con pocas sesiones casi siempre sale «no concluyente», y está bien que lo diga.
- **Entre versiones** (`laboratorio comparar ID`): `guardar` pasa el informe anterior a `ID.previo.json` cuando cambió la beta (huellas u objeto distintos); `comparar` lista regresiones (completan menos con cambio claro, una etapa del embudo que cae ≥ 25 puntos, problemas o errores nuevos, dejó de ser determinista, una falla nueva), mejoras y otros cambios (incluidos avisos nuevos y diferencias grandes con poca muestra).

## Experimentos de hoy

- `rebote-primer-minuto`: ¿llega una persona a su primer tiro y a ganar el nivel 1?; variante `tiros-3`.
- `arena-primer-minuto`: ¿descubre la montaña, el agua y el barro?; variante `sostener-60`.

Se agregan nuevos como archivos de `laboratorio/experimentos/`; no hace falta tocar código mientras se usen los verbos de arriba. Lo que haga falta de más (un verbo, un
dato de la página) entra al motor con prueba, no como un parche del experimento.

## Plataforma externa

El laboratorio **no envía nada afuera**. Si Max decide usar una plataforma que simula personas, la forma de conectarla es exportar de aquí los **perfiles** (`laboratorio/perfiles.json`) y la **pregunta** del experimento, y ponerla a navegar la beta; eso exige una dirección a la que llegue, y exponer una beta en una dirección alcanzable es publicar: lo decide Max con su aprobación y su huella (ver `BOTS.md`). Mientras tanto el laboratorio corre lo mismo en su propio navegador.
