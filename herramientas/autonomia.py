"""Autonomía: el objetivo secundario del motor, que la fábrica necesite cada vez menos de Max sin cruzar sus límites.

Qué hace cada pieza (todo es de archivos: nada de esto necesita red ni claves, y nada de esto publica ni aprueba):
  motor/autonomia.json     el inventario: cada paso del ciclo de vida, quién lo hace (fábrica, agente o dueño) y, si es del dueño, de qué clase es
                           (obligatoria · reducible · automatizable), cuántas veces al mes lo toca (estimado) y cómo se reduce. También las
                           autorizaciones que Max ya dio, los límites que no cambian y las reglas que podría autorizar (propuestas).
  catalogo / problemas_de_catalogo   lo carga y lo revisa: un paso del dueño sin motivo, una «regla» que no existe o una propuesta que se hace pasar
                           por autorización son errores.
  medir()                  tres números, sin mezclarlos en un puntaje inventado: pasos del ciclo que corren sin Max, toques de Max por mes (estimado)
                           y los días que la fábrica corre sola con lo ya aprobado (este sí se mide, con el calendario).
  cola_items()             lo «automatizable» y construible entra a la cola del motor (herramientas/motor.py → cola_con_autonomia). Lo «reducible»
                           NUNCA entra: depende de que Max autorice una regla, y una propuesta no es una autorización.
  registrar()              una fila por semana en metricas/autonomia.csv, para ver la tendencia y avisar si la fábrica empezó a pedir más.

Lo que no hace: no cambia la política, no abre ni cierra canales, no aprueba nada en nombre de Max."""
import csv
import datetime
import json
import pathlib

CLASES = ('obligatoria', 'reducible', 'automatizable')
QUIENES = ('fabrica', 'agente', 'dueno')
FRECUENCIAS = ('diaria', 'semanal', 'por-lote', 'por-lanzamiento', 'eventual', 'una-vez')
CAMPOS = ['semana', 'pasos_autonomos', 'pasos_totales', 'toques_mes', 'toques_evitables_mes', 'dias_aprobados']
ESTADOS_CON_CONTENIDO = ('lista', 'aún no es su fecha')


class ErrorAutonomia(Exception):
    pass


def _json(ruta, defecto=None):
    ruta = pathlib.Path(ruta)
    return json.loads(ruta.read_text(encoding='utf-8')) if ruta.exists() else defecto


def catalogo(raiz):
    cat = _json(pathlib.Path(raiz) / 'motor' / 'autonomia.json')
    if cat is None:
        raise ErrorAutonomia('falta motor/autonomia.json (el inventario de autonomía)')
    return cat


def problemas_de_catalogo(cat):
    """Lista de motivos por los que el inventario no es confiable (vacía = bien)."""
    p = []
    pasos = cat.get('pasos') or []
    ids = [x.get('id') for x in pasos]
    if len(set(ids)) != len(ids) or not all(ids):
        p.append('los pasos necesitan un «id» único')
    propuestas = {x.get('id'): x for x in cat.get('propuestas') or []}
    limites = cat.get('limites') or {}
    autorizaciones = cat.get('autorizaciones_vigentes') or []
    por_propuesta = {a.get('propuesta'): a for a in autorizaciones if a.get('propuesta')}
    for a in autorizaciones:
        if not (a.get('id') and a.get('fecha') and a.get('texto') and a.get('origen')):
            p.append('la autorización «%s» necesita id, fecha, texto y origen (de dónde salió, en palabras de Max)' % a.get('id'))
        if a.get('propuesta') and a['propuesta'] not in propuestas:
            p.append('la autorización «%s» dice autorizar la propuesta «%s», que no existe' % (a.get('id'), a['propuesta']))
    for n, x in propuestas.items():
        if x.get('estado') not in ('propuesta', 'autorizada'):
            p.append('la propuesta «%s» debe estar en estado «propuesta» o «autorizada»' % n)
        if x.get('estado') == 'autorizada' and n not in por_propuesta:
            p.append('la propuesta «%s» figura como autorizada pero no hay una autorización suya en «autorizaciones_vigentes» (campo «propuesta»): una regla solo es de Max cuando él la autoriza y queda su origen' % n)
        if x.get('estado') == 'propuesta' and n in por_propuesta:
            p.append('la propuesta «%s» ya tiene una autorización pero sigue como «propuesta»' % n)
        if x.get('cambia_la_politica') not in (True, False):
            p.append('la propuesta «%s» debe decir si cambia la política (true o false)' % n)
        for campo in ('titulo', 'como_funciona', 'ahorra', 'riesgo', 'requiere'):
            if not x.get(campo):
                p.append('la propuesta «%s» no explica «%s»' % (n, campo))
    for x in pasos:
        i = x.get('id')
        if x.get('quien') not in QUIENES:
            p.append('%s: «quien» debe ser uno de %s' % (i, ', '.join(QUIENES)))
            continue
        if x.get('frecuencia') not in FRECUENCIAS:
            p.append('%s: «frecuencia» debe ser una de %s' % (i, ', '.join(FRECUENCIAS)))
        for dep in x.get('requiere') or []:
            if dep not in ids:
                p.append('%s: requiere «%s», que no existe' % (i, dep))
            elif next(y for y in pasos if y['id'] == dep)['quien'] != 'dueno':
                p.append('%s: solo se puede requerir un paso del dueño (hoy «%s»)' % (i, dep))
        if x['quien'] != 'dueno':
            if not x.get('donde'):
                p.append('%s: falta «donde» (el flujo o la rutina que lo hace)' % i)
            continue
        clase = x.get('clase')
        if clase not in CLASES:
            p.append('%s: «clase» debe ser una de %s' % (i, ', '.join(CLASES)))
            continue
        if x.get('estado') not in ('abierta', 'resuelta'):
            p.append('%s: «estado» debe ser abierta o resuelta' % i)
        if not x.get('por_que'):
            p.append('%s: todo paso del dueño dice por qué es suyo' % i)
        recurrente = x.get('frecuencia') != 'una-vez'
        if recurrente and not isinstance(x.get('veces_por_mes'), (int, float)):
            p.append('%s: un paso recurrente necesita «veces_por_mes» (estimado)' % i)
        if clase == 'obligatoria':
            if x.get('ancla') not in limites:
                p.append('%s: una obligación se ancla en uno de los límites (%s)' % (i, ', '.join(limites)))
        else:
            if not x.get('como_se_reduce'):
                p.append('%s: si no es obligatoria, dice cómo se reduce' % i)
            if recurrente and not isinstance(x.get('veces_con_regla'), (int, float)):
                p.append('%s: falta «veces_con_regla» (cuánto bajaría)' % i)
            elif recurrente and x['veces_con_regla'] > x['veces_por_mes']:
                p.append('%s: «veces_con_regla» no puede ser mayor que «veces_por_mes»' % i)
        if clase == 'reducible':
            reglas = x.get('regla') or []
            if not reglas or any(r not in propuestas for r in reglas):
                p.append('%s: «regla» debe nombrar propuestas que existan (hoy %r)' % (i, reglas))
            elif x.get('estado') == 'resuelta' and not any(propuestas[r].get('estado') == 'autorizada' for r in reglas):
                p.append('%s: un paso reducible solo queda «resuelta» si Max autorizó alguna de sus reglas' % i)
        if clase == 'automatizable' and x.get('construible') not in (True, False):
            p.append('%s: «construible» debe ser true o false' % i)
        if clase == 'automatizable' and x.get('regla'):
            p.append('%s: lo automatizable no depende de una regla de Max' % i)
        for desb in x.get('desbloquea') or []:
            if desb not in ids:
                p.append('%s: desbloquea «%s», que no existe' % (i, desb))
    return p


# ---------------------------------------------------------------------------------------------------------------------
# Medición
# ---------------------------------------------------------------------------------------------------------------------

def _paso(cat, i):
    return next((x for x in cat['pasos'] if x['id'] == i), None)


def _bloqueantes(cat, x):
    """Pasos del dueño aún abiertos que impiden que este paso corra solo."""
    return [d for d in x.get('requiere') or [] if (_paso(cat, d) or {}).get('estado') == 'abierta']


def medir(cat):
    """Lo que sale del inventario (no de la red ni del reloj). Los toques son estimaciones: sirven para la tendencia, no como cifra."""
    autonomos = [x for x in cat['pasos'] if x['quien'] in ('fabrica', 'agente')]
    activos = [x for x in autonomos if not _bloqueantes(cat, x)]
    recurrentes = [x for x in cat['pasos'] if x['quien'] == 'dueno' and x['estado'] == 'abierta' and x['frecuencia'] != 'una-vez']
    hoy = sum(x['veces_por_mes'] for x in recurrentes)
    evitables = sum(x['veces_por_mes'] for x in recurrentes if x['clase'] != 'obligatoria')
    con_reglas = sum(x.get('veces_con_regla', x['veces_por_mes']) for x in recurrentes)
    con_automatizables = sum(x['veces_por_mes'] for x in recurrentes if x['clase'] == 'obligatoria' or x['clase'] == 'reducible')
    return {
        'pasos_autonomos': len(activos), 'pasos_totales': len(autonomos) + len(recurrentes),
        'detenidos_por_dueno': {x['id']: _bloqueantes(cat, x) for x in autonomos if _bloqueantes(cat, x)},
        'toques_mes': round(hoy, 2), 'toques_evitables_mes': round(evitables, 2),
        'toques_con_reglas_mes': round(con_reglas, 2), 'toques_sin_automatizables_mes': round(con_automatizables, 2),
        'unicos_abiertos': [x['id'] for x in cat['pasos'] if x['quien'] == 'dueno' and x['frecuencia'] == 'una-vez' and x['estado'] == 'abierta'],
    }


def dias_aprobados(lineas, hoy):
    """(días, fecha del último día con publicación) que la fábrica corre sola con lo ya aprobado. `lineas` = calendario.estado(...).
    Cuenta lo aprobado y vigente: las publicaciones con fecha (listas o por llegar) y la reserva perenne aprobada, que llena los días en que no hay nada con fecha
    (una publicación del calendario por día). Lo sin aprobar o cambiado no cuenta: ahí la fábrica se detiene. (0, None) = nada por salir."""
    pendientes, reserva = [], 0
    for l in lineas:
        if l.get('perenne'):
            if l['estado'] in ('en reserva', 'lista'):
                reserva += 1
        elif l['estado'] in ESTADOS_CON_CONTENIDO and l.get('fecha'):
            pendientes.append(l['fecha'] if isinstance(l['fecha'], datetime.date) else datetime.date.fromisoformat(str(l['fecha'])))
    pendientes.sort()
    dia, ultimo, vueltas = hoy, None, 0
    while (pendientes or reserva > 0) and vueltas < 1000:
        if pendientes and pendientes[0] <= dia:
            pendientes.pop(0)
            ultimo = dia
        elif reserva > 0:
            reserva -= 1
            ultimo = dia
        dia += datetime.timedelta(days=1)
        vueltas += 1
    if ultimo is None:
        return 0, None
    return (ultimo - hoy).days, ultimo


def cola_items(raiz):
    """Lo que el motor puede construir sin que Max decida, para la cola del motor. Nunca incluye lo «reducible» (necesita una autorización)."""
    cat = catalogo(raiz)
    items = []
    for x in cat['pasos']:
        if x['quien'] == 'dueno' and x['clase'] == 'automatizable' and x['estado'] == 'abierta' and x.get('construible'):
            items.append({'prioridad': 3, 'tipo': 'autonomia', 'titulo': 'Automatizar: %s' % x['titulo'],
                          'por_que': 'Hoy lo hace Max (~%s veces al mes, estimado). %s' % (x['veces_por_mes'], x['como_se_reduce'])})
    return items


# ---------------------------------------------------------------------------------------------------------------------
# Registro semanal y tendencia
# ---------------------------------------------------------------------------------------------------------------------

def semana(hoy):
    a, s, _ = hoy.isocalendar()
    return '%d-W%02d' % (a, s)


def _ruta_registro(raiz):
    return pathlib.Path(raiz) / 'metricas' / 'autonomia.csv'


def historial(raiz):
    ruta = _ruta_registro(raiz)
    if not ruta.exists():
        return []
    with open(ruta, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def registrar(raiz, hoy, m, dias):
    """Una fila por semana (la de esa semana se reemplaza: correr el ciclo dos veces no la duplica). Devuelve la fila."""
    fila = {'semana': semana(hoy), 'pasos_autonomos': m['pasos_autonomos'], 'pasos_totales': m['pasos_totales'],
            'toques_mes': m['toques_mes'], 'toques_evitables_mes': m['toques_evitables_mes'], 'dias_aprobados': dias}
    filas = [r for r in historial(raiz) if r['semana'] != fila['semana']] + [{k: str(v) for k, v in fila.items()}]
    filas.sort(key=lambda r: r['semana'])
    ruta = _ruta_registro(raiz)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, lineterminator='\n')
        w.writeheader()
        w.writerows(filas)
    return fila


def avisos(raiz, hoy, m):
    """Si respecto a la semana anterior registrada la fábrica pide más o hace menos sola, que se note y se explique en el inventario."""
    previas = [r for r in historial(raiz) if r['semana'] < semana(hoy)]
    if not previas:
        return []
    ant = previas[-1]
    out = []
    if m['toques_mes'] > float(ant['toques_mes']) + 1e-9:
        out.append('Los toques de Max subieron (de %s a %s al mes, semana %s): algo nuevo le pide a él. Debe quedar explicado en motor/autonomia.json.' % (ant['toques_mes'], m['toques_mes'], ant['semana']))
    if m['pasos_autonomos'] < int(ant['pasos_autonomos']):
        out.append('Bajaron los pasos que corren sin Max (de %s a %s desde la semana %s).' % (ant['pasos_autonomos'], m['pasos_autonomos'], ant['semana']))
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Informe
# ---------------------------------------------------------------------------------------------------------------------

def _num(x):
    return '%g' % x


def informe(raiz, hoy, lineas_calendario=None, listos=None, completo=True):
    """Líneas para PENDIENTE.md (completo=False) y para `fabrica.py autonomia` (completo=True).
    `lineas_calendario`: resultado de calendario.estado(); `listos`: [(juego, huella_corta)] de juegos listos para aprobar. Ambos opcionales."""
    cat = catalogo(raiz)
    malos = problemas_de_catalogo(cat)
    if malos:
        raise ErrorAutonomia('el inventario de autonomía tiene problemas: ' + '; '.join(malos))
    m = medir(cat)
    L = []
    if lineas_calendario is not None:
        dias, hasta = dias_aprobados(lineas_calendario, hoy)
        if hasta:
            L.append('- **Contenido aprobado por salir:** hasta el %s (%d días). Cuando se acabe, el calendario se detiene hasta que Max apruebe un lote nuevo.' % (hasta.isoformat(), dias))
        else:
            L.append('- **Contenido aprobado por salir:** nada. El calendario está detenido hasta que Max apruebe un lote.')
        pend = [l for l in lineas_calendario if l['estado'] in ('sin aprobar', 'cambió tras aprobar')]
        reserva = len([l for l in lineas_calendario if l.get('perenne') and l['estado'] in ('en reserva', 'lista')])
        if reserva:
            L.append('- La reserva perenne aprobada tiene %d publicación(es); ya cuentan en los días de arriba.' % reserva)
        if pend:
            L.append('- Esperan su aprobación %d publicación(es) del calendario (`python3 fabrica.py calendario` muestra la huella del lote).' % len(pend))
    else:
        dias = None
    for juego, huella in listos or []:
        L.append('- Espera su aprobación el plan de «%s» (huella %s).' % (juego, huella))
    L.append('- Pasos del ciclo que corren sin Max: %d de %d (%d %%).' % (m['pasos_autonomos'], m['pasos_totales'], round(100 * m['pasos_autonomos'] / m['pasos_totales'])))
    L.append('- Toques de Max por mes (estimado del inventario, no medido): %s; de ellos evitables: %s. Con todas las reglas (las autorizadas y las propuestas) bajarían a %s; si solo se construye lo automatizable, a %s.'
             % (_num(m['toques_mes']), _num(m['toques_evitables_mes']), _num(m['toques_con_reglas_mes']), _num(m['toques_sin_automatizables_mes'])))
    for n, bloqueos in sorted(m['detenidos_por_dueno'].items()):
        L.append('- «%s» no corre solo todavía: falta %s.' % (n, ', '.join('«%s»' % b for b in bloqueos)))
    for a in avisos(raiz, hoy, m):
        L.append('- AVISO: ' + a)
    items = cola_items(raiz)
    if items:
        L.append('- Lo que la fábrica puede automatizar sin pedirle nada a Max (entra a la cola del motor): ' + '; '.join(i['titulo'].replace('Automatizar: ', '') for i in items) + '.')
    if not completo:
        L.append('- Detalle, reglas que Max podría autorizar y lo que solo él puede hacer: `python3 fabrica.py autonomia`.')
        return L
    por_autorizar = [x for x in cat.get('propuestas', []) if x.get('estado') == 'propuesta']
    if por_autorizar:
        L += ['', '## Reglas que Max podría autorizar (hoy NO están autorizadas)', '']
    for x in por_autorizar:
        L += ['**%s** (`%s`)' % (x['titulo'], x['id']), '- Cómo funciona: ' + x['como_funciona'], '- Qué ahorra: ' + x['ahorra'], '- Riesgo: ' + x['riesgo'],
              '- Cambia la política: %s. Hace falta: %s' % ('sí' if x['cambia_la_politica'] else 'no', x['requiere']), '']
    L += ['## Lo que Max ya autorizó', '']
    L += ['- %s (%s)' % (a['texto'], a['fecha']) for a in cat.get('autorizaciones_vigentes', [])]
    L += ['', '## Lo que solo Max puede hacer, una sola vez', '']
    for x in cat['pasos']:
        if x['quien'] == 'dueno' and x['frecuencia'] == 'una-vez' and x['estado'] == 'abierta':
            L.append('- %s — %s%s' % (x['titulo'], x['por_que'], (' Con eso corre solo: ' + ', '.join('«%s»' % d for d in x['desbloquea']) + '.') if x.get('desbloquea') else ''))
    L += ['', '## Cada vez que algo se publica o cambia, esto le toca a Max', '']
    for x in sorted((x for x in cat['pasos'] if x['quien'] == 'dueno' and x['frecuencia'] != 'una-vez' and x['estado'] == 'abierta'), key=lambda x: -x['veces_por_mes']):
        L.append('- [%s] %s (~%s al mes) — %s' % (x['clase'], x['titulo'], _num(x['veces_por_mes']), x['por_que']))
    L += ['', '## Límites que no cambian', '']
    L += ['- %s' % t for t in cat.get('limites', {}).values()]
    hist = historial(raiz)
    if hist:
        L += ['', '## Tendencia (una fila por semana, metricas/autonomia.csv)', '', '| Semana | Pasos sin Max | Toques por mes | Días aprobados por salir |', '|---|---|---|---|']
        L += ['| %s | %s de %s | %s | %s |' % (r['semana'], r['pasos_autonomos'], r['pasos_totales'], r['toques_mes'], r['dias_aprobados']) for r in hist[-8:]]
    return L
