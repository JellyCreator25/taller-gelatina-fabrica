// Escenario de prueba de la plantilla «arena»: lo usa herramientas/probar.js. `ctx` trae: modo ('prueba' con comprobaciones | 'video' a ritmo normal),
// medios (carpeta de salida), log, assert y slug ('escritorio' | 'celular'). Deja medios/portada-fuente.png (solo en escritorio) y una captura.
// Juega con entradas reales: arrastre sobre el lienzo (ratón; la API táctil de Playwright solo sabe tocar), teclado (cursor, Espacio y teclas de material) y botones.
// Para no esperar minutos se adelanta el reloj del mundo con window.__arena.avanzar(ticks) solo entre una acción y otra; los descubrimientos se ganan con entradas reales.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

module.exports = {
  listo: '#cv',
  async jugar(page, ctx) {
    const { modo, medios, log, assert, slug } = ctx;
    const tactil = slug === 'celular';
    const E = () => page.evaluate(() => window.__arena.estado());
    const tocar = (sel) => { const l = page.locator(sel); return tactil ? l.tap() : l.click(); };
    const celdaAPantalla = async (cx, cy) => {
      const c = await page.locator('#cv').boundingBox();
      return [c.x + (cx + 0.5) / 160 * c.width, c.y + (cy + 0.5) / 100 * c.height];
    };
    // verter manteniendo apretado en una celda durante `ms` milisegundos reales
    const verter = async (cx, cy, ms) => {
      const [x, y] = await celdaAPantalla(cx, cy);
      await page.mouse.move(x, y);
      await page.mouse.down();
      await sleep(ms);
      await page.mouse.up();
    };
    const esperarDescubrir = async (nombre, ms) => {
      const t0 = Date.now();
      for (;;) {
        await page.evaluate(() => window.__arena.avanzar(30));
        const e = await E();
        if (e.descubiertos.indexOf(nombre) >= 0) return e;
        if (Date.now() - t0 > ms) throw new Error('no se descubrió «' + nombre + '» (montaña ' + e.montana + ', barro ' + e.conteos.barro + ')');
        await sleep(40);
      }
    };

    if (modo === 'video') {
      await sleep(1200);
      await verter(80, 10, 2400);                       // una montaña de arena
      await page.evaluate(() => window.__arena.avanzar(160));
      await sleep(500);
      await tocar('.mat[data-mat="agua"]');
      await verter(80, 10, 1800);                       // agua encima: barro
      await sleep(1800);
      return { descubiertos: (await E()).descubiertos.length };
    }

    let e = await E();
    assert(e.descubiertos.length === 0 && e.desbloqueados.join() === 'arena', 'al empezar solo debería haber arena y ningún descubrimiento (' + JSON.stringify(e.desbloqueados) + ')');
    assert(await page.locator('.mat[data-mat="agua"]').isDisabled().catch(() => true) || e.desbloqueados.indexOf('agua') < 0, 'el agua debería estar bloqueada al empezar');

    // teclado: un material bloqueado no se puede elegir; Espacio empieza y para de verter
    await page.locator('#cv').focus();
    await page.keyboard.press('Digit2');
    e = await E();
    assert(e.material === 'arena', 'la tecla 2 no debería elegir el agua mientras está bloqueada (material: ' + e.material + ')');
    for (let i = 0; i < 6; i++) await page.keyboard.press('ArrowUp');
    await page.keyboard.press('Space');
    await sleep(500);
    await page.keyboard.press('Space');
    await page.evaluate(() => window.__arena.avanzar(60));
    e = await E();
    assert(e.conteos.arena > 0, 'Espacio debería haber vertido arena (hay ' + e.conteos.arena + ' celdas)');
    const antes = e.conteos.arena;
    await sleep(400);
    e = await E();
    assert(e.conteos.arena === antes, 'al volver a pulsar Espacio debería dejar de verter (' + antes + ' → ' + e.conteos.arena + ')');
    log('  teclado → ' + antes + ' celdas de arena y dejó de verter al parar');

    // limpiar con el botón
    await tocar('#btnLimpiar');
    e = await E();
    assert(e.conteos.arena === 0, 'Limpiar todo debería vaciar el lienzo (quedan ' + e.conteos.arena + ' celdas)');

    // arrastre real: una montaña de arena desbloquea el agua
    await verter(80, 12, 2600);
    e = await esperarDescubrir('montana', 8000);
    assert(e.desbloqueados.indexOf('agua') >= 0, 'descubrir la montaña debería desbloquear el agua (' + JSON.stringify(e.desbloqueados) + ')');
    log('  arrastre → montaña de arena (altura ' + e.montana + '), agua desbloqueada');

    // elegir agua con el botón y mezclarla con la arena: barro, que desbloquea la piedra
    await tocar('.mat[data-mat="agua"]');
    e = await E();
    assert(e.material === 'agua', 'el botón Agua no eligió el agua (material: ' + e.material + ')');
    await verter(80, 12, 2400);
    e = await esperarDescubrir('barro', 12000);
    assert(e.desbloqueados.indexOf('piedra') >= 0, 'descubrir el barro debería desbloquear la piedra (' + JSON.stringify(e.desbloqueados) + ')');
    log('  agua sobre la arena → barro (' + e.conteos.barro + ' celdas), piedra desbloqueada');

    assert(await page.locator('#pista').innerText() !== '', 'debería mostrarse una pista para el siguiente descubrimiento');
    if (slug === 'escritorio') await page.screenshot({ path: medios + '/portada-fuente.png', clip: await page.locator('#cv').boundingBox() });
    await page.screenshot({ path: medios + '/captura-juego-' + slug + '.png' });
    return { descubiertos: e.descubiertos.length, desbloqueados: e.desbloqueados.length };
  },
};
