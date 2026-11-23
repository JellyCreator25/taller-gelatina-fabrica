#!/usr/bin/env node
// Ilustraciones de caricatura para las publicaciones: nuestros personajes (los mismos sprites del juego) en escena, sobre fondos y efectos dibujados en SVG.
// Sin texto escrito (salvo cifras en una etiqueta de precio), así una misma imagen sirve en español, inglés y chino.
//   node herramientas/ilustraciones.js                 → dibuja todas las escenas a contenido/imagenes/ilustracion-<id>.png
//   node herramientas/ilustraciones.js id [id ...]     → solo esas
//   node herramientas/ilustraciones.js --lista         → ids y texto alternativo
//   node herramientas/ilustraciones.js --salida DIR    → escribir en otra carpeta (muestras)
//   node herramientas/ilustraciones.js --verificar     → revisa las escenas sin abrir navegador (personajes que existen, sin texto escrito, alt en es y en)
// Cada escena es una función que devuelve capas de atrás hacia adelante: texto SVG (fondos, efectos, atrezo) o un personaje S(tipo, equipo, x, y, radio, opciones).
const fs = require('fs');
const path = require('path');
const { dibujarSprites, tipografias } = require('./arte.js');
const L = require('./ilustraciones/lib.js');

const RAIZ = path.resolve(__dirname, '..');
const JUEGO = path.join(RAIZ, 'salida', 'guerreros-gelatina', 'index.html');
const ANCHO = 1200, ALTO = 675, RADIO_SPRITE = 160, DENSIDAD = 2;
const ESTILO = 1;   // versión del estilo (ver motor/ILUSTRACIONES.md): sube cuando el arte cambia de nivel
const PERSONAJES = ['campesino', 'arquero', 'caballero', 'bruja', 'pollo', 'gigante', 'rana', 'zeus', 'medusa', 'anubis', 'hercules', 'merlin', 'robin', 'llorona', 'dracula'];

// Un personaje en la escena. (x, y) es el centro de su cuerpo; r, su radio en píxeles; el resto son retoques.
function S(tipo, equipo, x, y, r, o = {}) { return Object.assign({ sprite: true, tipo, equipo, x, y, r, dir: 1, golpe: 0, rot: 0, filtro: '', alfa: 1, extra: null, sombra: true, contorno: true }, o); }
const claveSprite = (c) => [c.tipo, c.equipo, c.dir, c.golpe, JSON.stringify(c.extra || null)].join('|');

function aplanar(capas) { return capas.flat(Infinity).filter(Boolean); }

function html(capas, sprites, tipos) {
  let cuerpo = '', pend = []; const defs = new Set();
  const vaciar = () => { if (pend.length) { cuerpo += '<svg viewBox="0 0 ' + ANCHO + ' ' + ALTO + '" width="' + ANCHO + '" height="' + ALTO + '" xmlns="http://www.w3.org/2000/svg">' + pend.join('') + '</svg>'; pend = []; } };
  const { lado, centroY, urls } = sprites;
  for (const c of capas) {
    if (typeof c === 'string') { pend.push(c); continue; }
    if (c.sombra) pend.push(L.sombra(c.x + (c.sombraDx || 0), c.sombraY != null ? c.sombraY : c.y + c.r * 0.86, c.r * 1.05));
    vaciar();
    const k = c.r / RADIO_SPRITE, w = lado * k, ox = w / 2, oy = w * centroY;
    const borde = Math.max(3, Math.round(c.r * 0.042));
    defs.add(borde);
    const filtros = [c.filtro, c.contorno ? 'url(#cont' + borde + ')' : ''].filter(Boolean).join(' ');
    cuerpo += '<img src="' + urls[tipos.get(claveSprite(c))] + '" style="position:absolute;left:' + (c.x - ox).toFixed(1) + 'px;top:' + (c.y - oy).toFixed(1) + 'px;width:' + w.toFixed(1) + 'px;height:' + w.toFixed(1) + 'px;transform-origin:' + ox.toFixed(1) + 'px ' + oy.toFixed(1) + 'px;transform:rotate(' + c.rot + 'deg);opacity:' + c.alfa + ';filter:' + filtros + '">';
  }
  vaciar();
  const filtrosSvg = '<svg width="0" height="0" style="position:absolute"><defs>' + [...defs].map((b) => '<filter id="cont' + b + '" x="-15%" y="-15%" width="130%" height="130%" color-interpolation-filters="sRGB"><feComponentTransfer in="SourceAlpha" result="solido"><feFuncA type="discrete" tableValues="0 0 0 0 1"/></feComponentTransfer><feMorphology in="solido" operator="dilate" radius="' + b + '" result="gordo"/><feFlood flood-color="' + L.O + '"/><feComposite in2="gordo" operator="in" result="borde"/><feMerge><feMergeNode in="borde"/><feMergeNode in="SourceGraphic"/></feMerge></filter>').join('') + '</defs></svg>';
  return '<!doctype html><meta charset="utf-8"><style>' + tipografias(RAIZ) + 'html,body{margin:0;background:#fff}#l{position:relative;width:' + ANCHO + 'px;height:' + ALTO + 'px;overflow:hidden}#l svg{position:absolute;left:0;top:0}</style><div id="l">' + filtrosSvg + cuerpo + '</div>';
}

async function dibujar(browser, ids, escenas, salida) {
  const hechas = [];
  const plan = ids.map((id) => ({ id, capas: aplanar(escenas[id].hacer(S, L)) }));
  const claves = new Map(), lista = [];
  for (const { capas } of plan) for (const c of capas) if (typeof c !== 'string' && !claves.has(claveSprite(c))) { claves.set(claveSprite(c), lista.length); lista.push({ tipo: c.tipo, equipo: c.equipo, dir: c.dir, golpe: c.golpe, extra: c.extra }); }
  const sprites = await dibujarSprites(browser, JUEGO, lista, { radio: RADIO_SPRITE, densidad: DENSIDAD });
  for (const { id, capas } of plan) {
    const ctx = await browser.newContext({ viewport: { width: ANCHO, height: ALTO }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    await page.setContent(html(capas, sprites, claves), { waitUntil: 'load' });
    await page.evaluate(() => Promise.all([...document.images].map((i) => i.decode()).concat(document.fonts.ready)));
    const destino = path.join(salida, 'ilustracion-' + id + '.png');
    await page.locator('#l').screenshot({ path: destino });
    await ctx.close();
    hechas.push(destino);
  }
  return hechas;
}

// Revisión sin navegador: cada escena arma sus capas, usa personajes que existen, no escribe texto (salvo cifras) y trae su alt en español e inglés.
function verificar(escenas) {
  const problemas = [];
  for (const [id, e] of Object.entries(escenas)) {
    if (!/^[a-z0-9-]{1,50}$/.test(id)) problemas.push(id + ': el id debe ser minúsculas, números y guiones');
    for (const idioma of ['es', 'en']) if (!e.alt || !String(e.alt[idioma] || '').trim()) problemas.push(id + ': falta el alt en «' + idioma + '»');
    if (e.alt && !/^Ilustración de caricatura/.test(e.alt.es || '')) problemas.push(id + ': el alt en español debe empezar con «Ilustración de caricatura»');
    if (e.alt && !/^Cartoon illustration/.test(e.alt.en || '')) problemas.push(id + ': el alt en inglés debe empezar con «Cartoon illustration»');
    let capas;
    try { capas = aplanar(e.hacer(S, L)); } catch (err) { problemas.push(id + ': no arma sus capas (' + err.message + ')'); continue; }
    if (!capas.length) problemas.push(id + ': no tiene capas');
    for (const c of capas) {
      if (typeof c === 'string') {
        for (const m of c.matchAll(/<text[^>]*>([^<]*)<\/text>/g)) if (!/^[-+0-9%.,$ ]+$/.test(m[1])) problemas.push(id + ': escribe texto en la imagen («' + m[1] + '»): solo se permiten cifras');
        if (/NaN|undefined/.test(c)) problemas.push(id + ': hay NaN o undefined en un dibujo');
      } else {
        if (!PERSONAJES.includes(c.tipo)) problemas.push(id + ': personaje desconocido «' + c.tipo + '»');
        if (![0, 1].includes(c.equipo)) problemas.push(id + ': equipo inválido en ' + c.tipo);
        for (const k of ['x', 'y', 'r']) if (!Number.isFinite(c[k])) problemas.push(id + ': ' + c.tipo + ' tiene «' + k + '» inválido');
      }
    }
  }
  return problemas;
}

async function main() {
  const argv = process.argv.slice(2);
  const escenas = require('./ilustraciones/escenas.js');
  if (argv.includes('--verificar')) { const p = verificar(escenas); if (p.length) { console.error(p.join('\n')); process.exit(1); } console.log('ok: ' + Object.keys(escenas).length + ' escenas (estilo ' + ESTILO + ')'); return; }
  if (argv.includes('--lista')) { for (const [id, e] of Object.entries(escenas)) console.log(id + '\t' + e.alt); return; }
  let salida = path.join(RAIZ, 'contenido', 'imagenes');
  const i = argv.indexOf('--salida'); if (i >= 0) { salida = path.resolve(argv[i + 1]); argv.splice(i, 2); }
  const ids = argv.length ? argv : Object.keys(escenas);
  for (const id of ids) if (!escenas[id]) { console.error('no existe la escena «' + id + '»'); process.exit(2); }
  fs.mkdirSync(salida, { recursive: true });
  const { chromium } = require('playwright');
  const browser = await chromium.launch();
  try { for (const f of await dibujar(browser, ids, escenas, salida)) console.log(path.relative(RAIZ, f) + '  ' + Math.round(fs.statSync(f).size / 1024) + ' KB'); }
  finally { await browser.close(); }
}
if (require.main === module) main().catch((e) => { console.error(e); process.exit(1); });
module.exports = { S, dibujar, verificar, ESTILO, PERSONAJES };
