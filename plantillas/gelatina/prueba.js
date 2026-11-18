// Escenario de prueba de Guerreros Gelatina: coloca Leyendas con el ratón o el dedo, pelea y comprueba que el sonido se dispara.
// Lo usa herramientas/probar.js. `ctx` trae: modo ('prueba' rápido | 'video' a ritmo normal), medios (carpeta), log, assert.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const ESCRITORIO = [['zeus', 90, 100], ['merlin', 80, 190], ['robin', 80, 280], ['llorona', 90, 370], ['anubis', 190, 140], ['dracula', 190, 250], ['medusa', 190, 360], ['hercules', 200, 450],
  ['campesino', 300, 90], ['campesino', 300, 140], ['campesino', 300, 190], ['campesino', 300, 240], ['campesino', 300, 290], ['campesino', 300, 340], ['campesino', 300, 390], ['campesino', 300, 440]];
const MOVIL = [['zeus', 110, 450], ['hercules', 250, 450], ['medusa', 390, 450], ['merlin', 110, 560], ['dracula', 250, 570], ['robin', 390, 570],
  ['campesino', 70, 630], ['campesino', 130, 630], ['campesino', 190, 630], ['campesino', 250, 630], ['campesino', 310, 630], ['campesino', 370, 630], ['campesino', 430, 630]];

module.exports = {
  listo: '#cv',
  async jugar(page, ctx) {
    const { modo, medios, log, assert, slug } = ctx;
    const video = modo === 'video';
    const vp = page.viewportSize();
    const vertical = vp.width < 600;
    const W = vertical ? 520 : 960, H = vertical ? 680 : 540;
    const plan = vertical ? MOVIL : ESCRITORIO;

    if (video) await sleep(1400);
    await page.click('#mLibre'); await page.selectOption('#oro', '5000'); await page.click('#tBlue'); await page.click('#btnClear');
    const cv = page.locator('#cv');
    await page.evaluate(() => { window.__hits = 0; });
    for (const [t, x, y] of plan) {
      await page.click('button[data-t="' + t + '"]');
      await cv.scrollIntoViewIfNeeded();
      const box = await cv.boundingBox();
      if (video) await page.mouse.move(box.x + (x / W) * box.width, box.y + (y / H) * box.height, { steps: 6 });
      await page.mouse.click(box.x + (x / W) * box.width, box.y + (y / H) * box.height);
      if (video) await sleep(180);
    }
    await sleep(300);
    const azul = Number(await page.textContent('#n0'));
    assert(azul === plan.length, 'se colocaron ' + azul + ' guerreros azules, se esperaban ' + plan.length);
    if (!video) await page.screenshot({ path: medios + '/captura-colocar-' + slug + '.png', fullPage: !vertical });

    // Un clic en un sitio imposible (fuera de la zona azul) debe sonar a error y no colocar nada
    const box0 = await cv.boundingBox();
    await page.click('button[data-t="campesino"]');
    await page.mouse.click(box0.x + box0.width * 0.9, box0.y + box0.height * 0.5);
    await sleep(120);
    assert(Number(await page.textContent('#n0')) === azul, 'se colocó un guerrero fuera de la zona');

    // Acabado con el motor: el botón de accesibilidad y el distintivo ya están, el sello abre la primera batalla de la visita
    // y la pelea arranca sola cuando termina; la música arranca con el primer gesto.
    const antes = await page.evaluate(() => ({ boton: !!document.querySelector('.head-r .ggx-a11y-btn'), firma: !!document.querySelector('#firma *'), sellos: window.GGX.marca.estado().sellos }));
    assert(antes.boton, 'falta el botón de accesibilidad en el encabezado');
    assert(antes.firma, 'falta el distintivo de la marca en el pie');
    assert(antes.sellos === 0, 'el sello ya había salido antes de pulsar ¡Pelear!');
    await page.click('#btnFight');
    await page.waitForFunction(() => window.GuerrerosGelatina.api.state.phase === 'fight', null, { timeout: 6000 });
    const abierta = await page.evaluate(() => ({ sellos: window.GGX.marca.estado().sellos, musica: window.GGX.music.estado() }));
    assert(abierta.sellos === 1, 'la primera batalla debía abrir con el sello (salió ' + abierta.sellos + ' veces)');
    assert(abierta.musica.sonando && abierta.musica.animo === 'aventura', 'la música no arrancó con la primera batalla: ' + JSON.stringify(abierta.musica));
    log('  sello al primer ¡Pelear! y música «' + abierta.musica.animo + '» a ' + abierta.musica.bpm + ' bpm');
    if (!video) { await page.click('#btnSpeed'); }               // ×2
    await sleep(video ? 5500 : 4500);
    await cv.scrollIntoViewIfNeeded();
    if (slug === 'escritorio') {   // la portada se compone con este momento de la batalla, recortado sobre la acción
      const caja = await cv.boundingBox();
      const pts = await page.evaluate(() => window.GuerrerosGelatina.api.state.units.filter((u) => !u.dead).map((u) => [u.x, u.y]));
      const cx = pts.reduce((a, p) => a + p[0], 0) / pts.length, cy = pts.reduce((a, p) => a + p[1], 0) / pts.length;
      const cw = 560, ch = 350;
      const x0 = Math.min(Math.max(cx - cw / 2, 0), W - cw), y0 = Math.min(Math.max(cy - ch / 2, 0), H - ch);
      await page.screenshot({ path: medios + '/portada-fuente.png', clip: { x: caja.x + (x0 / W) * caja.width, y: caja.y + (y0 / H) * caja.height, width: (cw / W) * caja.width, height: (ch / H) * caja.height } });
    }
    if (!video) {
      await page.click('#btnSpeed');                               // ×4 para terminar rápido
      const t0 = Date.now();
      while (Date.now() - t0 < 60000) {
        const fase = await page.evaluate(() => window.GuerrerosGelatina.api.state.phase);
        if (fase === 'over') break;
        await sleep(250);
      }
      const fase = await page.evaluate(() => window.GuerrerosGelatina.api.state.phase);
      assert(fase === 'over', 'la batalla no terminó en 60 s');
      log('  batalla terminada en ' + ((Date.now() - t0) / 1000 + 4.5).toFixed(1) + ' s reales · ' + (await page.textContent('#bTitle')));
      await cv.scrollIntoViewIfNeeded();
      await page.screenshot({ path: medios + '/captura-final-' + slug + '.png', fullPage: !vertical });
    } else {
      await sleep(9000);                                            // el clip sigue la batalla a ritmo normal
    }

    const plays = await page.evaluate(() => window.GGX.sfx.plays);
    log('  sonidos disparados: ' + JSON.stringify(plays));
    if (!video) {
      for (const n of ['pop', 'error', 'horn', 'hit', 'hurt', 'click']) assert((plays[n] || 0) > 0, 'el sonido «' + n + '» nunca se disparó');
      assert((plays.win || 0) + (plays.lose || 0) + (plays.error || 0) > 0, 'no sonó el final de la batalla');
    }
    // Modo Reto: al subir de nivel el jugador debe recibir más oro (antes se quedaba fijo mientras el del rival crecía).
    // Se fuerza la victoria dejando caer al rival; el resto del flujo (banner, botón «siguiente», colocar) es el real.
    let reto = null;
    if (!video) {
      const oro = (e) => page.evaluate((b) => window.GuerrerosGelatina.oro(b), e);
      const nivel = () => page.evaluate(() => window.GuerrerosGelatina.api.state.level);
      const gastado = () => page.evaluate(() => { const g = window.GuerrerosGelatina; return g.api.state.units.filter((u) => !u.dead && u.team === 0).reduce((s, u) => s + g.units[u.type].cost, 0); });
      await page.click('#mReto');
      assert((await nivel()) === 1, 'el modo Reto no empieza en el nivel 1');
      const paso = await page.evaluate(() => window.GuerrerosGelatina.reto.oro_por_nivel);
      assert(paso > 0, 'el oro por nivel del jugador debe ser mayor que 0 (es ' + paso + ')');
      const oro1 = await oro(0);
      const tocar = async (fx, fy) => { await cv.scrollIntoViewIfNeeded(); const b = await cv.boundingBox(); await page.mouse.click(b.x + b.width * fx, b.y + b.height * fy); await sleep(120); };
      await page.click('button[data-t="caballero"]');
      await tocar(vertical ? 0.5 : 0.2, vertical ? 0.8 : 0.5);
      assert(Number(await page.textContent('#n0')) === 1, 'no se pudo colocar el guerrero del nivel 1');
      await page.click('#btnFight');
      await page.evaluate(() => { window.GuerrerosGelatina.api.state.units.forEach((u) => { if (u.team === 1) u.dead = true; }); });
      await page.waitForSelector('#bBtns [data-act="next"]', { timeout: 20000 });
      const festejo = await page.evaluate(() => ({ fx: window.GGX.fx.count(), titulo: document.getElementById('bTitle').textContent }));
      assert(festejo.fx > 0, 'ganar un nivel no lanzó confeti ni efectos');
      await sleep(250);
      const anuncio = await page.evaluate(() => (document.getElementById('ggx-live') || {}).textContent || '');
      assert(anuncio.includes(festejo.titulo), 'el lector de pantalla no anunció el resultado: «' + anuncio + '» no incluye «' + festejo.titulo + '»');
      log('  al ganar: ' + festejo.fx + ' efectos vivos y anuncio «' + anuncio + '»');
      await page.click('#bBtns [data-act="next"]');
      assert((await nivel()) === 2, 'tras ganar no se pasó al nivel 2');
      const oro2 = await oro(0);
      assert(oro2 === oro1 + paso, 'el oro del nivel 2 es ' + oro2 + ' y debía ser ' + (oro1 + paso));
      const libre = oro2 - (await gastado());
      assert(libre >= paso, 'en el nivel 2 solo queda ' + libre + ' de oro libre y debía haber al menos ' + paso);
      await page.click('button[data-t="campesino"]');
      await tocar(vertical ? 0.3 : 0.1, vertical ? 0.9 : 0.8);
      assert(Number(await page.textContent('#n0')) === 2, 'con el oro extra del nivel 2 no se pudo añadir un guerrero');
      reto = { nivel1: oro1, nivel2: oro2, libre_nivel2: libre };
      log('  oro del jugador en Reto: nivel 1 → ' + oro1 + ', nivel 2 → ' + oro2 + ' (oro libre ' + libre + ')');
    }

    // Accesibilidad: con «alto contraste» cada guerrero lleva marca de bando por forma (pixel blanco al pie); con «menos movimiento» no hay
    // sacudida ni partículas, y al quitarlo vuelven.
    let accesibilidad = null;
    if (!video) {
      const pixel = () => page.evaluate(() => { const S = window.GuerrerosGelatina.api.state; const u = S.units.find((v) => !v.dead && v.team === 0); const d = document.getElementById('cv').getContext('2d').getImageData(Math.round(u.x * S.scale), Math.round((u.y + u.r * 0.6) * S.scale), 1, 1).data; return [d[0], d[1], d[2]]; });
      await page.evaluate(() => window.GGX.a11y.set('altoContraste', true)); await sleep(250);
      const conMarca = await pixel();
      await page.evaluate(() => window.GGX.a11y.set('altoContraste', false)); await sleep(250);
      const sinMarca = await pixel();
      await page.evaluate(() => window.GGX.a11y.set('altoContraste', null));
      assert(conMarca.every((v) => v >= 250), 'con alto contraste no se dibujó la marca de bando (pixel ' + conMarca + ')');
      assert(!sinMarca.every((v) => v >= 250), 'sin alto contraste aparece la marca de bando (pixel ' + sinMarca + ')');
      const mover = (quieto) => page.evaluate((q) => { const g = window.GuerrerosGelatina, S = g.api.state, A = window.GGX.a11y; A.set('reducirMovimiento', q); S.shake = 0; g.api.shake(12); const sac = S.shake; const creadas = window.GGX.fx.burst(100, 100, { n: 10 }); S.shake = 0; A.set('reducirMovimiento', null); return { sac, creadas }; }, quieto);
      const quieto = await mover(true), normal = await mover(null);
      assert(quieto.sac === 0 && quieto.creadas === 0, 'con menos movimiento hubo sacudida (' + quieto.sac + ') o partículas (' + quieto.creadas + ')');
      assert(normal.sac > 0 && normal.creadas > 0, 'sin pedir menos movimiento no hay sacudida (' + normal.sac + ') ni partículas (' + normal.creadas + ')');
      accesibilidad = { marca_alto_contraste: true, quieto, normal };
      log('  accesibilidad: marca de bando en alto contraste; con menos movimiento sacudida ' + quieto.sac + ' y partículas ' + quieto.creadas + ' (normal: ' + normal.sac + ' y ' + normal.creadas + ')');
    }

    // Idiomas: el selector cambia todo el juego al instante (también con el aviso de fin de batalla abierto), cada texto sale del
    // diccionario de juego.json, los guerreros y las frases de los poderes siguen al idioma, y la elección se recuerda al recargar.
    let idiomas = null;
    if (!video) {
      const tx = await page.evaluate(() => window.JUEGO.textos);
      const langs = await page.evaluate(() => window.GGX.langs);
      assert(langs.length >= 3, 'el juego debería ofrecer al menos tres idiomas (' + langs + ')');
      const sel = page.locator('.head-r select.ggx-lang');
      log('  idiomas ofrecidos: ' + (await sel.locator('option').allTextContents()).join(' · '));
      const rell = (t, v) => String(t).replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m));
      const num = (n) => Number(n).toLocaleString('en-US');          // es-MX, en-US y zh-CN separan los miles con coma
      const texto = (s) => page.evaluate((q) => (document.querySelector(q) || {}).textContent, s);
      const revisarComun = async (l) => {
        await sel.selectOption(l); await sleep(160);
        const est = await page.evaluate(() => ({
          lang: window.GGX.lang, etiqueta: document.documentElement.lang, h1: document.querySelector('h1').textContent, doc: document.title,
          fuente: getComputedStyle(document.querySelector('h1')).fontFamily,
          tray: [...document.querySelectorAll('.tray .unit[data-t]')].filter((b) => b.dataset.t !== 'borrar').map((b) => [b.dataset.t, b.querySelector('.nm').textContent, b.title]),
          sueltos: (() => {
            const hojas = [...document.querySelectorAll('body *')].filter((e) => e.children.length === 0 && e.textContent.trim() && !['SCRIPT', 'STYLE', 'OPTION'].includes(e.tagName));
            const t = hojas.map((e) => e.textContent.trim()).concat([...document.querySelectorAll('[title]')].map((e) => e.title));
            return t.filter((x) => /^[a-z]+(_[a-z0-9]+)+$/.test(x) || /\{\w+\}/.test(x));
          })(),
        }));
        assert(est.lang === l, 'al elegir ' + l + ' el motor quedó en ' + est.lang);
        assert(est.etiqueta === (l === 'zh' ? 'zh-Hans' : l), 'html lang es «' + est.etiqueta + '» en ' + l);
        assert(est.h1 === tx[l].titulo && est.doc === tx[l].titulo, 'el título no siguió al idioma ' + l + ': «' + est.h1 + '» / «' + est.doc + '»');
        assert((await texto('#mReto')) === tx[l].modo_reto && (await texto('#mLibre')) === tx[l].modo_libre, 'los botones de modo no siguieron al idioma ' + l);
        assert((await texto('#btnFight')) === tx[l].pelear, 'el botón de pelear no siguió al idioma ' + l);
        assert((await texto('.tray .unit[data-t="borrar"] .nm')) === tx[l].borrar, 'el botón de borrar no siguió al idioma ' + l);
        for (const [id, nombre, ayuda] of est.tray) {
          assert(nombre === tx[l]['u_' + id], 'el guerrero «' + id + '» se llama «' + nombre + '» en ' + l + ' y debería llamarse «' + tx[l]['u_' + id] + '»');
          assert(ayuda === (tx[l]['u_' + id + '_tip'] || ''), 'la ayuda de «' + id + '» no sigue al idioma ' + l);
        }
        assert(est.sueltos.length === 0, 'quedaron claves sin traducir o marcas {x} sin llenar en ' + l + ': ' + est.sueltos.join(' | '));
        if (l === 'zh') assert(/PingFang|YaHei|Noto Sans CJK|Hiragino|Noto Sans SC|WenQuanYi/.test(est.fuente), 'la pila tipográfica del título no incluye fuentes chinas: ' + est.fuente);
        return est;
      };

      // 1) Aviso de victoria abierto: título, texto con números y botones cambian con el idioma
      await sel.selectOption(langs[0]);
      await page.click('#btnFight');
      await page.evaluate(() => { window.GuerrerosGelatina.api.state.units.forEach((u) => { if (u.team === 1) u.dead = true; }); });
      await page.waitForSelector('#bBtns [data-act="next"]', { timeout: 20000 });
      const fin = await page.evaluate(() => { const g = window.GuerrerosGelatina, S = g.api.state; return { level: S.level, left: S.result.left, best: S.best, mas: g.reto.oro_por_nivel, oroSig: g.reto.oro_inicial + g.reto.oro_por_nivel * S.level }; });
      for (const l of langs) {
        await revisarComun(l);
        const b = await page.evaluate(() => ({ t: document.getElementById('bTitle').textContent, s: document.getElementById('bSub').textContent, btns: [...document.querySelectorAll('#bBtns button')].map((x) => x.textContent), visible: !document.getElementById('banner').hidden }));
        assert(b.visible, 'el aviso de fin de batalla no estaba visible');
        assert(b.t === rell(tx[l].b_nivel_t, { n: num(fin.level) }), 'título del aviso en ' + l + ': «' + b.t + '»');
        const esp = rell(tx[l][fin.left === 1 ? 'b_nivel_s_one' : 'b_nivel_s_other'], { left: num(fin.left), mejor: num(fin.best), sig: num(fin.level + 1), mas: num(fin.mas), oro: num(fin.oroSig) });
        assert(b.s === esp, 'texto del aviso en ' + l + ': «' + b.s + '» y debía ser «' + esp + '»');
        assert(b.btns.join('|') === [tx[l].b_siguiente, tx[l].b_revancha].join('|'), 'botones del aviso en ' + l + ': ' + b.btns.join(' / '));
        await page.screenshot({ path: medios + '/captura-idioma-' + l + '-' + slug + '.png', fullPage: true });
      }
      log('  aviso de victoria revisado en ' + langs.join(', ') + ': «' + (await texto('#bSub')) + '»');

      // 2) Modo Reto en preparación: pista, marcadores, nivel y botones
      await page.click('#bBtns [data-act="rematch"]');
      const est2 = await page.evaluate(() => { const g = window.GuerrerosGelatina, S = g.api.state; const gastado = S.units.filter((u) => !u.dead && u.team === 0).reduce((a, u) => a + g.units[u.type].cost, 0);
        return { level: S.level, best: S.best, oro: g.oro(0), libre: g.oro(0) - gastado, mas: g.reto.oro_por_nivel, vel: [0.4, 1, 2, 4][S.speedIdx], n1: S.units.filter((u) => !u.dead && u.team === 1).length }; });
      for (const l of langs) {
        await revisarComun(l);
        assert((await texto('#hint')) === rell(tx[l].pista_reto_nivel, { n: num(est2.level), oro: num(est2.oro), mas: num(est2.mas) }), 'pista del modo Reto en ' + l + ': «' + (await texto('#hint')) + '»');
        assert((await texto('#c0')) === rell(tx[l].oro_libre, { n: num(est2.libre) }), 'marcador azul en ' + l + ': «' + (await texto('#c0')) + '»');
        assert((await texto('#c1')) === rell(tx[l].rival_nivel, { n: num(est2.level) }), 'marcador rojo en ' + l + ': «' + (await texto('#c1')) + '»');
        assert((await texto('#lvl')) === rell(tx[l].nivel_mejor, { n: num(est2.level), mejor: num(est2.best) }), 'nivel en ' + l + ': «' + (await texto('#lvl')) + '»');
        assert((await texto('#btnRandom')) === tx[l].otro_rival, 'botón «otro rival» en ' + l);
        assert((await texto('#btnSpeed')) === rell(tx[l].velocidad, { v: String(est2.vel) }), 'botón de velocidad en ' + l + ': «' + (await texto('#btnSpeed')) + '»');
        assert((await texto('#btnPause')) === tx[l].pausa, 'botón de pausa en ' + l);
      }
      log('  modo Reto revisado en ' + langs.join(', '));

      // 3) Modo Libre: opciones de oro con el formato del idioma, botones de bando y pista
      await page.click('#mLibre');
      for (const l of langs) {
        await revisarComun(l);
        assert((await texto('#hint')) === tx[l].pista_libre, 'pista del modo Libre en ' + l);
        assert((await texto('#tBlue')) === tx[l].colocar_azul && (await texto('#tRed')) === tx[l].colocar_rojo, 'botones de bando en ' + l);
        assert((await texto('label.sel span')) === tx[l].oro_por_bando, 'etiqueta del oro en ' + l);
        const opciones = await page.locator('#oro option').allTextContents();
        assert(opciones.join('|') === ['1000', '2500', '5000'].map(num).join('|'), 'opciones de oro en ' + l + ': ' + opciones.join(' / '));
        assert((await texto('#btnRandom')) === tx[l].rival_azar, 'botón de rival al azar en ' + l);
      }
      log('  modo Libre revisado en ' + langs.join(', '));

      // 4) Frases de los poderes: se lanza cada poder y la burbuja sale en el idioma activo
      for (const l of langs) {
        await sel.selectOption(l); await sleep(120);
        const dichos = await page.evaluate(() => {
          const g = window.GuerrerosGelatina, api = g.api, S = api.state, out = {};
          for (const id of ['zeus', 'medusa', 'anubis', 'hercules', 'merlin', 'robin', 'llorona', 'dracula']) {
            S.fx = [];
            const u = api.spawn(id, 0, 300, 300);
            const foes = [api.spawn('campesino', 1, 330, 300), api.spawn('campesino', 1, 340, 320), api.spawn('campesino', 1, 320, 280)];
            const ally = api.spawn('campesino', 0, 280, 300); ally.dead = true;
            try { g.abilities[id].cast(u, api); out[id] = S.fx.filter((f) => f.kind === 'text').map((f) => f.text); } catch (e) { out[id] = ['ERROR ' + e.message]; }
            S.units = S.units.filter((x) => x !== u && x !== ally && !foes.includes(x));
          }
          S.fx = [];
          return out;
        });
        for (const id of Object.keys(dichos)) assert(dichos[id].includes(tx[l]['u_' + id + '_dice']), 'la frase de ' + id + ' en ' + l + ' debía ser «' + tx[l]['u_' + id + '_dice'] + '» y fue ' + JSON.stringify(dichos[id]));
      }
      log('  frases de las 8 Leyendas revisadas en ' + langs.join(', '));

      // 5) La elección se recuerda al recargar y la dirección (?lang=) manda sobre lo guardado
      const ultimo = langs[langs.length - 1];
      await sel.selectOption(ultimo);
      await page.reload();
      await page.waitForSelector('#cv'); await sleep(500);
      assert((await page.evaluate(() => window.GGX.lang)) === ultimo, 'el idioma elegido no se recordó al recargar');
      assert((await texto('h1')) === tx[ultimo].titulo, 'tras recargar el título no sigue al idioma ' + ultimo);
      await page.goto(page.url().split('?')[0] + '?lang=en');
      await page.waitForSelector('#cv'); await sleep(400);
      assert((await page.evaluate(() => window.GGX.lang)) === 'en' && (await texto('h1')) === tx.en.titulo, '?lang=en no cambió el idioma');
      log('  tras recargar el idioma se mantiene (' + ultimo + ') y ?lang=en lo cambia');
      idiomas = langs;
    }
    // Anuncios (módulo apagado por defecto): con un portal simulado, el botón del cartel de resultado pide UN anuncio entre batallas, el juego espera a que termine
    // y sigue; la batalla en sí nunca se interrumpe. Sin proveedor (todo lo anterior) los botones ya actuaron como siempre. Va al final: parte de un Reto nuevo.
    let anuncios = null;
    if (!video) {
      await page.click('#mReto');
      await page.click('button[data-t="caballero"]');
      await cv.scrollIntoViewIfNeeded();
      const caja = await cv.boundingBox();
      await page.mouse.click(caja.x + caja.width * (vertical ? 0.5 : 0.2), caja.y + caja.height * (vertical ? 0.8 : 0.5));
      await sleep(150);
      await page.evaluate(() => {
        window.__reg = [];
        window.CrazyGames = { SDK: { init: async () => {}, game: { gameplayStart() { window.__reg.push('start'); }, gameplayStop() { window.__reg.push('stop'); } },
          ad: { requestAd: (tipo, c) => { window.__reg.push(tipo); c.adStarted(); window.__reg.push('pausa:' + document.documentElement.hasAttribute('data-anuncio') + ',nivel:' + window.GuerrerosGelatina.api.state.level);
            setTimeout(() => c.adFinished(), 250); } } } };
        window.GGX.ads.configurar({ proveedor: 'crazygames' });
      });
      await sleep(150);
      await page.click('#btnFight');
      await page.evaluate(() => { window.GuerrerosGelatina.api.state.units.forEach((u) => { if (u.team === 1) u.dead = true; }); });
      await page.waitForSelector('#bBtns [data-act="next"]', { timeout: 20000 });
      await page.click('#bBtns [data-act="next"]');
      await page.waitForFunction(() => window.GuerrerosGelatina.api.state.level === 2, null, { timeout: 5000 });
      const reg = await page.evaluate(() => window.__reg.slice());
      assert(reg.filter((x) => x === 'midgame').length === 1, 'se esperaba un solo anuncio entre batallas y el registro dice ' + JSON.stringify(reg));
      assert(reg.includes('pausa:true,nivel:1'), 'durante el anuncio el juego debía estar en pausa y todavía en el nivel 1: ' + JSON.stringify(reg));
      assert(reg.indexOf('start') >= 0 && reg.indexOf('stop') > reg.indexOf('start'), 'gameplayStart/gameplayStop no se llamaron en orden: ' + JSON.stringify(reg));
      assert(reg.indexOf('stop') < reg.indexOf('midgame'), 'el anuncio no debía pedirse antes de que terminara la batalla: ' + JSON.stringify(reg));
      await page.evaluate(() => { window.GGX.ads.configurar({ proveedor: 'ninguno' }); delete window.CrazyGames; });
      anuncios = { pedidos: reg.length };
      log('  anuncio entre batallas con portal simulado: ' + JSON.stringify(reg));
    }

    return { colocados: azul, reto, accesibilidad, idiomas, anuncios };
  },
};
