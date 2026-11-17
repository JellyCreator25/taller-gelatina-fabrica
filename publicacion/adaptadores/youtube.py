"""YouTube: subida reanudable con videos.insert y OAuth con token de actualización.
Fuentes: developers.google.com/youtube/v3/docs/videos/insert (endpoint, part, permisos, campos, cuota) y developers.google.com/identity/protocols/oauth2 (caducidad de tokens).
La subida reanudable (uploadType=resumable, cabecera Location) y el endpoint del token siguen la guía general de Google, que no releí hoy: la primera subida real se hace supervisada."""
import json
import urllib.parse

from ..nucleo import ErrorPlan, ErrorPublicacion, sha256_archivo
from .. import red

TOKEN_URL = 'https://oauth2.googleapis.com/token'
SUBIDA_URL = 'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status'


class YouTube:
    canal = 'youtube-api'
    categoria = 'redes'
    secretos = ['YT_CLIENT_ID', 'YT_CLIENT_SECRET', 'YT_REFRESH_TOKEN']

    def acciones(self, ctx):
        clip = ctx.archivo('salida/%s/medios/clip-vertical.mp4' % ctx.id)
        if not clip:
            raise ErrorPlan('falta medios/clip-vertical.mp4 (corre «python3 fabrica.py probar %s»)' % ctx.id)
        idioma = ctx.idioma_de('youtube-api')
        f = ctx.spec['ficha'][idioma]
        d = ((ctx.spec.get('difusion') or {}).get(idioma) or {})
        linea = ctx.linea_ia(idioma)
        url = ctx.url_juego(idioma)
        descr = (d.get('descripcion_video', '').replace('{ia}', linea).strip() + '\n\n' + url + '\n\n#indiegame #juegosweb').strip()
        titulo = f['titulo']
        pol = ctx.politica.get('youtube') or {}
        if 'PENDIENTE' in descr or '{' in descr:
            raise ErrorPlan('la descripción del video tiene marcas sin resolver o PENDIENTE')
        if linea and linea not in descr:
            raise ErrorPlan('la descripción del video no lleva la línea de IA')
        if len(titulo) > 100 or len(descr) > 5000:
            raise ErrorPlan('título (%d) o descripción (%d) exceden los límites de YouTube (100 y 5000)' % (len(titulo), len(descr)))
        return [{'id': '%s:%s:youtube:video' % (ctx.id, ctx.version), 'tipo': 'video',
                 'datos': {'archivo': clip['archivo'], 'sha256': clip['sha256'], 'titulo': titulo, 'descripcion': descr, 'idioma': idioma,
                           'etiquetas': pol.get('etiquetas', []), 'categoria': str(pol.get('categoria', '20')), 'privacidad': pol.get('privacidad', 'public'),
                           'hecho_para_ninos': bool(pol.get('hecho_para_ninos', False)), 'contenido_sintetico': bool(pol.get('contenido_sintetico', False))}}]

    def ejecutar(self, a, ent, ctx):
        d = a['datos']
        r = ent.http('POST', TOKEN_URL, {'Content-Type': 'application/x-www-form-urlencoded'}, urllib.parse.urlencode(
            {'client_id': ent.env['YT_CLIENT_ID'], 'client_secret': ent.env['YT_CLIENT_SECRET'], 'refresh_token': ent.env['YT_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode())
        if r.status != 200 or 'access_token' not in r.json():
            raise ErrorPublicacion('Google no dio un token de acceso (HTTP %d). Si pasó a los 7 días de autorizar, la pantalla de consentimiento sigue en modo de prueba: '
                                   'hay que publicarla y autorizar de nuevo' % r.status)
        ruta = ctx.raiz / d['archivo']
        if sha256_archivo(ruta) != d['sha256']:
            raise ErrorPublicacion('el clip cambió después de aprobar el plan: se detiene')
        datos = ruta.read_bytes()
        snippet = {'title': d['titulo'], 'description': d['descripcion'], 'tags': d['etiquetas'], 'categoryId': d['categoria'], 'defaultLanguage': d['idioma']}
        estado = {'privacyStatus': d['privacidad'], 'selfDeclaredMadeForKids': d['hecho_para_ninos']}
        if d['contenido_sintetico']:
            estado['containsSyntheticMedia'] = True
        aut = {'Authorization': 'Bearer ' + r.json()['access_token']}
        r = ent.http('POST', SUBIDA_URL, dict(aut, **{'Content-Type': 'application/json; charset=UTF-8', 'X-Upload-Content-Length': str(len(datos)),
                                                      'X-Upload-Content-Type': 'video/mp4'}), json.dumps({'snippet': snippet, 'status': estado}).encode('utf-8'))
        sesion = r.cabeceras.get('location')
        if r.status != 200 or not sesion:
            raise ErrorPublicacion('YouTube no abrió la subida (HTTP %d: %s)' % (r.status, r.texto(160)))
        try:
            r = ent.http('PUT', sesion, dict(aut, **{'Content-Type': 'video/mp4', 'Content-Length': str(len(datos))}), datos)
        except red.ErrorRed as e:
            raise ErrorPublicacion('la subida a YouTube se cortó (%s): mira tu canal antes de repetir' % e, incierto=True)
        if r.status in (200, 201) and r.json().get('id'):
            vid = r.json()['id']
            return {'detalle': 'video subido (%s)' % d['privacidad'], 'ref': vid, 'url': 'https://www.youtube.com/watch?v=' + vid}
        raise ErrorPublicacion('YouTube no confirmó la subida (HTTP %d: %s): mira tu canal antes de repetir' % (r.status, r.texto(160)), incierto=r.status >= 500)
