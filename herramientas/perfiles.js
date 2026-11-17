// Convierte una página HTML en imagen (avatar o banner de las cuentas de difusión) con un Chromium real.
// Uso: node herramientas/perfiles.js <archivo.html> <salida> <ancho> <alto> [png|jpeg]
const { chromium } = require('playwright');
const path = require('path');

const [, , html, salida, ancho, alto, tipo] = process.argv;
if (!html || !salida || !ancho || !alto) { console.error('Uso: node herramientas/perfiles.js <archivo.html> <salida> <ancho> <alto> [png|jpeg]'); process.exit(2); }

(async () => {
  const b = await chromium.launch();
  try {
    const p = await b.newPage({ viewport: { width: Number(ancho), height: Number(alto) }, deviceScaleFactor: 1 });
    await p.goto('file://' + path.resolve(html), { waitUntil: 'load' });
    await p.evaluate(() => document.fonts.ready);
    const opciones = { path: salida, type: tipo === 'jpeg' ? 'jpeg' : 'png' };
    if (opciones.type === 'jpeg') opciones.quality = 92;
    await p.screenshot(opciones);
  } finally {
    await b.close();
  }
})().catch((e) => { console.error(e.message || e); process.exit(1); });
