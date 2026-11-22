"""Pruebas con bots: el órgano del motor que hace jugar a un juego sin personas, miles de veces, y dice qué encontró.

Qué hace: abre el juego construido (salida/ID/index.html) con ?bot=1, hace correr las políticas de su plantilla (plantillas/NOMBRE/bots.js) episodio por episodio con
tiempo simulado (el módulo «bots» del motor; contrato en motor/BOTS.md), vuelve a jugar una semilla para comprobar que el resultado es el mismo, y resume.
Deja metricas/bots/ID.json, que es reproducible: mismas semillas y mismo juego, mismo archivo (sin fechas ni tiempos de reloj).

Qué dice un bot y qué NO: dice si el juego se puede ganar, qué tan ancho es el margen, qué tan fácil es a ciegas, si falla, se rompe o no es determinista.
NO dice si a la gente le va a gustar, cuántos van a venir ni si es divertido: eso lo dicen las métricas de visitas (rumbo) y los jugadores. Por eso estas banderas
se muestran junto a la idea en el ranking, pero no cambian su puntaje (nadie sabe todavía qué peso darles; hay que calibrarlas con datos reales).

Banderas (nivel «falla» = algo está roto; «aviso» = mírelo un humano):
  falla  no-determinista     la misma semilla dio otro resultado
  falla  fallas-de-pagina    errores de consola o excepciones en la página
  falla  errores-del-juego   el juego o una política lanzó un error durante un episodio
  falla  violaciones         se rompió una regla que el juego declara intocable (invariantes)
  falla  imposible           la política «solucionadora» no ganó ni una vez en una escena (o nadie, si no hay solucionadora)
  aviso  trivial             la política más débil gana casi siempre (se gana a ciegas)
  aviso  dificil             el solucionador gana, pero la política «humana» (con temblor) casi nunca
  aviso  se-corta            muchos episodios (de una política que no sea la débil) terminan por límite o abandono en vez de ganar o perder (¿se atasca?)"""
import hashlib
import json
import pathlib
import statistics
import subprocess

UMBRAL_TRIVIAL = 0.9
UMBRAL_DIFICIL = 0.2
UMBRAL_CORTE = 0.25
FALLAS = ('no-determinista', 'fallas-de-pagina', 'errores-del-juego', 'violaciones', 'imposible')


class ErrorBots(Exception):
    pass


def politicas_de(raiz, plantilla):
    return pathlib.Path(raiz) / 'plantillas' / plantilla / 'bots.js'


def juegos_con_bots(raiz):
    """Ids de los juegos cuya plantilla define pruebas con bots (plantillas/NOMBRE/bots.js)."""
    raiz = pathlib.Path(raiz)
    salida = []
    for ruta in sorted((raiz / 'juegos').glob('*/juego.json')):
        spec = json.loads(ruta.read_text(encoding='utf-8'))
        if politicas_de(raiz, spec.get('plantilla', '')).exists():
            salida.append(ruta.parent.name)
    return salida


def _mediana(valores):
    return statistics.median(valores) if valores else 0


def _agregar_resumenes(eps):
    """Junta los números que el juego declara en `resumen()` (uno por episodio): mediana y cuántos episodios los tuvieron.
    Un número suelto sale como «campo»; un diccionario de números (p. ej. cuándo se logró cada cosa) sale como «campo.clave»."""
    acum = {}

    def numero(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    for e in eps:
        r = e.get('resumen')
        if not isinstance(r, dict):
            continue
        for k, v in r.items():
            if numero(v):
                acum.setdefault(str(k), []).append(v)
            elif isinstance(v, dict):
                for k2, v2 in v.items():
                    if numero(v2):
                        acum.setdefault('%s.%s' % (k, k2), []).append(v2)
    return {k: {'p50': _mediana(vs), 'n': len(vs)} for k, vs in sorted(acum.items())}


def resumir(resultado):
    """De lo que devolvió jugar_bots.js al informe: por escena y política, y las banderas. Es una función pura (las pruebas la usan con datos inventados)."""
    cfg = resultado.get('config') or {}
    base, solucionador, humano = cfg.get('base'), cfg.get('solucionador'), cfg.get('humano')
    grupos = {}
    for e in resultado.get('episodios', []):
        grupos.setdefault((e['escena'], e['politica']), []).append(e)
    escenas = {}
    for (escena, politica), eps in sorted(grupos.items()):
        n = len(eps)
        exitos = sum(1 for e in eps if e.get('exito'))
        motivos = {}
        for e in eps:
            motivos[e.get('motivo') or '-'] = motivos.get(e.get('motivo') or '-', 0) + 1
        notas = [e['politica_info'] for e in eps if e.get('politica_info') is not None]
        fila = {'partidas': n, 'exitos': exitos, 'tasa': round(exitos / n, 4), 'pasos_p50': _mediana([e.get('pasos', 0) for e in eps]),
                'ms_simulados_p50': _mediana([e.get('ms_simulados', 0) for e in eps]), 'puntaje_prom': round(sum(e.get('puntaje', 0) for e in eps) / n, 3), 'motivos': dict(sorted(motivos.items())),
                'violaciones': sorted({v for e in eps for v in e.get('violaciones', [])}), 'errores': sorted({v for e in eps for v in e.get('errores', [])})}
        if notas:
            fila['info'] = notas[0]
        agregados = _agregar_resumenes(eps)
        if agregados:
            fila['resumen'] = agregados
        escenas.setdefault(escena, {})[politica] = fila
    banderas = []

    def bandera(codigo, texto, escena=None):
        banderas.append({'codigo': codigo, 'nivel': 'falla' if codigo in FALLAS else 'aviso', 'escena': escena, 'texto': texto})
    malas = [d for d in resultado.get('deterministas', []) if not d.get('ok')]
    if malas:
        bandera('no-determinista', 'con la misma semilla y la misma política el resultado cambió en: ' + ', '.join('%s/%s' % (d['escena'], d['politica']) for d in malas))
    if resultado.get('errores_de_pagina'):
        bandera('fallas-de-pagina', 'errores en la página: ' + ' | '.join(sorted(set(resultado['errores_de_pagina']))[:3]))
    errores = sorted({x for e in resultado.get('episodios', []) for x in e.get('errores', [])})
    if errores or any(e.get('motivo') in ('error-del-juego', 'error-de-politica') for e in resultado.get('episodios', [])):
        bandera('errores-del-juego', 'un episodio terminó por error: ' + (' | '.join(errores[:3]) or 'sin detalle'))
    viol = sorted({(v, esc) for esc, ps in escenas.items() for f in ps.values() for v in f['violaciones']})
    for v, esc in viol:
        bandera('violaciones', v, esc)
    for esc, ps in escenas.items():
        if solucionador in ps:
            if ps[solucionador]['exitos'] == 0:
                bandera('imposible', 'la política «%s» no ganó ni una vez: no se pudo resolver' % solucionador, esc)
        elif ps and all(f['exitos'] == 0 for f in ps.values()):
            bandera('imposible', 'ninguna política ganó ni una vez (%d partidas): ¿se puede ganar?' % sum(f['partidas'] for f in ps.values()), esc)
        if base in ps and ps[base]['partidas'] >= 5 and ps[base]['tasa'] >= UMBRAL_TRIVIAL:
            bandera('trivial', 'la política «%s» gana el %d %% de las veces: se gana a ciegas' % (base, round(ps[base]['tasa'] * 100)), esc)
        if humano in ps and solucionador in ps and ps[solucionador]['exitos'] and ps[humano]['partidas'] >= 5 and ps[humano]['tasa'] < UMBRAL_DIFICIL:
            bandera('dificil', 'se puede ganar, pero la política «%s» (con temblor humano) gana solo el %d %%' % (humano, round(ps[humano]['tasa'] * 100)), esc)
        for pol, f in ps.items():
            if pol == base and len(ps) > 1:                  # la política débil por diseño no termina casi nunca: que se corte no dice nada del juego
                continue
            cortados = f['motivos'].get('limite', 0) + f['motivos'].get('abandono', 0)
            if f['partidas'] >= 5 and cortados / f['partidas'] > UMBRAL_CORTE:
                bandera('se-corta', 'el %d %% de los episodios de «%s» terminan por límite o abandono, no por ganar o perder' % (round(cortados * 100 / f['partidas']), pol), esc)
    return escenas, banderas


def informe(juego_id, version, huella_html, resultado):
    escenas, banderas = resumir(resultado)
    cfg = resultado.get('config') or {}
    return {'juego': juego_id, 'version': version, 'huella_html': huella_html, 'semilla_base': cfg.get('semilla_base'), 'factor': cfg.get('factor'),
            'descripcion': cfg.get('descripcion', ''), 'politicas': {'base': cfg.get('base'), 'solucionador': cfg.get('solucionador'), 'humano': cfg.get('humano')},
            'determinista': not any(b['codigo'] == 'no-determinista' for b in banderas), 'escenas': escenas, 'banderas': banderas}


def texto(rep):
    pol = rep.get('politicas') or {}
    L = ['[bots] %s v%s · %d escena(s) · semilla base %s' % (rep['juego'], rep.get('version', '?'), len(rep['escenas']), rep.get('semilla_base'))]
    for esc, ps in rep['escenas'].items():
        partes = []
        for p in sorted(ps, key=lambda x: (x != pol.get('base'), x != pol.get('humano'), x)):
            f = ps[p]
            partes.append('%s %d/%d (%d %%)' % (p, f['exitos'], f['partidas'], round(f['tasa'] * 100)))
        extra = ''
        s = ps.get(pol.get('solucionador')) or {}
        if s.get('info'):
            extra = ' · soluciones: %s' % ', '.join('%s=%s' % (k, v) for k, v in sorted(s['info'].items()))
        L.append('  %-12s %s%s' % (esc, ' · '.join(partes), extra))
        for nombre in (pol.get('solucionador'), pol.get('humano')):
            r = (ps.get(nombre) or {}).get('resumen')
            if r:
                L.append('               «%s» (mediana): %s' % (nombre, ', '.join('%s=%s' % (k, v['p50']) for k, v in r.items())))
    if rep['banderas']:
        L.append('  Banderas:')
        for b in rep['banderas']:
            L.append('    [%s] %s%s: %s' % (b['nivel'], b['codigo'], (' · ' + b['escena']) if b.get('escena') else '', b['texto']))
    else:
        L.append('  Sin banderas.')
    return L


def correr(raiz, juego_id, factor=1.0, semilla_base=1000, politicas=None):
    """Juega el juego construido con las políticas de su plantilla y devuelve (informe, líneas_de_texto). No escribe nada."""
    raiz = pathlib.Path(raiz)
    ficha = json.loads((raiz / 'juegos' / juego_id / 'juego.json').read_text(encoding='utf-8'))
    pol = politicas_de(raiz, ficha['plantilla'])
    if not pol.exists():
        raise ErrorBots('la plantilla «%s» no define pruebas con bots (falta plantillas/%s/bots.js)' % (ficha['plantilla'], ficha['plantilla']))
    html = raiz / 'salida' / juego_id / 'index.html'
    if not html.exists():
        raise ErrorBots('«%s» no está construido: corre «python3 fabrica.py construir %s»' % (juego_id, juego_id))
    if 'bots' not in (ficha.get('motor') or []):
        raise ErrorBots('«%s» no declara el módulo «bots» en juego.json → motor' % juego_id)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        cfg = pathlib.Path(tmp) / 'config.json'
        cfg.write_text(json.dumps({'semilla_base': semilla_base, 'factor': factor, 'politicas': politicas}), encoding='utf-8')
        r = subprocess.run(['node', str(raiz / 'herramientas' / 'jugar_bots.js'), str(html), str(pol), str(cfg)], cwd=str(raiz), capture_output=True, text=True, timeout=900)
    if r.returncode != 0 or not r.stdout.strip():
        raise ErrorBots('las pruebas con bots no devolvieron resultado (¿están node y playwright?):\n%s' % (r.stderr or r.stdout)[-600:])
    try:
        resultado = json.loads(r.stdout.strip().splitlines()[-1])
    except ValueError:
        raise ErrorBots('la salida de las pruebas con bots no es JSON:\n%s' % r.stdout[-400:])
    huella = hashlib.sha256(html.read_bytes()).hexdigest()
    rep = informe(juego_id, ficha.get('version', ''), huella, resultado)
    return rep, texto(rep)


def guardar(raiz, rep):
    ruta = pathlib.Path(raiz) / 'metricas' / 'bots' / ('%s.json' % rep['juego'])
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return ruta


def leer(raiz, juego_id):
    ruta = pathlib.Path(raiz) / 'metricas' / 'bots' / ('%s.json' % juego_id)
    return json.loads(ruta.read_text(encoding='utf-8')) if ruta.exists() else None


def resumen_corto(rep):
    """Una línea para el ranking: qué se probó y si hay banderas."""
    if not rep:
        return None
    n = len(rep.get('escenas', {}))
    fallas = [b for b in rep['banderas'] if b['nivel'] == 'falla']
    avisos = [b for b in rep['banderas'] if b['nivel'] == 'aviso']
    estado = 'sin banderas' if not rep['banderas'] else '%d falla(s), %d aviso(s)' % (len(fallas), len(avisos))
    return '%d escena(s) probadas con bots: %s' % (n, estado)
