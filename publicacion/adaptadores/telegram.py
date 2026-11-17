"""Canal propio de Telegram con un bot: sendMessage. Fuentes: core.telegram.org/bots/api (forma de la URL y de la respuesta) y /bots/faq (límites de envío).
Los nombres de parámetros chat_id y text no pude releerlos hoy (la página se truncó); el primer envío real se hace supervisado."""
import json

from ..nucleo import ErrorPlan, ErrorPublicacion
from .. import texto as tx

LIMITE = 900


class Telegram:
    canal = 'telegram-canal'
    categoria = 'redes'
    secretos = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']

    def acciones(self, ctx):
        idioma = ctx.idioma_de('telegram-canal')
        texto, problemas = tx.componer_post(ctx.spec, idioma, ctx.url_juego(idioma), ctx.linea_ia_corta(idioma))
        if problemas:
            raise ErrorPlan('; '.join(problemas))
        if len(texto) > LIMITE:
            raise ErrorPlan('el texto mide %d caracteres (máximo %d): acórtalo en difusion.%s.post_corto' % (len(texto), LIMITE, idioma))
        return [{'id': '%s:%s:telegram:post' % (ctx.id, ctx.version), 'tipo': 'post', 'datos': {'texto': texto, 'idioma': idioma}}]

    def ejecutar(self, a, ent, ctx):
        url = 'https://api.telegram.org/bot%s/sendMessage' % ent.env['TELEGRAM_BOT_TOKEN']
        cuerpo = json.dumps({'chat_id': ent.env['TELEGRAM_CHAT_ID'], 'text': a['datos']['texto']}).encode('utf-8')
        r = ent.http('POST', url, {'Content-Type': 'application/json'}, cuerpo)
        j = r.json()
        if r.status == 200 and j.get('ok'):
            return {'detalle': 'mensaje enviado', 'ref': str((j.get('result') or {}).get('message_id', ''))}
        if r.status >= 500:
            raise ErrorPublicacion('Telegram respondió %d: mira el canal antes de repetir' % r.status, incierto=True)
        raise ErrorPublicacion('Telegram rechazó el mensaje (HTTP %d: %s)' % (r.status, j.get('description') or r.texto(120)))
