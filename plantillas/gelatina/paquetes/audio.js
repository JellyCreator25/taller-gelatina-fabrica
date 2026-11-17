/* Pack Audio 1.0.0 · sonido para Guerreros Gelatina sin tocar el núcleo del juego.
   Solo usa la API abierta (eventos y acciones de api.*) y el motor común GGX. Si GGX no está, no hace nada.
   Todo suena sintetizado (WebAudio), arranca con el primer toque del jugador y se puede silenciar con el botón del encabezado. */
(function () {
  'use strict';
  const gg = window.GuerrerosGelatina, X = window.GGX;
  if (!gg || !X) return;

  gg.registerPack({
    id: 'audio', name: 'Audio', version: '1.0.0',
    setup(g) {
      const api = g.api, S = api.state;

      // Eventos de la batalla
      g.on('battle:start', () => X.sfx('horn', 0));
      g.on('battle:end', (winner) => X.sfx(winner === -1 ? 'error' : winner === 1 && S.mode === 'reto' ? 'lose' : 'win', 0));
      g.on('unit:hit', () => X.sfx('hit', 70));
      g.on('unit:die', () => X.sfx('hurt', 90));

      // Explosiones y pisotones: el núcleo los marca con una sacudida de pantalla
      let shake = 0;
      g.on('tick', () => { if (S.shake > shake + 3.5) X.sfx('boom', 120); shake = S.shake; });

      // Poderes: se envuelven las acciones de la API que usan las Leyendas
      const wrap = (name, sound, min) => {
        const f = api[name];
        if (typeof f !== 'function') return;
        api[name] = function () { X.sfx(sound, min); return f.apply(this, arguments); };
      };
      wrap('bolt', 'zap', 100);
      wrap('stone', 'land', 80);
      wrap('fear', 'whoosh', 150);
      wrap('revive', 'heal', 150);
      wrap('morph', 'merge', 80);
      wrap('heal', 'heal', 250);
      wrap('shoot', 'whoosh', 130);

      // Interfaz: colocar, borrar y botones
      const cv = document.getElementById('cv');
      if (cv) {
        const watch = (e) => {
          if (S.phase !== 'place') return;
          if (e.type === 'pointermove' && e.buttons === 0) return; // pasar el ratón por encima no cuenta
          const before = S.units.length, tool = S.tool;
          setTimeout(() => {
            const after = S.units.length;
            if (after > before) X.sfx('pop', 35);
            else if (after < before) X.sfx('click', 35);
            else if (e.type === 'pointerdown' && tool !== 'borrar') X.sfx('error', 250); // no cabe o no alcanza el oro
          }, 0);
        };
        cv.addEventListener('pointerdown', watch, true);
        cv.addEventListener('pointermove', watch, true);
      }
      document.addEventListener('click', (e) => {
        const b = e.target.closest && e.target.closest('button');
        if (!b || b.classList.contains('ggx-btn') || b.id === 'btnFight') return;
        X.sfx('click', 30);
      }, true);

      // Botón de silencio junto al selector de modo
      const where = document.querySelector('.head-r');
      if (where) X.ui.muteButton(where);
    },
  });
})();
