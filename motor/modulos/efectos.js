/* GGX · módulo «efectos» · el «jugo» que hace que un golpe, un acierto o una victoria se sientan.
   Se activa con "motor": ["accesible", "efectos"] en juego.json (necesita «accesible»: con menos movimiento pedido no hay partículas, sacudidas ni destellos).
   Es un sistema de partículas y de efectos de pantalla SIN dibujo propio: el juego lo actualiza y lo dibuja en SU canvas.
     GGX.fx.burst(x, y, {n, color|[colores], vel, vida, tam, gravedad, arco:[a0,a1], forma:'circulo'|'cuadro'})   chorro de partículas; devuelve cuántas creó
     GGX.fx.preset('chispas'|'confeti'|'polvo'|'burbujas', x, y)                                                    chorros ya afinados
     GGX.fx.text(x, y, 'texto', {color, borde, px, vida, sube})                                                     texto flotante (puntos, «¡Perfecto!»)
     GGX.fx.shake(magnitud_px, ms) · GGX.fx.flash(color, ms, alfa)                                                  sacudida y destello de pantalla
     GGX.fx.update(dt_segundos)   avanza todo (llámalo una vez por cuadro) · GGX.fx.offset() → {x, y}: desplazamiento de la sacudida (aplícalo con translate)
     GGX.fx.draw(ctx, ancho, alto)   dibuja partículas, textos y destello encima del juego
     GGX.fx.count() · GGX.fx.clear() · GGX.fx.semilla(n)   cuántos efectos hay vivos · vaciar · aleatorio reproducible (pruebas)
   Con «reducir movimiento»: no hay partículas, sacudida ni destello; los textos flotantes se quedan quietos un instante. */
(function () {
  'use strict';
  const G = window.GGX;
  if (!G || G.fx) return;
  const MAX = 400;           // tope de partículas vivas: un celular modesto no debe sufrir por un chorro grande
  const P = [], T = [];
  let rnd = G.rng(20260101), sac = null, des = null, ox = 0, oy = 0;
  const quieto = () => !!(G.a11y && G.a11y.reducedMotion());
  const fx = (G.fx = { version: '1.0.0', creadas: 0, maximo: MAX });
  fx.semilla = (n) => { rnd = G.rng(n); };
  fx.quieto = quieto;

  fx.burst = (x, y, o) => {
    if (quieto()) return 0;
    o = o || {};
    const n = Math.max(0, Math.min(o.n == null ? 12 : o.n | 0, MAX - P.length));
    const cols = Array.isArray(o.color) && o.color.length ? o.color : [o.color || '#ffffff'];
    for (let i = 0; i < n; i++) {
      const a = o.arco ? o.arco[0] + rnd() * (o.arco[1] - o.arco[0]) : rnd() * Math.PI * 2;
      const v = (o.vel == null ? 120 : o.vel) * (0.4 + rnd() * 0.8);
      P.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, g: o.gravedad == null ? 260 : o.gravedad, vida: (o.vida || 0.7) * (0.7 + rnd() * 0.6), t: 0,
        r: (o.tam || 4) * (0.6 + rnd() * 0.8), c: cols[(rnd() * cols.length) | 0], forma: o.forma || 'circulo', giro: (rnd() - 0.5) * 8, ang: rnd() * 6.28 });
    }
    fx.creadas += n;
    return n;
  };
  fx.text = (x, y, texto, o) => {
    o = o || {};
    const q = quieto();
    T.push({ x, y, s: String(texto), vida: q ? 0.6 : o.vida || 0.9, t: 0, c: o.color || '#ffffff', borde: o.borde || 'rgba(0,0,0,.45)', px: o.px || 18, sube: q ? 0 : o.sube == null ? 40 : o.sube });
    if (T.length > 40) T.shift();
  };
  fx.shake = (mag, ms) => {
    if (quieto()) return;
    const m = Math.max(0, +mag || 0);
    sac = { mag: sac ? Math.max(m, sac.mag * (1 - sac.t / sac.dur)) : m, t: 0, dur: Math.max(0.05, (ms || 250) / 1000) };
  };
  fx.flash = (color, ms, alfa) => {
    if (quieto()) return;
    des = { c: color || '#ffffff', t: 0, dur: Math.max(0.03, (ms || 160) / 1000), a: alfa == null ? 0.5 : alfa };
  };
  fx.update = (dt) => {
    dt = Math.min(Math.max(dt || 0, 0), 0.05);   // un cuadro perdido no debe lanzar las partículas al otro lado de la pantalla
    for (let i = P.length - 1; i >= 0; i--) {
      const p = P[i];
      p.t += dt;
      if (p.t >= p.vida) { P[i] = P[P.length - 1]; P.pop(); continue; }
      p.vy += p.g * dt; p.x += p.vx * dt; p.y += p.vy * dt; p.ang += p.giro * dt;
    }
    for (let i = T.length - 1; i >= 0; i--) { T[i].t += dt; if (T[i].t >= T[i].vida) T.splice(i, 1); }
    if (sac) {
      sac.t += dt;
      if (sac.t >= sac.dur) { sac = null; ox = oy = 0; } else { const k = sac.mag * (1 - sac.t / sac.dur); ox = (rnd() * 2 - 1) * k; oy = (rnd() * 2 - 1) * k; }
    }
    if (des) { des.t += dt; if (des.t >= des.dur) des = null; }
  };
  fx.offset = () => ({ x: ox, y: oy });
  fx.draw = (c, w, h) => {
    c.save();
    for (const p of P) {
      c.globalAlpha = Math.max(0, 1 - p.t / p.vida);
      c.fillStyle = p.c;
      if (p.forma === 'cuadro') { c.save(); c.translate(p.x, p.y); c.rotate(p.ang); c.fillRect(-p.r, -p.r, p.r * 2, p.r * 1.2); c.restore(); }
      else { c.beginPath(); c.arc(p.x, p.y, p.r, 0, Math.PI * 2); c.fill(); }
    }
    c.textAlign = 'center'; c.textBaseline = 'middle'; c.lineJoin = 'round';
    for (const t of T) {
      const k = t.t / t.vida;
      c.globalAlpha = k < 0.7 ? 1 : Math.max(0, 1 - (k - 0.7) / 0.3);
      c.font = '700 ' + t.px + 'px Fredoka, "Nunito Sans", ' + G.cjk + ', sans-serif';
      const y = t.y - t.sube * k;
      c.lineWidth = Math.max(3, t.px / 5); c.strokeStyle = t.borde; c.strokeText(t.s, t.x, y);
      c.fillStyle = t.c; c.fillText(t.s, t.x, y);
    }
    if (des && w && h) { c.globalAlpha = des.a * (1 - des.t / des.dur); c.fillStyle = des.c; c.fillRect(0, 0, w, h); }
    c.restore();
  };
  fx.count = () => P.length + T.length;
  fx.clear = () => { P.length = 0; T.length = 0; sac = null; des = null; ox = oy = 0; };
  fx.presets = ['chispas', 'confeti', 'polvo', 'burbujas'];
  fx.preset = (nombre, x, y) => {
    switch (nombre) {
      case 'chispas': return fx.burst(x, y, { n: 14, color: ['#ffffff', '#ffe66b'], vel: 180, vida: 0.5, tam: 3 });
      case 'confeti': return fx.burst(x, y, { n: 40, color: ['#5ad1ff', '#ff6bd6', '#ffe66b', '#6bff95', '#ff6b6b'], vel: 260, vida: 1.1, tam: 4, gravedad: 380, arco: [-Math.PI * 0.95, -Math.PI * 0.05], forma: 'cuadro' });
      case 'polvo': return fx.burst(x, y, { n: 8, color: 'rgba(255,255,255,.7)', vel: 50, vida: 0.6, tam: 5, gravedad: -20 });
      case 'burbujas': return fx.burst(x, y, { n: 10, color: 'rgba(255,255,255,.65)', vel: 40, vida: 1.2, tam: 5, gravedad: -80, arco: [-Math.PI * 0.8, -Math.PI * 0.2] });
      default: return 0;
    }
  };
})();
