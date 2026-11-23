// Prueba el motor común y sus módulos en un Chromium real, sin ningún juego de por medio.
// Uso: node herramientas/probar_motor.js <pagina.html>   (la página la arma `python3 fabrica.py motor probar`: núcleo + todos los módulos)
// Imprime una sola línea JSON con el resultado: {nucleo: {pruebas, fallas, fallos:[…]}, modulos: {nombre: {…}}, errores_de_pagina: […]}
const { chromium } = require('playwright');

const pagina = process.argv[2];
if (!pagina) { console.error('Uso: node herramientas/probar_motor.js <pagina.html>'); process.exit(2); }
const url = 'file://' + require('path').resolve(pagina);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const resultado = {};
const chequear = (grupo, ok, texto) => {
  const g = (resultado[grupo] = resultado[grupo] || { pruebas: 0, fallas: 0, fallos: [] });
  g.pruebas++;
  if (!ok) { g.fallas++; g.fallos.push(texto); }
};

async function abrir(browser, opts, query) {
  const ctx = await browser.newContext(Object.assign({ viewport: { width: 800, height: 600 }, locale: 'es-MX' }, opts));
  const page = await ctx.newPage();
  const errores = [];
  page.on('pageerror', (e) => errores.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error') errores.push('consola: ' + m.text()); });
  await page.goto(url + (query || ''));
  await page.waitForFunction(() => !!window.GGX);
  return { ctx, page, errores };
}

async function nucleo(browser) {
  const { ctx, page, errores } = await abrir(browser);
  const r = await page.evaluate(() => {
    const G = window.GGX, a = G.rng(42), b = G.rng(42);
    const sa = [a(), a(), a(), a()], sb = [b(), b(), b(), b()];
    G.store.set('x', { n: 3 });
    return { version: G.version, igual: JSON.stringify(sa) === JSON.stringify(sb), rango: sa.every((v) => v >= 0 && v < 1), guardado: G.store.get('x', null), lang: G.lang,
      t: G.t('clave-que-no-existe'), jelly: typeof G.draw.jelly, sfx: G.sfx.names.length };
  });
  chequear('nucleo', /^\d+\.\d+\.\d+$/.test(r.version), 'GGX.version tiene forma 1.2.3 (hoy «' + r.version + '»)');
  chequear('nucleo', r.igual && r.rango, 'GGX.rng es reproducible y queda en [0, 1)');
  chequear('nucleo', r.guardado && r.guardado.n === 3, 'GGX.store guarda y devuelve');
  chequear('nucleo', r.t === 'clave-que-no-existe', 'GGX.t devuelve la clave si falta el texto');
  chequear('nucleo', r.jelly === 'function' && r.sfx >= 10, 'la gelatina de la casa y los efectos de sonido están');
  chequear('nucleo', errores.length === 0, 'sin errores de consola ni de página' + (errores.length ? ': ' + errores.join(' || ') : ''));
  await ctx.close();
}

async function accesible(browser) {
  const M = 'accesible';
  let { ctx, page, errores } = await abrir(browser);
  const ini = await page.evaluate(() => ({ mov: GGX.a11y.reducedMotion(), con: GGX.a11y.highContrast(), attr: document.documentElement.hasAttribute('data-reducir-movimiento') }));
  chequear(M, ini.mov === false && ini.con === false && ini.attr === false, 'sin pedir nada, no se reduce el movimiento ni cambia el contraste');
  await page.evaluate(() => GGX.a11y.set('reducirMovimiento', true));
  chequear(M, await page.evaluate(() => GGX.a11y.reducedMotion() && document.documentElement.hasAttribute('data-reducir-movimiento')), 'pedir menos movimiento lo activa y marca la página');
  await page.reload(); await page.waitForFunction(() => !!window.GGX && !!GGX.a11y && document.readyState === 'complete');   // sin esperar a la carga completa, a veces se lee antes de que el módulo aplique lo guardado
  chequear(M, await page.evaluate(() => GGX.a11y.reducedMotion()), 'la elección sobrevive a recargar la página');
  await page.evaluate(() => GGX.a11y.set('reducirMovimiento', null));
  chequear(M, !(await page.evaluate(() => GGX.a11y.reducedMotion())), 'null vuelve a seguir al sistema');
  await page.evaluate(() => GGX.a11y.set('altoContraste', true));
  const cont = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--ink').trim());
  chequear(M, cont === '#000', 'alto contraste cambia las variables de color de la interfaz');
  await page.evaluate(() => { GGX.a11y.set('altoContraste', null); window.__avisos = 0; GGX.a11y.onChange(() => { window.__avisos++; }); GGX.a11y.set('reducirMovimiento', true); });
  chequear(M, (await page.evaluate(() => window.__avisos)) === 1, 'onChange avisa una vez por cambio');
  await page.evaluate(() => GGX.a11y.announce('Puntaje 10'));
  await sleep(120);
  chequear(M, (await page.evaluate(() => { const e = document.getElementById('ggx-live'); return e && e.getAttribute('role') + '|' + e.textContent; })) === 'status|Puntaje 10', 'announce escribe en una región «status» para lectores de pantalla');
  // botón y panel
  await page.evaluate(() => { GGX.a11y.set('reducirMovimiento', false); GGX.ui.accessButton(document.body); });
  const b = page.locator('.ggx-a11y-btn');
  chequear(M, (await b.getAttribute('aria-expanded')) === 'false' && (await page.locator('.ggx-a11y-panel').isHidden()), 'el panel empieza cerrado');
  await b.click();
  chequear(M, (await b.getAttribute('aria-expanded')) === 'true' && (await page.locator('.ggx-a11y-panel').isVisible()), 'el botón abre el panel y lo declara con aria-expanded');
  await page.locator('.ggx-a11y-panel input').first().check();
  chequear(M, await page.evaluate(() => GGX.a11y.reducedMotion()), 'la casilla «reducir movimiento» cambia el ajuste');
  await page.keyboard.press('Escape');
  chequear(M, await page.locator('.ggx-a11y-panel').isHidden() && (await page.evaluate(() => document.activeElement.className.includes('ggx-a11y-btn'))), 'Escape cierra el panel y devuelve el foco al botón');
  chequear(M, (await b.getAttribute('aria-label')) === 'Accesibilidad', 'el botón tiene nombre accesible en español');
  chequear(M, errores.length === 0, 'sin errores de consola ni de página' + (errores.length ? ': ' + errores.join(' || ') : ''));
  await ctx.close();
  // idiomas y preferencia del sistema
  for (const [l, esperado] of [['en', 'Accessibility'], ['zh', '无障碍']]) {
    ({ ctx, page } = await abrir(browser, {}, '?lang=' + l));
    chequear(M, (await page.evaluate(() => GGX.t('a11y_titulo'))) === esperado, 'texto del panel en «' + l + '»');
    await ctx.close();
  }
  ({ ctx, page } = await abrir(browser, { reducedMotion: 'reduce' }));
  chequear(M, await page.evaluate(() => GGX.a11y.reducedMotion()), 'si el sistema pide menos movimiento, se respeta sin que el jugador haga nada');
  await ctx.close();
}

async function efectos(browser) {
  const M = 'efectos';
  let { ctx, page, errores } = await abrir(browser);
  const r = await page.evaluate(() => {
    const fx = GGX.fx; fx.clear(); fx.semilla(7);
    const n = fx.burst(100, 100, { n: 20, color: ['#f00', '#0f0'] });
    const vivos = fx.count();
    const excedido = fx.burst(0, 0, { n: 100000 });
    const tope = fx.count() <= fx.maximo;
    fx.clear(); fx.semilla(7); fx.burst(100, 100, { n: 5 }); fx.update(0.016);
    const a = JSON.stringify(fx.count());
    for (let i = 0; i < 200; i++) fx.update(0.016);
    const fin = fx.count();
    fx.shake(10, 200); fx.update(0.016); const o1 = fx.offset();
    for (let i = 0; i < 40; i++) fx.update(0.016);
    const o2 = fx.offset();
    fx.clear(); fx.text(50, 50, '¡Perfecto!'); const conTexto = fx.count();
    fx.flash('#fff', 100, 0.6);
    // dibujo real: debe quedar algo pintado
    const cv = document.createElement('canvas'); cv.width = cv.height = 200; const c = cv.getContext('2d');
    fx.clear(); fx.burst(100, 100, { n: 30, color: '#ff0000', vel: 0, gravedad: 0, tam: 6, vida: 5 }); fx.update(0.01); fx.draw(c, 200, 200);
    const px = c.getImageData(0, 0, 200, 200).data; let pintados = 0; for (let i = 3; i < px.length; i += 4) if (px[i] > 0) pintados++;
    fx.clear();
    const p = fx.presets.map((nombre) => [nombre, fx.preset(nombre, 10, 10)]); fx.clear();
    return { n, vivos, excedido, tope, a, fin, o1, o2, conTexto, pintados, p, desconocido: fx.preset('no-existe', 0, 0) };
  });
  chequear(M, r.n === 20 && r.vivos === 20, 'burst crea las partículas pedidas');
  chequear(M, r.tope, 'nunca hay más partículas que el tope (' + 400 + ')');
  chequear(M, r.fin === 0, 'las partículas mueren solas con el tiempo');
  chequear(M, Math.abs(r.o1.x) + Math.abs(r.o1.y) > 0 && r.o2.x === 0 && r.o2.y === 0, 'la sacudida desplaza la pantalla y termina en cero');
  chequear(M, r.conTexto === 1, 'text agrega un texto flotante');
  chequear(M, r.pintados > 100, 'draw pinta las partículas en el canvas (' + r.pintados + ' píxeles)');
  chequear(M, r.p.length === 4 && r.p.every(([, n]) => n > 0) && r.desconocido === 0, 'los cuatro presets crean partículas y uno desconocido no hace nada');
  const dos = await page.evaluate(() => { const fx = GGX.fx; const cuenta = () => { fx.clear(); fx.semilla(99); fx.burst(0, 0, { n: 6 }); fx.update(0.02); const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d'); fx.draw(x, 64, 64); return Array.from(x.getImageData(0, 0, 64, 64).data).join(','); }; return cuenta() === cuenta(); });
  chequear(M, dos, 'con la misma semilla las partículas salen iguales');
  chequear(M, errores.length === 0, 'sin errores de consola ni de página' + (errores.length ? ': ' + errores.join(' || ') : ''));
  await ctx.close();
  // con «menos movimiento» no hay partículas ni sacudida ni destello
  ({ ctx, page } = await abrir(browser, { reducedMotion: 'reduce' }));
  const q = await page.evaluate(() => { const fx = GGX.fx; fx.clear(); const n = fx.burst(0, 0, { n: 10 }); fx.shake(20, 300); fx.flash('#fff', 100); fx.update(0.016); fx.text(5, 5, 'x'); return { n, off: fx.offset(), cuenta: fx.count(), preset: fx.preset('confeti', 1, 1) }; });
  chequear(M, q.n === 0 && q.preset === 0 && q.off.x === 0 && q.off.y === 0 && q.cuenta === 1, 'con «reducir movimiento»: sin partículas, sacudida ni destello (el texto sí aparece, quieto)');
  await ctx.close();
}

async function musica(browser) {
  const M = 'musica';
  const { ctx, page, errores } = await abrir(browser);
  const r = await page.evaluate(() => {
    const m = GGX.music, A = m.plan(5, { animo: 'alegre', compases: 8 }), B = m.plan(5, { animo: 'alegre', compases: 8 }), C = m.plan(6, { animo: 'alegre', compases: 8 });
    const pent = [0, 2, 4, 7, 9];
    const melodia = A.compases.flatMap((c) => c.notas.filter((n) => n.voz === 'melodia'));
    const enEscala = melodia.every((n) => pent.includes(((n.midi - A.raiz) % 12 + 12) % 12));
    const capa0 = new Set(A.compases.flatMap((c) => c.notas.filter((n) => n.capa === 0).map((n) => n.voz)));
    const tiempos = A.compases.every((c) => c.notas.every((n) => n.t >= 0 && n.t < 4));
    return { igual: JSON.stringify(A) === JSON.stringify(B), distinta: JSON.stringify(A) !== JSON.stringify(C), ocho: A.compases.length, hayMelodia: melodia.length > 4, enEscala, capa0: [...capa0].sort().join(','), tiempos,
      animos: m.animos.join(','), todos: m.animos.every((a) => m.plan(1, { animo: a, compases: 4 }).compases.length === 4), bpmTension: m.plan(1, { animo: 'tension' }).bpm };
  });
  chequear(M, r.igual && r.distinta, 'la misma semilla da la misma partitura y otra semilla da otra');
  chequear(M, r.ocho === 8 && r.tiempos, 'la partitura tiene los compases pedidos y todas las notas caen dentro del compás');
  chequear(M, r.hayMelodia && r.enEscala, 'la melodía solo usa notas de la escala del ánimo');
  chequear(M, r.capa0 === 'bajo,bombo', 'en la capa mínima solo suenan bajo y bombo (el resto entra con la intensidad)');
  chequear(M, r.animos === 'alegre,tension,calma,aventura' && r.todos && r.bpmTension > 120, 'los cuatro ánimos generan partitura');
  await page.mouse.click(100, 100);                            // un gesto del jugador, como exige el navegador
  const s = await page.evaluate(async () => {
    const m = GGX.music, ok = m.start({ animo: 'calma', semilla: 3, intensidad: 1 });
    await new Promise((r) => setTimeout(r, 400));
    const e1 = m.estado();
    m.stop(); const e2 = m.estado();
    GGX.setMuted(true); const ok2 = m.start('alegre'); await new Promise((r) => setTimeout(r, 200)); const e3 = m.estado(); m.stop(); GGX.setMuted(false);
    const por_compas = async (inten) => {   // cuántas notas por compás se programan con esa intensidad
      const a = m.estado(); m.start({ animo: 'alegre', semilla: 3, intensidad: inten }); await new Promise((r) => setTimeout(r, 150)); const b = m.estado(); m.stop();
      return (b.notas - a.notas) / Math.max(1, b.compases - a.compases);
    };
    const bajo = await por_compas(0), alto = await por_compas(1);
    return { ok, e1, e2, ok2, e3, bajo, alto };
  });
  chequear(M, s.ok && s.e1.sonando && s.e1.animo === 'calma' && s.e1.compases >= 1 && s.e1.notas > 0, 'start empieza a programar compases y notas');
  chequear(M, s.bajo > 0 && s.alto > s.bajo * 2, 'la intensidad manda: con 0 solo suenan bajo y bombo (' + s.bajo + ' notas por compás) y con 1 entra todo (' + s.alto + ')');
  chequear(M, !s.e2.sonando, 'stop la detiene');
  chequear(M, s.ok2 && s.e3.silencio === true, 'con el juego en silencio, la música lo sabe');
  chequear(M, errores.length === 0, 'sin errores de consola ni de página' + (errores.length ? ': ' + errores.join(' || ') : ''));
  await ctx.close();
}

async function marca(browser) {
  const M = 'marca';
  let { ctx, page, errores } = await abrir(browser);
  const r = await page.evaluate(() => {
    const m = GGX.marca, dp = new DOMParser();
    const doc = dp.parseFromString(m.svg('prueba'), 'image/svg+xml');
    const valido = !doc.querySelector('parsererror') && doc.documentElement.tagName === 'svg';
    const ojos = doc.querySelectorAll('ellipse[rx="16"]').length;
    const rosa = m.svg('r', 'rosa').includes('#c2337a') && !m.svg('r', 'rosa').includes('#15804f');
    const dos = document.createElement('div'); dos.innerHTML = m.svg('uno') + m.svg('dos');
    const ids = [...dos.querySelectorAll('linearGradient')].map((g) => g.id);
    const el = m.emblema(64);
    const d = m.distintivo(document.body, { texto: true });
    return { valido, ojos, rosa, ids: ids.join(','), ancho: el.style.width, etiqueta: d.getAttribute('aria-label'), rol: d.getAttribute('role'), texto: d.textContent, nombre: m.nombre,
      svgOculto: d.querySelector('svg').getAttribute('aria-hidden') };
  });
  chequear(M, r.valido && r.ojos === 2, 'el emblema es un SVG válido con sus dos ojos');
  chequear(M, r.rosa, 'el emblema se puede pintar de rosa sin que quede verde');
  chequear(M, r.ids === 'guno,gdos', 'dos emblemas en la misma página no comparten degradado');
  chequear(M, r.ancho === '64px', 'emblema(px) respeta el tamaño pedido');
  chequear(M, r.rol === 'img' && r.etiqueta === 'Taller Gelatina' && r.texto === 'Taller Gelatina' && r.svgOculto === 'true', 'el distintivo se anuncia una sola vez, como imagen con nombre');
  // sello completo (un gesto antes para que el sonido esté permitido)
  await page.mouse.click(50, 50);
  const t0 = Date.now();
  const durante = await page.evaluate(async () => {
    const p = GGX.marca.sello({ al_terminar: () => { window.__terminó = true; } });
    await new Promise((r) => setTimeout(r, 200));
    const visible = !!document.querySelector('.ggx-sello') && document.querySelector('.ggx-sello .nom').textContent === 'Taller Gelatina' && document.querySelector('.ggx-sello').getAttribute('aria-hidden') === 'true';
    const res = await p;
    return { visible, res, terminó: window.__terminó === true, blups: GGX.marca.estado().blups };
  });
  const dur = Date.now() - t0;
  chequear(M, durante.visible, 'el sello se ve, dice el nombre y es decorativo (aria-hidden)');
  chequear(M, durante.res.omitido === false && durante.res.saltado === false && durante.terminó, 'el sello termina solo y avisa con al_terminar');
  chequear(M, dur > 1200 && dur < 2600, 'dura alrededor de 1,4 s (' + dur + ' ms)');
  chequear(M, durante.blups === 1, 'suena el «blup» una vez');
  await sleep(400);
  chequear(M, (await page.locator('.ggx-sello').count()) === 0, 'el sello se retira solo de la página');
  const otra = await page.evaluate(async () => { const r = await GGX.marca.sello(); return { r, sellos: GGX.marca.estado().sellos }; });
  chequear(M, otra.r.omitido === true && otra.sellos === 1, 'una vez por visita: la segunda llamada no vuelve a mostrarlo');
  // saltarlo con un toque
  const salto = await page.evaluate(async () => {
    const t = performance.now(); const p = GGX.marca.sello({ forzar: true });
    await new Promise((r) => setTimeout(r, 120));
    document.querySelector('.ggx-sello').dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
    const res = await p; return { res, ms: performance.now() - t };
  });
  chequear(M, salto.res.saltado === true && salto.ms < 600, 'un toque salta el sello (' + Math.round(salto.ms) + ' ms)');
  await sleep(350);
  const tecla = await page.evaluate(async () => { const p = GGX.marca.sello({ forzar: true }); await new Promise((r) => setTimeout(r, 100)); window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); return (await p).saltado; });
  chequear(M, tecla === true, 'una tecla también salta el sello');
  await sleep(350);
  const mudo = await page.evaluate(async () => { GGX.setMuted(true); const a = GGX.marca.estado().blups; const sono = GGX.marca.blup(); GGX.setMuted(false); return { sono, igual: GGX.marca.estado().blups === a }; });
  chequear(M, mudo.sono === false && mudo.igual, 'con el juego en silencio, el «blup» no suena');
  chequear(M, errores.length === 0, 'sin errores de consola ni de página' + (errores.length ? ': ' + errores.join(' || ') : ''));
  await ctx.close();
  // con «menos movimiento»: quieto, sin animación
  ({ ctx, page } = await abrir(browser, { reducedMotion: 'reduce' }));
  const q = await page.evaluate(async () => {
    const t = performance.now(); const p = GGX.marca.sello();
    await new Promise((r) => setTimeout(r, 100));
    const el = document.querySelector('.ggx-sello'); const quieto = el.hasAttribute('data-quieto'); const anim = getComputedStyle(el.querySelector('.gel')).animationName;
    const res = await p; return { quieto, anim, ms: performance.now() - t, res };
  });
  chequear(M, q.quieto && q.anim === 'none' && q.ms < 1100 && q.res.saltado === false, 'con «reducir movimiento» el sello no se anima y dura menos de un segundo (' + Math.round(q.ms) + ' ms)');
  await ctx.close();
}

async function anuncios(browser) {
  const M = 'anuncios';
  let { ctx, page, errores } = await abrir(browser);
  // por defecto está apagado: sin proveedor no hay anuncio, el juego sigue y no se carga nada de afuera
  const base = await page.evaluate(() => {
    let n = 0; const r = GGX.ads.intermedio('fin_de_partida', () => { n++; });
    let rec = null; GGX.ads.recompensa('vida', { ok: () => { rec = 'ok'; }, no: (m) => { rec = m; } });
    return { r, n, rec, disp: GGX.ads.recompensaDisponible(), e: GGX.ads.estado(), externos: [...document.scripts].filter((s) => /googlesyndication|crazygames|poki/.test(s.src)).length };
  });
  chequear(M, base.r === false && base.n === 1 && base.e.proveedor === 'ninguno' && base.e.mostrados === 0, 'sin proveedor no hay anuncio y el juego sigue enseguida (al_terminar corre una vez)');
  chequear(M, base.rec === 'sin_proveedor' && base.disp === false, 'sin proveedor la recompensa no se concede y el botón de recompensa no debe mostrarse');
  chequear(M, base.externos === 0, 'sin proveedor no se carga ningún script de afuera');
  await ctx.close();

  // AdSense simulado: reglas propias, silencio y pausa solo mientras suena
  ({ ctx, page, errores } = await abrir(browser));
  const ad = await page.evaluate(async () => {
    const espera = (ms) => new Promise((r) => setTimeout(r, ms)), reg = [], out = {};
    window.adConfig = () => {};
    window.adBreak = (o) => {
      reg.push(o.type);
      const mostrar = () => { o.beforeAd(); reg.push('mudo:' + GGX.muted() + ',pausa:' + document.documentElement.hasAttribute('data-anuncio')); setTimeout(() => { if (o.type === 'reward' && window.__ver) o.adViewed(); o.afterAd(); o.adBreakDone({ breakStatus: 'viewed' }); }, 30); };
      if (o.type === 'reward') o.beforeReward(mostrar); else mostrar();
    };
    GGX.ads.configurar({ proveedor: 'adsense', sdk: false, reglas: { espera_inicial_s: 0, min_entre_s: 1000, max_por_sesion: 2, recompensa_min_entre_s: 0 } });
    let pausas = 0, reanudas = 0; GGX.ads.alPausar(() => pausas++); GGX.ads.alReanudar(() => reanudas++);
    let cb = 0; const cuenta = () => cb++;
    GGX.ads.intermedio('fin_de_partida', cuenta); out.antes = { cb, motivo: GGX.ads.estado().ultimoRechazo };           // aún sin tocar nada
    window.dispatchEvent(new Event('keydown'));
    GGX.ads.intermedio('menu', cuenta); out.menu = { cb, motivo: GGX.ads.estado().ultimoRechazo };
    out.pidio = GGX.ads.intermedio('fin_de_partida', cuenta); out.durante = { cb };
    await espera(90); out.despues = { cb, mudo: GGX.muted(), pausa: document.documentElement.hasAttribute('data-anuncio'), pausas, reanudas, mostrados: GGX.ads.estado().mostrados };
    GGX.ads.intermedio('fin_de_nivel', cuenta); out.seguido = { cb, motivo: GGX.ads.estado().ultimoRechazo };
    GGX.ads.configurar({ reglas: { min_entre_s: 0 } }); GGX.setMuted(true);
    GGX.ads.intermedio('fin_de_nivel', cuenta); await espera(90); out.mudoPrevio = GGX.muted(); GGX.setMuted(false);
    GGX.ads.intermedio('fin_de_nivel', cuenta); out.tope = { cb, motivo: GGX.ads.estado().ultimoRechazo };
    window.__ver = true; let r1 = null; GGX.ads.recompensa('vida', { ok: () => { r1 = 'ok'; }, no: (m) => { r1 = m; } }); await espera(90);
    window.__ver = false; let r2 = null; GGX.ads.recompensa('vida', { ok: () => { r2 = 'ok'; }, no: (m) => { r2 = m; } }); await espera(90);
    out.r1 = r1; out.r2 = r2; out.disp = GGX.ads.recompensaDisponible(); out.reg = reg; out.e = GGX.ads.estado();
    return out;
  });
  chequear(M, ad.antes.cb === 1 && ad.antes.motivo === 'sin_entrada', 'antes de que el jugador toque algo no se pide anuncio (y el juego sigue)');
  chequear(M, ad.menu.cb === 2 && ad.menu.motivo === 'momento', 'en un menú no se pide anuncio (solo en cortes naturales)');
  chequear(M, ad.pidio === true && ad.durante.cb === 2, 'en un corte natural se pide el anuncio y el juego espera a que termine');
  chequear(M, ad.reg.indexOf('mudo:true,pausa:true') >= 0 && ad.despues.cb === 3 && ad.despues.mudo === false && ad.despues.pausa === false, 'mientras suena: silencio y pausa; al terminar, todo vuelve y el juego sigue');
  chequear(M, ad.despues.pausas === 1 && ad.despues.reanudas === 1 && ad.despues.mostrados === 1, 'el juego recibe una pausa y una reanudación por anuncio');
  chequear(M, ad.seguido.cb === 4 && ad.seguido.motivo === 'frecuencia', 'un segundo anuncio seguido se rechaza por frecuencia');
  chequear(M, ad.mudoPrevio === true, 'si el jugador ya había silenciado el juego, sigue silenciado después del anuncio');
  chequear(M, ad.tope.motivo === 'tope', 'hay un tope de anuncios por visita');
  chequear(M, ad.r1 === 'ok' && ad.r2 === 'descartado' && ad.e.recompensas === 1, 'la recompensa solo se concede si el anuncio se vio completo');
  chequear(M, ad.reg.filter((x) => x === 'reward').length === 2 && ad.reg.filter((x) => x === 'next').length === 2, 'AdSense recibe adBreak de tipo «next» y «reward» (hoy ' + ad.reg.join(',') + ')');
  chequear(M, errores.length === 0, 'AdSense simulado: sin errores de consola ni de página' + (errores.length ? ': ' + errores.join(' || ') : ''));
  await ctx.close();

  // CrazyGames simulado: manda su SDK (sin temporizadores propios); un error no premia
  ({ ctx, page, errores } = await abrir(browser));
  const cg = await page.evaluate(async () => {
    const espera = (ms) => new Promise((r) => setTimeout(r, ms)), reg = [], out = {};
    window.CrazyGames = { SDK: { init: async () => { reg.push('init'); },
      ad: { requestAd: (t, c) => { reg.push(t); c.adStarted(); reg.push('mudo:' + GGX.muted()); setTimeout(() => (window.__fallar ? c.adError('x') : c.adFinished()), 30); } },
      game: { gameplayStart: () => reg.push('start'), gameplayStop: () => reg.push('stop') } } };
    GGX.ads.configurar({ proveedor: 'crazygames' }); await espera(30);
    window.dispatchEvent(new Event('pointerdown'));
    let cb = 0; out.pidio = GGX.ads.intermedio('fin_de_partida', () => cb++); await espera(90);
    out.pidio2 = GGX.ads.intermedio('fin_de_partida', () => cb++); await espera(90);          // sin espera ni separación propias: manda el SDK
    window.__fallar = true; let r = null; GGX.ads.recompensa('vida', { ok: () => { r = 'ok'; }, no: (m) => { r = m; } }); await espera(90);
    let cbError = 0; GGX.ads.intermedio('fin_de_partida', () => cbError++); await espera(90);   // anuncio intermedio con error (Basic Launch, sin relleno): el juego sigue y no queda nada pendiente
    out.cbError = cbError; out.enAnuncio = document.documentElement.hasAttribute('data-anuncio'); out.mudoTrasError = GGX.muted();
    GGX.ads.jugando(true); GGX.ads.jugando(true); GGX.ads.jugando(false); GGX.ads.jugando(false);
    out.cb = cb; out.r = r; out.reg = reg; out.mudo = GGX.muted(); out.e = GGX.ads.estado();
    return out;
  });
  chequear(M, cg.reg[0] === 'init' && cg.pidio === true && cg.pidio2 === true && cg.cb === 2, 'CrazyGames: se inicializa el SDK y se piden anuncios sin temporizadores propios');
  chequear(M, cg.reg.indexOf('midgame') >= 0 && cg.reg.indexOf('mudo:true') >= 0 && cg.mudo === false, 'CrazyGames: «midgame», sonido silenciado mientras suena y restituido al terminar');
  chequear(M, cg.r === 'error' && cg.e.recompensas === 0, 'CrazyGames: si el anuncio con recompensa falla, no se premia');
  chequear(M, cg.cbError === 1 && cg.enAnuncio === false && cg.mudoTrasError === false, 'CrazyGames: si un anuncio intermedio falla (adError), el juego sigue, no queda en pausa ni mudo');
  chequear(M, cg.reg.filter((x) => x === 'start').length === 1 && cg.reg.filter((x) => x === 'stop').length === 1, 'CrazyGames: gameplayStart/Stop no se repiten dos veces seguidas');
  chequear(M, errores.length === 0, 'CrazyGames simulado: sin errores de consola ni de página' + (errores.length ? ': ' + errores.join(' || ') : ''));
  await ctx.close();

  // CrazyGames pide el idioma del jugador según su SDK; el que el jugador ya eligió o la dirección tienen prioridad
  ({ ctx, page, errores } = await abrir(browser, { locale: 'es-MX' }));
  const sdkLoc = (l) => `window.CrazyGames = { SDK: { init: async () => {}, user: { systemInfo: { locale: '${l}' } }, ad: { requestAd: (t, c) => c.adError('x') }, game: { gameplayStart() {}, gameplayStop() {} } } };`;
  const idi = {};
  await page.evaluate(`${sdkLoc('en-US')} GGX.ads.configurar({ proveedor: 'crazygames' });`);
  await page.waitForTimeout(80);
  idi.sin_eleccion = await page.evaluate(() => GGX.lang);
  await page.evaluate(`GGX.setLang('es'); ${sdkLoc('en-GB')} GGX.ads.configurar({ proveedor: 'crazygames' });`);
  await page.waitForTimeout(80);
  idi.con_eleccion = await page.evaluate(() => GGX.lang);
  await ctx.close();
  ({ ctx, page, errores } = await abrir(browser, { locale: 'es-MX' }, '?lang=es'));
  await page.evaluate(`${sdkLoc('en-US')} GGX.ads.configurar({ proveedor: 'crazygames' });`);
  await page.waitForTimeout(80);
  idi.forzado = await page.evaluate(() => GGX.lang);
  await ctx.close();
  chequear(M, idi.sin_eleccion === 'en', 'CrazyGames: sin idioma elegido se usa el que informa su SDK (hoy ' + idi.sin_eleccion + ')');
  chequear(M, idi.con_eleccion === 'es' && idi.forzado === 'es', 'CrazyGames: un idioma ya elegido o forzado en la dirección manda sobre el del SDK');

  // Poki simulado (borrador, se confirma al aceptar el juego)
  ({ ctx, page, errores } = await abrir(browser));
  const pk = await page.evaluate(async () => {
    const espera = (ms) => new Promise((r) => setTimeout(r, ms)), reg = [], out = {};
    window.PokiSDK = { commercialBreak: (antes) => { antes(); reg.push('mudo:' + GGX.muted()); return new Promise((r) => setTimeout(r, 30)); },
      rewardedBreak: (antes) => { antes(); return new Promise((r) => setTimeout(() => r(!!window.__ver), 30)); }, gameplayStart: () => reg.push('start'), gameplayStop: () => reg.push('stop') };
    GGX.ads.configurar({ proveedor: 'poki' }); window.dispatchEvent(new Event('keydown'));
    let cb = 0; GGX.ads.intermedio('fin_de_nivel', () => cb++); await espera(90);
    window.__ver = true; let a = null; GGX.ads.recompensa('vida', { ok: () => { a = 'ok'; }, no: (m) => { a = m; } }); await espera(90);
    window.__ver = false; let b = null; GGX.ads.recompensa('vida', { ok: () => { b = 'ok'; }, no: (m) => { b = m; } }); await espera(90);
    return { cb, a, b, reg, mudo: GGX.muted() };
  });
  chequear(M, pk.cb === 1 && pk.reg.indexOf('mudo:true') >= 0 && pk.mudo === false, 'Poki: commercialBreak con sonido silenciado mientras dura y restituido después');
  chequear(M, pk.a === 'ok' && pk.b === 'descartado', 'Poki: la recompensa depende de lo que devuelve rewardedBreak');
  chequear(M, errores.length === 0, 'Poki simulado: sin errores de consola ni de página' + (errores.length ? ': ' + errores.join(' || ') : ''));
  await ctx.close();
}

async function bots(browser) {
  const M = 'bots';
  // sin ?bot=1 el módulo está inerte: no expone nada ni cambia la página
  let { ctx, page, errores } = await abrir(browser);
  const inerte = await page.evaluate(() => {
    const ok = GGX.bots.registrar({ reiniciar() {}, estado: () => ({}), actuar: () => ({ valida: true }), avanzar() {}, terminado: () => ({ fin: false }) });
    return { activo: GGX.bots.activo, ok, expuesto: typeof window.__bot, marca: document.documentElement.hasAttribute('data-bot') };
  });
  chequear(M, inerte.activo === false && inerte.ok === true && inerte.expuesto === 'undefined' && inerte.marca === false, 'sin ?bot=1 el módulo no expone window.__bot ni marca la página');
  await ctx.close();

  // con ?bot=1: un juego de mentira (cuenta hasta 10) para probar la maquinaria
  ({ ctx, page, errores } = await abrir(browser, {}, '?bot=1&semilla=7'));
  const r = await page.evaluate(() => {
    const out = {};
    let n = 0, t = 0, rr = null, sem = 0;
    GGX.bots.registrar({
      juego: 'prueba', version: '0.0.1',
      reiniciar(semilla) { sem = semilla; rr = GGX.rng(semilla); n = 0; t = 0; return { n }; },
      estado: () => ({ n, t, objetivo: 10 }),
      acciones: () => [{ tipo: 'sumar', rango: [1, 3] }],
      actuar(a) { if (a && a.tipo === 'sumar' && a.v >= 1 && a.v <= 3) { n += a.v + (rr() < 0.2 ? 1 : 0); return { valida: true }; } return { valida: false, motivo: 'acción desconocida' }; },
      avanzar(ms) { t += ms; },
      terminado: () => ({ fin: n >= 10 || t >= 5000, exito: n >= 10, motivo: n >= 10 ? 'meta' : t >= 5000 ? 'tiempo' : '' }),
      puntaje: () => n,
      simular: (a) => ({ exito: n + a.v >= 10 }),
      invariantes: () => (n > 12 ? ['n se pasó de 12'] : []),
      resumen: () => ({ n }),
    });
    out.expuesto = typeof window.__bot; out.marca = document.documentElement.getAttribute('data-bot');
    out.info = __bot.info();
    out.url = GGX.bots.api === window.__bot;
    const buena = '(api, rng) => ({ tipo: "sumar", v: 3, info: { nota: 7 } })';
    const mala = '(api, rng) => ({ tipo: "romper", v: 9 })';
    const quieta = '(api, rng) => ({ tipo: "esperar" })';
    const rinde = '(api, rng, ctx) => ctx.paso >= 2 ? null : { tipo: "esperar" }';
    const explota = '(api, rng, ctx) => { throw new Error("política rota"); }';
    const quitaDeUnaVez = (a) => { delete a.ms_reales; return JSON.stringify(a); };
    const a1 = __bot.correr(buena, 7), a2 = __bot.correr(buena, 7), a3 = __bot.correr(buena, 8);
    out.buena = a1; out.determinista = quitaDeUnaVez(Object.assign({}, a1)) === quitaDeUnaVez(Object.assign({}, a2));
    out.otraSemilla = a3.semilla;
    out.ms_reales = typeof a1.ms_reales;
    out.mala = __bot.correr(mala, 7, { max_pasos: 5 });
    out.quieta = __bot.correr(quieta, 7);
    out.rinde = __bot.correr(rinde, 7);
    out.explota = __bot.correr(explota, 7);
    out.limite = __bot.correr(quieta, 7, { max_pasos: 3 });
    out.dt = __bot.correr(quieta, 7, { dt: 1000, max_pasos: 100 });
    const conPerfil = '(api, rng, ctx) => (ctx.perfil && ctx.perfil.temblor === 2 ? null : { tipo: "esperar" })';
    out.perfil = { con: __bot.correr(conPerfil, 7, { perfil: { temblor: 2 } }), sin: __bot.correr(conPerfil, 7, { max_pasos: 3 }) };
    __bot.reiniciar(7); out.antes = JSON.stringify(__bot.estado());
    out.simular = __bot.simular({ v: 12 }); out.simularNo = __bot.simular({ v: 1 });
    out.despues = JSON.stringify(__bot.estado());
    out.registro = GGX.bots.estado();
    let falla = null; try { GGX.bots.registrar({ estado() {} }); } catch (e) { falla = e.message; }
    out.rechazo = falla;
    return out;
  });
  chequear(M, r.expuesto === 'object' && r.marca === '1' && r.url, 'con ?bot=1 existe window.__bot y la página queda marcada con data-bot');
  chequear(M, r.info.juego === 'prueba' && r.info.contrato === 1 && r.info.semilla_url === 7 && r.info.capacidades.simular === true, 'info() dice qué juego es, la versión del contrato y qué capacidades tiene');
  chequear(M, r.buena.exito === true && r.buena.motivo === 'meta' && r.buena.pasos >= 3 && r.buena.pasos <= 4 && r.buena.puntaje >= 10, 'correr() juega un episodio entero dentro de la página y devuelve su resultado');
  chequear(M, r.buena.politica_info && r.buena.politica_info.nota === 7, 'la «info» que deja una política queda en el resultado (politica_info)');
  chequear(M, r.determinista === true && r.otraSemilla === 8, 'misma semilla y misma política dan exactamente el mismo resultado (ms_reales aparte)');
  chequear(M, r.ms_reales === 'number', 'ms_reales es lo único que depende del reloj de la computadora');
  chequear(M, r.mala.invalidas === 5 && r.mala.exito === false, 'las acciones inválidas se cuentan y no rompen el episodio');
  chequear(M, r.quieta.motivo === 'tiempo' && r.quieta.exito === false && r.quieta.ms_simulados === 5000, 'el tiempo es simulado: esperar lo hace correr hasta el límite del juego');
  chequear(M, r.rinde.motivo === 'abandono' && r.rinde.terminado === false, 'una política que devuelve null se rinde y queda anotado');
  chequear(M, r.explota.motivo === 'error-de-politica' && r.explota.errores.length === 1, 'una política que lanza un error no tumba la página: queda anotado');
  chequear(M, r.limite.motivo === 'limite' && r.limite.pasos === 3, 'max_pasos corta el episodio con el motivo «limite»');
  chequear(M, r.dt.ms_simulados === 5000 && r.dt.pasos === 5, 'dt manda cuánto avanza el juego entre decisiones');
  chequear(M, r.perfil.con.motivo === 'abandono' && r.perfil.sin.motivo === 'limite', 'el «perfil» de las opciones llega a la política en ctx.perfil (y es null si no se pasó)');
  chequear(M, r.simular.exito === true && r.simularNo.exito === false && r.antes === r.despues, 'simular() contesta sin tocar el estado real');
  chequear(M, r.registro.registrado === true && r.registro.expuesto === true && Array.isArray(r.registro.errores), 'GGX.bots.estado() informa del registro');
  chequear(M, typeof r.rechazo === 'string' && /faltan/.test(r.rechazo), 'un adaptador al que le faltan funciones obligatorias se rechaza con un motivo claro');
  chequear(M, errores.length === 0, 'sin errores de consola ni de página' + (errores.length ? ': ' + errores.join(' || ') : ''));
  await ctx.close();

  // las reglas rotas (invariantes) y los errores del juego se anotan sin tumbar a quien juega
  ({ ctx, page, errores } = await abrir(browser, {}, '?bot=1'));
  const v = await page.evaluate(() => {
    let n = 0;
    GGX.bots.registrar({ reiniciar() { n = 0; }, estado: () => ({ n }), actuar: () => { n += 5; return { valida: true }; }, avanzar() { if (n > 20) throw new Error('el juego se rompió'); },
      terminado: () => ({ fin: false }), invariantes: () => (n > 10 ? ['n pasó de 10'] : []) });
    const a = __bot.correr('(api) => ({ tipo: "x" })', 1, { max_pasos: 30, cada_invariantes: 1 });
    return { a, errores: __bot.metricas().errores };
  });
  chequear(M, v.a.violaciones.length === 1 && v.a.violaciones[0] === 'n pasó de 10', 'invariantes(): una regla rota queda en el informe, sin repetirse');
  chequear(M, v.a.motivo === 'error-del-juego' && v.errores.some((x) => /se rompió/.test(x)), 'un error dentro del juego termina el episodio con «error-del-juego» y queda anotado');
  await ctx.close();
}

(async () => {
  const browser = await chromium.launch();
  const pasos = { nucleo, accesible, efectos, musica, marca, anuncios, bots };
  for (const [nombre, f] of Object.entries(pasos)) {
    const hay = nombre === 'nucleo' || (await (async () => { const { ctx, page } = await abrir(browser); const v = await page.evaluate((n) => (n === 'accesible' ? !!GGX.a11y : n === 'efectos' ? !!GGX.fx : n === 'musica' ? !!GGX.music : n === 'marca' ? !!GGX.marca : n === 'bots' ? !!GGX.bots : !!GGX.ads), nombre); await ctx.close(); return v; })());
    if (!hay) { chequear(nombre, false, 'el módulo «' + nombre + '» no está en la página de prueba'); continue; }
    try { await f(browser); } catch (e) { chequear(nombre, false, 'la prueba se detuvo: ' + e.message); }
  }
  await browser.close();
  const fallas = Object.values(resultado).reduce((n, g) => n + g.fallas, 0);
  console.log(JSON.stringify({ nucleo: resultado.nucleo, modulos: { accesible: resultado.accesible, efectos: resultado.efectos, musica: resultado.musica, marca: resultado.marca, anuncios: resultado.anuncios, bots: resultado.bots }, fallas }));
  process.exit(fallas ? 1 : 0);
})().catch((e) => { console.error('FALLO GENERAL', e); process.exit(1); });
