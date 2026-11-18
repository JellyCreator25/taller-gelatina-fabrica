/* GGX · módulo «musica» · música de fondo que se compone sola, sin archivos de audio.
   Se activa con "motor": ["musica"] en juego.json. Cada ánimo tiene su escala, su tempo y su progresión; la semilla fija la melodía, así el mismo juego
   suena igual en todos los dispositivos y cada cuatro vueltas la melodía cambia un poco para no cansar.
     GGX.music.start(animo | {animo, semilla, bpm, escala, raiz, intensidad})   empieza (llámalo desde un toque o tecla del jugador: el navegador no deja sonar antes)
     GGX.music.stop()                    la detiene
     GGX.music.intensidad(0..1)          0 = solo bajo y bombo; sube y entran la melodía, los platillos y la caja (úsalo con el peligro o el combo)
     GGX.music.estado()                  {sonando, animo, bpm, compases, notas, intensidad, silencio}  (las pruebas lo leen)
     GGX.music.plan(semilla, {animo, compases})   la partitura como datos: [{acorde, notas:[{t, midi, dur, v, voz, capa}]}] (sin sonar; reproducible)
     GGX.music.animos                    ['alegre', 'tension', 'calma', 'aventura']
   Respeta el botón de silencio del juego (GGX.muted) y se suspende con la pestaña oculta. Usa su propio AudioContext y un volumen bajo, para no tapar los efectos. */
(function () {
  'use strict';
  const G = window.GGX;
  if (!G || G.music) return;
  const ESCALAS = { 'pentatonica-mayor': [0, 2, 4, 7, 9], 'pentatonica-menor': [0, 3, 5, 7, 10], dorica: [0, 2, 3, 5, 7, 9, 10], mixolidia: [0, 2, 4, 5, 7, 9, 10] };
  const ANIMOS = {
    alegre: { escala: 'pentatonica-mayor', bpm: 112, raiz: 60 },
    tension: { escala: 'pentatonica-menor', bpm: 128, raiz: 57 },
    calma: { escala: 'dorica', bpm: 84, raiz: 55 },
    aventura: { escala: 'mixolidia', bpm: 104, raiz: 57 },
  };
  const PROGRESIONES = [[0, 4, 5, 3], [0, 5, 3, 4], [0, 3, 4, 3], [5, 3, 0, 4]];   // grados de la escala que sostienen el bajo en cada compás
  const VOLUMEN = 0.16;
  const grado = (raiz, escala, g) => { const L = escala.length, o = Math.floor(g / L), i = ((g % L) + L) % L; return raiz + 12 * o + escala[i]; };
  const hz = (m) => 440 * Math.pow(2, (m - 69) / 12);

  /* La partitura como datos: 4 tiempos por compás; t en tiempos desde el inicio del compás; capa = intensidad mínima para que suene. */
  function plan(semilla, o) {
    o = o || {};
    const a = ANIMOS[o.animo] || ANIMOS.alegre;
    const escala = ESCALAS[o.escala] || ESCALAS[a.escala];
    const raiz = o.raiz == null ? a.raiz : o.raiz;
    const rnd = G.rng(semilla == null ? 1 : semilla);
    const prog = PROGRESIONES[(rnd() * PROGRESIONES.length) | 0];
    const n = o.compases || 8;
    const compases = [];
    let g = prog[0] + escala.length;                // la melodía parte una octava arriba del primer acorde
    for (let c = 0; c < n; c++) {
      const acorde = prog[c % prog.length], notas = [];
      const base = grado(raiz - 12, escala, acorde);
      notas.push({ t: 0, midi: base, dur: 1.6, v: 0.9, voz: 'bajo', capa: 0 }, { t: 2, midi: base, dur: 1.6, v: 0.7, voz: 'bajo', capa: 0 });
      notas.push({ t: 0, midi: 0, dur: 0.2, v: 1, voz: 'bombo', capa: 0 }, { t: 2, midi: 0, dur: 0.2, v: 0.9, voz: 'bombo', capa: 0 });
      for (const t of [0.5, 1.5, 2.5, 3.5]) notas.push({ t, midi: 0, dur: 0.1, v: 0.5, voz: 'hat', capa: 0.35 });
      for (const t of [1, 3]) notas.push({ t, midi: 0, dur: 0.2, v: 0.7, voz: 'caja', capa: 0.65 });
      for (let t = 0; t < 4; t += 0.5) {             // melodía: paseo por la escala, que tiende a volver al acorde
        if (rnd() < (t % 1 === 0 ? 0.8 : 0.5)) {
          const hacia = acorde + escala.length, paso = rnd() < 0.5 ? (g < hacia ? 1 : -1) : (rnd() < 0.5 ? 1 : -1) * (1 + ((rnd() * 2) | 0));
          g = Math.max(acorde, Math.min(acorde + escala.length * 2 - 1, g + paso));
          notas.push({ t, midi: grado(raiz, escala, g), dur: t % 1 === 0 ? 0.9 : 0.45, v: 0.55 + rnd() * 0.25, voz: 'melodia', capa: 0.15 });
        }
      }
      compases.push({ acorde, notas });
    }
    return { animo: o.animo in ANIMOS ? o.animo : 'alegre', bpm: o.bpm || a.bpm, raiz, escala, compases };
  }

  const M = (G.music = { version: '1.0.0', animos: Object.keys(ANIMOS), plan });
  let ac = null, master = null, ruido = null, timer = null, voces = 0;
  let cfg = null, vuelta = 0, compas = 0, proximo = 0, intensidad = 0.5, compasesDichos = 0, notasProgramadas = 0, sonando = false, partitura = null;

  function asegurar() {
    if (ac) return true;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return false;
    try { ac = new AC(); master = ac.createGain(); master.gain.value = G.muted() ? 0 : VOLUMEN; master.connect(ac.destination); } catch (e) { ac = null; return false; }
    return true;
  }
  const despertar = () => { if (sonando && ac && ac.state === 'suspended') ac.resume().catch(() => {}); };
  ['pointerdown', 'keydown', 'touchend'].forEach((ev) => window.addEventListener(ev, despertar, { capture: true, passive: true }));
  G.onMute((m) => { if (master) master.gain.value = m ? 0 : VOLUMEN; });
  G.onHide((oculta) => { if (!ac || !sonando) return; (oculta ? ac.suspend() : ac.resume()).catch(() => {}); });

  function tono(f, t0, d, tipo, v) {
    if (voces > 24) return;
    const o = ac.createOscillator(), g = ac.createGain();
    o.type = tipo; o.frequency.setValueAtTime(f, t0);
    g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(Math.max(0.0002, v), t0 + 0.012); g.gain.exponentialRampToValueAtTime(0.0001, t0 + d);
    o.connect(g); g.connect(master); voces++; o.onended = () => { voces--; };
    o.start(t0); o.stop(t0 + d + 0.03);
  }
  function soplo(t0, d, v, hp) {
    if (voces > 24) return;
    if (!ruido) { ruido = ac.createBuffer(1, ac.sampleRate, ac.sampleRate); const x = ruido.getChannelData(0); for (let i = 0; i < x.length; i++) x[i] = Math.random() * 2 - 1; }
    const s = ac.createBufferSource(), f = ac.createBiquadFilter(), g = ac.createGain();
    s.buffer = ruido; f.type = 'highpass'; f.frequency.value = hp;
    g.gain.setValueAtTime(v, t0); g.gain.exponentialRampToValueAtTime(0.0001, t0 + d);
    s.connect(f); f.connect(g); g.connect(master); voces++; s.onended = () => { voces--; };
    s.start(t0); s.stop(t0 + d + 0.03);
  }
  function sonar(n, t0, seg) {
    const d = Math.max(0.04, n.dur * seg);
    if (n.voz === 'bajo') tono(hz(n.midi), t0, d, 'triangle', 0.5 * n.v);
    else if (n.voz === 'melodia') tono(hz(n.midi), t0, d, 'square', 0.12 * n.v);
    else if (n.voz === 'bombo') { const o = ac.createOscillator(), g = ac.createGain(); o.frequency.setValueAtTime(130, t0); o.frequency.exponentialRampToValueAtTime(45, t0 + 0.14); g.gain.setValueAtTime(0.7 * n.v, t0); g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.18); o.connect(g); g.connect(master); o.start(t0); o.stop(t0 + 0.2); }
    else if (n.voz === 'hat') soplo(t0, 0.05, 0.12 * n.v, 7000);
    else if (n.voz === 'caja') { soplo(t0, 0.14, 0.2 * n.v, 1800); tono(190, t0, 0.1, 'triangle', 0.15 * n.v); }
  }

  function programar() {                      // pone en el reloj de audio un compás completo y deja listo el siguiente
    if (!partitura || compas >= partitura.compases.length) {
      if (partitura) { compas = 0; vuelta++; }
      if (!partitura || vuelta % 4 === 0) partitura = plan((cfg.semilla || 1) + (partitura ? vuelta : 0), cfg);
    }
    const seg = 60 / cfg.bpm, c = partitura.compases[compas++];
    for (const n of c.notas) {
      if (n.capa > intensidad + 1e-9) continue;
      notasProgramadas++;
      if (!G.muted()) sonar(n, proximo + n.t * seg, seg);
    }
    compasesDichos++;
    proximo += 4 * seg;
  }
  function reloj() {
    if (!ac || !sonando) return;
    if (proximo < ac.currentTime) proximo = ac.currentTime + 0.05;
    while (proximo < ac.currentTime + 0.25) programar();
  }

  M.start = (o) => {
    o = typeof o === 'string' ? { animo: o } : o || {};
    const a = ANIMOS[o.animo] || ANIMOS.alegre;
    cfg = { animo: o.animo in ANIMOS ? o.animo : 'alegre', semilla: o.semilla == null ? 1 : o.semilla, bpm: o.bpm || a.bpm, escala: o.escala || a.escala, raiz: o.raiz == null ? a.raiz : o.raiz, compases: 8 };
    intensidad = o.intensidad == null ? 0.5 : Math.max(0, Math.min(1, o.intensidad));
    if (!asegurar()) return false;
    M.stop();
    sonando = true; partitura = null; vuelta = 0; compas = 0; proximo = ac.currentTime + 0.05;
    if (ac.state === 'suspended') ac.resume().catch(() => {});
    reloj();
    timer = setInterval(reloj, 50);
    return true;
  };
  M.stop = () => { if (timer) clearInterval(timer); timer = null; sonando = false; };
  M.intensidad = (x) => { intensidad = Math.max(0, Math.min(1, +x || 0)); };
  M.estado = () => ({ sonando, animo: cfg ? cfg.animo : null, bpm: cfg ? cfg.bpm : null, compases: compasesDichos, notas: notasProgramadas, intensidad, silencio: G.muted() });
})();
