// Escenario de prueba de Compás Gelatina: juega canciones completas con precisión de milisegundos, usando el estado que expone window.__compas.
// Lo usa herramientas/probar.js. `ctx` trae: modo ('prueba' con comprobaciones | 'video' a ritmo normal), medios (carpeta), log, assert, slug.
// La página se abre con ?demo=1: la canción dura una sola vuelta de ocho compases en lugar de dos.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Corre DENTRO de la página. Espera a que una gota llegue a su hora (más `desfase` ms) y, si `soltar` es true, toca ahí mismo su carril con un evento de puntero
// (así no hay latencia entre medir y actuar); si es false solo avisa unos `adelanto` ms antes, para que la prueba haga un clic, un toque o una tecla de verdad.
//   desfase: 0 = justo en la línea · positivo = tarde · negativo = temprano   carril: elige la primera gota pendiente de ese carril (por defecto, la siguiente)
const golpe = ({ desfase, soltar, adelanto, carril }) => new Promise((resolve, reject) => {
  const C = window.__compas, stage = document.getElementById('stage');
  const e0 = C.estado();
  if (e0.fase !== 'juego') return reject(new Error('la partida no está en juego (' + e0.fase + ')'));
  const g = carril == null ? e0.siguiente : e0.proximas.find((d) => d.lane === carril);
  if (!g) return reject(new Error('no quedan gotas pendientes' + (carril == null ? '' : ' en el carril ' + carril)));
  const lane = g.lane;
  const r = stage.getBoundingClientRect();
  const x = r.left + (r.width * (lane + 0.5)) / 3, y = r.top + r.height / 2;
  let tg = g.t;
  const t0 = performance.now();
  (function f() {
    const e = C.estado();
    if (e.fase !== 'juego') return reject(new Error('la partida salió de «juego» mientras se esperaba (' + e.fase + ')'));
    if (performance.now() - t0 > 8000) return reject(new Error('la gota no llegó a su hora en 8 s'));
    const aqui = e.proximas.find((d) => d.lane === lane && Math.abs(d.t - tg) < 100);   // la hora de la gota se corrige un par de milisegundos cuando arranca la música
    if (!aqui) return reject(new Error('la gota esperada ya no estaba pendiente (carril ' + lane + ')'));
    tg = aqui.t;
    const falta = tg + (desfase || 0) - (adelanto || 0) - e.T;
    if (falta <= 4) {
      if (falta > 0) { const fin = performance.now() + falta; while (performance.now() < fin) { /* espera exacta de unos milisegundos */ } }
      if (soltar) stage.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerType: 'mouse', isPrimary: true, button: 0, clientX: x, clientY: y }));
      return resolve(Object.assign({}, C.estado(), { lane, x, y }));
    }
    requestAnimationFrame(f);
  })();
});

// Un toque sin gota cerca: busca un carril sin gotas pendientes dentro de la ventana más un margen y toca ahí.
const pifia = () => {
  const C = window.__compas, stage = document.getElementById('stage');
  const e = C.estado(), margen = C.cfg.ventanas.casi * (e.amplia ? C.cfg.ventana_amplia : 1) + 15;
  const libre = [0, 1, 2].find((l) => !e.proximas.some((d) => d.lane === l && Math.abs(d.t - e.T) < margen));
  if (libre === undefined) throw new Error('no hay un carril libre para probar un toque sin gota');
  const r = stage.getBoundingClientRect();
  stage.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerType: 'mouse', isPrimary: true, button: 0, clientX: r.left + (r.width * (libre + 0.5)) / 3, clientY: r.top + r.height / 2 }));
  return Object.assign({}, C.estado(), { lane: libre });
};

module.exports = {
  listo: '#cv',
  clip: { ancho: 600, alto: 720 },   // el juego es vertical: el clip principal también
  gif: { ultimos: 13, duracion: 12 },   // termina con la tarjeta de récord
  async jugar(page, ctx) {
    const { modo, medios, log, assert, slug } = ctx;
    const video = modo === 'video';
    const tactil = slug === 'celular';
    const E = () => page.evaluate(() => window.__compas.estado());
    const G = (o) => page.evaluate(golpe, o);
    const tocar = (sel) => { const l = typeof sel === 'string' ? page.locator(sel) : sel; return tactil ? l.tap() : l.click(); };
    const aciertos = (e) => e.perfectos + e.bien + e.casi;
    const esperarJuego = () => page.waitForFunction(() => window.__compas.estado().fase === 'juego', null, { timeout: 7000 });
    const conflicto = (g, lista, margen) => lista.some((o) => o !== g && o.lane === g.lane && o.t > g.t && o.t - g.t < margen);
    // toca perfecto las gotas que estorbarían (otra gota del mismo carril muy cerca) hasta que la siguiente quede aislada
    const aislada = async (margen) => {
      for (let i = 0; i < 8; i++) {
        const e = await E();
        if (!e.siguiente || !conflicto(e.siguiente, e.proximas, margen)) return e;
        await G({ desfase: 0, soltar: true });
      }
      throw new Error('no apareció una gota aislada');
    };
    await page.goto(page.url().split('?')[0] + '?demo=1');
    await page.waitForSelector('#cv');
    await sleep(500);

    if (video) {
      await sleep(1300);
      await tocar('#btnJugar');
      await esperarJuego();
      let i = 0;
      for (;;) {
        const e = await E();
        if (e.fase !== 'juego' || !e.siguiente) break;
        i++;
        try {
          if (i % 11 === 0) { await G({ desfase: 0, soltar: false }); await sleep(260); }   // un fallo a propósito: la racha se rompe y se arma de nuevo
          else await G({ desfase: i % 5 === 0 ? 90 : 0, soltar: true });
        } catch (err) { if ((await E()).fase !== 'juego') break; }
      }
      await page.waitForFunction(() => window.__compas.estado().fase === 'fin', null, { timeout: 20000 });
      await sleep(3200);   // pantalla final con el récord
      return { puntos: (await E()).puntos };
    }

    const P = await page.evaluate(() => window.__compas.cfg);
    let e = await E();
    assert(e.fase === 'inicio', 'la partida debería esperar en la pantalla de inicio (' + e.fase + ')');
    assert((await page.isVisible('#ovInicio')) && (await page.isVisible('#btnJugar')), 'no se ve la tarjeta de inicio');
    assert((await page.locator('#animos input').count()) === 3, 'deberían ofrecerse tres ánimos');
    assert(e.animo === 'alegre' && (await page.isChecked('#animos input[value=alegre]')), 'el ánimo inicial debería ser «alegre» (' + e.animo + ')');
    log('  idioma al abrir: ' + (await page.evaluate(() => document.documentElement.lang)) + ' · canción «' + e.animo + '» a ' + e.bpm + ' bpm con ' + e.total + ' gotas');
    assert(e.total >= 25, 'la canción demo debería tener al menos 25 gotas (' + e.total + ')');
    await tocar('#btnJugar');
    await esperarJuego();
    assert(!(await page.isVisible('#ovInicio')), 'la tarjeta de inicio sigue visible durante la partida');
    const sellos = await page.evaluate(() => window.GGX.marca.estado().sellos);
    assert(sellos >= 1, 'la marca no mostró su sello al empezar (' + sellos + ')');

    // 1) Racha de perfectos: 100 puntos cada uno y, al llegar a 10 seguidos, multiplicador ×2
    const esperado = (n) => 100 * Math.min(n, 10) + 200 * Math.max(0, n - 10);
    for (let i = 1; i <= 12; i++) {
      e = await G({ desfase: 0, soltar: true });
      assert(e.ultimo && e.ultimo.nivel === 'perfecto' && Math.abs(e.ultimo.dt) <= P.ventanas.perfecto, 'perfecto ' + i + ': ' + JSON.stringify(e.ultimo));
      assert(e.perfectos === i && e.combo === i && e.fallos === 0, 'perfecto ' + i + ': conteo ' + JSON.stringify({ p: e.perfectos, c: e.combo, f: e.fallos }));
      assert(e.puntos === esperado(i), 'perfecto ' + i + ': ' + e.puntos + ' puntos, se esperaban ' + esperado(i));
      if (i === 9) assert(e.mult === 1, 'con 9 seguidos el multiplicador debería seguir en ×1');
      if (i === 10) {
        assert(e.mult === 2, 'con 10 seguidos el multiplicador debería ser ×2 (' + e.mult + ')');
        await sleep(120);
        const aviso = await page.textContent('#ggx-live');
        assert(/2/.test(aviso || ''), 'el aviso para lector de pantalla no anunció el multiplicador: «' + aviso + '»');
        assert((await page.textContent('#mult')).includes('2'), 'el marcador no muestra el multiplicador');
      }
    }
    assert(e.musica && (await page.evaluate(() => window.GGX.music.estado().sonando)), 'la música no estaba sonando durante la partida');
    log('  12 perfectos seguidos: ' + e.puntos + ' puntos, multiplicador ×' + e.mult + ' (aviso: «' + (await page.textContent('#ggx-live')) + '»)');
    if (slug === 'escritorio') await page.screenshot({ path: medios + '/portada-fuente.png', clip: await page.locator('#stage').boundingBox() });
    await page.screenshot({ path: medios + '/captura-juego-' + slug + '.png' });

    // 2) Un acierto «bien» y uno «casi»: calificación por ventana, puntos con el multiplicador y la racha como corresponde
    await aislada(400);
    let a = await E();
    e = await G({ desfase: 100, soltar: true });
    assert(e.ultimo.nivel === 'bien' && Math.abs(e.ultimo.dt) > P.ventanas.perfecto && Math.abs(e.ultimo.dt) <= P.ventanas.bien, '«bien»: ' + JSON.stringify(e.ultimo));
    assert(e.puntos === a.puntos + P.puntos.bien * a.mult && e.bien === a.bien + 1 && e.combo === a.combo + 1, '«bien» sumó mal: ' + a.puntos + ' → ' + e.puntos);
    log('  «bien» (' + e.ultimo.dt + ' ms): +' + (e.puntos - a.puntos) + ' puntos con ×' + a.mult);
    await aislada(400);
    a = await E();
    e = await G({ desfase: 165, soltar: true });
    assert(e.ultimo.nivel === 'casi' && Math.abs(e.ultimo.dt) > P.ventanas.bien && Math.abs(e.ultimo.dt) <= P.ventanas.casi, '«casi»: ' + JSON.stringify(e.ultimo));
    assert(e.puntos === a.puntos + P.puntos.casi * a.mult && e.casi === a.casi + 1 && e.combo === a.combo, '«casi» sumó mal o tocó la racha: ' + a.combo + ' → ' + e.combo);
    log('  «casi» (' + e.ultimo.dt + ' ms): +' + (e.puntos - a.puntos) + ' puntos y la racha se mantiene (' + e.combo + ')');

    // 3) Entradas reales: clic o toque en el carril, flechas, letras y barra espaciadora
    const caja = await page.locator('#stage').boundingBox();
    const real = async (nombre, accion, carril) => {
      const antes = await E();
      const g = await G({ desfase: 0, adelanto: 25, soltar: false, carril });
      await accion(g, caja);
      await sleep(90);
      const des = await E();
      assert(aciertos(des) === aciertos(antes) + 1 && des.ultimo.lane === g.lane && !['pifia', 'fallo'].includes(des.ultimo.nivel), nombre + ' no acertó la gota del carril ' + g.lane + ': ' + JSON.stringify(des.ultimo));
      log('  ' + nombre + ' → carril ' + g.lane + ': «' + des.ultimo.nivel + '» (' + des.ultimo.dt + ' ms)');
    };
    await real(tactil ? 'toque real' : 'clic real', async (g, c) => {
      const x = c.x + (c.width * (g.lane + 0.5)) / 3, y = c.y + c.height / 2;
      if (tactil) await page.touchscreen.tap(x, y); else await page.mouse.click(x, y);
    });
    await real('flechas', (g) => page.keyboard.press(['ArrowLeft', 'ArrowDown', 'ArrowRight'][g.lane]));
    await real('letras A S D', (g) => page.keyboard.press(['KeyA', 'KeyS', 'KeyD'][g.lane]));
    await real('barra espaciadora (carril central)', () => page.keyboard.press('Space'), 1);

    // 4) Un toque sin gota cerca rompe la racha sin quitar puntos; una gota que se pasa es un fallo y también la rompe
    e = await G({ desfase: 0, soltar: true });
    assert(e.combo >= 1, 'antes de la pifia debería haber racha');
    a = e;
    e = await page.evaluate(pifia);
    assert(e.ultimo.nivel === 'pifia' && e.pifias === 1 && e.combo === 0 && e.mult === 1 && e.puntos === a.puntos, 'una pifia debía romper la racha sin quitar puntos: ' + JSON.stringify({ u: e.ultimo, p: e.pifias, c: e.combo, m: e.mult, pts: e.puntos }));
    log('  toque sin gota: racha ' + a.combo + ' → 0, puntos intactos (' + e.puntos + ')');
    a = await G({ desfase: 0, soltar: true });
    assert(a.combo >= 1, 'antes del fallo debería haber racha');
    const f0 = a.fallos;
    await page.waitForFunction((n) => window.__compas.estado().fallos > n, f0, { timeout: 4000 });
    e = await E();
    assert(e.fallos === f0 + 1 && e.combo === 0 && e.mult === 1, 'una gota que se pasa debía ser un fallo y romper la racha: ' + JSON.stringify({ f: e.fallos, c: e.combo }));
    log('  gota que se pasa: fallo ' + e.fallos + ', racha 0');

    // 5) Fin de la canción: tarjeta final, récord por ánimo, sonidos y música detenida
    await page.waitForFunction(() => window.__compas.estado().fase === 'fin', null, { timeout: 25000 });
    await sleep(300);
    e = await E();
    assert(await page.isVisible('#ovFin'), 'no apareció la tarjeta final');
    log('  final: «' + (await page.textContent('#fT')) + '» · ' + (await page.textContent('#fP')) + ' · ' + (await page.textContent('#fD')));
    assert(e.record === true, 'la primera partida debía ser récord');
    assert(aciertos(e) + e.fallos === e.total, 'cada gota debía quedar como acierto o fallo (' + aciertos(e) + ' + ' + e.fallos + ' vs ' + e.total + ')');
    assert((await page.textContent('#fP')).includes(String(e.puntos)), 'la tarjeta final no muestra los puntos');
    const mejor = await page.evaluate(() => JSON.parse(localStorage.getItem('compas-gelatina:mejor')));
    assert(mejor && mejor.alegre === e.puntos, 'el récord guardado no coincide con los puntos: ' + JSON.stringify(mejor) + ' vs ' + e.puntos);
    await page.screenshot({ path: medios + '/captura-final-' + slug + '.png' });
    const plays = await page.evaluate(() => window.GGX.sfx.plays);
    log('  sonidos disparados: ' + JSON.stringify(plays));
    for (const n of ['click', 'coin', 'pop', 'merge', 'error']) assert((plays[n] || 0) > 0, 'el sonido «' + n + '» nunca se disparó');
    assert((plays.win || 0) + (plays.lose || 0) > 0, 'no sonó el final de la canción');
    const mus = await page.evaluate(() => window.GGX.music.estado());
    log('  música: ' + JSON.stringify(mus));
    assert(!mus.sonando && mus.compases >= 6 && mus.notas > 20, 'la música debía haber sonado y quedar detenida: ' + JSON.stringify(mus));
    const puntosAlegre = e.puntos, totalAlegre = e.total;

    // 6) Cambiar de ánimo: otro tempo y otra canción; la ventana amplia vuelve «perfecto» un acierto que antes era «bien»
    await tocar('#btnAnimo');
    await sleep(150);
    e = await E();
    assert(e.fase === 'inicio' && (await page.isVisible('#ovInicio')), 'Cambiar ánimo debía volver a la pantalla de inicio (' + e.fase + ')');
    await tocar('#animos input[value=tension]');   // el selector es un grupo de botones de opción: la casilla transparente cubre su etiqueta
    e = await E();
    assert(e.animo === 'tension' && e.bpm === 128, 'al elegir «tensión» el tempo debía ser 128 bpm: ' + JSON.stringify({ a: e.animo, b: e.bpm }));
    assert((await page.evaluate(() => JSON.parse(localStorage.getItem('compas-gelatina:animo')))) === 'tension', 'el ánimo elegido no se guardó');
    await tocar('#amplia');
    e = await E();
    assert(e.amplia === true, 'la casilla de ventana amplia no se activó');
    log('  «tensión»: ' + e.bpm + ' bpm, ' + e.total + ' gotas (la de «alegre» tenía ' + totalAlegre + ') · ventana amplia activada');
    await tocar('#btnJugar');
    await esperarJuego();
    await aislada(450);
    a = await E();
    e = await G({ desfase: 95, soltar: true });
    assert(e.ultimo.nivel === 'perfecto' && e.ultimo.dt > P.ventanas.perfecto, 'con la ventana amplia, ' + e.ultimo.dt + ' ms tarde debía ser «perfecto»: ' + JSON.stringify(e.ultimo));
    log('  con ventana amplia, un toque ' + e.ultimo.dt + ' ms tarde cuenta como «perfecto» (sin ella era «bien»)');
    assert((await page.evaluate(() => window.GGX.music.estado())).animo === 'tension', 'la música no cambió de ánimo');

    // 7) Idiomas: el selector ofrece todos, cada texto sigue al idioma, <html lang> lleva la etiqueta correcta y el chino se ve con sus caracteres
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
      const esperadoT = await page.evaluate((x) => window.JUEGO.textos[x].titulo, l);
      assert(est.lang === l, 'al elegir ' + l + ' el motor quedó en ' + est.lang);
      assert(est.titulo === esperadoT && est.doc === esperadoT, 'el título no siguió al idioma ' + l + ': «' + est.titulo + '» / «' + est.doc + '» vs «' + esperadoT + '»');
      assert(est.etiqueta === (l === 'zh' ? 'zh-Hans' : l), 'html lang es «' + est.etiqueta + '» en ' + l);
      const mejorEsperado = await page.evaluate((x) => window.JUEGO.textos[x].mejor, l);
      assert(est.mejor.startsWith(mejorEsperado), 'el marcador «' + est.mejor + '» no empieza por «' + mejorEsperado + '» en ' + l);
      if (l === 'zh') assert(/PingFang|YaHei|Noto Sans CJK|Hiragino|Noto Sans SC|WenQuanYi/.test(est.fuente), 'la pila tipográfica del título no incluye fuentes chinas: ' + est.fuente);
      await page.screenshot({ path: medios + '/captura-idioma-' + l + '-' + slug + '.png' });
    }
    // el chino debe dibujarse de verdad: no puede medir lo mismo que con cuadros vacíos
    const trazo = await page.evaluate(() => {
      const c = document.createElement('canvas').getContext('2d');
      const fam = (window.GGX.cjk || '') + ', sans-serif';
      const m = (txt, f) => { c.font = '32px ' + f; return Math.round(c.measureText(txt).width); };
      return { chino: m('果冻节拍', fam), sinFuente: m('果冻节拍', '"NoExisteEstaFuente123"') };
    });
    log('  medida de «果冻节拍» a 32 px: ' + trazo.chino + ' px con la pila china');
    assert(trazo.chino >= 80 && trazo.chino <= 150, 'la medida del texto chino (' + trazo.chino + ' px) no parece de caracteres reales');
    const lang1 = idiomas[idiomas.length - 1];
    assert((await page.evaluate(() => window.GGX.lang)) === lang1, 'el último idioma probado no quedó activo');

    // 8) Tras recargar siguen el idioma, el ánimo, la ventana amplia y el récord de «alegre»; y ?lang=en manda sobre lo guardado
    await page.reload();
    await page.waitForSelector('#cv');
    await sleep(500);
    e = await E();
    assert((await page.evaluate(() => window.GGX.lang)) === lang1, 'el idioma elegido no se recordó al recargar');
    assert(e.animo === 'tension' && e.amplia === true && e.fase === 'inicio', 'tras recargar debían seguir «tensión» y la ventana amplia: ' + JSON.stringify({ a: e.animo, w: e.amplia, f: e.fase }));
    const guardado = await page.evaluate(() => JSON.parse(localStorage.getItem('compas-gelatina:mejor')));
    assert(guardado && guardado.alegre === puntosAlegre, 'el récord de «alegre» no sobrevivió a la recarga: ' + JSON.stringify(guardado));
    await page.goto(page.url().split('?')[0] + '?demo=1&lang=en');
    await page.waitForSelector('#cv');
    assert((await page.evaluate(() => window.GGX.lang)) === 'en', '?lang=en no cambió el idioma');
    log('  tras recargar: idioma (' + lang1 + '), ánimo y ventana amplia se mantienen, el récord de «alegre» (' + puntosAlegre + ') también, y ?lang=en lo cambia');
    return { puntos: puntosAlegre };
  },
};
