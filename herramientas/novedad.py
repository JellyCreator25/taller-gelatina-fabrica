"""Comprobador de novedad: la fábrica no publica variantes en serie.

Las plataformas rechazan los «reskins» (el mismo juego con otro tema) y la producción en masa de páginas casi iguales. La respuesta correcta no es
esquivar esa regla sino cumplirla: cada juego que sale como juego aparte tiene que ser, de verdad, otro juego. Aquí se mide con hechos que cualquiera
puede revisar: la mecánica de cada juego se declara en `juego.json` («mecanica») con valores de `catalogo/vocabulario.json`.

Tres ejes forman el NÚCLEO: género, verbo (lo que el jugador hace una y otra vez) y objetivo.
  · los tres iguales a los de otro juego de la fábrica  → «variante»: no se publica como juego aparte; sus cambios van como paquete o modo del original
  · cambian el género y al menos otro eje del núcleo     → «distinto»
  · cualquier otro caso                                   → «parecido»: se puede publicar en el sitio propio y en redes, pero no en portales
Cambiar tema, colores, personajes o textos no cuenta. Además se avisa si las fichas de dos juegos tienen textos casi idénticos.

Lo que NO hace: no compara con juegos de fuera de la fábrica. Eso lo cubren `originalidad.referencias` y `originalidad.riesgo_portales`, que se declaran a mano,
y la decisión final siempre es de cada plataforma."""
import json
import pathlib
import re

NUCLEO = ('genero', 'verbo', 'objetivo')
OTROS_EJES = ('entrada', 'progresion')
GRAVEDAD = {'distinto': 1, 'parecido': 2, 'variante': 3}
LISTAS = ('entrada',)


def cargar_vocabulario(raiz):
    return json.loads((pathlib.Path(raiz) / 'catalogo' / 'vocabulario.json').read_text(encoding='utf-8'))


def cargar_juegos(raiz):
    """Todas las fichas de la fábrica (sin salir del programa si una está mal)."""
    juegos = {}
    for ruta in sorted((pathlib.Path(raiz) / 'juegos').glob('*/juego.json')):
        try:
            juegos[ruta.parent.name] = json.loads(ruta.read_text(encoding='utf-8'))
        except ValueError:
            juegos[ruta.parent.name] = {'id': ruta.parent.name, '_ilegible': True}
    return juegos


def pendientes(spec):
    """Rutas de los campos de la ficha que todavía dicen PENDIENTE (los dejó el andamio para que el autor los complete)."""
    salida = []

    def ver(o, ruta):
        if isinstance(o, str):
            if 'PENDIENTE' in o:
                salida.append(ruta)
        elif isinstance(o, dict):
            for k, v in o.items():
                ver(v, ruta + '.' + str(k) if ruta else str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                ver(v, '%s[%d]' % (ruta, i))
    ver(spec, '')
    return salida


def _vals(m, eje):
    v = (m or {}).get(eje)
    if isinstance(v, list):
        return frozenset(v)
    return frozenset([v]) if v else frozenset()


def _orden(spec):
    return ((spec.get('lanzamiento') or {}).get('orden', 999), spec.get('id', ''))


def validar_mecanica(spec, vocab, raiz=None, requerir_todo=True):
    """Lista de problemas de la sección «mecanica» de una ficha (o de una idea, con requerir_todo=False)."""
    nombre = spec.get('id', '(sin id)')
    m = spec.get('mecanica')
    if not isinstance(m, dict):
        return ['%s: falta la sección «mecanica» (género, verbo, objetivo…)' % nombre]
    p = []
    for eje in NUCLEO + (OTROS_EJES if requerir_todo else ()):
        if not m.get(eje):
            p.append('%s: mecanica.%s es obligatorio' % (nombre, eje))
            continue
        for v in (m[eje] if isinstance(m[eje], list) else [m[eje]]):
            if v not in vocab['ejes'][eje]:
                p.append('%s: mecanica.%s = «%s» no está en catalogo/vocabulario.json (valores: %s). Si de verdad es una categoría nueva, se añade allí con su motivo.'
                         % (nombre, eje, v, ', '.join(sorted(vocab['ejes'][eje]))))
    if requerir_todo:
        for libre in ('ambientacion', 'arte'):
            if not str(m.get(libre, '')).strip():
                p.append('%s: mecanica.%s es obligatorio (texto corto, p. ej. «gelatina-vectorial»)' % (nombre, libre))
        if not isinstance(m.get('sistemas', []), list):
            p.append('%s: mecanica.sistemas debe ser una lista' % nombre)
    if raiz and spec.get('plantilla'):
        ruta = pathlib.Path(raiz) / 'plantillas' / spec['plantilla'] / 'plantilla.json'
        if ruta.exists():
            man = json.loads(ruta.read_text(encoding='utf-8'))
            distintos = [e for e in NUCLEO if m.get(e) and _vals(man, e) != _vals(m, e)]
            if distintos and not m.get('justificacion'):
                p.append('%s: usa la plantilla «%s» (%s) pero declara otro núcleo (%s): explica por qué en mecanica.justificacion'
                         % (nombre, spec['plantilla'], ' · '.join(str(man[e]) for e in NUCLEO), ', '.join(distintos)))
    return p


def _palabras(spec):
    ficha = (spec.get('ficha') or {})
    idioma = (spec.get('idiomas') or ['es'])[0]
    f = ficha.get(idioma) or {}
    return re.findall(r'\w+', (f.get('corta', '') + ' ' + f.get('larga', '')).lower())


def similitud_texto(a, b, n=4):
    """Parecido (0 a 1) entre los textos de dos fichas: proporción de grupos de n palabras en común."""
    def grupos(spec):
        w = _palabras(spec)
        return {tuple(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}
    ga, gb = grupos(a), grupos(b)
    return len(ga & gb) / len(ga | gb) if ga and gb else 0.0


def comparar(a, b):
    """Compara dos fichas (o ideas) por su núcleo."""
    ma, mb = a.get('mecanica') or {}, b.get('mecanica') or {}
    distintos = [e for e in NUCLEO if _vals(ma, e) != _vals(mb, e)]
    if not distintos:
        v = 'variante'
    elif 'genero' in distintos and len(distintos) >= 2:
        v = 'distinto'
    else:
        v = 'parecido'
    misma_marca = bool(ma.get('arte')) and ma.get('arte') == mb.get('arte')
    return {'con': b.get('id', '?'), 'veredicto': v, 'nucleo_distinto': distintos, 'misma_marca_visual': misma_marca,
            'texto_parecido': round(similitud_texto(a, b), 2)}


def evaluar(raiz, juego_id=None, spec=None):
    """Evalúa un juego de la fábrica (por id) o una ficha/idea suelta (spec). Devuelve un diccionario con errores, avisos, comparaciones y aptitud por canal."""
    vocab = cargar_vocabulario(raiz)
    juegos = cargar_juegos(raiz)
    es_idea = spec is not None
    spec = spec if es_idea else juegos[juego_id]
    errores = validar_mecanica(spec, vocab, None if es_idea else raiz, requerir_todo=not es_idea)
    avisos, comparaciones = [], []
    resultado = {'id': spec.get('id'), 'errores': errores, 'avisos': avisos, 'comparaciones': comparaciones}
    if errores:
        resultado.update(veredicto='sin evaluar', apto={'sitio': False, 'redes': False, 'portales': False}, motivos=['La ficha de mecánica tiene errores.'], padre=None)
        return resultado
    peor, padre = 'distinto', None
    for oid, o in juegos.items():
        if oid == spec.get('id') or o.get('_ilegible') or not isinstance(o.get('mecanica'), dict):
            continue
        c = comparar(spec, o)
        c['anterior'] = es_idea or _orden(o) < _orden(spec)   # el que salió antes es el original
        comparaciones.append(c)
        if c['texto_parecido'] >= 0.25:
            avisos.append('Los textos de la ficha se parecen mucho a los de «%s» (%d %% de grupos de 4 palabras iguales): reescríbelos con lo que hace propio a este juego.' % (oid, c['texto_parecido'] * 100))
        if c['veredicto'] != 'distinto' and c['anterior'] and GRAVEDAD[c['veredicto']] > GRAVEDAD[peor]:
            peor, padre = c['veredicto'], oid
    orig = spec.get('originalidad') or {}
    riesgo = orig.get('riesgo_portales')
    motivos = []
    apto = {'sitio': peor != 'variante', 'redes': peor != 'variante', 'portales': peor == 'distinto'}
    if peor == 'variante':
        motivos.append('Es una variante de «%s» (mismo género, verbo y objetivo): no se publica como juego aparte; sus cambios van como paquete o modo de «%s».' % (padre, padre))
    elif peor == 'parecido':
        motivos.append('Se parece demasiado a «%s» para un portal: cambia el género y al menos otro eje del núcleo, o publícalo solo en el sitio propio y en redes.' % padre)
    if apto['portales'] and riesgo == 'alto':
        apto['portales'] = False
        motivos.append('Riesgo «alto» de ser visto como clon de un juego de fuera (%s): no se envía a portales.' % (', '.join(orig.get('referencias', [])) or 'sin referencias declaradas'))
    if riesgo not in ('bajo', 'medio', 'alto') and not es_idea:
        avisos.append('Falta originalidad.riesgo_portales (bajo, medio o alto).')
    if apto['portales'] and not all(((orig.get('diferenciador') or {}).get(i) or '').strip() for i in (spec.get('idiomas') or [])) and not es_idea:
        apto['portales'] = False
        motivos.append('Falta originalidad.diferenciador en algún idioma: sin decir qué hace propio al juego no se envía a portales.')
    if riesgo == 'medio':
        avisos.append('Riesgo «medio» frente a juegos de fuera (%s): en portales hay que poder enseñar qué lo hace propio.' % (', '.join(orig.get('referencias', [])) or 'sin referencias'))
    marcas = [c['con'] for c in comparaciones if c['misma_marca_visual']]
    if marcas:
        avisos.append('Comparte el estilo visual con %s: es una marca común, pero muchos juegos con la misma apariencia pueden parecer «de plantilla» en portales.' % ', '.join('«%s»' % m for m in marcas))
    if not es_idea:
        pend = pendientes(spec)
        if pend:
            apto = {k: False for k in apto}
            motivos.append('Quedan %d campos con PENDIENTE en la ficha (por ejemplo %s): hay que completarlos antes de publicar.' % (len(pend), ', '.join(pend[:3])))
    resultado.update(veredicto=peor, padre=padre, apto=apto, motivos=motivos)
    return resultado


ETIQUETA_EJE = {'genero': 'género', 'verbo': 'verbo', 'objetivo': 'objetivo'}
NOMBRE_CANAL = {'sitio': 'sitio propio', 'redes': 'redes', 'portales': 'portales e itch.io'}


def informe(r):
    L = ['[novedad] %s → %s' % (r['id'], r['veredicto'].upper())]
    for e in r['errores']:
        L.append('  ERROR %s' % e)
    for c in r['comparaciones']:
        extra = (' (cambian %s)' % ', '.join(ETIQUETA_EJE[e] for e in c['nucleo_distinto'])) if c['nucleo_distinto'] else ' (género, verbo y objetivo iguales)'
        L.append('  frente a «%s»: %s%s%s' % (c['con'], c['veredicto'], extra, '' if c['anterior'] else ' · sale después que este'))
    if not r['errores']:
        L.append('  apto para: ' + ' · '.join('%s %s' % (NOMBRE_CANAL[k], 'sí' if v else 'NO') for k, v in r['apto'].items()))
    for m in r['motivos']:
        L.append('  ' + m)
    for a in r['avisos']:
        L.append('  aviso: ' + a)
    return '\n'.join(L)


def cargar_ideas(raiz):
    ruta = pathlib.Path(raiz) / 'ideas' / 'ideas.json'
    return json.loads(ruta.read_text(encoding='utf-8')) if ruta.exists() else {'ideas': []}


def evaluar_ideas(raiz):
    """Cada idea del cuaderno de ideas frente a los juegos de la fábrica (sirve para decidir qué plantilla construir después)."""
    salida = []
    for idea in cargar_ideas(raiz)['ideas']:
        spec = {'id': idea['id'], 'mecanica': idea['mecanica'], 'originalidad': {'riesgo_portales': idea.get('riesgo_estimado'), 'referencias': idea.get('referencias', [])},
                'ficha': {}, 'idiomas': ['es']}
        salida.append((idea, evaluar(raiz, spec=spec)))
    return salida
