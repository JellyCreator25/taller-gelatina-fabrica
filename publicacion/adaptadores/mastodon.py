"""Mastodon: imagen con POST /api/v2/media (espera si responde 202) y estado con POST /api/v1/statuses y Idempotency-Key.
Fuentes: docs.joinmastodon.org/methods/statuses/, /methods/media/ y /methods/accounts/. El límite de caracteres depende del servidor: se usa 450 (el habitual es 500)."""
import hashlib
import json

from .imagen import preparar_imagen
from ..nucleo import ErrorPlan, ErrorPublicacion
from .. import red, texto as tx

LIMITE = 450


def _instancia(ent):
    inst = ent.env['MASTODON_INSTANCE'].strip().rstrip('/')
    if not inst.startswith('https://'):
        raise ErrorPublicacion('MASTODON_INSTANCE debe empezar por https://')
    return inst


class Mastodon:
    canal = 'mastodon'
    categoria = 'redes'
    secretos = ['MASTODON_INSTANCE', 'MASTODON_TOKEN']

    def acciones(self, ctx):
        idioma = ctx.idioma_de('mastodon')
        texto, problemas = tx.componer_post(ctx.spec, idioma, ctx.url_juego(idioma), ctx.linea_ia_corta(idioma))
        if problemas:
            raise ErrorPlan('; '.join(problemas))
        if len(texto) > LIMITE:
            raise ErrorPlan('el texto mide %d caracteres (se usa un máximo de %d): acórtalo en difusion.%s.post_corto' % (len(texto), LIMITE, idioma))
        return [{'id': '%s:%s:mastodon:post' % (ctx.id, ctx.version), 'tipo': 'post',
                 'datos': {'texto': texto, 'idioma': idioma, 'imagen': ctx.imagen_social(), 'alt': ctx.texto_alternativo(idioma)}}]

    def ejecutar(self, a, ent, ctx):
        d = a['datos']
        inst = _instancia(ent)
        aut = {'Authorization': 'Bearer ' + ent.env['MASTODON_TOKEN']}
        ids = []
        if d.get('imagen'):
            datos, mime = preparar_imagen(str(ctx.raiz / d['imagen']['archivo']), max_bytes=3000000)
            cuerpo, tipo = red.multipart({'description': d['alt']}, {'file': ('portada.jpg', datos, mime)})
            r = ent.http('POST', inst + '/api/v2/media', dict(aut, **{'Content-Type': tipo}), cuerpo)
            if r.status not in (200, 202) or 'id' not in r.json():
                raise ErrorPublicacion('Mastodon no aceptó la imagen (HTTP %d: %s)' % (r.status, r.texto(120)))
            media = r.json()['id']
            if r.status == 202:   # se procesa: se consulta hasta que dé 200
                for _ in range(20):
                    ent.dormir(3)
                    if ent.http('GET', inst + '/api/v1/media/' + media, aut).status == 200:
                        break
                else:
                    raise ErrorPublicacion('Mastodon no terminó de procesar la imagen a tiempo')
            ids = [media]
        cuerpo = json.dumps({'status': d['texto'], 'language': d['idioma'], 'visibility': 'public', 'media_ids': ids}).encode('utf-8')
        cab = dict(aut, **{'Content-Type': 'application/json', 'Idempotency-Key': hashlib.sha256(a['id'].encode()).hexdigest()[:32]})
        r = None
        for intento in (1, 2):   # con Idempotency-Key repetir es seguro (la misma clave no duplica durante una hora)
            try:
                r = ent.http('POST', inst + '/api/v1/statuses', cab, cuerpo)
                break
            except red.ErrorRed as e:
                if intento == 2:
                    raise ErrorPublicacion('Mastodon no respondió (%s): mira la cuenta antes de repetir' % e, incierto=True)
        if r.status == 200:
            j = r.json()
            return {'detalle': 'estado publicado', 'ref': j.get('uri'), 'url': j.get('url')}
        if r.status >= 500:
            raise ErrorPublicacion('Mastodon respondió %d: mira la cuenta antes de repetir' % r.status, incierto=True)
        raise ErrorPublicacion('Mastodon rechazó el estado (HTTP %d: %s)' % (r.status, r.texto(160)))


def marcar_bot(ent, politica):
    inst = _instancia(ent)
    r = ent.http('PATCH', inst + '/api/v1/accounts/update_credentials', {'Authorization': 'Bearer ' + ent.env['MASTODON_TOKEN'], 'Content-Type': 'application/x-www-form-urlencoded'},
                 b'bot=true')
    if r.status != 200:
        raise ErrorPublicacion('Mastodon no marcó la cuenta como bot (HTTP %d: %s)' % (r.status, r.texto(120)))
    return 'cuenta marcada como bot'
