"""Rumbo: qué juego conviene construir después, según lo que dicen las métricas.

Lee el registro (`metricas/registro.csv`), las fichas de los juegos, el cuaderno de ideas (`ideas/ideas.json`) y el libro de publicaciones, y devuelve una
lista ordenada de ideas con la razón de cada lugar. Es determinista: con los mismos archivos da siempre el mismo orden, así que cualquier recomendación
pasada se puede recalcular desde el historial de git.

Dos modos, según haya o no evidencia suficiente (umbrales en `metricas/politica.json`):

  EXPLORAR  (hay menos de 2 juegos medibles). No se aprende nada de los números: se prefiere lo que más se aleja de lo que la fábrica ya tiene, con menos riesgo
            de clon y menor costo. Es el modo en el que está la fábrica hasta tener semanas de datos.
  APRENDER  (2 o más juegos con ≥3 semanas completas y ≥200 vistas del juego). Cada juego recibe un puntaje relativo al promedio de la cartera:
              · alcance:    vistas del juego por cada «unidad de empuje» (1 + publicaciones del motor en redes esa semana), para no confundir un buen
                            juego con una semana de mucha difusión;
              · aceptación: proporción de comentarios favorables (solo con ≥10 comentarios);
              · apoyo:      dólares (donaciones + ingresos) por cada mil vistas (solo si alguien pagó algo en la cartera).
            Todo se suaviza hacia el promedio (a poca evidencia, el puntaje se queda cerca de 1). El puntaje de un juego se reparte entre sus rasgos (género,
            verbo, objetivo, entrada, progresión, ambientación); cada idea hereda el efecto de sus rasgos y, para no cerrarse, suma un premio por lo no probado
            (más grande cuanto menos juegos medibles tienen ese rasgo).

En los dos modos el puntaje final de una idea es (efecto + premio de exploración) × factor de riesgo de clon × factor de costo × factor de novedad.

Lo que el rumbo NO hace: no construye, no publica ni salta ninguna regla. Una idea que el comprobador de novedad declara variante de un juego existente queda
fuera siempre; una idea con «bloqueada_por» (algo que solo una persona puede resolver) se lista aparte; y construir algo no autoriza lanzarlo: el lanzamiento
sigue sujeto a la pausa entre lanzamientos, a las compuertas y a la huella que apruebe el dueño.

Límites honestos: con poco tráfico los números son ruido y por eso existen los mínimos; las vistas de Cloudflare no son partidas ni tiempo de juego; los pesos
y los factores son criterio de quien armó la fábrica, no resultados medidos. Con pocos juegos, casi todos los rasgos tienen una sola observación."""
import datetime
import math
import pathlib

import metricas as met
import novedad as nov

EJES = ('genero', 'verbo', 'objetivo', 'entrada', 'progresion', 'ambientacion')


def _lista(m, eje):
    v = (m or {}).get(eje)
    if isinstance(v, list):
        return [str(x) for x in v if x]
    return [str(v)] if v else []


def rasgos_de(mecanica):
    return [(e, v) for e in EJES for v in _lista(mecanica, e)]


def _fecha_ts(ts):
    try:
        return datetime.date.fromisoformat(str(ts)[:10])
    except ValueError:
        return None


def _semanas_de_ventana(hoy, n):
    ultima = met.lunes(hoy) - datetime.timedelta(days=7)
    return [ultima - datetime.timedelta(days=7 * i) for i in reversed(range(n))]


def datos_de_juegos(juegos, filas, libro, hoy, pol):
    """Resumen de evidencia por juego: semanas, vistas, comentarios, dinero y empuje, solo con semanas completas."""
    r = pol['rumbo']
    ventana = _semanas_de_ventana(hoy, r['ventana_semanas'])
    en_ventana = set(ventana)
    s = met.sumas(filas)
    sin_empuje = set(r.get('canales_sin_empuje', []))
    empuje = {}
    for e in libro:
        d = _fecha_ts(e.get('ts'))
        if e.get('resultado') == 'ok' and d and e.get('canal') not in sin_empuje and e.get('juego'):
            k = (e['juego'], met.lunes(d))
            empuje[k] = empuje.get(k, 0) + 1
    salida = {}
    for jid in sorted(juegos):
        con_fila = sorted(w for (w, j, m) in s if j == jid and m == 'vistas_juego' and w in en_ventana)
        positivas = [w for w in con_fila if s[(w, jid, 'vistas_juego')] > 0]
        semanas = [w for w in con_fila if positivas and w >= positivas[0]]

        def total(metrica):
            return sum(s.get((w, jid, metrica), 0) for w in semanas)
        d = {'id': jid, 'semanas': len(semanas), 'vistas_juego': total('vistas_juego'), 'vistas_ficha': total('vistas_ficha'),
             'pos': total('comentarios_pos'), 'neg': total('comentarios_neg'),
             'dinero': round(total('donaciones_usd') + total('ingresos_usd'), 2),
             'empuje': sum(empuje.get((jid, w), 0) for w in semanas)}
        d['exposicion'] = d['semanas'] + d['empuje']        # 1 de base por semana (lo orgánico) + cada publicación del motor
        faltan = []
        if d['semanas'] < r['minimo_semanas']:
            faltan.append('faltan %d semana(s) completa(s) con vistas' % (r['minimo_semanas'] - d['semanas']))
        if d['vistas_juego'] < r['minimo_vistas_juego']:
            faltan.append('faltan %d vistas del juego' % (r['minimo_vistas_juego'] - d['vistas_juego']))
        d['faltan'] = faltan
        d['medible'] = not faltan
        salida[jid] = d
    return salida


def puntajes(datos, pol):
    """{id: {puntaje, componentes}} de los juegos medibles. Cada componente es un cociente contra el promedio de la cartera (1 = promedio)."""
    r = pol['rumbo']
    m = [d for d in datos.values() if d['medible']]
    if not m:
        return {}
    previa = r['fuerza_previa']
    comp = {d['id']: {} for d in m}
    # alcance: vistas por unidad de exposición
    r0 = sum(d['vistas_juego'] for d in m) / sum(d['exposicion'] for d in m)
    for d in m:
        comp[d['id']]['alcance'] = ((d['vistas_juego'] + previa['alcance'] * r0) / (d['exposicion'] + previa['alcance'])) / r0
    # aceptación: proporción de comentarios favorables, solo entre juegos con comentarios suficientes
    con_com = [d for d in m if d['pos'] + d['neg'] >= r['minimo_comentarios']]
    if len(con_com) >= 2:
        p0 = sum(d['pos'] for d in con_com) / sum(d['pos'] + d['neg'] for d in con_com)
        if p0 > 0:
            for d in con_com:
                comp[d['id']]['aceptacion'] = ((d['pos'] + previa['aceptacion'] * p0) / (d['pos'] + d['neg'] + previa['aceptacion'])) / p0
    # apoyo: dólares por mil vistas, solo si alguien pagó algo en la cartera
    s0 = sum(d['dinero'] for d in m) / (sum(d['vistas_juego'] for d in m) / 1000.0)
    if s0 > 0:
        for d in m:
            comp[d['id']]['apoyo'] = ((d['dinero'] + previa['apoyo'] * s0) / (d['vistas_juego'] / 1000.0 + previa['apoyo'])) / s0
    pesos = r['pesos']
    salida = {}
    for jid, c in comp.items():
        w = sum(pesos[k] for k in c)
        salida[jid] = {'puntaje': sum(pesos[k] * v for k, v in c.items()) / w, 'componentes': c}
    return salida


def estadisticas_de_rasgos(specs, pts, modo, k):
    """{(eje, valor): {n, efecto}}. En «aprender» solo cuentan los juegos medibles y su puntaje; en «explorar» cuentan todos los juegos con efecto neutro."""
    est = {}
    for jid, spec in specs.items():
        if modo == 'aprender':
            if jid not in pts:
                continue
            valor = pts[jid]['puntaje']
        else:
            valor = 1.0
        for rasgo in rasgos_de(spec.get('mecanica')):
            e = est.setdefault(rasgo, {'n': 0, 'suma': 0.0})
            e['n'] += 1
            e['suma'] += valor
    for e in est.values():
        e['efecto'] = (e['suma'] + k * 1.0) / (e['n'] + k)
    return est


def _factor(tabla, clave, defecto):
    return tabla.get(clave, tabla.get(defecto, 1.0))


def candidatas(raiz, specs, pts, modo, pol):
    r = pol['rumbo']
    est = estadisticas_de_rasgos(specs, pts, modo, r['fuerza_previa']['rasgos'])
    pesos_eje = r['peso_ejes']
    c = r['exploracion']
    ranking, en_espera, excluidas = [], [], []
    for idea, ev in nov.evaluar_ideas(raiz):
        iid = idea['id']
        if (pathlib.Path(raiz) / 'juegos' / iid).exists() or (pathlib.Path(raiz) / 'plantillas' / iid).exists():
            excluidas.append({'id': iid, 'motivo': 'ya está construida'})
            continue
        if ev['veredicto'] not in r['factor_novedad']:
            excluidas.append({'id': iid, 'motivo': ' '.join(ev['motivos']) or 'el comprobador de novedad no la evalúa (%s)' % ev['veredicto']})
            continue
        if idea.get('bloqueada_por'):
            en_espera.append({'id': iid, 'titulo': idea.get('titulo', ''), 'motivo': idea['bloqueada_por']})
            continue
        ejes, num, den = [], 0.0, 0.0
        for eje in EJES:
            valores = _lista(idea['mecanica'], eje)
            if not valores:
                continue
            efectos = [est.get((eje, v), {}).get('efecto', 1.0) for v in valores]
            ns = [est.get((eje, v), {}).get('n', 0) for v in valores]
            premios = [c / math.sqrt(n + 1) for n in ns]
            ejes.append({'eje': eje, 'valores': valores, 'n': ns, 'efecto': sum(efectos) / len(efectos), 'premio': sum(premios) / len(premios)})
            num += pesos_eje.get(eje, 0) * (ejes[-1]['efecto'] + ejes[-1]['premio'])
            den += pesos_eje.get(eje, 0)
        base = num / den if den else 1.0
        riesgo = idea.get('riesgo_estimado')
        costo = idea.get('costo_estimado')
        f_riesgo = _factor(r['factor_riesgo'], riesgo, 'alto')
        f_costo = _factor(r['factor_costo'], costo, 'medio')
        f_nov = r['factor_novedad'][ev['veredicto']]
        ranking.append({'id': iid, 'titulo': idea.get('titulo', ''), 'mecanica': idea['mecanica'], 'puntaje': base * f_riesgo * f_costo * f_nov, 'base': base,
                        'ejes': ejes, 'riesgo': riesgo or '?', 'costo': costo or '?', 'novedad': ev['veredicto'],
                        'factores': {'riesgo': f_riesgo, 'costo': f_costo, 'novedad': f_nov}})
    ranking.sort(key=lambda x: (-round(x['puntaje'], 9), x['id']))
    return ranking, en_espera, excluidas


def recomendar(raiz, hoy=None, libro=None):
    """Todo el análisis, sin escribir nada. `libro`: lista de entradas del libro de publicaciones (por defecto, publicacion/libro.jsonl)."""
    raiz = pathlib.Path(raiz)
    hoy = hoy or met.hoy_utc()
    pol = met.cargar_politica(raiz)
    specs = {i: s for i, s in nov.cargar_juegos(raiz).items() if not s.get('_ilegible') and isinstance(s.get('mecanica'), dict)}
    filas = met.leer(raiz, set(nov.cargar_juegos(raiz)))
    if libro is None:
        import json
        ruta = raiz / 'publicacion' / 'libro.jsonl'
        libro = [json.loads(l) for l in ruta.read_text(encoding='utf-8').splitlines() if l.strip()] if ruta.exists() else []
    datos = datos_de_juegos(specs, filas, libro, hoy, pol)
    pts = puntajes(datos, pol)
    minimo = pol['rumbo']['minimo_juegos_medibles']
    modo = 'aprender' if len(pts) >= minimo else 'explorar'
    ranking, en_espera, excluidas = candidatas(raiz, specs, pts, modo, pol)
    avisos = []
    if not filas:
        avisos.append('No hay ninguna métrica registrada. La fuente automática es Cloudflare Web Analytics (ver LEEME-DUENO.md, «Medir visitas»); lo demás se anota con `python3 fabrica.py metricas anotar`.')
    sitio_ruta = raiz / 'publicacion' / 'sitio.json'
    if sitio_ruta.exists():
        import json
        sitio = json.loads(sitio_ruta.read_text(encoding='utf-8'))
        if any(f['fuente'] == 'cloudflare' for f in filas) and sitio.get('analitica') != 'cloudflare':
            avisos.append('**Hay datos de Cloudflare Web Analytics, pero `publicacion/sitio.json` no declara `"analitica": "cloudflare"`.** La página de privacidad del sitio todavía dice que no se usa analítica: corrígelo y vuelve a publicar el sitio.')
    return {'modo': modo, 'minimo_juegos': minimo, 'datos': datos, 'puntajes': pts, 'ranking': ranking, 'en_espera': en_espera, 'excluidas': excluidas, 'avisos': avisos,
            'semanas_en_ventana': pol['rumbo']['ventana_semanas'], 'minimos': {k: pol['rumbo'][k] for k in ('minimo_semanas', 'minimo_vistas_juego', 'minimo_juegos_medibles')}}


def _razon_eje(e):
    nombre = {'genero': 'género', 'progresion': 'progresión', 'ambientacion': 'ambientación'}.get(e['eje'], e['eje'])
    if sum(e['n']) == 0:
        return '%s «%s» no se ha probado' % (nombre, '/'.join(e['valores']))
    return '%s «%s»: ×%.2f con %d observación(es)' % (nombre, '/'.join(e['valores']), e['efecto'], sum(e['n']))


def informe(r, detalle=False, n=3):
    """Líneas de texto (Markdown) sin fechas ni claves; sirve para publicacion/PENDIENTE.md y para el comando `rumbo`."""
    L = []
    for a in r['avisos']:
        L += ['- ' + a, '']
    m = r['minimos']
    if r['modo'] == 'explorar':
        L.append('**Todavía no hay datos para decidir por métricas.** Hacen falta al menos %d juegos con %d semanas completas y %d vistas del juego; mientras tanto el rumbo se elige '
                 'explorando: lo que más se aleja de lo que ya hay, con menos riesgo de clon y menor costo.' % (m['minimo_juegos_medibles'], m['minimo_semanas'], m['minimo_vistas_juego']))
    else:
        L.append('**Hay datos de %d juegos medibles:** el orden combina cómo les fue a los rasgos de cada juego con un premio por lo no probado.' % len(r['puntajes']))
    L.append('')
    L.append('Evidencia por juego (semanas completas, últimas %d):' % r['semanas_en_ventana'])
    for d in r['datos'].values():
        estado = 'medible' if d['medible'] else ('sin datos todavía' if not d['semanas'] and not d['vistas_juego'] else '; '.join(d['faltan']))
        linea = '- `%s`: %d semana(s), %d vistas del juego, %d de la ficha' % (d['id'], d['semanas'], d['vistas_juego'], d['vistas_ficha'])
        if d['pos'] + d['neg']:
            linea += ', %d comentarios (%d favorables)' % (d['pos'] + d['neg'], d['pos'])
        if d['dinero']:
            linea += ', %.2f USD' % d['dinero']
        L.append('%s → %s' % (linea, estado))
        if detalle and d['id'] in r['puntajes']:
            p = r['puntajes'][d['id']]
            L.append('  puntaje %.2f (%s)' % (p['puntaje'], ', '.join('%s ×%.2f' % (k, v) for k, v in sorted(p['componentes'].items()))))
    L.append('')
    if not r['ranking']:
        L.append('No hay ideas disponibles: agrega una a `ideas/ideas.json` o desbloquea una de las que están en espera.')
    else:
        L.append('Recomendación, en orden:')
        for i, c in enumerate(r['ranking'][:n if not detalle else len(r['ranking'])], start=1):
            mec = c['mecanica']
            razones = [_razon_eje(e) for e in c['ejes'][:3 if not detalle else len(c['ejes'])]]
            L.append('%d. `%s` · %s · puntaje %.2f · riesgo de clon %s · costo %s%s' % (
                i, c['id'], c['titulo'], c['puntaje'], c['riesgo'], c['costo'], ' · se parece a un juego existente (no apta para portales)' if c['novedad'] == 'parecido' else ''))
            L.append('   Por qué: %s. Crearla: `python3 fabrica.py nueva-plantilla NOMBRE --genero %s --verbo %s --objetivo %s`' % ('; '.join(razones), mec['genero'], mec['verbo'], mec['objetivo']))
    if r['en_espera']:
        L += ['', 'En espera (algo que solo una persona puede resolver):']
        L += ['- `%s`: %s' % (e['id'], e['motivo']) for e in r['en_espera']]
    if detalle and r['excluidas']:
        L += ['', 'Excluidas:']
        L += ['- `%s`: %s' % (e['id'], e['motivo']) for e in r['excluidas']]
    elif r['excluidas']:
        L += ['', 'Excluidas: %s (detalle: `python3 fabrica.py rumbo --detalle`).' % ', '.join('`%s`' % e['id'] for e in r['excluidas'])]
    L += ['', 'Recomendar no es lanzar: un juego nuevo sigue sujeto a la revisión de novedad, a la pausa entre lanzamientos y a tu aprobación con la huella.']
    return L
