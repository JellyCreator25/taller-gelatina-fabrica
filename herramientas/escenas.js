// Escenas de batalla para las publicaciones: juega una pelea preparada en el juego de verdad y guarda el momento exacto en que pasa algo
// (rayos, petrificación, caos) como imagen del campo, sin textos, para que sirva igual en español, inglés y chino.
// Uso: node herramientas/escenas.js <id-del-juego> [escena ...] [--en|--zh]   → contenido/imagenes/batalla-<escena>[-en|-zh].png (≈1200×675)
// Sin textos de interfaz, pero los guerreros hablan en el idioma de la partida («¡Rayos!» / «Lightning!»): --en y --zh dan la versión para esos públicos.
// Las batallas usan el azar del juego: cada corrida da un momento distinto. Se mira el resultado y se conserva el mejor; el archivo
// que queda en contenido/imagenes/ es el que se publica (las publicaciones citan la imagen, no esta corrida).
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const RAIZ = path.resolve(__dirname, '..');
const id = process.argv[2];
if (!id) { console.error('Uso: node herramientas/escenas.js <id-del-juego> [escena ...]'); process.exit(2); }
const destino = path.join(RAIZ, 'contenido', 'imagenes');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const fila = (tipo, x, y0, n, paso) => Array.from({ length: n }, (_, i) => [tipo, x, y0 + i * paso]);

// azul (equipo 0, mitad izquierda) y rojo (equipo 1, mitad derecha) en unidades del campo (960×540); `cuando` decide el momento de la foto
const ESCENAS = {
  caos: {
    azul: [['zeus', 250, 120], ['merlin', 230, 205], ['robin', 190, 290], ['hercules', 285, 270], ['anubis', 215, 360], ['dracula', 300, 190], ['medusa', 270, 345], ['llorona', 180, 440],
      ...fila('campesino', 340, 110, 7, 52), ...fila('arquero', 150, 150, 4, 70)],
    rojo: [['gigante', 640, 270], ['gigante', 700, 150], ['gigante', 700, 400], ...fila('campesino', 600, 100, 8, 48), ...fila('caballero', 670, 110, 6, 62), ...fila('bruja', 760, 150, 4, 80), ...fila('arquero', 800, 120, 5, 70)],
    cuando: (s) => s.units.filter((u) => u.dead).length >= 8 && s.fx.length >= 6,
  },
  duelo: {
    azul: [['hercules', 400, 270], ...fila('campesino', 330, 190, 4, 52), ['merlin', 300, 270]],
    rojo: [['medusa', 560, 270], ...fila('campesino', 630, 190, 4, 52), ['anubis', 660, 270]],
    cuando: (s) => s.units.filter((u) => u.stone > 0).length >= 2,
  },
  tormenta: {
    azul: [['zeus', 330, 270], ['robin', 250, 200], ['llorona', 250, 340], ...fila('campesino', 400, 160, 5, 55)],
    rojo: [...fila('campesino', 600, 110, 8, 46), ...fila('caballero', 690, 130, 5, 70), ...fila('bruja', 770, 170, 4, 65)],
    cuando: (s) => s.fx.filter((f) => f.kind === 'bolt').length >= 2,
  },
};

(async () => {
  fs.mkdirSync(destino, { recursive: true });
  const args = process.argv.slice(3);
  const idioma = args.includes('--en') ? 'en' : args.includes('--zh') ? 'zh' : 'es';
  const pedidas = args.filter((a) => !a.startsWith('--'));
  const quienes = pedidas.length ? pedidas : Object.keys(ESCENAS);
  const browser = await chromium.launch();
  for (const nombre of quienes) {
    const esc = ESCENAS[nombre];
    if (!esc) { console.error('FALLA · no existe la escena «' + nombre + '» (hay: ' + Object.keys(ESCENAS).join(', ') + ')'); process.exitCode = 1; continue; }
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1.54, locale: idioma === 'es' ? 'es-MX' : idioma === 'zh' ? 'zh-CN' : 'en-US' });
    const page = await ctx.newPage();
    const errores = [];
    page.on('pageerror', (e) => errores.push(e.message));
    await page.goto('file://' + path.join(RAIZ, 'salida', id, 'index.html') + '?lang=' + idioma);
    await page.waitForSelector('#cv');
    await page.click('#mLibre'); await page.click('#btnClear');
    await page.evaluate((e) => {
      const api = window.GuerrerosGelatina.api;
      for (const [t, x, y] of e.azul) api.spawn(t, 0, x, y);
      for (const [t, x, y] of e.rojo) api.spawn(t, 1, x, y);
    }, { azul: esc.azul, rojo: esc.rojo });
    await sleep(200);
    await page.click('#btnFight');
    const t0 = Date.now();
    let hecho = false;
    while (Date.now() - t0 < 25000) {
      const listo = await page.evaluate((src) => (new Function('s', 'return (' + src + ')(s)'))(window.GuerrerosGelatina.api.state), esc.cuando.toString());
      if (listo) {
        await sleep(90);
        const archivo = path.join(destino, 'batalla-' + nombre + (idioma === 'es' ? '' : '-' + idioma) + '.png');
        const png = await page.locator('#cv').screenshot();
        const b64 = await page.evaluate(async (data) => {   // se normaliza a 1200×675, la forma de tarjeta de las publicaciones
          const img = new Image(); img.src = 'data:image/png;base64,' + data; await img.decode();
          const c = document.createElement('canvas'); c.width = 1200; c.height = 675;
          const g = c.getContext('2d'); g.imageSmoothingQuality = 'high'; g.drawImage(img, 0, 0, 1200, 675);
          return c.toDataURL('image/png').split(',')[1];
        }, png.toString('base64'));
        fs.writeFileSync(archivo, Buffer.from(b64, 'base64'));
        console.log('ok     · ' + path.relative(RAIZ, archivo));
        hecho = true;
        break;
      }
      await sleep(40);
    }
    if (!hecho) { console.error('FALLA · la escena «' + nombre + '» no llegó al momento pedido en 25 s'); process.exitCode = 1; }
    if (errores.length) { console.error('FALLA · errores de página: ' + errores.join(' | ')); process.exitCode = 1; }
    await ctx.close();
  }
  await browser.close();
})().catch((e) => { console.error('FALLA · ' + e.message); process.exit(1); });
