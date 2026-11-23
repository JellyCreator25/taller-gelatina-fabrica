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
  antesdespues: {   // dos fotos del mismo campo apiladas: antes de pulsar «¡Pelear!» y cuando ya es un caos (formato «antes y después»)
    compuesta: true,
    azul: [['zeus', 250, 190], ['merlin', 225, 255], ['robin', 200, 320], ['hercules', 320, 225], ['medusa', 310, 300], ['dracula', 350, 360],
      ...fila('campesino', 410, 160, 6, 40)],
    rojo: [['gigante', 700, 270], ['gigante', 770, 200], ['gigante', 770, 345], ...fila('campesino', 620, 160, 6, 40), ['caballero', 690, 185], ['caballero', 690, 235], ['caballero', 690, 305], ['caballero', 690, 355],
      ['bruja', 840, 220], ['bruja', 840, 280], ['bruja', 840, 340]],
    cuando: (s) => s.units.filter((u) => u.dead).length >= 8 && s.fx.length >= 6,
  },
  tormenta: {
    azul: [['zeus', 330, 270], ['robin', 250, 200], ['llorona', 250, 340], ...fila('campesino', 400, 160, 5, 55)],
    rojo: [...fila('campesino', 600, 110, 8, 46), ...fila('caballero', 690, 130, 5, 70), ...fila('bruja', 770, 170, 4, 65)],
    cuando: (s) => s.fx.filter((f) => f.kind === 'bolt').length >= 2,
  },
  ranas: {   // Merlín convierte en ranas a los enemigos más fuertes
    azul: [['merlin', 300, 270], ['merlin', 280, 200], ...fila('campesino', 350, 150, 5, 60)],
    rojo: [['gigante', 640, 200], ['gigante', 660, 340], ['caballero', 600, 270], ['caballero', 600, 170], ['caballero', 600, 370], ...fila('campesino', 700, 130, 5, 70)],
    cuando: (s) => s.units.filter((u) => !u.dead && u.type === 'rana').length >= 3,
  },
  susto: {   // el lamento de La Llorona: los enemigos cercanos huyen sin atacar
    azul: [['llorona', 330, 270], ...fila('campesino', 280, 170, 4, 70)],
    rojo: [...fila('caballero', 500, 140, 4, 80), ...fila('campesino', 560, 120, 6, 56), ...fila('arquero', 640, 160, 4, 70)],
    cuando: (s) => s.units.filter((u) => !u.dead && u.fear > 0).length >= 4,
  },
  furia: {   // Hércules con menos de la mitad de vida entra en furia
    azul: [['hercules', 330, 270], ['robin', 250, 230], ...fila('campesino', 280, 150, 4, 70)],
    rojo: [['gigante', 560, 270], ...fila('caballero', 520, 150, 4, 70), ...fila('campesino', 600, 130, 6, 56)],
    cuando: (s) => s.units.some((u) => !u.dead && u.type === 'hercules' && u.rage),
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
    const antes = esc.compuesta ? await page.locator('#cv').screenshot() : null;
    await page.click('#btnFight');
    const t0 = Date.now();
    let hecho = false;
    while (Date.now() - t0 < 25000) {
      const listo = await page.evaluate((src) => (new Function('s', 'return (' + src + ')(s)'))(window.GuerrerosGelatina.api.state), esc.cuando.toString());
      if (listo) {
        await sleep(90);
        const archivo = path.join(destino, 'batalla-' + nombre + (idioma === 'es' ? '' : '-' + idioma) + '.png');
        const png = await page.locator('#cv').screenshot();
        const ETIQ = { es: ['ANTES', 'DESPUÉS'], en: ['BEFORE', 'AFTER'], zh: ['之前', '之后'] }[idioma];
        const b64 = await page.evaluate(async ({ data, previa, etiquetas }) => {   // se normaliza a 1200×675, la forma de tarjeta de las publicaciones
          const cargar = async (d) => { const img = new Image(); img.src = 'data:image/png;base64,' + d; await img.decode(); return img; };
          const img = await cargar(data);
          const c = document.createElement('canvas'); c.width = 1200; c.height = 675;
          const g = c.getContext('2d'); g.imageSmoothingQuality = 'high';
          if (!previa) { g.drawImage(img, 0, 0, 1200, 675); return c.toDataURL('image/png').split(',')[1]; }
          await document.fonts.load('700 30px Fredoka');
          const otra = await cargar(previa);
          [[otra, 0, etiquetas[0]], [img, 338, etiquetas[1]]].forEach(([im, y, texto]) => {
            const alto = 337, sh = im.width * alto / 1200;
            g.drawImage(im, 0, (im.height - sh) / 2, im.width, sh, 0, y, 1200, alto);   // franja central del campo: ahí está la acción
            g.font = '700 30px Fredoka, sans-serif'; g.textBaseline = 'middle';
            const w = g.measureText(texto).width + 36;
            g.fillStyle = 'rgba(21,32,59,.86)'; g.beginPath(); g.roundRect(18, y + 16, w, 46, 23); g.fill();
            g.fillStyle = '#fff'; g.fillText(texto, 36, y + 40);
          });
          g.fillStyle = '#fff'; g.fillRect(0, 336, 1200, 3);
          return c.toDataURL('image/png').split(',')[1];
        }, { data: png.toString('base64'), previa: antes ? antes.toString('base64') : null, etiquetas: ETIQ });
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
