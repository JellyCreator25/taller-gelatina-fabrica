"""Resultados de las publicaciones de Bluesky: qué tanta gente las movió de verdad y qué formatos funcionan.

Cada publicación que salió (libro de registro) se mide una vez a las 24 horas y otra a los 3 días: se leen sus contadores públicos
(likes, reposts, respuestas y citas) del AppView de Bluesky, que no necesita contraseña, y se anotan en contenido/resultados.jsonl. Con eso se arma una
tabla por formato e idioma (el campo «formato» de cada publicación en contenido/calendario.json) para que los lotes siguientes aprendan de lo que pasó.

Qué cuenta más: en Bluesky el repost es la principal vía de descubrimiento, así que pesa 3; una respuesta y una cita pesan 2; un like pesa 1.
Es una convención de la fábrica, no una medida oficial.

Límites honestos: una cuenta nueva tiene pocos lectores, y con pocas publicaciones los promedios son ruido. Por eso la tabla solo concluye algo cuando hay al
menos MIN_PARA_CONCLUIR publicaciones medidas, y aun así una diferencia pequeña entre formatos no demuestra nada. Los contadores no dicen cuánta gente jugó:
para eso están las métricas del sitio (metricas/registro.csv).

Esto solo LEE datos públicos: no publica, no responde a nadie y no necesita ningún secreto."""
import datetime
import json
import pathlib
import urllib.parse

from . import nucleo

API = 'https://public.api.bsky.app/xrpc/app.bsky.feed.getPosts'
VENTANAS_HORAS = (24, 72)
MIN_PARA_CONCLUIR = 8
PESOS = {'likes': 1, 'reposts': 3, 'respuestas': 2, 'citas': 2}
LOTE = 25                        # getPosts admite hasta 25 direcciones por petición


class ErrorResultados(Exception):
    pass


def _ruta(raiz):
    return pathlib.Path(raiz) / 'contenido' / 'resultados.jsonl'


def cargar(raiz):
    r = _ruta(raiz)
    if not r.exists():
        return []
    return [json.loads(l) for l in r.read_text(encoding='utf-8').splitlines() if l.strip()]


def _hora(ts):
    return datetime.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)


def puntaje(r):
    return sum(PESOS[k] * int(r.get(k, 0) or 0) for k in PESOS)


def publicadas(libro):
    """Entradas del libro que son publicaciones de Bluesky ya hechas y con dirección (at://) para consultarlas."""
    return [e for e in libro.entradas()
            if e.get('canal') == 'bluesky' and e.get('tipo') == 'post' and e.get('resultado') == 'ok' and str(e.get('ref', '')).startswith('at://')]


def pendientes(raiz, ahora, libro):
    """[(entrada, ventana, horas)] de lo que ya toca medir: la ventana más grande que ya pasó y todavía no tiene registro."""
    hechas = {(r.get('accion'), r.get('ventana')) for r in cargar(raiz)}
    salida = []
    for e in publicadas(libro):
        horas = (ahora - _hora(e['ts'])).total_seconds() / 3600
        vencidas = [w for w in VENTANAS_HORAS if horas >= w]
        if vencidas and (e['accion'], max(vencidas)) not in hechas:
            salida.append((e, max(vencidas), horas))
    return salida


def medir(raiz, ahora, ent, libro=None):
    """Lee los contadores de lo que ya toca y lo anota. Devuelve los registros nuevos."""
    libro = libro or nucleo.Libro(pathlib.Path(raiz) / 'publicacion' / 'libro.jsonl')
    pend = pendientes(raiz, ahora, libro)
    nuevos = []
    for i in range(0, len(pend), LOTE):
        grupo = pend[i:i + LOTE]
        url = API + '?' + '&'.join('uris=' + urllib.parse.quote(e['ref'], safe=':/') for e, _, _ in grupo)
        try:
            r = ent.http('GET', url, {'Accept': 'application/json'})
        except Exception as ex:
            raise ErrorResultados('no hubo respuesta de Bluesky al leer los contadores (%s)' % ex)
        if r.status != 200:
            raise ErrorResultados('Bluesky respondió HTTP %d al leer los contadores: %s' % (r.status, r.texto(120)))
        por_uri = {p.get('uri'): p for p in r.json().get('posts', [])}
        for e, ventana, horas in grupo:
            p = por_uri.get(e['ref'])
            reg = {'ts': ahora.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'accion': e['accion'], 'ref': e['ref'], 'ventana': ventana, 'horas': round(horas, 1)}
            if p is None:
                reg['ausente'] = True      # borrada u oculta: se anota para no volver a preguntar, y no cuenta en la tabla
            else:
                reg.update({'likes': int(p.get('likeCount', 0)), 'reposts': int(p.get('repostCount', 0)),
                            'respuestas': int(p.get('replyCount', 0)), 'citas': int(p.get('quoteCount', 0))})
            nuevos.append(reg)
    if nuevos:
        ruta = _ruta(raiz)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, 'a', encoding='utf-8') as f:
            for reg in nuevos:
                f.write(json.dumps(reg, sort_keys=True, ensure_ascii=False) + '\n')
    return nuevos


def _filas(raiz, libro=None):
    """Una fila por publicación medida (la medición más reciente), con los rasgos de su ficha del calendario."""
    from . import calendario
    items = {'calendario:%s:bluesky' % it['id']: it for it in calendario.cargar(raiz)}
    ultima = {}
    for r in cargar(raiz):
        if r.get('ausente'):
            continue
        a = r['accion']
        if a not in ultima or r['ventana'] >= ultima[a]['ventana']:
            ultima[a] = r
    filas = []
    for a, r in sorted(ultima.items()):
        it = items.get(a, {})
        filas.append({'accion': a, 'id': it.get('id', a), 'formato': it.get('formato') or 'sin formato', 'idioma': it.get('idioma') or '?',
                      'ventana': r['ventana'], 'puntaje': puntaje(r), 'likes': r['likes'], 'reposts': r['reposts'], 'respuestas': r['respuestas'], 'citas': r['citas']})
    return filas


def _promedios(filas, clave):
    grupos = {}
    for f in filas:
        grupos.setdefault(f[clave], []).append(f['puntaje'])
    return sorted(((k, sum(v) / len(v), len(v)) for k, v in grupos.items()), key=lambda t: (-t[1], t[0]))


def resumen(raiz):
    """Líneas de texto: cuántas publicaciones hay medidas y, si son suficientes, qué formatos e idiomas van mejor."""
    filas = _filas(raiz)
    if not filas:
        return ['Todavía no hay publicaciones medidas: se miden a las 24 horas y a los 3 días de salir.']
    L = ['%d publicación(es) medida(s). Puntaje = likes + 3 × reposts + 2 × respuestas + 2 × citas.' % len(filas), '']
    for f in sorted(filas, key=lambda f: -f['puntaje'])[:3]:
        L.append('- Más movida: «%s» (%s, %s) → %d (%d likes, %d reposts, %d respuestas, %d citas, a %d h)' % (f['id'], f['formato'], f['idioma'], f['puntaje'], f['likes'], f['reposts'], f['respuestas'], f['citas'], f['ventana']))
    L.append('')
    if len(filas) < MIN_PARA_CONCLUIR:
        L.append('Todavía son pocas (%d de %d): no saco conclusiones sobre formatos, solo las anoto.' % (len(filas), MIN_PARA_CONCLUIR))
        return L
    for clave, nombre in (('formato', 'Por formato'), ('idioma', 'Por idioma')):
        L.append(nombre + ' (promedio de puntaje, publicaciones):')
        L += ['- %s: %.1f (%d)' % t for t in _promedios(filas, clave)]
        L.append('')
    L.append('Una diferencia pequeña entre formatos no demuestra nada con tan pocas publicaciones: sirve para decidir qué probar más, no para descartar lo demás.')
    return L
