"""Perfiles de las cuentas de difusión: avatar, banner y textos (nombre, biografía, campos) para Bluesky, Mastodon y el canal de Telegram.

Todo sale de publicacion/sitio.json (nombre, dirección, idiomas), así que cambiar la marca cambia los perfiles.
Las cuentas son de bot y lo dicen en su biografía; la fábrica no responde, no sigue y no menciona a nadie (ver LEEME-DUENO.md).

  python3 fabrica.py perfiles          escribe difusion/perfiles/{avatar.png, banner.png, perfiles.json, perfiles.md}
  python3 fabrica.py perfiles --texto  solo los textos (no necesita navegador)

Los límites de cada red se comprobaron en sus páginas oficiales o en el esquema público del protocolo el 15 de noviembre de 2026
(Bluesky: nombre 64 y biografía 256 grafemas; Mastodon: nombre 30, biografía 500 y 4 campos —el límite puede variar según el servidor—;
Telegram: título 128 y descripción 255). Si un texto no cabe, este módulo se niega a escribir en lugar de dejar que la red lo corte.
"""
import json
import pathlib
import re
import subprocess
import sys
import unicodedata

LIMITES = {
    'bluesky': {'nombre': 64, 'bio': 256},
    'mastodon': {'nombre': 30, 'bio': 500, 'campos': 4, 'campo': 255},
    'telegram': {'nombre': 128, 'bio': 255},
}
PESO_MAXIMO_IMAGEN = 1_000_000          # Bluesky admite hasta 1 MB por avatar y por banner; Mastodon, 2 MB

TEXTOS = {
    'es': {
        'nombre_visible': '{nombre} (bot)',
        'bluesky': 'Cuenta automatizada (bot) de {nombre}: avisa de juegos y versiones nuevas. Juegos chiquitos, gratis y con delirios de grandeza, hechos con ayuda de IA. No responde ni sigue cuentas; contacto en el sitio: {url}',
        'mastodon': 'Cuenta automatizada (bot) de {nombre}. Publica avisos de juegos nuevos y de versiones nuevas: juegos gratis para el navegador, sin descargas, hechos con ayuda de inteligencia artificial. No responde mensajes, no sigue cuentas y no impulsa publicaciones. Todos los juegos y el contacto están en {url}',
        'telegram_titulo': '{nombre} · Juegos gratis',
        'telegram': 'Avisos automáticos de {nombre}: juegos nuevos y versiones nuevas. Juegos gratis para el navegador, hechos con ayuda de IA. Canal publicado por un bot. Juegos y contacto: {url}',
        'campos': [('Web', '{url}'), ('Cuenta', 'Automatizada (bot)'), ('Hecho con', 'Ayuda de IA'), ('Idiomas', 'Español · English · 中文')],
        'banner': ['Juegos chiquitos, gratis y con delirios de grandeza.', 'Tiny games, free and with delusions of grandeur.'],
    },
    'en': {
        'nombre_visible': '{nombre} (bot)',
        'bluesky': 'Automated account (bot) of {nombre}: announces new games and versions. Tiny games, free and with delusions of grandeur, made with the help of AI. It does not reply or follow accounts; contact is on the site: {url}',
        'mastodon': 'Automated account (bot) of {nombre}. It posts announcements of new games and new versions: free browser games, no downloads, made with the help of artificial intelligence. It does not reply to messages, follow accounts or boost posts. All the games and the contact are at {url}',
        'telegram_titulo': '{nombre} · Free games',
        'telegram': 'Automatic announcements from {nombre}: new games and new versions. Free browser games, made with the help of AI. Channel published by a bot. Games and contact: {url}',
        'campos': [('Web', '{url}'), ('Account', 'Automated (bot)'), ('Made with', 'AI help'), ('Languages', 'Español · English · 中文')],
        'banner': ['Tiny games, free and with delusions of grandeur.', 'Juegos chiquitos, gratis y con delirios de grandeza.'],
    },
    'zh': {
        'nombre_visible': '{nombre}（机器人）',
        'bluesky': '{nombre} 的自动账号（机器人）：发布新游戏和新版本的通知。小小的游戏，免费，却野心满满，借助人工智能制作。不回复也不关注账号；联系方式在网站上：{url}',
        'mastodon': '{nombre} 的自动账号（机器人）。发布新游戏和新版本的通知：免费网页游戏，无需下载，借助人工智能制作。不回复消息，不关注账号，不转发帖子。所有游戏和联系方式见 {url}',
        'telegram_titulo': '{nombre} · 免费游戏',
        'telegram': '{nombre} 的自动通知：新游戏和新版本。免费网页游戏，借助人工智能制作。本频道由机器人发布。游戏和联系方式：{url}',
        'campos': [('网站', '{url}'), ('账号', '自动账号（机器人）'), ('制作方式', '借助人工智能'), ('语言', 'Español · English · 中文')],
        'banner': ['Tiny games, free and with delusions of grandeur.', 'Juegos chiquitos, gratis y con delirios de grandeza.'],
    },
}


class ErrorPerfiles(Exception):
    pass


def largo(texto):
    """Longitud como la cuentan las redes: caracteres, sin emojis ni marcas combinadas en estos textos."""
    return len(unicodedata.normalize('NFC', texto))


def _datos(raiz):
    raiz = pathlib.Path(raiz)
    cfg = json.loads((raiz / 'publicacion' / 'sitio.json').read_text(encoding='utf-8'))
    politica = json.loads((raiz / 'publicacion' / 'politica.json').read_text(encoding='utf-8'))
    nombre, url = str(cfg.get('nombre', '')).strip(), str(cfg.get('url_base', '')).rstrip('/')
    if not nombre or not url.startswith('https://') or 'CAMBIA-ESTE-NOMBRE' in url + nombre:
        raise ErrorPerfiles('«nombre» y «url_base» de publicacion/sitio.json deben ser los reales antes de escribir los perfiles.')
    return cfg, politica, nombre, url


def _usuario(cfg):
    base = re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', str(cfg.get('proyecto') or cfg.get('nombre', ''))).encode('ascii', 'ignore').decode().lower())
    return base or 'juegos'


def textos(raiz):
    """Todos los textos por red e idioma, ya con la marca y la dirección; falla si alguno no cabe en su red."""
    cfg, politica, nombre, url = _datos(raiz)
    usuario = _usuario(cfg)
    idiomas = politica.get('idioma', {})
    salida = {'nombre': nombre, 'url': url, 'redes': {}}
    errores = []

    def poner(s):
        return s.replace('{nombre}', nombre).replace('{url}', url)

    def comprobar(red, campo, idioma, texto, limite):
        if largo(texto) > limite:
            errores.append('%s · %s · %s: %d caracteres, el límite es %d' % (red, campo, idioma, largo(texto), limite))
    for red, clave_bio, clave_nombre, clave_idioma, usuario_sugerido in (
            ('bluesky', 'bluesky', 'nombre_visible', 'bluesky', usuario + '.bsky.social'),
            ('mastodon', 'mastodon', 'nombre_visible', 'mastodon', usuario),
            ('telegram', 'telegram', 'telegram_titulo', 'telegram-canal', '@' + usuario)):
        lim = LIMITES[red]
        datos = {'idioma_recomendado': idiomas.get(clave_idioma, 'es'), 'usuario_sugerido': usuario_sugerido, 'limites': lim, 'nombre_visible': {}, 'bio': {}}
        for l, t in TEXTOS.items():
            datos['nombre_visible'][l] = poner(t[clave_nombre])
            datos['bio'][l] = poner(t[clave_bio])
            comprobar(red, 'nombre', l, datos['nombre_visible'][l], lim['nombre'])
            comprobar(red, 'biografía', l, datos['bio'][l], lim['bio'])
        if red == 'mastodon':
            datos['campos'] = {}
            for l, t in TEXTOS.items():
                campos = [(poner(a), poner(b)) for a, b in t['campos']]
                if len(campos) > lim['campos']:
                    errores.append('mastodon · campos · %s: %d campos, el límite es %d' % (l, len(campos), lim['campos']))
                for a, b in campos:
                    comprobar(red, 'campo «%s»' % a, l, a, lim['campo'])
                    comprobar(red, 'campo «%s»' % a, l, b, lim['campo'])
                datos['campos'][l] = [list(c) for c in campos]
        salida['redes'][red] = datos
    if errores:
        raise ErrorPerfiles('Hay textos que no caben en su red:\n  ' + '\n  '.join(errores))
    return salida


def markdown(datos):
    nombres = {'es': 'Español', 'en': 'English', 'zh': '中文'}
    L = ['# Perfiles de las cuentas de difusión', '',
         'Texto listo para copiar en cada red, generado por `python3 fabrica.py perfiles` a partir de `publicacion/sitio.json`. '
         'Las tres cuentas son **de bot y lo dicen**: no cambies la biografía para quitar esa frase. '
         'El idioma recomendado es el de `publicacion/politica.json` (en el que publicará la cuenta); los otros dos quedan por si quieres cambiarlo.', '',
         'Imágenes: `avatar.png` (cuadrada; las redes la recortan en círculo o con esquinas redondeadas) y `banner.png` (proporción 3:1; Bluesky y Mastodon). Telegram solo usa la foto del canal: sube `avatar.png`.', '']
    titulos = {'bluesky': 'Bluesky', 'mastodon': 'Mastodon', 'telegram': 'Canal de Telegram'}
    for red in ('bluesky', 'mastodon', 'telegram'):
        d = datos['redes'][red]
        lim = d['limites']
        L += ['## %s' % titulos[red], '',
              '- Usuario sugerido (si está libre): `%s`' % d['usuario_sugerido'],
              '- Idioma recomendado: **%s**' % nombres.get(d['idioma_recomendado'], d['idioma_recomendado']),
              '- Límites: nombre %d, %s %d caracteres%s.' % (lim['nombre'], 'descripción' if red == 'telegram' else 'biografía', lim['bio'],
                                                           ' (puede variar según el servidor de Mastodon), %d campos' % lim['campos'] if red == 'mastodon' else ''), '']
        for l in ('es', 'en', 'zh'):
            marca = ' (recomendado)' if l == d['idioma_recomendado'] else ''
            L += ['### %s%s' % (nombres[l], marca), '',
                  '**%s:**' % ('Título del canal' if red == 'telegram' else 'Nombre visible'), '', '```', d['nombre_visible'][l], '```', '',
                  '**%s:**' % ('Descripción' if red == 'telegram' else 'Biografía'), '', '```', d['bio'][l], '```', '']
            if red == 'mastodon':
                L += ['**Campos del perfil (etiqueta → contenido):**', ''] + ['- %s → %s' % (a, b) for a, b in d['campos'][l]] + ['']
    return '\n'.join(L).rstrip() + '\n'


def _fuentes(raiz):
    """Los @font-face de Fredoka y Nunito Sans que ya vienen incrustados en los juegos (así no se descarga nada)."""
    for p in sorted((pathlib.Path(raiz) / 'salida').glob('*/index.html')):
        t = p.read_text(encoding='utf-8')
        bloques = re.findall(r'@font-face\s*\{[^}]*\}', t)
        elegidos = [b for b in bloques if re.search(r"font-family:\s*'Fredoka'", b) and re.search(r'font-weight:\s*700', b)] + \
                   [b for b in bloques if re.search(r"font-family:\s*'Nunito Sans'", b) and re.search(r'font-weight:\s*700', b)]
        if len(elegidos) == 2:
            return '\n'.join(elegidos)
    raise ErrorPerfiles('No encontré las tipografías en salida/*/index.html: construye un juego primero (python3 fabrica.py construir).')


def gelatina(cx, cy, escala, claro, oscuro, id_, cachete='#ffc2d8'):
    """Una gelatina con cara, dibujada con trazos propios (no copia ningún personaje)."""
    return (
        "<g transform='translate(%s %s) scale(%s)'>"
        "<defs><linearGradient id='g%s' x1='0' y1='-1' x2='0' y2='1'><stop offset='0' stop-color='%s'/><stop offset='1' stop-color='%s'/></linearGradient></defs>"
        "<ellipse cx='0' cy='106' rx='96' ry='13' fill='#14251b' opacity='.14'/>"
        "<path d='M-102 62 C-114 -22 -72 -92 0 -92 C72 -92 114 -22 102 62 C99 88 70 102 0 102 C-70 102 -99 88 -102 62 Z' fill='url(#g%s)'/>"
        "<path d='M-102 62 C-99 88 -70 102 0 102 C70 102 99 88 102 62 C80 80 -80 80 -102 62 Z' fill='#14251b' opacity='.10'/>"
        "<ellipse cx='-48' cy='-50' rx='30' ry='14' transform='rotate(-35 -48 -50)' fill='#fff' opacity='.55'/>"
        "<circle cx='-80' cy='-6' r='5' fill='#fff' opacity='.5'/>"
        "<ellipse cx='-33' cy='6' rx='16' ry='19' fill='#fff'/><ellipse cx='33' cy='6' rx='16' ry='19' fill='#fff'/>"
        "<circle cx='-30' cy='10' r='9' fill='#14251b'/><circle cx='36' cy='10' r='9' fill='#14251b'/>"
        "<circle cx='-27' cy='6' r='3' fill='#fff'/><circle cx='39' cy='6' r='3' fill='#fff'/>"
        "<ellipse cx='-58' cy='38' rx='11' ry='7' fill='%s' opacity='.8'/><ellipse cx='58' cy='38' rx='11' ry='7' fill='%s' opacity='.8'/>"
        "<path d='M-15 42 Q0 56 15 42' fill='none' stroke='#14251b' stroke-width='5' stroke-linecap='round'/>"
        "</g>" % (cx, cy, escala, id_, claro, oscuro, id_, cachete, cachete))


FONDO = 'radial-gradient(circle at 30% 25%, #fff6fa 0%, #fbf8f1 45%, #f3d6e4 100%)'


def _html(cuerpo, fuentes, ancho, alto):
    return ("<!doctype html><meta charset='utf-8'><style>%s html,body{margin:0;padding:0;width:%dpx;height:%dpx;overflow:hidden;background:%s}"
            "*{box-sizing:border-box}</style>%s" % (fuentes, ancho, alto, FONDO, cuerpo))


def html_avatar(fuentes):
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='800' height='800' viewBox='0 0 800 800'>%s</svg>"
           % gelatina(400, 390, 2.3, '#6fe0a6', '#15804f', 'a'))
    return _html(svg, fuentes, 800, 800)


def html_banner(fuentes, nombre, linea1, linea2):
    esc = lambda s: s.replace('&', '&amp;').replace('<', '&lt;')
    jaleas = (gelatina(1190, 262, 1.45, '#6fe0a6', '#15804f', 'v') + gelatina(950, 345, .8, '#ff9cc4', '#c2337a', 'r', '#ff6f9f') +
              gelatina(1385, 340, .72, '#ffd36b', '#e39a00', 'a', '#ff9f80'))
    svg = "<svg xmlns='http://www.w3.org/2000/svg' width='1500' height='500' viewBox='0 0 1500 500' style='position:absolute;left:0;top:0'>%s</svg>" % jaleas
    texto = ("<div style=\"position:absolute;left:92px;top:118px;width:760px\">"
             "<div style=\"font:700 112px/1.05 'Fredoka',sans-serif;color:#c2337a;letter-spacing:-1px\">%s</div>"
             "<div style=\"margin-top:22px;font:700 40px/1.2 'Nunito Sans',sans-serif;color:#1c2a23;text-wrap:balance\">%s</div>"
             "<div style=\"margin-top:6px;font:700 30px/1.2 'Nunito Sans',sans-serif;color:#4d5f55\">%s</div></div>" % (esc(nombre), esc(linea1), esc(linea2)))
    return _html(svg + texto, fuentes, 1500, 500)


def _dibujar(raiz, html, salida, ancho, alto, tipo='png'):
    tmp = pathlib.Path(raiz) / 'dist' / 'tmp-perfiles'
    tmp.mkdir(parents=True, exist_ok=True)
    pagina = tmp / (pathlib.Path(salida).stem + '.html')
    pagina.write_text(html, encoding='utf-8')
    r = subprocess.run(['node', str(pathlib.Path(raiz) / 'herramientas' / 'perfiles.js'), str(pagina), str(salida), str(ancho), str(alto), tipo],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise ErrorPerfiles('No pude dibujar %s (necesita node y playwright): %s' % (pathlib.Path(salida).name, (r.stderr or r.stdout).strip()[:300]))


def imagenes(raiz):
    raiz = pathlib.Path(raiz)
    cfg, _, nombre, _ = _datos(raiz)
    destino = raiz / 'difusion' / 'perfiles'
    destino.mkdir(parents=True, exist_ok=True)
    fuentes = _fuentes(raiz)
    textos_banner = TEXTOS['es']['banner']
    _dibujar(raiz, html_avatar(fuentes), destino / 'avatar.png', 800, 800)
    _dibujar(raiz, html_banner(fuentes, nombre, textos_banner[0], textos_banner[1]), destino / 'banner.png', 1500, 500)
    for n in ('avatar.png', 'banner.png'):
        peso = (destino / n).stat().st_size
        if peso > PESO_MAXIMO_IMAGEN:
            raise ErrorPerfiles('%s pesa %d bytes: Bluesky admite hasta %d.' % (n, peso, PESO_MAXIMO_IMAGEN))
    return [destino / 'avatar.png', destino / 'banner.png']


def generar(raiz, con_imagenes=True):
    raiz = pathlib.Path(raiz)
    datos = textos(raiz)
    destino = raiz / 'difusion' / 'perfiles'
    destino.mkdir(parents=True, exist_ok=True)
    (destino / 'perfiles.json').write_text(json.dumps(datos, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    (destino / 'perfiles.md').write_text(markdown(datos), encoding='utf-8')
    escritos = [destino / 'perfiles.json', destino / 'perfiles.md']
    if con_imagenes:
        escritos += imagenes(raiz)
    return escritos


def main(argv):
    try:
        escritos = generar(pathlib.Path(__file__).resolve().parent.parent, con_imagenes='--texto' not in argv)
    except ErrorPerfiles as e:
        sys.exit('[perfiles] %s' % e)
    for e in escritos:
        print('[perfiles] escrito %s' % e.relative_to(pathlib.Path(__file__).resolve().parent.parent))
