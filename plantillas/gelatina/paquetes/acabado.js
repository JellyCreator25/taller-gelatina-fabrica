/* Pack Acabado 1.0.0 · el acabado de Guerreros Gelatina con el motor común: accesibilidad, efectos, música que se compone sola y el sello de la marca.
   Solo usa la API abierta (eventos y api.*) y los módulos del motor (GGX.a11y, GGX.fx, GGX.music, GGX.marca). Si falta alguno de los cuatro, no hace
   nada y el juego sigue igual. Con el módulo «anuncios» (opcional) también deja un corte natural para un anuncio entre batallas, pero solo se usa si el
   juego sale con un proveedor (una versión para portal): sin proveedor no cambia nada. Para quitarlo, borra «acabado» de "paquetes" y los módulos de "motor" en juego.json. */
(function () {
  'use strict';
  const gg = window.GuerrerosGelatina, GGX = window.GGX;
  if (!gg || !GGX || !GGX.a11y || !GGX.fx || !GGX.music || !GGX.marca) return;
  const $ = (id) => document.getElementById(id);
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  gg.registerPack({
    id: 'acabado', name: 'Acabado', version: '1.0.0',
    setup(g) {
      const S = g.api.state, t = (k, v) => g.t(k, v);

      /* ---- Accesibilidad: botón con «menos movimiento» y «alto contraste», y avisos para el lector de pantalla ---- */
      const donde = document.querySelector('.head-r');
      if (donde) GGX.ui.accessButton(donde);
      g.on('battle:start', () => GGX.a11y.announce(t('a11y_inicio')));
      g.on('battle:end', () => setTimeout(() => {          // el aviso de fin se arma justo después de este evento
        const ti = $('bTitle'), su = $('bSub');
        const titulo = ti ? ti.textContent : '';
        GGX.a11y.announce(titulo + (/[.!?。！？]$/.test(titulo) ? ' ' : '. ') + (su ? su.textContent : ''));
      }, 40));

      // Con «alto contraste» el bando también se distingue por la forma (círculo = azul, rombo = rojo), no solo por el color.
      const marcasDeBando = (c) => {
        for (const u of S.units) {
          if (u.dead) continue;
          const x = u.x, y = u.y + u.r * 0.6, k = 5;
          c.beginPath();
          if (u.team === 0) c.arc(x, y, k, 0, S.TAU || Math.PI * 2);
          else { c.moveTo(x, y - k - 1); c.lineTo(x + k + 1, y); c.lineTo(x, y + k + 1); c.lineTo(x - k - 1, y); c.closePath(); }
          c.fillStyle = '#ffffff'; c.fill();
          c.lineWidth = 2; c.strokeStyle = '#14251b'; c.stroke();
        }
      };

      /* ---- Efectos: chispas al caer un guerrero, confeti al ganar, textos flotantes ---- */
      let ventana = 0, chispas = 0;
      g.on('unit:die', (u) => {
        const ahora = performance.now();
        if (ahora - ventana > 120) { ventana = ahora; chispas = 0; }
        if (chispas++ >= 5) return;                         // un derrumbe de cien guerreros no debe ahogar el cuadro
        GGX.fx.burst(u.x, u.y - u.r * 0.4, { n: 7, color: ['#ffffff', '#ffd24a'], vel: 95, vida: 0.45, tam: 2.6 });
      });
      g.on('battle:start', () => { GGX.fx.clear(); GGX.fx.text(S.W / 2, S.H * 0.2, t('fx_pelea'), { color: '#ffffff', px: 36 }); });
      g.on('battle:end', (winner) => {
        if (winner === -1) return;
        const reto = S.mode === 'reto';
        if (reto && winner !== 0) return;                   // perder en Reto no se celebra
        GGX.fx.preset('confeti', S.W * 0.3, S.H * 0.28);
        GGX.fx.preset('confeti', S.W * 0.7, S.H * 0.28);
        GGX.fx.flash('#ffffff', 180, 0.22);
        if (reto) {
          GGX.fx.text(S.W / 2, S.H * 0.4, t(S.level > S.best ? 'fx_record' : 'fx_nivel', { n: GGX.num(S.level) }), { color: '#ffe66b', px: 38 });
        }
      });
      g.on('frame', (dt) => GGX.fx.update(dt));
      g.on('draw', (c, W, H) => {
        GGX.fx.draw(c, W, H);
        if (GGX.a11y.highContrast()) marcasDeBando(c);
      });

      /* ---- Música: se compone sola y se pone más intensa cuanto más reñida va la batalla ---- */
      let suena = false, intensidad = 0.25, reloj = 0;
      const arrancar = () => {
        if (suena) return;
        suena = true;
        for (const ev of ['click', 'keydown', 'pointerup', 'touchend']) window.removeEventListener(ev, arrancar, true);
        GGX.music.start({ animo: 'aventura', semilla: 1120, intensidad });
      };
      for (const ev of ['click', 'keydown', 'pointerup', 'touchend']) window.addEventListener(ev, arrancar, true);   // el navegador solo deja sonar tras un gesto
      const vida = (equipo) => {
        let hp = 0;
        for (const u of S.units) if (!u.dead && u.team === equipo) hp += u.hp;
        return clamp(hp / (S.maxTotal[equipo] || 1), 0, 1);
      };
      g.on('frame', (dt) => {
        reloj += dt;
        if (reloj < 0.25) return;
        reloj = 0;
        let i = 0.25;                                       // colocando
        if (S.phase === 'fight') i = S.paused ? 0.15 : 0.4 + 0.6 * (1 - Math.min(vida(0), vida(1)));
        if (Math.abs(i - intensidad) < 0.04) return;
        intensidad = i;
        if (suena) GGX.music.intensidad(i);
      });

      /* ---- Marca: el sello abre la primera batalla de la visita y el distintivo firma el pie de página ---- */
      const pelear = $('btnFight');
      let sellado = false;
      const hayDosBandos = () => {
        let a = 0, r = 0;
        for (const u of S.units) if (!u.dead) { if (u.team === 0) a++; else r++; }
        return a > 0 && r > 0;
      };
      const conSello = (reanudar) => { sellado = true; GGX.marca.sello({ al_terminar: reanudar }); };
      if (pelear) {
        pelear.addEventListener('click', (e) => {
          if (sellado || S.phase !== 'place' || !hayDosBandos()) return;
          e.stopImmediatePropagation(); e.preventDefault();
          conSello(() => { if (S.phase === 'place') pelear.click(); });
        }, true);
        window.addEventListener('keydown', (e) => {
          if (e.key !== 'Enter' || sellado || S.phase !== 'place' || document.activeElement !== document.body || !hayDosBandos()) return;
          e.stopImmediatePropagation(); e.preventDefault();
          conSello(() => { if (S.phase === 'place') pelear.click(); });
        }, true);
      }
      /* ---- Anuncios (módulo opcional, apagado por defecto): un corte natural entre batallas, en el cartel de resultado ---- */
      if (GGX.ads && GGX.ads.intermedio && GGX.ads.estado) {
        g.on('battle:start', () => GGX.ads.jugando(true));
        g.on('battle:end', () => GGX.ads.jugando(false));
        const cartel = $('bBtns');
        const momento = { next: 'fin_de_nivel', rematch: 'fin_de_partida', restart: 'fin_de_partida', fresh: 'fin_de_partida' };   // los botones que llevan a otra batalla; ninguno abre un menú
        let dejarPasar = false;
        if (cartel) {
          cartel.addEventListener('click', (e) => {
            const b = e.target.closest ? e.target.closest('button') : null;
            if (dejarPasar || !b || !momento[b.dataset.act] || GGX.ads.estado().proveedor === 'ninguno') return;   // sin proveedor el botón actúa como siempre
            e.stopImmediatePropagation(); e.preventDefault();
            GGX.ads.intermedio(momento[b.dataset.act], () => { dejarPasar = true; try { b.click(); } finally { dejarPasar = false; } });
          }, true);
        }
      }
      const pie = $('packs');
      if (pie && pie.parentNode) {
        const firma = document.createElement('p');
        firma.className = 'foot'; firma.id = 'firma';
        pie.parentNode.insertBefore(firma, pie.nextSibling);
        GGX.marca.distintivo(firma, { texto: true });
      }
    },
  });
})();
