// Piezas para componer ilustraciones de caricatura (fondos, efectos y atrezo) en SVG, con el mismo trazo grueso y oscuro de la marca nueva.
// Todo devuelve texto SVG para un lienzo de 1200×675; nada lleva texto escrito (salvo cifras en una etiqueta de precio), así una misma imagen sirve en español, inglés y chino.
// El azar sale de una semilla: la misma escena da siempre la misma imagen.
const O = '#14251b';   // el trazo oscuro de la marca
const C = { rosa: '#ef4f93', amarillo: '#ffd95e', oro: '#f7b21b', verde: '#46c68d', azul: '#2f6fe0', rojo: '#e24a33', morado: '#6d3fb8', marino: '#171c5c', crema: '#fff6e0', piel: '#ffd9b0' };
const n1 = (v) => (Math.round(v * 10) / 10).toString();
function azar(semilla) { let s = (semilla >>> 0) || 1; return () => (s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296; }
let _id = 0; const uid = (p) => p + (++_id);
const grosor = (w) => ' stroke="' + O + '" stroke-width="' + w + '" stroke-linejoin="round" stroke-linecap="round"';

// ---------- efectos ----------
function impacto(x, y, r, { c1 = C.amarillo, c2 = '#fff', puntas = 11, giro = 0, semilla = 1, trazo = 7 } = {}) {
  const A = azar(semilla), pts = [], pts2 = [];
  for (let i = 0; i < puntas * 2; i++) {
    const a = giro + (i / (puntas * 2)) * Math.PI * 2, rr = i % 2 === 0 ? r * (0.9 + A() * 0.2) : r * (0.5 + A() * 0.08);
    pts.push(n1(x + Math.cos(a) * rr) + ',' + n1(y + Math.sin(a) * rr)); pts2.push(n1(x + Math.cos(a) * rr * 0.62) + ',' + n1(y + Math.sin(a) * rr * 0.62));
  }
  return '<polygon points="' + pts.join(' ') + '" fill="' + c1 + '"' + grosor(trazo) + '/><polygon points="' + pts2.join(' ') + '" fill="' + c2 + '" opacity=".92"/>';
}
function lineas(x, y, r0, r1, n, { c = '#fff', w = 5, semilla = 2, desde = 0, hasta = Math.PI * 2, alfa = 0.9 } = {}) {
  const A = azar(semilla); let s = '';
  for (let i = 0; i < n; i++) {
    const a = desde + (hasta - desde) * (i + A() * 0.6) / n, a0 = r0 * (0.9 + A() * 0.3), a1 = r1 * (0.75 + A() * 0.4);
    s += '<line x1="' + n1(x + Math.cos(a) * a0) + '" y1="' + n1(y + Math.sin(a) * a0) + '" x2="' + n1(x + Math.cos(a) * a1) + '" y2="' + n1(y + Math.sin(a) * a1) + '" stroke="' + c + '" stroke-width="' + n1(w * (0.6 + A() * 0.8)) + '" stroke-linecap="round" opacity="' + alfa + '"/>';
  }
  return s;
}
function nube(x, y, r, { c = '#fff', semilla = 4, n = 7, trazo = 6, alfa = 1 } = {}) {   // polvo / humo: círculos que se funden en una sola silueta con contorno
  const A = azar(semilla), cs = [];
  for (let i = 0; i < n; i++) { const a = (i / n) * Math.PI * 2 + A() * 0.5; cs.push([x + Math.cos(a) * r * 0.62 * (0.6 + A() * 0.5), y + Math.sin(a) * r * 0.5 * (0.6 + A() * 0.5), r * (0.34 + A() * 0.18)]); }
  cs.push([x, y, r * 0.5]);
  const g = (extra) => cs.map(([cx, cy, cr]) => '<circle cx="' + n1(cx) + '" cy="' + n1(cy) + '" r="' + n1(cr) + '" fill="' + c + '"' + extra + '/>').join('');
  return '<g opacity="' + alfa + '">' + g(grosor(trazo * 2).replace('stroke-width="' + trazo * 2 + '"', 'stroke-width="' + trazo * 2 + '"')) + g('') + '</g>';
}
function rayo(x0, y0, x1, y1, { ancho = 34, c = '#ffe14a', semilla = 3, tramos = 5, quiebre = 0.16 } = {}) {
  const A = azar(semilla), dx = x1 - x0, dy = y1 - y0, L = Math.hypot(dx, dy), nx = -dy / L, ny = dx / L, pts = [[x0, y0]];
  for (let i = 1; i < tramos; i++) { const t = i / tramos, o = (i % 2 ? 1 : -1) * L * quiebre * (0.6 + A() * 0.7); pts.push([x0 + dx * t + nx * o, y0 + dy * t + ny * o]); }
  pts.push([x1, y1]);
  const d = pts.map((p, i) => (i ? 'L' : 'M') + n1(p[0]) + ' ' + n1(p[1])).join(' ');
  return '<path d="' + d + '" fill="none" stroke="' + O + '" stroke-width="' + (ancho + 14) + '" stroke-linejoin="miter" stroke-linecap="round"/><path d="' + d + '" fill="none" stroke="' + c + '" stroke-width="' + ancho + '" stroke-linejoin="miter" stroke-linecap="round"/><path d="' + d + '" fill="none" stroke="#fff" stroke-width="' + n1(ancho * 0.32) + '" stroke-linejoin="miter" stroke-linecap="round"/>';
}
function ondas(x, y, rx, ry, n, { c = '#fff', w = 8, paso = 0.28, alfa = 0.95 } = {}) {
  let s = '';
  for (let i = 0; i < n; i++) { const k = 1 + i * paso; s += '<ellipse cx="' + x + '" cy="' + y + '" rx="' + n1(rx * k) + '" ry="' + n1(ry * k) + '" fill="none" stroke="' + c + '" stroke-width="' + n1(w * (1 - i * 0.12)) + '" opacity="' + n1(alfa - i * 0.2) + '"/>'; }
  return s;
}
function destello(x, y, s, { c = '#fff', trazo = 0 } = {}) {
  const d = 'M' + x + ' ' + (y - s) + ' Q' + x + ' ' + y + ' ' + (x + s) + ' ' + y + ' Q' + x + ' ' + y + ' ' + x + ' ' + (y + s) + ' Q' + x + ' ' + y + ' ' + (x - s) + ' ' + y + ' Q' + x + ' ' + y + ' ' + x + ' ' + (y - s) + 'Z';
  return '<path d="' + d + '" fill="' + c + '"' + (trazo ? grosor(trazo) : '') + '/>';
}
function destellos(lista, o) { return lista.map(([x, y, s, c]) => destello(x, y, s, Object.assign({}, o, c ? { c } : {}))).join(''); }
function corazon(x, y, s, { c = C.rosa } = {}) {
  return '<path d="M' + x + ' ' + n1(y + s * 0.9) + ' C' + n1(x - s * 1.6) + ' ' + n1(y - s * 0.2) + ' ' + n1(x - s * 0.7) + ' ' + n1(y - s * 1.2) + ' ' + x + ' ' + n1(y - s * 0.4) + ' C' + n1(x + s * 0.7) + ' ' + n1(y - s * 1.2) + ' ' + n1(x + s * 1.6) + ' ' + n1(y - s * 0.2) + ' ' + x + ' ' + n1(y + s * 0.9) + 'Z" fill="' + c + '"' + grosor(Math.max(3, s * 0.18)) + '/>';
}
function gota(x, y, s) { return '<path d="M' + x + ' ' + n1(y - s) + ' C' + n1(x + s * 0.9) + ' ' + n1(y + s * 0.1) + ' ' + n1(x + s * 0.7) + ' ' + n1(y + s) + ' ' + x + ' ' + n1(y + s) + ' C' + n1(x - s * 0.7) + ' ' + n1(y + s) + ' ' + n1(x - s * 0.9) + ' ' + n1(y + s * 0.1) + ' ' + x + ' ' + n1(y - s) + 'Z" fill="#9fdcff"' + grosor(Math.max(3, s * 0.2)) + '/>'; }
function signo(x, y, tipo, s, { c = C.amarillo } = {}) {   // globito con ! o ? dibujado (no es texto: es forma)
  const burbuja = '<ellipse cx="' + x + '" cy="' + y + '" rx="' + n1(s * 0.85) + '" ry="' + n1(s * 0.8) + '" fill="#fff"' + grosor(Math.max(4, s * 0.14)) + '/><path d="M' + n1(x - s * 0.2) + ' ' + n1(y + s * 0.7) + ' L' + n1(x - s * 0.5) + ' ' + n1(y + s * 1.2) + ' L' + n1(x + s * 0.15) + ' ' + n1(y + s * 0.74) + 'Z" fill="#fff"' + grosor(Math.max(4, s * 0.14)) + '/><ellipse cx="' + x + '" cy="' + y + '" rx="' + n1(s * 0.8) + '" ry="' + n1(s * 0.74) + '" fill="#fff"/>';
  if (tipo === '!') return burbuja + '<rect x="' + n1(x - s * 0.11) + '" y="' + n1(y - s * 0.52) + '" width="' + n1(s * 0.22) + '" height="' + n1(s * 0.66) + '" rx="' + n1(s * 0.11) + '" fill="' + C.rojo + '"/><circle cx="' + x + '" cy="' + n1(y + s * 0.38) + '" r="' + n1(s * 0.14) + '" fill="' + C.rojo + '"/>';
  return burbuja + '<path d="M' + n1(x - s * 0.3) + ' ' + n1(y - s * 0.3) + ' Q' + n1(x - s * 0.3) + ' ' + n1(y - s * 0.62) + ' ' + x + ' ' + n1(y - s * 0.62) + ' Q' + n1(x + s * 0.34) + ' ' + n1(y - s * 0.62) + ' ' + n1(x + s * 0.34) + ' ' + n1(y - s * 0.28) + ' Q' + n1(x + s * 0.34) + ' ' + n1(y - s * 0.06) + ' ' + x + ' ' + n1(y + s * 0.1) + ' L' + x + ' ' + n1(y + s * 0.2) + '" fill="none" stroke="' + C.morado + '" stroke-width="' + n1(s * 0.2) + '" stroke-linecap="round"/><circle cx="' + x + '" cy="' + n1(y + s * 0.46) + '" r="' + n1(s * 0.12) + '" fill="' + C.morado + '"/>';
}
function grietas(x, y, r, { semilla = 6, c = O } = {}) {
  const A = azar(semilla); let s = '';
  for (let i = 0; i < 7; i++) {
    const a = (i / 7) * Math.PI * 2 + A() * 0.4; let px = x, py = y, d = 'M' + x + ' ' + y;
    for (let k = 0; k < 3; k++) { const aa = a + (A() - 0.5) * 0.7, l = r * (0.28 + A() * 0.22); px += Math.cos(aa) * l; py += Math.sin(aa) * l * 0.5; d += ' L' + n1(px) + ' ' + n1(py); }
    s += '<path d="' + d + '" fill="none" stroke="' + c + '" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>';
  }
  return s;
}
function llamas(x, y, r, { c1 = '#ff6a2b', c2 = '#ffd95e', semilla = 8 } = {}) {   // aura de furia
  const A = azar(semilla); let s1 = '', s2 = '';
  for (let i = 0; i < 9; i++) {
    const a = Math.PI + (i / 8) * Math.PI, h = r * (0.35 + A() * 0.4), cx = x + Math.cos(a) * r, cy = y + Math.sin(a) * r * 0.9;
    const p = (k) => 'M' + n1(cx - 26 * k) + ' ' + n1(cy + 18) + ' Q' + n1(cx - 12 * k) + ' ' + n1(cy - h * 0.5 * k) + ' ' + n1(cx + (A() - 0.5) * 22) + ' ' + n1(cy - h * k) + ' Q' + n1(cx + 14 * k) + ' ' + n1(cy - h * 0.4 * k) + ' ' + n1(cx + 26 * k) + ' ' + n1(cy + 18) + 'Z';
    s1 += '<path d="' + p(1) + '" fill="' + c1 + '"' + grosor(6) + '/>'; s2 += '<path d="' + p(0.55) + '" fill="' + c2 + '"/>';
  }
  return s1 + s2;
}
function flecha(x0, y0, x1, y1, { c = '#8a5a2b', pluma = C.rojo, w = 7 } = {}) {
  const a = Math.atan2(y1 - y0, x1 - x0), ux = Math.cos(a), uy = Math.sin(a), px = -uy, py = ux;
  const punta = 'M' + x1 + ' ' + y1 + ' L' + n1(x1 - ux * 26 + px * 12) + ' ' + n1(y1 - uy * 26 + py * 12) + ' L' + n1(x1 - ux * 26 - px * 12) + ' ' + n1(y1 - uy * 26 - py * 12) + 'Z';
  const pl = (k) => 'M' + n1(x0 + ux * k) + ' ' + n1(y0 + uy * k) + ' l' + n1(-ux * 16 + px * 12) + ' ' + n1(-uy * 16 + py * 12) + ' M' + n1(x0 + ux * k) + ' ' + n1(y0 + uy * k) + ' l' + n1(-ux * 16 - px * 12) + ' ' + n1(-uy * 16 - py * 12);
  return '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x1 + '" y2="' + y1 + '" stroke="' + O + '" stroke-width="' + (w + 7) + '" stroke-linecap="round"/><line x1="' + x0 + '" y1="' + y0 + '" x2="' + x1 + '" y2="' + y1 + '" stroke="' + c + '" stroke-width="' + w + '" stroke-linecap="round"/>' +
    '<path d="' + punta + '" fill="#d7dde3"' + grosor(5) + '/><path d="' + pl(6) + pl(20) + '" fill="none" stroke="' + pluma + '" stroke-width="7" stroke-linecap="round"/>';
}
function diana(x, y, r) {
  return [[r, '#fff'], [r * 0.72, C.rojo], [r * 0.46, '#fff'], [r * 0.2, C.rojo]].map(([rr, c], i) => '<circle cx="' + x + '" cy="' + y + '" r="' + n1(rr) + '" fill="' + c + '"' + (i === 0 ? grosor(7) : '') + '/>').join('');
}
function confeti(n, { semilla = 9, x0 = 0, x1 = 1200, y0 = 0, y1 = 675, tam = 16 } = {}) {
  const A = azar(semilla), cols = [C.rosa, C.amarillo, C.verde, '#6fc4ff', '#fff', C.oro]; let s = '';
  for (let i = 0; i < n; i++) { const x = x0 + A() * (x1 - x0), y = y0 + A() * (y1 - y0), w = tam * (0.6 + A() * 0.8), h = w * (0.35 + A() * 0.3); s += '<rect x="' + n1(x) + '" y="' + n1(y) + '" width="' + n1(w) + '" height="' + n1(h) + '" rx="2" fill="' + cols[(A() * cols.length) | 0] + '" transform="rotate(' + n1(A() * 360) + ' ' + n1(x) + ' ' + n1(y) + ')"/>'; }
  return s;
}
function foco(xTop, yTop, xBase, yBase, ancho, { alfa = 0.2, c = '#fff6c9' } = {}) {   // haz de reflector
  const id = uid('foco');
  return '<defs><linearGradient id="' + id + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + c + '" stop-opacity="' + (alfa + 0.18) + '"/><stop offset="1" stop-color="' + c + '" stop-opacity="' + alfa * 0.4 + '"/></linearGradient></defs><polygon points="' + n1(xTop - 14) + ',' + yTop + ' ' + n1(xTop + 14) + ',' + yTop + ' ' + n1(xBase + ancho) + ',' + yBase + ' ' + n1(xBase - ancho) + ',' + yBase + '" fill="url(#' + id + ')"/><ellipse cx="' + xBase + '" cy="' + yBase + '" rx="' + ancho + '" ry="' + n1(ancho * 0.22) + '" fill="' + c + '" opacity="' + n1(alfa + 0.15) + '"/>';
}
function sombra(x, y, rx, { ry, alfa = 0.28 } = {}) { return '<ellipse cx="' + x + '" cy="' + y + '" rx="' + rx + '" ry="' + n1(ry || rx * 0.3) + '" fill="rgba(8,16,40,' + alfa + ')"/>'; }

// ---------- atrezo ----------
function trofeo(x, y, s, { c = C.oro } = {}) {   // copa dorada con una gelatina en lo alto (y x,y = base)
  const k = s / 100;
  return '<g transform="translate(' + x + ' ' + y + ') scale(' + k + ')">' +
    '<rect x="-46" y="-26" width="92" height="26" rx="6" fill="#8a4b12"' + grosor(6) + '/><rect x="-30" y="-52" width="60" height="30" rx="5" fill="' + c + '"' + grosor(6) + '/>' +
    '<path d="M-52 -150 C-84 -150 -88 -96 -42 -88" fill="none"' + grosor(11).replace(O, O) + '/><path d="M52 -150 C84 -150 88 -96 42 -88" fill="none"' + grosor(11) + '/>' +
    '<path d="M-52 -150 C-84 -150 -88 -96 -42 -88" fill="none" stroke="' + c + '" stroke-width="5"/><path d="M52 -150 C84 -150 88 -96 42 -88" fill="none" stroke="' + c + '" stroke-width="5"/>' +
    '<path d="M-56 -158 L56 -158 C56 -96 34 -58 0 -54 C-34 -58 -56 -96 -56 -158Z" fill="' + c + '"' + grosor(7) + '/><path d="M-36 -146 C-36 -108 -26 -84 -14 -72" fill="none" stroke="#fff" stroke-width="8" stroke-linecap="round" opacity=".7"/>' +
    '<path d="M-26 -158 C-28 -196 -14 -214 0 -214 C14 -214 28 -196 26 -158Z" fill="#7de3b1"' + grosor(6) + '/><circle cx="-9" cy="-184" r="3.2" fill="' + O + '"/><circle cx="9" cy="-184" r="3.2" fill="' + O + '"/></g>';
}
function carrito(x, y, s) {   // x,y = centro de la base
  const k = s / 100;
  const rej = [-40, -20, 0, 20, 40].map((v) => '<line x1="' + v + '" y1="-98" x2="' + n1(v * 0.8) + '" y2="-36" stroke="' + O + '" stroke-width="4"/>').join('') + [-76, -56, -36].map((v) => '<line x1="-52" y1="' + v + '" x2="52" y2="' + v + '" stroke="' + O + '" stroke-width="4"/>').join('');
  return '<g transform="translate(' + x + ' ' + y + ') scale(' + k + ')"><path d="M-86 -126 L-62 -126 L-48 -98" fill="none"' + grosor(9) + '/><path d="M-56 -102 L56 -102 L44 -30 L-44 -30Z" fill="#dfe6ee"' + grosor(7) + '/>' + rej +
    '<circle cx="-28" cy="-6" r="14" fill="#2b2f3a"' + grosor(5) + '/><circle cx="30" cy="-6" r="14" fill="#2b2f3a"' + grosor(5) + '/></g>';
}
function etiqueta(x, y, texto, s, { c = C.rojo, giro = -8 } = {}) {   // etiqueta de precio con cifras (las cifras son iguales en todos los idiomas)
  const k = s / 100;
  return '<g transform="translate(' + x + ' ' + y + ') rotate(' + giro + ') scale(' + k + ')"><path d="M-150 0 L-110 -62 L150 -62 L150 62 L-110 62Z" fill="' + c + '"' + grosor(9) + '/><circle cx="-118" cy="0" r="9" fill="#fff"' + grosor(5) + '/>' +
    '<text x="28" y="26" text-anchor="middle" font-family="Fredoka, sans-serif" font-weight="700" font-size="82" fill="#fff" stroke="' + O + '" stroke-width="9" paint-order="stroke" stroke-linejoin="round">' + texto + '</text></g>';
}
function microfono(x, y, s) {
  const k = s / 100;
  return '<g transform="translate(' + x + ' ' + y + ') scale(' + k + ')"><ellipse cx="0" cy="0" rx="40" ry="11" fill="#2b2f3a"' + grosor(6) + '/><line x1="0" y1="0" x2="0" y2="-150" stroke="' + O + '" stroke-width="14" stroke-linecap="round"/><line x1="0" y1="0" x2="0" y2="-150" stroke="#9aa6b2" stroke-width="6" stroke-linecap="round"/>' +
    '<rect x="-17" y="-205" width="34" height="62" rx="17" fill="#c7d0da"' + grosor(6) + '/><path d="M-17 -182 L17 -182 M-17 -168 L17 -168" stroke="' + O + '" stroke-width="3"/></g>';
}
function mesa(x, y, ancho, { c = '#b97a3e' } = {}) {   // mesa de juntas vista de frente: x,y = centro del tablero
  const a = ancho / 2;
  return '<rect x="' + n1(x - a * 0.78) + '" y="' + n1(y + 12) + '" width="26" height="150" fill="#7a4a22"' + grosor(6) + '/><rect x="' + n1(x + a * 0.78 - 26) + '" y="' + n1(y + 12) + '" width="26" height="150" fill="#7a4a22"' + grosor(6) + '/>' +
    '<rect x="' + n1(x - a) + '" y="' + n1(y - 22) + '" width="' + ancho + '" height="46" rx="14" fill="' + c + '"' + grosor(8) + '/><rect x="' + n1(x - a + 14) + '" y="' + n1(y - 14) + '" width="' + n1(ancho - 28) + '" height="9" rx="4" fill="#fff" opacity=".35"/>';
}
function papel(x, y, s, giro = 0, { lineas: l = 4 } = {}) {
  let r = ''; for (let i = 0; i < l; i++) r += '<line x1="' + n1(-s * 0.32) + '" y1="' + n1(-s * 0.3 + i * s * 0.17) + '" x2="' + n1(s * 0.32 - (i % 2) * s * 0.12) + '" y2="' + n1(-s * 0.3 + i * s * 0.17) + '" stroke="#9aa6b2" stroke-width="4" stroke-linecap="round"/>';
  return '<g transform="translate(' + x + ' ' + y + ') rotate(' + giro + ')"><rect x="' + n1(-s * 0.42) + '" y="' + n1(-s * 0.55) + '" width="' + n1(s * 0.84) + '" height="' + n1(s * 1.1) + '" rx="5" fill="#fff"' + grosor(5) + '/>' + r + '</g>';
}
function taza(x, y, s, giro = 0) {
  const k = s / 100;
  return '<g transform="translate(' + x + ' ' + y + ') rotate(' + giro + ') scale(' + k + ')"><path d="M-34 -40 L34 -40 L28 34 Q0 44 -28 34Z" fill="#fff"' + grosor(7) + '/><path d="M34 -22 C62 -22 62 14 30 14" fill="none"' + grosor(9) + '/><path d="M-30 -26 L30 -26" stroke="#8a4b12" stroke-width="12" stroke-linecap="round"/></g>';
}
function reloj(x, y, r, h = 9, m = 0) {
  const a = (h % 12 + m / 60) / 12 * Math.PI * 2 - Math.PI / 2, b = (m / 60) * Math.PI * 2 - Math.PI / 2;
  return '<circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="#fff"' + grosor(8) + '/>' + [0, 3, 6, 9].map((i) => { const t = i / 12 * Math.PI * 2 - Math.PI / 2; return '<circle cx="' + n1(x + Math.cos(t) * r * 0.76) + '" cy="' + n1(y + Math.sin(t) * r * 0.76) + '" r="' + n1(r * 0.07) + '" fill="' + O + '"/>'; }).join('') +
    '<line x1="' + x + '" y1="' + y + '" x2="' + n1(x + Math.cos(a) * r * 0.5) + '" y2="' + n1(y + Math.sin(a) * r * 0.5) + '" stroke="' + O + '" stroke-width="' + n1(r * 0.12) + '" stroke-linecap="round"/><line x1="' + x + '" y1="' + y + '" x2="' + n1(x + Math.cos(b) * r * 0.74) + '" y2="' + n1(y + Math.sin(b) * r * 0.74) + '" stroke="' + O + '" stroke-width="' + n1(r * 0.08) + '" stroke-linecap="round"/>';
}
function garrote(x, y, largo, giro = 0) {   // garrote de gigante, de punta a mango: x,y = mango
  return '<g transform="translate(' + x + ' ' + y + ') rotate(' + giro + ')"><path d="M-14 0 L14 0 L22 -' + n1(largo * 0.55) + ' L-22 -' + n1(largo * 0.55) + 'Z" fill="#8a5a2b"' + grosor(8) + '/><path d="M-22 -' + n1(largo * 0.5) + ' C-52 -' + n1(largo * 0.6) + ' -52 -' + n1(largo) + ' 0 -' + n1(largo) + ' C52 -' + n1(largo) + ' 52 -' + n1(largo * 0.6) + ' 22 -' + n1(largo * 0.5) + 'Z" fill="#a8703a"' + grosor(8) + '/>' +
    [[-14, 0.7], [12, 0.78], [-4, 0.9]].map(([dx, f]) => '<circle cx="' + dx + '" cy="-' + n1(largo * f) + '" r="6" fill="#d9a56a"/>').join('') + '</g>';
}
function murcielago(x, y, s, giro = 0) {
  const k = s / 100;
  return '<g transform="translate(' + x + ' ' + y + ') rotate(' + giro + ') scale(' + k + ')"><path d="M0 -10 C-20 -50 -70 -52 -96 -30 C-80 -22 -70 -10 -64 6 C-50 -8 -36 -4 -28 12 C-18 0 -8 4 0 14 C8 4 18 0 28 12 C36 -4 50 -8 64 6 C70 -10 80 -22 96 -30 C70 -52 20 -50 0 -10Z" fill="#3b2a5c"' + grosor(7) + '/><circle cx="-8" cy="-6" r="5" fill="#ffd95e"/><circle cx="8" cy="-6" r="5" fill="#ffd95e"/><path d="M-10 -20 L-6 -34 L-2 -20 M2 -20 L6 -34 L10 -20" fill="#3b2a5c"' + grosor(5) + '/></g>';
}
function ankh(x, y, s, { c = C.oro } = {}) {
  const k = s / 100;
  return '<g transform="translate(' + x + ' ' + y + ') scale(' + k + ')"><ellipse cx="0" cy="-70" rx="30" ry="40" fill="none" stroke="' + O + '" stroke-width="26"/><line x1="0" y1="-30" x2="0" y2="70" stroke="' + O + '" stroke-width="26" stroke-linecap="round"/><line x1="-44" y1="-6" x2="44" y2="-6" stroke="' + O + '" stroke-width="26" stroke-linecap="round"/>' +
    '<ellipse cx="0" cy="-70" rx="30" ry="40" fill="none" stroke="' + c + '" stroke-width="12"/><line x1="0" y1="-30" x2="0" y2="70" stroke="' + c + '" stroke-width="12" stroke-linecap="round"/><line x1="-44" y1="-6" x2="44" y2="-6" stroke="' + c + '" stroke-width="12" stroke-linecap="round"/></g>';
}
function mano(x, y, r, { c = C.piel } = {}) { return '<circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="' + c + '"' + grosor(Math.max(4, r * 0.3)) + '/>'; }
function bota(x, y, s, giro = 0) { return '<g transform="translate(' + x + ' ' + y + ') rotate(' + giro + ') scale(' + s / 100 + ')"><path d="M-20 -40 L18 -40 L18 -4 L52 6 Q58 30 40 34 L-24 34 Q-34 34 -32 20Z" fill="#8a5a2b"' + grosor(8) + '/></g>'; }
function moneda(x, y, r) { return '<circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="' + C.oro + '"' + grosor(Math.max(3, r * 0.22)) + '/><circle cx="' + x + '" cy="' + y + '" r="' + n1(r * 0.62) + '" fill="none" stroke="#fff3b0" stroke-width="' + n1(Math.max(2, r * 0.16)) + '"/>'; }
function estrellita(x, y, r, c = C.amarillo) {
  let p = ''; for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r * 0.45 : r; p += n1(x + Math.cos(a) * rr) + ',' + n1(y + Math.sin(a) * rr) + ' '; }
  return '<polygon points="' + p + '" fill="' + c + '"' + grosor(Math.max(3, r * 0.2)) + '/>';
}
function escalera(x, y, ancho, nivel, alto) {   // peldaños que suben hacia la derecha (modo Reto)
  let s = ''; for (let i = 0; i < nivel; i++) { const px = x + i * ancho, py = y - i * alto; s += '<rect x="' + n1(px) + '" y="' + n1(py) + '" width="' + ancho + '" height="' + n1(alto * (i + 1) + 40) + '" fill="' + (i % 2 ? '#ffd95e' : '#ffc233') + '"' + grosor(7) + '/>'; }
  return s;
}
function espejo(x, y, ancho, alto) { return '<rect x="' + x + '" y="' + y + '" width="' + ancho + '" height="' + alto + '" rx="16" fill="#cfeaff"' + grosor(8) + '/><path d="M' + n1(x + ancho * 0.18) + ' ' + n1(y + alto * 0.8) + ' L' + n1(x + ancho * 0.5) + ' ' + n1(y + alto * 0.2) + ' M' + n1(x + ancho * 0.42) + ' ' + n1(y + alto * 0.9) + ' L' + n1(x + ancho * 0.74) + ' ' + n1(y + alto * 0.3) + '" stroke="#fff" stroke-width="12" stroke-linecap="round" opacity=".8"/>'; }

// ---------- fondos ----------
const dg = (id, c0, c1, v = true) => '<linearGradient id="' + id + '" x1="0" y1="0" x2="' + (v ? 0 : 1) + '" y2="' + (v ? 1 : 0) + '"><stop offset="0" stop-color="' + c0 + '"/><stop offset="1" stop-color="' + c1 + '"/></linearGradient>';
function nubesFondo(A, n, c = '#fff', y0 = 40, y1 = 240) {
  let s = ''; for (let i = 0; i < n; i++) { const x = A() * 1200, y = y0 + A() * (y1 - y0), r = 36 + A() * 38; s += '<g opacity=".92"><ellipse cx="' + n1(x) + '" cy="' + n1(y) + '" rx="' + n1(r * 1.9) + '" ry="' + n1(r * 0.62) + '" fill="' + c + '"/><circle cx="' + n1(x - r * 0.5) + '" cy="' + n1(y - r * 0.3) + '" r="' + n1(r * 0.7) + '" fill="' + c + '"/><circle cx="' + n1(x + r * 0.45) + '" cy="' + n1(y - r * 0.4) + '" r="' + n1(r * 0.8) + '" fill="' + c + '"/></g>'; }
  return s;
}
function fondoPrado({ cielo = ['#7fd0ff', '#dff4ff'], suelo = ['#a6dd6e', '#6fbf4f'], horizonte = 380, semilla = 11, sol = true } = {}) {
  const A = azar(semilla), g1 = uid('cielo'), g2 = uid('suelo'); let hierba = '';
  for (let i = 0; i < 34; i++) { const x = A() * 1200, y = horizonte + 30 + A() * (675 - horizonte - 40), k = 0.6 + (y - horizonte) / 300; hierba += '<path d="M' + n1(x) + ' ' + n1(y) + ' l-' + n1(7 * k) + ' -' + n1(16 * k) + ' M' + n1(x) + ' ' + n1(y) + ' l0 -' + n1(20 * k) + ' M' + n1(x) + ' ' + n1(y) + ' l' + n1(7 * k) + ' -' + n1(16 * k) + '" stroke="#4e9d3d" stroke-width="4" stroke-linecap="round" fill="none"/>'; }
  return '<defs>' + dg(g1, cielo[0], cielo[1]) + dg(g2, suelo[0], suelo[1]) + '</defs><rect width="1200" height="675" fill="url(#' + g1 + ')"/>' + (sol ? '<circle cx="1010" cy="110" r="64" fill="#fff3b0" opacity=".9"/><circle cx="1010" cy="110" r="44" fill="#ffe27a"/>' : '') + nubesFondo(A, 5) +
    '<path d="M-20 ' + (horizonte + 10) + ' Q220 ' + (horizonte - 90) + ' 470 ' + (horizonte - 10) + ' T980 ' + (horizonte - 20) + ' T1240 ' + (horizonte - 50) + ' V700 H-20Z" fill="#8bd05f"/>' +
    '<path d="M-20 ' + (horizonte + 24) + ' Q300 ' + (horizonte - 20) + ' 620 ' + (horizonte + 14) + ' T1240 ' + (horizonte + 6) + ' V700 H-20Z" fill="url(#' + g2 + ')"/><path d="M-20 ' + (horizonte + 24) + ' Q300 ' + (horizonte - 20) + ' 620 ' + (horizonte + 14) + ' T1240 ' + (horizonte + 6) + '" fill="none" stroke="#c9f08f" stroke-width="6"/>' + hierba;
}
function fondoNoche({ semilla = 12, niebla = true } = {}) {
  const A = azar(semilla), g1 = uid('noche'); let est = '', lapidas = '';
  for (let i = 0; i < 40; i++) est += destello(A() * 1200, 20 + A() * 300, 4 + A() * 9, { c: '#fff' });
  for (const x of [90, 300, 880, 1090]) lapidas += '<path d="M' + (x - 38) + ' 470 V400 Q' + (x - 38) + ' 360 ' + x + ' 360 Q' + (x + 38) + ' 360 ' + (x + 38) + ' 400 V470Z" fill="#4b4f86"' + grosor(6) + '/><line x1="' + x + '" y1="388" x2="' + x + '" y2="428" stroke="#6b70b0" stroke-width="7" stroke-linecap="round"/><line x1="' + (x - 14) + '" y1="402" x2="' + (x + 14) + '" y2="402" stroke="#6b70b0" stroke-width="7" stroke-linecap="round"/>';
  return '<defs>' + dg(g1, '#141a4d', '#5b3a8f') + '</defs><rect width="1200" height="675" fill="url(#' + g1 + ')"/>' + est + '<circle cx="960" cy="130" r="92" fill="#fff6c8"' + grosor(0) + '/><circle cx="930" cy="108" r="14" fill="#f0e2a0"/><circle cx="990" cy="160" r="20" fill="#f0e2a0"/><circle cx="1002" cy="96" r="9" fill="#f0e2a0"/>' +
    '<path d="M-20 470 Q300 420 600 460 T1240 450 V700 H-20Z" fill="#2a3a6e"/>' + lapidas + '<path d="M-20 500 Q300 470 600 500 T1240 490 V700 H-20Z" fill="#23305f"/>' + (niebla ? '<ellipse cx="300" cy="560" rx="420" ry="46" fill="#9fb4ff" opacity=".18"/><ellipse cx="900" cy="590" rx="460" ry="52" fill="#9fb4ff" opacity=".16"/>' : '');
}
function fondoEscenario({ semilla = 13 } = {}) {
  const A = azar(semilla), g1 = uid('esc'), g2 = uid('tab'); let publico = '';
  for (let i = 0; i < 17; i++) { const x = 20 + i * 72 + (A() - 0.5) * 24, y = 640 + (A() - 0.5) * 16; publico += '<circle cx="' + n1(x) + '" cy="' + n1(y) + '" r="' + n1(30 + A() * 7) + '" fill="#10163f"/><rect x="' + n1(x - 33) + '" y="' + n1(y + 18) + '" width="66" height="60" rx="26" fill="#10163f"/>' + (A() > 0.55 ? '<rect x="' + n1(x + 12) + '" y="' + n1(y - 62 - A() * 14) + '" width="14" height="22" rx="3" fill="#fff6c9"/>' : ''); }
  let rayos = ''; const sx = 600, sy = 250; for (let i = 0; i < 22; i++) { const a = (i / 22) * Math.PI * 2, b = a + 0.1; rayos += '<polygon points="' + sx + ',' + sy + ' ' + n1(sx + Math.cos(a) * 900) + ',' + n1(sy + Math.sin(a) * 900) + ' ' + n1(sx + Math.cos(b) * 900) + ',' + n1(sy + Math.sin(b) * 900) + '" fill="#ffd95e" opacity=".13"/>'; }
  const cortina = (lado) => { const x = lado < 0 ? 0 : 1200, d = lado; return '<path d="M' + x + ' 0 H' + (x + d * 230) + ' Q' + (x + d * 170) + ' 120 ' + (x + d * 205) + ' 240 Q' + (x + d * 150) + ' 380 ' + (x + d * 190) + ' 520 L' + (x + d * 180) + ' 560 H' + x + 'Z" fill="#c2243c"' + grosor(8) + '/><path d="M' + (x + d * 60) + ' 0 Q' + (x + d * 40) + ' 280 ' + (x + d * 62) + ' 560 M' + (x + d * 125) + ' 0 Q' + (x + d * 100) + ' 280 ' + (x + d * 130) + ' 560" stroke="#8d1530" stroke-width="10" fill="none"/>'; };
  return '<defs>' + dg(g1, '#0f1450', '#3a2a86') + dg(g2, '#b9763a', '#7c4a22') + '</defs><rect width="1200" height="675" fill="url(#' + g1 + ')"/>' + rayos + '<circle cx="600" cy="250" r="150" fill="#ffd95e" opacity=".22"/>' + destellos([[300, 90, 16], [870, 70, 20], [1010, 190, 12], [180, 210, 12]]) +
    '<path d="M-20 470 H1220 V700 H-20Z" fill="url(#' + g2 + ')"/><rect x="-20" y="462" width="1240" height="16" fill="#ffd95e"' + grosor(6) + '/>' + [140, 300, 460, 620, 780, 940, 1100].map((x) => '<line x1="' + x + '" y1="478" x2="' + (x - 40) + '" y2="700" stroke="#6a3e1c" stroke-width="5" opacity=".6"/>').join('') + cortina(-1) + cortina(1) + publico;
}
function fondoOficina() {
  const g1 = uid('of'); let edificios = '';
  [[760, 190, 70, 150], [832, 130, 90, 210], [926, 170, 60, 170], [990, 110, 80, 230]].forEach(([x, y, w, h]) => { edificios += '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" fill="#9cb7d9"' + grosor(5) + '/>'; for (let r = 0; r < h / 40 - 1; r++) for (let c = 0; c < w / 28; c++) edificios += '<rect x="' + (x + 8 + c * 24) + '" y="' + (y + 12 + r * 38) + '" width="12" height="18" fill="#e9f3ff"/>'; });
  return '<defs>' + dg(g1, '#e8efff', '#cdd9f5') + '</defs><rect width="1200" height="675" fill="url(#' + g1 + ')"/><rect x="700" y="80" width="400" height="300" rx="14" fill="#bfe3ff"' + grosor(10) + '/>' + edificios + '<line x1="900" y1="80" x2="900" y2="380" stroke="' + O + '" stroke-width="8"/><line x1="700" y1="230" x2="1100" y2="230" stroke="' + O + '" stroke-width="8"/>' +
    '<rect x="-20" y="440" width="1240" height="260" fill="#c9b79b"/><rect x="-20" y="432" width="1240" height="14" fill="#ab977a"' + grosor(5) + '/>' + [0, 1, 2, 3, 4, 5, 6].map((i) => '<line x1="' + (i * 190 - 40) + '" y1="446" x2="' + (i * 260 - 300) + '" y2="700" stroke="#b6a287" stroke-width="5"/>').join('');
}
function fondoTienda() {
  const g1 = uid('ti'); let rayas = ''; for (let i = -2; i < 22; i++) rayas += '<polygon points="' + (i * 64) + ',0 ' + (i * 64 + 32) + ',0 ' + (i * 64 - 18) + ',86 ' + (i * 64 - 50) + ',86" fill="#14251b"/>';
  return '<defs>' + dg(g1, '#ffe27a', '#ffc233') + '</defs><rect width="1200" height="675" fill="url(#' + g1 + ')"/><rect width="1200" height="92" fill="#ffd24a"/>' + rayas + '<rect y="86" width="1200" height="12" fill="' + O + '"/>' +
    '<rect x="330" y="150" width="540" height="330" rx="12" fill="#bfe8ff"' + grosor(10) + '/><line x1="600" y1="150" x2="600" y2="480" stroke="' + O + '" stroke-width="10"/><path d="M380 450 L520 190 M430 450 L570 190 M650 450 L790 190 M700 450 L840 190" stroke="#fff" stroke-width="16" opacity=".55" stroke-linecap="round"/>' +
    '<rect x="-20" y="480" width="1240" height="220" fill="#8d97a6"/><rect x="-20" y="472" width="1240" height="16" fill="#aab3c0"' + grosor(5) + '/>' + [0, 1, 2, 3, 4, 5].map((i) => '<line x1="' + (i * 240 - 20) + '" y1="488" x2="' + (i * 300 - 220) + '" y2="700" stroke="#7b8594" stroke-width="5"/>').join('');
}
function fondoTormenta({ semilla = 14 } = {}) {
  const A = azar(semilla), g1 = uid('tor'); let nub = '', lluvia = '';
  for (let i = 0; i < 9; i++) { const x = i * 150 - 30 + A() * 40, y = 30 + A() * 110, r = 70 + A() * 40; nub += '<ellipse cx="' + n1(x) + '" cy="' + n1(y) + '" rx="' + n1(r * 1.7) + '" ry="' + n1(r * 0.8) + '" fill="#5a5f86"/><ellipse cx="' + n1(x + 30) + '" cy="' + n1(y - 26) + '" rx="' + n1(r * 1.1) + '" ry="' + n1(r * 0.7) + '" fill="#6d7298"/>'; }
  for (let i = 0; i < 46; i++) { const x = A() * 1200, y = 130 + A() * 520; lluvia += '<line x1="' + n1(x) + '" y1="' + n1(y) + '" x2="' + n1(x - 14) + '" y2="' + n1(y + 40) + '" stroke="#cfe3ff" stroke-width="4" stroke-linecap="round" opacity=".5"/>'; }
  return fondoPrado({ cielo: ['#2c3158', '#6d7298'], suelo: ['#7fb85a', '#4f9a45'], sol: false, semilla }).replace('<defs>', '<defs>') + '<rect width="1200" height="675" fill="#1b1f48" opacity=".3"/>' + nub + lluvia;
}
function fondoRayos({ c1 = '#ffd95e', c2 = '#ffe998', cx = 600, cy = 340, n = 26 } = {}) {
  let s = '<rect width="1200" height="675" fill="' + c1 + '"/>'; for (let i = 0; i < n; i += 2) { const a = (i / n) * Math.PI * 2, b = ((i + 1) / n) * Math.PI * 2; s += '<polygon points="' + cx + ',' + cy + ' ' + n1(cx + Math.cos(a) * 1500) + ',' + n1(cy + Math.sin(a) * 1500) + ' ' + n1(cx + Math.cos(b) * 1500) + ',' + n1(cy + Math.sin(b) * 1500) + '" fill="' + c2 + '"/>'; }
  return s;
}
function fondoNavegador({ c = '#e7eeff' } = {}) {
  return '<rect width="1200" height="675" fill="' + c + '"/><rect x="60" y="44" width="1080" height="590" rx="26" fill="#fff"' + grosor(9) + '/><path d="M60 114 H1140" stroke="' + O + '" stroke-width="9"/><rect x="60" y="44" width="1080" height="70" rx="26" fill="#d9e3fb"/><rect x="60" y="86" width="1080" height="28" fill="#d9e3fb"/>' +
    '<circle cx="110" cy="80" r="11" fill="#ff7a6b"/><circle cx="146" cy="80" r="11" fill="#ffd25a"/><circle cx="182" cy="80" r="11" fill="#6fd68f"/><rect x="240" y="62" width="760" height="38" rx="19" fill="#fff"' + grosor(5) + '/><circle cx="268" cy="81" r="9" fill="' + C.verde + '"/>';
}
function marcoPanel(x, y, w, h, { r = 18 } = {}) { return '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" rx="' + r + '" fill="none"' + grosor(8) + '/>'; }

// ---------- más atrezo (segunda tanda) ----------
function prohibido(x, y, r, { c = C.rojo } = {}) {   // círculo rojo con diagonal, para tachar lo que NO se necesita
  const d = r * 0.7071;
  return '<circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="none" stroke="' + O + '" stroke-width="' + n1(r * 0.34) + '"/><circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="none" stroke="' + c + '" stroke-width="' + n1(r * 0.2) + '"/>' +
    '<line x1="' + n1(x - d) + '" y1="' + n1(y - d) + '" x2="' + n1(x + d) + '" y2="' + n1(y + d) + '" stroke="' + O + '" stroke-width="' + n1(r * 0.34) + '" stroke-linecap="round"/><line x1="' + n1(x - d) + '" y1="' + n1(y - d) + '" x2="' + n1(x + d) + '" y2="' + n1(y + d) + '" stroke="' + c + '" stroke-width="' + n1(r * 0.2) + '" stroke-linecap="round"/>';
}
function iconoDescarga(x, y, r) {   // flecha hacia abajo sobre una bandeja, dentro de un círculo azul
  return '<circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="#4b8cff"' + grosor(Math.max(5, r * 0.07)) + '/><path d="M' + n1(x - r * 0.2) + ' ' + n1(y - r * 0.55) + ' H' + n1(x + r * 0.2) + ' V' + n1(y - r * 0.05) + ' H' + n1(x + r * 0.42) + ' L' + x + ' ' + n1(y + r * 0.42) + ' L' + n1(x - r * 0.42) + ' ' + n1(y - r * 0.05) + ' H' + n1(x - r * 0.2) + 'Z" fill="#fff"' + grosor(Math.max(4, r * 0.05)) + '/><path d="M' + n1(x - r * 0.5) + ' ' + n1(y + r * 0.58) + ' H' + n1(x + r * 0.5) + '" stroke="#fff" stroke-width="' + n1(r * 0.12) + '" stroke-linecap="round"/>';
}
function iconoCuenta(x, y, r) {   // silueta de usuario y dos campos de formulario
  return '<rect x="' + n1(x - r) + '" y="' + n1(y - r * 0.8) + '" width="' + n1(r * 2) + '" height="' + n1(r * 1.6) + '" rx="' + n1(r * 0.16) + '" fill="#fff"' + grosor(Math.max(5, r * 0.07)) + '/><circle cx="' + x + '" cy="' + n1(y - r * 0.38) + '" r="' + n1(r * 0.2) + '" fill="#9aa6b2"/><path d="M' + n1(x - r * 0.38) + ' ' + n1(y - r * 0.02) + ' Q' + x + ' ' + n1(y - r * 0.28) + ' ' + n1(x + r * 0.38) + ' ' + n1(y - r * 0.02) + 'Z" fill="#9aa6b2"/>' +
    '<rect x="' + n1(x - r * 0.7) + '" y="' + n1(y + r * 0.12) + '" width="' + n1(r * 1.4) + '" height="' + n1(r * 0.22) + '" rx="' + n1(r * 0.08) + '" fill="#dfe6ee"' + grosor(3) + '/><rect x="' + n1(x - r * 0.7) + '" y="' + n1(y + r * 0.44) + '" width="' + n1(r * 1.4) + '" height="' + n1(r * 0.22) + '" rx="' + n1(r * 0.08) + '" fill="#dfe6ee"' + grosor(3) + '/>';
}
function barraCarga(x, y, ancho, alto, frac) {
  return '<rect x="' + x + '" y="' + y + '" width="' + ancho + '" height="' + alto + '" rx="' + n1(alto / 2) + '" fill="#dfe6ee"' + grosor(6) + '/><rect x="' + n1(x + 5) + '" y="' + n1(y + 5) + '" width="' + n1((ancho - 10) * frac) + '" height="' + n1(alto - 10) + '" rx="' + n1((alto - 10) / 2) + '" fill="' + C.verde + '"/>';
}
function pizza(x, y, r) {
  let s = '<circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="#e8b45c"' + grosor(Math.max(6, r * 0.06)) + '/><circle cx="' + x + '" cy="' + y + '" r="' + n1(r * 0.86) + '" fill="#ffd95e"/>';
  const A = azar(5);
  for (let i = 0; i < 6; i++) { const a = (i / 6) * Math.PI * 2 + 0.4, d = r * (0.38 + (i % 2) * 0.24); s += '<circle cx="' + n1(x + Math.cos(a) * d) + '" cy="' + n1(y + Math.sin(a) * d) + '" r="' + n1(r * 0.12) + '" fill="#d94a3a"' + grosor(3) + '/>'; }
  for (let i = 0; i < 6; i++) { const a = (i / 6) * Math.PI * 2 + 1.0, d = r * (0.28 + ((i + 1) % 2) * 0.34), px = x + Math.cos(a) * d, py = y + Math.sin(a) * d; s += '<path d="M' + n1(px - r * 0.1) + ' ' + n1(py + r * 0.08) + ' L' + n1(px) + ' ' + n1(py - r * 0.12) + ' L' + n1(px + r * 0.1) + ' ' + n1(py + r * 0.08) + 'Z" fill="#fff08a"' + grosor(3) + '/>'; }
  return s + '<path d="M' + x + ' ' + y + ' L' + n1(x + r * 0.86) + ' ' + y + ' M' + x + ' ' + y + ' L' + n1(x - r * 0.43) + ' ' + n1(y + r * 0.74) + ' M' + x + ' ' + y + ' L' + n1(x - r * 0.43) + ' ' + n1(y - r * 0.74) + '" stroke="#c98e3d" stroke-width="4" stroke-linecap="round" opacity=".7"/>';
}
function botiquin(x, y, s) {
  const k = s / 100;
  return '<g transform="translate(' + x + ' ' + y + ') scale(' + k + ')"><path d="M-30 -66 Q-30 -88 -8 -88 H8 Q30 -88 30 -66" fill="none"' + grosor(10) + '/><rect x="-74" y="-70" width="148" height="104" rx="16" fill="#fff"' + grosor(8) + '/><rect x="-12" y="-52" width="24" height="68" rx="5" fill="' + C.rojo + '"/><rect x="-34" y="-30" width="68" height="24" rx="5" fill="' + C.rojo + '"/></g>';
}
function enojo(x, y, s) {   // marca de enojo: cuatro arcos rojos
  let p = ''; for (const [dx, dy, a] of [[-1, -1, 0], [1, -1, 90], [1, 1, 180], [-1, 1, 270]]) p += '<path d="M' + n1(x + dx * s * 0.28) + ' ' + n1(y + dy * s * 0.28) + ' q' + n1(dx * s * 0.62) + ' ' + n1(0) + ' ' + n1(dx * s * 0.62) + ' ' + n1(dy * s * 0.62) + '" fill="none" stroke="' + O + '" stroke-width="' + n1(s * 0.34) + '" stroke-linecap="round"/><path d="M' + n1(x + dx * s * 0.28) + ' ' + n1(y + dy * s * 0.28) + ' q' + n1(dx * s * 0.62) + ' ' + n1(0) + ' ' + n1(dx * s * 0.62) + ' ' + n1(dy * s * 0.62) + '" fill="none" stroke="' + C.rojo + '" stroke-width="' + n1(s * 0.2) + '" stroke-linecap="round"/>';
  return p;
}
function sol(x, y, r) {
  let rayos = ''; for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2; rayos += '<line x1="' + n1(x + Math.cos(a) * r * 1.2) + '" y1="' + n1(y + Math.sin(a) * r * 1.2) + '" x2="' + n1(x + Math.cos(a) * r * 1.65) + '" y2="' + n1(y + Math.sin(a) * r * 1.65) + '" stroke="' + O + '" stroke-width="' + n1(r * 0.3) + '" stroke-linecap="round"/><line x1="' + n1(x + Math.cos(a) * r * 1.2) + '" y1="' + n1(y + Math.sin(a) * r * 1.2) + '" x2="' + n1(x + Math.cos(a) * r * 1.65) + '" y2="' + n1(y + Math.sin(a) * r * 1.65) + '" stroke="#ffd13d" stroke-width="' + n1(r * 0.16) + '" stroke-linecap="round"/>'; }
  return rayos + '<circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="#ffe266"' + grosor(Math.max(5, r * 0.12)) + '/>';
}
function nubeIcono(x, y, r, { c = '#fff' } = {}) {   // nube de dibujo animado, con contorno
  const d = 'M' + n1(x - r * 1.1) + ' ' + n1(y + r * 0.45) + ' Q' + n1(x - r * 1.5) + ' ' + n1(y + r * 0.45) + ' ' + n1(x - r * 1.4) + ' ' + n1(y + r * 0.0) + ' Q' + n1(x - r * 1.3) + ' ' + n1(y - r * 0.4) + ' ' + n1(x - r * 0.8) + ' ' + n1(y - r * 0.3) + ' Q' + n1(x - r * 0.6) + ' ' + n1(y - r * 1.0) + ' ' + n1(x + r * 0.1) + ' ' + n1(y - r * 0.8) + ' Q' + n1(x + r * 0.8) + ' ' + n1(y - r * 0.9) + ' ' + n1(x + r * 0.9) + ' ' + n1(y - r * 0.2) + ' Q' + n1(x + r * 1.5) + ' ' + n1(y - r * 0.2) + ' ' + n1(x + r * 1.5) + ' ' + n1(y + r * 0.2) + ' Q' + n1(x + r * 1.5) + ' ' + n1(y + r * 0.45) + ' ' + n1(x + r * 1.1) + ' ' + n1(y + r * 0.45) + 'Z';
  return '<path d="' + d + '" fill="' + c + '"' + grosor(Math.max(5, r * 0.1)) + '/>';
}
function lluvia(x, y, r, n = 5) { let s = ''; for (let i = 0; i < n; i++) s += gota(x - r + (i + 0.5) * (2 * r / n), y + (i % 2) * r * 0.5, r * 0.14); return s; }
function copo(x, y, r) {
  let s = ''; for (let i = 0; i < 6; i++) { const a = i / 6 * Math.PI * 2 + Math.PI / 6, x1 = x + Math.cos(a) * r, y1 = y + Math.sin(a) * r; s += '<line x1="' + x + '" y1="' + y + '" x2="' + n1(x1) + '" y2="' + n1(y1) + '" stroke="' + O + '" stroke-width="' + n1(r * 0.3) + '" stroke-linecap="round"/><line x1="' + n1(x + Math.cos(a) * r * 0.55) + '" y1="' + n1(y + Math.sin(a) * r * 0.55) + '" x2="' + n1(x + Math.cos(a + 0.7) * r * 0.8) + '" y2="' + n1(y + Math.sin(a + 0.7) * r * 0.8) + '" stroke="' + O + '" stroke-width="' + n1(r * 0.22) + '" stroke-linecap="round"/>'; }
  let b = ''; for (let i = 0; i < 6; i++) { const a = i / 6 * Math.PI * 2 + Math.PI / 6, x1 = x + Math.cos(a) * r, y1 = y + Math.sin(a) * r; b += '<line x1="' + x + '" y1="' + y + '" x2="' + n1(x1) + '" y2="' + n1(y1) + '" stroke="#bfe6ff" stroke-width="' + n1(r * 0.14) + '" stroke-linecap="round"/><line x1="' + n1(x + Math.cos(a) * r * 0.55) + '" y1="' + n1(y + Math.sin(a) * r * 0.55) + '" x2="' + n1(x + Math.cos(a + 0.7) * r * 0.8) + '" y2="' + n1(y + Math.sin(a + 0.7) * r * 0.8) + '" stroke="#bfe6ff" stroke-width="' + n1(r * 0.1) + '" stroke-linecap="round"/>'; }
  return s + b;
}
function arcoiris(x, y, r) { return ['#e24a33', '#ffa63d', '#ffe14a', '#46c68d', '#4b8cff', '#8a5cd6'].map((c, i) => '<path d="M' + n1(x - r + i * r * 0.1) + ' ' + y + ' A' + n1(r - i * r * 0.1) + ' ' + n1(r - i * r * 0.1) + ' 0 0 1 ' + n1(x + r - i * r * 0.1) + ' ' + y + '" fill="none" stroke="' + c + '" stroke-width="' + n1(r * 0.1) + '"/>').join(''); }
function piramides({ y = 400 } = {}) {
  return '<polygon points="120,' + y + ' 300,' + (y - 170) + ' 480,' + y + '" fill="#e8b865"' + grosor(7) + '/><polygon points="300,' + (y - 170) + ' 480,' + y + ' 360,' + y + '" fill="#cf9a4a"/><polygon points="760,' + y + ' 950,' + (y - 230) + ' 1140,' + y + '" fill="#e8b865"' + grosor(7) + '/><polygon points="950,' + (y - 230) + ' 1140,' + y + ' 1030,' + y + '" fill="#cf9a4a"/>';
}
function pensamiento(x, y, rx, ry, colaX, colaY) {   // globo de pensamiento con tres bolitas hacia (colaX, colaY)
  let s = '<ellipse cx="' + x + '" cy="' + y + '" rx="' + rx + '" ry="' + ry + '" fill="#fff"' + grosor(8) + '/>';
  for (let i = 1; i <= 3; i++) { const t = i / 4; s += '<circle cx="' + n1(x + (colaX - x) * (0.55 + t * 0.4)) + '" cy="' + n1(y + ry + (colaY - y - ry) * t) + '" r="' + n1(18 - i * 4) + '" fill="#fff"' + grosor(5) + '/>'; }
  return s + '<ellipse cx="' + x + '" cy="' + y + '" rx="' + n1(rx - 5) + '" ry="' + n1(ry - 5) + '" fill="#fff"/>';
}
function antena(x, y, alto) { return '<line x1="' + x + '" y1="' + y + '" x2="' + x + '" y2="' + n1(y - alto) + '" stroke="' + O + '" stroke-width="12" stroke-linecap="round"/><line x1="' + x + '" y1="' + y + '" x2="' + x + '" y2="' + n1(y - alto) + '" stroke="#9aa6b2" stroke-width="6" stroke-linecap="round"/><circle cx="' + x + '" cy="' + n1(y - alto) + '" r="13" fill="' + C.rojo + '"' + grosor(5) + '/>'; }
function laptop(x, y, s) {
  const k = s / 100;
  return '<g transform="translate(' + x + ' ' + y + ') scale(' + k + ')"><rect x="-70" y="-100" width="140" height="94" rx="9" fill="#2b2f3a"' + grosor(7) + '/><rect x="-58" y="-90" width="116" height="74" rx="4" fill="#bfe8ff"/><path d="M-46 -34 L-24 -52 L-6 -40 L18 -68 L44 -76" fill="none" stroke="' + C.verde + '" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/><path d="M-84 -6 H84 L96 10 H-96Z" fill="#c7d0da"' + grosor(7) + '/></g>';
}
function megafono(x, y, s, giro = 0) {
  const k = s / 100;
  return '<g transform="translate(' + x + ' ' + y + ') rotate(' + giro + ') scale(' + k + ')"><path d="M-40 -22 L50 -62 L50 62 L-40 22Z" fill="' + C.rojo + '"' + grosor(8) + '/><rect x="-66" y="-26" width="34" height="52" rx="8" fill="#2b2f3a"' + grosor(7) + '/><path d="M-50 22 L-44 64 L-24 64 L-26 28Z" fill="#2b2f3a"' + grosor(6) + '/><path d="M70 -30 Q90 0 70 30 M86 -48 Q116 0 86 48" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round"/></g>';
}
function graficaPared(x, y, w, h) {
  return '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" rx="10" fill="#fff"' + grosor(7) + '/><path d="M' + n1(x + w * 0.1) + ' ' + n1(y + h * 0.78) + ' L' + n1(x + w * 0.35) + ' ' + n1(y + h * 0.55) + ' L' + n1(x + w * 0.55) + ' ' + n1(y + h * 0.65) + ' L' + n1(x + w * 0.88) + ' ' + n1(y + h * 0.2) + '" fill="none" stroke="' + C.verde + '" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>' + [0.1, 0.35, 0.55, 0.88].map((f, i) => '<circle cx="' + n1(x + w * f) + '" cy="' + n1(y + h * [0.78, 0.55, 0.65, 0.2][i]) + '" r="9" fill="' + C.amarillo + '"' + grosor(4) + '/>').join('');
}

module.exports = { O, C, azar, impacto, lineas, nube, rayo, ondas, destello, destellos, corazon, gota, signo, grietas, llamas, flecha, diana, confeti, foco, sombra, trofeo, carrito, etiqueta, microfono, mesa, papel, taza, reloj, garrote, murcielago, ankh, mano, bota, moneda, estrellita, prohibido, iconoDescarga, iconoCuenta, barraCarga, pizza, botiquin, enojo, sol, nubeIcono, lluvia, copo, arcoiris, piramides, pensamiento, antena, laptop, megafono, graficaPared, escalera, espejo,
  fondoPrado, fondoNoche, fondoEscenario, fondoOficina, fondoTienda, fondoTormenta, fondoRayos, fondoNavegador, marcoPanel };
