/* GGX · módulo «accesible» · lo que cualquier juego necesita para poder jugarse con otras necesidades.
   Se activa con "motor": ["accesible"] en juego.json. Todo se guarda en el propio dispositivo (GGX.store), sin red.
     GGX.a11y.reducedMotion()          true si el jugador (o su sistema) pidió menos movimiento; los demás módulos lo respetan
     GGX.a11y.highContrast()           true si pidió alto contraste (la interfaz cambia sola; lo que se dibuja en canvas lo decide el juego)
     GGX.a11y.set(clave, valor)        clave: 'reducirMovimiento' | 'altoContraste'; valor: true | false | null (null = seguir al sistema)
     GGX.a11y.onChange(f)              avisa cuando cambia cualquiera de los dos
     GGX.a11y.announce(texto)          lo anuncia un lector de pantalla (región «status»); úsalo para puntaje, fin de partida, errores
     GGX.ui.accessButton(contenedor)   botón con un panel de dos casillas, con los colores de la plantilla (--ink, --surface, --line, --focus)
   Qué NO hace: no convierte por sí solo un juego de canvas en accesible para un lector de pantalla; eso depende de lo que cada juego anuncie. */
(function () {
  'use strict';
  const G = window.GGX;
  if (!G || G.a11y) return;
  const mqMov = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  const mqCon = window.matchMedia ? window.matchMedia('(prefers-contrast: more)') : null;
  const guardado = G.store.get('a11y', {}) || {};
  const bool = (v) => (typeof v === 'boolean' ? v : null);
  const ajustes = { reducirMovimiento: bool(guardado.reducirMovimiento), altoContraste: bool(guardado.altoContraste) };
  const cbs = [];
  const root = document.documentElement;
  const mov = () => (ajustes.reducirMovimiento === null ? !!(mqMov && mqMov.matches) : ajustes.reducirMovimiento);
  const con = () => (ajustes.altoContraste === null ? !!(mqCon && mqCon.matches) : ajustes.altoContraste);

  const css = document.createElement('style');
  css.id = 'ggx-a11y-css';
  css.textContent =
    'html[data-reducir-movimiento] *,html[data-reducir-movimiento] *::before,html[data-reducir-movimiento] *::after{animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important;scroll-behavior:auto!important}' +
    'html[data-alto-contraste]{--ink:#000;--surface:#fff;--line:#000;--focus:#0033cc}' +
    '.ggx-sr{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}' +
    '.ggx-a11y{position:relative;display:inline-block}' +
    '.ggx-a11y-btn{display:inline-flex;align-items:center;justify-content:center;min-width:40px;height:40px;padding:0 10px;border-radius:12px;border:1px solid var(--line,#bbb);background:var(--surface,#fff);color:var(--ink,#111);font:inherit;cursor:pointer;box-sizing:border-box}' +
    '.ggx-a11y-btn:focus-visible{outline:3px solid var(--focus,#1b5fe0);outline-offset:2px}' +
    '.ggx-a11y-panel{position:absolute;right:0;top:calc(100% + 6px);z-index:60;min-width:14em;padding:10px 12px;border-radius:12px;border:1px solid var(--line,#bbb);background:var(--surface,#fff);color:var(--ink,#111);box-shadow:0 6px 20px rgba(0,0,0,.25);display:grid;gap:8px;font-size:.9rem}' +
    '.ggx-a11y-panel[hidden]{display:none}.ggx-a11y-panel label{display:flex;align-items:center;gap:8px;cursor:pointer}' +
    '.ggx-a11y-panel input{width:18px;height:18px;accent-color:var(--focus,#1b5fe0)}';
  document.head.appendChild(css);

  function aplicar() {
    root.toggleAttribute('data-reducir-movimiento', mov());
    root.toggleAttribute('data-alto-contraste', con());
  }
  const avisar = () => cbs.forEach((f) => { try { f({ reducirMovimiento: mov(), altoContraste: con() }); } catch (e) { console.error('[GGX.a11y]', e); } });
  aplicar();

  const A = (G.a11y = { version: '1.0.0' });
  A.reducedMotion = mov;
  A.highContrast = con;
  A.get = (k) => ajustes[k];
  A.set = (k, v) => {
    if (!(k in ajustes)) return;
    ajustes[k] = bool(v);
    G.store.set('a11y', Object.assign({}, ajustes));
    aplicar(); avisar();
  };
  A.onChange = (f) => { cbs.push(f); };
  [mqMov, mqCon].forEach((m) => { if (m && m.addEventListener) m.addEventListener('change', () => { aplicar(); avisar(); }); });

  let live = null;
  function region() {
    if (live) return live;
    live = document.createElement('div');
    live.id = 'ggx-live'; live.className = 'ggx-sr';
    live.setAttribute('role', 'status'); live.setAttribute('aria-live', 'polite'); live.setAttribute('aria-atomic', 'true');
    (document.body || root).appendChild(live);
    return live;
  }
  A.announce = (texto) => {
    const el = region();
    el.textContent = '';
    setTimeout(() => { el.textContent = String(texto); }, 30);   // vaciar y volver a escribir: así el lector repite aunque el texto sea el mismo
  };

  /* Textos comunes (el juego puede sobrescribirlos en su juego.json → textos) */
  const base = {
    es: { a11y_titulo: 'Accesibilidad', a11y_reducir: 'Reducir movimiento', a11y_contraste: 'Alto contraste' },
    en: { a11y_titulo: 'Accessibility', a11y_reducir: 'Reduce motion', a11y_contraste: 'High contrast' },
    zh: { a11y_titulo: '无障碍', a11y_reducir: '减少动态效果', a11y_contraste: '高对比度' },
  };
  window.JUEGO = window.JUEGO || {};
  const textos = (window.JUEGO.textos = window.JUEGO.textos || {});   // el mismo objeto que lee GGX.t
  for (const l of Object.keys(base)) textos[l] = Object.assign({}, base[l], textos[l] || {});

  const ICONO = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="4.5" r="1.8"/><path d="M5 8.5h14"/><path d="M12 8.5v5"/><path d="m8.5 20 3.5-6.5 3.5 6.5"/></svg>';
  let n = 0;
  G.ui = G.ui || {};
  G.ui.accessButton = (parent) => {
    const id = 'ggx-a11y-' + (++n);
    const caja = document.createElement('span'); caja.className = 'ggx-a11y';
    const b = document.createElement('button'); b.type = 'button'; b.className = 'ggx-a11y-btn ggx-btn'; b.innerHTML = ICONO;
    b.setAttribute('aria-haspopup', 'true'); b.setAttribute('aria-expanded', 'false'); b.setAttribute('aria-controls', id);
    const panel = document.createElement('div'); panel.id = id; panel.className = 'ggx-a11y-panel'; panel.hidden = true; panel.setAttribute('role', 'group');
    const filas = [['reducirMovimiento', 'a11y_reducir', mov], ['altoContraste', 'a11y_contraste', con]].map(([clave, texto, leer]) => {
      const l = document.createElement('label'), i = document.createElement('input'), s = document.createElement('span');
      i.type = 'checkbox'; i.checked = leer();
      i.addEventListener('change', () => A.set(clave, i.checked));
      l.appendChild(i); l.appendChild(s); panel.appendChild(l);
      return () => { s.textContent = G.t(texto); i.checked = leer(); };
    });
    const pintar = () => { b.setAttribute('aria-label', G.t('a11y_titulo')); b.title = G.t('a11y_titulo'); panel.setAttribute('aria-label', G.t('a11y_titulo')); filas.forEach((f) => f()); };
    const abrir = (si) => { panel.hidden = !si; b.setAttribute('aria-expanded', String(si)); };
    b.addEventListener('click', () => abrir(panel.hidden));
    caja.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !panel.hidden) { abrir(false); b.focus(); } });
    document.addEventListener('pointerdown', (e) => { if (!panel.hidden && !caja.contains(e.target)) abrir(false); }, true);
    G.onLang(pintar); A.onChange(pintar); pintar();
    caja.appendChild(b); caja.appendChild(panel);
    if (parent) parent.appendChild(caja);
    return caja;
  };
})();
