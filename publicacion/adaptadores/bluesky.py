"""Bluesky (AT Protocol): sesión con contraseña de aplicación, imagen con uploadBlob y post con createRecord.
Fuentes: atproto.com/guides/bot-tutorial (cuenta dedicada, contraseña de aplicación, etiqueta «bot», sin interacciones automáticas), lexicons app.bsky.feed.post y com.atproto.repo.uploadBlob.
No leí hoy el esquema de app.bsky.embed.images ni getRecord/putRecord: el primer envío real se hace supervisado."""
import json
import re
import unicodedata

from .imagen import preparar_imagen
from ..nucleo import ErrorPlan, ErrorPublicacion
from .. import texto as tx

LIMITE = 300           # límite de grafemas de un post (lexicon app.bsky.feed.post)
LIMITE_PRUDENTE = 290  # si el texto lleva emojis o marcas combinantes, el conteo propio es aproximado: se deja margen


def limite_para(texto):
    ambiguo = any(unicodedata.category(c)[0] == 'M' or unicodedata.category(c) in ('Cf', 'So', 'Cs', 'Co') or ord(c) >= 0x1F000 for c in texto)
    return LIMITE_PRUDENTE if ambiguo else LIMITE


def _credenciales(ent):
    """Identificador (sin espacios ni «@» al borde, que se cuelan al copiar) y contraseña de aplicación (sin espacios ni saltos de línea al borde)."""
    ident = (ent.env.get('BSKY_IDENTIFIER') or '').strip().lstrip('@').strip()
    clave = (ent.env.get('BSKY_APP_PASSWORD') or '').strip()
    return ident, clave


def _pistas(ident, clave):
    """Qué suele fallar cuando Bluesky rechaza el inicio de sesión. Solo cuentas y formas: nunca el contenido de las claves."""
    pistas = []
    if not ident:
        pistas.append('BSKY_IDENTIFIER está vacío')
    else:
        if '@' in ident:
            pistas.append('BSKY_IDENTIFIER parece un correo (lleva «@»): usa el nombre de usuario, por ejemplo usuario.bsky.social')
        if re.search(r'\s', ident):
            pistas.append('BSKY_IDENTIFIER trae espacios o saltos de línea en medio')
        if '.' not in ident and '@' not in ident:
            pistas.append('BSKY_IDENTIFIER no trae el dominio completo: el nombre de usuario completo termina en «.bsky.social»')
    if not clave:
        pistas.append('BSKY_APP_PASSWORD está vacío')
    else:
        if re.search(r'\s', clave):
            pistas.append('BSKY_APP_PASSWORD trae espacios o saltos de línea en medio')
        if not re.fullmatch(r'[a-z0-9]{4}(-[a-z0-9]{4}){3}', clave):
            pistas.append('BSKY_APP_PASSWORD mide %d caracteres y no tiene la forma de una contraseña de aplicación (cuatro grupos de cuatro separados por guiones, 19 caracteres): '
                          '¿es la contraseña normal de la cuenta? Las de aplicación se crean en Configuración → Privacidad y seguridad → Contraseñas de aplicación' % len(clave))
    return pistas


def _sesion(ent, pds):
    ident, clave = _credenciales(ent)
    r = ent.http('POST', pds + '/xrpc/com.atproto.server.createSession', {'Content-Type': 'application/json'},
                 json.dumps({'identifier': ident, 'password': clave}).encode('utf-8'))
    if r.status != 200:
        codigo = r.json().get('error') if isinstance(r.json(), dict) else None
        codigo = codigo if isinstance(codigo, str) and re.fullmatch(r'[A-Za-z]{1,40}', codigo) else None
        pistas = _pistas(ident, clave)
        raise ErrorPublicacion('Bluesky no inició sesión (HTTP %d%s): revisa BSKY_IDENTIFIER y la contraseña de aplicación%s' % (
            r.status, ', ' + codigo if codigo else '', '. Pistas: ' + '; '.join(pistas) if pistas else ''))
    s = r.json()
    return s['accessJwt'], s['did']


class Bluesky:
    canal = 'bluesky'
    categoria = 'redes'
    secretos = ['BSKY_IDENTIFIER', 'BSKY_APP_PASSWORD']

    def acciones(self, ctx):
        idioma = ctx.idioma_de('bluesky')
        texto, problemas = tx.componer_post(ctx.spec, idioma, ctx.url_juego(idioma), ctx.linea_ia(idioma))
        if problemas:
            raise ErrorPlan('; '.join(problemas))
        n, tope = tx.grafemas(texto), limite_para(texto)
        if n > tope or tx.bytes_utf8(texto) > 3000:
            raise ErrorPlan('el texto mide %d grafemas (máximo %d) y %d bytes (máximo 3000): acórtalo en difusion.%s.post_corto de juego.json' % (n, tope, tx.bytes_utf8(texto), idioma))
        return [{'id': '%s:%s:bluesky:post' % (ctx.id, ctx.version), 'tipo': 'post',
                 'datos': {'texto': texto, 'idioma': idioma, 'imagen': ctx.imagen_social(), 'alt': ctx.texto_alternativo(idioma)}}]

    def ejecutar(self, a, ent, ctx):
        d = a['datos']
        pds = ((ctx.politica.get('bluesky') or {}).get('pds') or 'https://bsky.social').rstrip('/')
        jwt, did = _sesion(ent, pds)
        aut = {'Authorization': 'Bearer ' + jwt}
        record = {'$type': 'app.bsky.feed.post', 'text': d['texto'], 'createdAt': ent.ahora().strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                  'langs': [d['idioma']], 'facets': tx.facetas_enlaces(d['texto'])}
        if d.get('imagen'):
            datos, mime = preparar_imagen(str(ctx.raiz / d['imagen']['archivo']))
            r = ent.http('POST', pds + '/xrpc/com.atproto.repo.uploadBlob', dict(aut, **{'Content-Type': mime}), datos)
            if r.status != 200 or 'blob' not in r.json():
                raise ErrorPublicacion('Bluesky no aceptó la imagen (HTTP %d: %s)' % (r.status, r.texto(120)))
            record['embed'] = {'$type': 'app.bsky.embed.images', 'images': [{'alt': d['alt'], 'image': r.json()['blob']}]}
        cuerpo = json.dumps({'repo': did, 'collection': 'app.bsky.feed.post', 'record': record}).encode('utf-8')
        try:
            r = ent.http('POST', pds + '/xrpc/com.atproto.repo.createRecord', dict(aut, **{'Content-Type': 'application/json'}), cuerpo)
        except Exception as e:   # sin respuesta: el post pudo haberse creado; no se reintenta
            raise ErrorPublicacion('Bluesky no respondió al crear el post (%s): mira la cuenta antes de repetir' % e, incierto=True)
        if r.status == 200:
            uri = r.json().get('uri', '')
            return {'detalle': 'post creado', 'ref': uri, 'url': 'https://bsky.app/profile/%s/post/%s' % (did, uri.rsplit('/', 1)[-1])}
        if r.status >= 500:
            raise ErrorPublicacion('Bluesky respondió %d al crear el post: mira la cuenta antes de repetir' % r.status, incierto=True)
        raise ErrorPublicacion('Bluesky rechazó el post (HTTP %d: %s)' % (r.status, r.texto(160)))


def marcar_bot(ent, politica):
    """Configuración de una sola vez (la recomienda la guía oficial de bots): pone la etiqueta propia «bot» en el perfil, conservando el resto del perfil."""
    pds = ((politica.get('bluesky') or {}).get('pds') or 'https://bsky.social').rstrip('/')
    jwt, did = _sesion(ent, pds)
    aut = {'Authorization': 'Bearer ' + jwt}
    r = ent.http('GET', pds + '/xrpc/com.atproto.repo.getRecord?repo=%s&collection=app.bsky.actor.profile&rkey=self' % did, aut)
    if r.status == 200:
        perfil, cid = r.json().get('value', {}), r.json().get('cid')
    elif r.status in (400, 404):
        perfil, cid = {'$type': 'app.bsky.actor.profile'}, None
    else:
        raise ErrorPublicacion('Bluesky no devolvió el perfil (HTTP %d)' % r.status)
    perfil['labels'] = {'$type': 'com.atproto.label.defs#selfLabels', 'values': [{'val': 'bot'}]}
    cuerpo = {'repo': did, 'collection': 'app.bsky.actor.profile', 'rkey': 'self', 'record': perfil}
    if cid:
        cuerpo['swapRecord'] = cid
    r = ent.http('POST', pds + '/xrpc/com.atproto.repo.putRecord', dict(aut, **{'Content-Type': 'application/json'}), json.dumps(cuerpo).encode('utf-8'))
    if r.status != 200:
        raise ErrorPublicacion('Bluesky no guardó la etiqueta (HTTP %d: %s)' % (r.status, r.texto(160)))
    return 'etiqueta «bot» puesta en el perfil de %s' % did
