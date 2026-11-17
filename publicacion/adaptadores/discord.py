"""Servidor propio de Discord mediante un webhook. Fuente: docs.discord.com/developers/resources/webhook (POST /webhooks/ID/TOKEN; content ≤2000; allowed_mentions;
el token no pide autenticación, así que la URL completa es un secreto)."""
import json
import re

from ..nucleo import ErrorPlan, ErrorPublicacion
from .. import texto as tx

URL_VALIDA = re.compile(r'^https://(?:discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$')


class Discord:
    canal = 'discord-webhook'
    categoria = 'redes'
    secretos = ['DISCORD_WEBHOOK_URL']

    def acciones(self, ctx):
        idioma = ctx.idioma_de('discord-webhook')
        texto, problemas = tx.componer_post(ctx.spec, idioma, ctx.url_juego(idioma), ctx.linea_ia(idioma))
        if problemas:
            raise ErrorPlan('; '.join(problemas))
        if len(texto) > 1800:
            raise ErrorPlan('el texto mide %d caracteres (Discord admite 2000; se usa 1800 de margen)' % len(texto))
        return [{'id': '%s:%s:discord:post' % (ctx.id, ctx.version), 'tipo': 'post',
                 'datos': {'texto': texto, 'idioma': idioma, 'nombre': str(ctx.sitio.get('nombre', 'Novedades'))[:80]}}]

    def ejecutar(self, a, ent, ctx):
        url = ent.env['DISCORD_WEBHOOK_URL'].strip()
        if not URL_VALIDA.match(url):
            raise ErrorPublicacion('DISCORD_WEBHOOK_URL no tiene la forma https://discord.com/api/webhooks/ID/TOKEN')
        cuerpo = json.dumps({'username': a['datos']['nombre'], 'content': a['datos']['texto'], 'allowed_mentions': {'parse': []}}).encode('utf-8')
        r = ent.http('POST', url + '?wait=true', {'Content-Type': 'application/json'}, cuerpo)
        if r.status in (200, 204):
            return {'detalle': 'mensaje enviado', 'ref': str(r.json().get('id', ''))}
        if r.status >= 500:
            raise ErrorPublicacion('Discord respondió %d: mira el canal antes de repetir' % r.status, incierto=True)
        raise ErrorPublicacion('Discord rechazó el mensaje (HTTP %d: %s)' % (r.status, r.texto(120)))
