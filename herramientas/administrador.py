"""El administrador del motor: sus ojos (chequeo) y su memoria (bitácora).

El administrador es una tarea programada de Claude que corre cada día, sin nadie delante, con la carta de motor/ADMINISTRADOR.md. No es un proceso
siempre encendido: cada corrida empieza de cero, y lo que le da continuidad es lo que queda escrito en el repositorio. Este módulo es esa escritura.

  chequeo()     mira el estado de la fábrica y devuelve hallazgos de tres niveles:
                  resolver  lo puede arreglar el propio administrador, dentro de su carta (pruebas del motor vencidas, inventario roto, el siguiente
                            paso de autonomía de la cola);
                  avisar    necesita a Max o algo falló de verdad (calendario por agotarse, envío en duda, publicación que falló, ciclo semanal parado);
                  info      vale saber, no pide nada hoy.
  bitacora      motor/bitacora.jsonl: una línea por cosa hecha o decidida, solo se agrega (nunca se reescribe). Es lo primero que lee la corrida
                siguiente y lo que Max puede leer para ver qué hizo el administrador.

Lo que este módulo no hace: aprobar, publicar, cambiar la política ni tocar un juego publicado. Mira y anota."""
import datetime
import json
import pathlib
import subprocess

import autonomia
import motor

NIVELES = ('resolver', 'avisar', 'info')
FALLAS_DE_LA_RED = ('fallo', 'error')
UMBRAL_AVISAR = 3        # días de contenido aprobado por salir por debajo de los cuales Max tiene que enterarse
UMBRAL_LOTE = 7          # por debajo de esto la rutina de los lunes debe preparar el siguiente lote
MAX_TEXTO = 400
IDENTIDAD = 'administrador-del-motor'
RUTAS_PROTEGIDAS = ('contenido/aprobaciones.json', 'publicacion/politica.json', 'publicacion/libro.jsonl', 'publicacion/sitio.json', 'motor/ggx.js',
                    'motor/ADMINISTRADOR.md', '.github/workflows/publicar.yml', '.github/workflows/calendario.yml')


class ErrorAdministrador(Exception):
    pass


def _h(nivel, id_, texto, accion=''):
    return {'nivel': nivel, 'id': id_, 'texto': texto, 'accion': accion}


def _semana_a_fecha(s):
    a, w = s.split('-W')
    return datetime.date.fromisocalendar(int(a), int(w), 1)


def en_duda(entradas):
    """Acciones cuyo último apunte en el libro es «incierto»: nadie sabe si salieron."""
    ultimo = {}
    for e in entradas:
        if e.get('accion'):
            ultimo[e['accion']] = e
    return sorted(a for a, e in ultimo.items() if e.get('resultado') == 'incierto')


def fallas_recientes(entradas, hoy, dias=3):
    """Acciones cuyo último apunte fue una falla de la red en los últimos `dias` días (una que ya salió bien después no cuenta)."""
    ultimo = {}
    for e in entradas:
        if e.get('accion'):
            ultimo[e['accion']] = e
    corte = datetime.datetime.combine(hoy - datetime.timedelta(days=dias), datetime.time.min)
    fallas = []
    for a, e in sorted(ultimo.items()):
        if e.get('resultado') in FALLAS_DE_LA_RED:
            try:
                cuando = datetime.datetime.strptime(e.get('ts', ''), '%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                cuando = corte                      # sin fecha legible se prefiere avisar de más que callar
            if cuando >= corte:
                fallas.append(a)
    return fallas


def chequeo(raiz, hoy, lineas_calendario=None, entradas_libro=None, juegos=None):
    """Hallazgos ordenados (resolver, avisar, info). Todo entra por parámetro para que se pueda probar sin red ni reloj."""
    raiz = pathlib.Path(raiz)
    H = []
    cat = None
    try:
        cat = autonomia.catalogo(raiz)
        for p in autonomia.problemas_de_catalogo(cat):
            H.append(_h('resolver', 'inventario-roto', 'El inventario de autonomía tiene un problema: ' + p, 'corregir motor/autonomia.json y correr `python3 fabrica.py autonomia revisar`'))
    except autonomia.ErrorAutonomia as e:
        H.append(_h('resolver', 'inventario-falta', str(e), 'restaurar motor/autonomia.json desde git'))
    vigente, motivo = motor.informe_vigente(raiz)
    if not vigente:
        H.append(_h('resolver', 'pruebas-vencidas', 'Las pruebas del motor están vencidas (%s): ningún juego que use el motor puede salir.' % motivo, 'python3 fabrica.py motor probar'))
    entradas = entradas_libro or []
    for a in en_duda(entradas):
        H.append(_h('avisar', 'envio-en-duda', 'El envío «%s» quedó en duda: pudo salir o no. No se reintenta solo.' % a, 'revisar la cuenta y `python3 fabrica.py resolver %s salio|no-salio`' % a))
    for a in fallas_recientes(entradas, hoy):
        H.append(_h('avisar', 'publicacion-fallida', 'La publicación «%s» falló en los últimos 3 días.' % a, 'mirar el motivo en publicacion/libro.jsonl y en la corrida del flujo'))
    if lineas_calendario is not None:
        dias, hasta = autonomia.dias_aprobados(lineas_calendario, hoy)
        pend = [l for l in lineas_calendario if l['estado'] in ('sin aprobar', 'cambió tras aprobar')]
        for l in lineas_calendario:
            if l['estado'] in ('vencida', 'con problemas', 'en duda'):
                H.append(_h('avisar', 'calendario-' + l['estado'].replace(' ', '-'), 'La publicación «%s» del calendario está %s.' % (l['id'], l['estado']), 'ver `python3 fabrica.py calendario`'))
        if dias == 0:
            H.append(_h('avisar', 'calendario-detenido', 'No queda contenido aprobado por salir: el calendario está detenido%s.' % (' (hay %d sin aprobar)' % len(pend) if pend else ''),
                        'que Max apruebe el lote pendiente' if pend else 'preparar un lote nuevo para que Max lo apruebe'))
        elif dias < UMBRAL_AVISAR:
            H.append(_h('avisar', 'calendario-por-agotarse', 'Quedan %d días de contenido aprobado (hasta %s).' % (dias, hasta.isoformat()),
                        'que Max apruebe el lote pendiente' if pend else 'preparar un lote nuevo ya, sin esperar al lunes'))
        elif dias < UMBRAL_LOTE and not pend:
            H.append(_h('info', 'lote-por-preparar', 'Quedan %d días de contenido aprobado: la rutina de los lunes debe preparar el siguiente lote.' % dias))
        elif pend:
            H.append(_h('info', 'lote-esperando', 'Hay %d publicación(es) esperando la aprobación de Max; quedan %d días de contenido aprobado.' % (len(pend), dias)))
    hist = autonomia.historial(raiz)
    if hist:
        ultima = _semana_a_fecha(hist[-1]['semana'])
        if (hoy - ultima).days > 13:
            H.append(_h('avisar', 'ciclo-semanal-parado', 'El ciclo semanal no ha dejado su registro desde la semana %s.' % hist[-1]['semana'],
                        'revisar que el flujo «Ciclo semanal» siga activo (`gh workflow list --all`) y reactivarlo; correr `python3 fabrica.py ciclo`'))
    if cat is not None:
        items = autonomia.cola_items(raiz)
        if items:
            H.append(_h('resolver', 'autonomia-por-construir', 'Hay %d paso(s) de autonomía que se pueden construir sin Max. El primero: %s' % (len(items), items[0]['titulo'].replace('Automatizar: ', '')),
                        'construir ese paso (con pruebas) y marcarlo «resuelta» en motor/autonomia.json'))
        abiertos = [x for x in cat['pasos'] if x['quien'] == 'dueno' and x['frecuencia'] == 'una-vez' and x['estado'] == 'abierta']
        if abiertos:
            H.append(_h('info', 'pendientes-unicos-de-max', '%d pendiente(s) de una sola vez que solo Max puede hacer (ver `python3 fabrica.py autonomia`).' % len(abiertos)))
    return sorted(H, key=lambda h: (NIVELES.index(h['nivel']), h['id']))


def resumen(hallazgos):
    if not hallazgos:
        return ['Todo en orden: nada que arreglar ni que avisar.']
    L = []
    for nivel, titulo in (('avisar', 'Para avisar a Max'), ('resolver', 'Para resolver sin Max'), ('info', 'Solo para saber')):
        grupo = [h for h in hallazgos if h['nivel'] == nivel]
        if grupo:
            L += ['## %s' % titulo, '']
            for h in grupo:
                L.append('- [%s] %s%s' % (h['id'], h['texto'], (' → ' + h['accion']) if h['accion'] else ''))
            L.append('')
    return L


# ---------------------------------------------------------------------------------------------------------------------
# Bitácora
# ---------------------------------------------------------------------------------------------------------------------

def _ruta_bitacora(raiz):
    return pathlib.Path(raiz) / 'motor' / 'bitacora.jsonl'


def bitacora(raiz):
    ruta = _ruta_bitacora(raiz)
    if not ruta.exists():
        return []
    return [json.loads(l) for l in ruta.read_text(encoding='utf-8').splitlines() if l.strip()]


def anotar(raiz, hoy, que, resultado, commit=''):
    """Agrega una línea a la bitácora (solo agrega). `resultado`: hecho · no-se-pudo · avisado · nada-que-hacer."""
    if resultado not in ('hecho', 'no-se-pudo', 'avisado', 'nada-que-hacer'):
        raise ErrorAdministrador('el resultado debe ser hecho, no-se-pudo, avisado o nada-que-hacer')
    que = ' '.join(str(que).split())
    if not que or len(que) > MAX_TEXTO:
        raise ErrorAdministrador('la nota debe tener entre 1 y %d caracteres' % MAX_TEXTO)
    linea = {'fecha': hoy.isoformat(), 'que': que, 'resultado': resultado}
    if commit:
        linea['commit'] = str(commit)[:40]
    ruta = _ruta_bitacora(raiz)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, 'a', encoding='utf-8') as f:
        f.write(json.dumps(linea, ensure_ascii=False, sort_keys=True) + '\n')
    return linea


def ultimas(raiz, n=10):
    return bitacora(raiz)[-n:]


# ---------------------------------------------------------------------------------------------------------------------
# Guardia: comprobación independiente de lo que tocó el administrador
# ---------------------------------------------------------------------------------------------------------------------

def protegidas(entradas_libro):
    """(archivos exactos, carpetas) que el administrador no puede tocar: las fijas y, por cada juego ya publicado, su ficha y su salida/."""
    carpetas = []
    for j in sorted(motor.lanzados(entradas_libro or [])):
        carpetas += ['salida/%s/' % j, 'juegos/%s/' % j]
    return set(RUTAS_PROTEGIDAS), carpetas


def violaciones(cambios, entradas_libro):
    """`cambios`: [(commit, ruta)]. Devuelve las que tocan algo protegido, como [(commit, ruta, motivo)]."""
    exactas, carpetas = protegidas(entradas_libro)
    malas = []
    for commit, ruta in cambios:
        if ruta in exactas:
            malas.append((commit, ruta, 'ruta protegida'))
        else:
            c = next((c for c in carpetas if ruta.startswith(c)), None)
            if c:
                malas.append((commit, ruta, 'juego ya publicado (%s)' % c))
    return malas


def cambios_del_administrador(raiz, identidad=IDENTIDAD):
    """[(commit, ruta)] de todos los commits firmados por el administrador que el repositorio tiene a la vista (en una copia superficial, los visibles)."""
    r = subprocess.run(['git', '-C', str(raiz), 'log', '--author=' + identidad, '--name-only', '--pretty=format:@%H'], capture_output=True, text=True)
    if r.returncode:
        raise ErrorAdministrador('no se pudo leer el historial de git: %s' % (r.stderr.strip() or r.stdout.strip())[:200])
    cambios, commit = [], None
    for linea in r.stdout.splitlines():
        if linea.startswith('@'):
            commit = linea[1:]
        elif linea.strip() and commit:
            cambios.append((commit, linea.strip()))
    return cambios
