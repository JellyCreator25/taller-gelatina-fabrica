// Prueba un juego construido por la fábrica con un Chromium real y prepara sus medios (capturas, portada y clip).
// Uso: node herramientas/probar.js <id> [--rapido | --portada]   (necesita playwright; los clips necesitan ffmpeg)
//   --rapido   solo las pruebas funcionales, sin portada ni clips
//   --portada  solo vuelve a componer la portada con medios/portada-fuente.png (útil al retocar herramientas/portada.html)
// Cada plantilla trae su escenario en plantillas/<nombre>/prueba.js: { listo: selector, async jugar(page, ctx) }.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const RAIZ = path.resolve(__dirname, '..');
const id = process.argv[2];
const RAPIDO = process.argv.includes('--rapido');
const SOLO_PORTADA = process.argv.includes('--portada');
if (!id) { console.error('Uso: node herramientas/probar.js <id>'); process.exit(2); }
const spec = JSON.parse(fs.readFileSync(path.join(RAIZ, 'juegos', id, 'juego.json'), 'utf8'));
const dir = path.join(RAIZ, 'salida', id), medios = path.join(dir, 'medios');
fs.mkdirSync(medios, { recursive: true });
const escenario = require(path.join(RAIZ, 'plantillas', spec.plantilla, 'prueba.js'));
const url = 'file://' + path.join(dir, 'index.html');
const LOCALE = spec.idiomas[0] === 'es' ? 'es-MX' : 'en-US';   // las capturas salen en el primer idioma de la ficha

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const informe = [];
let fallos = 0;
const log = (m) => { informe.push(m); console.log(m); };
const chequear = (c, m) => { if (c) log('ok     · ' + m); else { fallos++; log('FALLA  · ' + m); } };
const assert = (c, m) => { if (!c) throw new Error(m); };
const esc = (t) => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;');

async function correr(browser, nombre, slug, opts) {
  log('— ' + nombre);
  const ctx = await browser.newContext(Object.assign({ locale: LOCALE }, opts));
  const page = await ctx.newPage();
  const errores = [], externas = [];
  page.on('pageerror', (e) => errores.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error') errores.push('consola: ' + m.text()); });
  page.on('request', (r) => { if (!/^(file|data|blob|about):/.test(r.url())) externas.push(r.url().slice(0, 100)); });
  try {
    await page.goto(url);
    await page.waitForSelector(escenario.listo || 'body');
    await sleep(900);
    const inicio = await page.evaluate(async () => {
      await document.fonts.ready;
      const f = [...document.fonts];
      return { ggx: typeof window.GGX === 'object' && !!window.GGX.version,
        cargadas: f.filter((x) => x.status === 'loaded').length, conError: f.filter((x) => x.status === 'error').length,
        desborde: document.documentElement.scrollWidth - window.innerWidth };
    });
    chequear(inicio.ggx, 'el motor común (GGX) está cargado');
    chequear(inicio.cargadas > 0 && inicio.conError === 0, 'tipografías incrustadas: ' + inicio.cargadas + ' en uso, ' + inicio.conError + ' con error');
    chequear(inicio.desborde <= 1, 'sin desplazamiento horizontal al abrir (' + inicio.desborde + ' px de más)');
    const res = await escenario.jugar(page, { modo: 'prueba', medios, log, assert, nombre, slug });
    chequear(true, 'escenario completo ' + JSON.stringify(res || {}));
    const fin = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    chequear(fin <= 1, 'sin desplazamiento horizontal al terminar (' + fin + ' px de más)');
  } catch (e) { chequear(false, 'escenario: ' + e.message); }
  chequear(errores.length === 0, 'sin errores de consola ni de página' + (errores.length ? ': ' + errores.slice(0, 3).join(' || ') : ''));
  chequear(externas.length === 0, 'sin conexiones externas' + (externas.length ? ': ' + externas.slice(0, 3).join(', ') : ''));
  await ctx.close();
}

// Portada «de héroes»: las Leyendas se dibujan con el propio código del juego (la plantilla expone drawJelly solo dentro de su función; aquí se
// pone una copia temporal de index.html con una línea más que la deja a mano) y quedan sobre fondo transparente. No toca el juego publicado.
// juego.json → portada.reparto: [tipo, equipo (0 azul, 1 rojo), x, y, escala, dirección (1 | -1), golpe (0 a 1)] sobre un lienzo de 630×500.
async function arteHeroes(browser, reparto) {
  const origen = path.join(dir, 'index.html');
  let html = fs.readFileSync(origen, 'utf8');
  const gancho = 'else boot();\n})();';
  if (html.split(gancho).length !== 2) throw new Error('la plantilla de «' + id + '» no permite dibujar la portada de héroes (no encuentro «else boot();» al final de su script)');
  html = html.replace(gancho, 'else boot();\nwindow.__dibujo = { drawJelly, UNITS, teamColor };\n})();');
  const tmp = fs.mkdtempSync(path.join(require('os').tmpdir(), 'portada-'));
  try {
    const archivo = path.join(tmp, 'juego.html');
    fs.writeFileSync(archivo, html);
    const ctx = await browser.newContext({ viewport: { width: 1300, height: 900 } });
    const page = await ctx.newPage();
    await page.goto('file://' + archivo);
    await page.waitForSelector('#cv');
    const url = await page.evaluate((lista) => {
      const { drawJelly, UNITS, teamColor } = window.__dibujo;
      const c = document.createElement('canvas'); c.width = 1260; c.height = 1000;
      const x = c.getContext('2d'); x.scale(2, 2);
      for (const [t] of lista) if (!UNITS[t]) throw new Error('portada.reparto: la unidad «' + t + '» no existe');
      for (const [t, eq, px, py, s, dir, golpe] of lista.slice().sort((a, b) => a[3] - b[3])) {   // de atrás hacia adelante
        const r = UNITS[t].r * s, col = teamColor(eq);
        x.fillStyle = 'rgba(8,16,40,.38)'; x.beginPath(); x.ellipse(px, py + r * 0.7, r * 1.15, r * 0.42, 0, 0, Math.PI * 2); x.fill();
        x.globalAlpha = 0.9; x.strokeStyle = col; x.lineWidth = 1.3 * s; x.beginPath(); x.ellipse(px, py + r * 0.7, r * 1.17, r * 0.48, 0, 0, Math.PI * 2); x.stroke();
        x.globalAlpha = 0.55; x.strokeStyle = '#ffd24a'; x.lineWidth = 0.8 * s; x.beginPath(); x.ellipse(px, py + r * 0.7, r * 1.34, r * 0.58, 0, 0, Math.PI * 2); x.stroke();
        x.globalAlpha = 1;
        drawJelly(x, t, col, px, py, { scale: s, dir, swing: golpe });
      }
      return c.toDataURL('image/png');
    }, reparto);
    await ctx.close();
    return url;
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
}

function lineasDeTitulo(titulo) {   // dos líneas lo más parejas posible; un título de una sola palabra queda en una línea
  const w = String(titulo).trim().split(/\s+/);
  if (w.length < 2) return [w.join(' '), ''];
  let mejor = 1, dif = Infinity;
  for (let k = 1; k < w.length; k++) { const d = Math.abs(w.slice(0, k).join(' ').length - w.slice(k).join(' ').length); if (d < dif) { dif = d; mejor = k; } }
  return [w.slice(0, mejor).join(' '), w.slice(mejor).join(' ')];
}

async function portada(browser) {
  log('— portada');
  const p = spec.portada || {};
  const heroes = p.estilo === 'heroes';
  const fuente = path.join(medios, 'portada-fuente.png');
  if (!heroes && !fs.existsSync(fuente)) { chequear(false, 'el escenario no dejó portada-fuente.png'); return; }
  const mapa = JSON.parse(fs.readFileSync(path.join(RAIZ, 'motor', 'fuentes', 'fuentes.json'), 'utf8'));
  let css = '';
  for (const fam of ['Fredoka', 'Nunito Sans']) {
    for (const [peso, arch] of Object.entries(mapa[fam])) {
      const b64 = fs.readFileSync(path.join(RAIZ, 'motor', 'fuentes', arch)).toString('base64');
      css += "@font-face{font-family:'" + fam + "';font-weight:" + peso + ';src:url(data:font/woff2;base64,' + b64 + ") format('woff2')}\n";
    }
  }
  const idioma = spec.idiomas[0], f = spec.ficha[idioma];
  const gratis = ['donar', 'gratis'].includes((spec.precio || {}).modo);
  const sello = idioma === 'en' ? (gratis ? 'Free in your browser' : 'Play in your browser') : (gratis ? 'Gratis en el navegador' : 'Juega en el navegador');
  const lema = (p.lema || {})[idioma] || f.corta.split(/[.!?]/)[0];
  let marcas, plantilla;
  if (heroes) {
    if (!Array.isArray(p.reparto) || !p.reparto.length) { chequear(false, 'portada.estilo es «heroes» pero falta portada.reparto en juego.json'); return; }
    let arte;
    try { arte = await arteHeroes(browser, p.reparto); } catch (e) { chequear(false, 'arte de la portada: ' + e.message); return; }
    const sitio = JSON.parse(fs.readFileSync(path.join(RAIZ, 'publicacion', 'sitio.json'), 'utf8'));
    const [l1, l2] = lineasDeTitulo(f.titulo);
    marcas = { '@@FUENTES@@': css, '@@ARTE@@': arte, '@@L1@@': esc(l1), '@@L2@@': esc(l2), '@@LEMA@@': esc(lema), '@@SELLO@@': esc(sello), '@@ESTUDIO@@': esc(sitio.nombre || '') };
    plantilla = 'portada-heroes.html';
  } else {
    const img = 'data:image/png;base64,' + fs.readFileSync(fuente).toString('base64');
    marcas = { '@@FUENTES@@': css, '@@A@@': p.color_a || '#2f6bdc', '@@B@@': p.color_b || '#e04a34', '@@TITULO@@': esc(f.titulo), '@@LEMA@@': esc(lema), '@@SELLO@@': sello, '@@CLASE@@': p.vertical ? 'vertical' : '', '@@IMG@@': img };
    plantilla = 'portada.html';
  }
  let html = fs.readFileSync(path.join(__dirname, plantilla), 'utf8');
  for (const [k, v] of Object.entries(marcas)) html = html.split(k).join(v);
  const ctx = await browser.newContext({ viewport: { width: 630, height: 500 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  await page.setContent(html);
  await page.evaluate(() => document.fonts.ready);
  await sleep(150);
  await page.screenshot({ path: path.join(medios, 'portada.png') });
  await ctx.close();
  chequear(fs.statSync(path.join(medios, 'portada.png')).size > 20000, 'portada.png generada (1260×1000)');
}

async function clip(browser, nombre, slug, ancho, alto, conGif) {
  log('— ' + nombre);
  const tmp = path.join(medios, 'tmp-video');
  fs.rmSync(tmp, { recursive: true, force: true });
  fs.mkdirSync(tmp, { recursive: true });
  const ctx = await browser.newContext({ locale: LOCALE, viewport: { width: ancho, height: alto }, recordVideo: { dir: tmp, size: { width: ancho, height: alto } } });
  const page = await ctx.newPage();
  const video = page.video();
  try {
    await page.goto(url);
    await page.waitForSelector(escenario.listo || 'body');
    await escenario.jugar(page, { modo: 'video', medios, log, assert, nombre, slug });
  } catch (e) { chequear(false, 'clip: ' + e.message); }
  await ctx.close();
  const webm = await video.path();
  const mp4 = path.join(medios, slug + '.mp4'), gif = path.join(medios, slug + '.gif');
  try {
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', webm, '-vf', 'fps=30,scale=' + ancho + ':-2', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4]);
    const dur = Number(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', mp4]).toString().trim());
    let extra = '';
    if (conGif) {   // GIF corto y liviano con el tramo final; cada escenario puede ajustarlo con `gif: { ultimos, duracion }` (segundos)
      const g = Object.assign({ ultimos: 14, duracion: 12 }, escenario.gif || {});
      execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-ss', String(Math.max(0, dur - g.ultimos)), '-t', String(g.duracion), '-i', mp4, '-vf', 'fps=10,scale=420:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4', gif]);
      extra = ' y ' + slug + '.gif (' + Math.round(fs.statSync(gif).size / 1024) + ' KB)';
    }
    chequear(dur > 8, slug + '.mp4 generado (' + dur.toFixed(1) + ' s, ' + Math.round(fs.statSync(mp4).size / 1024) + ' KB)' + extra);
  } catch (e) { chequear(false, 'no se pudo convertir el clip (¿está ffmpeg instalado?): ' + String(e.message).split('\n')[0]); }
  fs.rmSync(tmp, { recursive: true, force: true });
}

(async () => {
  const browser = await chromium.launch();
  if (SOLO_PORTADA) { await portada(browser); await browser.close(); process.exit(fallos ? 1 : 0); }
  await correr(browser, 'escritorio 1280×800', 'escritorio', { viewport: { width: 1280, height: 800 }, deviceScaleFactor: 2 });
  await correr(browser, 'celular 390×844', 'celular', { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  if (RAPIDO) log('— (modo rápido: sin portada ni clips)');
  else {
    await portada(browser);
    const dim = escenario.clip || { ancho: 960, alto: 600 };   // cada plantilla puede pedir otro tamaño (p. ej. juegos verticales)
    await clip(browser, 'clip principal ' + dim.ancho + '×' + dim.alto, 'clip', dim.ancho, dim.alto, true);
    await clip(browser, 'clip vertical (Shorts, Reels, TikTok)', 'clip-vertical', 540, 960, false);
  }
  await browser.close();
  fs.writeFileSync(path.join(dir, 'informe-pruebas.txt'), 'Informe de pruebas · ' + id + ' v' + spec.version + '\n\n' + informe.join('\n') + '\n\n' + (fallos ? fallos + ' prueba(s) fallaron' : 'Todo en orden') + '\n');
  console.log('\n' + (fallos ? fallos + ' prueba(s) fallaron' : 'Todo en orden'));
  process.exit(fallos ? 1 : 0);
})().catch((e) => { console.error('FALLO GENERAL', e); process.exit(1); });
