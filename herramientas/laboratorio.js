// Laboratorio de betas: ejecuta, en un Chromium real, las «celdas» que planeó herramientas/laboratorio.py y devuelve la telemetría cruda.
// Uso: node herramientas/laboratorio.js <plan.json> <salida.json>
// Cada celda (variante × perfil × prueba × semilla) corre en un CONTEXTO NUEVO: sin cookies, sin almacenamiento, sin caché, sin service workers, con la red controlada
// (solo se llega a un servidor local en 127.0.0.1 que sirve la variante; todo lo demás se corta y se anota), con el azar fijado por semilla y con el RELOJ FIJO
// (Playwright clock: Date, setTimeout, requestAnimationFrame y performance.now avanzan solo cuando la persona «deja pasar» tiempo). Por eso una sesión es reproducible
// y además rápida: esperar 20 segundos de juego no cuesta 20 segundos.
// Lo que sale se separa en dos mitades: lo DETERMINISTA (embudo, abandonos, errores, accesibilidad, traza) y lo MEDIDO (tiempos reales de esta computadora: ruido).
// El contrato está en motor/LABORATORIO.md.
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const [planRuta, salidaRuta] = process.argv.slice(2);
if (!planRuta || !salidaRuta) { console.error('Uso: node herramientas/laboratorio.js <plan.json> <salida.json>'); process.exit(2); }
const plan = JSON.parse(fs.readFileSync(planRuta, 'utf8'));
const EPOCA = '2026-01-01T00:00:00Z';
const TOPE_EVENTOS = 160;
const TOPE_CELDA_MS = 120000;                       // reloj real: una celda que no termina se corta y se marca como falla

// ---------- utilidades ----------
const mulberry = (semilla) => { let s = semilla >>> 0; return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; };
const hashTexto = (txt) => { let h = 2166136261; for (let i = 0; i < txt.length; i++) { h ^= txt.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return h >>> 0; };
const gauss = (rng) => { const u = Math.max(1e-9, rng()), v = rng(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
const sha = (x) => crypto.createHash('sha256').update(typeof x === 'string' ? x : JSON.stringify(x)).digest('hex').slice(0, 16);
const redondear = (n, d) => { const k = Math.pow(10, d == null ? 2 : d); return Math.round(n * k) / k; };
const corto = (s, n) => String(s).replace(/\s+/g, ' ').slice(0, n || 200);

// ---------- el servidor local: sirve cada variante desde memoria; solo escucha en 127.0.0.1 (nada sale a internet) ----------
const variantes = {};
for (const v of plan.variantes) {
  const raizHtml = path.dirname(v.html);
  let html = fs.readFileSync(v.html, 'utf8');
  for (const r of v.reemplazos || []) {
    const veces = html.split(r.buscar).length - 1;
    if (!veces) { console.error('REEMPLAZO SIN EFECTO en la variante «' + v.id + '»: no se encontró «' + corto(r.buscar, 60) + '»'); process.exit(3); }
    html = r.veces === 1 ? html.replace(r.buscar, () => r.poner) : html.split(r.buscar).join(r.poner);
  }
  variantes[v.id] = { raiz: raizHtml, html: Buffer.from(html, 'utf8'), consulta: v.consulta || '', juego: v.juego || null, css: v.css || '' };
}
const TIPOS = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.woff2': 'font/woff2', '.txt': 'text/plain; charset=utf-8' };
const servidor = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://127.0.0.1');
  if (u.pathname === '/favicon.ico') { res.writeHead(204); return res.end(); }
  const m = /^\/v\/([^/]+)\/(.*)$/.exec(u.pathname);
  const v = m && variantes[decodeURIComponent(m[1])];
  if (!v) { res.writeHead(404); return res.end('no existe'); }
  const rel = decodeURIComponent(m[2]) || 'index.html';
  if (rel === 'index.html') { res.writeHead(200, { 'content-type': TIPOS['.html'], 'cache-control': 'no-store' }); return res.end(v.html); }
  const ruta = path.resolve(v.raiz, rel);
  if (!ruta.startsWith(v.raiz + path.sep) || !fs.existsSync(ruta) || !fs.statSync(ruta).isFile()) { res.writeHead(404); return res.end('no existe'); }
  res.writeHead(200, { 'content-type': TIPOS[path.extname(ruta)] || 'application/octet-stream', 'cache-control': 'no-store' });
  res.end(fs.readFileSync(ruta));
});

// ---------- lo que se inyecta en cada página antes que nada ----------
function guionInicial(arg) {
  // un contador de entradas que la página ya procesó: el ejecutor lo usa como barrera para que cada toque, clic o tecla se «sienta» antes de dejar pasar más tiempo (si no, el orden entre la entrada y el reloj depende de la carga de la computadora)
  window.__lab = { n: 0, clic: 0 };
  ['touchstart', 'touchmove', 'touchend', 'touchcancel', 'pointerdown', 'pointermove', 'pointerup', 'pointercancel', 'mousedown', 'mousemove', 'mouseup', 'keydown', 'keyup'].forEach((t) => addEventListener(t, () => { window.__lab.n++; }, true));
  addEventListener('click', () => { window.__lab.clic++; }, true);
  let s = (arg.semilla >>> 0) || 1;
  Math.random = function () { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  if (arg.juego) {                                                   // cambia mecánicas o textos de la variante sin reconstruir el juego: se mezcla en window.JUEGO cuando la página lo define
    let guardado;
    const mezcla = (a, b) => { Object.keys(b).forEach((k) => { if (b[k] && typeof b[k] === 'object' && !Array.isArray(b[k]) && a[k] && typeof a[k] === 'object' && !Array.isArray(a[k])) mezcla(a[k], b[k]); else a[k] = b[k]; }); return a; };
    Object.defineProperty(window, 'JUEGO', { configurable: true, get() { return guardado; }, set(x) { guardado = (x && typeof x === 'object') ? mezcla(x, JSON.parse(JSON.stringify(arg.juego))) : x; } });
  }
  if (arg.css) document.addEventListener('DOMContentLoaded', () => { const st = document.createElement('style'); st.setAttribute('data-laboratorio', '1'); st.textContent = arg.css; document.head.appendChild(st); });
}

// ---------- la auditoría de accesibilidad y de uso (corre dentro de la página; todo lo que devuelve es determinista) ----------
function auditar(o) {
  const out = {};
  const add = (codigo, ejemplo) => { const k = out[codigo] || (out[codigo] = { codigo, n: 0, ejemplo: ejemplo || '' }); k.n++; };
  const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && cs.opacity !== '0'; };
  const desc = (el) => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\s+/)[0] : '');
  const luz = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const rgba = (txt) => { const m = /rgba?\(([^)]+)\)/.exec(txt || ''); if (!m) return null; const p = m[1].split(',').map((x) => parseFloat(x)); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const nombre = (el) => {
    const aria = (el.getAttribute('aria-label') || '').trim(); if (aria) return aria;
    const por = el.getAttribute('aria-labelledby'); if (por) { const t = por.split(/\s+/).map((i) => { const x = document.getElementById(i); return x ? x.textContent : ''; }).join(' ').trim(); if (t) return t; }
    const txt = (el.innerText || el.textContent || '').trim(); if (txt) return txt;
    if (el.getAttribute('title')) return el.getAttribute('title');
    const img = el.querySelector && el.querySelector('img[alt]'); if (img && img.getAttribute('alt').trim()) return img.getAttribute('alt');
    if (el.tagName === 'INPUT' && (el.value || el.placeholder)) return el.value || el.placeholder;
    if (el.labels && el.labels.length) return el.labels[0].textContent.trim();
    return '';
  };
  if (!document.documentElement.getAttribute('lang')) add('idioma-falta', 'html');
  if (!document.title.trim()) add('titulo-falta', 'title');
  if (!document.querySelector('meta[name=viewport]')) add('viewport-falta', 'head');
  document.querySelectorAll('img').forEach((im) => { if (visible(im) && !im.hasAttribute('alt') && im.getAttribute('role') !== 'presentation') add('imagen-sin-alt', desc(im)); });
  const minimo = o.tactil ? 44 : 24;
  document.querySelectorAll('button, a[href], input:not([type=hidden]), select, textarea, [role=button], [tabindex]:not([tabindex="-1"])').forEach((el) => {
    if (!visible(el) || el.disabled) return;
    const rol = el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'button';
    if ((rol || /^(INPUT|SELECT|TEXTAREA)$/.test(el.tagName)) && !nombre(el)) add('control-sin-nombre', desc(el));
    if (el.tagName === 'CANVAS' || el.getAttribute('tabindex') !== null && !rol && !/^(INPUT|SELECT|TEXTAREA)$/.test(el.tagName)) return;     // los lienzos de juego se miden por separado
    const r = el.getBoundingClientRect();
    if (r.width < minimo || r.height < minimo) add(o.tactil ? 'objetivo-chico-tactil' : 'objetivo-chico', desc(el) + ' ' + Math.round(r.width) + '×' + Math.round(r.height));
  });
  if (document.documentElement.scrollWidth > window.innerWidth + 1) add('desborde-horizontal', document.documentElement.scrollWidth + '>' + window.innerWidth);
  let contados = 0;
  const hojas = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const vistos = new Set();
  for (let n = hojas.nextNode(); n && contados < 400; n = hojas.nextNode()) {
    if (!n.textContent.trim()) continue;
    const el = n.parentElement; if (!el || vistos.has(el) || /^(SCRIPT|STYLE|NOSCRIPT)$/.test(el.tagName) || !visible(el)) continue;
    vistos.add(el); contados++;
    const cs = getComputedStyle(el);
    const px = parseFloat(cs.fontSize);
    if (px < (o.tactil ? 14 : 12)) add('texto-chico', desc(el) + ' ' + px + 'px');
    const fg = rgba(cs.color); if (!fg) continue;
    let bg = null, cubre = false;
    for (let p = el; p; p = p.parentElement) {
      const s = getComputedStyle(p);
      if (s.backgroundImage && s.backgroundImage !== 'none') { cubre = true; break; }
      const c = rgba(s.backgroundColor);
      if (c && c[3] > 0.99) { bg = c; break; }
    }
    if (cubre) continue;
    if (!bg) bg = [255, 255, 255, 1];
    const a = luz(fg), b = luz(bg);
    const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    const grande = px >= 24 || (px >= 18.66 && parseInt(cs.fontWeight, 10) >= 700);
    if (ratio < (grande ? 3 : 4.5)) add('contraste-bajo', desc(el) + ' ' + ratio.toFixed(2) + ':1');
  }
  if (o.movimientoReducido && document.getAnimations && document.getAnimations().some((a) => a.playState === 'running')) add('ignora-movimiento-reducido', 'animaciones activas con prefers-reduced-motion');
  return Object.keys(out).sort().map((k) => out[k]);
}

// ---------- una sesión: una persona (perfil) con una variante, en un contexto aislado ----------
async function contextoAislado(browser, cell, perfil, variante, opciones) {
  const d = perfil.dispositivo;
  const ctx = await browser.newContext({
    viewport: { width: d.ancho, height: d.alto }, deviceScaleFactor: d.escala, isMobile: !!d.movil, hasTouch: !!d.tactil,
    locale: perfil.idioma, timezoneId: perfil.zona, colorScheme: perfil.ambiente.tema === 'oscuro' ? 'dark' : 'light',
    reducedMotion: perfil.ambiente.movimiento_reducido ? 'reduce' : 'no-preference',
    serviceWorkers: 'block', acceptDownloads: false, permissions: [], javaScriptEnabled: true,
  });
  const reg = { pagina: [], consola: [], red: [], bloqueadas: [], solicitudes: 0, peso: 0 };
  const nota = (lista, txt) => { const t = corto(txt, 220); if (lista.length < 12 && lista.indexOf(t) < 0) lista.push(t); };
  await ctx.route('**/*', (route) => {
    const u = new URL(route.request().url());
    if (u.hostname === '127.0.0.1' && String(u.port) === String(plan.puerto)) { reg.solicitudes++; return route.continue(); }
    nota(reg.bloqueadas, u.host + u.pathname.slice(0, 60));
    return route.abort('blockedbyclient');
  });
  await ctx.addInitScript(guionInicial, { semilla: cell.semilla, juego: variante.juego, css: variante.css });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => nota(reg.pagina, e.message));
  page.on('console', (m) => { if (m.type() === 'error' && !/^Failed to load resource/.test(m.text())) nota(reg.consola, m.text()); });   // los recursos que faltan o se cortan ya quedan en «red» y «bloqueadas»
  page.on('response', (r) => { const u = new URL(r.url()); if (u.hostname === '127.0.0.1' && r.status() >= 400) nota(reg.red, r.status() + ' ' + u.pathname.replace(/^\/v\/[^/]+\//, '/')); });
  page.on('requestfinished', async (r) => { try { const z = await r.sizes(); reg.peso += z.responseBodySize + z.responseHeadersSize; } catch (e) { /* una solicitud que ya no existe */ } });
  const cdp = await ctx.newCDPSession(page);
  if (perfil.cpu > 1) await cdp.send('Emulation.setCPUThrottlingRate', { rate: perfil.cpu });
  if (!opciones || opciones.reloj !== false) {
    await page.clock.install({ time: new Date(EPOCA) });
    await page.clock.pauseAt(new Date(Date.parse(EPOCA) + 1000));   // sin pauseAt el reloj falso sigue corriendo con el real: el tiempo solo avanza cuando la persona lo deja pasar
  }
  return { ctx, page, cdp, reg };
}

function cargaModelada(perfil, solicitudes, bytes) {
  const r = perfil.red;
  const viajes = 1 + Math.ceil(Math.max(0, solicitudes - 1) / 6);                 // conexión + respuesta, y las demás solicitudes de seis en seis
  const descarga = r.bajada_kbps > 0 ? (bytes * 8) / r.bajada_kbps : 0;           // bits / (kbit/s) = ms
  return Math.round(r.latencia_ms * viajes + descarga + 40 * perfil.cpu);
}

async function sesion(browser, cell) {
  const perfil = cell.perfil, variante = variantes[cell.variante];
  const rng = mulberry(cell.semilla * 7919 + hashTexto(perfil.id + '|' + cell.variante + '|' + cell.prueba.id));
  const { ctx, page, cdp, reg } = await contextoAislado(browser, cell, perfil, variante);
  const S = { t: 0, datos: {}, embudo: [], eventos: [], estado: 'completo', abandono: null, falla: null, primera: null, acciones: 0, interrumpida: new Set() };
  const real = { carga: 0, ms: 0, sim: 0, max: 0 };
  const ev = (tipo, extra) => { if (S.eventos.length < TOPE_EVENTOS) S.eventos.push(Object.assign({ t: Math.round(S.t), tipo }, extra || {})); };
  const pasar = async (ms) => {
    ms = Math.max(0, Math.round(ms)); if (!ms) return;
    const t0 = Date.now(); await page.clock.runFor(ms); const dt = Date.now() - t0;
    S.t += ms;
    if (ms >= 200) { real.ms += dt; real.sim += ms; real.max = Math.max(real.max, dt); }
  };
  const abandonar = (paso, motivo, extra) => { S.estado = 'abandono'; S.abandono = Object.assign({ paso, motivo }, extra || {}); ev('abandono', { paso, motivo }); };
  const fallar = (paso, mensaje) => { S.estado = 'falla'; S.falla = { paso, mensaje: corto(mensaje, 200) }; ev('falla', { paso, mensaje: corto(mensaje, 120) }); };
  let aislado = true, auditoria = [], teclado = null;
  try {
    const url = 'http://127.0.0.1:' + plan.puerto + '/v/' + encodeURIComponent(cell.variante) + '/index.html' + construirConsulta(variante.consulta, cell.prueba.tipo === 'bots' ? 'bot=1' : '');
    const t0 = Date.now();
    await page.goto(url, { waitUntil: 'load', timeout: 30000 });
    real.carga = Date.now() - t0;
    // el reloj falso de la página nace con un desfase que depende de la carga de la computadora; se alinea la rejilla de fotogramas (múltiplos de 16 ms) para que dos sesiones iguales vean los mismos fotogramas
    const p0 = await page.evaluate(() => performance.now());
    const alinear = Math.ceil(p0 / 16) * 16 - p0;
    if (alinear > 0) await page.clock.runFor(alinear);
    S.t = 0;
    if (variante.juego) {                                              // una variante que no se aplicó en silencio sería un experimento inútil: se comprueba
      const sin = await page.evaluate((cambios) => {
        const falta = [], mira = (obj, real, ruta) => { Object.keys(obj).forEach((k) => { const r = real == null ? undefined : real[k]; if (obj[k] && typeof obj[k] === 'object' && !Array.isArray(obj[k])) mira(obj[k], r, ruta + k + '.'); else if (JSON.stringify(r) !== JSON.stringify(obj[k])) falta.push(ruta + k); }); };
        mira(cambios, window.JUEGO, 'JUEGO.'); return falta;
      }, variante.juego);
      if (sin.length) { fallar('interno', 'la variante «' + cell.variante + '» no se aplicó en la página: ' + sin.slice(0, 3).join(', ') + ' (¿la página define window.JUEGO?)'); throw new Error('variante-no-aplicada'); }
    }
    aislado = await page.evaluate(() => { try { return localStorage.length === 0 && sessionStorage.length === 0 && document.cookie === ''; } catch (e) { return true; } });
    await pasar(300);                                                 // la página arranca sus temporizadores
    const modelada = cargaModelada(perfil, Math.max(1, reg.solicitudes), reg.peso);
    ev('carga', { modelada_ms: modelada, bytes: reg.peso, solicitudes: reg.solicitudes });
    S.t = modelada;
    auditoria = await page.evaluate(auditar, { tactil: !!perfil.dispositivo.tactil, movimientoReducido: !!perfil.ambiente.movimiento_reducido });
    if (cell.prueba.tipo === 'auditoria') {
      await page.keyboard.press('Tab'); await page.keyboard.press('Tab'); await page.keyboard.press('Tab');
      teclado = await page.evaluate(() => { const a = document.activeElement; return !!a && a !== document.body && a !== document.documentElement; });
      if (!teclado) auditoria.push({ codigo: 'teclado-sin-foco', n: 1, ejemplo: 'Tab no llega a ningún control' });
      await pasar(Math.min(cell.prueba.observar_ms || 3000, 60000));
      ev('observado');
    } else if (modelada > perfil.conducta.paciencia_carga_ms) {
      abandonar('carga', 'carga-lenta', { modelada_ms: modelada, paciencia_ms: perfil.conducta.paciencia_carga_ms });
    } else if (cell.prueba.tipo === 'guion') {
      await correrPasos(cell.prueba.pasos, { page, cdp, rng, perfil, S, pasar, ev, abandonar, fallar });
    }
  } catch (e) {
    if (e.message !== 'variante-no-aplicada') fallar('interno', e.message || e);
  }
  let memoria = null;
  try { memoria = await page.evaluate(() => (performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576 * 10) / 10 : null)); } catch (e) { /* la página ya no está */ }
  await ctx.close();
  for (const k of ['pagina', 'consola', 'red', 'bloqueadas']) reg[k].sort();                 // el orden en que llegan los avisos de la página depende de la carga de la computadora
  const traza = sha({ e: S.estado, a: S.abandono, f: S.falla, m: S.embudo, d: S.datos, v: S.eventos, x: auditoria.map((a) => a.codigo + ':' + a.n), r: [reg.pagina, reg.consola, reg.red, reg.bloqueadas] });
  return {
    cell: { variante: cell.variante, perfil: perfil.id, prueba: cell.prueba.id, semilla: cell.semilla, repeticion: !!cell.repeticion },
    estado: S.estado, abandono: S.abandono, falla: S.falla, embudo: S.embudo, datos: S.datos, primera_accion_ms: S.primera, acciones: S.acciones,
    carga_modelada_ms: ((S.eventos.find((x) => x.tipo === 'carga')) || {}).modelada_ms || null, peso_bytes: reg.peso, solicitudes: reg.solicitudes,
    errores: { pagina: reg.pagina, consola: reg.consola, red: reg.red, bloqueadas: reg.bloqueadas }, a11y: auditoria, aislado, traza,
    eventos: S.eventos, ms_simulados: Math.round(S.t),
    medido: { carga_real_ms: real.carga, ritmo_cpu: real.sim ? redondear(real.ms / real.sim, 3) : null, pasada_max_ms: real.max, memoria_mb: memoria },
  };
}

function construirConsulta(base, extra) {
  const partes = [String(base || '').replace(/^\?/, ''), extra].filter(Boolean);
  return partes.length ? '?' + partes.join('&') : '';
}

// ---------- los pasos de una persona ----------
const VERBOS_DE_ENTRADA = ['tocar', 'arrastrar', 'mantener', 'tecla', 'escribir'];
async function correrPasos(pasos, X) {
  const { page, perfil, S, ev, abandonar, fallar, pasar } = X;
  for (let i = 0; i < pasos.length && S.estado === 'completo'; i++) {
    await unPaso(pasos[i], X, 'p' + (i + 1));
  }
}

async function unPaso(paso, X, id) {
  const { page, cdp, rng, perfil, S, ev, abandonar, fallar, pasar } = X;
  const verbo = ['esperar', 'esperar_hasta', 'tocar', 'arrastrar', 'mantener', 'tecla', 'escribir', 'leer', 'verificar', 'pasar', 'interrumpir', 'repetir'].find((v) => paso[v] !== undefined);
  const nombre = paso.id || id;
  if (paso.si && paso.si.entrada && [].concat(paso.si.entrada).indexOf(perfil.entrada) < 0) return;
  if (paso.si && paso.si.dispositivo && paso.si.dispositivo !== (perfil.dispositivo.tactil ? 'tactil' : 'escritorio')) return;
  const ritmo = perfil.conducta.ritmo;
  if (perfil.entrada === 'teclado' && ['tocar', 'arrastrar', 'mantener'].indexOf(verbo) >= 0 && !paso.si) return void abandonar(nombre, 'requiere-puntero', { verbo });
  const paciencia = paso.paciencia != null ? paso.paciencia : perfil.conducta.paciencia_ms;
  if (paso.pausa) await pasar(paso.pausa * ritmo);
  if (VERBOS_DE_ENTRADA.indexOf(verbo) >= 0) {
    await pasar(perfil.conducta.reaccion_ms * ritmo);
    await interrupcionesPendientes(X);
  }
  const marcar = () => { if (paso.embudo && !S.embudo.some((x) => x.etapa === paso.embudo)) { S.embudo.push({ etapa: paso.embudo, t: Math.round(S.t) }); ev('embudo', { etapa: paso.embudo }); } };
  const sinExito = (motivo, extra) => { if (paso.opcional) { ev('omitido', { paso: nombre, motivo }); return false; } abandonar(nombre, motivo, extra); return false; };
  const accion = () => { S.acciones++; if (S.primera === null) S.primera = Math.round(S.t); };
  try {
    switch (verbo) {
      case 'esperar': {
        const r = await esperarListo(page, paso.esperar, paciencia, pasar);
        if (!r.ok) return void sinExito(r.motivo, { selector: paso.esperar });
        ev('visto', { paso: nombre }); break;
      }
      case 'esperar_hasta': {
        const t0 = S.t; const tope = paso.max_ms != null ? paso.max_ms : paciencia;
        while (!(await page.evaluate(paso.esperar_hasta)) ) { if (S.t - t0 >= tope) return void (paso.falla_si_no ? fallar(nombre, 'no se cumplió: ' + corto(paso.esperar_hasta, 100)) : sinExito('paciencia', { condicion: corto(paso.esperar_hasta, 80) })); await pasar(100); }
        ev('cumplido', { paso: nombre }); break;
      }
      case 'pasar': await pasar(paso.pasar * ritmo); ev('pausa', { ms: Math.round(paso.pasar * ritmo) }); break;
      case 'interrumpir': await interrumpir(X, paso.interrumpir); break;
      case 'leer': {
        let v = null;
        try { v = await page.evaluate(paso.leer.js); } catch (e) { ev('lectura-fallida', { paso: nombre }); }
        S.datos[paso.leer.id] = v; ev('leido', { id: paso.leer.id }); break;
      }
      case 'verificar': {
        const t0 = S.t; const espera = paso.verificar.espera || 0;
        let ok = await page.evaluate(paso.verificar.js);
        while (!ok && S.t - t0 < espera) { await pasar(100); ok = await page.evaluate(paso.verificar.js); }
        if (!ok) return void fallar(nombre, paso.verificar.mensaje || ('no se cumplió: ' + corto(paso.verificar.js, 100)));
        ev('verificado', { paso: nombre }); break;
      }
      case 'tocar': {
        const r = await apuntar(X, paso.tocar, paciencia, true);
        if (!r.ok) return void sinExito(r.motivo, r.extra);
        await tocarEn(X, r.x, r.y); accion(); ev('toque', { paso: nombre }); break;
      }
      case 'mantener': {
        const r = await apuntar(X, paso.mantener.en, paciencia, false);
        if (!r.ok) return void sinExito(r.motivo, r.extra);
        await presionar(X, r.x, r.y); await pasar(paso.mantener.ms * (paso.mantener.ritmo === false ? 1 : 1)); await soltar(X, r.x, r.y); accion(); ev('mantenido', { paso: nombre, ms: paso.mantener.ms }); break;
      }
      case 'arrastrar': {
        const a = await apuntar(X, paso.arrastrar.desde, paciencia, false);
        if (!a.ok) return void sinExito(a.motivo, a.extra);
        const b = await apuntar(X, paso.arrastrar.hasta, paciencia, false, true);   // el destino se acota a la pantalla
        if (!b.ok) return void sinExito(b.motivo, b.extra);
        const pasosN = paso.arrastrar.pasos || 6;
        await presionar(X, a.x, a.y);
        for (let k = 1; k <= pasosN; k++) { await moverA(X, a.x + (b.x - a.x) * k / pasosN, a.y + (b.y - a.y) * k / pasosN); await pasar(16); }
        await soltar(X, b.x, b.y); accion(); ev('arrastre', { paso: nombre }); break;
      }
      case 'tecla': {
        const v = paso.veces || 1;
        const veces = typeof v === 'object' ? v.min + Math.floor(rng() * (v.max - v.min + 1)) : v;
        for (let k = 0; k < veces; k++) { await teclear(X, paso.tecla); await pasar(60); }
        accion(); ev('tecla', { paso: nombre, tecla: paso.tecla, veces }); break;
      }
      case 'escribir': {
        const r = await apuntar(X, paso.escribir.selector, paciencia, true);
        if (!r.ok) return void sinExito(r.motivo, r.extra);
        await tocarEn(X, r.x, r.y);
        for (const ch of String(paso.escribir.texto)) { await entrada(X, () => page.keyboard.type(ch)); await pasar(70 * ritmo); }
        accion(); ev('escrito', { paso: nombre }); break;
      }
      case 'repetir': {
        const R = paso.repetir; let n = 0;
        while (n < R.maximo && S.estado === 'completo') {
          if (R.hasta && (await page.evaluate(R.hasta))) break;
          for (let k = 0; k < R.pasos.length && S.estado === 'completo'; k++) await unPaso(R.pasos[k], X, id + '.' + (n + 1) + '.' + (k + 1));
          n++;
        }
        ev('repeticion', { paso: nombre, vueltas: n }); break;
      }
      default: return void fallar(nombre, 'paso sin verbo conocido');
    }
    if (S.estado === 'completo') marcar();
  } catch (e) {
    fallar(nombre, e.message || e);
  }
}

async function interrupcionesPendientes(X) {
  const { perfil, S } = X;
  for (const it of perfil.conducta.interrupciones || []) {
    const clave = it.tras_acciones + ':' + it.ms;
    if (S.acciones >= it.tras_acciones && !S.interrumpida.has(clave)) { S.interrumpida.add(clave); await interrumpir(X, it.ms); }
  }
}
// «Cambió de aplicación»: la página queda oculta unos segundos y vuelve (visibilitychange). Un juego bien hecho se pausa y retoma sin perder nada.
async function interrumpir(X, ms) {
  const { page, pasar, ev } = X;
  await page.evaluate(() => { const d = document; Object.defineProperty(d, 'hidden', { configurable: true, get: () => true }); Object.defineProperty(d, 'visibilityState', { configurable: true, get: () => 'hidden' }); d.dispatchEvent(new Event('visibilitychange')); window.dispatchEvent(new Event('blur')); });
  ev('oculta', { ms }); await pasar(ms);
  await page.evaluate(() => { const d = document; delete d.hidden; delete d.visibilityState; d.dispatchEvent(new Event('visibilitychange')); window.dispatchEvent(new Event('focus')); });
  ev('visible');
}

async function esperarListo(page, selector, paciencia, pasar) {
  let t = 0, ultimo = 'no-existe';
  for (;;) {
    const r = await page.evaluate((s) => {
      const el = document.querySelector(s); if (!el) return 'no-existe';
      const rc = el.getBoundingClientRect(); const cs = getComputedStyle(el);
      if (rc.width <= 0 || rc.height <= 0 || cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0') return 'no-visible';
      if (el.disabled || el.getAttribute('aria-disabled') === 'true') return 'deshabilitado';
      return true;
    }, selector);
    if (r === true) return { ok: true };
    ultimo = r;
    if (t >= paciencia) return { ok: false, motivo: ultimo };
    await pasar(100); t += 100;
  }
}

// Convierte «dónde toca la persona» en un punto de la pantalla. spec: un selector, o {selector, x, y (fracciones de la caja), js (devuelve {x,y} en coordenadas de `ref`), ref:[ancho,alto]}.
// La persona tiene mala puntería según su perfil (punteria_px × temblor): si falla un botón chico, lo reintenta una vez y luego se rinde.
async function apuntar(X, spec, paciencia, exigirBlanco, destino) {
  const { page, perfil, rng, pasar, ev } = X;
  const s = typeof spec === 'string' ? { selector: spec } : spec;
  const w = await esperarListo(page, s.selector, paciencia, pasar);
  if (!w.ok) return { ok: false, motivo: w.motivo, extra: { selector: s.selector } };
  let p = null;
  if (s.js) p = await page.evaluate(s.js);
  const sigma = (perfil.conducta.punteria_px || 0) * (perfil.conducta.temblor || 1);
  for (let intento = 0; intento < 2; intento++) {
    const caja = await page.evaluate((a) => {
      const el = document.querySelector(a.selector); if (!el) return null;
      el.scrollIntoView({ block: 'center', inline: 'center' });
      const r = el.getBoundingClientRect();
      let fx = a.x == null ? 0.5 : a.x, fy = a.y == null ? 0.5 : a.y;
      if (a.p) { fx = a.ref ? a.p.x / a.ref[0] : a.p.x; fy = a.ref ? a.p.y / a.ref[1] : a.p.y; }
      return { x: r.left + r.width * fx, y: r.top + r.height * fy, ancho: r.width, alto: r.height, vw: window.innerWidth, vh: window.innerHeight };
    }, { selector: s.selector, x: s.x, y: s.y, p, ref: s.ref });
    if (!caja) return { ok: false, motivo: 'no-existe', extra: { selector: s.selector } };
    let x = caja.x + (sigma ? gauss(rng) * sigma : 0), y = caja.y + (sigma ? gauss(rng) * sigma : 0);
    if (destino) {                                          // un dedo o un ratón no pasan del borde de la pantalla: se queda en el borde
      x = Math.min(Math.max(x, 1), caja.vw - 1); y = Math.min(Math.max(y, 1), caja.vh - 1);
      if (x !== caja.x + 0 && (caja.x < 0 || caja.x > caja.vw || caja.y < 0 || caja.y > caja.vh)) ev('tope-de-pantalla', { selector: s.selector });
      return { ok: true, x, y };
    }
    if (x < 0 || y < 0 || x > caja.vw || y > caja.vh) return { ok: false, motivo: 'fuera-de-pantalla', extra: { selector: s.selector } };
    const golpe = await page.evaluate((a) => {
      const el = document.querySelector(a.selector); const h = document.elementFromPoint(a.x, a.y);
      if (!h) return 'nada';
      if (el === h || el.contains(h) || h.contains(el)) return true;
      return 'cubierto por ' + h.tagName.toLowerCase() + (h.id ? '#' + h.id : '');
    }, { selector: s.selector, x, y });
    if (golpe === true) return { ok: true, x, y };
    const cubierto = String(golpe).indexOf('cubierto') === 0;
    ev(cubierto ? 'cubierto' : 'punteria', { selector: s.selector, detalle: String(golpe) });
    if (cubierto) return { ok: false, motivo: 'cubierto', extra: { selector: s.selector, detalle: String(golpe) } };
    if (!exigirBlanco) return { ok: true, x, y };
    await pasar(400 * perfil.conducta.ritmo);               // falló el toque: lo vuelve a intentar con calma
  }
  return { ok: false, motivo: 'punteria', extra: { selector: s.selector, ancho: null } };
}

// Cada entrada se manda y se ESPERA a que la página la haya procesado (contador window.__lab): así una sesión no depende de qué tan cargada esté la computadora.
const pausaReal = (ms) => new Promise((r) => setTimeout(r, ms));
async function leerContador(page) { return page.evaluate(() => [window.__lab.n, window.__lab.clic]); }
async function esperarContador(page, antes, campo, tope) {
  const t0 = Date.now();
  for (;;) {
    const c = await leerContador(page);
    if (c[campo] > antes[campo]) return true;
    if (Date.now() - t0 > tope) return false;                       // la página no escuchó nada (p. ej. un evento cancelado): no se cuelga
    await pausaReal(3);
  }
}
async function entrada(X, enviar, campo, tope) {
  const antes = await leerContador(X.page);
  await enviar();
  return esperarContador(X.page, antes, campo || 0, tope || 1500);
}
async function tocarEn(X, x, y) {
  const { page, cdp, perfil, pasar } = X;
  if (perfil.dispositivo.tactil) {
    await entrada(X, () => cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] }));
    await pasar(70);
    const antes = await leerContador(page);
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await esperarContador(page, antes, 0, 1500);
    await esperarContador(page, antes, 1, 400);                     // el toque se vuelve clic un instante después
  } else {
    await entrada(X, async () => { await page.mouse.move(x, y); await page.mouse.down(); });
    await pasar(60);
    await entrada(X, () => page.mouse.up());
  }
}
async function presionar(X, x, y) { const { page, cdp, perfil } = X; await entrada(X, async () => { if (perfil.dispositivo.tactil) await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] }); else { await page.mouse.move(x, y); await page.mouse.down(); } }); }
async function moverA(X, x, y) { const { page, cdp, perfil } = X; await entrada(X, async () => { if (perfil.dispositivo.tactil) await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x, y }] }); else await page.mouse.move(x, y); }); }
async function soltar(X, x, y) { const { page, cdp, perfil } = X; await entrada(X, async () => { if (perfil.dispositivo.tactil) await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }); else await page.mouse.up(); }); }
async function teclear(X, tecla) { await entrada(X, () => X.page.keyboard.press(tecla)); }

// ---------- la prueba «bots»: las políticas de la plantilla juegan episodios enteros dentro de la página, con el temple de este perfil ----------
async function celdaBots(browser, cell) {
  const perfil = cell.perfil, variante = variantes[cell.variante], P = cell.prueba;
  const def = require(path.resolve(P.bots_js));
  const { ctx, page, reg } = await contextoAislado(browser, cell, perfil, variante, { reloj: false });
  const salida = { cell: { variante: cell.variante, perfil: perfil.id, prueba: P.id, semilla: 0, repeticion: false }, tipo: 'bots',
    config: { descripcion: def.descripcion || '', base: def.base || null, solucionador: def.solucionador || null, humano: def.humano || null,
      escenas: (def.escenas && def.escenas.length ? def.escenas : [{ nombre: 'unica' }]).map((e) => e.nombre), partidas: def.partidas || {}, semilla_base: P.semilla_base, factor: P.factor },
    episodios: [], deterministas: [], errores_de_pagina: [], a11y: [], aislado: true, medido: {} };
  const limpiar = (x) => { const y = Object.assign({}, x); delete y.ms_reales; return JSON.stringify(y); };
  try {
    await page.goto('http://127.0.0.1:' + plan.puerto + '/v/' + encodeURIComponent(cell.variante) + '/index.html' + construirConsulta(variante.consulta, 'bot=1'), { waitUntil: 'load', timeout: 30000 });
    await page.waitForFunction(() => !!window.__bot, null, { timeout: 15000 });
    salida.aislado = await page.evaluate(() => { try { return localStorage.length === 0 && sessionStorage.length === 0; } catch (e) { return true; } });
    if (def.preludio) await page.evaluate('(() => {' + def.preludio + '})()');
    const temblor = perfil.conducta.temblor, ritmo = perfil.conducta.ritmo;
    const escenas = def.escenas && def.escenas.length ? def.escenas : [{ nombre: 'unica', opciones: {} }];
    for (const nombre of Object.keys(def.politicas)) {
      if (P.politicas && P.politicas.indexOf(nombre) < 0) continue;
      const n = Math.max(1, Math.round(((def.partidas && def.partidas[nombre]) || 10) * (P.factor || 1)));
      const fuente = def.politicas[nombre].toString();
      for (const escena of escenas) {
        const base = Object.assign({}, def.episodio || {}, escena.opciones || {});
        // El temple es de la persona simulada: solo la política HUMANA actúa más lento (dt × ritmo) y más temblorosa. La débil y la solucionadora miden el juego
        // (¿se gana a ciegas?, ¿se puede ganar?) y no deben cambiar de cadencia según el perfil: una solucionadora que solo gana a cierto ritmo falsearía «imposible».
        const dt = (base.dt || 50) * (nombre === def.humano ? ritmo : 1);
        const opciones = Object.assign({}, base, { dt, perfil: { temblor, ritmo, id: perfil.id } });
        let primero = null;
        for (let i = 0; i < n; i++) {
          const r = await page.evaluate(([f, s, o]) => window.__bot.correr(f, s, o), [fuente, P.semilla_base + i, opciones]);
          if (i === 0) primero = r;
          salida.episodios.push(Object.assign({ politica: nombre, escena: escena.nombre }, r));
        }
        const otra = await page.evaluate(([f, s, o]) => window.__bot.correr(f, s, o), [fuente, P.semilla_base, opciones]);
        salida.deterministas.push({ politica: nombre, escena: escena.nombre, ok: limpiar(primero) === limpiar(otra) });
      }
    }
  } catch (e) {
    salida.errores_de_pagina.push('laboratorio: ' + corto(e.message || e, 200));
  }
  salida.errores_de_pagina = salida.errores_de_pagina.concat(reg.pagina.map((x) => 'pageerror: ' + x), reg.consola.map((x) => 'consola: ' + x));
  for (const k of ['pagina', 'consola', 'red', 'bloqueadas']) reg[k].sort();
  salida.errores = { pagina: reg.pagina, consola: reg.consola, red: reg.red, bloqueadas: reg.bloqueadas };
  await ctx.close();
  return salida;
}

async function conTope(promesa, ms, etiqueta) {
  let t;
  const tope = new Promise((_, rej) => { t = setTimeout(() => rej(new Error('tiempo agotado (' + Math.round(ms / 1000) + ' s reales) en ' + etiqueta)), ms); });
  try { return await Promise.race([promesa, tope]); } finally { clearTimeout(t); }
}

(async () => {
  await new Promise((ok) => servidor.listen(0, '127.0.0.1', ok));
  plan.puerto = servidor.address().port;
  const browser = await chromium.launch();
  const resultados = new Array(plan.celdas.length);
  let siguiente = 0;
  const trabajador = async () => {
    for (;;) {
      const i = siguiente++;
      if (i >= plan.celdas.length) return;
      const cell = plan.celdas[i];
      const etiqueta = [cell.variante, cell.perfil.id, cell.prueba.id, cell.semilla].join('/');
      try {
        resultados[i] = await conTope(cell.prueba.tipo === 'bots' ? celdaBots(browser, cell) : sesion(browser, cell), TOPE_CELDA_MS, etiqueta);
      } catch (e) {
        resultados[i] = { cell: { variante: cell.variante, perfil: cell.perfil.id, prueba: cell.prueba.id, semilla: cell.semilla, repeticion: !!cell.repeticion }, tipo: cell.prueba.tipo, estado: 'falla',
          falla: { paso: 'interno', mensaje: corto(e.message || e, 200) }, abandono: null, embudo: [], datos: {}, errores: { pagina: [], consola: [], red: [], bloqueadas: [] }, a11y: [], aislado: true, traza: 'error', eventos: [], medido: {}, episodios: [], deterministas: [], errores_de_pagina: [] };
      }
    }
  };
  await Promise.all(Array.from({ length: Math.max(1, Math.min(plan.concurrencia || 4, plan.celdas.length)) }, trabajador));
  await browser.close();
  servidor.close();
  fs.writeFileSync(salidaRuta, JSON.stringify({ celdas: resultados }));
})().catch((e) => { console.error('FALLO GENERAL', e); process.exit(1); });
