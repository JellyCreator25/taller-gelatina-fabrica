/* GGX · módulo «anuncios» · puntos de anuncio que respetan al jugador. Apagado por defecto: sin proveedor no carga nada y no toca la red.
   Se activa con "motor": [..., "anuncios"] en juego.json; el proveedor lo decide la fábrica al construir (monetizacion/politica.json), no el juego.
     GGX.ads.intermedio(momento, al_terminar)   anuncio de pantalla completa en un corte natural. momento: 'fin_de_partida' | 'fin_de_nivel' | 'pausa_larga'.
                                                al_terminar corre SIEMPRE, una sola vez, haya o no anuncio (sin proveedor, antes de la primera interacción,
                                                en un menú, o si el anuncio falla): el juego sigue igual. Devuelve true si pidió un anuncio.
     GGX.ads.recompensa(motivo, {ok, no})       anuncio que el jugador elige ver a cambio de algo. ok() solo si lo vio completo; no(motivo) si no hay
                                                anuncio, lo descartó, falló o hay bloqueador. Nunca premia sin anuncio visto.
     GGX.ads.recompensaDisponible()             true si hay proveedor listo: el juego muestra el botón de recompensa solo entonces (un botón sin efecto no se permite).
     GGX.ads.jugando(true|false)                avisa a los portales que empezó o paró el juego activo (sin repetir dos veces lo mismo seguido).
     GGX.ads.alPausar(f) · GGX.ads.alReanudar(f)   el juego detiene y retoma su bucle mientras dura un anuncio.
     GGX.ads.configurar({proveedor, publicador, sdk_url, reglas, sdk:false, prueba})  lo llama la fábrica con GGX_CONFIG.anuncios; sdk:false = el SDK ya está en la página.
     GGX.ads.estado()                           {proveedor, listo, pedidos, mostrados, rechazados, recompensas, ultimo, ultimoRechazo} (las pruebas lo leen)
   Reglas que el módulo hace cumplir (vienen de las políticas de AdSense, CrazyGames y Poki; ver monetizacion/ESTRATEGIA.md):
     · nunca durante la partida ni en menús, ajustes o tienda; solo en los momentos permitidos y después de una interacción del jugador;
     · el juego se pausa y el sonido se silencia solo mientras el anuncio suena (y vuelve a como estaba); el lector de pantalla recibe un aviso;
     · con AdSense (o sin proveedor) hay espera inicial, separación entre anuncios y tope por visita; con un portal NO hay temporizadores propios (lo prohíben): manda su SDK;
     · si el anuncio no responde en 30 s, el juego sigue. Los proveedores 'adsense', 'crazygames' y 'poki' se prueban aquí con simulaciones; la prueba real es
       la herramienta de vista previa de cada portal / el modo de prueba de AdSense (monetizacion/ESTRATEGIA.md). */
(function () {
  'use strict';
  const G = window.GGX;
  if (!G || (G.ads && G.ads.intermedio)) return;     // el núcleo ya trae un GGX.ads vacío (use/interstitial/rewarded); el módulo lo completa sin quitarle nada
  const C = (window.GGX_CONFIG && window.GGX_CONFIG.anuncios) || {};
  const PERMITIDOS = ['fin_de_partida', 'fin_de_nivel', 'pausa_larga'];
  const AVISO = { es: 'Anuncio. El juego sigue enseguida.', en: 'Advertisement. The game resumes shortly.', zh: '广告。游戏马上继续。' };
  const PROPIAS = { espera_inicial_s: 90, min_entre_s: 180, max_por_sesion: 4, recompensa_min_entre_s: 120 };
  const S = { proveedor: 'ninguno', reglas: Object.assign({}, PROPIAS), sdk: true, prueba: false, publicador: '', sdkUrl: '', pedidos: 0, mostrados: 0, intermedios: 0, rechazados: 0, recompensas: 0,
    ultimo: '', ultimoRechazo: '', entrada: false, t0: performance.now(), tAnuncio: -1e9, tRecompensa: -1e9, enAnuncio: false, mudoAntes: false, jugando: null, listo: false, nombre: 'ggx' };
  const pausar = [], reanudar = [];
  const seg = () => (performance.now() - S.t0) / 1000;
  const seguro = (f, ...a) => { try { return f(...a); } catch (e) { setTimeout(() => { throw e; }); } };
  ['pointerdown', 'keydown', 'touchstart'].forEach((ev) => window.addEventListener(ev, () => { S.entrada = true; }, { capture: true, passive: true }));

  // ---- pausa, silencio y aviso mientras suena un anuncio ----
  function alEmpezar() {
    if (S.enAnuncio) return;
    S.enAnuncio = true; S.mostrados++;
    S.mudoAntes = G.muted();
    if (!S.mudoAntes) G.setMuted(true);
    document.documentElement.setAttribute('data-anuncio', '1');
    pausar.forEach((f) => seguro(f));
    if (G.a11y && G.a11y.announce) seguro(G.a11y.announce, AVISO[G.lang] || AVISO.es);
  }
  function alTerminar() {
    if (!S.enAnuncio) return;
    S.enAnuncio = false;
    if (!S.mudoAntes && G.muted()) G.setMuted(false);
    document.documentElement.removeAttribute('data-anuncio');
    reanudar.forEach((f) => seguro(f));
  }
  window.addEventListener('pagehide', () => { if (S.enAnuncio && !S.mudoAntes) G.setMuted(false); });   // que un anuncio abierto no deje el juego mudo para la próxima visita

  // ---- proveedores ----
  const hacia = (tipo, bien, mal) => window.CrazyGames.SDK.ad.requestAd(tipo, { adStarted: alEmpezar, adFinished: () => { alTerminar(); bien(); }, adError: (e) => { alTerminar(); mal('error'); } });
  const PROVEEDORES = {
    ninguno: { listo: () => false },
    adsense: {
      listo: () => typeof window.adBreak === 'function',
      intermedio: (seguir) => window.adBreak({ type: 'next', name: S.nombre, beforeAd: alEmpezar, afterAd: alTerminar, adBreakDone: () => { alTerminar(); seguir(); } }),
      recompensa: (ok, no) => {
        let visto = false;
        window.adBreak({ type: 'reward', name: S.nombre, beforeAd: alEmpezar, afterAd: alTerminar, beforeReward: (mostrar) => mostrar(), adViewed: () => { visto = true; },
          adDismissed: () => {}, adBreakDone: () => { alTerminar(); if (visto) ok(); else no('descartado'); } });
      },
    },
    crazygames: {
      listo: () => S.listo && !!(window.CrazyGames && window.CrazyGames.SDK && window.CrazyGames.SDK.ad),
      intermedio: (seguir) => hacia('midgame', seguir, seguir),
      recompensa: (ok, no) => hacia('rewarded', ok, no),
      jugando: (b) => { const j = window.CrazyGames.SDK.game; if (j) (b ? j.gameplayStart() : j.gameplayStop()); },
    },
    poki: {   // borrador: Poki entrega su documentación del SDK solo después de aceptar el juego; se confirma entonces
      listo: () => !!window.PokiSDK,
      intermedio: (seguir) => Promise.resolve(window.PokiSDK.commercialBreak(alEmpezar)).then(() => { alTerminar(); seguir(); }, () => { alTerminar(); seguir(); }),
      recompensa: (ok, no) => Promise.resolve(window.PokiSDK.rewardedBreak(alEmpezar)).then((v) => { alTerminar(); if (v) ok(); else no('descartado'); }, () => { alTerminar(); no('error'); }),
      jugando: (b) => (b ? window.PokiSDK.gameplayStart() : window.PokiSDK.gameplayStop()),
    },
  };
  const P = () => PROVEEDORES[S.proveedor] || PROVEEDORES.ninguno;
  const reglasPropias = () => S.proveedor === 'adsense' || S.proveedor === 'ninguno';

  function inicializar() {
    S.listo = false;
    if (S.proveedor === 'crazygames' && window.CrazyGames && window.CrazyGames.SDK) {
      Promise.resolve(window.CrazyGames.SDK.init()).then(() => { S.listo = true; }, () => { S.listo = false; });
    } else if (S.proveedor === 'adsense') {
      if (S.sdk && S.publicador && S.sdkUrl) {
        window.adsbygoogle = window.adsbygoogle || [];
        window.adBreak = window.adConfig = function (o) { window.adsbygoogle.push(o); };
        const s = document.createElement('script');
        s.async = true; s.crossOrigin = 'anonymous';
        s.src = S.sdkUrl + encodeURIComponent(S.publicador);
        s.setAttribute('data-ad-client', S.publicador);
        if (S.prueba) s.setAttribute('data-adbreak-test', 'on');
        document.head.appendChild(s);
      }
      if (typeof window.adConfig === 'function') window.adConfig({ preloadAdBreaks: 'on', sound: G.muted() ? 'off' : 'on' });
      S.listo = true;
    } else S.listo = S.proveedor !== 'ninguno';
  }

  // ---- por qué sí o por qué no ----
  function motivoDeRechazo(momento, recompensa) {
    if (S.proveedor === 'ninguno') return 'sin_proveedor';
    if (!P().listo()) return 'no_listo';
    if (S.enAnuncio) return 'en_curso';
    if (!recompensa && PERMITIDOS.indexOf(momento) < 0) return 'momento';
    if (!S.entrada) return 'sin_entrada';
    if (reglasPropias()) {
      const R = S.reglas, t = seg();
      if (recompensa) { if (t - S.tRecompensa < R.recompensa_min_entre_s) return 'frecuencia'; }
      else {
        if (t < R.espera_inicial_s) return 'espera_inicial';
        if (t - S.tAnuncio < R.min_entre_s) return 'frecuencia';
        if (S.intermedios >= R.max_por_sesion) return 'tope';
      }
    }
    return '';
  }
  const conTope = (fin) => {
    let hecho = false; const tm = setTimeout(() => cierre(), 30000);
    function cierre() { if (hecho) return; hecho = true; clearTimeout(tm); alTerminar(); if (fin) seguro(fin); }
    return cierre;
  };

  G.ads = Object.assign(G.ads || {}, {
    configurar(o) {
      o = o || {};
      if (o.proveedor) S.proveedor = PROVEEDORES[o.proveedor] ? o.proveedor : 'ninguno';
      if (o.reglas) Object.assign(S.reglas, o.reglas);
      if (typeof o.publicador === 'string') S.publicador = o.publicador;
      if (typeof o.sdk_url === 'string') S.sdkUrl = o.sdk_url;     // la dirección del script la pone la fábrica solo cuando la ruta está encendida: apagado, el juego no lleva ninguna dirección de afuera
      if (o.sdk === false) S.sdk = false;
      if (o.prueba) S.prueba = true;
      inicializar();
      return G.ads;
    },
    intermedio(momento, alTerminarFn) {
      S.pedidos++;
      const motivo = motivoDeRechazo(momento, false);
      if (motivo) { S.rechazados++; S.ultimoRechazo = motivo; if (alTerminarFn) seguro(alTerminarFn); return false; }
      S.ultimo = momento; S.tAnuncio = seg(); S.intermedios++;
      const cierre = conTope(alTerminarFn);
      try { P().intermedio(cierre); } catch (e) { S.ultimoRechazo = 'error'; cierre(); }
      return true;
    },
    recompensa(motivo, cb) {
      cb = cb || {};
      const no = (m) => { if (cb.no) seguro(cb.no, m); };
      S.pedidos++;
      const r = motivoDeRechazo(motivo, true);
      if (r) { S.rechazados++; S.ultimoRechazo = r; no(r); return false; }
      S.ultimo = 'recompensa:' + motivo; S.tRecompensa = seg();
      let hecho = false;
      const fin = (bien, m) => { if (hecho) return; hecho = true; clearTimeout(tm); alTerminar(); if (bien) { S.recompensas++; if (cb.ok) seguro(cb.ok); } else no(m || 'error'); };
      const tm = setTimeout(() => fin(false, 'tiempo'), 30000);
      try { P().recompensa(() => fin(true), (m) => fin(false, m)); } catch (e) { fin(false, 'error'); }
      return true;
    },
    recompensaDisponible() { return S.proveedor !== 'ninguno' && !!PROVEEDORES[S.proveedor] && P().listo() && !S.enAnuncio; },
    jugando(b) {
      b = !!b;
      if (S.jugando === b) return;
      S.jugando = b;
      if (P().jugando && P().listo()) seguro(P().jugando, b);
    },
    alPausar(f) { if (typeof f === 'function') pausar.push(f); },
    alReanudar(f) { if (typeof f === 'function') reanudar.push(f); },
    estado() { return { proveedor: S.proveedor, listo: S.proveedor !== 'ninguno' && P().listo(), pedidos: S.pedidos, mostrados: S.mostrados, rechazados: S.rechazados, recompensas: S.recompensas, ultimo: S.ultimo, ultimoRechazo: S.ultimoRechazo }; },
  });
  if (C.proveedor) G.ads.configurar(C);
})();
