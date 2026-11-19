"""Comprobar solo qué pasó con un envío que quedó en duda («incierto» en el libro), para que el calendario no se detenga hasta que una persona mire la cuenta.

Solo LEE la cuenta pública: no usa claves, no publica nada y no toca nada que no sea el libro de registro. Es conservador a propósito, porque
equivocarse hacia «no salió» repetiría un post en público:

  «salió»     solo si, entre las publicaciones recientes de la cuenta, hay una propia cuyo texto tiene el hash que el libro anotó al intentar
              y cuya hora cae en la ventana del intento.
  «no salió»  solo si (1) pasó tiempo suficiente, (2) la lectura llega hasta antes de la ventana del intento, (3) en esa misma lectura se ve un
              post que SÍ salió antes (prueba de que la lectura funciona y es de la cuenta correcta) y (4) no se había descartado ya
              automáticamente una vez este mismo envío.
  en duda     todo lo demás (red caída, el libro no anotó cuenta o texto, canal sin comprobador, lectura que no cubre el intento…): no se anota nada
              y la duda sigue, con el motivo a la vista.

La lectura usa la API pública de Bluesky (app.bsky.feed.getAuthorFeed, sin autenticación, más nuevas primero). No pude probarla contra la red real
desde donde se escribió; `python3 fabrica.py resolver --verificar` lo comprueba sin escribir nada, y el flujo «Comprobar» lo corre en GitHub."""
import datetime
import urllib.parse

from . import nucleo, red

APPVIEW = 'https://public.api.bsky.app'
PAGINA = 100                                   # máximo de getAuthorFeed
PAGINAS_MAX = 3                                # hasta 300 publicaciones recientes
ESPERA_MIN = datetime.timedelta(minutes=30)    # antes de esto un post puede estar por aparecer
VENTANA_ANTES = datetime.timedelta(minutes=20)  # createdAt del post = hora al empezar el intento; el libro anota al terminar
VENTANA_DESPUES = datetime.timedelta(minutes=2)
QUIEN = 'la comprobación automática'


class ErrorComprobacion(Exception):
    """La lectura pública no sirvió (respuesta rara, código distinto de 200)."""


def _tiempo(valor):
    """datetime con zona UTC o None si el texto no se entiende."""
    try:
        t = datetime.datetime.fromisoformat(str(valor).replace('Z', '+00:00'))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)


def _en_duda(motivo):
    return {'estado': 'sigue-en-duda', 'motivo': motivo}


def leer_cuenta(http, did, appview=APPVIEW):
    """Publicaciones propias recientes de la cuenta, de la más nueva a la más vieja. → (items, completa).
    items: [{'uri', 'texto', 'creado'}]; completa=True si ya no quedaban más páginas. Lanza red.ErrorRed o ErrorComprobacion."""
    items, cursor = [], None
    for _ in range(PAGINAS_MAX):
        url = '%s/xrpc/app.bsky.feed.getAuthorFeed?actor=%s&limit=%d' % (appview, urllib.parse.quote(did, safe=':'), PAGINA)
        if cursor:
            url += '&cursor=' + urllib.parse.quote(cursor, safe='')
        r = http('GET', url, {'Accept': 'application/json'})
        if r.status != 200:
            raise ErrorComprobacion('la lectura pública de la cuenta respondió HTTP %d' % r.status)
        d = r.json()
        feed = d.get('feed') if isinstance(d, dict) else None
        if not isinstance(feed, list):
            raise ErrorComprobacion('la lectura pública no trajo una lista de publicaciones')
        for it in feed:
            post = (it or {}).get('post') or {}
            if (post.get('author') or {}).get('did') != did:     # un repost de otra cuenta no es un post propio
                continue
            rec = post.get('record') or {}
            items.append({'uri': str(post.get('uri', '')), 'texto': str(rec.get('text', '')), 'creado': _tiempo(rec.get('createdAt', ''))})
        cursor = d.get('cursor')
        if not cursor:
            return items, True
    return items, False


def _llega_antes_de(items, completa, instante):
    """¿La lectura cubre hasta antes de `instante`? (más nuevas primero: basta con ver algo más viejo)."""
    return completa or any(i['creado'] and i['creado'] < instante for i in items)


def _ancla_de(entradas, entrada):
    """El post más reciente de esa misma cuenta que SÍ salió (fila «ok» de Bluesky con referencia): {'uri', 'ts'} o None."""
    did = entrada.get('did')
    mejor = None
    for e in entradas:
        ref = str(e.get('ref') or '')
        if e.get('canal') == 'bluesky' and e.get('resultado') == 'ok' and ref.startswith('at://') and (not did or ref.startswith('at://%s/' % did)):
            t = _tiempo(e.get('ts'))
            if t and (mejor is None or t >= mejor['ts']):
                mejor = {'uri': ref, 'ts': t}
    return mejor


def comprobar_bluesky(http, entrada, ahora, ancla=None, descartes_previos=0):
    """entrada: la fila «incierto» del libro. → {'estado': 'salio'|'no-salio'|'sigue-en-duda', 'motivo', ['ref', 'url']}."""
    did = entrada.get('did') or (ancla['uri'].split('/')[2] if ancla else None)
    sha = entrada.get('texto_sha256')
    ts = _tiempo(entrada.get('ts'))
    if not did or not sha or ts is None:
        return _en_duda('el libro no anotó con qué cuenta ni con qué texto se intentó (es un envío anterior a este comprobador): hay que mirar la cuenta')
    desde, hasta = ts - VENTANA_ANTES, ts + VENTANA_DESPUES
    try:
        items, completa = leer_cuenta(http, did)
    except (red.ErrorRed, ErrorComprobacion) as e:
        return _en_duda('no pude leer la cuenta pública (%s); se reintenta en la siguiente corrida' % e)
    for it in items:
        if it['creado'] and desde <= it['creado'] <= hasta and nucleo.sha256_texto(it['texto']) == sha:
            return {'estado': 'salio', 'motivo': 'el post con ese texto está en la cuenta (%s)' % it['uri'], 'ref': it['uri'],
                    'url': 'https://bsky.app/profile/%s/post/%s' % (did, it['uri'].rsplit('/', 1)[-1])}
    if ahora - ts < ESPERA_MIN:
        return _en_duda('el intento es de hace menos de 30 minutos y el post puede estar por aparecer')
    if not _llega_antes_de(items, completa, desde):
        return _en_duda('la lectura no llegó hasta antes del intento (la cuenta publicó mucho desde entonces): hay que mirar la cuenta')
    if ancla is None:
        return _en_duda('no hay un post anterior que sí salió con el que comprobar que la lectura es de esta cuenta: hay que mirar la cuenta')
    if (completa or _llega_antes_de(items, completa, ancla['ts'])) and not any(i['uri'] == ancla['uri'] for i in items):
        return _en_duda('la lectura no mostró un post que sí salió (%s): no me fío de ella, hay que mirar la cuenta' % ancla['uri'])
    if descartes_previos >= 1:
        return _en_duda('este envío ya se descartó una vez automáticamente y volvió a quedar en duda: que lo mire una persona')
    return {'estado': 'no-salio', 'motivo': 'la lectura cubre el intento, se ve el post anterior que sí salió y ninguno tiene ese texto'}


COMPROBADORES = {('bluesky', 'post'): comprobar_bluesky}


def en_duda(entradas):
    """Última fila de cada acción cuyo último resultado es «incierto»."""
    ultima = {}
    for e in entradas:
        ultima[e.get('accion')] = e
    return [e for e in ultima.values() if e.get('resultado') == 'incierto']


def resolver_en_duda(libro, http, ahora, accion=None):
    """Comprueba cada envío en duda (o solo `accion`) y anota en el libro los que se pueden aclarar. → [{'accion', 'estado', 'motivo'}]."""
    entradas = libro.entradas()
    dudosas = [e for e in en_duda(entradas) if accion is None or e['accion'] == accion]
    if accion and not dudosas:
        raise nucleo.ErrorPublicacion('«%s» no tiene un resultado dudoso en el libro; nada que resolver' % accion)
    informe = []
    for e in dudosas:
        comprobador = COMPROBADORES.get((e.get('canal'), e.get('tipo')))
        if comprobador is None:
            informe.append({'accion': e['accion'], 'estado': 'sigue-en-duda', 'motivo': 'este canal no se comprueba solo: hay que mirar la cuenta'})
            continue
        descartes = sum(1 for x in entradas if x.get('accion') == e['accion'] and x.get('resultado') == 'descartado')
        r = comprobador(http, e, ahora, ancla=_ancla_de(entradas, e), descartes_previos=descartes)
        if r['estado'] == 'salio':
            nucleo.resolver(libro, e['accion'], True, ahora, quien=QUIEN, extra={k: r[k] for k in ('ref', 'url') if r.get(k)})
        elif r['estado'] == 'no-salio':
            nucleo.resolver(libro, e['accion'], False, ahora, quien=QUIEN)
        informe.append({'accion': e['accion'], 'estado': r['estado'], 'motivo': r['motivo']})
    return informe


def verificar(http, entradas):
    """Comprobación de solo lectura de que la lectura pública funciona: ¿se ve el último post que sí salió? → (estado, texto); estado: ok|inconcluso|falla."""
    ancla = _ancla_de(entradas, {})
    if ancla is None:
        return 'inconcluso', 'el libro no tiene todavía un post de Bluesky que haya salido; no hay con qué comparar'
    did = ancla['uri'].split('/')[2]
    try:
        items, completa = leer_cuenta(http, did)
    except (red.ErrorRed, ErrorComprobacion) as e:
        return 'falla', 'no pude leer la cuenta pública: %s' % e
    if any(i['uri'] == ancla['uri'] for i in items):
        return 'ok', 'la lectura funciona: se ve el post %s entre las %d publicaciones recientes' % (ancla['uri'], len(items))
    if not completa and not _llega_antes_de(items, completa, ancla['ts']):
        return 'inconcluso', 'ese post es más viejo que las %d publicaciones leídas; no se puede comparar' % len(items)
    return 'falla', 'la lectura no muestra el post %s, que el libro dice que salió (¿lo borraron, o la lectura no es de esa cuenta?)' % ancla['uri']
