/* GGX · motor común de la fábrica de juegos.
   Todo es opcional: cada plantilla usa lo que necesite. Sin red, sin analítica, sin cookies.
   Lo que ofrece:
     GGX.cfg                      configuración del juego (id, version, idiomas, apoyo_url…) que inyecta la fábrica
     GGX.store.get/set            localStorage con prefijo del juego y respaldo en memoria
     GGX.t(clave, vars) · lang · langs · setLang · onLang     textos por idioma (vienen de juego.json → textos); si falta la clave
                                  en el idioma actual se usa inglés, luego el primer idioma del juego y por último la clave
     GGX.num(n) · langName(l) · langTag(l) · locale() · cjk      número en el formato del idioma · nombre del idioma en su propio idioma ·
                                  etiqueta para el atributo lang de la página (chino → zh-Hans) · locale de Intl · familias tipográficas para chino
                                  El idioma sale de ?lang=xx en la dirección, del último que eligió el jugador o de los del navegador
     GGX.sfx(nombre) · muted() · setMuted(b) · onMute(f)      efectos de sonido sintetizados (WebAudio, sin archivos)
     GGX.onHide(f)                avisa cuando la pestaña se oculta o vuelve (para pausar)
     GGX.ui.muteButton/langButton/supportLink(contenedor)     botones listos, hechos con las variables de color de la plantilla
     GGX.ads                      adaptador de anuncios; por defecto no hace nada (aquí se enchufaría el SDK de un portal)
     GGX.link(url) · GGX.apoyo()  abrir un enlace externo / la página de apoyo del juego
     GGX.rng(semilla)             aleatorio reproducible (pruebas y retos diarios)
     GGX.draw.jelly(...)          la gelatina de la casa, para que todos los juegos compartan identidad */
(function () {
  'use strict';
  const cfg = window.GGX_CONFIG || {};
  const G = (window.GGX = { version: '1.1.0', cfg });
  const cbs = { lang: [], mute: [], hide: [] };
  const fire = (name, ...a) => cbs[name].forEach((f) => { try { f(...a); } catch (e) { console.error('[GGX]', e); } });

  /* ---------- Almacenamiento ---------- */
  const mem = {};
  const key = (k) => (cfg.id || 'ggx') + ':' + k;
  G.store = {
    get(k, d) {
      try { const v = localStorage.getItem(key(k)); if (v !== null) return JSON.parse(v); } catch (e) { /* sin acceso o dato dañado */ }
      return k in mem ? mem[k] : d;
    },
    set(k, v) { mem[k] = v; try { localStorage.setItem(key(k), JSON.stringify(v)); } catch (e) { /* opcional */ } },
  };

  /* ---------- Idiomas ---------- */
  const dict = (window.JUEGO && window.JUEGO.textos) || {};
  const langs = Array.isArray(cfg.idiomas) && cfg.idiomas.length ? cfg.idiomas : ['es'];
  G.langs = langs;
  const NOMBRES = { es: 'Español', en: 'English', zh: '中文', pt: 'Português', hi: 'हिन्दी', fr: 'Français', de: 'Deutsch', ru: 'Русский', ja: '日本語', ar: 'العربية' };
  const ETIQUETA = { zh: 'zh-Hans' };   // lo que va en el atributo lang de la página: en chino decide qué forma tienen los caracteres (simplificada)
  const LOCALE = { es: 'es-MX', en: 'en-US', zh: 'zh-CN', pt: 'pt-BR', hi: 'hi-IN', fr: 'fr-FR', de: 'de-DE', ru: 'ru-RU', ja: 'ja-JP', ar: 'ar' };
  // El chino usa las tipografías del sistema (todo dispositivo configurado en chino las trae); el orden pone primero las de cada plataforma.
  G.cjk = '"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC","Noto Sans SC","WenQuanYi Micro Hei"';
  G.langName = (l) => NOMBRES[l] || String(l).toUpperCase();
  G.langTag = (l) => ETIQUETA[l] || l;
  G.locale = () => LOCALE[G.lang] || G.lang;
  G.num = (n, o) => { try { return new Intl.NumberFormat(G.locale(), o).format(n); } catch (e) { return String(n); } };
  (function pick() {
    let forced = null;
    try { forced = new URLSearchParams(location.search).get('lang'); } catch (e) { /* sin dirección */ }
    const saved = G.store.get('lang', null);
    const prefs = (navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language]).map((x) => String(x || '').slice(0, 2).toLowerCase());
    G.lang = langs.includes(forced) ? forced : saved && langs.includes(saved) ? saved
      : prefs.find((p) => langs.includes(p)) || (langs.includes('en') ? 'en' : langs[0]);
    document.documentElement.lang = G.langTag(G.lang);
  })();
  G.t = (k, vars) => {
    let s = k;
    for (const l of [G.lang, 'en', langs[0]]) if (dict[l] && dict[l][k] != null) { s = dict[l][k]; break; }
    if (vars) s = String(s).replace(/\{(\w+)\}/g, (m, n) => (n in vars ? vars[n] : m));
    return s;
  };
  G.setLang = (l) => {
    if (!langs.includes(l) || l === G.lang) return;
    G.lang = l; G.store.set('lang', l); document.documentElement.lang = G.langTag(l); fire('lang', l);
  };
  G.onLang = (f) => { cbs.lang.push(f); };

  /* ---------- Sonido: todo sintetizado, se activa con el primer gesto del jugador ---------- */
  let ctx = null, master = null, muted = !!G.store.get('mute', false), armed = false, voices = 0, nbuf = null, pitch = 1;
  function arm() {
    if (armed) return;
    armed = true;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    try { ctx = new AC(); master = ctx.createGain(); master.gain.value = muted ? 0 : 0.5; master.connect(ctx.destination); } catch (e) { ctx = null; }
  }
  const wake = () => { arm(); if (ctx && ctx.state === 'suspended') ctx.resume().catch(() => {}); };
  ['pointerdown', 'keydown', 'touchend'].forEach((ev) => window.addEventListener(ev, wake, { capture: true, passive: true }));

  function tone(o) {
    if (!ctx || muted || voices > 14) return;
    const t0 = ctx.currentTime + (o.at || 0), d = o.d || 0.1;
    const osc = ctx.createOscillator(), g = ctx.createGain();
    osc.type = o.type || 'sine';
    osc.frequency.setValueAtTime(o.f * pitch, t0);
    if (o.f2) osc.frequency.exponentialRampToValueAtTime(Math.max(20, o.f2 * pitch), t0 + d);
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(o.v || 0.2, t0 + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + d);
    osc.connect(g); g.connect(master);
    voices++; osc.onended = () => { voices--; };
    osc.start(t0); osc.stop(t0 + d + 0.03);
  }
  function noise(o) {
    if (!ctx || muted || voices > 14) return;
    if (!nbuf) {
      nbuf = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
      const a = nbuf.getChannelData(0);
      for (let i = 0; i < a.length; i++) a[i] = Math.random() * 2 - 1;
    }
    const t0 = ctx.currentTime + (o.at || 0), d = o.d || 0.1;
    const src = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
    src.buffer = nbuf;
    f.type = o.hp ? 'highpass' : 'lowpass';
    f.frequency.setValueAtTime(o.hp || o.lp || 1500, t0);
    if (o.to) f.frequency.exponentialRampToValueAtTime(o.to, t0 + d);
    g.gain.setValueAtTime(o.v || 0.2, t0);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + d);
    src.connect(f); f.connect(g); g.connect(master);
    voices++; src.onended = () => { voices--; };
    src.start(t0); src.stop(t0 + d + 0.03);
  }
  const SFX = {
    click: () => tone({ f: 520, f2: 380, d: 0.06, type: 'triangle', v: 0.16 }),
    pop: () => tone({ f: 300, f2: 760, d: 0.09, type: 'sine', v: 0.24 }),
    jump: () => tone({ f: 260, f2: 640, d: 0.15, type: 'square', v: 0.1 }),
    land: () => { noise({ d: 0.07, v: 0.16, lp: 600 }); tone({ f: 140, f2: 80, d: 0.08, type: 'sine', v: 0.2 }); },
    coin: () => { tone({ f: 880, d: 0.07, type: 'square', v: 0.1 }); tone({ f: 1320, d: 0.15, type: 'square', v: 0.1, at: 0.07 }); },
    hit: () => { noise({ d: 0.08, v: 0.22, lp: 1800 }); tone({ f: 190, f2: 90, d: 0.09, type: 'sawtooth', v: 0.1 }); },
    hurt: () => tone({ f: 330, f2: 110, d: 0.22, type: 'sawtooth', v: 0.16 }),
    boom: () => { noise({ d: 0.5, v: 0.45, lp: 900, to: 120 }); tone({ f: 120, f2: 38, d: 0.45, type: 'sine', v: 0.4 }); },
    zap: () => { tone({ f: 1700, f2: 180, d: 0.28, type: 'sawtooth', v: 0.1 }); noise({ d: 0.22, v: 0.14, hp: 2500 }); },
    heal: () => { tone({ f: 600, f2: 900, d: 0.18, type: 'sine', v: 0.16 }); tone({ f: 900, f2: 1200, d: 0.2, type: 'sine', v: 0.12, at: 0.1 }); },
    whoosh: () => noise({ d: 0.28, v: 0.18, hp: 400, to: 3000 }),
    horn: () => { tone({ f: 196, d: 0.35, type: 'sawtooth', v: 0.1 }); tone({ f: 294, d: 0.35, type: 'sawtooth', v: 0.08, at: 0.02 }); tone({ f: 392, d: 0.5, type: 'sawtooth', v: 0.08, at: 0.3 }); },
    merge: () => { tone({ f: 440, f2: 660, d: 0.12, type: 'triangle', v: 0.2 }); tone({ f: 660, f2: 990, d: 0.16, type: 'triangle', v: 0.16, at: 0.08 }); },
    error: () => tone({ f: 160, d: 0.14, type: 'square', v: 0.1 }),
    win: () => [523, 659, 784, 1047].forEach((f, i) => tone({ f, d: 0.2, type: 'triangle', v: 0.2, at: i * 0.12 })),
    lose: () => [392, 330, 262, 196].forEach((f, i) => tone({ f, d: 0.24, type: 'sawtooth', v: 0.12, at: i * 0.16 })),
  };
  const last = {};
  G.sfx = (name, minMs, rate) => {   // rate: multiplicador de tono (1 = normal; sube 6 % por semitono)
    const f = SFX[name];
    if (!f || !ctx || muted) return;
    const now = performance.now();
    if (now - (last[name] || -1e9) < (minMs == null ? 45 : minMs)) return;
    last[name] = now;
    G.sfx.plays[name] = (G.sfx.plays[name] || 0) + 1;   // las pruebas lo leen para comprobar que el sonido sí se disparó
    pitch = rate || 1;
    try { f(); } catch (e) { /* un sonido nunca rompe el juego */ }
    pitch = 1;
  };
  G.sfx.names = Object.keys(SFX);
  G.sfx.plays = {};
  G.muted = () => muted;
  G.setMuted = (m) => {
    muted = !!m; G.store.set('mute', muted);
    if (master) master.gain.value = muted ? 0 : 0.5;
    fire('mute', muted);
  };
  G.onMute = (f) => { cbs.mute.push(f); };

  /* ---------- Pestaña oculta: pausar y callar ---------- */
  document.addEventListener('visibilitychange', () => {
    if (ctx) { if (document.hidden) ctx.suspend().catch(() => {}); else ctx.resume().catch(() => {}); }
    fire('hide', document.hidden);
  });
  G.onHide = (f) => { cbs.hide.push(f); };

  /* ---------- Anuncios: sin SDK no pasa nada. Un portal se enchufa con GGX.ads.use({ interstitial(), rewarded() }) ---------- */
  G.ads = {
    adapter: null,
    use(a) { this.adapter = a; },
    interstitial() { const a = this.adapter; return a && a.interstitial ? Promise.resolve().then(() => a.interstitial()).catch(() => {}) : Promise.resolve(); },
    rewarded() { const a = this.adapter; return a && a.rewarded ? Promise.resolve().then(() => a.rewarded()).then(Boolean).catch(() => false) : Promise.resolve(false); },
  };

  /* ---------- Enlaces ---------- */
  G.link = (url) => { try { window.open(url, '_blank', 'noopener'); } catch (e) { /* el marco puede no permitirlo */ } };
  G.apoyo = () => { if (cfg.apoyo_url) G.link(cfg.apoyo_url); };

  /* ---------- Aleatorio reproducible (mulberry32) ---------- */
  G.rng = (seed) => {
    let a = (seed >>> 0) || 1;
    return () => { a = (a + 0x6d2b79f5) >>> 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  };

  /* ---------- Botones de la casa (heredan las variables de color de la plantilla) ---------- */
  const ICON_ON = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/></svg>';
  const ICON_OFF = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="m16 9 5 6"/><path d="m21 9-5 6"/></svg>';
  let styled = false;
  function style() {
    if (styled) return; styled = true;
    const s = document.createElement('style');
    s.textContent = '.ggx-btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-width:40px;height:40px;padding:0 12px;border-radius:12px;' +
      'border:1px solid var(--line,#bbb);background:var(--surface,#fff);color:var(--ink,#111);font:inherit;font-weight:700;font-size:.85rem;cursor:pointer;text-decoration:none;box-sizing:border-box}' +
      '.ggx-btn:hover{filter:brightness(.97)}.ggx-btn:focus-visible{outline:3px solid var(--focus,#1b5fe0);outline-offset:2px}' +
      '.ggx-lang{padding:0 6px;max-width:9em;appearance:auto;-webkit-appearance:menulist}';
    document.head.appendChild(s);
  }
  G.ui = {
    muteButton(parent) {
      style();
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'ggx-btn';
      const paint = () => { b.innerHTML = muted ? ICON_OFF : ICON_ON; b.setAttribute('aria-pressed', String(muted)); b.setAttribute('aria-label', G.t(muted ? 'sonido_activar' : 'sonido_silenciar')); b.title = b.getAttribute('aria-label'); };
      b.addEventListener('click', () => { wake(); G.setMuted(!muted); if (!muted) G.sfx('click', 0); });
      G.onMute(paint); G.onLang(paint); paint();
      if (parent) parent.appendChild(b);
      return b;
    },
    langButton(parent) {   // selector nativo: sirve igual con 2 que con 10 idiomas, y cada uno aparece con su propio nombre
      if (langs.length < 2) return null;
      style();
      const s = document.createElement('select');
      s.className = 'ggx-btn ggx-lang';
      for (const l of langs) { const o = document.createElement('option'); o.value = l; o.textContent = G.langName(l); o.lang = G.langTag(l); s.appendChild(o); }
      const paint = () => { s.value = G.lang; s.setAttribute('aria-label', G.t('idioma_cambiar')); s.title = s.getAttribute('aria-label'); };
      s.addEventListener('change', () => G.setLang(s.value));
      G.onLang(paint); paint();
      if (parent) parent.appendChild(s);
      return s;
    },
    supportLink(parent) {
      if (!cfg.apoyo_url) return null;
      style();
      const a = document.createElement('a');
      a.className = 'ggx-btn'; a.href = cfg.apoyo_url; a.target = '_blank'; a.rel = 'noopener noreferrer';
      const paint = () => { a.textContent = G.t('apoyar'); };
      G.onLang(paint); paint();
      if (parent) parent.appendChild(a);
      return a;
    },
  };

  /* Textos comunes que todo juego tiene (el juego puede sobrescribirlos en su juego.json) */
  const base = {
    es: { sonido_silenciar: 'Silenciar sonido', sonido_activar: 'Activar sonido', idioma_cambiar: 'Cambiar idioma', apoyar: 'Apoyar el juego' },
    en: { sonido_silenciar: 'Mute sound', sonido_activar: 'Unmute sound', idioma_cambiar: 'Change language', apoyar: 'Support the game' },
    zh: { sonido_silenciar: '静音', sonido_activar: '开启声音', idioma_cambiar: '切换语言', apoyar: '支持游戏' },
  };
  for (const l of Object.keys(base)) dict[l] = Object.assign({}, base[l], dict[l] || {});

  /* ---------- La gelatina de la casa ---------- */
  G.draw = {
    // o: sx, sy (aplastado/estirado), look (-1..1 hacia dónde mira), blink (bool), shine (bool, por defecto sí)
    jelly(c, x, y, r, col, o) {
      o = o || {};
      c.save(); c.translate(x, y); c.scale(o.sx || 1, o.sy || 1);
      c.fillStyle = col;
      c.beginPath();
      c.moveTo(-r, r * 0.55);
      c.bezierCurveTo(-r * 1.08, -r * 1.3, r * 1.08, -r * 1.3, r, r * 0.55);
      c.quadraticCurveTo(0, r * 0.98, -r, r * 0.55);
      c.closePath(); c.fill();
      if (o.shine !== false) {
        c.fillStyle = 'rgba(255,255,255,0.35)';
        c.beginPath(); c.ellipse(-r * 0.4, -r * 0.5, r * 0.24, r * 0.12, -0.5, 0, Math.PI * 2); c.fill();
      }
      const ex = r * 0.34, ey = -r * 0.08, er = r * 0.2, look = (o.look || 0) * er * 0.35;
      for (const s of [-1, 1]) {
        c.fillStyle = '#fff'; c.beginPath(); c.ellipse(s * ex, ey, er, er * (o.blink ? 0.12 : 1.15), 0, 0, Math.PI * 2); c.fill();
        if (!o.blink) { c.fillStyle = '#14251b'; c.beginPath(); c.arc(s * ex + look, ey + er * 0.1, er * 0.5, 0, Math.PI * 2); c.fill(); }
      }
      c.restore();
    },
  };
})();
