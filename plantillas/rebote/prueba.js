// Escenario de prueba de la plantilla «rebote»: lo usa herramientas/probar.js. `ctx` trae: modo ('prueba' con comprobaciones | 'video' a ritmo normal),
// medios (carpeta de salida), log, assert y slug ('escritorio' | 'celular'). Deja medios/portada-fuente.png (solo en escritorio) y una captura.
// Juega con entradas reales: teclado (ángulo y potencia) y arrastre desde la gelatina, como una resortera. Para el arrastre se usa el ratón también en
// «celular» (la API táctil de Playwright solo sabe tocar, no arrastrar); el toque sí se usa para el botón.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

module.exports = {
  listo: '#cv',
  async jugar(page, ctx) {
    const { modo, medios, log, assert, slug } = ctx;
    const tactil = slug === 'celular';
    const E = () => page.evaluate(() => window.__rebote.estado());
    const tocar = (sel) => { const l = page.locator(sel); return tactil ? l.tap() : l.click(); };
    const esperar = async (fases, ms) => {
      const t0 = Date.now();
      for (;;) {
        const e = await E();
        if (fases.indexOf(e.fase) >= 0) return e;
        if (Date.now() - t0 > ms) throw new Error('esperaba ' + fases.join(' o ') + ' y la fase sigue en «' + e.fase + '»');
        await sleep(80);
      }
    };
    // el tiro ganador más robusto (el de más vecinos de la rejilla que también ganan): tolera el redondeo del arrastre en píxeles
    const ganador = () => page.evaluate(() => {
      const e = window.__rebote.estado(), A = [], P = [];
      for (let a = 5; a <= 88; a++) A.push(a);
      for (let p = 0.2; p <= 1.0001; p += 0.02) P.push(Math.round(p * 100) / 100);
      const ok = A.map((a) => P.map((p) => window.__rebote.simular(a, p, e.nivel).exito));
      let mejor = null, mejorV = -1;
      for (let i = 0; i < A.length; i++) for (let j = 0; j < P.length; j++) {
        if (!ok[i][j]) continue;
        let v = 0;
        for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++) if (ok[i + di] && ok[i + di][j + dj]) v++;
        if (v > mejorV) { mejorV = v; mejor = { angulo: A[i], potencia: P[j] }; }
      }
      return mejor;
    });
    const arrastrar = async (angulo, potencia) => {
      const e = await E(), c = await page.locator('#cv').boundingBox();
      const kx = c.width / 640, ky = c.height / 400, d = potencia * 140, a = angulo * Math.PI / 180;
      const bx = c.x + e.bola.x * kx, by = c.y + e.bola.y * ky;
      await page.mouse.move(bx, by);
      await page.mouse.down();
      await page.mouse.move(bx - Math.cos(a) * d * kx * 0.5, by + Math.sin(a) * d * ky * 0.5, { steps: 4 });
      await page.mouse.move(bx - Math.cos(a) * d * kx, by + Math.sin(a) * d * ky, { steps: 4 });
      await page.mouse.up();
    };

    let e = await E();
    assert(e.fase === 'inicio', 'la partida debería esperar en la pantalla de inicio (' + e.fase + ')');
    await sleep(modo === 'video' ? 1200 : 100);
    await tocar('#btnJugar');
    e = await esperar(['apuntando'], 5000);                    // entre el toque y el nivel 1 está el sello de la Gelatina (≈1,4 s)
    assert(e.fase === 'apuntando' && e.nivel === 0, 'el botón Jugar no cargó el nivel 1 (' + e.fase + ', nivel ' + e.nivel + ')');

    if (modo === 'video') {
      await page.locator('#cv').focus();
      await sleep(1200);
      for (let i = 0; i < 8; i++) { await page.keyboard.press('Shift+ArrowDown'); await sleep(60); }   // un tiro raso que falla
      await sleep(500);
      await page.keyboard.press('Space');
      await esperar(['nivel-ok', 'apuntando', 'sin-tiros'], 15000);
      await sleep(900);
      const t = await ganador();
      assert(t, 'no hay tiro ganador en el nivel');
      await arrastrar(t.angulo, t.potencia);
      await esperar(['nivel-ok', 'apuntando', 'sin-tiros'], 15000);
      await sleep(2200);
      return { nivel: (await E()).nivel };
    }

    assert(e.tiros === 5, 'el nivel debería empezar con 5 tiros y tiene ' + e.tiros);
    await page.locator('#cv').focus();
    const a0 = e.angulo, p0 = e.potencia;
    for (let i = 0; i < 3; i++) await page.keyboard.press('ArrowUp');
    for (let i = 0; i < 2; i++) await page.keyboard.press('ArrowRight');
    e = await E();
    assert(e.angulo === a0 + 3, 'tres flechas hacia arriba deberían subir el ángulo 3 grados (de ' + a0 + ' a ' + e.angulo + ')');
    assert(e.potencia > p0, 'la flecha derecha debería subir la potencia (de ' + p0 + ' a ' + e.potencia + ')');
    for (let i = 0; i < 12; i++) await page.keyboard.press('Shift+ArrowDown');
    e = await E();
    assert(e.angulo === 0, 'con Mayús+flecha abajo el ángulo debería llegar a 0 y llegó a ' + e.angulo);
    log('  teclado → ángulo ' + e.angulo + '°, potencia ' + e.potencia);

    // un tiro con el teclado: lo que pase en la partida real debe coincidir con lo que dice la simulación de la página
    const previsto = await page.evaluate(() => { const s = window.__rebote.estado(); return window.__rebote.simular(s.angulo, s.potencia, s.nivel); });
    await page.keyboard.press('Space');
    assert((await E()).fase === 'volando', 'la barra espaciadora no lanzó la gelatina');
    e = await esperar(['nivel-ok', 'apuntando', 'sin-tiros'], 15000);
    assert(e.usados === 1 && e.tiros === 4, 'un tiro debería gastar un tiro (usados ' + e.usados + ', quedan ' + e.tiros + ')');
    assert((e.fase === 'nivel-ok') === !!previsto.exito, 'la partida real (' + e.fase + ') no coincide con la simulación (' + previsto.resultado + ')');
    log('  tiro con teclado → ' + e.fase + ' (la simulación dijo «' + previsto.resultado + '»)');
    if (e.fase === 'nivel-ok') { await page.keyboard.press('Enter'); e = await E(); assert(e.fase === 'apuntando', 'Enter no abrió el nivel siguiente'); }

    const nivel = e.nivel, t = await ganador();
    assert(t, 'no hay tiro ganador en el nivel ' + (nivel + 1));
    await arrastrar(t.angulo, t.potencia);
    assert((await E()).fase === 'volando', 'el arrastre no lanzó la gelatina');
    e = await esperar(['nivel-ok', 'apuntando', 'sin-tiros'], 15000);
    assert(e.fase === 'nivel-ok', 'el tiro ganador (' + t.angulo + '°, ' + t.potencia + ') arrastrado con el ratón no ganó (' + e.fase + ')');
    log('  arrastre (' + t.angulo + '°, potencia ' + t.potencia + ') → nivel ' + (nivel + 1) + ' superado');
    assert(e.estrellas[nivel] >= 1, 'un nivel superado debería dar al menos una estrella (' + JSON.stringify(e.estrellas) + ')');
    if (slug === 'escritorio') await page.screenshot({ path: medios + '/portada-fuente.png', clip: await page.locator('#cv').boundingBox() });
    await page.screenshot({ path: medios + '/captura-juego-' + slug + '.png' });

    await page.keyboard.press('Enter');
    e = await E();
    assert(e.fase === 'apuntando' && e.nivel === nivel + 1 && e.tiros === 5, 'Enter después de superar el nivel debería abrir el siguiente con 5 tiros (' + e.fase + ', nivel ' + e.nivel + ')');
    return { nivel: e.nivel + 1, estrellas: e.total };
  },
};
