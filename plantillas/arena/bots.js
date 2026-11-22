// Pruebas con bots de la plantilla «arena» (las lee `python3 fabrica.py bots`; el contrato está en motor/BOTS.md).
// Las políticas corren DENTRO de la página, con el tiempo simulado del juego: son funciones sueltas (no pueden usar variables de afuera);
// el estado propio de una política vive en window.__arena_bot y se reinicia cuando ctx.paso === 0.
module.exports = {
  descripcion: 'Sandbox de materiales: ¿se puede descubrir todo?, ¿cuánto tarda cada descubrimiento?, ¿la materia se conserva y la simulación es estable?',
  base: 'aleatorio',          // la más débil: si descubre todo a ciegas, el juego no tiene reto
  solucionador: 'explorador', // la que sabe qué hacer: demuestra que todo se puede descubrir
  humano: 'torpe',            // la que imita a una persona imprecisa: su tasa es la dificultad que sentiría alguien
  escenas: [{ nombre: 'mundo', opciones: {} }],
  episodio: { max_pasos: 1200, dt: 100, cada_invariantes: 50 },      // 120 segundos de juego como máximo
  partidas: { aleatorio: 12, explorador: 1, torpe: 12 },
  politicas: {
    aleatorio: (api, rng) => {
      const e = api.estado(), r = rng();
      if (r < 0.1) return { tipo: 'esperar' };
      if (r < 0.2) return { tipo: 'borrar', x: Math.floor(rng() * e.ancho), y: Math.floor(rng() * e.alto), radio: 1 + Math.floor(rng() * 6) };
      const m = e.desbloqueados[Math.floor(rng() * e.desbloqueados.length)];
      return { tipo: 'poner', material: m, x: Math.floor(rng() * e.ancho), y: Math.floor(rng() * 25), radio: 1 + Math.floor(rng() * 6) };
    },
    explorador: (api, rng, ctx) => {
      const s = (window.__arena_bot = window.__arena_bot || {});
      if (ctx.paso === 0) s.k = 0;
      const e = api.estado(), d = e.descubrimientos, u = e.desbloqueados;
      if (d.indexOf('montana') < 0) return { tipo: 'poner', material: 'arena', x: 80, y: 4, radio: 4 };
      if (d.indexOf('barro') < 0) return u.indexOf('agua') >= 0 ? { tipo: 'poner', material: 'agua', x: 80, y: 4, radio: 4 } : { tipo: 'esperar' };
      if (d.indexOf('estanque') < 0) {
        if (u.indexOf('piedra') < 0) return { tipo: 'esperar' };
        if (s.k < 20) { const k = s.k++; return { tipo: 'poner', material: 'piedra', x: k % 2 ? 46 : 8, y: 95 - 4 * Math.floor(k / 2), radio: 3 }; }   // dos muros, tramo a tramo
        return { tipo: 'poner', material: 'agua', x: 27, y: 4, radio: 4 };
      }
      if (d.indexOf('isla') < 0) return u.indexOf('gelatina') >= 0 ? { tipo: 'poner', material: 'gelatina', x: 27, y: 4, radio: 4 } : { tipo: 'esperar' };
      return { tipo: 'esperar' };
    },
    torpe: (api, rng, ctx) => {
      const s = (window.__arena_bot = window.__arena_bot || {});
      if (ctx.paso === 0) s.k = 0;
      const e = api.estado(), d = e.descubrimientos, u = e.desbloqueados;
      const ruido = (v, a) => Math.max(0, Math.min(159, Math.round(v + (rng() * 2 - 1) * a)));
      const r = rng();
      if (r < 0.25) return { tipo: 'esperar' };                                                    // se distrae
      if (r < 0.32) return { tipo: 'poner', material: u[Math.floor(rng() * u.length)], x: ruido(80, 80), y: 4, radio: 1 + Math.floor(rng() * 5) };    // se equivoca de material o de lugar
      const radio = 2 + Math.floor(rng() * 4);
      if (d.indexOf('montana') < 0) return { tipo: 'poner', material: 'arena', x: ruido(80, 14), y: 4, radio };
      if (d.indexOf('barro') < 0) return u.indexOf('agua') >= 0 ? { tipo: 'poner', material: 'agua', x: ruido(80, 14), y: 4, radio } : { tipo: 'esperar' };
      if (d.indexOf('estanque') < 0) {
        if (u.indexOf('piedra') < 0) return { tipo: 'esperar' };
        if (s.k < 20) { const k = s.k++; return { tipo: 'poner', material: 'piedra', x: ruido(k % 2 ? 46 : 8, 3), y: 95 - 4 * Math.floor(k / 2) + Math.round((rng() * 2 - 1) * 2), radio: 3 }; }
        return { tipo: 'poner', material: 'agua', x: ruido(27, 8), y: 4, radio };
      }
      if (d.indexOf('isla') < 0) return u.indexOf('gelatina') >= 0 ? { tipo: 'poner', material: 'gelatina', x: ruido(27, 8), y: 4, radio } : { tipo: 'esperar' };
      return { tipo: 'esperar' };
    },
  },
};
