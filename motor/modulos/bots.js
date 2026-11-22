/* GGX · módulo «bots» · el laboratorio de pruebas con bots: una interfaz estándar para que algo que no es una persona (un bot de la fábrica, un script,
   una plataforma que simula jugadores) juegue un juego del Taller, de forma reproducible y mucho más rápido que el tiempo real.
   Se activa con "motor": [..., "bots"] en juego.json. Está INERTE salvo que la dirección lleve ?bot=1: un jugador normal no ve ni activa nada.
   Qué mide y qué NO: un bot dice si el juego se puede ganar, qué tan difícil es, si falla o se rompe, y si es determinista. NO dice si a la gente le va a gustar,
   cuántos van a venir ni si es divertido: eso lo dicen las métricas de visitas y los jugadores (ver LEEME.md, «Pruebas con bots»).

   El juego registra un adaptador (todo opcional salvo lo marcado), con tiempo SIMULADO: el bot decide cuánto avanza el mundo, el reloj real no cuenta.
     GGX.bots.registrar({
       juego: 'id', version: '1.0.0',
       reiniciar(semilla, opciones)  (obligatorio) empieza un episodio nuevo y determinista: misma semilla y mismas acciones, mismo resultado
       estado()                      (obligatorio) lo que ve quien juega, como datos simples (JSON)
       actuar(accion)                (obligatorio) aplica una acción; devuelve {valida: true|false, motivo}
       avanzar(ms)                   (obligatorio) hace pasar ms milisegundos de juego en pasos fijos (sin requestAnimationFrame ni reloj real)
       terminado()                   (obligatorio) {fin: bool, exito: bool, motivo: texto}
       acciones()                    descripción de las acciones posibles (para quien no conoce el juego)
       puntaje()                     número; por omisión 0
       simular(accion)               qué pasaría con esa acción sin cambiar el estado real (para bots que planean); devuelve {exito, puntaje, ms, …}
       invariantes()                 lista de reglas rotas (vacía si todo está bien): masa que se conserva, sin NaN, dentro de los límites…
       resumen()                     datos propios del juego para el informe (p. ej. descubrimientos), como datos simples
     })
   Con ?bot=1 (y opcionalmente &semilla=N) existe window.__bot con: info() reiniciar(semilla, opciones) estado() acciones() actuar(a) avanzar(ms) terminado()
   puntaje() simular(a) metricas() y correr(politica, semilla, opciones), que juega un episodio entero DENTRO de la página:
     politica(api, rng, ctx) → una acción, {tipo:'esperar'} para dejar pasar el tiempo, o null para rendirse. api = {estado, acciones, simular, puntaje, terminado}.
     opciones: {max_pasos: 2000, dt: 50 (ms de juego entre decisiones), max_ms: 600000, cada_invariantes: 25} y lo demás va a reiniciar().
     Una acción puede traer una propiedad «info» (datos simples): la última queda en el resultado como politica_info (p. ej. cuántas soluciones encontró un bot que planea).
     Devuelve {semilla, pasos, ms_simulados, exito, terminado, motivo, puntaje, invalidas, violaciones, errores, resumen, politica_info, ms_reales}.
     ms_reales es lo único que no es reproducible (es el reloj de la computadora); todo lo demás es idéntico si la semilla y la política lo son.
   Contrato completo para plataformas externas: motor/BOTS.md. */
(function () {
  'use strict';
  const G = window.GGX;
  if (!G || G.bots) return;
  const q = new URLSearchParams(location.search);
  const activo = q.get('bot') === '1' || window.__GGX_BOT__ === true;
  const CONTRATO = 1;
  const OBLIGATORIOS = ['reiniciar', 'estado', 'actuar', 'avanzar', 'terminado'];
  const errores = [];
  let ad = null;
  let invalidas = 0;

  const nota = (txt) => { if (errores.length < 20) errores.push(String(txt).slice(0, 240)); };
  const llamar = (nombre, ...args) => {
    try { return ad[nombre](...args); } catch (e) { nota(nombre + ': ' + (e && e.message ? e.message : e)); throw e; }
  };
  const hay = (nombre) => !!ad && typeof ad[nombre] === 'function';
  const falta = () => { throw new Error('GGX.bots: el juego no registró su adaptador (GGX.bots.registrar)'); };
  const datos = (o) => (o === undefined ? null : JSON.parse(JSON.stringify(o)));     // lo que sale de la página son datos simples, nunca referencias vivas
  const num = (n, d) => (Number.isFinite(Number(n)) && n !== null && n !== '' ? Number(n) : d);
  const uno = (o) => (o && typeof o === 'object' ? o : {});

  function comoFuncion(politica) {
    if (typeof politica === 'function') return politica;
    if (typeof politica === 'string') { const f = new Function('return (' + politica + ')')(); if (typeof f === 'function') return f; }
    throw new Error('GGX.bots.correr: la política debe ser una función o su código');
  }

  const api = {
    contrato: CONTRATO,
    info() {
      if (!ad) falta();
      return { juego: ad.juego || '', version: ad.version || '', contrato: CONTRATO, semilla_url: q.get('semilla') === null ? null : num(q.get('semilla'), null),
        capacidades: { acciones: hay('acciones'), puntaje: hay('puntaje'), simular: hay('simular'), invariantes: hay('invariantes'), resumen: hay('resumen') } };
    },
    reiniciar(semilla, opciones) { if (!ad) falta(); invalidas = 0; return datos(llamar('reiniciar', num(semilla, 1), uno(opciones))); },
    estado() { if (!ad) falta(); return datos(llamar('estado')); },
    acciones() { if (!ad) falta(); return hay('acciones') ? datos(llamar('acciones')) : null; },
    actuar(accion) {
      if (!ad) falta();
      const r = uno(llamar('actuar', accion));
      if (r.valida === false) invalidas++;
      return datos(r);
    },
    avanzar(ms) { if (!ad) falta(); llamar('avanzar', Math.max(0, num(ms, 0))); return true; },
    terminado() { if (!ad) falta(); const t = uno(llamar('terminado')); return { fin: !!t.fin, exito: !!t.exito, motivo: String(t.motivo || '') }; },
    puntaje() { if (!ad) falta(); return hay('puntaje') ? num(llamar('puntaje'), 0) : 0; },
    simular(accion) { if (!ad) falta(); if (!hay('simular')) return null; return datos(llamar('simular', accion)); },
    metricas() { return { errores: errores.slice(), invalidas }; },
    correr(politica, semilla, opciones) {
      if (!ad) falta();
      const o = Object.assign({ max_pasos: 2000, dt: 50, max_ms: 600000, cada_invariantes: 25 }, uno(opciones));
      const pol = comoFuncion(politica);
      const rng = G.rng((num(semilla, 1) * 7919 + 13) >>> 0);                  // el azar de la política no comparte la corriente del azar del juego
      const vista = { estado: api.estado, acciones: api.acciones, simular: api.simular, puntaje: api.puntaje, terminado: api.terminado };
      const violaciones = [];
      const nErr0 = errores.length;
      const t0 = performance.now();
      api.reiniciar(semilla, o);
      let pasos = 0, ms = 0, fin = null, nota_politica = null;
      const revisar = () => {
        if (!hay('invariantes')) return;
        const v = llamar('invariantes');
        if (Array.isArray(v)) v.forEach((x) => { if (violaciones.length < 5 && violaciones.indexOf(String(x)) < 0) violaciones.push(String(x)); });
      };
      try {
        while (pasos < o.max_pasos && ms < o.max_ms) {
          const t = api.terminado();
          if (t.fin) { fin = t; break; }
          let a;
          try { a = pol(vista, rng, { paso: pasos, ms, dt: o.dt }); } catch (e) { nota('politica: ' + (e && e.message ? e.message : e)); fin = { fin: true, exito: false, motivo: 'error-de-politica' }; break; }
          if (a === null || a === undefined || a === 'fin') { fin = { fin: false, exito: false, motivo: 'abandono' }; break; }
          if (typeof a === 'object' && a.info !== undefined) nota_politica = a.info;
          if (!(typeof a === 'object' && a.tipo === 'esperar')) api.actuar(a);
          api.avanzar(o.dt); ms += o.dt; pasos++;
          if (o.cada_invariantes > 0 && pasos % o.cada_invariantes === 0) revisar();
        }
        if (!fin) { const t = api.terminado(); fin = t.fin ? t : { fin: false, exito: false, motivo: 'limite' }; }
        revisar();
      } catch (e) { fin = { fin: true, exito: false, motivo: 'error-del-juego' }; }
      return datos({ semilla: num(semilla, 1), pasos, ms_simulados: ms, exito: !!fin.exito, terminado: !!fin.fin, motivo: String(fin.motivo || ''),
        puntaje: api.puntaje(), invalidas, violaciones, errores: errores.slice(nErr0), resumen: hay('resumen') ? uno(llamar('resumen')) : null, politica_info: nota_politica,
        ms_reales: Math.round((performance.now() - t0) * 100) / 100 });
    },
  };

  G.bots = {
    version: '1.0.0',
    contrato: CONTRATO,
    activo,
    registrar(adaptador) {
      const a = uno(adaptador);
      const faltan = OBLIGATORIOS.filter((n) => typeof a[n] !== 'function');
      if (faltan.length) { nota('registrar: faltan ' + faltan.join(', ')); throw new Error('GGX.bots.registrar: al adaptador le faltan ' + faltan.join(', ')); }
      ad = a;
      if (activo) { window.__bot = api; document.documentElement.setAttribute('data-bot', '1'); }
      return true;
    },
    estado() { return { activo, registrado: !!ad, juego: ad ? ad.juego || '' : '', errores: errores.slice(), expuesto: !!window.__bot }; },
    api,
  };
})();
