// Prepara lo que un portal pide para recibir un juego: portadas en sus tres formatos y videos de vista previa, a partir de la versión para portal ya construida.
// Uso: node herramientas/envio_portal.js <id> crazygames      (la versión se arma antes con «python3 fabrica.py monetizar variantes <id> crazygames»)
// Medidas y reglas de CrazyGames (leídas en https://docs.crazygames.com/requirements/game-covers/): portadas 1920×1080, 800×1200 y 800×800, sin bordes ni texto aparte del título;
// videos de 15 a 20 s, máximo 50 MB, 1080p horizontal (16:9) y vertical (2:3), sin sonido, sin pantallas negras ni transiciones de logotipo.
// Cada plantilla trae su parte en plantillas/<nombre>/prueba.js → envio(page, { segundos, marcar, capturar, parar_tras_captura }).
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { tipografias } = require('./arte.js');

const RAIZ = path.resolve(__dirname, '..');
const [id, portal] = process.argv.slice(2);
if (!id || portal !== 'crazygames') { console.error('Uso: node herramientas/envio_portal.js <id> crazygames'); process.exit(2); }
const spec = JSON.parse(fs.readFileSync(path.join(RAIZ, 'juegos', id, 'juego.json'), 'utf8'));
const escenario = require(path.join(RAIZ, 'plantillas', spec.plantilla, 'prueba.js'));
if (typeof escenario.envio !== 'function') { console.error('La plantilla «' + spec.plantilla + '» todavía no sabe jugar para el paquete de envío (falta envio() en su prueba.js).'); process.exit(2); }
const variante = path.join(RAIZ, 'dist', 'portales', id, portal, 'index.html');
if (!fs.existsSync(variante)) { console.error('Falta la versión para el portal: python3 fabrica.py monetizar variantes ' + id + ' ' + portal); process.exit(2); }
const salida = path.join(RAIZ, 'salida', id, 'medios', portal);
const tmp = path.join(RAIZ, 'dist', 'portales', id, portal, 'tmp-envio');
fs.rmSync(salida, { recursive: true, force: true }); fs.mkdirSync(salida, { recursive: true });
fs.rmSync(tmp, { recursive: true, force: true }); fs.mkdirSync(tmp, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const esc = (t) => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;');
let fallos = 0;
const ok = (c, m) => { console.log((c ? 'ok     · ' : 'FALLA  · ') + m); if (!c) fallos++; };
// El SDK del portal no existe fuera de su sitio: un doble mínimo deja que el juego arranque igual que allá (sin anuncios en el Basic Launch).
const SDK_FALSO = "window.CrazyGames={SDK:{init:()=>Promise.resolve(),ad:{requestAd:(t,c)=>{c.adError&&c.adError('basic')}},game:{gameplayStart(){},gameplayStop(){},loadingStart(){},loadingStop(){}},user:{systemInfo:{locale:'en-US'}}}};";
const url = 'file://' + variante + '?lang=en';

// Para los videos: sin la cabecera de la página y con el fondo en degradado de la portada, de modo que el escenario ocupe el cuadro (el juego no se toca).
const estiloDeVideo = () => 'html,body{background:linear-gradient(135deg,' + ((spec.portada || {}).color_a || '#2f6bdc') + ' 0%,' + ((spec.portada || {}).color_b || '#e04a34') + ' 100%) !important;min-height:100vh}'
  + 'header{display:none !important}.app{--chrome:0px !important;padding-block:0 !important;max-width:calc(100vh * 0.5625 + 32px) !important}';   // el escenario crece hasta ocupar todo el alto del cuadro (en la página real tiene un tope de 520 px)

async function abrir(browser, opts, paraVideo) {
  const ctx = await browser.newContext(Object.assign({ locale: 'en-US' }, opts));
  await ctx.route('https://sdk.crazygames.com/**', (r) => r.fulfill({ contentType: 'application/javascript', body: SDK_FALSO }));
  const page = await ctx.newPage();
  const errores = [];
  page.on('pageerror', (e) => errores.push(e.message));
  await page.goto(url);
  await page.waitForSelector(escenario.listo || 'body');
  if (paraVideo) await page.addStyleTag({ content: estiloDeVideo() });
  await sleep(900);
  return { ctx, page, errores };
}

function lineasDeTitulo(titulo) {
  const w = String(titulo).trim().split(/\s+/);
  if (w.length < 2) return [w.join(' '), ''];
  let mejor = 1, dif = Infinity;
  for (let k = 1; k < w.length; k++) { const d = Math.abs(w.slice(0, k).join(' ').length - w.slice(k).join(' ').length); if (d < dif) { dif = d; mejor = k; } }
  return [w.slice(0, mejor).join(' '), w.slice(mejor).join(' ')];
}

async function captura(browser) {   // el escenario del juego en inglés, con una racha ya lograda
  const { ctx, page, errores } = await abrir(browser, { viewport: { width: 1280, height: 800 }, deviceScaleFactor: 2 });
  const ruta = path.join(tmp, 'escenario.png');
  let hecha = false;
  await escenario.envio(page, { segundos: 40, parar_tras_captura: true, marcar() {}, capturar: async () => { await page.locator(spec.portada && spec.portada.selector || '#stage').screenshot({ path: ruta }); hecha = true; } });
  ok(hecha && errores.length === 0, 'captura del juego en inglés con racha' + (errores.length ? ' · errores: ' + errores.join(' | ') : ''));
  await ctx.close();
  return ruta;
}

async function portadas(browser, ruta) {
  const f = spec.ficha.en, p = spec.portada || {};
  const [l1, l2] = lineasDeTitulo(f.titulo);
  const img = 'data:image/png;base64,' + fs.readFileSync(ruta).toString('base64');
  const css = tipografias(RAIZ);
  const html = fs.readFileSync(path.join(__dirname, 'portada-portal.html'), 'utf8');
  const hechas = [];
  for (const [forma, nombre, w, h] of [['horizontal', 'portada-16x9-1920x1080', 1920, 1080], ['vertical', 'portada-2x3-800x1200', 800, 1200], ['cuadrada', 'portada-1x1-800x800', 800, 800]]) {
    const marcas = { '@@FUENTES@@': css, '@@A@@': p.color_a || '#2f6bdc', '@@B@@': p.color_b || '#e04a34', '@@L1@@': esc(l1), '@@L2@@': esc(l2), '@@IMG@@': img, '@@FORMA@@': forma, '@@W@@': w, '@@H@@': h };
    let doc = html;
    for (const [k, v] of Object.entries(marcas)) doc = doc.split(k).join(String(v));
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    await page.setContent(doc);
    await page.evaluate(() => document.fonts.ready);
    await sleep(150);
    const destino = path.join(salida, nombre + '.png');
    await page.screenshot({ path: destino });
    await ctx.close();
    const cab = fs.readFileSync(destino).subarray(16, 24);
    ok(cab.readUInt32BE(0) === w && cab.readUInt32BE(4) === h, nombre + '.png (' + w + '×' + h + ')');
    hechas.push(destino);
  }
  return hechas;
}

async function video(browser, nombre, ancho, alto) {
  const dir = path.join(tmp, nombre); fs.mkdirSync(dir, { recursive: true });
  const t0 = Date.now();
  let inicioJuego = null;
  const { ctx, page, errores } = await abrir(browser, { viewport: { width: ancho, height: alto }, recordVideo: { dir, size: { width: ancho, height: alto } } }, true);
  const v = page.video();
  await escenario.envio(page, { segundos: 24, marcar: () => { inicioJuego = (Date.now() - t0) / 1000; } });
  await ctx.close();
  const webm = await v.path();
  const mp4 = path.join(salida, nombre + '.mp4');
  // se recorta desde que empieza la partida (sin tarjeta de inicio, sello ni cuenta regresiva) y se deja en 19 s; sin sonido
  const desde = Math.max(0, (inicioJuego || 0) + 2.4);   // 2,4 s: pasa la cuenta regresiva del juego («Get ready!») y entra directo a tocar
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-ss', String(desde), '-i', webm, '-t', '19', '-an', '-vf', 'fps=30,scale=' + ancho + ':' + alto, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4]);
  const info = JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration,size:stream=codec_type,width,height', '-of', 'json', mp4]).toString());
  const dur = Number(info.format.duration), mb = Number(info.format.size) / 1048576;
  const sinAudio = !info.streams.some((s) => s.codec_type === 'audio');
  ok(dur >= 15 && dur <= 20.05 && mb <= 50 && sinAudio && errores.length === 0,
    nombre + '.mp4 (' + ancho + '×' + alto + ', ' + dur.toFixed(1) + ' s, ' + mb.toFixed(1) + ' MB, ' + (sinAudio ? 'sin sonido' : 'CON SONIDO') + ')' + (errores.length ? ' · errores: ' + errores.join(' | ') : ''));
}

(async () => {
  const browser = await chromium.launch();
  const ruta = await captura(browser);
  await portadas(browser, ruta);
  await video(browser, 'vista-previa-16x9-1920x1080', 1920, 1080);
  await video(browser, 'vista-previa-2x3-1080x1620', 1080, 1620);
  await browser.close();
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log(fallos ? fallos + ' comprobación(es) fallaron' : 'Paquete de portadas y videos listo en ' + path.relative(RAIZ, salida));
  process.exit(fallos ? 1 : 0);
})().catch((e) => { console.error('FALLO GENERAL', e); process.exit(1); });
