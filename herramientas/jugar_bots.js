// Pruebas con bots de un juego, en un Chromium real: el juego se abre con ?bot=1 y cada política juega episodios enteros DENTRO de la página, con tiempo simulado.
// Uso: node herramientas/jugar_bots.js <index.html> <plantillas/NOMBRE/bots.js> <config.json>
//   config.json: {"semilla_base": 1000, "factor": 1, "politicas": ["aleatorio", …] | null}
// Imprime una sola línea JSON: {config, info, episodios: […], deterministas: […], errores_de_pagina: […]}. La lee herramientas/bots.py.
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const [html, botsJs, cfgJson] = process.argv.slice(2);
if (!html || !botsJs || !cfgJson) { console.error('Uso: node herramientas/jugar_bots.js <index.html> <bots.js> <config.json>'); process.exit(2); }
const def = require(path.resolve(botsJs));
const cfg = JSON.parse(fs.readFileSync(cfgJson, 'utf8'));
const url = 'file://' + path.resolve(html) + '?bot=1';
const limpiar = (x) => { const y = Object.assign({}, x); delete y.ms_reales; return JSON.stringify(y); };

(async () => {
  const browser = await chromium.launch();
  const escenas = def.escenas && def.escenas.length ? def.escenas : [{ nombre: 'unica', opciones: {} }];
  const salida = { config: { descripcion: def.descripcion || '', base: def.base || null, solucionador: def.solucionador || null, humano: def.humano || null,
    escenas: escenas.map((e) => e.nombre), partidas: def.partidas || {}, semilla_base: cfg.semilla_base, factor: cfg.factor || 1 },
    info: null, episodios: [], deterministas: [], errores_de_pagina: [] };
  for (const nombre of Object.keys(def.politicas)) {
    if (cfg.politicas && !cfg.politicas.includes(nombre)) continue;
    const n = Math.max(1, Math.round(((def.partidas && def.partidas[nombre]) || 10) * (cfg.factor || 1)));
    const ctx = await browser.newContext({ viewport: { width: 800, height: 600 }, locale: 'es-MX' });
    const page = await ctx.newPage();
    page.on('pageerror', (e) => salida.errores_de_pagina.push('pageerror: ' + e.message));
    page.on('console', (m) => { if (m.type() === 'error') salida.errores_de_pagina.push('consola: ' + m.text()); });
    await page.goto(url);
    await page.waitForFunction(() => !!window.__bot, null, { timeout: 15000 });
    if (def.preludio) await page.evaluate('(() => {' + def.preludio + '})()');
    if (!salida.info) salida.info = await page.evaluate(() => window.__bot.info());
    const fuente = def.politicas[nombre].toString();
    for (const escena of escenas) {
      const opciones = Object.assign({}, def.episodio || {}, escena.opciones || {});
      let primero = null;
      for (let i = 0; i < n; i++) {
        const semilla = cfg.semilla_base + i;
        const r = await page.evaluate(([f, s, o]) => window.__bot.correr(f, s, o), [fuente, semilla, opciones]);
        if (i === 0) primero = r;
        salida.episodios.push(Object.assign({ politica: nombre, escena: escena.nombre }, r));
      }
      const otra = await page.evaluate(([f, s, o]) => window.__bot.correr(f, s, o), [fuente, cfg.semilla_base, opciones]);   // misma semilla, mismo resultado
      salida.deterministas.push({ politica: nombre, escena: escena.nombre, ok: limpiar(primero) === limpiar(otra) });
    }
    await ctx.close();
  }
  await browser.close();
  console.log(JSON.stringify(salida));
})().catch((e) => { console.error('FALLO GENERAL', e); process.exit(1); });
