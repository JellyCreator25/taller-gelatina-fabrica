// Escenario de prueba de Torre Gelatina: juega una partida completa con precisión, usando el estado que expone window.__torre.
// Lo usa herramientas/probar.js. `ctx` trae: modo ('prueba' con comprobaciones | 'video' a ritmo normal), medios (carpeta), log, assert, slug.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Corre DENTRO de la página. Espera a que el bloque que se mueve llegue al punto pedido y, si `soltar` es true, lo suelta ahí mismo
// (así no hay latencia entre medir y actuar); si es false solo avisa, para que la prueba haga un clic, un toque o una tecla de verdad.
//   modo: 'perfecto' (justo encima de la torre) · 'corte' (se pierde casi la mitad) · 'fallo' (corte casi total)
//   adelanto: milisegundos que tardará en llegar una entrada real; se compensa con la velocidad del bloque
const alinear = ({ modo, soltar, adelanto }) => new Promise((resolve, reject) => {
  const T = window.__torre, stage = document.getElementById('stage'), W = 360;
  const s0 = T.estado();
  if (s0.fase !== 'juego') return reject(new Error('la partida no está en juego (' + s0.fase + ')'));
  const izq = s0.topX, der = W - s0.w - s0.topX, lado = der >= izq ? 1 : -1, sitio = Math.max(izq, der);
  const off = modo === 'perfecto' ? 0 : lado * Math.min((modo === 'corte' ? 0.45 : 0.9) * s0.w, Math.max(0, sitio - 1));
  const meta = s0.topX + off, t0 = performance.now();
  let antes = null;
  (function f() {
    const s = T.estado();
    if (s.fase !== 'juego') return reject(new Error('la partida salió de «juego» mientras se esperaba (' + s.fase + ')'));
    if (performance.now() - t0 > 9000) return reject(new Error('el bloque no llegó al punto pedido en 9 s'));
    const paso = antes === null ? s.v / 60 : Math.abs(s.x - antes);
    antes = s.x;
    const px = s.x + s.dir * ((adelanto || 0) * s.v) / 1000;
    if (Math.abs(px - meta) <= Math.max(1, paso / 2 + 0.01)) {
      if (soltar) {
        const r = stage.getBoundingClientRect();
        stage.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerType: 'mouse', isPrimary: true, button: 0, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 }));
      }
      return resolve(Object.assign({}, T.estado(), { error: px - meta }));
    }
    requestAnimationFrame(f);
  })();
});

module.exports = {
  listo: '#cv',
  clip: { ancho: 600, alto: 720 },   // el juego es vertical: el clip principal también
  gif: { ultimos: 12.5, duracion: 12 },   // termina con la tarjeta de récord
  async jugar(page, ctx) {
    const { modo, medios, log, assert, slug } = ctx;
    const video = modo === 'video';
    const tactil = slug === 'celular';
    const E = () => page.evaluate(() => window.__torre.estado());
    const soltar = (m) => page.evaluate(alinear, { modo: m, soltar: true });
    const tocar = (sel) => { const l = typeof sel === 'string' ? page.locator(sel) : sel; return tactil ? l.tap() : l.click(); };
    const final = async () => {   // cortes casi totales hasta que el bloque cae sin apoyo
      for (let i = 0; i < 12; i++) {
        if ((await E()).fase !== 'juego') break;
        await page.evaluate(alinear, { modo: 'fallo', soltar: true }).catch(() => {});
      }
      await page.waitForFunction(() => window.__torre.estado().fase !== 'juego', null, { timeout: 5000 });
    };

    if (video) {
      await sleep(1300);
      await tocar('#btnJugar');
      for (let i = 0; i < 8; i++) await soltar('perfecto');
      await soltar('corte');
      while ((await E()).n < 24) await soltar('perfecto');
      await sleep(500);
      await final();
      await sleep(3200);   // pantalla final con el récord
      return { pisos: (await E()).n };
    }

    const P = await page.evaluate(() => window.__torre.cfg);
    let e = await E();
    assert(e.fase === 'inicio', 'la partida debería esperar en la pantalla de inicio (' + e.fase + ')');
    assert((await page.isVisible('#ovInicio')) && (await page.isVisible('#btnJugar')), 'no se ve la tarjeta de inicio');
    log('  idioma al abrir: ' + (await page.evaluate(() => document.documentElement.lang)));
    await tocar('#btnJugar');
    await sleep(150);
    e = await E();
    assert(e.fase === 'juego', 'el botón Jugar no empezó la partida (' + e.fase + ')');
    assert(!(await page.isVisible('#ovInicio')), 'la tarjeta de inicio sigue visible durante la partida');

    // 1) Una racha perfecta no quita ancho
    for (let i = 1; i <= 6; i++) {
      e = await soltar('perfecto');
      assert(e.n === i && e.perfectos === i && e.combo === i, 'perfecto ' + i + ': ' + JSON.stringify(e));
    }
    assert(Math.abs(e.topW - P.ancho_inicial) < 0.01, 'una racha perfecta no debe quitar ancho (' + e.topW + ')');
    log('  6 perfectos seguidos con el ancho intacto (' + e.topW + ' px)');

    // 2) Los cortes estrechan la torre y rompen la racha
    const w0 = e.topW;
    e = await soltar('corte');
    assert(e.combo === 0 && e.topW < w0 - 10, 'el primer corte debía estrechar y romper la racha: ' + JSON.stringify(e));
    const w1 = e.topW;
    e = await soltar('corte');
    assert(e.topW < w1 - 5, 'el segundo corte debía estrechar más: ' + JSON.stringify(e));
    log('  dos cortes: ' + w0.toFixed(0) + ' → ' + w1.toFixed(0) + ' → ' + e.topW.toFixed(0) + ' px');

    // 3) A partir del tercer perfecto seguido la torre se ensancha
    const base = e.topW;
    for (let i = 1; i <= 4; i++) {
      e = await soltar('perfecto');
      const esperado = base + P.crecimiento * Math.max(0, i - P.meta_perfectos + 1);
      assert(Math.abs(e.topW - esperado) < 0.5, 'perfecto ' + i + ' de la racha: ancho ' + e.topW.toFixed(1) + ', se esperaban ' + esperado);
    }
    log('  racha de 4: ' + base.toFixed(0) + ' → ' + e.topW.toFixed(0) + ' px (+' + P.crecimiento + ' desde el tercero)');

    // 4) La torre crece y la cámara la sigue
    while ((await E()).n < 23) await soltar('perfecto');

    // 5) Entradas reales: clic o toque, y barra espaciadora
    const caja = await page.locator('#stage').boundingBox();
    const antes = (await E()).n;
    await page.evaluate(alinear, { modo: 'perfecto', soltar: false, adelanto: 25 });
    if (tactil) await page.touchscreen.tap(caja.x + caja.width / 2, caja.y + caja.height / 2);
    else await page.mouse.click(caja.x + caja.width / 2, caja.y + caja.height / 2);
    await sleep(80);
    e = await E();
    assert(e.n === antes + 1, (tactil ? 'el toque' : 'el clic') + ' real no soltó el bloque (' + antes + ' → ' + e.n + ')');
    await page.evaluate(alinear, { modo: 'perfecto', soltar: false, adelanto: 25 });
    await page.keyboard.press('Space');
    await sleep(80);
    e = await E();
    assert(e.n === antes + 2, 'la barra espaciadora no soltó el bloque (' + antes + ' → ' + e.n + ')');
    log('  entradas reales: ' + (tactil ? 'toque' : 'clic') + ' y barra espaciadora sueltan el bloque');

    // 6) Una captura con la racha a la vista (y la fuente de la portada)
    e = await soltar('perfecto');
    await sleep(380);
    const hud = await page.textContent('#score');
    assert(Number(hud) === e.n, 'el marcador muestra ' + hud + ' y la torre tiene ' + e.n + ' pisos');
    if (slug === 'escritorio') await page.screenshot({ path: medios + '/portada-fuente.png', clip: await page.locator('#stage').boundingBox() });
    await page.screenshot({ path: medios + '/captura-juego-' + slug + '.png' });
    log('  torre de ' + e.n + ' pisos · racha ' + e.combo + ' · velocidad ' + e.v.toFixed(0) + ' px/s');

    // 7) Un fallo total termina la partida y guarda el récord
    await final();
    await sleep(300);
    await page.screenshot({ path: medios + '/captura-caida-' + slug + '.png' });
    await page.waitForFunction(() => window.__torre.estado().fase === 'fin', null, { timeout: 5000 });
    e = await E();
    assert(await page.isVisible('#ovFin'), 'no apareció la tarjeta final');
    log('  final: «' + (await page.textContent('#fT')) + '» · ' + (await page.textContent('#fP')));
    assert(e.record === true, 'la primera partida debía ser récord');
    const guardado = await page.evaluate(() => JSON.parse(localStorage.getItem('torre-gelatina:mejor')));
    assert(guardado === e.n, 'el récord guardado (' + guardado + ') no coincide con los pisos (' + e.n + ')');
    await page.screenshot({ path: medios + '/captura-final-' + slug + '.png' });
    const plays = await page.evaluate(() => window.GGX.sfx.plays);
    log('  sonidos disparados: ' + JSON.stringify(plays));
    for (const n of ['click', 'coin', 'pop', 'hurt']) assert((plays[n] || 0) > 0, 'el sonido «' + n + '» nunca se disparó');
    assert((plays.win || 0) + (plays.lose || 0) > 0, 'no sonó el final de la partida');
    const pisos = e.n;

    // 8) Jugar otra vez (con el botón)
    await sleep(500);
    await tocar('#btnOtra');
    await sleep(150);
    e = await E();
    assert(e.fase === 'juego' && e.n === 0, 'Jugar otra vez no reinició la partida: ' + JSON.stringify(e));
    assert(!(await page.isVisible('#ovFin')), 'la tarjeta final sigue visible');

    // 9) Idiomas: el selector ofrece todos, cada texto sigue al idioma, <html lang> lleva la etiqueta correcta y el chino se ve con sus caracteres
    const idiomas = await page.evaluate(() => window.GGX.langs);
    assert(idiomas.length >= 3, 'el juego debería ofrecer al menos tres idiomas (' + idiomas + ')');
    const sel = page.locator('.tools select.ggx-lang');
    log('  idiomas ofrecidos: ' + (await sel.locator('option').allTextContents()).join(' · '));
    for (const l of idiomas) {
      await sel.selectOption(l);
      await sleep(120);
      const est = await page.evaluate(() => ({
        lang: window.GGX.lang, etiqueta: document.documentElement.lang, titulo: document.getElementById('titulo').textContent, doc: document.title,
        mejor: document.getElementById('best').textContent, fuente: getComputedStyle(document.getElementById('titulo')).fontFamily,
      }));
      const esperado = await page.evaluate((x) => window.JUEGO.textos[x].titulo, l);
      assert(est.lang === l, 'al elegir ' + l + ' el motor quedó en ' + est.lang);
      assert(est.titulo === esperado && est.doc === esperado, 'el título no siguió al idioma ' + l + ': «' + est.titulo + '» / «' + est.doc + '» vs «' + esperado + '»');
      assert(est.etiqueta === (l === 'zh' ? 'zh-Hans' : l), 'html lang es «' + est.etiqueta + '» en ' + l);
      const mejorEsperado = await page.evaluate((x) => window.JUEGO.textos[x].mejor, l);
      assert(est.mejor.startsWith(mejorEsperado), 'el marcador «' + est.mejor + '» no empieza por «' + mejorEsperado + '» en ' + l);
      if (l === 'zh') assert(/PingFang|YaHei|Noto Sans CJK|Hiragino|Noto Sans SC|WenQuanYi/.test(est.fuente), 'la pila tipográfica del título no incluye fuentes chinas: ' + est.fuente);
      if (!video) await page.screenshot({ path: medios + '/captura-idioma-' + l + '-' + slug + '.png' });
    }
    // el chino debe dibujarse de verdad: la tarjeta de inicio con texto chino no puede medir lo mismo que con cuadros vacíos
    const trazo = await page.evaluate(() => {
      const c = document.createElement('canvas').getContext('2d');
      const fam = (window.GGX.cjk || '') + ', sans-serif';
      const m = (txt, f) => { c.font = '32px ' + f; return Math.round(c.measureText(txt).width); };
      return { chino: m('果冻塔', fam), sinFuente: m('果冻塔', '"NoExisteEstaFuente123"'), latino: m('abc', fam) };
    });
    log('  medida de «果冻塔» a 32 px: ' + trazo.chino + ' px con la pila china');
    assert(trazo.chino >= 60 && trazo.chino <= 110, 'la medida del texto chino (' + trazo.chino + ' px) no parece de caracteres reales');
    const lang1 = idiomas[idiomas.length - 1];
    assert((await page.evaluate(() => window.GGX.lang)) === lang1, 'el último idioma probado no quedó activo');

    // 10) Tras recargar, el récord y el idioma elegido siguen ahí
    await page.reload();
    await page.waitForSelector('#cv');
    await sleep(500);
    const mejor = await page.textContent('#best');
    assert(new RegExp('\\b' + pisos + '\\b').test(mejor), 'tras recargar, el marcador de mejor dice «' + mejor + '» y el récord era ' + pisos);
    assert((await page.evaluate(() => window.GGX.lang)) === lang1, 'el idioma elegido no se recordó al recargar');
    // la dirección manda sobre lo guardado: ?lang=en abre en inglés aunque el jugador hubiera elegido otro
    await page.goto(page.url().split('?')[0] + '?lang=en');
    await page.waitForSelector('#cv');
    assert((await page.evaluate(() => window.GGX.lang)) === 'en', '?lang=en no cambió el idioma');
    log('  tras recargar: «' + mejor + '», el idioma se mantiene (' + lang1 + ') y ?lang=en lo cambia');
    return { pisos };
  },
};
