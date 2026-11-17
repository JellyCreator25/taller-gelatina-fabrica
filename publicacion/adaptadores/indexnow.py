"""Aviso a buscadores con IndexNow. Fuente: indexnow.org/documentation y /faq (endpoint global https://api.indexnow.org/indexnow; basta enviar a uno)."""
import hashlib
import json
from urllib.parse import urlparse

from ..nucleo import ErrorPlan, ErrorPublicacion

ENDPOINT = 'https://api.indexnow.org/indexnow'


def clave_de(sitio):
    """Clave pública del sitio (va en un archivo de la raíz, no es un secreto). Si sitio.json no la fija, se deriva de la dirección."""
    return sitio.get('indexnow_clave') or hashlib.sha256(str(sitio.get('url_base', '')).encode('utf-8')).hexdigest()[:32]


class IndexNow:
    canal = 'indexnow'
    categoria = 'sitio'
    secretos = []

    def acciones(self, ctx):
        base = ctx.base()
        clave = clave_de(ctx.sitio)
        if not (ctx.dist / (clave + '.txt')).exists():
            raise ErrorPlan('el sitio generado no trae el archivo %s.txt: corre «python3 fabrica.py sitio»' % clave)
        urls = [ctx.url_juego(i) for i in ctx.spec['idiomas']] + ['%s/%s/' % (base, i) for i in ctx.spec['idiomas']]
        return [{'id': 'indexnow:%s:%s' % (ctx.id, ctx.version), 'tipo': 'avisar',
                 'datos': {'host': urlparse(base).netloc, 'clave': clave, 'ubicacion': '%s/%s.txt' % (base, clave), 'urls': urls}}]

    def ejecutar(self, a, ent, ctx):
        d = a['datos']
        cuerpo = json.dumps({'host': d['host'], 'key': d['clave'], 'keyLocation': d['ubicacion'], 'urlList': d['urls']}).encode('utf-8')
        r = ent.http('POST', ENDPOINT, {'Content-Type': 'application/json; charset=utf-8'}, cuerpo)
        if r.status in (200, 202):
            return {'detalle': 'IndexNow recibió %d direcciones (HTTP %d%s)' % (len(d['urls']), r.status, ': clave pendiente de validar' if r.status == 202 else '')}
        razones = {400: 'formato inválido', 403: 'clave no válida (¿está %s en la raíz del sitio?)' % d['ubicacion'], 422: 'direcciones de otro dominio o clave que no cumple el formato',
                   429: 'demasiadas solicitudes (posible spam): se detiene'}
        raise ErrorPublicacion('IndexNow respondió %d: %s' % (r.status, razones.get(r.status, r.texto(120))))
