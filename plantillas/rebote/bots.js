// Pruebas con bots de la plantilla «rebote» (las lee `python3 fabrica.py bots`; el contrato está en motor/BOTS.md).
// Las políticas corren DENTRO de la página, con el tiempo simulado del juego: son funciones sueltas (no pueden usar variables de afuera);
// lo común va en `preludio`, que se ejecuta una vez en la página antes de jugar.
module.exports = {
  descripcion: 'Puzzle de física: ¿se puede ganar cada nivel?, ¿qué tan ancho es el margen para acertar?, ¿cuánto ayuda tener varios tiros?',
  base: 'aleatorio',          // la política más débil: si gana casi siempre, el nivel es trivial
  solucionador: 'oraculo',    // la que demuestra que se puede ganar: si ni ella gana, el nivel es imposible
  humano: 'novato',           // la que imita una mano humana con temblor: su tasa de éxito es la dificultad que sentiría una persona
  escenas: [0, 1, 2, 3, 4, 5].map((n) => ({ nombre: 'nivel-' + (n + 1), opciones: { nivel: n } })),
  episodio: { max_pasos: 400, dt: 250 },
  partidas: { aleatorio: 60, oraculo: 1, novato: 40 },
  preludio: `
    // Busca, por simulación, todos los tiros de una rejilla que ganan, y elige el más robusto (el de más vecinos que también ganan).
    window.__rebote_bot = window.__rebote_bot || { cache: {} };
    window.__rebote_bot.buscar = function (api) {
      const e = api.estado(), clave = String(e.nivel);
      const c = window.__rebote_bot.cache;
      if (c[clave]) return c[clave];
      const A = [], Pw = [];
      for (let a = 5; a <= 88; a += 1) A.push(a);
      for (let p = 0.2; p <= 1.0001; p += 0.02) Pw.push(Math.round(p * 100) / 100);
      const ok = A.map((a) => Pw.map((p) => { const r = api.simular({ angulo: a, potencia: p }); return !!(r && r.exito); }));
      let total = 0, mejor = null, mejorV = -1;
      for (let i = 0; i < A.length; i++) for (let j = 0; j < Pw.length; j++) {
        if (!ok[i][j]) continue;
        total++;
        let v = 0;
        for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++) if (ok[i + di] && ok[i + di][j + dj]) v++;
        if (v > mejorV) { mejorV = v; mejor = { angulo: A[i], potencia: Pw[j] }; }
      }
      return (c[clave] = { total, celdas: A.length * Pw.length, mejor, robustez: mejorV / 9 });
    };
  `,
  politicas: {
    aleatorio: (api, rng) => {
      const e = api.estado();
      if (e.fase !== 'apuntando') return { tipo: 'esperar' };
      return { tipo: 'disparar', angulo: 5 + rng() * 83, potencia: 0.2 + rng() * 0.8 };
    },
    oraculo: (api, rng) => {
      const e = api.estado();
      if (e.fase !== 'apuntando') return { tipo: 'esperar' };
      const b = window.__rebote_bot.buscar(api);
      const info = { soluciones: b.total, fraccion: Math.round(b.total / b.celdas * 10000) / 10000, robustez: Math.round(b.robustez * 100) / 100 };
      if (!b.mejor) return { tipo: 'disparar', angulo: 45, potencia: 0.7, info };
      return { tipo: 'disparar', angulo: b.mejor.angulo, potencia: b.mejor.potencia, info };
    },
    novato: (api, rng) => {
      const e = api.estado();
      if (e.fase !== 'apuntando') return { tipo: 'esperar' };
      const b = window.__rebote_bot.buscar(api);
      const base = b.mejor || { angulo: 45, potencia: 0.7 };
      return { tipo: 'disparar', angulo: base.angulo + (rng() * 2 - 1) * 6, potencia: base.potencia + (rng() * 2 - 1) * 0.08 };
    },
  },
};
