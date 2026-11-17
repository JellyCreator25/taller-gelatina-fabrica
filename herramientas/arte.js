// Dibuja personajes de la plantilla de gelatina con el propio código del juego, sobre un lienzo transparente (PNG en data URL).
// La plantilla guarda drawJelly dentro de una función; aquí se usa una copia TEMPORAL de index.html con una línea más que la deja a mano.
// El juego publicado no se toca. Lo usan la portada de héroes (probar.js) y las tarjetas de Leyenda (tarjetas.js).
// reparto: [tipo, equipo (0 azul, 1 rojo), x, y, escala, dirección (1 | -1), golpe (0 a 1)] en unidades del lienzo (ancho × alto).
// Una escala NEGATIVA pide un radio de cuerpo fijo: -88 dibuja a cualquier personaje con 88 unidades de radio, sea chico o grande.
const fs = require('fs');
const os = require('os');
const path = require('path');

const GANCHO = 'else boot();\n})();';

async function dibujarUnidades(browser, rutaIndex, reparto, { ancho, alto, densidad }) {
  let html = fs.readFileSync(rutaIndex, 'utf8');
  if (html.split(GANCHO).length !== 2) throw new Error('la plantilla de ese juego no permite dibujar personajes (no encuentro «else boot();» al final de su script)');
  html = html.replace(GANCHO, 'else boot();\nwindow.__dibujo = { drawJelly, UNITS, teamColor, G };\n})();');
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'arte-'));
  try {
    const archivo = path.join(tmp, 'juego.html');
    fs.writeFileSync(archivo, html);
    const ctx = await browser.newContext({ viewport: { width: 1300, height: 900 } });
    const page = await ctx.newPage();
    await page.goto('file://' + archivo);
    await page.waitForSelector('#cv');
    const url = await page.evaluate(({ lista, ancho, alto, d }) => {
      const { drawJelly, UNITS, teamColor, G } = window.__dibujo;
      G.rt = 1.2;   // las animaciones del juego dependen del reloj: un instante fijo hace que la imagen salga igual cada vez
      const c = document.createElement('canvas'); c.width = Math.round(ancho * d); c.height = Math.round(alto * d);
      const x = c.getContext('2d'); x.scale(d, d);
      for (const [t] of lista) if (!UNITS[t]) throw new Error('la unidad «' + t + '» no existe en ese juego');
      for (const [t, eq, px, py, s0, dir, golpe] of lista.slice().sort((a, b) => a[3] - b[3])) {   // de atrás hacia adelante
        const s = s0 < 0 ? -s0 / UNITS[t].r : s0;
        const r = UNITS[t].r * s, col = teamColor(eq);
        x.fillStyle = 'rgba(8,16,40,.38)'; x.beginPath(); x.ellipse(px, py + r * 0.7, r * 1.15, r * 0.42, 0, 0, Math.PI * 2); x.fill();
        x.globalAlpha = 0.9; x.strokeStyle = col; x.lineWidth = 1.3 * s; x.beginPath(); x.ellipse(px, py + r * 0.7, r * 1.17, r * 0.48, 0, 0, Math.PI * 2); x.stroke();
        x.globalAlpha = 0.55; x.strokeStyle = '#ffd24a'; x.lineWidth = 0.8 * s; x.beginPath(); x.ellipse(px, py + r * 0.7, r * 1.34, r * 0.58, 0, 0, Math.PI * 2); x.stroke();
        x.globalAlpha = 1;
        drawJelly(x, t, col, px, py, { scale: s, dir, swing: golpe });
      }
      return c.toDataURL('image/png');
    }, { lista: reparto, ancho, alto, d: densidad });
    await ctx.close();
    return url;
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
}

function tipografias(raiz) {   // @font-face con las fuentes del motor incrustadas (las páginas de portada y tarjetas no cargan nada de fuera)
  const mapa = JSON.parse(fs.readFileSync(path.join(raiz, 'motor', 'fuentes', 'fuentes.json'), 'utf8'));
  let css = '';
  for (const fam of ['Fredoka', 'Nunito Sans']) {
    for (const [peso, arch] of Object.entries(mapa[fam])) {
      const b64 = fs.readFileSync(path.join(raiz, 'motor', 'fuentes', arch)).toString('base64');
      css += "@font-face{font-family:'" + fam + "';font-weight:" + peso + ';src:url(data:font/woff2;base64,' + b64 + ") format('woff2')}\n";
    }
  }
  return css;
}

module.exports = { dibujarUnidades, tipografias };
