/* GGX · módulo «marca» · la Gelatina como insignia del Taller: el sello que abre cada juego, su sonido y su distintivo.
   Se activa con "motor": [..., "marca"] en juego.json (ver marca/guia.md para la idea y las reglas de uso).
     GGX.marca.sello({al_terminar, forzar})   la Gelatina cae, se aplasta y saluda con su nombre y su «blup» (≈1,4 s); un toque o una tecla lo salta.
                                              Úsalo cuando el jugador pulsa «Jugar» (el navegador solo deja sonar después de un gesto). Una vez por visita,
                                              salvo forzar:true. Devuelve una promesa con {omitido, saltado}; al_terminar corre en todos los casos.
     GGX.marca.blup()                         el sonido de marca solo (respeta el silencio del juego)
     GGX.marca.distintivo(contenedor, {texto})  el emblema chico (y, con texto:true, el nombre) para una esquina; no es un enlace ni pide nada
     GGX.marca.emblema(px, color)             elemento con el emblema ('verde' | 'rosa' | 'amarilla') · GGX.marca.svg(id) · GGX.marca.nombre
     GGX.marca.estado()                       {sellos, blups, ultimo}  (las pruebas lo leen)
   Con «reducir movimiento» el sello no se anima: se muestra quieto un instante. Es decorativo: no atrapa el foco ni oculta nada al lector de pantalla. */
(function () {
  'use strict';
  const G = window.GGX;
  if (!G || G.marca) return;
  const NOMBRE = 'Taller Gelatina';
  const EMBLEMAS = {   // el mismo dibujo que herramientas/marca.py (una prueba lo verifica); {id} evita que dos emblemas compartan el degradado
    verde: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='-118 -98 236 208' role='img' aria-label='Taller Gelatina'><defs><linearGradient id='g{id}' x1='0' y1='-1' x2='0' y2='1'><stop offset='0' stop-color='#6fe0a6'/><stop offset='1' stop-color='#15804f'/></linearGradient></defs><path d='M-102 62 C-114 -22 -72 -92 0 -92 C72 -92 114 -22 102 62 C99 88 70 102 0 102 C-70 102 -99 88 -102 62 Z' fill='url(#g{id})'/><path d='M-102 62 C-99 88 -70 102 0 102 C70 102 99 88 102 62 C80 80 -80 80 -102 62 Z' fill='#14251b' opacity='.10'/><ellipse cx='-48' cy='-50' rx='30' ry='14' transform='rotate(-35 -48 -50)' fill='#fff' opacity='.55'/><circle cx='-80' cy='-6' r='5' fill='#fff' opacity='.5'/><ellipse cx='-33' cy='6' rx='16' ry='19' fill='#fff'/><ellipse cx='33' cy='6' rx='16' ry='19' fill='#fff'/><circle cx='-30' cy='10' r='9' fill='#14251b'/><circle cx='36' cy='10' r='9' fill='#14251b'/><circle cx='-27' cy='6' r='3' fill='#fff'/><circle cx='39' cy='6' r='3' fill='#fff'/><ellipse cx='-58' cy='38' rx='11' ry='7' fill='#ffc2d8' opacity='.8'/><ellipse cx='58' cy='38' rx='11' ry='7' fill='#ffc2d8' opacity='.8'/><path d='M-15 42 Q0 56 15 42' fill='none' stroke='#14251b' stroke-width='5' stroke-linecap='round'/></svg>",
    colores: { rosa: ['#ff9cc4', '#c2337a', '#ff6f9f'], amarilla: ['#ffd36b', '#e39a00', '#ff9f80'] },
  };
  let contador = 0;
  const svg = (id, color) => {
    let t = EMBLEMAS.verde.split('{id}').join(id || 'm' + (++contador));
    const c = EMBLEMAS.colores[color];
    if (c) t = t.split('#6fe0a6').join(c[0]).split('#15804f').join(c[1]).split('#ffc2d8').join(c[2]);
    return t;
  };

  const M = (G.marca = { version: '1.0.0', nombre: NOMBRE, svg });
  const est = { sellos: 0, blups: 0, ultimo: null };
  const quieto = () => !!(G.a11y && G.a11y.reducedMotion());

  M.emblema = (px, color) => {
    const e = document.createElement('span');
    e.style.cssText = 'display:inline-block;line-height:0;width:' + (px || 48) + 'px';
    e.innerHTML = svg(null, color);
    return e;
  };
  M.estado = () => Object.assign({}, est);

  /* El «blup»: dos gotas de tono, una sube y otra se asienta. Su propio AudioContext, volumen bajo. */
  let ac = null;
  M.blup = () => {
    if (G.muted()) return false;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return false;
    try {
      if (!ac) ac = new AC();
      if (ac.state === 'suspended') ac.resume().catch(() => {});
      const t0 = ac.currentTime + 0.01;
      [[300, 640, 0.1, 'triangle', 0.2, 0], [640, 380, 0.16, 'sine', 0.16, 0.09]].forEach(([f, f2, d, tipo, v, at]) => {
        const o = ac.createOscillator(), g = ac.createGain();
        o.type = tipo; o.frequency.setValueAtTime(f, t0 + at); o.frequency.exponentialRampToValueAtTime(f2, t0 + at + d);
        g.gain.setValueAtTime(0.0001, t0 + at); g.gain.exponentialRampToValueAtTime(v, t0 + at + 0.012); g.gain.exponentialRampToValueAtTime(0.0001, t0 + at + d);
        o.connect(g); g.connect(ac.destination); o.start(t0 + at); o.stop(t0 + at + d + 0.03);
      });
      est.blups++;
      return true;
    } catch (e) { return false; }
  };

  let estilo = null, visto = false;
  const ponerEstilo = () => {
    if (estilo) return;
    estilo = document.createElement('style');
    estilo.id = 'ggx-marca-css';
    estilo.textContent =
      '.ggx-sello{position:fixed;inset:0;z-index:100000;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;cursor:pointer;' +
      'background:radial-gradient(circle at 30% 25%,#fff6fa 0%,#fbf8f1 45%,#f3d6e4 100%);color:#c2337a;font:700 1.7rem/1.1 Fredoka,"Nunito Sans",' + G.cjk + ',sans-serif;opacity:1;transition:opacity .25s}' +
      '.ggx-sello.fuera{opacity:0}.ggx-sello .gel{width:min(34vmin,170px);transform-origin:50% 100%;animation:ggx-cae .9s cubic-bezier(.3,.7,.4,1) both}' +
      '.ggx-sello .nom{opacity:0;animation:ggx-nombre .5s .55s ease-out both;letter-spacing:-.5px}' +
      '.ggx-sello[data-quieto] .gel,.ggx-sello[data-quieto] .nom{animation:none;opacity:1}' +
      '@keyframes ggx-cae{0%{transform:translateY(-60vh) scale(.9,1.1)}45%{transform:translateY(0) scale(1.28,.7)}62%{transform:translateY(-14%) scale(.92,1.1)}80%{transform:translateY(0) scale(1.08,.92)}100%{transform:none}}' +
      '@keyframes ggx-nombre{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}' +
      '.ggx-marca-d{display:inline-flex;align-items:center;gap:6px;color:var(--ink,#111);opacity:.8;font:700 .75rem/1 Fredoka,"Nunito Sans",' + G.cjk + ',sans-serif}' +
      '.ggx-marca-d svg{width:26px;height:auto;display:block}';
    document.head.appendChild(estilo);
  };

  M.sello = (o) => {
    o = o || {};
    const fin = (r) => { try { if (o.al_terminar) o.al_terminar(r); } catch (e) { console.error('[GGX.marca]', e); } return r; };
    let guardado = false;
    try { guardado = sessionStorage.getItem('ggx-sello') === '1'; } catch (e) { /* sin almacenamiento de sesión */ }
    if ((visto || guardado) && !o.forzar) { est.ultimo = 'omitido'; return Promise.resolve(fin({ omitido: true, saltado: false })); }
    visto = true;
    try { sessionStorage.setItem('ggx-sello', '1'); } catch (e) { /* opcional */ }
    ponerEstilo();
    est.sellos++;
    const q = quieto();
    const el = document.createElement('div');
    el.className = 'ggx-sello'; el.setAttribute('aria-hidden', 'true');
    if (q) el.setAttribute('data-quieto', '');
    const gel = document.createElement('div'); gel.className = 'gel'; gel.innerHTML = svg(null);
    const nom = document.createElement('div'); nom.className = 'nom'; nom.textContent = NOMBRE;
    el.appendChild(gel); el.appendChild(nom);
    document.body.appendChild(el);
    if (!q) setTimeout(M.blup, 380); else M.blup();      // el «blup» cae justo con el aplastón
    return new Promise((resolve) => {
      let listo = false;
      const terminar = (saltado) => {
        if (listo) return; listo = true;
        window.removeEventListener('keydown', tecla, true); el.removeEventListener('pointerdown', toque);
        est.ultimo = saltado ? 'saltado' : q ? 'estatico' : 'completo';
        el.classList.add('fuera');
        setTimeout(() => { if (el.parentNode) el.parentNode.removeChild(el); }, 260);
        resolve(fin({ omitido: false, saltado }));
      };
      const toque = () => terminar(true), tecla = () => terminar(true);
      el.addEventListener('pointerdown', toque); window.addEventListener('keydown', tecla, true);
      setTimeout(() => terminar(false), q ? 700 : 1400);
    });
  };

  M.distintivo = (parent, o) => {
    ponerEstilo();
    const d = document.createElement('span');
    d.className = 'ggx-marca-d'; d.setAttribute('role', 'img'); d.setAttribute('aria-label', NOMBRE);
    d.innerHTML = svg(null);
    d.querySelector('svg').removeAttribute('role'); d.querySelector('svg').removeAttribute('aria-label'); d.querySelector('svg').setAttribute('aria-hidden', 'true');
    if (o && o.texto) { const t = document.createElement('span'); t.textContent = NOMBRE; t.setAttribute('aria-hidden', 'true'); d.appendChild(t); }
    if (parent) parent.appendChild(d);
    return d;
  };
})();
