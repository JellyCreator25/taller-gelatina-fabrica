// Tarjetas de «Leyenda de la semana»: una imagen por Leyenda de un juego, con su poder y su frase, para el calendario de contenido.
// Uso: node herramientas/tarjetas.js <id-del-juego> [idioma]    → contenido/imagenes/leyenda-<unidad>.png (1200×675)
// Los personajes salen del propio código del juego (herramientas/arte.js); el texto, de juego.json → textos.<idioma>.u_<unidad>, u_<unidad>_tip y u_<unidad>_dice.
// Qué Leyendas y de qué equipo: juego.json → portada.reparto (las que ahí aparecen).
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { dibujarUnidades, tipografias } = require('./arte.js');

const RAIZ = path.resolve(__dirname, '..');
const id = process.argv[2];
if (!id) { console.error('Uso: node herramientas/tarjetas.js <id-del-juego> [idioma]'); process.exit(2); }
const spec = JSON.parse(fs.readFileSync(path.join(RAIZ, 'juegos', id, 'juego.json'), 'utf8'));
const idioma = process.argv[3] || spec.idiomas[0];
const t = spec.textos[idioma], f = spec.ficha[idioma];
const sitio = JSON.parse(fs.readFileSync(path.join(RAIZ, 'publicacion', 'sitio.json'), 'utf8'));
const destino = path.join(RAIZ, 'contenido', 'imagenes');
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const ETIQUETA = { es: 'Conoce a las Leyendas', en: 'Meet the Legends', zh: '认识传奇' }[idioma] || 'Meet the Legends';
const SELLO = { es: 'Gratis en el navegador', en: 'Free in your browser', zh: '免费网页游戏' }[idioma] || 'Free in your browser';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  fs.mkdirSync(destino, { recursive: true });
  const browser = await chromium.launch();
  const css = tipografias(RAIZ);
  const plantilla = fs.readFileSync(path.join(__dirname, 'tarjeta-leyenda.html'), 'utf8');
  const vistas = new Set();
  for (const [tipo, equipo] of spec.portada.reparto) {
    if (vistas.has(tipo) || !t['u_' + tipo + '_tip']) continue;   // solo las unidades que tienen ficha de poder
    vistas.add(tipo);
    const arte = await dibujarUnidades(browser, path.join(RAIZ, 'salida', id, 'index.html'), [[tipo, equipo, 252, 292, -86, 1, 0]], { ancho: 800, alto: 450, densidad: 1.5 });
    const marcas = { '@@FUENTES@@': css, '@@ARTE@@': arte, '@@ETIQUETA@@': esc(ETIQUETA), '@@NOMBRE@@': esc(t['u_' + tipo]), '@@PODER@@': esc(t['u_' + tipo + '_tip']),
      '@@FRASE@@': esc(t['u_' + tipo + '_dice'] || ''), '@@JUEGO@@': esc(f.titulo), '@@SELLO@@': esc(SELLO), '@@ESTUDIO@@': esc(sitio.nombre || '') };
    let html = plantilla;
    for (const [k, v] of Object.entries(marcas)) html = html.split(k).join(v);
    const ctx = await browser.newContext({ viewport: { width: 800, height: 450 }, deviceScaleFactor: 1.5 });
    const page = await ctx.newPage();
    await page.setContent(html);
    await page.evaluate(() => document.fonts.ready);
    await sleep(150);
    const archivo = path.join(destino, 'leyenda-' + tipo + '.png');
    await page.screenshot({ path: archivo });
    await ctx.close();
    console.log('ok     · ' + path.relative(RAIZ, archivo));
  }
  await browser.close();
})().catch((e) => { console.error('FALLA · ' + e.message); process.exit(1); });
