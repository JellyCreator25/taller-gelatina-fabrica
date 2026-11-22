"""Andamio de la fábrica: crea el esqueleto de una plantilla nueva (un género nuevo) o de un juego nuevo sobre una plantilla.

  python3 fabrica.py nueva-plantilla NOMBRE --genero G --verbo V --objetivo O [--entrada toque,teclado] [--progresion P]
  python3 fabrica.py nuevo ID PLANTILLA

Escalar la fábrica = más plantillas de géneros distintos (no más variantes). Por eso `nueva-plantilla` exige declarar el núcleo desde el principio y
se niega a crear una plantilla cuyo núcleo ya existe: en ese caso lo que corresponde es un juego nuevo sobre la plantilla existente, o un paquete.
Todo lo que el autor debe completar queda marcado con la palabra PENDIENTE; mientras quede alguna, el juego se puede construir y probar, pero no publicar."""
import json
import pathlib
import re
import sys

import json_fmt
import novedad

PLANTILLA_HTML = r'''<style>
/* ESQUELETO de la plantilla «@@N@@». Reemplaza el juego de ejemplo por el tuyo; lo que se conserva:
   · colores como variables, con tema claro y oscuro (el fondo del body siempre explícito)
   · todo texto visible sale de X.t('clave') y se rellena de nuevo con X.onLang (los textos viven en juego.json → textos, en cada idioma)
   · números con X.num; fuente del lienzo con FONT() (trae la tipografía china del sistema)
   · el estado para las pruebas se expone en window.__@@N@@.estado()
   · sin conexiones externas, sin Google Fonts: la fábrica incrusta las tipografías */
:root {
  --bg: #f1f5ff; --surface: #ffffff; --ink: #15203b; --ink-soft: #4a5a7e; --line: #cfd9f0; --accent: #2f6bdc; --accent-ink: #ffffff; --focus: #1b5fe0;
  --cjk: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", "Noto Sans SC", "WenQuanYi Micro Hei";
  --font-display: 'Fredoka', var(--cjk), 'Trebuchet MS', system-ui, sans-serif;
  --font-body: 'Nunito Sans', var(--cjk), system-ui, -apple-system, 'Segoe UI', sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --bg: #0b1020; --surface: #141b33; --ink: #e6ecff; --ink-soft: #9fb0d9; --line: #29345c; --focus: #8db0ff; color-scheme: dark; }
}
:root[data-theme="dark"] { --bg: #0b1020; --surface: #141b33; --ink: #e6ecff; --ink-soft: #9fb0d9; --line: #29345c; --focus: #8db0ff; color-scheme: dark; }
body { background: var(--bg); color: var(--ink); font-family: var(--font-body); min-height: 100vh; }
.app { box-sizing: border-box; max-width: 760px; margin: 0 auto; padding-block: 12px 18px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
h1 { margin: 0; font: 700 1.5rem/1.1 var(--font-display); text-wrap: balance; }
.tools { display: flex; gap: 8px; }
canvas { display: block; width: 100%; height: auto; margin-top: 12px; border-radius: 18px; background: var(--surface); border: 2px solid var(--line); touch-action: manipulation; }
.bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-top: 10px; }
#marcador { margin: 0; color: var(--ink-soft); }
.btn { font: 700 1.05rem var(--font-display); border: 0; border-radius: 14px; padding: .7em 1.5em; background: var(--accent); color: var(--accent-ink); cursor: pointer; }
.btn:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
</style>

<div class="app">
  <header>
    <h1 id="titulo"></h1>
    <div class="tools" id="tools"></div>
  </header>
  <canvas id="cv" width="640" height="400" role="img"></canvas>
  <div class="bar">
    <p id="marcador"></p>
    <button class="btn" id="btnJugar" type="button"></button>
  </div>
</div>

<script>
const X = window.GGX;
const $ = (id) => document.getElementById(id);
const cv = $('cv'), g = cv.getContext('2d');
const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const FONT = (px, w) => w + ' ' + px + 'px Fredoka, ' + X.cjk + ', "Trebuchet MS", sans-serif';
const S = { fase: 'inicio', puntos: 0, mejor: Number(X.store.get('mejor', 0)) || 0, t: 0 };

function textos() {
  document.title = X.t('titulo');
  $('titulo').textContent = X.t('titulo');
  $('btnJugar').textContent = X.t('jugar');
  cv.setAttribute('aria-label', X.t('aria_juego'));
  marcador();
}
function marcador() { $('marcador').textContent = X.t('puntos', { n: X.num(S.puntos) }) + ' · ' + X.t('mejor', { n: X.num(S.mejor) }); }
function jugar() { X.sfx('click', 0); S.fase = 'juego'; S.puntos = 0; $('btnJugar').hidden = true; marcador(); }
function tocar() {
  if (S.fase !== 'juego') return;
  S.puntos += 1;
  if (S.puntos > S.mejor) { S.mejor = S.puntos; X.store.set('mejor', S.mejor); }
  X.sfx('coin', 0);
  marcador();
}
function draw() {
  const css = getComputedStyle(document.documentElement);
  g.clearRect(0, 0, cv.width, cv.height);
  const pulso = reduce ? 0 : Math.sin(S.t * 3) * 6;
  g.fillStyle = css.getPropertyValue('--accent').trim() || '#2f6bdc';
  g.beginPath(); g.arc(cv.width / 2, cv.height / 2, 70 + pulso + Math.min(S.puntos, 30), 0, Math.PI * 2); g.fill();
  g.fillStyle = '#fff'; g.font = FONT(40, 700); g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText(String(S.puntos), cv.width / 2, cv.height / 2);
}
function bucle(ts) { S.t = ts / 1000; draw(); requestAnimationFrame(bucle); }

$('btnJugar').addEventListener('click', jugar);
cv.addEventListener('pointerdown', tocar);
addEventListener('keydown', (e) => { if (e.code === 'Space') { e.preventDefault(); tocar(); } });
X.ui.muteButton($('tools')); X.ui.langButton($('tools')); X.ui.supportLink($('tools'));
X.onLang(textos); textos(); requestAnimationFrame(bucle);
window.__@@N@@ = { estado: () => ({ fase: S.fase, puntos: S.puntos, mejor: S.mejor }) };
</script>
'''

PRUEBA_JS = r'''// Escenario de prueba de la plantilla «@@N@@»: lo usa herramientas/probar.js. `ctx` trae: modo ('prueba' con comprobaciones | 'video' a ritmo normal),
// medios (carpeta de salida), log, assert y slug ('escritorio' | 'celular'). Debe dejar medios/portada-fuente.png (solo en escritorio) y una captura.
// ESQUELETO: reemplaza los pasos por los de tu juego, y comprueba sus reglas con el estado que expone window.__@@N@@.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

module.exports = {
  listo: '#cv',
  async jugar(page, ctx) {
    const { modo, medios, log, assert, slug } = ctx;
    const tactil = slug === 'celular';
    const E = () => page.evaluate(() => window.__@@N@@.estado());
    const tocar = (sel) => { const l = page.locator(sel); return tactil ? l.tap() : l.click(); };
    const lienzo = async () => { const c = await page.locator('#cv').boundingBox(); return [c.x + c.width / 2, c.y + c.height / 2]; };
    const pulsar = async () => { const [x, y] = await lienzo(); if (tactil) await page.touchscreen.tap(x, y); else await page.mouse.click(x, y); };

    if (modo === 'video') {
      await sleep(1200);
      await tocar('#btnJugar');
      for (let i = 0; i < 12; i++) { await pulsar(); await sleep(260); }
      await sleep(1500);
      return { puntos: (await E()).puntos };
    }

    let e = await E();
    assert(e.fase === 'inicio', 'la partida debería esperar en la pantalla de inicio (' + e.fase + ')');
    await tocar('#btnJugar');
    e = await E();
    assert(e.fase === 'juego', 'el botón Jugar no empezó la partida (' + e.fase + ')');
    for (let i = 1; i <= 5; i++) { await pulsar(); }
    e = await E();
    assert(e.puntos === 5, 'cinco toques deberían dar 5 puntos y dieron ' + e.puntos);
    log('  cinco toques → ' + e.puntos + ' puntos');
    await page.keyboard.press('Space');
    assert((await E()).puntos === 6, 'la barra espaciadora no sumó');
    await sleep(300);
    if (slug === 'escritorio') await page.screenshot({ path: medios + '/portada-fuente.png', clip: await page.locator('#cv').boundingBox() });
    await page.screenshot({ path: medios + '/captura-juego-' + slug + '.png' });
    return { puntos: (await E()).puntos };
  },
};
'''

DISENO_MD = '''# Diseño de la plantilla «@@N@@»

Estado: borrador. Mientras diga PENDIENTE en algún apartado, ningún juego de esta plantilla se publica (lo comprueba `python3 fabrica.py novedad`).

## Núcleo (declarado en `plantilla.json`)

- Género: @@GENERO@@ · Verbo: @@VERBO@@ · Objetivo: @@OBJETIVO@@

## Qué hace el jugador, una y otra vez (una frase)

PENDIENTE

## Por qué es divertido (la tensión o la decisión central)

PENDIENTE

## Referencias y qué mejora esta plantilla frente a cada una

La regla de la casa es que cada juego sea una mejora respecto de lo que lo inspira, no una copia con otro tema.

- PENDIENTE: «juego de referencia» → qué hace mejor o distinto

## Qué la distingue de las plantillas que ya existen (@@EXISTENTES@@)

PENDIENTE

## Qué puede cambiar entre juegos de esta plantilla sin que sea una variante

Lo que sí varía (niveles, unidades, modos, parámetros) y lo que no (el núcleo). Un juego que solo cambie el tema no es un juego nuevo: va como paquete o modo.

PENDIENTE

## Plan de pruebas automáticas (`prueba.js`)

Qué reglas del juego se comprueban con el estado de `window.__@@N@@.estado()` (puntaje, fin de partida, límites) y qué se deja a jugadores humanos.

PENDIENTE

## Textos y chino

Todo texto visible va por `X.t()` y existe en español, inglés y chino con las mismas marcas `{n}`. El chino solo usa caracteres de GB2312, y una persona hablante nativa lo revisa antes de publicar.
'''


def _comprobar_nombre(nombre, que):
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,40}', nombre):
        raise SystemExit('%s: usa minúsculas, números y guiones (por ejemplo «mi-juego»), de 2 a 41 caracteres' % que)


def nueva_plantilla(raiz, nombre, genero, verbo, objetivo, entrada=('toque',), progresion='niveles-fijos'):
    raiz = pathlib.Path(raiz)
    _comprobar_nombre(nombre, 'Nombre de plantilla')
    destino = raiz / 'plantillas' / nombre
    if destino.exists():
        raise SystemExit('Ya existe la plantilla «%s».' % nombre)
    vocab = novedad.cargar_vocabulario(raiz)
    propuesta = {'id': nombre, 'mecanica': {'genero': genero, 'verbo': verbo, 'objetivo': objetivo, 'entrada': list(entrada), 'progresion': progresion}}
    problemas = novedad.validar_mecanica(propuesta, vocab, requerir_todo=False)
    for eje in novedad.OTROS_EJES:
        for v in propuesta['mecanica'][eje] if isinstance(propuesta['mecanica'][eje], list) else [propuesta['mecanica'][eje]]:
            if v not in vocab['ejes'][eje]:
                problemas.append('mecanica.%s = «%s» no está en el vocabulario' % (eje, v))
    if problemas:
        raise SystemExit('No se creó la plantilla:\n  - ' + '\n  - '.join(problemas))
    r = novedad.evaluar(raiz, spec=propuesta)
    repetidas = [c['con'] for c in r['comparaciones'] if c['veredicto'] == 'variante']
    for ruta in sorted((raiz / 'plantillas').glob('*/plantilla.json')):
        man = json.loads(ruta.read_text(encoding='utf-8'))
        if all(novedad._vals(man, e) == novedad._vals(propuesta['mecanica'], e) for e in novedad.NUCLEO):
            repetidas.append('plantilla ' + man['nombre'])
    if repetidas:
        raise SystemExit('No se creó la plantilla: su núcleo (%s · %s · %s) es el de «%s», que ya existe. No hace falta otra plantilla: crea un juego nuevo con '
                         '`nuevo` sobre la existente o añade un paquete. Una plantilla nueva es un género nuevo.' % (genero, verbo, objetivo, ', '.join(repetidas)))
    existentes = ', '.join(sorted(p.parent.name for p in (raiz / 'plantillas').glob('*/plantilla.json'))) or 'ninguna'
    destino.mkdir(parents=True)
    ident = nombre.replace('-', '_')
    sust = {'@@N@@': ident, '@@GENERO@@': genero, '@@VERBO@@': verbo, '@@OBJETIVO@@': objetivo, '@@EXISTENTES@@': existentes}

    def poner(texto):
        for k, v in sust.items():
            texto = texto.replace(k, v)
        return texto
    (destino / 'plantilla.html').write_text(poner(PLANTILLA_HTML), encoding='utf-8')
    (destino / 'prueba.js').write_text(poner(PRUEBA_JS), encoding='utf-8')
    (destino / 'DISENO.md').write_text(poner(DISENO_MD), encoding='utf-8')
    json_fmt.guardar(destino / 'plantilla.json', {'nombre': nombre, 'genero': genero, 'verbo': verbo, 'objetivo': objetivo, 'entrada': list(entrada),
                                                  'progresion': progresion, 'descripcion': 'PENDIENTE: una frase sobre qué es esta plantilla.'})
    return destino


TEXTOS_BASE = {
    'es': {'titulo': 'PENDIENTE título', 'aria_juego': 'Zona de juego', 'jugar': 'Jugar', 'puntos': 'Puntos: {n}', 'mejor': 'Mejor: {n}'},
    'en': {'titulo': 'PENDIENTE title', 'aria_juego': 'Game area', 'jugar': 'Play', 'puntos': 'Score: {n}', 'mejor': 'Best: {n}'},
    'zh': {'titulo': 'PENDIENTE', 'aria_juego': '游戏区域', 'jugar': '开始', 'puntos': '分数：{n}', 'mejor': '最高：{n}'},
}


def nuevo_juego(raiz, juego_id, plantilla, beta=False):
    raiz = pathlib.Path(raiz)
    _comprobar_nombre(juego_id, 'Id del juego')
    base = raiz / 'plantillas' / plantilla
    if not (base / 'plantilla.json').exists():
        raise SystemExit('La plantilla «%s» no existe o no tiene plantilla.json. Plantillas: %s' % (plantilla, ', '.join(sorted(p.parent.name for p in (raiz / 'plantillas').glob('*/plantilla.json')))))
    destino = raiz / 'juegos' / juego_id
    if destino.exists():
        raise SystemExit('Ya existe el juego «%s».' % juego_id)
    man = json.loads((base / 'plantilla.json').read_text(encoding='utf-8'))
    otros = novedad.cargar_juegos(raiz)
    orden = max([(o.get('lanzamiento') or {}).get('orden', 0) for o in otros.values()] + [0]) + 1
    previo = max(otros, key=lambda i: (otros[i].get('lanzamiento') or {}).get('orden', 0)) if otros else None
    idiomas = ['es', 'en', 'zh']
    p = 'PENDIENTE'
    spec = {
        'id': juego_id, 'plantilla': plantilla, 'version': '0.1.0', 'idiomas': idiomas, 'paquetes': [], 'fuentes': ['Fredoka', 'Nunito Sans'], 'apoyo_url': '',
        'motor': _modulos_del_motor(raiz, plantilla), 'necesidades_motor': [],
        'parametros': {}, 'textos': TEXTOS_BASE,
        'portada': {'color_a': '#2f6bdc', 'color_b': '#e04a34', 'lema': {i: p for i in idiomas}, 'selector': '#cv'},
        'ia': {'codigo': True, 'graficos': True, 'texto': True, 'sonido': False},
        'precio': {'modo': 'donar', 'sugerido_usd': 2}, 'etiquetas': [p], 'clasificacion': p,
        'ficha': {i: {'titulo': p, 'corta': p, 'larga': p, 'controles': p} for i in idiomas},
        'difusion': {i: {'post_corto': p, 'post_comunidad_titulo': p, 'post_comunidad': p, 'guion_video': [p], 'mensaje_clase': p, 'devlog_titulo': p, 'devlog': p, 'descripcion_video': p} for i in idiomas},
        'lanzamiento': dict({'orden': orden}, **({'despues_de': previo, 'espera_semanas': '2 a 4'} if previo else {})),
        'originalidad': {'riesgo_portales': p, 'referencias': [], 'motivo': p, 'diferenciador': {i: p for i in idiomas}},
        'mecanica': {'genero': man['genero'], 'verbo': man['verbo'], 'objetivo': man['objetivo'], 'entrada': man['entrada'], 'progresion': man['progresion'],
                     'ambientacion': p, 'arte': p, 'sistemas': []},
        'creacion': {'herramientas': ['Claude (Anthropic): programación, gráficos y textos del juego, y sus pruebas automáticas.'], 'decisiones_dueno': [p], 'decisiones_claude': [p]},
        'prueba': {'escenario': plantilla},
    }
    if beta:
        spec['estado'] = 'beta'           # prototipo para probar con bots: se construye, nunca se publica (ver novedad.es_beta)
        spec['motor'] = ['bots']
    destino.mkdir(parents=True)
    json_fmt.guardar(destino / 'juego.json', spec)
    return destino


def _modulos_del_motor(raiz, plantilla=None):
    """Un juego nuevo parte con TODOS los módulos del motor declarados: cada juego debe sentirse mejor que el anterior. Quitar uno exige una razón, y
    declararlo no basta: el nivel de calidad solo cuenta lo que el código del juego llama (python3 fabrica.py calidad ID).
    Excepción: «bots» (el laboratorio de pruebas) solo viene si la plantilla trae sus políticas (plantillas/NOMBRE/bots.js); si no, sería peso muerto en cada juego."""
    sys.path.insert(0, str(pathlib.Path(raiz) / 'herramientas'))
    import motor
    con_bots = bool(plantilla) and (pathlib.Path(raiz) / 'plantillas' / plantilla / 'bots.js').exists()
    return [m for m in motor.manifiesto(raiz) if m != 'bots' or con_bots]


pendientes = novedad.pendientes
