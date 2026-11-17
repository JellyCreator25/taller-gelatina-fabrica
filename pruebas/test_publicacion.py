"""Pruebas del módulo de publicación con servicios simulados: ninguna toca la red ni necesita claves.
Lo que se comprueba (cada prueba nombra la regla que protege):
  · la huella cubre todo lo que se publica y no depende del orden del proceso
  · sin la aprobación exacta no sale nada; si algo cambia después de aprobar, se detiene
  · la forma exacta de cada petición a cada servicio, y que las claves nunca llegan al libro
  · lo ya hecho no se repite; lo dudoso no se repite solo; el ritmo y las compuertas frenan
Correr: python3 -I -m unittest discover -s pruebas   (desde la carpeta de la fábrica)"""
import datetime
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / 'herramientas'))

from publicacion import nucleo, red, texto as tx          # noqa: E402
from publicacion.adaptadores import ADAPTADORES            # noqa: E402
from publicacion.adaptadores import imagen as img          # noqa: E402
import sitio as gen                                        # noqa: E402

SECRETOS = {
    'CLOUDFLARE_API_TOKEN': 'cf-token-SECRETO-1', 'CLOUDFLARE_ACCOUNT_ID': 'cfcuenta123',
    'BSKY_IDENTIFIER': 'taller.bsky.social', 'BSKY_APP_PASSWORD': 'app-clave-SECRETO-2',
    'MASTODON_INSTANCE': 'https://mast.ejemplo', 'MASTODON_TOKEN': 'masto-token-SECRETO-3',
    'TELEGRAM_BOT_TOKEN': '123456:TELE-SECRETO-4', 'TELEGRAM_CHAT_ID': '@canal_gelatina',
    'DISCORD_WEBHOOK_URL': 'https://discord.com/api/webhooks/123456789/WEBHOOK-SECRETO-5',
    'YT_CLIENT_ID': 'ytid', 'YT_CLIENT_SECRET': 'yt-secreto-SECRETO-6', 'YT_REFRESH_TOKEN': 'yt-refresco-SECRETO-7',
    'BUTLER_API_KEY': 'butler-SECRETO-8',
}
SITIO_URL = 'https://taller-gelatina.pages.dev'
TODOS = ['sitio-propio', 'indexnow', 'bluesky', 'mastodon', 'telegram-canal', 'discord-webhook', 'youtube-api', 'itch-pagina']
JUEGO = 'guerreros-gelatina'
PLANTILLA_PROYECTO = None


def _copiar_proyecto(destino):
    for carpeta in ('juegos', 'plantillas', 'catalogo', 'ideas', 'difusion', 'herramientas', 'publicacion', 'metricas'):
        shutil.copytree(RAIZ / carpeta, destino / carpeta, ignore=shutil.ignore_patterns('__pycache__', 'libro.jsonl'))
    shutil.copy(RAIZ / 'fabrica.py', destino / 'fabrica.py')
    shutil.copytree(RAIZ / 'motor', destino / 'motor')
    reales = {'portada.png', 'portada-web.jpg', 'captura-colocar-escritorio.png', 'captura-final-escritorio.png', 'captura-caida-escritorio.png', 'captura-juego-escritorio.png'}

    def copiar(origen, destino):
        # los medios pesados se reemplazan por un archivo mínimo: las pruebas solo necesitan que existan (el kit los cita) y que se puedan leer
        if pathlib.Path(origen).parent.name == 'medios' and pathlib.Path(origen).name not in reales:
            pathlib.Path(destino).write_bytes(b'archivo-de-prueba:' + pathlib.Path(origen).name.encode())
        else:
            shutil.copy2(origen, destino)
    for juego in (RAIZ / 'salida').iterdir():
        if juego.is_dir():
            shutil.copytree(juego, destino / 'salida' / juego.name, copy_function=copiar, ignore=shutil.ignore_patterns('tmp-video'))


def setUpModule():
    global PLANTILLA_PROYECTO
    PLANTILLA_PROYECTO = pathlib.Path(tempfile.mkdtemp(prefix='ggx-pruebas-'))
    _copiar_proyecto(PLANTILLA_PROYECTO)
    (PLANTILLA_PROYECTO / 'publicacion' / 'sitio.json').write_text(json.dumps({
        'nombre': 'Taller Gelatina', 'url_base': SITIO_URL, 'proyecto': 'taller-gelatina', 'rama_produccion': 'main', 'contacto': 'hola@ejemplo.org',
        'idioma_inicial': 'es', 'juegos': ['guerreros-gelatina'], 'privacidad_actualizada': '2026-11-12',
        'lema': {'es': 'Juegos para el navegador.', 'en': 'Browser games.', 'zh': '浏览器小游戏。'}, 'adsense_publisher': '', 'indexnow_clave': ''}), encoding='utf-8')
    politica = json.loads((PLANTILLA_PROYECTO / 'publicacion' / 'politica.json').read_text(encoding='utf-8'))
    politica['canales'] = TODOS
    politica['ritmo']['min_dias_entre_lanzamientos'] = 14
    (PLANTILLA_PROYECTO / 'publicacion' / 'politica.json').write_text(json.dumps(politica), encoding='utf-8')
    ficha = PLANTILLA_PROYECTO / 'juegos' / JUEGO / 'juego.json'
    spec = json.loads(ficha.read_text(encoding='utf-8'))
    spec['publicacion'] = {'itch': {'destino': 'taller/guerreros-gelatina', 'canal': 'html5'}}
    ficha.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding='utf-8')
    gen.generar(PLANTILLA_PROYECTO)


def tearDownModule():
    shutil.rmtree(PLANTILLA_PROYECTO, ignore_errors=True)


# ---------------------------------------------------------------------------------------------------------------------
# Servicios simulados
# ---------------------------------------------------------------------------------------------------------------------

def resp(estado=200, cuerpo=None, cabeceras=None):
    datos = json.dumps(cuerpo).encode('utf-8') if cuerpo is not None else b''
    return red.Respuesta(estado, cabeceras or {}, datos)


class Red:
    """http falso: responde según (método, prefijo de dirección) y guarda cada petición recibida."""

    def __init__(self):
        self.llamadas = []
        self.rutas = []

    def al(self, metodo, prefijo, respuesta):
        self.rutas.insert(0, (metodo, prefijo, respuesta))     # lo último que se registra manda

    def __call__(self, metodo, url, cabeceras=None, cuerpo=None):
        self.llamadas.append({'metodo': metodo, 'url': url, 'cab': dict(cabeceras or {}), 'cuerpo': cuerpo})
        for m, prefijo, r in self.rutas:
            if m == metodo and url.startswith(prefijo):
                if callable(r):
                    r = r(url, cabeceras or {}, cuerpo)
                if isinstance(r, Exception):
                    raise r
                return r
        raise AssertionError('petición no prevista: %s %s' % (metodo, url))

    def a(self, metodo, prefijo):
        return [c for c in self.llamadas if c['metodo'] == metodo and c['url'].startswith(prefijo)]

    @classmethod
    def todo_bien(cls):
        r = cls()
        r.al('GET', SITIO_URL + '/', resp(200))
        r.al('POST', 'https://api.indexnow.org/indexnow', resp(200))
        r.al('POST', 'https://bsky.social/xrpc/com.atproto.server.createSession', resp(200, {'accessJwt': 'jwt-uno', 'did': 'did:plc:abc123'}))
        r.al('POST', 'https://bsky.social/xrpc/com.atproto.repo.uploadBlob', resp(200, {'blob': {'$type': 'blob', 'ref': {'$link': 'bafkreiabc'}, 'mimeType': 'image/jpeg', 'size': 123}}))
        r.al('POST', 'https://bsky.social/xrpc/com.atproto.repo.createRecord', resp(200, {'uri': 'at://did:plc:abc123/app.bsky.feed.post/3kpost', 'cid': 'bafy'}))
        r.al('POST', 'https://mast.ejemplo/api/v2/media', resp(200, {'id': '555'}))
        r.al('POST', 'https://mast.ejemplo/api/v1/statuses', resp(200, {'uri': 'https://mast.ejemplo/users/taller/statuses/9', 'url': 'https://mast.ejemplo/@taller/9'}))
        r.al('POST', 'https://api.telegram.org/bot', resp(200, {'ok': True, 'result': {'message_id': 7}}))
        r.al('POST', 'https://discord.com/api/webhooks/123456789/', resp(200, {'id': '1'}))
        r.al('POST', 'https://oauth2.googleapis.com/token', resp(200, {'access_token': 'ya29.token'}))
        r.al('POST', 'https://www.googleapis.com/upload/youtube/v3/videos', resp(200, None, {'Location': 'https://subida.ejemplo/sesion1'}))
        r.al('PUT', 'https://subida.ejemplo/sesion1', resp(200, {'id': 'vid123'}))
        return r


class Cmd:
    def __init__(self, codigo=0):
        self.llamadas = []
        self.codigo = codigo

    def __call__(self, argv, cwd=None, env=None, tiempo=900):
        self.llamadas.append({'argv': list(argv), 'env': dict(env or {}), 'cwd': cwd})
        return self.codigo, 'ok', ''


class Reloj:
    def __init__(self):
        self.t = datetime.datetime(2026, 11, 20, 15, 0, tzinfo=datetime.timezone.utc)

    def __call__(self):
        return self.t

    def avanzar(self, **kw):
        self.t += datetime.timedelta(**kw)


class Proyecto:
    def __init__(self, raiz):
        self.raiz = pathlib.Path(raiz)
        self.red = Red.todo_bien()
        self.cmd = Cmd()
        self.reloj = Reloj()
        self.env = dict(SECRETOS)

    def ent(self):
        return nucleo.Entorno(env=self.env, http=self.red, cmd=self.cmd, ahora=self.reloj, dormir=lambda s: None)

    def ctx(self, juego=JUEGO):
        return nucleo.Contexto(self.raiz, juego)

    def plan(self, juego=JUEGO, solo=None):
        ctx = self.ctx(juego)
        plan, problemas = nucleo.construir_plan(ctx, ADAPTADORES, solo)
        return ctx, plan, problemas

    def ejecutar(self, juego=JUEGO, aprobar=None, solo=None):
        ctx, plan, problemas = self.plan(juego, solo)
        return nucleo.ejecutar(ctx, plan, problemas, aprobar if aprobar is not None else plan['huella'][:16], self.ent(), ADAPTADORES)

    def libro(self):
        return nucleo.Libro(self.raiz / 'publicacion' / 'libro.jsonl').entradas()

    def texto_libro(self):
        ruta = self.raiz / 'publicacion' / 'libro.jsonl'
        return ruta.read_text(encoding='utf-8') if ruta.exists() else ''

    def editar(self, rel, f):
        ruta = self.raiz / rel
        datos = json.loads(ruta.read_text(encoding='utf-8'))
        f(datos)
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding='utf-8')

    def politica(self, f):
        self.editar('publicacion/politica.json', f)

    def regenerar_sitio(self):
        gen.generar(self.raiz)

    def resultados(self, informe):
        return {l['accion']: l['resultado'] for l in informe}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='ggx-caso-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        shutil.copytree(PLANTILLA_PROYECTO, self.tmp / 'p')
        self.p = Proyecto(self.tmp / 'p')

    def nuevo_proyecto(self, nombre):
        shutil.copytree(PLANTILLA_PROYECTO, self.tmp / nombre)
        return Proyecto(self.tmp / nombre)


# ---------------------------------------------------------------------------------------------------------------------
# Textos
# ---------------------------------------------------------------------------------------------------------------------

class PruebasTexto(unittest.TestCase):
    def test_grafemas_no_cuenta_marcas_ni_uniones(self):
        self.assertEqual(tx.grafemas('hola'), 4)
        self.assertEqual(tx.grafemas('e\u0301'), 1)                       # e + acento combinante
        self.assertEqual(tx.grafemas('👨‍👩‍👧'), 1)                          # familia con uniones
        self.assertEqual(tx.grafemas('🇲🇽'), 1)                           # bandera = 2 indicadores regionales
        self.assertEqual(tx.grafemas('果冻'), 2)

    def test_facetas_usan_bytes_utf8_no_letras(self):
        t = '¡Mira 😀 esto! https://ejemplo.org/a?b=1. Fin'
        f = tx.facetas_enlaces(t)
        self.assertEqual(len(f), 1)
        i = f[0]['index']
        self.assertEqual(t.encode('utf-8')[i['byteStart']:i['byteEnd']].decode('utf-8'), 'https://ejemplo.org/a?b=1')
        self.assertEqual(f[0]['features'][0]['uri'], 'https://ejemplo.org/a?b=1')

    def test_componer_post_exige_enlace_ia_y_sin_marcas(self):
        spec = {'difusion': {'es': {'post_corto': 'Juega: {enlace} {ia}'}}}
        t, problemas = tx.componer_post(spec, 'es', 'https://x.org/es/', 'Hecho con IA.')
        self.assertEqual((t, problemas), ('Juega: https://x.org/es/ Hecho con IA.', []))
        _, problemas = tx.componer_post(spec, 'es', 'https://x.org/es/', '')
        self.assertEqual(problemas, [])                                    # sin IA declarada no hay línea que exigir
        spec['difusion']['es']['post_corto'] = 'Juega ya {otra}'
        _, problemas = tx.componer_post(spec, 'es', 'https://x.org/es/', 'Hecho con IA.')
        self.assertTrue(any('marcas sin resolver' in x for x in problemas) and any('enlace' in x for x in problemas) and any('IA' in x for x in problemas))
        _, problemas = tx.componer_post({'difusion': {}}, 'es', 'https://x.org/', '')
        self.assertTrue(any('falta difusion.es.post_corto' in x for x in problemas))

    def test_redactar_quita_secretos(self):
        self.assertEqual(red.redactar('error con SECRETO-abc en la URL', ['SECRETO-abc']), 'error con *** en la URL')
        self.assertEqual(red.redactar('abc', ['abc']), 'abc')              # secretos muy cortos no se tocan (evita destrozar el texto)


# ---------------------------------------------------------------------------------------------------------------------
# Plan, huella y aprobación
# ---------------------------------------------------------------------------------------------------------------------

class PruebasPlan(Base):
    def test_el_plan_ordena_sitio_primero_y_redes_despues(self):
        _, plan, problemas = self.p.plan()
        self.assertEqual(problemas, [])
        canales = [a['canal'] for a in plan['acciones']]
        self.assertEqual(canales[:2], ['sitio-propio', 'indexnow'])
        self.assertEqual(sorted(canales[2:]), sorted(['bluesky', 'mastodon', 'telegram-canal', 'discord-webhook', 'youtube-api', 'itch-pagina']))
        self.assertEqual(canales[-1], 'itch-pagina')                       # los portales van al final
        self.assertEqual(plan['tipo'], 'lanzamiento')

    def test_huella_estable_entre_procesos_y_cambia_con_el_contenido(self):
        _, plan1, _ = self.p.plan()
        _, plan2, _ = self.p.plan()
        self.assertEqual(plan1['huella'], plan2['huella'])
        salida = subprocess.run([sys.executable, '-I', str(self.p.raiz / 'fabrica.py'), 'huella', JUEGO], capture_output=True, text=True, env={'PYTHONHASHSEED': '7'})
        self.assertEqual(salida.stdout.strip(), plan1['huella'], salida.stderr)
        self.p.editar('juegos/%s/juego.json' % JUEGO, lambda s: s['difusion']['es'].update(post_corto=s['difusion']['es']['post_corto'] + ' Una coma, más.'))
        _, plan3, _ = self.p.plan()
        self.assertNotEqual(plan1['huella'], plan3['huella'])

    def test_huella_cambia_con_politica_y_con_solo(self):
        _, plan1, _ = self.p.plan()
        self.p.politica(lambda d: d['idioma'].update(bluesky='en'))
        _, plan2, _ = self.p.plan()
        self.assertNotEqual(plan1['huella'], plan2['huella'])
        _, plan3, _ = self.p.plan(solo={'bluesky'})
        self.assertEqual([a['canal'] for a in plan3['acciones']], ['bluesky'])
        self.assertNotEqual(plan2['huella'], plan3['huella'])

    def test_la_huella_no_depende_del_tipo(self):
        ctx, plan, _ = self.p.plan()
        self.assertEqual(plan['huella'], nucleo.huella_de(dict(plan, tipo='parche')))

    def test_cada_post_sale_en_el_idioma_del_canal_con_enlace_a_su_idioma(self):
        self.p.politica(lambda d: d['idioma'].update(bluesky='zh', mastodon='en'))
        _, plan, _ = self.p.plan()
        por = {a['canal']: a for a in plan['acciones']}
        self.assertIn(SITIO_URL + '/zh/juegos/%s/' % JUEGO, por['bluesky']['datos']['texto'])
        self.assertEqual(por['bluesky']['datos']['idioma'], 'zh')
        self.assertIn(SITIO_URL + '/en/juegos/%s/' % JUEGO, por['mastodon']['datos']['texto'])
        marca_ia = {'es': 'IA', 'en': 'AI', 'zh': 'AI'}
        for a in plan['acciones']:
            if a['tipo'] == 'post':
                self.assertIn(marca_ia[a['datos']['idioma']], a['datos']['texto'])                       # línea de transparencia

    def test_idioma_que_el_juego_no_tiene_es_un_problema_del_plan(self):
        self.p.politica(lambda d: d['idioma'].update(bluesky='fr'))
        _, plan, problemas = self.p.plan()
        self.assertTrue(any('bluesky' in x and 'fr' in x for x in problemas))

    def test_limites_de_texto_por_canal(self):
        largo = 'x' * 2000
        self.p.editar('juegos/%s/juego.json' % JUEGO, lambda s: s['difusion']['es'].update(post_corto='Hola {enlace} {ia} ' + largo))
        _, plan, problemas = self.p.plan()
        for canal in ('bluesky', 'mastodon', 'telegram-canal', 'discord-webhook'):
            self.assertTrue(any(x.startswith(canal) for x in problemas), canal)

    def test_canal_sin_adaptador_es_problema(self):
        self.p.politica(lambda d: d['canales'].append('poki'))
        _, _, problemas = self.p.plan()
        self.assertTrue(any('poki' in x and 'adaptador' in x for x in problemas))

    def test_solo_con_canal_inactivo_es_problema(self):
        self.p.politica(lambda d: d['canales'].remove('telegram-canal'))
        _, _, problemas = self.p.plan(solo={'telegram-canal'})
        self.assertTrue(any('--solo' in x for x in problemas))

    def test_un_parche_no_se_anuncia_en_redes_salvo_que_la_politica_lo_pida(self):
        informe, ok = self.p.ejecutar()
        self.assertTrue(ok, informe)
        pagina = self.p.raiz / 'salida' / JUEGO / 'index.html'
        pagina.write_text(pagina.read_text(encoding='utf-8') + '\n<!-- parche -->\n', encoding='utf-8')
        self.p.editar('juegos/%s/juego.json' % JUEGO, lambda s: s.update(version='1.5.0'))
        self.p.regenerar_sitio()
        ctx, plan, problemas = self.p.plan()
        self.assertEqual((ctx.tipo, problemas), ('parche', []))
        tipos = sorted(a['tipo'] for a in plan['acciones'])
        self.assertEqual(tipos, ['avisar', 'desplegar', 'empujar'])        # sitio, buscadores y portal sí; posts y video no
        self.p.politica(lambda d: d.update(avisar_parches=True))
        _, plan2, _ = self.p.plan()
        self.assertIn('post', [a['tipo'] for a in plan2['acciones']])

    def test_sitio_viejo_bloquea_el_plan(self):
        pagina = self.p.raiz / 'salida' / JUEGO / 'index.html'
        pagina.write_text(pagina.read_text(encoding='utf-8') + '\n<!-- cambió el juego -->\n', encoding='utf-8')
        _, _, problemas = self.p.plan(solo={'sitio-propio'})
        self.assertTrue(any('versión vieja' in x for x in problemas), problemas)

    def test_sitio_tocado_a_mano_bloquea_el_plan(self):
        (self.p.raiz / 'dist' / 'sitio' / 'index.html').write_text('<h1>otra cosa</h1>', encoding='utf-8')
        _, _, problemas = self.p.plan(solo={'sitio-propio'})
        self.assertTrue(any('cambió después de generarse' in x for x in problemas), problemas)

    def test_juego_fuera_de_la_lista_del_sitio_no_se_publica(self):
        _, _, problemas = self.p.plan('torre-gelatina', solo={'sitio-propio'})
        self.assertTrue(any('no está en sitio.json' in x for x in problemas), problemas)


class PruebasAprobacion(Base):
    def test_sin_aprobacion_o_con_una_distinta_no_sale_nada(self):
        for mala in (None, '', 'abc', 'zzzzzzzzzzzzzzzz', '0' * 16, 'a' * 64):
            with self.assertRaises(nucleo.ErrorPublicacion, msg=repr(mala)):
                self.p.ejecutar(aprobar=mala if mala is not None else '')
        self.assertEqual(self.p.red.llamadas, [])
        self.assertEqual(self.p.cmd.llamadas, [])
        self.assertEqual(self.p.libro(), [])

    def test_aprobacion_corta_no_vale(self):
        _, plan, _ = self.p.plan()
        self.assertFalse(nucleo.aprobada(plan, plan['huella'][:11]))
        self.assertTrue(nucleo.aprobada(plan, plan['huella'][:12]))
        self.assertTrue(nucleo.aprobada(plan, plan['huella'].upper()))
        self.assertTrue(nucleo.aprobada(plan, '  ' + plan['huella'] + ' '))

    def test_si_algo_cambia_despues_de_aprobar_se_detiene(self):
        _, plan, _ = self.p.plan()
        aprobada = plan['huella'][:16]
        self.p.politica(lambda d: d['idioma'].update(bluesky='en'))        # alguien toca la política entre la aprobación y la ejecución
        with self.assertRaises(nucleo.ErrorPublicacion) as e:
            self.p.ejecutar(aprobar=aprobada)
        self.assertIn('no coincide', str(e.exception))
        self.assertEqual(self.p.red.llamadas, [])


# ---------------------------------------------------------------------------------------------------------------------
# Compuertas
# ---------------------------------------------------------------------------------------------------------------------

class PruebasCompuertas(Base):
    def razones(self, juego=JUEGO):
        ctx, plan, problemas = self.p.plan(juego)
        return nucleo.compuertas(ctx, plan, problemas, self.p.reloj())

    def test_en_orden_no_hay_razones(self):
        self.assertEqual(self.razones(), [])

    def test_sitio_de_ejemplo_o_sin_contacto_no_se_publica(self):
        self.p.editar('publicacion/sitio.json', lambda d: d.update(url_base='https://CAMBIA-ESTE-NOMBRE.pages.dev', proyecto='CAMBIA-ESTE-NOMBRE', contacto=''))
        self.p.regenerar_sitio()
        r = ' | '.join(self.razones())
        self.assertIn('proyecto', r)
        self.assertIn('contacto', r)
        self.assertIn('url_base', r)

    def test_url_que_no_es_https_no_se_publica(self):
        self.p.editar('publicacion/sitio.json', lambda d: d.update(url_base='http://taller-gelatina.pages.dev'))
        self.assertTrue(any('url_base' in x for x in self.razones()))

    def test_ficha_con_pendiente_no_se_publica(self):
        self.p.editar('juegos/%s/juego.json' % JUEGO, lambda s: s['ficha']['es'].update(controles='PENDIENTE'))
        self.assertTrue(any('PENDIENTE' in x for x in self.razones()))

    def test_riesgo_de_clon_alto_cierra_los_portales_pero_no_el_sitio(self):
        self.p.editar('publicacion/sitio.json', lambda d: d['juegos'].append('torre-gelatina'))
        self.p.regenerar_sitio()
        self.p.editar('juegos/torre-gelatina/juego.json', lambda s: s.update(publicacion={'itch': {'destino': 'taller/torre', 'canal': 'html5'}}))
        r = ' | '.join(self.razones('torre-gelatina'))
        self.assertIn('portales', r)
        self.assertIn('Stack', r)
        ctx, plan, problemas = self.p.plan('torre-gelatina', solo={'sitio-propio', 'indexnow', 'bluesky'})
        self.assertEqual(nucleo.compuertas(ctx, plan, problemas, self.p.reloj()), [])

    def test_redes_sin_sitio_publicado_no_salen(self):
        self.p.politica(lambda d: d['canales'].remove('sitio-propio'))
        self.assertTrue(any('todavía no está publicado' in x for x in self.razones()))

    def test_ritmo_entre_lanzamientos(self):
        self.p.editar('publicacion/sitio.json', lambda d: d['juegos'].append('torre-gelatina'))
        informe, ok = self.p.ejecutar()
        self.assertTrue(ok, informe)
        self.p.regenerar_sitio()
        ctx, plan, problemas = self.p.plan('torre-gelatina', solo={'sitio-propio'})
        self.assertEqual(problemas, [])
        r = nucleo.compuertas(ctx, plan, problemas, self.p.reloj())
        self.assertTrue(any('ritmo' in x and '14 días' in x for x in r), r)
        self.p.reloj.avanzar(days=15)
        self.assertEqual(nucleo.compuertas(ctx, plan, problemas, self.p.reloj()), [])

    def test_ejecutar_se_niega_si_hay_razones(self):
        self.p.editar('publicacion/sitio.json', lambda d: d.update(contacto=''))
        self.p.regenerar_sitio()
        with self.assertRaises(nucleo.ErrorPublicacion) as e:
            self.p.ejecutar()
        self.assertIn('contacto', str(e.exception))
        self.assertEqual(self.p.red.llamadas, [])


# ---------------------------------------------------------------------------------------------------------------------
# Cada servicio: la forma exacta de lo que se envía
# ---------------------------------------------------------------------------------------------------------------------

class PruebasServicios(Base):
    def correr(self):
        informe, ok = self.p.ejecutar()
        self.assertTrue(ok, json.dumps(informe, ensure_ascii=False, indent=1))
        return self.p.resultados(informe)

    def test_todo_el_plan_sale_en_orden(self):
        res = self.correr()
        self.assertTrue(all(v == 'ok' for v in res.values()), res)
        orden = [e['canal'] for e in self.p.libro()]
        self.assertEqual(orden[0], 'sitio-propio')
        self.assertEqual(orden[1], 'indexnow')
        self.assertEqual(orden[-1], 'itch-pagina')
        self.assertTrue(all(e['lanzamiento'] for e in self.p.libro()))

    def test_cloudflare_pages(self):
        self.correr()
        (c,) = self.p.cmd.llamadas[:1]
        self.assertEqual(c['argv'][:6], ['npx', '--yes', 'wrangler@4', 'pages', 'deploy', str(self.p.raiz / 'dist' / 'sitio')])
        self.assertIn('--project-name=taller-gelatina', c['argv'])
        self.assertIn('--branch=main', c['argv'])
        self.assertEqual(c['env']['CLOUDFLARE_API_TOKEN'], SECRETOS['CLOUDFLARE_API_TOKEN'])
        self.assertEqual(c['env']['CLOUDFLARE_ACCOUNT_ID'], SECRETOS['CLOUDFLARE_ACCOUNT_ID'])
        self.assertEqual(c['env']['WRANGLER_SEND_METRICS'], 'false')
        self.assertTrue(self.p.red.a('GET', SITIO_URL + '/es/juegos/%s/' % JUEGO))      # comprueba que el sitio responde

    def test_si_wrangler_falla_no_sale_nada_mas(self):
        self.p.cmd.codigo = 1
        informe, ok = self.p.ejecutar()
        self.assertFalse(ok)
        self.assertEqual([l['canal'] for l in informe], ['sitio-propio'])
        self.assertEqual(self.p.red.llamadas, [])

    def test_el_error_de_wrangler_se_anota_sin_colores_de_terminal_y_se_puede_reintentar(self):
        self.p.cmd = lambda argv, cwd=None, env=None, tiempo=900: (1, '', '\x1b[31m✘ \x1b[41;31m[ERROR]\x1b[0m Invalid account ID "***"')
        informe, ok = self.p.ejecutar()
        self.assertFalse(ok)
        self.assertNotIn('\x1b', informe[0]['detalle'])
        self.assertIn('Invalid account ID', informe[0]['detalle'])
        self.assertNotIn('\x1b', self.p.texto_libro().replace('\\u001b', 'ESC'))
        self.assertEqual(informe[0]['resultado'], 'error')          # «error», no «incierto»: con la clave corregida se reintenta el mismo plan
        self.p.cmd = Cmd()
        informe, ok = self.p.ejecutar()
        self.assertTrue(ok, informe)

    def test_un_account_id_mal_pegado_se_explica_sin_mostrar_el_valor_y_ni_se_llama_a_wrangler(self):
        secreto = "94g7526cjs@privaterelay.appleid.com's Account"
        self.p.env['CLOUDFLARE_ACCOUNT_ID'] = secreto
        informe, ok = self.p.ejecutar()
        self.assertFalse(ok)
        self.assertEqual(informe[0]['resultado'], 'error')
        detalle = informe[0]['detalle']
        self.assertIn('CLOUDFLARE_ACCOUNT_ID no tiene la forma de un Account ID', detalle)
        self.assertIn('tiene %d caracteres' % len(secreto), detalle)
        for signo in ("'@'", "' '", '"\'"', "'.'"):
            self.assertIn(signo, detalle)
        for trozo in ('94g7526cjs', 'privaterelay', 'appleid'):
            self.assertNotIn(trozo, detalle)
            self.assertNotIn(trozo, self.p.texto_libro())
        self.assertEqual(self.p.cmd.llamadas, [])

    def test_las_peticiones_se_identifican_como_bot_y_respetan_un_agente_explicito(self):
        from unittest import mock

        class Fake:
            status = 200
            headers = {}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b''
        vistas = []

        def falso(req, timeout=None):
            vistas.append(req)
            return Fake()
        with mock.patch('urllib.request.urlopen', falso):
            red.solicitar('GET', 'https://ejemplo.test/')
            red.solicitar('GET', 'https://ejemplo.test/', {'User-Agent': 'otro/2'})
        self.assertIn('bot declarado', vistas[0].get_header('User-agent'))
        self.assertNotIn('Python-urllib', vistas[0].get_header('User-agent'))
        self.assertEqual(vistas[1].get_header('User-agent'), 'otro/2')

    def test_un_token_con_varias_lineas_se_explica_con_cuentas_y_sin_mostrar_nada_del_token(self):
        secreto = 'abcDEF123-token-parte-uno\n\ncurl https://api.cloudflare.com/ -H "Authorization: Bearer xyz"'
        self.p.env['CLOUDFLARE_API_TOKEN'] = secreto
        informe, ok = self.p.ejecutar()
        self.assertFalse(ok)
        detalle = informe[0]['detalle']
        self.assertIn('CLOUDFLARE_API_TOKEN no tiene la forma de un token', detalle)
        self.assertIn('tiene %d caracteres' % len(secreto.strip()), detalle)
        self.assertRegex(detalle, r'[1-9]\d* espacios o saltos de línea')
        for trozo in ('abcDEF', 'token-parte', 'curl', 'Bearer'):
            self.assertNotIn(trozo, detalle)
            self.assertNotIn(trozo, self.p.texto_libro())
        self.assertEqual(self.p.cmd.llamadas, [])

    def test_un_account_id_con_espacios_o_salto_de_linea_al_final_se_limpia(self):
        self.p.env['CLOUDFLARE_ACCOUNT_ID'] = '  ' + SECRETOS['CLOUDFLARE_ACCOUNT_ID'] + '\n'
        self.p.env['CLOUDFLARE_API_TOKEN'] = SECRETOS['CLOUDFLARE_API_TOKEN'] + ' \n'
        informe, ok = self.p.ejecutar()
        self.assertTrue(ok, informe)
        env = self.p.cmd.llamadas[0]['env']
        self.assertEqual((env['CLOUDFLARE_ACCOUNT_ID'], env['CLOUDFLARE_API_TOKEN']), (SECRETOS['CLOUDFLARE_ACCOUNT_ID'], SECRETOS['CLOUDFLARE_API_TOKEN']))

    def test_si_el_sitio_no_responde_no_se_anuncia(self):
        self.p.red.al('GET', SITIO_URL + '/', resp(404))
        informe, ok = self.p.ejecutar()
        self.assertFalse(ok)
        self.assertEqual([l['canal'] for l in informe], ['sitio-propio'])
        self.assertIn('no respondió 200', informe[0]['detalle'])
        self.assertIn('última respuesta: HTTP 404', informe[0]['detalle'])
        self.assertEqual(self.p.red.a('POST', 'https://bsky.social'), [])

    def test_indexnow(self):
        self.correr()
        (c,) = self.p.red.a('POST', 'https://api.indexnow.org/indexnow')
        cuerpo = json.loads(c['cuerpo'])
        clave = (self.p.raiz / 'dist' / 'sitio').glob('*.txt')
        claves = [f.stem for f in clave if f.stem not in ('robots',)]
        self.assertEqual(cuerpo['host'], 'taller-gelatina.pages.dev')
        self.assertEqual(cuerpo['key'], claves[0])
        self.assertEqual(cuerpo['keyLocation'], '%s/%s.txt' % (SITIO_URL, claves[0]))
        self.assertIn(SITIO_URL + '/en/juegos/%s/' % JUEGO, cuerpo['urlList'])
        self.assertTrue(all(u.startswith(SITIO_URL + '/') for u in cuerpo['urlList']))
        self.assertEqual((self.p.raiz / 'dist' / 'sitio' / (claves[0] + '.txt')).read_text().strip(), claves[0])

    def test_indexnow_errores_conocidos(self):
        for i, (estado, frase) in enumerate(((403, 'clave no válida'), (422, 'otro dominio'), (429, 'se detiene'))):
            p = self.nuevo_proyecto('indexnow%d' % i)
            p.red.al('POST', 'https://api.indexnow.org/indexnow', resp(estado))
            informe, ok = p.ejecutar(solo={'sitio-propio', 'indexnow'})
            self.assertFalse(ok)
            self.assertIn(frase, [l for l in informe if l['canal'] == 'indexnow'][0]['detalle'])

    def test_bluesky(self):
        self.correr()
        (sesion,) = self.p.red.a('POST', 'https://bsky.social/xrpc/com.atproto.server.createSession')
        self.assertEqual(json.loads(sesion['cuerpo']), {'identifier': 'taller.bsky.social', 'password': SECRETOS['BSKY_APP_PASSWORD']})
        (blob,) = self.p.red.a('POST', 'https://bsky.social/xrpc/com.atproto.repo.uploadBlob')
        self.assertEqual(blob['cab']['Authorization'], 'Bearer jwt-uno')
        self.assertEqual(blob['cab']['Content-Type'], 'image/jpeg')
        self.assertEqual(blob['cuerpo'][:2], b'\xff\xd8')
        self.assertLessEqual(len(blob['cuerpo']), 900000)
        (rec,) = self.p.red.a('POST', 'https://bsky.social/xrpc/com.atproto.repo.createRecord')
        cuerpo = json.loads(rec['cuerpo'])
        r = cuerpo['record']
        self.assertEqual((cuerpo['repo'], cuerpo['collection'], r['$type']), ('did:plc:abc123', 'app.bsky.feed.post', 'app.bsky.feed.post'))
        self.assertEqual(r['langs'], ['es'])
        self.assertLessEqual(tx.grafemas(r['text']), 300)
        faceta = r['facets'][0]['index']
        self.assertEqual(r['text'].encode('utf-8')[faceta['byteStart']:faceta['byteEnd']].decode(), SITIO_URL + '/es/juegos/%s/' % JUEGO)
        self.assertEqual(r['embed']['$type'], 'app.bsky.embed.images')
        self.assertTrue(r['embed']['images'][0]['alt'])
        self.assertEqual(r['embed']['images'][0]['image']['ref']['$link'], 'bafkreiabc')
        self.assertTrue(r['createdAt'].endswith('Z'))
        entrada = [e for e in self.p.libro() if e['canal'] == 'bluesky'][0]
        self.assertEqual(entrada['url'], 'https://bsky.app/profile/did:plc:abc123/post/3kpost')

    def test_bluesky_login_fallido_no_publica_ni_queda_en_duda(self):
        self.p.red.al('POST', 'https://bsky.social/xrpc/com.atproto.server.createSession', resp(401, {'error': 'AuthenticationRequired'}))
        informe, ok = self.p.ejecutar()
        bsky = [l for l in informe if l['canal'] == 'bluesky'][0]
        self.assertEqual(bsky['resultado'], 'error')
        self.assertEqual(self.p.red.a('POST', 'https://bsky.social/xrpc/com.atproto.repo.createRecord'), [])
        self.assertTrue(all(l['resultado'] == 'ok' for l in informe if l['canal'] != 'bluesky'))   # un canal caído no frena a los demás

    def test_bluesky_con_claves_mal_pegadas_explica_la_forma_sin_mostrar_nada_de_las_claves(self):
        from publicacion.adaptadores import bluesky
        casos = [
            ({'BSKY_IDENTIFIER': 'dueno@correo.mx', 'BSKY_APP_PASSWORD': 'abcd-efgh-ijkl-mnop'}, 'parece un correo'),
            ({'BSKY_IDENTIFIER': 'taller', 'BSKY_APP_PASSWORD': 'abcd-efgh-ijkl-mnop'}, 'dominio completo'),
            ({'BSKY_IDENTIFIER': 'taller.bsky.social', 'BSKY_APP_PASSWORD': 'LaContrasenaNormal9'}, 'mide 19 caracteres'),
            ({'BSKY_IDENTIFIER': 'taller.bsky.social', 'BSKY_APP_PASSWORD': 'abcd efgh ijkl mnop'}, 'espacios o saltos de línea'),
        ]
        for env, esperado in casos:
            with self.subTest(esperado=esperado):
                ent = nucleo.Entorno(env=env, http=lambda *a, **k: resp(401, {'error': 'AuthenticationRequired', 'message': 'Invalid identifier or password'}))
                with self.assertRaises(nucleo.ErrorPublicacion) as cm:
                    bluesky._sesion(ent, 'https://bsky.social')
                m = str(cm.exception)
                self.assertIn('HTTP 401, AuthenticationRequired', m)
                self.assertIn(esperado, m)
                for secreto in env.values():
                    self.assertNotIn(secreto, m)

    def test_bluesky_quita_espacios_y_arroba_al_borde_antes_de_iniciar_sesion(self):
        from publicacion.adaptadores import bluesky
        vistos = []

        def http(metodo, url, cab=None, cuerpo=None):
            vistos.append(json.loads(cuerpo))
            return resp(200, {'accessJwt': 'j', 'did': 'did:plc:x'})
        ent = nucleo.Entorno(env={'BSKY_IDENTIFIER': '  @taller.bsky.social\n', 'BSKY_APP_PASSWORD': 'abcd-efgh-ijkl-mnop\n'}, http=http)
        self.assertEqual(bluesky._sesion(ent, 'https://bsky.social'), ('j', 'did:plc:x'))
        self.assertEqual(vistos, [{'identifier': 'taller.bsky.social', 'password': 'abcd-efgh-ijkl-mnop'}])

    def test_mastodon(self):
        self.p.red.al('POST', 'https://mast.ejemplo/api/v2/media', resp(202, {'id': '555'}))
        estados = iter([resp(206), resp(206), resp(200, {'id': '555'})])
        self.p.red.al('GET', 'https://mast.ejemplo/api/v1/media/555', lambda *a: next(estados))
        self.correr()
        (m,) = self.p.red.a('POST', 'https://mast.ejemplo/api/v2/media')
        self.assertEqual(m['cab']['Authorization'], 'Bearer ' + SECRETOS['MASTODON_TOKEN'])
        self.assertTrue(m['cab']['Content-Type'].startswith('multipart/form-data; boundary='))
        self.assertIn(b'name="description"', m['cuerpo'])
        self.assertIn(b'\xff\xd8', m['cuerpo'])
        self.assertEqual(len(self.p.red.a('GET', 'https://mast.ejemplo/api/v1/media/555')), 3)     # esperó hasta el 200
        (s,) = self.p.red.a('POST', 'https://mast.ejemplo/api/v1/statuses')
        cuerpo = json.loads(s['cuerpo'])
        self.assertEqual((cuerpo['visibility'], cuerpo['language'], cuerpo['media_ids']), ('public', 'es', ['555']))
        self.assertIn(SITIO_URL, cuerpo['status'])
        self.assertLessEqual(len(cuerpo['status']), 450)
        self.assertEqual(len(s['cab']['Idempotency-Key']), 32)

    def test_mastodon_idempotency_key_estable(self):
        self.correr()
        clave1 = self.p.red.a('POST', 'https://mast.ejemplo/api/v1/statuses')[0]['cab']['Idempotency-Key']
        otra = self.nuevo_proyecto('otra')                                  # mismo envío desde cero (p. ej. otro trabajo de CI)
        otra.ejecutar(solo={'sitio-propio', 'mastodon'})
        self.assertEqual(otra.red.a('POST', 'https://mast.ejemplo/api/v1/statuses')[0]['cab']['Idempotency-Key'], clave1)

    def test_mastodon_servidor_sin_https_se_rechaza(self):
        self.p.env['MASTODON_INSTANCE'] = 'http://mast.ejemplo'
        informe, ok = self.p.ejecutar()
        self.assertEqual([l for l in informe if l['canal'] == 'mastodon'][0]['resultado'], 'error')
        self.assertEqual(self.p.red.a('POST', 'http://mast.ejemplo'), [])

    def test_telegram(self):
        self.correr()
        (c,) = self.p.red.a('POST', 'https://api.telegram.org/bot')
        self.assertEqual(c['url'], 'https://api.telegram.org/bot123456:TELE-SECRETO-4/sendMessage')
        cuerpo = json.loads(c['cuerpo'])
        self.assertEqual(cuerpo['chat_id'], '@canal_gelatina')
        self.assertIn(SITIO_URL, cuerpo['text'])

    def test_discord(self):
        self.correr()
        (c,) = self.p.red.a('POST', 'https://discord.com/api/webhooks/123456789/')
        self.assertTrue(c['url'].endswith('/WEBHOOK-SECRETO-5?wait=true'))
        cuerpo = json.loads(c['cuerpo'])
        self.assertEqual(cuerpo['allowed_mentions'], {'parse': []})        # un texto nunca puede mencionar a todo el servidor
        self.assertEqual(cuerpo['username'], 'Taller Gelatina')
        self.assertLessEqual(len(cuerpo['content']), 2000)

    def test_discord_rechaza_direcciones_que_no_son_de_webhook(self):
        self.p.env['DISCORD_WEBHOOK_URL'] = 'https://malo.ejemplo/api/webhooks/1/abc'
        informe, _ = self.p.ejecutar()
        self.assertEqual([l for l in informe if l['canal'] == 'discord-webhook'][0]['resultado'], 'error')
        self.assertEqual(self.p.red.a('POST', 'https://malo.ejemplo'), [])

    def test_youtube(self):
        self.correr()
        (tok,) = self.p.red.a('POST', 'https://oauth2.googleapis.com/token')
        for k, v in (('grant_type=refresh_token', 1), ('refresh_token=yt-refresco-SECRETO-7', 1), ('client_id=ytid', 1)):
            self.assertIn(k, tok['cuerpo'].decode())
        (ini,) = self.p.red.a('POST', 'https://www.googleapis.com/upload/youtube/v3/videos')
        self.assertIn('uploadType=resumable', ini['url'])
        self.assertIn('part=snippet,status', ini['url'])
        self.assertEqual(ini['cab']['Authorization'], 'Bearer ya29.token')
        self.assertEqual(ini['cab']['X-Upload-Content-Type'], 'video/mp4')
        meta = json.loads(ini['cuerpo'])
        self.assertEqual(meta['status']['privacyStatus'], 'public')
        self.assertIs(meta['status']['selfDeclaredMadeForKids'], False)
        self.assertNotIn('containsSyntheticMedia', meta['status'])          # solo si la política lo declara
        self.assertIn(SITIO_URL + '/es/juegos/%s/' % JUEGO, meta['snippet']['description'])
        self.assertIn('IA', meta['snippet']['description'])
        self.assertEqual(meta['snippet']['categoryId'], '20')
        (sube,) = self.p.red.a('PUT', 'https://subida.ejemplo/sesion1')
        self.assertEqual(int(sube['cab']['Content-Length']), len(sube['cuerpo']))
        self.assertEqual(sube['cuerpo'], (self.p.raiz / 'salida' / JUEGO / 'medios' / 'clip-vertical.mp4').read_bytes())
        e = [e for e in self.p.libro() if e['canal'] == 'youtube-api'][0]
        self.assertEqual(e['url'], 'https://www.youtube.com/watch?v=vid123')

    def test_youtube_con_contenido_sintetico_declarado(self):
        self.p.politica(lambda d: d['youtube'].update(contenido_sintetico=True, privacidad='unlisted'))
        self.correr()
        meta = json.loads(self.p.red.a('POST', 'https://www.googleapis.com/upload/youtube/v3/videos')[0]['cuerpo'])
        self.assertIs(meta['status']['containsSyntheticMedia'], True)
        self.assertEqual(meta['status']['privacyStatus'], 'unlisted')

    def test_youtube_token_vencido_explica_que_hacer(self):
        self.p.red.al('POST', 'https://oauth2.googleapis.com/token', resp(400, {'error': 'invalid_grant'}))
        informe, _ = self.p.ejecutar()
        y = [l for l in informe if l['canal'] == 'youtube-api'][0]
        self.assertEqual(y['resultado'], 'error')
        self.assertIn('7 días', y['detalle'])
        self.assertEqual(self.p.red.a('POST', 'https://www.googleapis.com/upload'), [])

    def test_youtube_clip_cambiado_despues_de_aprobar(self):
        ctx, plan, problemas = self.p.plan()
        clip = self.p.raiz / 'salida' / JUEGO / 'medios' / 'clip-vertical.mp4'
        clip.write_bytes(clip.read_bytes() + b'x')
        informe, ok = nucleo.ejecutar(ctx, plan, problemas, plan['huella'][:16], self.p.ent(), ADAPTADORES)
        y = [l for l in informe if l['canal'] == 'youtube-api'][0]
        self.assertEqual(y['resultado'], 'error')
        self.assertIn('cambió después de aprobar', y['detalle'])
        self.assertEqual(self.p.red.a('PUT', 'https://subida.ejemplo'), [])

    def test_itch_con_butler(self):
        self.correr()
        butler = [c for c in self.p.cmd.llamadas if c['argv'][0] == 'butler']
        self.assertEqual(len(butler), 1)
        a = butler[0]['argv']
        self.assertEqual(a[:2], ['butler', 'push'])
        self.assertTrue(a[2].endswith('guerreros-gelatina-web.zip'))
        self.assertEqual(a[3:], ['taller/guerreros-gelatina:html5', '--userversion', '1.4.0'])
        self.assertEqual(butler[0]['env']['BUTLER_API_KEY'], SECRETOS['BUTLER_API_KEY'])

    def test_itch_sin_destino_es_problema_del_plan(self):
        self.p.editar('juegos/%s/juego.json' % JUEGO, lambda s: s.pop('publicacion'))
        _, _, problemas = self.p.plan()
        self.assertTrue(any('itch-pagina' in x and 'destino' in x for x in problemas))

    def test_itch_zip_cambiado_despues_de_aprobar(self):
        ctx, plan, problemas = self.p.plan()
        z = self.p.raiz / 'salida' / JUEGO / ('%s-web.zip' % JUEGO)
        z.write_bytes(z.read_bytes() + b'x')
        informe, ok = nucleo.ejecutar(ctx, plan, problemas, plan['huella'][:16], self.p.ent(), ADAPTADORES)
        i = [l for l in informe if l['canal'] == 'itch-pagina'][0]
        self.assertEqual(i['resultado'], 'error')
        self.assertFalse([c for c in self.p.cmd.llamadas if c['argv'][0] == 'butler'])

    def test_imagen_para_redes_es_jpeg_liviano(self):
        datos, mime = img.preparar_imagen(self.p.raiz / 'salida' / JUEGO / 'medios' / 'portada.png')
        self.assertEqual((mime, datos[:2]), ('image/jpeg', b'\xff\xd8'))
        self.assertLessEqual(len(datos), 900000)
        with self.assertRaises(nucleo.ErrorPublicacion):
            img.preparar_imagen(self.p.raiz / 'salida' / JUEGO / 'medios' / 'portada.png', max_bytes=500)


# ---------------------------------------------------------------------------------------------------------------------
# Libro, repeticiones, dudas, ritmo y secretos
# ---------------------------------------------------------------------------------------------------------------------

class PruebasLibroYRitmo(Base):
    def test_repetir_la_misma_ejecucion_no_duplica_nada(self):
        informe, ok = self.p.ejecutar()
        self.assertTrue(ok)
        n_red, n_cmd, n_libro = len(self.p.red.llamadas), len(self.p.cmd.llamadas), len(self.p.libro())
        informe, ok = self.p.ejecutar()
        self.assertTrue(ok)
        self.assertTrue(all(l['resultado'] == 'ya hecho' for l in informe), informe)
        self.assertEqual((len(self.p.red.llamadas), len(self.p.cmd.llamadas), len(self.p.libro())), (n_red, n_cmd, n_libro))

    def test_repetir_despues_de_un_fallo_solo_hace_lo_que_falto(self):
        self.p.red.al('POST', 'https://api.telegram.org/bot', resp(400, {'ok': False, 'description': 'chat not found'}))
        informe, ok = self.p.ejecutar()
        self.assertFalse(ok)
        self.p.red = Red.todo_bien()
        antes = self.p.ctx().tipo
        self.assertEqual(antes, 'sin-cambios')                              # el sitio ya salió con esta versión
        informe, ok = self.p.ejecutar()                                     # misma aprobación: la huella no cambió por haber ejecutado a medias
        self.assertTrue(ok, informe)
        res = self.p.resultados(informe)
        self.assertEqual(res[[k for k in res if 'telegram' in k][0]], 'ok')
        self.assertTrue(all(v == 'ya hecho' for k, v in res.items() if 'telegram' not in k), res)
        self.assertEqual(self.p.red.a('POST', 'https://bsky.social/xrpc/com.atproto.repo.createRecord'), [])

    def test_lo_dudoso_no_se_repite_solo(self):
        self.p.red.al('POST', 'https://bsky.social/xrpc/com.atproto.repo.createRecord', red.ErrorRed('timeout'))
        informe, ok = self.p.ejecutar()
        b = [l for l in informe if l['canal'] == 'bluesky'][0]
        self.assertEqual(b['resultado'], 'incierto')
        self.assertFalse(ok)
        self.p.red = Red.todo_bien()
        informe, ok = self.p.ejecutar()
        b = [l for l in informe if l['canal'] == 'bluesky'][0]
        self.assertEqual(b['resultado'], 'detenido')
        self.assertIn('resolver', b['detalle'])
        self.assertEqual(self.p.red.a('POST', 'https://bsky.social/xrpc/com.atproto.repo.createRecord'), [])
        self.assertFalse(ok)

    def test_resolver_salio_lo_da_por_hecho_y_no_salio_permite_reintentar(self):
        self.p.red.al('POST', 'https://bsky.social/xrpc/com.atproto.repo.createRecord', red.ErrorRed('timeout'))
        self.p.ejecutar()
        accion = [e['accion'] for e in self.p.libro() if e['resultado'] == 'incierto'][0]
        libro = nucleo.Libro(self.p.raiz / 'publicacion' / 'libro.jsonl')
        nucleo.resolver(libro, accion, False, self.p.reloj())
        self.assertFalse(libro.hecho(accion))
        self.p.red = Red.todo_bien()
        informe, ok = self.p.ejecutar()
        self.assertTrue(ok, informe)
        self.assertEqual(len(self.p.red.a('POST', 'https://bsky.social/xrpc/com.atproto.repo.createRecord')), 1)
        with self.assertRaises(nucleo.ErrorPublicacion):                   # ya no hay nada dudoso que resolver
            nucleo.resolver(libro, accion, True, self.p.reloj())

    def test_resolver_salio(self):
        self.p.red.al('POST', 'https://bsky.social/xrpc/com.atproto.repo.createRecord', resp(503))
        self.p.ejecutar()
        accion = [e['accion'] for e in self.p.libro() if e['resultado'] == 'incierto'][0]
        libro = nucleo.Libro(self.p.raiz / 'publicacion' / 'libro.jsonl')
        nucleo.resolver(libro, accion, True, self.p.reloj())
        self.assertTrue(libro.hecho(accion))
        self.p.red = Red.todo_bien()
        informe, ok = self.p.ejecutar()
        self.assertTrue(ok, informe)
        self.assertEqual(self.p.red.a('POST', 'https://bsky.social/xrpc/com.atproto.repo.createRecord'), [])

    def test_ritmo_maximo_por_dia_y_separacion(self):
        self.p.politica(lambda d: (d.update(canales=['sitio-propio', 'bluesky']), d['ritmo'].update(min_dias_entre_lanzamientos=0),
                                   d['ritmo']['canales']['bluesky'].update(max_por_dia=1, min_horas_entre=0)))
        self.p.editar('publicacion/sitio.json', lambda d: d['juegos'].append('torre-gelatina'))
        self.p.regenerar_sitio()
        informe, ok = self.p.ejecutar()
        self.assertTrue(ok, informe)
        informe, ok = self.p.ejecutar('torre-gelatina')
        b = [l for l in informe if l['canal'] == 'bluesky'][0]
        self.assertEqual(b['resultado'], 'omitido')
        self.assertIn('máximo 1', b['detalle'])
        self.p.reloj.avanzar(hours=25)
        informe, ok = self.p.ejecutar('torre-gelatina')
        self.assertEqual([l for l in informe if l['canal'] == 'bluesky'][0]['resultado'], 'ok')

    def test_ritmo_horas_entre_publicaciones(self):
        self.p.politica(lambda d: (d.update(canales=['sitio-propio', 'bluesky']), d['ritmo'].update(min_dias_entre_lanzamientos=0),
                                   d['ritmo']['canales']['bluesky'].update(max_por_dia=5, min_horas_entre=6)))
        self.p.editar('publicacion/sitio.json', lambda d: d['juegos'].append('torre-gelatina'))
        self.p.regenerar_sitio()
        self.p.ejecutar()
        informe, _ = self.p.ejecutar('torre-gelatina')
        self.assertEqual([l for l in informe if l['canal'] == 'bluesky'][0]['resultado'], 'omitido')
        self.p.reloj.avanzar(hours=7)
        informe, _ = self.p.ejecutar('torre-gelatina')
        self.assertEqual([l for l in informe if l['canal'] == 'bluesky'][0]['resultado'], 'ok')

    def test_lo_omitido_por_ritmo_se_intenta_otra_vez_despues(self):
        self.p.politica(lambda d: (d.update(canales=['sitio-propio', 'telegram-canal']), d['ritmo'].update(min_dias_entre_lanzamientos=0),
                                   d['ritmo']['canales']['telegram-canal'].update(max_por_dia=1, min_horas_entre=0)))
        self.p.editar('publicacion/sitio.json', lambda d: d['juegos'].append('torre-gelatina'))
        self.p.regenerar_sitio()
        self.p.ejecutar()
        self.p.ejecutar('torre-gelatina')
        self.p.reloj.avanzar(days=2)
        informe, ok = self.p.ejecutar('torre-gelatina')
        res = self.p.resultados(informe)
        self.assertEqual(res['torre-gelatina:1.1.0:telegram:post'], 'ok')

    def test_faltan_secretos_de_un_canal_no_frena_a_los_otros(self):
        del self.p.env['TELEGRAM_BOT_TOKEN']
        informe, ok = self.p.ejecutar()
        self.assertFalse(ok)
        t = [l for l in informe if l['canal'] == 'telegram-canal'][0]
        self.assertEqual(t['resultado'], 'error')
        self.assertIn('TELEGRAM_BOT_TOKEN', t['detalle'])
        self.assertEqual(self.p.red.a('POST', 'https://api.telegram.org'), [])
        self.assertTrue(all(l['resultado'] == 'ok' for l in informe if l['canal'] != 'telegram-canal'))

    def test_faltan_secretos_del_sitio_no_sale_nada(self):
        del self.p.env['CLOUDFLARE_API_TOKEN']
        informe, ok = self.p.ejecutar()
        self.assertFalse(ok)
        self.assertEqual([l['canal'] for l in informe], ['sitio-propio'])
        self.assertEqual(self.p.red.llamadas, [])

    def test_las_claves_nunca_llegan_al_libro_ni_al_informe(self):
        # un servicio que repite la clave en su mensaje de error: debe quedar tachada
        self.p.red.al('POST', 'https://oauth2.googleapis.com/token', resp(500, {'error': 'falló con yt-refresco-SECRETO-7'}))
        self.p.red.al('POST', 'https://api.telegram.org/bot', resp(400, {'ok': False, 'description': 'bot 123456:TELE-SECRETO-4 inválido'}))
        informe, ok = self.p.ejecutar()
        todo = self.p.texto_libro() + json.dumps(informe, ensure_ascii=False)
        for nombre, valor in SECRETOS.items():
            if 'SECRETO' in valor:
                self.assertNotIn(valor, todo, nombre)
        self.assertIn('***', todo)

    def test_el_libro_es_json_por_linea_con_hora_y_sin_cuerpos(self):
        self.p.ejecutar()
        lineas = self.p.texto_libro().splitlines()
        self.assertGreater(len(lineas), 5)
        for l in lineas:
            e = json.loads(l)
            self.assertTrue({'accion', 'canal', 'tipo', 'juego', 'version', 'huella', 'resultado', 'ts'} <= set(e))
            self.assertRegex(e['ts'], r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')
            self.assertLess(len(l), 800)


# ---------------------------------------------------------------------------------------------------------------------
# Línea de comandos
# ---------------------------------------------------------------------------------------------------------------------

class PruebasComandos(Base):
    def fabrica(self, *args, entorno=None):
        env = {'PYTHONHASHSEED': '3', 'PATH': '/usr/bin:/bin'}
        env.update(entorno or {})
        return subprocess.run([sys.executable, '-I', str(self.p.raiz / 'fabrica.py'), *args], capture_output=True, text=True, env=env, cwd=str(self.p.raiz))

    def test_publicar_sin_ejecutar_solo_muestra_el_plan(self):
        r = self.fabrica('publicar', JUEGO)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Huella: ', r.stdout)
        self.assertIn('Compuertas: todo en orden', r.stdout)
        self.assertIn('--aprobar ' + self.p.plan()[1]['huella'][:16], r.stdout)
        self.assertFalse((self.p.raiz / 'publicacion' / 'libro.jsonl').exists())

    def test_publicar_ejecutar_sin_aprobacion_falla(self):
        r = self.fabrica('publicar', JUEGO, '--ejecutar')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('no coincide', r.stderr)
        self.assertFalse((self.p.raiz / 'publicacion' / 'libro.jsonl').exists())

    def test_sitio_zip_deja_index_en_la_raiz_y_es_reproducible(self):
        import hashlib
        import zipfile
        zip_ = self.p.raiz / 'dist' / 'sitio.zip'
        r = self.fabrica('sitio', '--zip')
        self.assertEqual(r.returncode, 0, r.stderr)
        with zipfile.ZipFile(zip_) as z:
            nombres = z.namelist()
            self.assertIsNone(z.testzip())
        self.assertIn('index.html', nombres)
        self.assertIn('404.html', nombres)
        self.assertIn('_headers', nombres)
        self.assertFalse([n for n in nombres if n.startswith(('sitio/', 'dist/', '/'))], 'el zip no debe traer una carpeta envolvente')
        primero = hashlib.sha256(zip_.read_bytes()).hexdigest()
        self.assertEqual(self.fabrica('sitio', '--zip').returncode, 0)
        self.assertEqual(primero, hashlib.sha256(zip_.read_bytes()).hexdigest())

    def test_sitio_zip_se_niega_con_datos_de_ejemplo(self):
        ruta = self.p.raiz / 'publicacion' / 'sitio.json'
        cfg = json.loads(ruta.read_text(encoding='utf-8'))
        cfg['url_base'] = 'https://CAMBIA-ESTE-NOMBRE.pages.dev'
        cfg['proyecto'] = 'CAMBIA-ESTE-NOMBRE'
        cfg['contacto'] = ''
        ruta.write_text(json.dumps(cfg), encoding='utf-8')
        r = self.fabrica('sitio', '--zip')
        self.assertNotEqual(r.returncode, 0)
        for campo in ('proyecto', 'url_base', 'contacto'):
            self.assertIn(campo, r.stderr)
        self.assertFalse((self.p.raiz / 'dist' / 'sitio.zip').exists())

    def test_publicar_pide_el_juego(self):
        r = self.fabrica('publicar')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Indica el juego', r.stderr)

    def test_configurar_sin_ejecutar_no_hace_nada(self):
        r = self.fabrica('configurar', 'bluesky-bot')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('no cambió nada', r.stdout)

    def test_configurar_ejecutar_sin_claves_falla_claro(self):
        r = self.fabrica('configurar', 'bluesky-bot', '--ejecutar')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('BSKY_IDENTIFIER', r.stderr)

    def test_configurar_desconocido(self):
        r = self.fabrica('configurar', 'nada')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('bluesky-bot', r.stderr)

    def test_resolver_sin_duda_pendiente(self):
        r = self.fabrica('resolver', 'x:1:y:z', 'salio')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('nada que resolver', r.stderr)


class PruebasPaginasDeDifusion(Base):
    """Novedades (notas de cada versión) y Prensa (datos e imágenes para quien reseñe): existen en los tres idiomas y no se rompen."""

    def leer(self, rel):
        return (self.p.raiz / 'dist' / 'sitio' / rel).read_text(encoding='utf-8')

    def test_novedades_y_prensa_existen_en_los_tres_idiomas_con_hreflang_y_en_el_mapa(self):
        mapa = self.leer('sitemap.xml')
        for pagina in ('novedades', 'prensa'):
            for l in ('es', 'en', 'zh'):
                html = self.leer('%s/%s/index.html' % (l, pagina))
                self.assertIn('<html lang="%s"' % ('zh-Hans' if l == 'zh' else l), html)
                for h, destino in (('es', 'es'), ('en', 'en'), ('zh-Hans', 'zh'), ('x-default', 'es')):
                    self.assertIn('<link rel="alternate" hreflang="%s" href="%s/%s/%s/">' % (h, SITIO_URL, destino, pagina), html)
                self.assertIn('<loc>%s/%s/%s/</loc>' % (SITIO_URL, l, pagina), mapa)
                self.assertIn('<link rel="canonical" href="%s/%s/%s/">' % (SITIO_URL, l, pagina), html)

    def test_el_pie_y_el_inicio_enlazan_a_novedades_y_prensa(self):
        for l in ('es', 'en', 'zh'):
            for rel in ('%s/index.html' % l, '%s/privacidad/index.html' % l, '%s/novedades/index.html' % l, '%s/prensa/index.html' % l):
                html = self.leer(rel)
                self.assertIn('href="/%s/novedades/"' % l, html, rel)
                self.assertIn('href="/%s/prensa/"' % l, html, rel)

    def test_novedades_muestra_la_version_y_el_texto_de_cada_idioma(self):
        spec = json.loads((self.p.raiz / 'juegos' / JUEGO / 'juego.json').read_text(encoding='utf-8'))
        notas = spec['novedades']
        self.assertTrue(notas)
        for l in ('es', 'en', 'zh'):
            html = self.leer('%s/novedades/index.html' % l)
            for n in notas:
                self.assertIn(n['version'], html)
                self.assertIn(n[l].replace('&', '&amp;'), html)
            self.assertIn('hola@ejemplo.org', html)
            self.assertIn('href="/%s/juegos/%s/"' % (l, JUEGO), html)

    def test_novedades_en_chino_no_mezcla_el_texto_de_otro_idioma(self):
        spec = json.loads((self.p.raiz / 'juegos' / JUEGO / 'juego.json').read_text(encoding='utf-8'))
        html = self.leer('zh/novedades/index.html')
        for n in spec['novedades']:
            self.assertNotIn(n['es'], html)
            self.assertNotIn(n['en'], html)

    def test_prensa_trae_datos_declaracion_de_ia_imagenes_reales_y_contacto(self):
        spec = json.loads((self.p.raiz / 'juegos' / JUEGO / 'juego.json').read_text(encoding='utf-8'))
        for l in ('es', 'en', 'zh'):
            html = self.leer('%s/prensa/index.html' % l)
            self.assertIn('<dl class="datos">', html)
            self.assertIn('<dd>%s</dd>' % spec['version'], html)
            self.assertIn('mailto:hola@ejemplo.org', html)
            imagenes = re.findall(r'<img src="(/medios/[^"]+)"', html)
            self.assertGreaterEqual(len(imagenes), 2, 'la portada y al menos una captura')
            for ruta in imagenes:
                self.assertTrue((self.p.raiz / 'dist' / 'sitio' / ruta.lstrip('/')).is_file(), ruta)
                self.assertIn('href="%s"' % ruta, html, 'cada imagen se puede abrir en grande')
        # la declaración de que se hizo con IA sale en cada idioma (es el dato que más piden los medios)
        for l, palabra in (('es', 'IA'), ('en', 'AI'), ('zh', 'AI')):
            self.assertIn(palabra, self.leer('%s/prensa/index.html' % l))

    def test_sin_contacto_no_hay_enlaces_de_contacto_en_las_paginas_nuevas(self):
        self.p.editar('publicacion/sitio.json', lambda c: c.update({'contacto': ''}))
        gen.generar(self.p.raiz)
        for pagina in ('novedades', 'prensa'):
            for l in ('es', 'en', 'zh'):
                self.assertNotIn('mailto:', self.leer('%s/%s/index.html' % (l, pagina)))

    def test_una_novedad_sin_un_idioma_o_sin_version_detiene_el_sitio(self):
        def sin_zh(spec):
            del spec['novedades'][0]['zh']
        self.p.editar('juegos/%s/juego.json' % JUEGO, sin_zh)
        with self.assertRaises(gen.ErrorSitio) as e:
            gen.generar(self.p.raiz)
        self.assertIn('novedades', str(e.exception))
        self.assertIn('zh', str(e.exception))

        def sin_version(spec):
            spec['novedades'][0]['zh'] = '修复了问题。'
            del spec['novedades'][0]['version']
        self.p.editar('juegos/%s/juego.json' % JUEGO, sin_version)
        with self.assertRaises(gen.ErrorSitio) as e:
            gen.generar(self.p.raiz)
        self.assertIn('version', str(e.exception))

    def test_un_juego_sin_novedades_no_rompe_la_pagina(self):
        self.p.editar('juegos/%s/juego.json' % JUEGO, lambda spec: spec.pop('novedades'))
        gen.generar(self.p.raiz)
        for l in ('es', 'en', 'zh'):
            self.assertIn('<h1>', self.leer('%s/novedades/index.html' % l))

    def test_el_sitio_con_las_paginas_nuevas_se_genera_igual_dos_veces(self):
        primero = gen.generar(self.p.raiz)['huella']
        self.assertEqual(primero, gen.generar(self.p.raiz)['huella'])

    def test_el_zip_incluye_novedades_y_prensa(self):
        import zipfile
        r = subprocess.run([sys.executable, '-I', str(self.p.raiz / 'fabrica.py'), 'sitio', '--zip'], capture_output=True, text=True, env={'PYTHONHASHSEED': '3', 'PATH': '/usr/bin:/bin'}, cwd=str(self.p.raiz))
        self.assertEqual(r.returncode, 0, r.stderr)
        with zipfile.ZipFile(self.p.raiz / 'dist' / 'sitio.zip') as z:
            nombres = set(z.namelist())
        for l in ('es', 'en', 'zh'):
            self.assertIn('%s/novedades/index.html' % l, nombres)
            self.assertIn('%s/prensa/index.html' % l, nombres)


class PruebasPerfiles(Base):
    """Avatar, banner y textos de las cuentas de bot: caben en cada red, dicen que son bot y no publican datos privados."""

    def setUp(self):
        super().setUp()
        sys.path.insert(0, str(self.p.raiz / 'herramientas'))
        self.addCleanup(sys.path.remove, str(self.p.raiz / 'herramientas'))
        import importlib
        import perfiles
        self.perfiles = importlib.reload(perfiles)

    def test_los_textos_caben_en_cada_red_y_llevan_la_direccion_real(self):
        d = self.perfiles.textos(self.p.raiz)
        self.assertEqual(set(d['redes']), {'bluesky', 'mastodon', 'telegram'})
        for red, datos in d['redes'].items():
            lim = datos['limites']
            for l in ('es', 'en', 'zh'):
                self.assertLessEqual(self.perfiles.largo(datos['bio'][l]), lim['bio'], (red, l))
                self.assertLessEqual(self.perfiles.largo(datos['nombre_visible'][l]), lim['nombre'], (red, l))
                self.assertIn(SITIO_URL, datos['bio'][l], (red, l))
        for l in ('es', 'en', 'zh'):
            campos = d['redes']['mastodon']['campos'][l]
            self.assertLessEqual(len(campos), 4)
            self.assertTrue(all(self.perfiles.largo(a) <= 255 and self.perfiles.largo(b) <= 255 for a, b in campos))

    def test_cada_biografia_declara_que_es_un_bot_y_nunca_trae_el_correo_de_contacto(self):
        d = self.perfiles.textos(self.p.raiz)
        for red, datos in d['redes'].items():
            self.assertIn('bot', datos['bio']['es'].lower(), red)
            self.assertIn('bot', datos['bio']['en'].lower(), red)
            self.assertIn('机器人', datos['bio']['zh'], red)
            self.assertIn('bot', datos['nombre_visible']['es'].lower() if red != 'telegram' else datos['bio']['es'].lower())
        self.assertNotIn('hola@ejemplo.org', json.dumps(d, ensure_ascii=False), 'el correo vive solo en el sitio')

    def test_el_idioma_recomendado_sale_de_la_politica_y_el_usuario_de_la_marca(self):
        self.p.politica(lambda pol: pol['idioma'].update({'mastodon': 'en'}))
        d = self.perfiles.textos(self.p.raiz)
        self.assertEqual(d['redes']['mastodon']['idioma_recomendado'], 'en')
        self.assertEqual(d['redes']['bluesky']['idioma_recomendado'], 'es')
        self.assertEqual(d['redes']['bluesky']['usuario_sugerido'], 'tallergelatina.bsky.social')
        self.assertEqual(d['redes']['telegram']['usuario_sugerido'], '@tallergelatina')

    def test_un_nombre_que_no_cabe_detiene_la_generacion_y_dice_donde(self):
        self.p.editar('publicacion/sitio.json', lambda c: c.update({'nombre': 'Taller de Gelatina Experimental Número Uno'}))
        with self.assertRaises(self.perfiles.ErrorPerfiles) as e:
            self.perfiles.textos(self.p.raiz)
        self.assertIn('mastodon · nombre', str(e.exception))
        self.assertIn('el límite es 30', str(e.exception))

    def test_se_niega_con_datos_de_ejemplo(self):
        self.p.editar('publicacion/sitio.json', lambda c: c.update({'url_base': 'https://CAMBIA-ESTE-NOMBRE.pages.dev'}))
        with self.assertRaises(self.perfiles.ErrorPerfiles):
            self.perfiles.textos(self.p.raiz)

    def test_el_comando_escribe_json_y_markdown_sin_navegador(self):
        r = subprocess.run([sys.executable, '-I', str(self.p.raiz / 'fabrica.py'), 'perfiles', '--texto'], capture_output=True, text=True,
                           env={'PYTHONHASHSEED': '3', 'PATH': '/usr/bin:/bin'}, cwd=str(self.p.raiz))
        self.assertEqual(r.returncode, 0, r.stderr)
        carpeta = self.p.raiz / 'difusion' / 'perfiles'
        datos = json.loads((carpeta / 'perfiles.json').read_text(encoding='utf-8'))
        md = (carpeta / 'perfiles.md').read_text(encoding='utf-8')
        self.assertIn(datos['redes']['bluesky']['bio']['es'], md)
        self.assertIn(datos['redes']['mastodon']['bio']['zh'], md)
        self.assertIn('(recomendado)', md)
        self.assertIn('de bot y lo dicen', md)

    def test_las_imagenes_del_repositorio_tienen_el_tamano_y_el_peso_que_piden_las_redes(self):
        from PIL import Image
        carpeta = RAIZ / 'difusion' / 'perfiles'
        for nombre, medida in (('avatar.png', (800, 800)), ('banner.png', (1500, 500))):
            archivo = carpeta / nombre
            self.assertTrue(archivo.is_file(), nombre)
            self.assertLessEqual(archivo.stat().st_size, self.perfiles.PESO_MAXIMO_IMAGEN, nombre)
            with Image.open(archivo) as im:
                self.assertEqual(im.size, medida, nombre)


class PruebasCiclo(Base):
    def fabrica(self, *args):
        return subprocess.run([sys.executable, '-I', str(self.p.raiz / 'fabrica.py'), *args], capture_output=True, text=True, env={'PYTHONHASHSEED': '5', 'PATH': '/usr/bin:/bin'}, cwd=str(self.p.raiz))

    def test_el_zip_es_igual_en_cada_construccion(self):
        import hashlib
        import time
        zip_ruta = self.p.raiz / 'salida' / JUEGO / ('%s-web.zip' % JUEGO)
        self.assertEqual(self.fabrica('construir', JUEGO).returncode, 0)
        primero = hashlib.sha256(zip_ruta.read_bytes()).hexdigest()
        time.sleep(2.2)                                                      # los zip guardan la fecha con resolución de 2 s
        self.assertEqual(self.fabrica('construir', JUEGO).returncode, 0)
        self.assertEqual(hashlib.sha256(zip_ruta.read_bytes()).hexdigest(), primero)

    def test_el_zip_del_juego_va_sin_comprimir_para_no_depender_del_zlib_de_cada_maquina(self):
        import zipfile
        self.assertEqual(self.fabrica('construir', JUEGO).returncode, 0)
        with zipfile.ZipFile(self.p.raiz / 'salida' / JUEGO / ('%s-web.zip' % JUEGO)) as z:
            (info,) = z.infolist()
            self.assertEqual(info.filename, 'index.html')
            self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
            self.assertEqual(z.read('index.html'), (self.p.raiz / 'salida' / JUEGO / 'index.html').read_bytes())

    def test_el_ciclo_deja_el_estado_y_no_cambia_la_huella(self):
        antes = self.p.plan()[1]['huella']
        r = self.fabrica('ciclo')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        texto = (self.p.raiz / 'publicacion' / 'PENDIENTE.md').read_text(encoding='utf-8')
        self.assertIn('## %s (v' % JUEGO, texto)
        self.assertIn('**Listo para aprobar**', texto)
        self.assertIn('--aprobar ' + antes[:16], texto)                       # reconstruir todo no altera lo que se aprobaría
        self.assertIn('Fuera del sitio', texto)                               # torre-gelatina todavía no está en sitio.json → juegos
        self.assertIn('## Qué construir después', texto)
        self.assertNotRegex(texto, r'\d{4}-\d\d-\d\d')                          # sin fechas: no ensucia el historial
        for valor in SECRETOS.values():
            self.assertNotIn(valor, texto)

    def test_despues_de_publicar_el_ciclo_dice_al_dia(self):
        informe, ok = self.p.ejecutar()
        self.assertTrue(ok, informe)
        self.p.regenerar_sitio()
        r = self.fabrica('ciclo')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        texto = (self.p.raiz / 'publicacion' / 'PENDIENTE.md').read_text(encoding='utf-8')
        self.assertIn('Al día', texto)

    def test_el_ciclo_muestra_lo_dudoso_con_su_comando(self):
        self.p.red.al('POST', 'https://bsky.social/xrpc/com.atproto.repo.createRecord', red.ErrorRed('timeout'))
        self.p.ejecutar()
        r = self.fabrica('ciclo')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        texto = (self.p.raiz / 'publicacion' / 'PENDIENTE.md').read_text(encoding='utf-8')
        self.assertIn('Hay envíos en duda', texto)
        self.assertIn('python3 fabrica.py resolver %s:1.4.0:bluesky:post salio|no-salio' % JUEGO, texto)


class PruebasCoherencia(unittest.TestCase):
    def test_los_secretos_del_flujo_del_mapa_y_de_los_adaptadores_coinciden(self):
        import re
        flujo = set(re.findall(r'\$\{\{ secrets\.(\w+) \}\}', (RAIZ / '.github' / 'workflows' / 'publicar.yml').read_text(encoding='utf-8')))
        canales = json.loads((RAIZ / 'difusion' / 'canales.json').read_text(encoding='utf-8'))
        mapa = {x for c in canales['canales'] for x in c.get('automatizacion', {}).get('secretos', [])}
        codigo = {x for a in ADAPTADORES for x in a.secretos}
        self.assertEqual(flujo, codigo)
        self.assertEqual(mapa, codigo)

    def test_cada_adaptador_corresponde_a_un_canal_del_mapa_con_su_nivel(self):
        canales = {c['id']: c for c in json.loads((RAIZ / 'difusion' / 'canales.json').read_text(encoding='utf-8'))['canales']}
        for a in ADAPTADORES:
            self.assertIn(a.canal, canales, a.canal)
            self.assertIn(canales[a.canal]['automatizacion']['nivel'], ('total', 'parcial'), a.canal)
            self.assertEqual(sorted(a.secretos), sorted(canales[a.canal]['automatizacion'].get('secretos', [])), a.canal)

    def test_la_guia_del_dueno_nombra_todas_las_claves_y_los_comandos_reales(self):
        import re
        guia = (RAIZ / 'LEEME-DUENO.md').read_text(encoding='utf-8')
        # el itch.io de las claves (BUTLER_API_KEY) también debe estar: son todas las que el código sabe usar
        for a in ADAPTADORES:
            for clave in a.secretos:
                self.assertIn(clave, guia, 'LEEME-DUENO.md no menciona la clave %s' % clave)
        ayuda = (RAIZ / 'fabrica.py').read_text(encoding='utf-8')
        for comando in re.findall(r'python3 fabrica\.py ([a-z-]+)', guia):
            self.assertIn('python3 fabrica.py ' + comando, ayuda, 'la guía usa un comando que la fábrica no documenta: ' + comando)

    def test_el_flujo_de_configurar_bot_usa_solo_las_claves_de_esas_dos_cuentas_y_sus_opciones_existen(self):
        import re
        texto = (RAIZ / '.github' / 'workflows' / 'configurar-bot.yml').read_text(encoding='utf-8')
        claves = set(re.findall(r'\$\{\{ secrets\.(\w+) \}\}', texto))
        self.assertEqual(claves, {'BSKY_IDENTIFIER', 'BSKY_APP_PASSWORD', 'MASTODON_INSTANCE', 'MASTODON_TOKEN'})
        self.assertLessEqual(claves, {x for a in ADAPTADORES for x in a.secretos})
        self.assertIn('environment: produccion', texto)
        fabrica = (RAIZ / 'fabrica.py').read_text(encoding='utf-8')
        for opcion in re.findall(r'^          - ([a-z-]+-bot)$', texto, re.M):
            self.assertIn("'%s':" % opcion, fabrica, 'el flujo ofrece una cuenta que «configurar» no conoce: ' + opcion)
        self.assertEqual(sorted(re.findall(r'^          - ([a-z-]+-bot)$', texto, re.M)), ['bluesky-bot', 'mastodon-bot'])

    def test_los_pasos_que_pasan_por_tee_usan_pipefail_para_no_ocultar_los_fallos(self):
        import re
        for f in (RAIZ / '.github' / 'workflows').glob('*.yml'):
            for paso in re.split(r'(?m)^(?=      - )', f.read_text(encoding='utf-8')):
                if '| tee' in paso:
                    self.assertIn('shell: bash', paso, '%s: con «| tee» y sin pipefail, un fallo de la fábrica sale como éxito' % f.name)

    def test_los_flujos_no_interpolan_entradas_dentro_de_los_scripts(self):
        import re
        for f in (RAIZ / '.github' / 'workflows').glob('*.yml'):
            texto = f.read_text(encoding='utf-8')
            for bloque in re.findall(r'run: \|\n((?:        .*\n?)+)', texto):
                self.assertNotIn('${{', bloque, '%s: una entrada del usuario dentro de un script abre la puerta a inyección de comandos' % f.name)


class PruebasEtiquetaBot(Base):
    def test_bluesky_conserva_el_perfil_y_pone_la_etiqueta(self):
        from publicacion.adaptadores import bluesky
        perfil = {'$type': 'app.bsky.actor.profile', 'displayName': 'Taller', 'description': 'Juegos'}
        self.p.red.al('GET', 'https://bsky.social/xrpc/com.atproto.repo.getRecord', resp(200, {'value': perfil, 'cid': 'bafyperfil'}))
        self.p.red.al('POST', 'https://bsky.social/xrpc/com.atproto.repo.putRecord', resp(200, {}))
        bluesky.marcar_bot(self.p.ent(), {})
        (c,) = self.p.red.a('POST', 'https://bsky.social/xrpc/com.atproto.repo.putRecord')
        cuerpo = json.loads(c['cuerpo'])
        self.assertEqual((cuerpo['collection'], cuerpo['rkey'], cuerpo['swapRecord']), ('app.bsky.actor.profile', 'self', 'bafyperfil'))
        self.assertEqual(cuerpo['record']['displayName'], 'Taller')
        self.assertEqual(cuerpo['record']['labels'], {'$type': 'com.atproto.label.defs#selfLabels', 'values': [{'val': 'bot'}]})

    def test_mastodon_marca_la_cuenta_como_bot(self):
        from publicacion.adaptadores import mastodon
        self.p.red.al('PATCH', 'https://mast.ejemplo/api/v1/accounts/update_credentials', resp(200, {}))
        mastodon.marcar_bot(self.p.ent(), {})
        (c,) = self.p.red.a('PATCH', 'https://mast.ejemplo/api/v1/accounts/update_credentials')
        self.assertEqual(c['cuerpo'], b'bot=true')
        self.assertEqual(c['cab']['Authorization'], 'Bearer ' + SECRETOS['MASTODON_TOKEN'])


# ---------------------------------------------------------------------------------------------------------------------
# Métricas y rumbo
# ---------------------------------------------------------------------------------------------------------------------

import metricas as met      # noqa: E402
import rumbo                # noqa: E402

IDS = {'guerreros-gelatina', 'torre-gelatina'}
TORRE = 'torre-gelatina'
HOY = datetime.date(2026, 11, 23)          # un lunes: las semanas completas son las que terminan antes de hoy
TOKEN_CF = 'cf-analitica-SECRETO-9'
CUENTA_CF = 'a1b2c3d4e5f60718293a4b5c6d7e8f90'
GRAPHQL = 'https://api.cloudflare.com/client/v4/graphql'


def gql(grupos):
    return resp(200, {'data': {'viewer': {'accounts': [{'rumPageloadEventsAdaptiveGroups': grupos}]}}, 'errors': None})


def grupo(fecha, ruta, cuenta):
    return {'count': cuenta, 'dimensions': {'date': fecha, 'requestPath': ruta}}


def idea(iid, genero, verbo, objetivo, entrada, progresion, riesgo='medio', costo='medio', **extra):
    d = {'id': iid, 'titulo': iid.capitalize(), 'mecanica': {'genero': genero, 'verbo': verbo, 'objetivo': objetivo, 'entrada': entrada, 'progresion': progresion},
         'referencias': [], 'riesgo_estimado': riesgo, 'costo_estimado': costo, 'brief': 'x', 'gancho': 'x'}
    d.update(extra)
    return d


# dos ideas que comparten rasgos, una con guerreros-gelatina y la otra con torre-gelatina, y por lo demás iguales
IDEA_COMO_GUERREROS = idea('cercana-a-guerreros', 'tiro-arcade', 'colocar', 'sobrevivir', ['arrastrar'], 'niveles-con-oro')
IDEA_COMO_TORRE = idea('cercana-a-torre', 'plataformas', 'soltar', 'llegar-a-la-meta', ['teclado'], 'puntaje-infinito')


class BaseMetricas(Base):
    def setUp(self):
        super().setUp()
        self.raiz = self.p.raiz

    def ideas(self, lista):
        (self.raiz / 'ideas' / 'ideas.json').write_text(json.dumps({'ideas': lista}, ensure_ascii=False), encoding='utf-8')

    def anota(self, juego, metrica, valor, semana, fuente='cloudflare'):
        return met.anotar(self.raiz, juego, metrica, valor, semana, fuente, '', IDS, HOY)

    def vistas(self, juego, por_semana, metrica='vistas_juego'):
        for semana, v in por_semana:
            self.anota(juego, metrica, v, semana)

    def tres_semanas(self, juego, cada_una):
        self.vistas(juego, [('2026-11-02', cada_una), ('2026-11-09', cada_una), ('2026-11-16', cada_una)])

    def recomendar(self, libro=None):
        return rumbo.recomendar(self.raiz, HOY, libro=libro if libro is not None else [])


class PruebasPortadaDeHeroes(unittest.TestCase):
    """La portada de Guerreros Gelatina se compone con un escenario de héroes (herramientas/portada-heroes.html + portada.reparto)."""

    def test_la_plantilla_trae_todas_las_marcas_que_sustituye_probar_y_ninguna_de_mas(self):
        js = (RAIZ / 'herramientas' / 'probar.js').read_text(encoding='utf-8')
        bloque = js[js.index('if (heroes) {'):js.index("plantilla = 'portada-heroes.html'")]
        usadas = set(re.findall(r"'(@@[A-Z0-9]+@@)'", bloque))
        html = (RAIZ / 'herramientas' / 'portada-heroes.html').read_text(encoding='utf-8')
        en_plantilla = set(re.findall(r'@@[A-Z0-9]+@@', html))
        self.assertTrue(usadas)
        self.assertEqual(usadas, en_plantilla, 'cada marca de la plantilla debe sustituirse (y al revés)')

    def test_el_reparto_es_valido_y_usa_unidades_que_existen_en_el_juego(self):
        spec = json.loads((RAIZ / 'juegos' / JUEGO / 'juego.json').read_text(encoding='utf-8'))
        p = spec['portada']
        self.assertEqual(p['estilo'], 'heroes')
        juego = (RAIZ / 'salida' / JUEGO / 'index.html').read_text(encoding='utf-8')
        self.assertIn('else boot();\n})();', juego, 'sin este final no se puede dibujar el arte de la portada')
        for tipo, equipo, x, y, escala, direccion, golpe in p['reparto']:
            with self.subTest(tipo=tipo):
                self.assertTrue(('units.%s = ' % tipo) in juego or re.search(r'\b%s: *\{' % tipo, juego), 'la unidad %s no existe' % tipo)
                self.assertIn(equipo, (0, 1))
                self.assertIn(direccion, (1, -1))
                self.assertTrue(0 <= golpe <= 1 and 0 < escala < 8)
                self.assertTrue(0 <= x <= 630 and 0 <= y <= 500)

    def test_la_portada_generada_tiene_la_proporcion_que_pide_itch(self):
        from PIL import Image
        with Image.open(RAIZ / 'salida' / JUEGO / 'medios' / 'portada.png') as im:
            self.assertEqual(im.size, (1260, 1000))


class PruebasRegistroDeMetricas(BaseMetricas):
    def test_anotar_escribe_una_fila_y_la_semana_es_siempre_un_lunes(self):
        f = met.anotar(self.raiz, JUEGO, 'vistas_juego', '40', '2026-11-19', 'manual', 'dato de prueba', IDS, HOY)     # un jueves
        self.assertEqual(f['semana'], datetime.date(2026, 11, 16))
        (fila,) = met.leer(self.raiz, IDS)
        self.assertEqual((fila['semana'], fila['juego'], fila['metrica'], fila['valor'], fila['fuente'], fila['nota']),
                         (datetime.date(2026, 11, 16), JUEGO, 'vistas_juego', 40, 'manual', 'dato de prueba'))

    def test_esta_y_pasada_se_calculan_desde_hoy_y_la_semana_en_curso_se_avisa(self):
        self.assertEqual(met.interpretar_semana('esta', datetime.date(2026, 11, 25)), datetime.date(2026, 11, 23))
        self.assertEqual(met.interpretar_semana('pasada', datetime.date(2026, 11, 25)), datetime.date(2026, 11, 16))
        self.assertTrue(met.anotar(self.raiz, JUEGO, 'vistas_juego', 1, 'esta', 'manual', '', IDS, HOY)['en_curso'])
        self.assertFalse(met.anotar(self.raiz, JUEGO, 'vistas_juego', 1, 'pasada', 'manual', '', IDS, HOY)['en_curso'])
        with self.assertRaises(met.ErrorMetricas):
            met.interpretar_semana('ayer', HOY)

    def test_se_rechaza_lo_que_no_tiene_sentido_y_no_se_escribe_nada(self):
        malos = [('no-existe', 'vistas_juego', '1', 'manual'), (JUEGO, 'visitas', '1', 'manual'), (JUEGO, 'vistas_juego', '-3', 'manual'),
                 (JUEGO, 'vistas_juego', '2.5', 'manual'), (JUEGO, 'vistas_juego', 'mucho', 'manual'), (JUEGO, 'vistas_juego', 'nan', 'manual'),
                 (JUEGO, 'donaciones_usd', '1.234', 'manual'), (JUEGO, 'vistas_juego', '1', 'Fuente Con Espacios')]
        for juego, metrica, valor, fuente in malos:
            with self.assertRaises(met.ErrorMetricas, msg=(juego, metrica, valor, fuente)):
                met.anotar(self.raiz, juego, metrica, valor, 'pasada', fuente, '', IDS, HOY)
        with self.assertRaises(met.ErrorMetricas):
            met.anotar(self.raiz, JUEGO, 'vistas_juego', 1, 'pasada', 'manual', 'dos\nlíneas', IDS, HOY)
        self.assertEqual(met.leer(self.raiz, IDS), [])

    def test_el_dinero_acepta_centavos_y_coma_decimal(self):
        met.anotar(self.raiz, JUEGO, 'donaciones_usd', '3,5', 'pasada', 'manual', '', IDS, HOY)
        (fila,) = met.leer(self.raiz, IDS)
        self.assertEqual((fila['valor'], fila['texto']), (3.5, '3.50'))

    def test_una_nota_no_puede_volverse_formula_en_una_hoja_de_calculo(self):
        met.anotar(self.raiz, JUEGO, 'vistas_juego', 1, 'pasada', 'manual', '=HYPERLINK("http://x")', IDS, HOY)
        met.anotar(self.raiz, JUEGO, 'vistas_juego', 2, 'pasada', 'itch', '-5 % que la semana pasada', IDS, HOY)
        for linea in (self.raiz / 'metricas' / 'registro.csv').read_text(encoding='utf-8').splitlines()[1:]:
            self.assertNotRegex(linea.split(',', 5)[-1].strip('"'), r'^[=+\-@]')

    def test_la_ultima_fila_de_cada_fuente_corrige_y_las_fuentes_se_suman(self):
        self.anota(JUEGO, 'vistas_juego', 100, '2026-11-09', 'cloudflare')
        self.anota(JUEGO, 'vistas_juego', 130, '2026-11-09', 'cloudflare')          # corrección
        self.anota(JUEGO, 'vistas_juego', 25, '2026-11-09', 'itch')
        s = met.sumas(met.leer(self.raiz, IDS))
        self.assertEqual(s[(datetime.date(2026, 11, 9), JUEGO, 'vistas_juego')], 155)
        self.assertEqual(len((self.raiz / 'metricas' / 'registro.csv').read_text(encoding='utf-8').splitlines()), 4)     # encabezado + las tres filas: nada se borra

    def test_un_registro_dañado_dice_en_que_linea_y_no_se_lee_a_medias(self):
        ruta = self.raiz / 'metricas' / 'registro.csv'
        ruta.write_text(','.join(met.ENCABEZADO) + '\n2026-11-18,%s,vistas_juego,3,manual,\n2026-11-16,%s,vistas_juego,3,manual\n2026-11-16,%s,vistas_juego,3,Mala Fuente,\n' % (JUEGO, JUEGO, JUEGO),
                        encoding='utf-8')
        with self.assertRaises(met.ErrorMetricas) as c:
            met.leer(self.raiz, IDS)
        mensaje = str(c.exception)
        for esperado in ('línea 2', 'línea 3', 'línea 4'):
            self.assertIn(esperado, mensaje)
        ruta.write_text('semana,otra\n', encoding='utf-8')
        with self.assertRaises(met.ErrorMetricas):
            met.leer(self.raiz, IDS)

    def test_agregar_a_un_archivo_sin_salto_final_no_pega_dos_filas(self):
        ruta = self.raiz / 'metricas' / 'registro.csv'
        ruta.write_text(','.join(met.ENCABEZADO) + '\n2026-11-16,%s,vistas_juego,3,manual,' % JUEGO, encoding='utf-8')
        self.anota(JUEGO, 'vistas_juego', 4, '2026-11-09', 'manual')
        self.assertEqual(len(met.leer(self.raiz, IDS)), 2)

    def test_la_tabla_marca_la_semana_en_curso(self):
        self.anota(JUEGO, 'vistas_juego', 7, '2026-11-16')
        self.anota(JUEGO, 'vistas_juego', 9, '2026-11-23', 'manual')
        texto = met.tabla(self.raiz, None, IDS, HOY)
        self.assertIn('2026-11-16 ', texto)
        self.assertIn('2026-11-23*', texto)
        self.assertEqual(met.tabla(self.raiz, TORRE, IDS, HOY), 'Todavía no hay métricas registradas de «%s».' % TORRE)

    def test_la_politica_es_coherente(self):
        pol = met.cargar_politica(self.raiz)
        r = pol['rumbo']
        self.assertEqual(set(r['pesos']), {'alcance', 'aceptacion', 'apoyo'})
        self.assertEqual(set(r['fuerza_previa']), {'alcance', 'aceptacion', 'apoyo', 'rasgos'})
        self.assertLessEqual(set(r['peso_ejes']), set(rumbo.EJES))
        for tabla in ('factor_riesgo', 'factor_costo'):
            self.assertEqual(set(r[tabla]), {'bajo', 'medio', 'alto'})
            self.assertTrue(all(0 < v <= 1 for v in r[tabla].values()))
        self.assertEqual(set(r['factor_novedad']), {'distinto', 'parecido'})        # una variante nunca entra
        for nombre, m in pol['metricas'].items():
            self.assertIn(m['tipo'], ('conteo', 'dinero'), nombre)


class PruebasImportarCloudflare(BaseMetricas):
    def setUp(self):
        super().setUp()
        self.p.env.update({'CLOUDFLARE_ANALITICA_TOKEN': TOKEN_CF, 'CLOUDFLARE_ACCOUNT_ID': CUENTA_CF})

    def importar(self, grupos=None, dias=21, hoy=datetime.date(2026, 11, 18)):
        self.p.red.al('POST', GRAPHQL, gql(grupos if grupos is not None else []))
        return met.importar_cloudflare(self.raiz, self.p.ent(), IDS, dias, hoy)

    def test_la_consulta_pide_las_vistas_del_dominio_desde_un_lunes_con_el_token_en_la_cabecera(self):
        self.importar([grupo('2026-11-17', '/jugar/%s/' % JUEGO, 5)])
        (c,) = self.p.red.a('POST', GRAPHQL)
        self.assertEqual(c['cab']['Authorization'], 'Bearer ' + TOKEN_CF)
        consulta = json.loads(c['cuerpo'])['query']
        for esperado in ('rumPageloadEventsAdaptiveGroups', 'accountTag: "%s"' % CUENTA_CF, 'requestHost: "taller-gelatina.pages.dev"', 'bot: 0',
                         'datetime_geq: "2026-10-26T00:00:00Z"', 'datetime_lt: "2026-11-19T00:00:00Z"', 'requestPath', 'date'):
            self.assertIn(esperado, consulta)
        self.assertNotIn(TOKEN_CF, consulta)

    def test_cada_ruta_va_a_su_metrica_y_las_demas_se_ignoran(self):
        r = self.importar([
            grupo('2026-11-02', '/jugar/%s/' % JUEGO, 30), grupo('2026-11-04', '/jugar/%s/' % JUEGO, 12),          # misma semana: se suman
            grupo('2026-11-03', '/es/juegos/%s/' % JUEGO, 8), grupo('2026-11-03', '/en/juegos/%s/index.html' % JUEGO, 2),
            grupo('2026-11-10', '/jugar/%s/' % TORRE, 4),
            grupo('2026-11-10', '/es/', 99), grupo('2026-11-10', '/jugar/no-existe/', 99), grupo('2026-11-10', '/jugar/%s/otra/cosa' % JUEGO, 99)])
        self.assertEqual(r['aviso'], '')
        s = met.sumas(met.leer(self.raiz, IDS))
        L = datetime.date
        self.assertEqual(s[(L(2026, 11, 2), JUEGO, 'vistas_juego')], 42)
        self.assertEqual(s[(L(2026, 11, 2), JUEGO, 'vistas_ficha')], 10)
        self.assertEqual(s[(L(2026, 11, 9), TORRE, 'vistas_juego')], 4)
        self.assertNotIn(99, s.values())

    def test_las_semanas_sin_visitas_quedan_en_cero_para_distinguirlas_de_no_medidas(self):
        self.importar([grupo('2026-11-10', '/jugar/%s/' % JUEGO, 3)])
        s = met.sumas(met.leer(self.raiz, IDS))
        self.assertEqual(s[(datetime.date(2026, 10, 26), TORRE, 'vistas_juego')], 0)
        self.assertEqual(s[(datetime.date(2026, 11, 16), JUEGO, 'vistas_ficha')], 0)

    def test_volver_a_importar_lo_mismo_no_agrega_filas_y_un_cambio_agrega_una_correccion(self):
        grupos = [grupo('2026-11-10', '/jugar/%s/' % JUEGO, 10)]
        primero = self.importar(grupos)
        filas = len((self.raiz / 'metricas' / 'registro.csv').read_text(encoding='utf-8').splitlines())
        segundo = self.importar(grupos)
        self.assertEqual((segundo['escritas'], len((self.raiz / 'metricas' / 'registro.csv').read_text(encoding='utf-8').splitlines())), (0, filas))
        self.assertEqual(segundo['sin_cambio'], primero['escritas'])
        tercero = self.importar([grupo('2026-11-10', '/jugar/%s/' % JUEGO, 14)])
        self.assertEqual(tercero['escritas'], 1)
        self.assertEqual(met.sumas(met.leer(self.raiz, IDS))[(datetime.date(2026, 11, 9), JUEGO, 'vistas_juego')], 14)

    def test_sin_ninguna_vista_no_se_escribe_nada_y_se_explica(self):
        r = self.importar([])
        self.assertEqual(r['escritas'], 0)
        self.assertIn('Web Analytics', r['aviso'])
        self.assertEqual(met.leer(self.raiz, IDS), [])

    def test_la_ventana_empieza_en_lunes_y_nunca_pide_mas_de_un_mes(self):
        self.importar([grupo('2026-11-10', '/jugar/%s/' % JUEGO, 1)], dias=400)
        consulta = json.loads(self.p.red.a('POST', GRAPHQL)[0]['cuerpo'])['query']
        # tope de 27 días antes del miércoles 18/11 = jueves 22/10; la ventana empieza el lunes anterior (19/10): menos de 5 semanas
        self.assertEqual(met.VENTANA_MAXIMA_DIAS, 27)
        self.assertIn('datetime_geq: "2026-10-19T00:00:00Z"', consulta)
        self.assertIn('datetime_lt: "2026-11-19T00:00:00Z"', consulta)
        filas = met.leer(self.raiz, IDS)
        self.assertEqual(min(f['semana'] for f in filas), datetime.date(2026, 10, 19))

    def test_token_sin_permiso_dice_que_permiso_falta_y_no_muestra_el_token(self):
        self.p.red.al('POST', GRAPHQL, resp(403, {'errors': [{'message': 'forbidden ' + TOKEN_CF}]}))
        with self.assertRaises(met.ErrorMetricas) as c:
            met.importar_cloudflare(self.raiz, self.p.ent(), IDS, 21, HOY)
        self.assertIn('Account Analytics: Read', str(c.exception))
        self.assertNotIn(TOKEN_CF, str(c.exception))
        self.assertEqual(met.leer(self.raiz, IDS), [])

    def test_si_el_esquema_rechaza_el_filtro_de_bots_se_reintenta_sin_el_y_queda_anotado(self):
        respuestas = [resp(200, {'data': None, 'errors': [{'message': 'unknown field "bot"'}]}), gql([grupo('2026-11-10', '/jugar/%s/' % JUEGO, 6)])]
        self.p.red.al('POST', GRAPHQL, lambda url, cab, cuerpo: respuestas.pop(0))
        r = met.importar_cloudflare(self.raiz, self.p.ent(), IDS, 21, datetime.date(2026, 11, 18))
        consultas = [json.loads(c['cuerpo'])['query'] for c in self.p.red.a('POST', GRAPHQL)]
        self.assertIn('bot: 0', consultas[0])
        self.assertNotIn('bot: 0', consultas[1])
        self.assertGreater(r['escritas'], 0)
        self.assertTrue(all(f['nota'] == 'sin filtro de bots' for f in met.leer(self.raiz, IDS)))

    def test_otros_errores_de_graphql_se_informan_y_no_escriben(self):
        self.p.red.al('POST', GRAPHQL, resp(200, {'data': None, 'errors': [{'message': 'zone not found'}]}))
        with self.assertRaises(met.ErrorMetricas) as c:
            met.importar_cloudflare(self.raiz, self.p.ent(), IDS, 21, HOY)
        self.assertIn('zone not found', str(c.exception))
        self.assertEqual(met.leer(self.raiz, IDS), [])

    def test_cuenta_vacia_y_secretos_faltantes_o_mal_formados(self):
        self.p.red.al('POST', GRAPHQL, resp(200, {'data': {'viewer': {'accounts': []}}, 'errors': None}))
        with self.assertRaises(met.ErrorMetricas):
            met.importar_cloudflare(self.raiz, self.p.ent(), IDS, 21, HOY)
        for cambio in ({'CLOUDFLARE_ANALITICA_TOKEN': ''}, {'CLOUDFLARE_ACCOUNT_ID': ''}, {'CLOUDFLARE_ACCOUNT_ID': 'no-es-hexadecimal'}):
            self.p.env.update(cambio)
            with self.assertRaises(met.ErrorMetricas):
                met.importar_cloudflare(self.raiz, self.p.ent(), IDS, 21, HOY)
            self.p.env.update({'CLOUDFLARE_ANALITICA_TOKEN': TOKEN_CF, 'CLOUDFLARE_ACCOUNT_ID': CUENTA_CF})

    def test_el_token_nunca_llega_al_registro(self):
        self.importar([grupo('2026-11-10', '/jugar/%s/' % JUEGO, 6)])
        texto = (self.raiz / 'metricas' / 'registro.csv').read_text(encoding='utf-8')
        for secreto in (TOKEN_CF, CUENTA_CF):
            self.assertNotIn(secreto, texto)


class PruebasRumbo(BaseMetricas):
    def test_sin_datos_explora_y_dice_cuanto_falta(self):
        self.ideas([idea('nueva', 'ritmo', 'cronometrar', 'puntaje-maximo', ['toque'], 'desbloqueos')])
        r = self.recomendar()
        self.assertEqual(r['modo'], 'explorar')
        self.assertEqual([c['id'] for c in r['ranking']], ['nueva'])
        texto = '\n'.join(rumbo.informe(r))
        self.assertIn('Todavía no hay datos para decidir por métricas', texto)
        self.assertIn('No hay ninguna métrica registrada', texto)

    def test_explorar_prefiere_lo_nuevo_barato_y_con_menos_riesgo_de_clon(self):
        self.ideas([idea('cara-y-arriesgada', 'ritmo', 'cronometrar', 'puntaje-maximo', ['toque'], 'desbloqueos', riesgo='alto', costo='alto'),
                    idea('barata-y-segura', 'sandbox-creativo', 'dibujar', 'descubrir', ['arrastrar'], 'desbloqueos', riesgo='bajo', costo='bajo'),
                    idea('media', 'puzzle-fisico', 'apuntar', 'resolver-nivel', ['apuntar-y-disparar'], 'niveles-fijos')])
        self.assertEqual([c['id'] for c in self.recomendar()['ranking']], ['barata-y-segura', 'media', 'cara-y-arriesgada'])

    def test_explorar_prefiere_los_rasgos_que_la_fabrica_todavia_no_tiene(self):
        self.ideas([idea('repite-rasgos', 'tiro-arcade', 'colocar', 'sobrevivir', ['toque'], 'niveles-con-oro'),
                    idea('rasgos-nuevos', 'tiro-arcade', 'apuntar', 'puntaje-maximo', ['apuntar-y-disparar'], 'niveles-fijos')])
        orden = [c['id'] for c in self.recomendar()['ranking']]
        self.assertEqual(orden, ['rasgos-nuevos', 'repite-rasgos'])

    def test_el_resultado_es_el_mismo_cada_vez(self):
        self.ideas([IDEA_COMO_GUERREROS, IDEA_COMO_TORRE])
        self.tres_semanas(JUEGO, 300)
        self.tres_semanas(TORRE, 100)
        a, b = self.recomendar(), self.recomendar()
        self.assertEqual(rumbo.informe(a, detalle=True), rumbo.informe(b, detalle=True))
        self.assertEqual([c['id'] for c in a['ranking']], [c['id'] for c in b['ranking']])

    def test_una_variante_de_un_juego_existente_nunca_se_recomienda(self):
        m = json.loads((self.raiz / 'juegos' / TORRE / 'juego.json').read_text(encoding='utf-8'))['mecanica']
        self.ideas([idea('torre-otra-vez', m['genero'], m['verbo'], m['objetivo'], ['toque'], 'niveles-fijos', riesgo='bajo', costo='bajo'),
                    idea('otra', 'ritmo', 'cronometrar', 'puntaje-maximo', ['toque'], 'desbloqueos', riesgo='alto', costo='alto')])
        r = self.recomendar()
        self.assertEqual([c['id'] for c in r['ranking']], ['otra'])
        self.assertEqual([e['id'] for e in r['excluidas']], ['torre-otra-vez'])
        self.assertIn('variante', r['excluidas'][0]['motivo'])

    def test_una_idea_bloqueada_se_lista_aparte_y_una_ya_construida_se_omite(self):
        (self.raiz / 'plantillas' / 'ya-hecha').mkdir()
        self.ideas([idea('bloqueada', 'ritmo', 'cronometrar', 'puntaje-maximo', ['toque'], 'desbloqueos', bloqueada_por='falta una revisión humana'),
                    idea('ya-hecha', 'sandbox-creativo', 'dibujar', 'descubrir', ['arrastrar'], 'desbloqueos'),
                    idea('libre', 'puzzle-fisico', 'apuntar', 'resolver-nivel', ['apuntar-y-disparar'], 'niveles-fijos')])
        r = self.recomendar()
        self.assertEqual([c['id'] for c in r['ranking']], ['libre'])
        self.assertEqual([(e['id'], e['motivo']) for e in r['en_espera']], [('bloqueada', 'falta una revisión humana')])
        self.assertIn(('ya-hecha', 'ya está construida'), [(e['id'], e['motivo']) for e in r['excluidas']])
        self.assertIn('falta una revisión humana', '\n'.join(rumbo.informe(r)))

    def test_lo_parecido_se_penaliza_y_se_avisa_que_no_es_apto_para_portales(self):
        # mismo género y verbo que Guerreros, otro objetivo: no es variante, pero tampoco es un juego distinto
        self.ideas([idea('parecida', 'simulador-batalla', 'colocar', 'sobrevivir', ['toque'], 'niveles-con-oro'),
                    idea('distinta', 'ritmo', 'cronometrar', 'puntaje-maximo', ['toque'], 'niveles-con-oro')])
        r = self.recomendar()
        por_id = {c['id']: c for c in r['ranking']}
        self.assertEqual((por_id['parecida']['novedad'], por_id['distinta']['novedad']), ('parecido', 'distinto'))
        self.assertEqual(por_id['parecida']['factores']['novedad'], met.cargar_politica(self.raiz)['rumbo']['factor_novedad']['parecido'])
        self.assertLess(por_id['parecida']['puntaje'], por_id['distinta']['puntaje'])
        self.assertIn('no apta para portales', '\n'.join(rumbo.informe(r)))

    def test_poca_evidencia_no_cambia_el_modo_y_se_dice_que_falta(self):
        self.ideas([IDEA_COMO_GUERREROS, IDEA_COMO_TORRE])
        self.tres_semanas(JUEGO, 300)
        self.tres_semanas(TORRE, 50)                               # 150 vistas: menos del mínimo
        r = self.recomendar()
        self.assertEqual(r['modo'], 'explorar')
        self.assertTrue(r['datos'][JUEGO]['medible'])
        self.assertFalse(r['datos'][TORRE]['medible'])
        self.assertIn('faltan 50 vistas', ' '.join(r['datos'][TORRE]['faltan']))
        self.assertIn('faltan 50 vistas del juego', '\n'.join(rumbo.informe(r)))

    def test_pocas_semanas_tampoco_bastan_aunque_haya_muchas_vistas(self):
        self.vistas(JUEGO, [('2026-11-09', 5000), ('2026-11-16', 5000)])
        self.vistas(TORRE, [('2026-11-09', 5000), ('2026-11-16', 5000)])
        r = self.recomendar()
        self.assertEqual(r['modo'], 'explorar')
        self.assertIn('faltan 1 semana', ' '.join(r['datos'][JUEGO]['faltan']))

    def test_la_semana_en_curso_no_cuenta(self):
        self.tres_semanas(JUEGO, 300)
        self.anota(JUEGO, 'vistas_juego', 100000, '2026-11-23')              # la semana de HOY, sin terminar
        d = self.recomendar()['datos'][JUEGO]
        self.assertEqual((d['semanas'], d['vistas_juego']), (3, 900))

    def test_los_ceros_antes_del_primer_dia_con_visitas_no_cuentan_como_semanas_de_exposicion(self):
        self.vistas(JUEGO, [('2026-10-26', 0), ('2026-11-02', 0), ('2026-11-09', 300), ('2026-11-16', 300)])
        d = self.recomendar()['datos'][JUEGO]
        self.assertEqual((d['semanas'], d['vistas_juego']), (2, 600))

    def test_con_evidencia_suficiente_aprende_y_las_ideas_cercanas_al_juego_que_funciono_suben(self):
        self.ideas([IDEA_COMO_TORRE, IDEA_COMO_GUERREROS])
        self.tres_semanas(JUEGO, 300)
        self.tres_semanas(TORRE, 100)
        r = self.recomendar()
        self.assertEqual(r['modo'], 'aprender')
        self.assertGreater(r['puntajes'][JUEGO]['puntaje'], 1)
        self.assertLess(r['puntajes'][TORRE]['puntaje'], 1)
        self.assertEqual([c['id'] for c in r['ranking']], ['cercana-a-guerreros', 'cercana-a-torre'])

    def test_si_los_datos_se_invierten_se_invierte_el_orden(self):
        self.ideas([IDEA_COMO_GUERREROS, IDEA_COMO_TORRE])
        self.tres_semanas(JUEGO, 100)
        self.tres_semanas(TORRE, 300)
        self.assertEqual([c['id'] for c in self.recomendar()['ranking']], ['cercana-a-torre', 'cercana-a-guerreros'])

    def test_el_puntaje_se_suaviza_hacia_el_promedio_con_poca_evidencia(self):
        self.tres_semanas(JUEGO, 70)                               # 210 vistas
        self.tres_semanas(TORRE, 67)                               # 201 vistas: casi iguales
        p = self.recomendar()['puntajes']
        self.assertAlmostEqual(p[JUEGO]['puntaje'], 1.0, delta=0.05)
        self.assertAlmostEqual(p[TORRE]['puntaje'], 1.0, delta=0.05)

    def test_la_difusion_se_descuenta_para_no_premiar_a_un_juego_solo_por_haberse_anunciado_mas(self):
        self.tres_semanas(JUEGO, 300)
        self.tres_semanas(TORRE, 300)
        base = self.recomendar()['puntajes']
        self.assertAlmostEqual(base[JUEGO]['puntaje'], base[TORRE]['puntaje'], places=9)
        libro = [{'ts': '2026-11-03T15:00:00Z', 'resultado': 'ok', 'canal': 'bluesky', 'juego': JUEGO},
                 {'ts': '2026-11-04T15:00:00Z', 'resultado': 'ok', 'canal': 'mastodon', 'juego': JUEGO},
                 {'ts': '2026-11-05T15:00:00Z', 'resultado': 'ok', 'canal': 'sitio-propio', 'juego': JUEGO},       # el sitio no es empuje
                 {'ts': '2026-11-06T15:00:00Z', 'resultado': 'fallo', 'canal': 'bluesky', 'juego': JUEGO}]          # lo que no salió tampoco
        con = self.recomendar(libro)
        self.assertEqual(con['datos'][JUEGO]['empuje'], 2)
        self.assertLess(con['puntajes'][JUEGO]['puntaje'], con['puntajes'][TORRE]['puntaje'])

    def test_aceptacion_y_apoyo_solo_cuentan_cuando_hay_con_que_compararlos(self):
        pol = met.cargar_politica(self.raiz)

        def d(jid, pos, neg, dinero):
            return {'id': jid, 'medible': True, 'vistas_juego': 500, 'exposicion': 4, 'pos': pos, 'neg': neg, 'dinero': dinero}
        solo_alcance = rumbo.puntajes({'a': d('a', 3, 1, 0), 'b': d('b', 2, 2, 0)}, pol)               # menos de 10 comentarios y nadie pagó nada
        self.assertEqual(set(solo_alcance['a']['componentes']), {'alcance'})
        completo = rumbo.puntajes({'a': d('a', 18, 2, 5.0), 'b': d('b', 10, 10, 0)}, pol)
        self.assertEqual(set(completo['a']['componentes']), {'alcance', 'aceptacion', 'apoyo'})
        self.assertGreater(completo['a']['componentes']['aceptacion'], 1)
        self.assertLess(completo['b']['componentes']['aceptacion'], 1)
        self.assertGreater(completo['a']['componentes']['apoyo'], completo['b']['componentes']['apoyo'])
        uno_con_comentarios = rumbo.puntajes({'a': d('a', 18, 2, 0), 'b': d('b', 2, 2, 0)}, pol)
        self.assertNotIn('aceptacion', uno_con_comentarios['a']['componentes'])                          # con un solo juego no hay contra qué comparar

    def test_el_informe_no_lleva_fechas_ni_claves(self):
        self.ideas([IDEA_COMO_GUERREROS])
        self.tres_semanas(JUEGO, 300)
        self.tres_semanas(TORRE, 100)
        texto = '\n'.join(rumbo.informe(self.recomendar(), detalle=True))
        self.assertNotRegex(texto, r'\d{4}-\d\d-\d\d')
        for valor in list(SECRETOS.values()) + [TOKEN_CF, CUENTA_CF]:
            self.assertNotIn(valor, texto)
        self.assertIn('Recomendar no es lanzar', texto)

    def test_datos_de_cloudflare_con_el_sitio_diciendo_que_no_hay_analitica_se_avisa(self):
        self.tres_semanas(JUEGO, 300)
        self.assertTrue(any('no declara `"analitica": "cloudflare"`' in a for a in self.recomendar()['avisos']))
        self.p.editar('publicacion/sitio.json', lambda d: d.update(analitica='cloudflare'))
        self.assertFalse(any('analitica' in a for a in self.recomendar()['avisos']))

    def test_datos_manuales_no_disparan_el_aviso_de_analitica(self):
        self.anota(JUEGO, 'comentarios_pos', 3, '2026-11-09', 'manual')
        self.assertFalse(any('analitica' in a for a in self.recomendar()['avisos']))


class PruebasMetricasEnLaFabrica(BaseMetricas):
    def fabrica(self, *args, env=None):
        e = {'PYTHONHASHSEED': '5', 'PATH': '/usr/bin:/bin'}
        e.update(env or {})
        return subprocess.run([sys.executable, '-I', str(self.raiz / 'fabrica.py'), *args], capture_output=True, text=True, env=e, cwd=str(self.raiz))

    def test_anotar_ver_y_rumbo_desde_la_linea_de_comandos(self):
        r = self.fabrica('metricas', 'anotar', JUEGO, 'vistas_juego', '123', '--semana', '2026-11-09', '--fuente', 'itch', '--nota', 'de itch')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('Anotado: 2026-11-09', r.stdout)
        r = self.fabrica('metricas', 'ver')
        self.assertIn('123', r.stdout)
        r = self.fabrica('rumbo')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Recomendación, en orden', r.stdout)

    def test_un_dato_malo_sale_con_codigo_distinto_de_cero_y_sin_escribir(self):
        r = self.fabrica('metricas', 'anotar', JUEGO, 'vistas_juego', 'mucho')
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(met.leer(self.raiz, IDS), [])

    def test_importar_de_cloudflare_es_opcional_sin_secretos_pero_manual_los_exige(self):
        r = self.fabrica('metricas', 'cloudflare', '--opcional')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('es opcional', r.stdout)
        r = self.fabrica('metricas', 'cloudflare')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('faltan', r.stdout + r.stderr)

    def test_el_ciclo_incluye_el_rumbo_y_un_registro_roto_lo_hace_fallar_a_la_vista(self):
        r = self.fabrica('ciclo')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        texto = (self.raiz / 'publicacion' / 'PENDIENTE.md').read_text(encoding='utf-8')
        self.assertIn('## Qué construir después', texto)
        self.assertIn('Todavía no hay datos para decidir por métricas', texto)
        (self.raiz / 'metricas' / 'registro.csv').write_text(','.join(met.ENCABEZADO) + '\nfecha-mala,%s,vistas_juego,1,manual,\n' % JUEGO, encoding='utf-8')
        r = self.fabrica('ciclo')
        self.assertNotEqual(r.returncode, 0)
        texto = (self.raiz / 'publicacion' / 'PENDIENTE.md').read_text(encoding='utf-8')
        self.assertIn('No se pudo calcular el rumbo', texto)
        self.assertIn('línea 2', texto)
        self.assertIn('## %s (v' % JUEGO, texto)                         # el resto del estado se escribe igual

    def test_el_flujo_semanal_usa_las_claves_que_el_codigo_lee_y_guarda_el_registro(self):
        texto = (RAIZ / '.github' / 'workflows' / 'ciclo.yml').read_text(encoding='utf-8')
        self.assertEqual(set(re.findall(r'\$\{\{ secrets\.(\w+) \}\}', texto)), {met.VARIABLE_TOKEN, met.VARIABLE_CUENTA})
        self.assertIn('metricas cloudflare --opcional', texto)
        self.assertIn('git add publicacion/PENDIENTE.md metricas/registro.csv', texto)
        self.assertIn('continue-on-error: true', texto)                       # un token vencido no debe apagar el latido semanal
        guia = (RAIZ / 'LEEME-DUENO.md').read_text(encoding='utf-8')
        for clave in (met.VARIABLE_TOKEN, met.VARIABLE_CUENTA, 'Account Analytics'):
            self.assertIn(clave, guia)


class PruebasAnaliticaEnElSitio(BaseMetricas):
    def privacidad(self, idioma):
        self.p.regenerar_sitio()
        return (self.raiz / 'dist' / 'sitio' / idioma / 'privacidad' / 'index.html').read_text(encoding='utf-8')

    def test_por_defecto_el_sitio_dice_que_no_usa_analitica(self):
        self.assertNotIn('analitica', json.loads((self.raiz / 'publicacion' / 'sitio.json').read_text(encoding='utf-8')))
        self.assertIn('herramientas de análisis', self.privacidad('es'))
        self.assertNotIn('Cloudflare Web Analytics', self.privacidad('es'))

    def test_con_cloudflare_la_privacidad_lo_dice_en_los_tres_idiomas_y_no_afirma_lo_contrario(self):
        self.p.editar('publicacion/sitio.json', lambda d: d.update(analitica='cloudflare'))
        for idioma, frase_que_ya_no_debe_estar in (('es', 'herramientas de análisis'), ('en', 'analytics tools'), ('zh', '不使用统计分析工具')):
            h = self.privacidad(idioma)
            self.assertIn('Cloudflare Web Analytics', h, idioma)
            self.assertNotIn(frase_que_ya_no_debe_estar, h, idioma)

    def test_con_anuncios_y_analitica_salen_los_dos_parrafos(self):
        self.p.editar('publicacion/sitio.json', lambda d: d.update(analitica='cloudflare', adsense_publisher='pub-1234567890123456'))
        h = self.privacidad('es')
        self.assertIn('AdSense', h)
        self.assertIn('Cloudflare Web Analytics', h)

    def test_un_valor_desconocido_de_analitica_detiene_la_generacion(self):
        self.p.editar('publicacion/sitio.json', lambda d: d.update(analitica='otra-herramienta'))
        with self.assertRaises(gen.ErrorSitio):
            self.p.regenerar_sitio()

    def test_la_analitica_no_cambia_nada_del_resto_del_sitio(self):
        self.p.regenerar_sitio()
        antes = {str(r.relative_to(self.raiz / 'dist' / 'sitio')): r.read_bytes() for r in (self.raiz / 'dist' / 'sitio').rglob('*') if r.is_file()}
        self.p.editar('publicacion/sitio.json', lambda d: d.update(analitica='cloudflare'))
        self.p.regenerar_sitio()
        despues = {str(r.relative_to(self.raiz / 'dist' / 'sitio')): r.read_bytes() for r in (self.raiz / 'dist' / 'sitio').rglob('*') if r.is_file()}
        self.assertEqual(sorted(k for k in antes if antes[k] != despues.get(k)), ['en/privacidad/index.html', 'es/privacidad/index.html', 'zh/privacidad/index.html'])


if __name__ == '__main__':
    unittest.main()
