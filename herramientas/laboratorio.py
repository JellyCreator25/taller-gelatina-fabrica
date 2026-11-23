"""Laboratorio de betas: el órgano del motor para probar una beta (de un juego, de una página, de un texto, de un cambio de interfaz) de forma aislada, extensa y comparable.

Qué hace: toma un EXPERIMENTO (un archivo declarativo en laboratorio/experimentos/ID.json), lo cruza con PERFILES de persona (aparato, entrada, idioma, ritmo, paciencia,
puntería, interrupciones, red, CPU: laboratorio/perfiles.json) y con VARIANTES (cambios de mecánica, de texto, de estilo o de página) y juega cada combinación en un contexto de
navegador NUEVO: sin cookies ni almacenamiento, con la red cortada (solo el servidor local de la variante), con el azar fijado por semilla y con el reloj fijo. Cada celda
devuelve telemetría (embudo, abandono, tiempo hasta la primera acción, errores, accesibilidad, determinismo) y este módulo la junta en un informe que se puede comparar entre
variantes (A/B) y entre versiones de la misma beta.

Qué dice un perfil y qué NO: dice dónde se traba, se confunde o se rinde una persona con ESAS condiciones y ESE temple, y qué se rompe en ese aparato. NO dice si a la gente le va a
gustar ni cuántos van a venir: los perfiles son arquetipos de condiciones y de conducta, no personas ni una muestra de la población. Igual que las banderas de los bots,
las del laboratorio se muestran, pero no cambian el puntaje del ranking.

Dos mitades del informe: lo DETERMINISTA (metricas/laboratorio/ID.json, reproducible: mismas semillas y misma beta, mismo archivo; es lo que se guarda en el repositorio) y lo MEDIDO
(metricas/laboratorio/ID.medido.json: tiempos reales de esta computadora; es ruido útil, se queda local y nunca decide una bandera de falla).

Banderas (nivel «falla» = algo está roto y el comando termina con error; «aviso» = que lo mire una persona):
  falla  no-determinista        la misma semilla, el mismo perfil y la misma variante dieron otra traza
  falla  fallas-de-pagina       errores de consola o excepciones en la página
  falla  recurso-faltante       la página pidió un archivo local que no existe (404): una imagen, un script, una fuente
  falla  contexto-sucio         una sesión empezó con almacenamiento o cookies que no eran suyas (el aislamiento falló)
  falla  verificacion-fallida   un paso «verificar» del guion no se cumplió (es un error de la beta, no un abandono de la persona)
  falla  error-interno          el laboratorio no pudo correr la celda (página que no carga, tiempo agotado…)
  falla  imposible              nadie, con ningún perfil, completó una prueba de guion en una variante
  aviso  abandono-alto          una de cada tres sesiones (o más) de un perfil se rinde
  aviso  bloqueado-para-perfil  un perfil no completa nunca algo que otros perfiles sí completan
  aviso  carga-lenta            sesiones que se rinden porque la página (modelada) tarda más que su paciencia
  aviso  red-externa            la beta intentó llegar a internet (debería ser autocontenida; el laboratorio lo cortó)
  aviso  a11y-CÓDIGO            problema de accesibilidad o de uso en pantalla (objetivo chico, contraste, texto chico, sin nombre, desborde…)
  falla/aviso  bots-CÓDIGO      las banderas del órgano de bots (motor/BOTS.md), vistas con el temple de cada perfil"""
import copy
import hashlib
import json
import math
import os
import pathlib
import re
import statistics
import subprocess
import tempfile

import bots as _bots

FORMATO = 1
PRUEBAS_TIPOS = ('auditoria', 'guion', 'bots')
VERBOS = ('esperar', 'esperar_hasta', 'tocar', 'arrastrar', 'mantener', 'tecla', 'escribir', 'leer', 'verificar', 'pasar', 'interrumpir', 'repetir')
CLAVES_COMUNES = ('id', 'embudo', 'pausa', 'paciencia', 'opcional', 'si')
CLAVES_VARIANTE = ('id', 'nota', 'consulta', 'html', 'juego', 'css', 'reemplazos')
CLAVES_EXPERIMENTO = ('formato', 'id', 'titulo', 'pregunta', 'objeto', 'variantes', 'perfiles', 'pruebas', 'umbrales', 'semilla_base')
CLAVES_PRUEBA = {'auditoria': ('id', 'tipo', 'observar_ms'), 'guion': ('id', 'tipo', 'semillas', 'pasos'), 'bots': ('id', 'tipo', 'politicas', 'partidas')}
UMBRALES = {'abandono': 0.30, 'bloqueo': 0.50}
ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,62}$')
DATO_RE = re.compile(r'^[a-z][a-z0-9_]{0,40}$')
TOPE_CELDAS = 4000

PERFIL_BASE = {
    'nombre': '', 'descripcion': '',
    'dispositivo': {'ancho': 1280, 'alto': 720, 'escala': 1, 'tactil': False, 'movil': False},
    'entrada': None,
    'idioma': 'es-MX', 'zona': 'America/Mexico_City',
    'ambiente': {'tema': 'claro', 'movimiento_reducido': False},
    'cpu': 1,
    'red': {'latencia_ms': 40, 'bajada_kbps': 20000},
    'conducta': {'ritmo': 1.0, 'reaccion_ms': 250, 'paciencia_ms': 8000, 'paciencia_carga_ms': 6000, 'temblor': 1.0, 'punteria_px': 1.0, 'interrupciones': []},
}


class ErrorLaboratorio(Exception):
    pass


# ---------------------------------------------------------------- perfiles
def _mezclar(base, extra):
    salida = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(salida.get(k), dict):
            salida[k] = _mezclar(salida[k], v)
        else:
            salida[k] = copy.deepcopy(v)
    return salida


def normalizar_perfil(p):
    """Completa un perfil con los valores por omisión y valida lo que importa. Devuelve un perfil nuevo; no cambia el original."""
    if not isinstance(p, dict) or not ID_RE.match(str(p.get('id', ''))):
        raise ErrorLaboratorio('un perfil necesita «id» en minúsculas, números y guiones')
    conocidas = set(PERFIL_BASE) | {'id'}
    raras = sorted(set(p) - conocidas)
    if raras:
        raise ErrorLaboratorio('perfil «%s»: campos desconocidos: %s' % (p['id'], ', '.join(raras)))
    r = _mezclar(PERFIL_BASE, p)
    d, c, red = r['dispositivo'], r['conducta'], r['red']
    for sec, base in (('dispositivo', PERFIL_BASE['dispositivo']), ('ambiente', PERFIL_BASE['ambiente']), ('red', PERFIL_BASE['red']), ('conducta', PERFIL_BASE['conducta'])):
        if set(r[sec]) - set(base):
            raise ErrorLaboratorio('perfil «%s»: «%s» no admite: %s' % (p['id'], sec, ', '.join(sorted(set(r[sec]) - set(base)))))
    if r['entrada'] is None:
        r['entrada'] = 'tactil' if d['tactil'] else 'raton'
    if r['entrada'] not in ('raton', 'tactil', 'teclado'):
        raise ErrorLaboratorio('perfil «%s»: «entrada» debe ser raton, tactil o teclado' % p['id'])
    if r['entrada'] == 'tactil' and not d['tactil']:
        raise ErrorLaboratorio('perfil «%s»: entrada táctil pide dispositivo.tactil verdadero' % p['id'])
    if not (200 <= d['ancho'] <= 3840 and 200 <= d['alto'] <= 3840 and d['escala'] in (1, 1.5, 2, 3)):
        raise ErrorLaboratorio('perfil «%s»: tamaño de pantalla fuera de rango' % p['id'])
    if r['ambiente']['tema'] not in ('claro', 'oscuro'):
        raise ErrorLaboratorio('perfil «%s»: ambiente.tema debe ser claro u oscuro' % p['id'])
    if not (1 <= r['cpu'] <= 20):
        raise ErrorLaboratorio('perfil «%s»: cpu va de 1 (normal) a 20 (muy lenta)' % p['id'])
    if red['latencia_ms'] < 0 or red['bajada_kbps'] <= 0:
        raise ErrorLaboratorio('perfil «%s»: red sin sentido' % p['id'])
    if not (0.1 <= c['ritmo'] <= 10) or c['reaccion_ms'] < 0 or c['paciencia_ms'] <= 0 or c['paciencia_carga_ms'] <= 0 or c['temblor'] < 0 or c['punteria_px'] < 0:
        raise ErrorLaboratorio('perfil «%s»: conducta fuera de rango' % p['id'])
    for it in c['interrupciones']:
        if not (isinstance(it, dict) and set(it) == {'tras_acciones', 'ms'} and it['tras_acciones'] >= 0 and 0 < it['ms'] <= 600000):
            raise ErrorLaboratorio('perfil «%s»: cada interrupción es {"tras_acciones": N, "ms": M}' % p['id'])
    return r


def ruta_perfiles(raiz):
    return pathlib.Path(raiz) / 'laboratorio' / 'perfiles.json'


def cargar_perfiles(raiz):
    """El catálogo de perfiles {id: perfil normalizado}. Los ids no se repiten."""
    ruta = ruta_perfiles(raiz)
    if not ruta.exists():
        raise ErrorLaboratorio('falta el catálogo de perfiles (laboratorio/perfiles.json)')
    datos = json.loads(ruta.read_text(encoding='utf-8'))
    lista = datos.get('perfiles') if isinstance(datos, dict) else None
    if not isinstance(lista, list) or not lista:
        raise ErrorLaboratorio('laboratorio/perfiles.json debe traer una lista «perfiles»')
    salida = {}
    for p in lista:
        n = normalizar_perfil(p)
        if n['id'] in salida:
            raise ErrorLaboratorio('perfil repetido: «%s»' % n['id'])
        salida[n['id']] = n
    return salida


# ---------------------------------------------------------------- experimentos
def carpeta_experimentos(raiz):
    return pathlib.Path(raiz) / 'laboratorio' / 'experimentos'


def ids_de_experimentos(raiz):
    return sorted(p.stem for p in carpeta_experimentos(raiz).glob('*.json'))


def cargar_experimento(raiz, exp_id):
    ruta = carpeta_experimentos(raiz) / ('%s.json' % exp_id)
    if not ruta.exists():
        raise ErrorLaboratorio('no existe el experimento «%s» (los que hay: %s)' % (exp_id, ', '.join(ids_de_experimentos(raiz)) or 'ninguno'))
    try:
        return json.loads(ruta.read_text(encoding='utf-8'))
    except ValueError as e:
        raise ErrorLaboratorio('«%s» no es JSON válido: %s' % (ruta.name, e))


def _validar_paso(paso, donde, errores):
    if not isinstance(paso, dict):
        errores.append('%s: un paso es un objeto' % donde)
        return
    verbos = [v for v in VERBOS if v in paso]
    if len(verbos) != 1:
        errores.append('%s: un paso lleva exactamente un verbo (%s); trae %s' % (donde, ', '.join(VERBOS), verbos or 'ninguno'))
        return
    v = verbos[0]
    raras = sorted(set(paso) - set(CLAVES_COMUNES) - {v} - ({'max_ms', 'falla_si_no'} if v == 'esperar_hasta' else set()) - ({'veces'} if v == 'tecla' else set()))
    if raras:
        errores.append('%s: claves que no corresponden: %s' % (donde, ', '.join(raras)))
    for k in ('pausa', 'paciencia'):
        if k in paso and not (isinstance(paso[k], (int, float)) and paso[k] >= 0):
            errores.append('%s: «%s» es un número de milisegundos ≥ 0' % (donde, k))
    if 'si' in paso:
        s = paso['si']
        if not (isinstance(s, dict) and s and set(s) <= {'entrada', 'dispositivo'}):
            errores.append('%s: «si» admite entrada y dispositivo' % donde)
        else:
            ent = [s['entrada']] if isinstance(s.get('entrada'), str) else s.get('entrada', [])
            if any(e not in ('raton', 'tactil', 'teclado') for e in ent) or (s.get('dispositivo') not in (None, 'tactil', 'escritorio')):
                errores.append('%s: «si» con valores desconocidos' % donde)
    val = paso[v]
    if v in ('esperar', 'tocar', 'tecla', 'esperar_hasta') and not (isinstance(val, str) and val.strip()):
        errores.append('%s: «%s» lleva un texto (selector, tecla o expresión)' % (donde, v))
    if v == 'pasar' and not (isinstance(val, (int, float)) and 0 < val <= 600000):
        errores.append('%s: «pasar» son milisegundos (1 a 600000)' % donde)
    if v == 'interrumpir' and not (isinstance(val, (int, float)) and 0 < val <= 600000):
        errores.append('%s: «interrumpir» son milisegundos (1 a 600000)' % donde)
    if v == 'tecla' and 'veces' in paso:
        n = paso['veces']
        bien = (isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= 200) or (isinstance(n, dict) and set(n) == {'min', 'max'} and all(isinstance(x, int) and 0 <= x <= 200 for x in n.values()) and n['min'] <= n['max'])
        if not bien:
            errores.append('%s: «veces» es un entero de 1 a 200 o {"min": a, "max": b} (azar con la semilla de la sesión)' % donde)
    if v in ('tocar',):
        _validar_punto(val, donde + '.tocar', errores)
    if v == 'mantener':
        if not (isinstance(val, dict) and set(val) <= {'en', 'ms'} and 'en' in val and isinstance(val.get('ms'), (int, float)) and 0 < val['ms'] <= 600000):
            errores.append('%s: «mantener» es {"en": punto, "ms": milisegundos}' % donde)
        else:
            _validar_punto(val['en'], donde + '.mantener.en', errores)
    if v == 'arrastrar':
        if not (isinstance(val, dict) and set(val) <= {'desde', 'hasta', 'pasos'} and 'desde' in val and 'hasta' in val):
            errores.append('%s: «arrastrar» es {"desde": punto, "hasta": punto, "pasos": N}' % donde)
        else:
            _validar_punto(val['desde'], donde + '.arrastrar.desde', errores)
            _validar_punto(val['hasta'], donde + '.arrastrar.hasta', errores)
            if 'pasos' in val and not (isinstance(val['pasos'], int) and 1 <= val['pasos'] <= 100):
                errores.append('%s: «pasos» va de 1 a 100' % donde)
    if v == 'escribir' and not (isinstance(val, dict) and set(val) == {'selector', 'texto'} and isinstance(val['selector'], str) and isinstance(val['texto'], str)):
        errores.append('%s: «escribir» es {"selector": …, "texto": …}' % donde)
    if v == 'leer' and not (isinstance(val, dict) and set(val) == {'id', 'js'} and DATO_RE.match(str(val.get('id', ''))) and isinstance(val['js'], str)):
        errores.append('%s: «leer» es {"id": nombre (minúsculas, números y guion bajo), "js": expresión}' % donde)
    if v == 'verificar' and not (isinstance(val, dict) and set(val) <= {'js', 'mensaje', 'espera'} and isinstance(val.get('js'), str) and isinstance(val.get('espera', 0), (int, float)) and 0 <= val.get('espera', 0) <= 60000):
        errores.append('%s: «verificar» es {"js": expresión, "mensaje": texto, "espera": milisegundos (opcional)}' % donde)
    if v == 'repetir':
        if not (isinstance(val, dict) and set(val) <= {'hasta', 'maximo', 'pasos'} and isinstance(val.get('maximo'), int) and 1 <= val['maximo'] <= 200 and isinstance(val.get('pasos'), list) and val['pasos']):
            errores.append('%s: «repetir» es {"hasta": expresión, "maximo": N (1 a 200), "pasos": [...]}' % donde)
        else:
            for i, sub in enumerate(val['pasos']):
                _validar_paso(sub, '%s.repetir[%d]' % (donde, i + 1), errores)


def _validar_punto(val, donde, errores):
    if isinstance(val, str):
        return
    if not (isinstance(val, dict) and isinstance(val.get('selector'), str) and set(val) <= {'selector', 'x', 'y', 'js', 'ref'}):
        errores.append('%s: un punto es un selector o {"selector", "x", "y", "js", "ref"}' % donde)
        return
    for k in ('x', 'y'):
        if k in val and not (isinstance(val[k], (int, float)) and 0 <= val[k] <= 1):
            errores.append('%s: «%s» es una fracción de 0 a 1 de la caja del elemento' % (donde, k))
    if 'ref' in val and not (isinstance(val['ref'], list) and len(val['ref']) == 2 and all(isinstance(n, (int, float)) and n > 0 for n in val['ref'])):
        errores.append('%s: «ref» es [ancho, alto] del sistema de coordenadas que devuelve «js»' % donde)
    if 'js' in val and not isinstance(val['js'], str):
        errores.append('%s: «js» es una expresión de texto' % donde)


def validar(raiz, exp, perfiles=None):
    """Lista de errores del experimento (vacía si está bien). No corre nada."""
    raiz = pathlib.Path(raiz)
    errores = []
    if not isinstance(exp, dict):
        return ['el experimento debe ser un objeto JSON']
    raras = sorted(set(exp) - set(CLAVES_EXPERIMENTO))
    if raras:
        errores.append('claves desconocidas en el experimento: %s' % ', '.join(raras))
    if exp.get('formato') != FORMATO:
        errores.append('«formato» debe ser %d' % FORMATO)
    if not ID_RE.match(str(exp.get('id', ''))):
        errores.append('«id» en minúsculas, números y guiones')
    for k in ('titulo', 'pregunta'):
        if not (isinstance(exp.get(k), str) and len(exp[k].strip()) >= 8):
            errores.append('«%s» es obligatorio: escribe qué se quiere saber con este experimento' % k)
    obj = exp.get('objeto')
    plantilla = None
    if not (isinstance(obj, dict) and len(obj) == 1 and next(iter(obj)) in ('juego', 'html') and isinstance(next(iter(obj.values())), str)):
        errores.append('«objeto» es {"juego": id} o {"html": ruta dentro del repositorio}')
        control_html = None
    elif 'juego' in obj:
        ficha_ruta = raiz / 'juegos' / obj['juego'] / 'juego.json'
        control_html = raiz / 'salida' / obj['juego'] / 'index.html'
        if not ficha_ruta.exists():
            errores.append('el juego «%s» no existe' % obj['juego'])
        else:
            plantilla = json.loads(ficha_ruta.read_text(encoding='utf-8')).get('plantilla')
            if not control_html.exists():
                errores.append('«%s» no está construido: corre «python3 fabrica.py construir %s»' % (obj['juego'], obj['juego']))
    else:
        control_html = (raiz / obj['html']).resolve()
        if not str(control_html).startswith(str(raiz.resolve()) + os.sep) or control_html.suffix != '.html' or not control_html.is_file():
            errores.append('«objeto.html» debe ser un .html que exista dentro del repositorio (la beta se prueba desde un archivo local, nunca desde internet)')
    # variantes
    vs = exp.get('variantes')
    if not (isinstance(vs, list) and vs):
        errores.append('«variantes» es una lista con al menos una (la primera es el control)')
        vs = []
    vistos = set()
    for i, v in enumerate(vs):
        d = 'variante %d' % (i + 1)
        if not isinstance(v, dict) or not ID_RE.match(str(v.get('id', ''))):
            errores.append('%s: necesita «id»' % d)
            continue
        d = 'variante «%s»' % v['id']
        if v['id'] in vistos:
            errores.append('%s repetida' % d)
        vistos.add(v['id'])
        raras = sorted(set(v) - set(CLAVES_VARIANTE))
        if raras:
            errores.append('%s: claves desconocidas: %s' % (d, ', '.join(raras)))
        if 'juego' in v and not isinstance(v['juego'], dict):
            errores.append('%s: «juego» es un objeto que se mezcla en window.JUEGO (parametros, textos…)' % d)
        for k in ('css', 'consulta', 'nota'):
            if k in v and not isinstance(v[k], str):
                errores.append('%s: «%s» es texto' % (d, k))
        if 'html' in v:
            h = (raiz / str(v['html'])).resolve()
            if not str(h).startswith(str(raiz.resolve()) + os.sep) or h.suffix != '.html' or not h.is_file():
                errores.append('%s: «html» debe ser un .html que exista dentro del repositorio' % d)
        for j, r in enumerate(v.get('reemplazos') or []):
            if not (isinstance(r, dict) and set(r) <= {'buscar', 'poner', 'veces'} and isinstance(r.get('buscar'), str) and r['buscar'] and isinstance(r.get('poner'), str) and r.get('veces', 1) in (1, 'todas')):
                errores.append('%s: reemplazo %d es {"buscar": texto, "poner": texto, "veces": 1}' % (d, j + 1))
            elif control_html and 'html' not in v and control_html.is_file() and r['buscar'] not in control_html.read_text(encoding='utf-8'):
                errores.append('%s: el reemplazo %d no encuentra «%s» en la página (¿está mal escrito?)' % (d, j + 1, r['buscar'][:50]))
    # perfiles
    ps = exp.get('perfiles')
    if not (isinstance(ps, list) and ps):
        errores.append('«perfiles» es una lista de ids del catálogo (o perfiles completos)')
        ps = []
    try:
        catalogo = perfiles if perfiles is not None else cargar_perfiles(raiz)
    except ErrorLaboratorio as e:
        catalogo = {}
        errores.append(str(e))
    vp = set()
    for p in ps:
        try:
            n = normalizar_perfil(p) if isinstance(p, dict) else catalogo[p] if p in catalogo else None
            if n is None:
                errores.append('el perfil «%s» no está en laboratorio/perfiles.json' % p)
            elif n['id'] in vp:
                errores.append('perfil repetido en el experimento: «%s»' % n['id'])
            else:
                vp.add(n['id'])
        except ErrorLaboratorio as e:
            errores.append(str(e))
    # pruebas
    pr = exp.get('pruebas')
    if not (isinstance(pr, list) and pr):
        errores.append('«pruebas» es una lista con al menos una')
        pr = []
    vistas = set()
    for i, p in enumerate(pr):
        d = 'prueba %d' % (i + 1)
        if not isinstance(p, dict) or not ID_RE.match(str(p.get('id', ''))) or p.get('tipo') not in PRUEBAS_TIPOS:
            errores.append('%s: necesita «id» y «tipo» (%s)' % (d, ', '.join(PRUEBAS_TIPOS)))
            continue
        d = 'prueba «%s»' % p['id']
        if p['id'] in vistas:
            errores.append('%s repetida' % d)
        vistas.add(p['id'])
        raras = sorted(set(p) - set(CLAVES_PRUEBA[p['tipo']]))
        if raras:
            errores.append('%s: claves que no corresponden a una prueba «%s»: %s' % (d, p['tipo'], ', '.join(raras)))
        if p['tipo'] == 'guion':
            if 'semillas' in p and not (isinstance(p['semillas'], int) and 1 <= p['semillas'] <= 200):
                errores.append('%s: «semillas» va de 1 a 200' % d)
            if not (isinstance(p.get('pasos'), list) and p['pasos']):
                errores.append('%s: «pasos» es una lista con al menos un paso' % d)
            else:
                for j, s in enumerate(p['pasos']):
                    _validar_paso(s, '%s, paso %d' % (d, j + 1), errores)
        if p['tipo'] == 'auditoria' and 'observar_ms' in p and not (isinstance(p['observar_ms'], (int, float)) and 0 <= p['observar_ms'] <= 60000):
            errores.append('%s: «observar_ms» va de 0 a 60000' % d)
        if p['tipo'] == 'bots':
            if not (isinstance(obj, dict) and 'juego' in obj):
                errores.append('%s: la prueba «bots» solo corre sobre un juego (objeto.juego)' % d)
            elif plantilla and not _bots.politicas_de(raiz, plantilla).exists():
                errores.append('%s: la plantilla «%s» no define pruebas con bots (falta plantillas/%s/bots.js)' % (d, plantilla, plantilla))
            elif 'juego' in (obj or {}):
                ficha = json.loads((raiz / 'juegos' / obj['juego'] / 'juego.json').read_text(encoding='utf-8'))
                if 'bots' not in (ficha.get('motor') or []):
                    errores.append('%s: «%s» no declara el módulo «bots» en juego.json → motor' % (d, obj['juego']))
            if 'partidas' in p and not (isinstance(p['partidas'], (int, float)) and 0 < p['partidas'] <= 20):
                errores.append('%s: «partidas» es un factor de 0 a 20' % d)
            if 'politicas' in p and not (isinstance(p['politicas'], list) and all(isinstance(x, str) for x in p['politicas'])):
                errores.append('%s: «politicas» es una lista de nombres' % d)
    um = exp.get('umbrales')
    if um is not None and not (isinstance(um, dict) and set(um) <= set(UMBRALES) and all(isinstance(x, (int, float)) and 0 < x <= 1 for x in um.values())):
        errores.append('«umbrales» admite: %s (fracciones de 0 a 1)' % ', '.join(sorted(UMBRALES)))
    if exp.get('semilla_base') is not None and not (isinstance(exp['semilla_base'], int) and 0 <= exp['semilla_base'] <= 10 ** 9):
        errores.append('«semilla_base» es un entero')
    return errores


# ---------------------------------------------------------------- plan
def _huella_archivo(ruta):
    return hashlib.sha256(pathlib.Path(ruta).read_bytes()).hexdigest()


def planear(raiz, exp, perfiles, factor=1.0, semilla_base=None, solo_perfiles=None, solo_pruebas=None, determinismo=True):
    """Expande el experimento en celdas (variante × perfil × prueba × semilla) y arma lo que lee herramientas/laboratorio.js. Función sin efectos (las pruebas la usan)."""
    raiz = pathlib.Path(raiz)
    semilla = exp.get('semilla_base', 1000) if semilla_base is None else semilla_base
    obj = exp['objeto']
    control = (raiz / 'salida' / obj['juego'] / 'index.html') if 'juego' in obj else (raiz / obj['html'])
    vs = []
    for v in exp['variantes']:
        vs.append({'id': v['id'], 'html': str((raiz / v['html']) if 'html' in v else control), 'consulta': v.get('consulta', ''), 'juego': v.get('juego'),
                   'css': v.get('css', ''), 'reemplazos': [{'buscar': r['buscar'], 'poner': r['poner'], 'veces': 1 if r.get('veces', 1) == 1 else 0} for r in v.get('reemplazos') or []]})
    lista = []
    for p in exp['perfiles']:
        lista.append(normalizar_perfil(p) if isinstance(p, dict) else copy.deepcopy(perfiles[p]))
    if solo_perfiles:
        faltan = sorted(set(solo_perfiles) - {p['id'] for p in lista})
        if faltan:
            raise ErrorLaboratorio('el experimento no usa el perfil: %s' % ', '.join(faltan))
        lista = [p for p in lista if p['id'] in solo_perfiles]
    pruebas = [p for p in exp['pruebas'] if not solo_pruebas or p['id'] in solo_pruebas]
    if solo_pruebas and len(pruebas) != len(set(solo_pruebas)):
        raise ErrorLaboratorio('el experimento no tiene la prueba: %s' % ', '.join(sorted(set(solo_pruebas) - {p['id'] for p in exp['pruebas']})))
    celdas = []
    for v in exp['variantes']:
        for perfil in lista:
            for p in pruebas:
                if p['tipo'] == 'bots':
                    ruta = _bots.politicas_de(raiz, json.loads((raiz / 'juegos' / obj['juego'] / 'juego.json').read_text(encoding='utf-8'))['plantilla'])
                    celdas.append({'variante': v['id'], 'perfil': perfil, 'semilla': semilla, 'repeticion': False,
                                   'prueba': {'id': p['id'], 'tipo': 'bots', 'bots_js': str(ruta), 'politicas': p.get('politicas'), 'factor': float(p.get('partidas', 1)) * factor, 'semilla_base': semilla}})
                    continue
                n = 1 if p['tipo'] == 'auditoria' else max(1, int(round(p.get('semillas', 5) * factor)))
                base = {'id': p['id'], 'tipo': p['tipo']}
                if p['tipo'] == 'guion':
                    base['pasos'] = p['pasos']
                else:
                    base['observar_ms'] = p.get('observar_ms', 3000)
                for i in range(n):
                    celdas.append({'variante': v['id'], 'perfil': perfil, 'prueba': base, 'semilla': semilla + i, 'repeticion': False})
                if determinismo:
                    celdas.append({'variante': v['id'], 'perfil': perfil, 'prueba': base, 'semilla': semilla, 'repeticion': True})
    if len(celdas) > TOPE_CELDAS:
        raise ErrorLaboratorio('el experimento pide %d celdas (el tope es %d): baja las semillas, los perfiles o las variantes' % (len(celdas), TOPE_CELDAS))
    return {'variantes': vs, 'celdas': celdas, 'concurrencia': 4, 'semilla_base': semilla, 'factor': factor, 'pruebas': pruebas, 'perfiles': lista}


# ---------------------------------------------------------------- estadística
def wilson(k, n, z=1.96):
    """Intervalo de Wilson al 95 % para una proporción (sirve con muestras chicas)."""
    if n <= 0:
        return [0.0, 1.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - m), 4), round(min(1.0, c + m), 4)]


def _no_se_cruzan(a, b):
    return a[1] < b[0] or b[1] < a[0]


def _p(valores, q):
    if not valores:
        return None
    v = sorted(valores)
    i = min(len(v) - 1, max(0, int(math.ceil(q * len(v))) - 1))
    return v[i]


def _numero(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# ---------------------------------------------------------------- agregación
def _agregar_datos(sesiones):
    """Lo que el guion leyó de la página (pasos «leer»): mediana si es número, reparto si es texto o sí/no; un diccionario se aplana como campo.clave."""
    num, cat = {}, {}

    def poner(k, v):
        if _numero(v):
            num.setdefault(k, []).append(v)
        elif isinstance(v, (str, bool)):
            cat.setdefault(k, {}).setdefault(str(v).lower() if isinstance(v, bool) else v, 0)
            cat[k][str(v).lower() if isinstance(v, bool) else v] += 1
        elif isinstance(v, dict):
            for k2, v2 in v.items():
                poner('%s.%s' % (k, k2), v2)
    for s in sesiones:
        for k, v in (s.get('datos') or {}).items():
            poner(k, v)
    salida = {k: {'p50': _p(vs, 0.5), 'n': len(vs)} for k, vs in sorted(num.items())}
    for k, d in sorted(cat.items()):
        salida[k] = {'reparto': dict(sorted(d.items(), key=lambda x: (-x[1], str(x[0]))))}
    return salida


def _grupo_sesiones(clave, tipo, sesiones, repeticiones):
    n = len(sesiones)
    estados = {'completo': 0, 'abandono': 0, 'falla': 0}
    for s in sesiones:
        estados[s['estado']] = estados.get(s['estado'], 0) + 1
    completas = estados['completo']
    abandonos = {}
    for s in sesiones:
        if s['estado'] == 'abandono' and s.get('abandono'):
            k = '%s: %s' % (s['abandono']['paso'], s['abandono']['motivo'])
            abandonos[k] = abandonos.get(k, 0) + 1
    # embudo: las etapas en el orden en que aparecen; cuántas sesiones llegaron y cuándo (tiempo simulado)
    orden, llegaron = [], {}
    for s in sesiones:
        for i, e in enumerate(s.get('embudo') or []):
            if e['etapa'] not in llegaron:
                orden.append(e['etapa'])
                llegaron[e['etapa']] = []
            llegaron[e['etapa']].append(e['t'])
    embudo = [{'etapa': e, 'alcanzaron': len(llegaron[e]), 'p50_ms': _p(llegaron[e], 0.5)} for e in orden]
    errores = {}
    for s in sesiones:
        for tipo_e, textos in (s.get('errores') or {}).items():
            for t in textos:
                errores.setdefault((tipo_e, t), set()).add(s['cell']['semilla'])
    a11y = {}
    for s in sesiones:
        for a in s.get('a11y') or []:
            d = a11y.setdefault(a['codigo'], {'codigo': a['codigo'], 'sesiones': 0, 'ejemplo': a.get('ejemplo', '')})
            d['sesiones'] += 1
    primeras = [s['primera_accion_ms'] for s in sesiones if s.get('primera_accion_ms') is not None]
    malo = next((s for s in sesiones if s['estado'] != 'completo'), None)
    reps = {r['cell']['semilla']: r for r in repeticiones}
    deterministas = [r['traza'] == next((s['traza'] for s in sesiones if s['cell']['semilla'] == sem), None) for sem, r in reps.items()]
    g = {'variante': clave[0], 'perfil': clave[1], 'prueba': clave[2], 'tipo': tipo, 'sesiones': n, 'completaron': completas, 'abandonaron': estados['abandono'], 'fallaron': estados['falla'],
         'tasa_completa': round(completas / n, 4) if n else 0, 'tasa_ic': wilson(completas, n), 'tasa_abandono': round(estados['abandono'] / n, 4) if n else 0,
         'embudo': embudo, 'abandonos_en': dict(sorted(abandonos.items(), key=lambda x: (-x[1], x[0]))),
         'primera_accion_p50_ms': _p(primeras, 0.5), 'carga_modelada_ms': _p([s['carga_modelada_ms'] for s in sesiones if s.get('carga_modelada_ms')], 0.5),
         'peso_bytes': _p([s['peso_bytes'] for s in sesiones if s.get('peso_bytes')], 0.5), 'ms_simulados_p50': _p([s.get('ms_simulados', 0) for s in sesiones], 0.5),
         'errores': [{'tipo': t, 'texto': x, 'sesiones': len(v)} for (t, x), v in sorted(errores.items(), key=lambda kv: (kv[0][0], kv[0][1]))],
         'a11y': [a11y[k] for k in sorted(a11y)], 'determinista': all(deterministas) if deterministas else None,
         'datos': _agregar_datos(sesiones), 'ejemplo_de_fallo': None}
    if malo:
        g['ejemplo_de_fallo'] = {'semilla': malo['cell']['semilla'], 'estado': malo['estado'], 'abandono': malo.get('abandono'), 'falla': malo.get('falla'), 'eventos': (malo.get('eventos') or [])[-14:]}
    return g


def _grupo_bots(clave, celda):
    escenas, banderas = _bots.resumir({'config': celda.get('config'), 'episodios': celda.get('episodios', []), 'deterministas': celda.get('deterministas', []),
                                       'errores_de_pagina': celda.get('errores_de_pagina', [])})
    return {'variante': clave[0], 'perfil': clave[1], 'prueba': clave[2], 'tipo': 'bots', 'escenas': escenas, 'banderas_bots': banderas,
            'determinista': not any(b['codigo'] == 'no-determinista' for b in banderas), 'aislado': celda.get('aislado', True),
            'errores': [{'tipo': t, 'texto': x, 'sesiones': 1} for t, xs in sorted((celda.get('errores') or {}).items()) for x in xs]}


def _medido(grupos_crudos):
    """Tiempos reales (de esta computadora) por variante, perfil y prueba: ruido, solo para mirar y comparar a grandes rasgos."""
    salida = []
    for clave, sesiones in grupos_crudos:
        m = [s.get('medido') or {} for s in sesiones]
        fila = {'variante': clave[0], 'perfil': clave[1], 'prueba': clave[2]}
        for campo in ('carga_real_ms', 'ritmo_cpu', 'pasada_max_ms', 'memoria_mb'):
            vs = [x[campo] for x in m if _numero(x.get(campo))]
            if vs:
                fila[campo] = {'p50': _p(vs, 0.5), 'p90': _p(vs, 0.9), 'max': max(vs), 'n': len(vs)}
        salida.append(fila)
    return salida


def informe(exp, plan, crudo, objeto_version='', huellas=None):
    """De lo que devolvió laboratorio.js al informe determinista, el medido y las banderas. Función pura (las pruebas la usan con datos inventados)."""
    celdas = crudo['celdas']
    umbrales = dict(UMBRALES, **(exp.get('umbrales') or {}))
    llaves, por_llave, reps = [], {}, {}
    for c in celdas:
        k = (c['cell']['variante'], c['cell']['perfil'], c['cell']['prueba'])
        if k not in por_llave:
            llaves.append(k)
            por_llave[k] = {'sesiones': [], 'reps': [], 'tipo': next(p['tipo'] for p in exp['pruebas'] if p['id'] == k[2])}
        if c['cell'].get('repeticion'):
            por_llave[k]['reps'].append(c)
        else:
            por_llave[k]['sesiones'].append(c)
    orden_v = {v['id']: i for i, v in enumerate(exp['variantes'])}
    orden_p = {(p['id'] if isinstance(p, dict) else p): i for i, p in enumerate(exp['perfiles'])}
    orden_t = {p['id']: i for i, p in enumerate(exp['pruebas'])}
    llaves.sort(key=lambda k: (orden_v[k[0]], orden_p[k[1]], orden_t[k[2]]))
    grupos, crudos = [], []
    for k in llaves:
        d = por_llave[k]
        if d['tipo'] == 'bots':
            g = _grupo_bots(k, d['sesiones'][0]) if d['sesiones'] else None
            if g:
                g['sesiones_crudas'] = d['sesiones']
        else:
            g = _grupo_sesiones(k, d['tipo'], d['sesiones'], d['reps']) if d['sesiones'] else None
        if g:
            grupos.append(g)
            crudos.append((k, d['sesiones']))
    banderas = _banderas(exp, grupos, umbrales, crudos)
    for g in grupos:
        g.pop('sesiones_crudas', None)
    contrastes = _contrastes(exp, grupos)
    rep = {'formato': FORMATO, 'experimento': exp['id'], 'titulo': exp['titulo'], 'pregunta': exp['pregunta'],
           'objeto': dict(exp['objeto'], **({'version': objeto_version} if objeto_version else {})), 'huellas': huellas or {},
           'semilla_base': plan['semilla_base'], 'factor': plan['factor'], 'variantes': [v['id'] for v in exp['variantes']], 'perfiles': [p['id'] for p in plan['perfiles']],
           'pruebas': [{'id': p['id'], 'tipo': p['tipo'], 'semillas': (1 if p['tipo'] == 'auditoria' else max(1, int(round(p.get('semillas', 5) * plan['factor'])))) if p['tipo'] != 'bots' else None} for p in plan['pruebas']],
           'grupos': grupos, 'contrastes': contrastes, 'banderas': banderas}
    rep['huella_resultado'] = hashlib.sha256(json.dumps(rep, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()[:16]
    medido = {'experimento': exp['id'], 'grupos': _medido(crudos)}
    return rep, medido


def _banderas(exp, grupos, umbrales, crudos):
    banderas = []
    comunes = {}                                    # problemas de la PÁGINA (no del perfil): una sola bandera por variante y texto, con cuántos grupos la vieron
    de_bots = {}                                    # banderas de bots: una por variante, prueba, escena y texto, con los perfiles en que salió

    def poner(codigo, nivel, donde, texto):
        banderas.append({'codigo': codigo, 'nivel': nivel, 'donde': donde, 'texto': texto})
    sesiones_de = dict(crudos)
    for g in grupos:
        k = (g['variante'], g['perfil'], g['prueba'])
        d = '%s/%s/%s' % k
        if g['tipo'] == 'bots':
            for b in g['banderas_bots']:
                de_bots.setdefault(('bots-' + b['codigo'], b['nivel'], g['variante'], g['prueba'], b.get('escena') or '', b['texto']), []).append(g['perfil'])
            if not g.get('aislado', True):
                poner('contexto-sucio', 'falla', d, 'la sesión de bots empezó con almacenamiento que no era suyo')
            continue
        ses = sesiones_de[k]
        if g['determinista'] is False:
            poner('no-determinista', 'falla', d, 'con la misma semilla, el mismo perfil y la misma variante, la traza cambió')
        malos = {}
        for s in ses:
            if s['estado'] == 'falla' and s.get('falla'):
                if s['falla']['paso'] == 'interno':
                    malos.setdefault(('error-interno', s['falla']['mensaje']), []).append(s['cell']['semilla'])
                else:
                    malos.setdefault(('verificacion-fallida', '%s: %s' % (s['falla']['paso'], s['falla']['mensaje'])), []).append(s['cell']['semilla'])
        for (codigo, texto), semillas in sorted(malos.items()):
            poner(codigo, 'falla', d, '%s (%d de %d sesiones)' % (texto, len(semillas), g['sesiones']))
        for t, x in sorted({(t, x) for s in ses for t, xs in (s.get('errores') or {}).items() if t in ('pagina', 'consola') for x in xs}):
            comunes.setdefault(('fallas-de-pagina', 'falla', g['variante'], '%s: %s' % (t, x)), []).append(d)
        for x in sorted({x for s in ses for x in (s.get('errores') or {}).get('red', [])}):
            comunes.setdefault(('recurso-faltante', 'falla', g['variante'], 'la página pidió un archivo que no existe: ' + x), []).append(d)
        if any(s.get('aislado') is False for s in ses):
            comunes.setdefault(('contexto-sucio', 'falla', g['variante'], 'una sesión empezó con almacenamiento o cookies que no eran suyas'), []).append(d)
        for x in sorted({x for s in ses for x in (s.get('errores') or {}).get('bloqueadas', [])}):
            comunes.setdefault(('red-externa', 'aviso', g['variante'], 'la beta intentó llegar a internet (cortado por el laboratorio): ' + x), []).append(d)
        if g['sesiones'] >= 5 and g['tasa_abandono'] >= umbrales['abandono']:
            top = next(iter(g['abandonos_en']), '-')
            poner('abandono-alto', 'aviso', d, 'se rinde el %d %% de las sesiones (donde más: %s)' % (round(g['tasa_abandono'] * 100), top))
        lentas = [s for s in ses if s['estado'] == 'abandono' and (s.get('abandono') or {}).get('motivo') == 'carga-lenta']
        if lentas:
            a = lentas[0]['abandono']
            poner('carga-lenta', 'aviso', d, '%d sesión(es) se rinden porque la página tarda ~%s ms (modelada) y su paciencia es de %s ms' % (len(lentas), a.get('modelada_ms'), a.get('paciencia_ms')))
    total_por_variante = {v['id']: sum(1 for g in grupos if g['variante'] == v['id'] and g['tipo'] != 'bots') for v in exp['variantes']}
    for (codigo, nivel, variante, texto), donde in sorted(comunes.items()):
        poner(codigo, nivel, variante, '%s (en %d de %d grupos)' % (texto, len(donde), total_por_variante[variante]))
    perfiles_de_bots = {}
    for g in grupos:
        if g['tipo'] == 'bots':
            perfiles_de_bots[(g['variante'], g['prueba'])] = perfiles_de_bots.get((g['variante'], g['prueba']), 0) + 1
    for (codigo, nivel, variante, prueba, escena, texto), perfiles in sorted(de_bots.items()):
        total = perfiles_de_bots[(variante, prueba)]
        poner(codigo, nivel, '%s/%s' % (variante, prueba) + ('/' + escena if escena else ''),
              '%s (en %d de %d perfil(es)%s)' % (texto, len(perfiles), total, ': ' + ', '.join(sorted(perfiles)) if len(perfiles) < total else ''))
    # nadie completa / bloqueado para un perfil: por variante y prueba de guion
    for v in exp['variantes']:
        for p in exp['pruebas']:
            if p['tipo'] != 'guion':
                continue
            gs = [g for g in grupos if g['variante'] == v['id'] and g['prueba'] == p['id'] and g['tipo'] == 'guion']
            if not gs:
                continue
            if all(g['completaron'] == 0 for g in gs):
                poner('imposible', 'falla', '%s/%s' % (v['id'], p['id']), 'ningún perfil completó el guion (%d sesiones en total)' % sum(g['sesiones'] for g in gs))
                continue
            buenos = [g for g in gs if g['tasa_completa'] >= umbrales['bloqueo']]
            for g in gs:
                if g['completaron'] == 0 and buenos:
                    poner('bloqueado-para-perfil', 'aviso', '%s/%s/%s' % (v['id'], g['perfil'], p['id']),
                          'nadie con este perfil completa el guion; con otros perfiles sí (%s). Donde se traban: %s' % (', '.join(b['perfil'] for b in buenos[:3]), next(iter(g['abandonos_en']), 'falla')))
    # accesibilidad: una bandera por código y variante, con los perfiles afectados
    for v in exp['variantes']:
        por_codigo = {}
        for g in grupos:
            if g['variante'] != v['id'] or g['tipo'] == 'bots':
                continue
            for a in g['a11y']:
                por_codigo.setdefault(a['codigo'], {})[g['perfil']] = a['ejemplo']
        for codigo, perfiles in sorted(por_codigo.items()):
            ej = next(iter(perfiles.values()))
            poner('a11y-' + codigo, 'aviso', v['id'], 'en %d perfil(es): %s · ejemplo: %s' % (len(perfiles), ', '.join(sorted(perfiles)[:4]) + ('…' if len(perfiles) > 4 else ''), ej))
    return banderas


def _contrastes(exp, grupos):
    """Cada variante contra el control (la primera), por perfil y prueba: ¿cambia el que completen?, ¿y el abandono? «claro» = los intervalos de Wilson no se cruzan."""
    if len(exp['variantes']) < 2:
        return []
    control = exp['variantes'][0]['id']
    base = {(g['perfil'], g['prueba']): g for g in grupos if g['variante'] == control and g['tipo'] != 'bots'}
    salida = []
    for g in grupos:
        if g['variante'] == control or g['tipo'] == 'bots':
            continue
        c = base.get((g['perfil'], g['prueba']))
        if not c or not c['sesiones'] or not g['sesiones']:
            continue
        a11y_c, a11y_g = {a['codigo'] for a in c['a11y']}, {a['codigo'] for a in g['a11y']}
        salida.append({'variante': g['variante'], 'contra': control, 'perfil': g['perfil'], 'prueba': g['prueba'],
                       'tasa_control': c['tasa_completa'], 'tasa_variante': g['tasa_completa'], 'delta_tasa': round(g['tasa_completa'] - c['tasa_completa'], 4),
                       'claro': _no_se_cruzan(c['tasa_ic'], g['tasa_ic']), 'delta_abandono': round(g['tasa_abandono'] - c['tasa_abandono'], 4),
                       'a11y_nuevos': sorted(a11y_g - a11y_c), 'a11y_resueltos': sorted(a11y_c - a11y_g)})
    return salida


# ---------------------------------------------------------------- comparar versiones
def comparar(a, b):
    """Compara dos informes del mismo experimento (a = antes, b = después) y devuelve {cambios: [...], resumen}. Un «cambio» es regresion, mejora o cambio."""
    if a.get('experimento') != b.get('experimento'):
        raise ErrorLaboratorio('no son el mismo experimento (%s y %s)' % (a.get('experimento'), b.get('experimento')))
    cambios = []

    def poner(tipo, donde, texto):
        cambios.append({'tipo': tipo, 'donde': donde, 'texto': texto})
    for k in ('huella_html',):
        pass
    ha, hb = a.get('huellas') or {}, b.get('huellas') or {}
    version_a, version_b = (a.get('objeto') or {}).get('version'), (b.get('objeto') or {}).get('version')
    nota = 'versión %s → %s' % (version_a or '?', version_b or '?') if version_a != version_b else ('misma versión' if ha == hb else 'la página cambió con la misma versión')
    ga = {(g['variante'], g['perfil'], g['prueba']): g for g in a['grupos']}
    gb = {(g['variante'], g['perfil'], g['prueba']): g for g in b['grupos']}
    for k in sorted(set(ga) | set(gb)):
        d = '%s/%s/%s' % k
        if k not in ga:
            poner('cambio', d, 'combinación nueva (antes no se probaba)')
            continue
        if k not in gb:
            poner('cambio', d, 'ya no se prueba esta combinación')
            continue
        x, y = ga[k], gb[k]
        if x['tipo'] == 'bots' or y['tipo'] == 'bots':
            _comparar_bots(x, y, d, poner)
            continue
        dt = round(y['tasa_completa'] - x['tasa_completa'], 4)
        if _no_se_cruzan(x['tasa_ic'], y['tasa_ic']):
            poner('regresion' if dt < 0 else 'mejora', d, 'completan %d %% → %d %% (cambio claro: los intervalos no se cruzan)' % (round(x['tasa_completa'] * 100), round(y['tasa_completa'] * 100)))
        elif abs(dt) >= 0.2:
            poner('cambio', d, 'completan %d %% → %d %% (diferencia grande pero con poca muestra: no es concluyente)' % (round(x['tasa_completa'] * 100), round(y['tasa_completa'] * 100)))
        ax, ay = {e['etapa']: e['alcanzaron'] / max(1, x['sesiones']) for e in x['embudo']}, {e['etapa']: e['alcanzaron'] / max(1, y['sesiones']) for e in y['embudo']}
        for etapa in ay:
            if etapa in ax and abs(ay[etapa] - ax[etapa]) >= 0.25:
                poner('regresion' if ay[etapa] < ax[etapa] else 'mejora', d, 'etapa «%s»: llega el %d %% → %d %%' % (etapa, round(ax[etapa] * 100), round(ay[etapa] * 100)))
        ca, cb = {a_['codigo'] for a_ in x['a11y']}, {a_['codigo'] for a_ in y['a11y']}
        for c in sorted(cb - ca):
            poner('regresion', d, 'problema nuevo de accesibilidad o de uso: %s' % c)
        for c in sorted(ca - cb):
            poner('mejora', d, 'problema resuelto: %s' % c)
        ea, eb = {(e['tipo'], e['texto']) for e in x['errores']}, {(e['tipo'], e['texto']) for e in y['errores']}
        for t, tx in sorted(eb - ea):
            poner('regresion', d, 'error nuevo (%s): %s' % (t, tx[:90]))
        for t, tx in sorted(ea - eb):
            poner('mejora', d, 'error resuelto (%s): %s' % (t, tx[:90]))
        if x.get('determinista') is not False and y.get('determinista') is False:
            poner('regresion', d, 'dejó de ser determinista')
        if x.get('primera_accion_p50_ms') and y.get('primera_accion_p50_ms') and abs(y['primera_accion_p50_ms'] - x['primera_accion_p50_ms']) >= max(500, 0.3 * x['primera_accion_p50_ms']):
            poner('cambio', d, 'tiempo hasta la primera acción (simulado): %s → %s ms' % (x['primera_accion_p50_ms'], y['primera_accion_p50_ms']))
    fa = {(f['codigo'], f['donde']): f for f in a['banderas']}
    fb = {(f['codigo'], f['donde']): f for f in b['banderas']}
    for k in sorted(set(fb) - set(fa)):
        poner('regresion' if fb[k]['nivel'] == 'falla' else 'cambio', k[1], 'bandera nueva: %s' % k[0])
    for k in sorted(set(fa) - set(fb)):
        poner('mejora' if fa[k]['nivel'] == 'falla' else 'cambio', k[1], 'bandera resuelta: %s' % k[0])
    orden = {'regresion': 0, 'mejora': 1, 'cambio': 2}
    cambios.sort(key=lambda c: (orden[c['tipo']], c['donde'], c['texto']))
    cuenta = {t: sum(1 for c in cambios if c['tipo'] == t) for t in orden}
    return {'experimento': b['experimento'], 'nota': nota, 'cambios': cambios, 'resumen': cuenta}


def _comparar_bots(x, y, d, poner):
    if x['tipo'] != y['tipo']:
        poner('cambio', d, 'la prueba cambió de tipo')
        return
    for esc in sorted(set(x['escenas']) & set(y['escenas'])):
        for pol in sorted(set(x['escenas'][esc]) & set(y['escenas'][esc])):
            fa, fb = x['escenas'][esc][pol], y['escenas'][esc][pol]
            if _no_se_cruzan(wilson(fa['exitos'], fa['partidas']), wilson(fb['exitos'], fb['partidas'])):
                poner('cambio', '%s/%s/%s' % (d, esc, pol), 'gana %d %% → %d %% (cambio claro; si es el solucionador o el humano, cambió la dificultad)' % (round(fa['tasa'] * 100), round(fb['tasa'] * 100)))


def texto_comparacion(cmp):
    L = ['[laboratorio] %s · comparación (%s) · %d regresión(es), %d mejora(s), %d otro(s) cambio(s)' % (cmp['experimento'], cmp['nota'], cmp['resumen']['regresion'], cmp['resumen']['mejora'], cmp['resumen']['cambio'])]
    if not cmp['cambios']:
        L.append('  Sin cambios que mostrar.')
    for c in cmp['cambios']:
        L.append('  [%s] %s: %s' % (c['tipo'], c['donde'], c['texto']))
    return L


# ---------------------------------------------------------------- texto, guardado
def texto(rep):
    L = ['[laboratorio] %s · «%s»' % (rep['experimento'], rep['titulo']),
         '  %d variante(s) × %d perfil(es) × %d prueba(s) · semilla base %s · factor %s · huella %s' % (len(rep['variantes']), len(rep['perfiles']), len(rep['pruebas']), rep['semilla_base'], rep['factor'], rep['huella_resultado'])]
    for g in rep['grupos']:
        if g['tipo'] == 'bots':
            partes = []
            for esc, ps in g['escenas'].items():
                partes.append('%s: ' % esc + ' '.join('%s %d%%' % (p, round(f['tasa'] * 100)) for p, f in sorted(ps.items())))
            L.append('  %-10s %-22s %-14s bots · %s' % (g['variante'], g['perfil'], g['prueba'], ' | '.join(partes[:3]) + (' …' if len(partes) > 3 else '')))
            continue
        etapas = ' → '.join('%s %d' % (e['etapa'], e['alcanzaron']) for e in g['embudo']) or '-'
        L.append('  %-10s %-22s %-14s %d/%d completan (%d %%) · abandonan %d · fallan %d · 1ª acción %s ms · %s' % (
            g['variante'], g['perfil'], g['prueba'], g['completaron'], g['sesiones'], round(g['tasa_completa'] * 100), g['abandonaron'], g['fallaron'],
            g['primera_accion_p50_ms'] if g['primera_accion_p50_ms'] is not None else '-', etapas))
    for c in rep['contrastes']:
        L.append('  A/B %s contra %s · %s/%s: completan %+d puntos%s' % (c['variante'], c['contra'], c['perfil'], c['prueba'], round(c['delta_tasa'] * 100), ' (claro)' if c['claro'] else ' (no concluyente)'))
    if rep['banderas']:
        L.append('  Banderas:')
        for b in rep['banderas']:
            L.append('    [%s] %s · %s: %s' % (b['nivel'], b['codigo'], b['donde'], b['texto']))
    else:
        L.append('  Sin banderas.')
    return L


def carpeta_informes(raiz):
    return pathlib.Path(raiz) / 'metricas' / 'laboratorio'


def _volcar(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def guardar(raiz, rep, medido):
    """Guarda metricas/laboratorio/ID.json (determinista). Si ya había uno de otra versión o de otra beta, pasa a ID.previo.json (con su medido) para poder compararlos."""
    base = carpeta_informes(raiz)
    ruta, previo = base / ('%s.json' % rep['experimento']), base / ('%s.previo.json' % rep['experimento'])
    if ruta.exists():
        anterior = json.loads(ruta.read_text(encoding='utf-8'))
        if anterior.get('huella_resultado') != rep['huella_resultado'] and (anterior.get('huellas') != rep.get('huellas') or anterior.get('objeto') != rep.get('objeto')):
            _volcar(previo, anterior)
            m = base / ('%s.medido.json' % rep['experimento'])
            if m.exists():
                _volcar(base / ('%s.previo.medido.json' % rep['experimento']), json.loads(m.read_text(encoding='utf-8')))
    _volcar(ruta, rep)
    _volcar(base / ('%s.medido.json' % rep['experimento']), medido)
    return ruta


def leer(raiz, exp_id, previo=False):
    ruta = carpeta_informes(raiz) / ('%s%s.json' % (exp_id, '.previo' if previo else ''))
    return json.loads(ruta.read_text(encoding='utf-8')) if ruta.exists() else None


def resumen_corto(rep):
    """Una línea para el ranking: qué se probó y si hay banderas."""
    if not rep:
        return None
    fallas = [b for b in rep['banderas'] if b['nivel'] == 'falla']
    avisos = [b for b in rep['banderas'] if b['nivel'] == 'aviso']
    estado = 'sin banderas' if not rep['banderas'] else '%d falla(s), %d aviso(s)' % (len(fallas), len(avisos))
    return 'laboratorio «%s»: %d perfil(es) × %d variante(s): %s' % (rep['experimento'], len(rep['perfiles']), len(rep['variantes']), estado)


# ---------------------------------------------------------------- correr
def _entorno():
    env = dict(os.environ)
    if not env.get('NODE_PATH') and os.path.isdir('/opt/npm-tools/node_modules'):
        env['NODE_PATH'] = '/opt/npm-tools/node_modules'
    return env


def correr(raiz, exp_id, factor=1.0, semilla_base=None, solo_perfiles=None, solo_pruebas=None, determinismo=True):
    """Valida, planea, corre en el navegador y devuelve (informe, medido, líneas de texto). No escribe nada."""
    raiz = pathlib.Path(raiz)
    exp = cargar_experimento(raiz, exp_id)
    if exp.get('id') != exp_id:
        raise ErrorLaboratorio('el «id» del experimento (%s) debe coincidir con el nombre del archivo (%s.json)' % (exp.get('id'), exp_id))
    perfiles = cargar_perfiles(raiz)
    errores = validar(raiz, exp, perfiles)
    if errores:
        raise ErrorLaboratorio('el experimento «%s» tiene %d problema(s):\n  - %s' % (exp_id, len(errores), '\n  - '.join(errores)))
    plan = planear(raiz, exp, perfiles, factor, semilla_base, solo_perfiles, solo_pruebas, determinismo)
    with tempfile.TemporaryDirectory() as tmp:
        ruta_plan, ruta_salida = pathlib.Path(tmp) / 'plan.json', pathlib.Path(tmp) / 'salida.json'
        ruta_plan.write_text(json.dumps({k: plan[k] for k in ('variantes', 'celdas', 'concurrencia')}), encoding='utf-8')
        r = subprocess.run(['node', str(raiz / 'herramientas' / 'laboratorio.js'), str(ruta_plan), str(ruta_salida)], cwd=str(raiz), capture_output=True, text=True, timeout=3600, env=_entorno())
        if r.returncode != 0 or not ruta_salida.exists():
            raise ErrorLaboratorio('el laboratorio no devolvió resultado (¿están node y playwright?):\n%s' % (r.stderr or r.stdout)[-800:])
        crudo = json.loads(ruta_salida.read_text(encoding='utf-8'))
    obj = exp['objeto']
    version = json.loads((raiz / 'juegos' / obj['juego'] / 'juego.json').read_text(encoding='utf-8')).get('version', '') if 'juego' in obj else ''
    huellas = {}
    for v in plan['variantes']:
        h = hashlib.sha256()
        h.update(pathlib.Path(v['html']).read_bytes())
        h.update(json.dumps([v['consulta'], v['juego'], v['css'], v['reemplazos']], sort_keys=True).encode('utf-8'))
        huellas[v['id']] = h.hexdigest()[:16]
    rep, medido = informe(exp, plan, crudo, version, huellas)
    return rep, medido, texto(rep)
