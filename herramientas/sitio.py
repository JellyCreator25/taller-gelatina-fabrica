"""Generador del sitio propio: páginas en español, inglés y chino, una por juego, con el juego embebido en /jugar/<id>/.

Qué escribe (en dist/sitio/, listo para Cloudflare Pages) y por qué:
  /                       elige idioma (con JavaScript va solo al del navegador; sin JavaScript se ven los tres enlaces)
  /<idioma>/              portada del sitio con los juegos de sitio.json → juegos
  /<idioma>/juegos/<id>/  página de cada juego: descripción, controles, capturas, enlace «Jugar», datos para buscadores (hreflang, Open Graph, JSON-LD)
  /jugar/<id>/            el juego tal como lo construyó la fábrica (salida/<id>/index.html) sin tocar; acepta ?lang=xx
  /<idioma>/privacidad/   política de privacidad corta y veraz para este sitio
  /404.html               imprescindible: sin él Cloudflare Pages responde con la portada ante cualquier dirección que no exista
  sitemap.xml, robots.txt, _headers, <clave>.txt (IndexNow), ads.txt (solo si hay editor de AdSense en sitio.json)
Es determinista: dos corridas con las mismas entradas dan los mismos bytes (la huella de aprobación depende de eso). Por eso no hay fechas de
«hoy», ni conjuntos sin ordenar, ni imágenes recomprimidas: los medios se copian tal cual desde salida/<id>/medios/.
Las páginas no listan variantes de un mismo juego: solo los juegos de sitio.json → juegos, que es la decisión explícita de lanzarlos."""
import hashlib
import html
import json
import pathlib
import re
import shutil
import struct
import sys

IDIOMA_ETIQUETA = {'zh': 'zh-Hans'}      # atributo lang y hreflang (chino simplificado)
OG_LOCALE = {'es': 'es_LA', 'en': 'en_US', 'zh': 'zh_CN'}


class ErrorSitio(Exception):
    pass


def etiqueta(idioma):
    return IDIOMA_ETIQUETA.get(idioma, idioma)


def _e(s):
    return html.escape(str(s), quote=True)


def _json_ld(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True).replace('</', '<\\/')


def _cadenas(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from _cadenas(v)
    elif isinstance(o, list):
        for v in o:
            yield from _cadenas(v)


# ---------------------------------------------------------------------------------------------------------------------
# Texto: el pequeño subconjunto de Markdown que usan las fichas (párrafos, listas con «- » y títulos en **negrita**)
# ---------------------------------------------------------------------------------------------------------------------

def _en_linea(s):
    return re.sub(r'\*\*(.+?)\*\*', lambda m: '<strong>%s</strong>' % m.group(1), _e(s))


def md(texto):
    salida = []
    for bloque in re.split(r'\n\s*\n', str(texto).strip()):
        lineas = [l for l in bloque.split('\n') if l.strip()]
        if not lineas:
            continue
        if all(l.startswith('- ') for l in lineas):
            salida.append('<ul>%s</ul>' % ''.join('<li>%s</li>' % _en_linea(l[2:]) for l in lineas))
        elif len(lineas) == 1 and re.fullmatch(r'\*\*[^*]+\*\*', lineas[0].strip()):
            salida.append('<h3>%s</h3>' % _e(lineas[0].strip()[2:-2]))
        else:
            salida.append('<p>%s</p>' % '<br>'.join(_en_linea(l) for l in lineas))
    return '\n'.join(salida)


def dimensiones(ruta):
    """(ancho, alto) de un PNG o JPEG leyendo solo la cabecera; None si no se reconoce."""
    b = pathlib.Path(ruta).read_bytes()
    if b[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>II', b[16:24])
    if b[:2] == b'\xff\xd8':
        i = 2
        while i + 9 < len(b):
            if b[i] != 0xFF:
                i += 1
                continue
            m = b[i + 1]
            if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7 or m == 0xFF:
                i += 1 if m == 0xFF else 2
                continue
            if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                alto, ancho = struct.unpack('>HH', b[i + 5:i + 9])
                return ancho, alto
            i += 2 + struct.unpack('>H', b[i + 2:i + 4])[0]
    return None


# ---------------------------------------------------------------------------------------------------------------------
# Estilos
# ---------------------------------------------------------------------------------------------------------------------

CSS = """:root{--bg:#fbf8f1;--fg:#1c2a23;--mut:#4d5f55;--card:#ffffff;--line:#e2dac8;--acc:#15804f;--acc-fg:#ffffff;--link:#0c6b42;--marca:#c2337a;--foco:#0b5fff;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#101912;--fg:#e8f1ea;--mut:#a5b8ac;--card:#17231b;--line:#2a3b30;--acc:#4cc58c;--acc-fg:#08150d;--link:#7fe0b0;--marca:#ff8ab8;--foco:#8ab4ff;color-scheme:dark}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans SC",sans-serif;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
a{color:var(--link)}
a:focus-visible,button:focus-visible{outline:3px solid var(--foco);outline-offset:2px;border-radius:4px}
.envoltura{max-width:960px;margin:0 auto}
header.alto{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px 24px;padding:20px 0 8px}
.marca{font-weight:800;font-size:1.25rem;text-decoration:none;color:var(--marca);letter-spacing:.01em}
.idiomas{display:flex;flex-wrap:wrap;gap:4px}
.idiomas a{display:inline-block;padding:6px 12px;border:1px solid var(--line);border-radius:999px;text-decoration:none;color:var(--fg);font-size:.9rem;background:var(--card)}
.idiomas a[aria-current=page]{background:var(--acc);border-color:var(--acc);color:var(--acc-fg);font-weight:700}
main{padding:12px 0 40px}
h1{font-size:clamp(1.8rem,5vw,2.6rem);line-height:1.15;margin:16px 0 8px;text-wrap:balance}
h2{font-size:1.35rem;margin:32px 0 8px}
h3{font-size:1.1rem;margin:24px 0 4px}
.lema,.corta{color:var(--mut);font-size:1.15rem;max-width:42em;margin:0 0 20px}
.migas{margin:8px 0 0;font-size:.95rem}
.boton{display:inline-block;background:var(--acc);color:var(--acc-fg);font-weight:800;font-size:1.15rem;padding:12px 28px;border-radius:14px;text-decoration:none;min-height:44px}
.boton:hover{filter:brightness(1.06)}
.rejilla{list-style:none;margin:20px 0 0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,280px),1fr));gap:20px}
.tarjeta{background:var(--card);border:1px solid var(--line);border-radius:18px;overflow:hidden;display:flex;flex-direction:column;min-width:0}
.tarjeta img{display:block;width:100%;height:auto;background:var(--line)}
.tarjeta .cuerpo{padding:16px 18px 20px;display:flex;flex-direction:column;gap:8px;flex:1}
.tarjeta h2{margin:0;font-size:1.25rem}
.tarjeta p{margin:0;color:var(--mut);font-size:.98rem}
.tarjeta .acciones{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;margin-top:auto;padding-top:8px}
.portada{display:block;width:100%;max-width:720px;height:auto;border-radius:18px;border:1px solid var(--line);margin:24px 0}
.texto{max-width:44em}
.texto ul{padding-left:1.2em}
.texto li{margin:4px 0}
.galeria{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,280px),1fr));gap:14px;margin-top:8px}
.galeria img{display:block;width:100%;height:auto;border-radius:12px;border:1px solid var(--line)}
.nota{color:var(--mut);font-size:.95rem;max-width:44em}
footer.pie{border-top:1px solid var(--line);margin-top:24px;padding:20px 0 32px;color:var(--mut);font-size:.95rem}
footer.pie p{margin:4px 0}
.eleccion{list-style:none;padding:0;display:flex;flex-wrap:wrap;gap:12px;margin:24px 0}
.eleccion a{display:inline-block;padding:14px 28px;border:2px solid var(--acc);border-radius:14px;font-weight:800;font-size:1.2rem;text-decoration:none;color:var(--fg);background:var(--card)}
.enlaces{display:flex;flex-wrap:wrap;gap:8px 20px;margin:28px 0 0}
.datos{display:grid;grid-template-columns:max-content 1fr;gap:6px 18px;margin:8px 0 16px;max-width:44em}
.datos dt{font-weight:700}
.datos dd{margin:0;min-width:0}
.novedad{margin:0 0 8px}
.novedad h3{margin:16px 0 2px}
.novedad p{margin:4px 0;max-width:44em}
@media (max-width:480px){body{font-size:16px}.boton{display:block;text-align:center}.datos{grid-template-columns:1fr;gap:0}.datos dd{margin-bottom:8px}}
"""


def favicon():
    return ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
            "<ellipse cx='32' cy='37' rx='27' ry='22' fill='#15804f'/>"
            "<ellipse cx='23' cy='32' rx='6' ry='7' fill='#fff'/><ellipse cx='41' cy='32' rx='6' ry='7' fill='#fff'/>"
            "<circle cx='24.5' cy='33.5' r='3' fill='#14251b'/><circle cx='42.5' cy='33.5' r='3' fill='#14251b'/></svg>\n")


# ---------------------------------------------------------------------------------------------------------------------
# Datos de entrada
# ---------------------------------------------------------------------------------------------------------------------

class Sitio:
    def __init__(self, raiz):
        self.raiz = pathlib.Path(raiz)
        sys.path.insert(0, str(self.raiz / 'herramientas'))
        sys.path.insert(0, str(self.raiz))
        self.cfg = json.loads((self.raiz / 'publicacion' / 'sitio.json').read_text(encoding='utf-8'))
        self.textos = json.loads((self.raiz / 'publicacion' / 'sitio-textos.json').read_text(encoding='utf-8'))
        self.idiomas = list(self.textos)
        self.base = str(self.cfg.get('url_base', '')).rstrip('/')
        self.nombre = str(self.cfg.get('nombre', '')).strip()
        self.juegos = []
        for jid in self.cfg.get('juegos', []):
            ruta = self.raiz / 'juegos' / jid / 'juego.json'
            if not ruta.exists():
                raise ErrorSitio('sitio.json → juegos: no existe la ficha de «%s»' % jid)
            if not (self.raiz / 'salida' / jid / 'index.html').exists():
                raise ErrorSitio('«%s» todavía no está construido: corre «python3 fabrica.py construir %s»' % (jid, jid))
            self.juegos.append({'id': jid, 'spec': json.loads(ruta.read_text(encoding='utf-8')), 'medios': self._medios(jid)})
        self.validar()

    def _medios(self, jid):
        carpeta = self.raiz / 'salida' / jid / 'medios'
        def hay(n):
            return (carpeta / n).exists()
        portada = 'portada.png' if hay('portada.png') else None
        tarjeta = 'portada-web.jpg' if hay('portada-web.jpg') else portada
        capturas = [p.name for p in sorted(carpeta.glob('captura-*-escritorio.png')) if not p.name.startswith('captura-idioma-')][:3] if carpeta.exists() else []
        return {'portada': portada, 'tarjeta': tarjeta, 'capturas': capturas}

    def validar(self):
        t0 = self.textos[self.idiomas[0]]
        for l in self.idiomas:
            if set(self.textos[l]) != set(t0):
                raise ErrorSitio('sitio-textos.json: las claves de «%s» no coinciden con las de «%s»' % (l, self.idiomas[0]))
        if not self.nombre:
            raise ErrorSitio('sitio.json: falta «nombre»')
        if self.cfg.get('idioma_inicial') not in self.idiomas:
            raise ErrorSitio('sitio.json: «idioma_inicial» debe ser uno de %s' % ', '.join(self.idiomas))
        for l in self.idiomas:
            if l not in (self.cfg.get('lema') or {}):
                raise ErrorSitio('sitio.json: falta «lema» en «%s»' % l)
        if not self.base.startswith('https://'):
            raise ErrorSitio('sitio.json: «url_base» debe empezar por https://')
        clave = self.cfg.get('indexnow_clave') or ''
        if clave and not re.fullmatch(r'[A-Za-z0-9-]{8,128}', clave):
            raise ErrorSitio('sitio.json: «indexnow_clave» debe medir de 8 a 128 y usar solo letras, números y guiones')
        ads = self.cfg.get('adsense_publisher') or ''
        if ads and not re.fullmatch(r'pub-\d{16}', ads):
            raise ErrorSitio('sitio.json: «adsense_publisher» debe tener la forma pub-0000000000000000')
        for j in self.juegos:
            faltan = [l for l in self.idiomas if l not in j['spec']['idiomas']]
            if faltan:
                raise ErrorSitio('«%s» no tiene versión en %s y el sitio es trilingüe: o se le agrega el idioma o se quita de sitio.json → juegos' % (j['id'], ', '.join(faltan)))
            for n in (j['spec'].get('novedades') or []):
                faltan_n = [l for l in self.idiomas if not str(n.get(l, '')).strip()] + ([] if n.get('version') else ['version'])
                if faltan_n:
                    raise ErrorSitio('«%s» → novedades (%s): falta %s' % (j['id'], n.get('version', '?'), ', '.join(faltan_n)))
            if not j['medios']['portada']:
                raise ErrorSitio('«%s» no tiene medios/portada.png: corre «python3 fabrica.py probar %s»' % (j['id'], j['id']))
        if 'zh' in self.idiomas:
            propios = [self.textos['zh'], self.cfg.get('lema', {}).get('zh', '')] + [j['spec']['ficha']['zh'] for j in self.juegos] + [n.get('zh', '') for j in self.juegos for n in (j['spec'].get('novedades') or [])]
            fuera = sorted({c for s in _cadenas(propios) for c in s if '一' <= c <= '鿿' and not c.encode('gb2312', 'ignore')})
            if fuera:
                raise ErrorSitio('caracteres chinos fuera de GB2312 en las páginas: %s' % ' '.join(fuera))
        if ads:   # coherencia: no decir «sin anuncios» en las fichas si el sitio los activa
            for j in self.juegos:
                for l in self.idiomas:
                    f = j['spec']['ficha'][l]
                    if re.search(r'sin anuncios|no ads|没有广告|无广告', f['larga'], re.I):
                        raise ErrorSitio('«%s» dice que no tiene anuncios (%s) pero sitio.json activa AdSense: ajusta la ficha' % (j['id'], l))

    # direcciones
    def ruta_inicio(self, l):
        return '/%s/' % l

    def ruta_juego(self, l, jid):
        return '/%s/juegos/%s/' % (l, jid)

    def ruta_privacidad(self, l):
        return '/%s/privacidad/' % l

    def ruta_novedades(self, l):
        return '/%s/novedades/' % l

    def ruta_prensa(self, l):
        return '/%s/prensa/' % l

    def ruta_jugar(self, jid, l=None):
        return '/jugar/%s/' % jid + ('?lang=%s' % l if l else '')

    def clave_indexnow(self):
        return self.cfg.get('indexnow_clave') or hashlib.sha256(self.base.encode('utf-8')).hexdigest()[:32]

    def titulo_juego(self, l, spec):
        gratis = (spec.get('precio') or {}).get('modo', 'gratis') in ('gratis', 'donar')
        return self.textos[l]['titulo_gratis' if gratis else 'titulo_simple'].format(titulo=spec['ficha'][l]['titulo'])


# ---------------------------------------------------------------------------------------------------------------------
# Piezas de página
# ---------------------------------------------------------------------------------------------------------------------

def _contacto(valor):
    v = str(valor).strip()
    if re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', v):
        return '<a href="mailto:%s">%s</a>' % (_e(v), _e(v))
    if v.startswith('https://'):
        return '<a href="%s" rel="noopener">%s</a>' % (_e(v), _e(v))
    return _e(v)


def _alternativas(s, rutas):
    """Etiquetas hreflang: rutas = {idioma: ruta, 'x-default': ruta}."""
    L = ['<link rel="alternate" hreflang="%s" href="%s%s">' % (etiqueta(l), s.base, rutas[l]) for l in s.idiomas if l in rutas]
    if 'x-default' in rutas:
        L.append('<link rel="alternate" hreflang="x-default" href="%s%s">' % (s.base, rutas['x-default']))
    return '\n'.join(L)


def _selector(s, l, rutas):
    t = s.textos[l]
    items = ''.join('<a href="%s" lang="%s" hreflang="%s"%s>%s</a>' % (rutas[x], etiqueta(x), etiqueta(x), ' aria-current="page"' if x == l else '', _e(s.textos[x]['idioma_nombre']))
                    for x in s.idiomas)
    return '<nav class="idiomas" aria-label="%s">%s</nav>' % (_e(t['idioma']), items)


def _pie(s, l):
    t = s.textos[l]
    contacto = str(s.cfg.get('contacto', '')).strip()
    partes = ['<p>%s</p>' % _e(t['ia_sitio']),
              '<p><a href="%s">%s</a> · <a href="%s">%s</a> · <a href="%s">%s</a>%s</p>' % (
                  s.ruta_novedades(l), _e(t['novedades']), s.ruta_prensa(l), _e(t['prensa']), s.ruta_privacidad(l), _e(t['privacidad']),
                  ' · %s: %s' % (_e(t['contacto']), _contacto(contacto)) if contacto else '')]
    return '<footer class="pie">%s</footer>' % ''.join(partes)


def _pagina(s, l, titulo, descripcion, ruta, rutas_idioma, cuerpo, imagen=None, alt_imagen='', json_ld=None, noindex=False, x_default=None):
    t = s.textos[l]
    rutas = dict(rutas_idioma)
    rutas['x-default'] = x_default or rutas_idioma[s.cfg['idioma_inicial']]
    cab = ['<meta charset="utf-8">', '<meta name="viewport" content="width=device-width,initial-scale=1">',
           '<title>%s</title>' % _e(titulo), '<meta name="description" content="%s">' % _e(descripcion),
           '<link rel="canonical" href="%s%s">' % (s.base, ruta), _alternativas(s, rutas),
           '<meta property="og:type" content="website">', '<meta property="og:site_name" content="%s">' % _e(s.nombre),
           '<meta property="og:title" content="%s">' % _e(titulo), '<meta property="og:description" content="%s">' % _e(descripcion),
           '<meta property="og:url" content="%s%s">' % (s.base, ruta), '<meta property="og:locale" content="%s">' % OG_LOCALE.get(l, l)]
    cab += ['<meta property="og:locale:alternate" content="%s">' % OG_LOCALE.get(x, x) for x in s.idiomas if x != l]
    if imagen:
        cab += ['<meta property="og:image" content="%s%s">' % (s.base, imagen), '<meta property="og:image:alt" content="%s">' % _e(alt_imagen),
                '<meta name="twitter:card" content="summary_large_image">']
    if noindex:
        cab.append('<meta name="robots" content="noindex">')
    cab += ['<link rel="icon" href="/favicon.svg" type="image/svg+xml">', '<link rel="stylesheet" href="/sitio.css">']
    if json_ld:
        cab.append('<script type="application/ld+json">%s</script>' % _json_ld(json_ld))
    alto = ('<header class="alto"><a class="marca" href="%s">%s</a>%s</header>'
            % (s.ruta_inicio(l), _e(s.nombre), _selector(s, l, {x: rutas_idioma[x] for x in s.idiomas})))
    return ('<!doctype html>\n<html lang="%s">\n<head>\n%s\n</head>\n<body>\n<div class="envoltura">\n%s\n<main>\n%s\n</main>\n%s\n</div>\n</body>\n</html>\n'
            % (etiqueta(l), '\n'.join(cab), alto, cuerpo, _pie(s, l)))


def _tarjeta(s, l, j):
    spec, t = j['spec'], s.textos[l]
    f = spec['ficha'][l]
    img = j['medios']['tarjeta']
    ancho_alto = dimensiones(s.raiz / 'salida' / j['id'] / 'medios' / img)
    dim = ' width="%d" height="%d"' % ancho_alto if ancho_alto else ''
    return ('<li class="tarjeta"><a href="%s" tabindex="-1" aria-hidden="true"><img src="/medios/%s/%s"%s alt="" loading="lazy" decoding="async"></a>'
            '<div class="cuerpo"><h2><a href="%s">%s</a></h2><p>%s</p><div class="acciones"><a class="boton" href="%s">%s</a><a href="%s">%s</a></div></div></li>'
            % (s.ruta_juego(l, j['id']), j['id'], img, dim, s.ruta_juego(l, j['id']), _e(f['titulo']), _e(f['corta']),
               s.ruta_jugar(j['id'], l), _e(t['jugar']), s.ruta_juego(l, j['id']), _e(t['ver'])))


def pagina_inicio(s, l):
    t = s.textos[l]
    rutas = {x: s.ruta_inicio(x) for x in s.idiomas}
    enlaces = '<p class="enlaces"><a href="%s">%s</a><a href="%s">%s</a></p>' % (s.ruta_novedades(l), _e(t['novedades']), s.ruta_prensa(l), _e(t['prensa']))
    cuerpo = '<h1>%s</h1>\n<p class="lema">%s</p>\n<ul class="rejilla">\n%s\n</ul>\n%s' % (_e(s.nombre), _e(s.cfg['lema'][l]), '\n'.join(_tarjeta(s, l, j) for j in s.juegos), enlaces)
    return _pagina(s, l, '%s — %s' % (s.nombre, s.cfg['lema'][l]), s.cfg['lema'][l], s.ruta_inicio(l), rutas, cuerpo, x_default='/')


def pagina_juego(s, l, j):
    import kit_lanzamiento
    spec, t = j['spec'], s.textos[l]
    f = spec['ficha'][l]
    jid, medios = j['id'], j['medios']
    rutas = {x: s.ruta_juego(x, jid) for x in s.idiomas}
    base_medios = '/medios/%s/' % jid
    ia = kit_lanzamiento.linea_ia(spec, l)
    ancho_alto = dimensiones(s.raiz / 'salida' / jid / 'medios' / medios['portada'])
    dim = ' width="%d" height="%d"' % ancho_alto if ancho_alto else ''
    alt_p = t['alt_portada'].format(titulo=f['titulo'])
    galeria = ''
    if medios['capturas']:
        figs = []
        for n in medios['capturas']:
            d = dimensiones(s.raiz / 'salida' / jid / 'medios' / n)
            figs.append('<img src="%s%s"%s alt="%s" loading="lazy" decoding="async">' % (base_medios, n, ' width="%d" height="%d"' % d if d else '', _e(t['alt_captura'].format(titulo=f['titulo']))))
        galeria = '<h2>%s</h2>\n<div class="galeria">%s</div>' % (_e(t['capturas']), ''.join(figs))
    cuerpo = '\n'.join([
        '<p class="migas"><a href="%s">← %s</a></p>' % (s.ruta_inicio(l), _e(t['todos'])),
        '<h1>%s</h1>' % _e(f['titulo']),
        '<p class="corta">%s</p>' % _e(f['corta']),
        '<p><a class="boton" href="%s">%s</a></p>' % (s.ruta_jugar(jid, l), _e(t['jugar'])),
        '<img class="portada" src="%s%s"%s alt="%s">' % (base_medios, medios['portada'], dim, _e(alt_p)),
        '<h2>%s</h2>\n<p class="texto">%s</p>' % (_e(t['controles']), _e(f['controles'])),
        '<div class="texto">\n%s\n</div>' % md(f['larga']),
        galeria,
        '<p class="nota">%s</p>' % _e(ia) if ia else ''])
    url = s.base + rutas[l]
    ld = {'@context': 'https://schema.org', '@type': 'VideoGame', 'name': f['titulo'], 'description': f['corta'], 'url': url,
          'image': '%s%s%s' % (s.base, base_medios, medios['portada']), 'inLanguage': etiqueta(l), 'applicationCategory': 'Game',
          'gamePlatform': 'Web browser', 'operatingSystem': 'Any', 'publisher': {'@type': 'Organization', 'name': s.nombre}}
    if (spec.get('precio') or {}).get('modo', 'gratis') in ('gratis', 'donar'):
        ld['isAccessibleForFree'] = True
        ld['offers'] = {'@type': 'Offer', 'price': '0', 'priceCurrency': 'USD'}
    return _pagina(s, l, s.titulo_juego(l, spec), f['corta'], rutas[l], rutas, cuerpo, imagen=base_medios + medios['portada'], alt_imagen=alt_p, json_ld=ld)


def _con_contacto(s, texto):
    """Texto con {contacto} y {nombre} resueltos; el resto se escapa."""
    return _e(texto.replace('{nombre}', s.nombre)).replace('{contacto}', _contacto(s.cfg.get('contacto', '')))


def pagina_novedades(s, l):
    """Notas de cada versión (juego.json → novedades). Aquí van los parches: no generan publicaciones en redes."""
    t = s.textos[l]
    rutas = {x: s.ruta_novedades(x) for x in s.idiomas}
    bloques = []
    for j in s.juegos:
        notas = j['spec'].get('novedades') or []
        if not notas:
            continue
        titulo = j['spec']['ficha'][l]['titulo']
        entradas = ''.join('<div class="novedad"><h3>%s</h3><p>%s</p></div>' % (_e(t['novedades_version'].format(version=n['version'])), _e(n[l])) for n in notas)
        bloques.append('<section>\n<h2><a href="%s">%s</a></h2>\n%s\n</section>' % (s.ruta_juego(l, j['id']), _e(titulo), entradas))
    cuerpo = '\n'.join(['<h1>%s</h1>' % _e(t['novedades_titulo']), '<p class="corta">%s</p>' % _e(t['novedades_intro'])] + bloques +
                        ['<p class="nota">%s</p>' % _con_contacto(s, t['novedades_cierre']) if str(s.cfg.get('contacto', '')).strip() else ''])
    return _pagina(s, l, '%s — %s' % (t['novedades_titulo'], s.nombre), t['novedades_intro'], rutas[l], rutas, cuerpo)


def pagina_prensa(s, l):
    """Información para quien quiera reseñar o mostrar los juegos: datos, declaración de IA, imágenes y contacto."""
    import kit_lanzamiento
    t = s.textos[l]
    rutas = {x: s.ruta_prensa(x) for x in s.idiomas}
    nombres_idiomas = lambda spec: ', '.join(s.textos[x]['idioma_nombre'] for x in s.idiomas if x in spec['idiomas'])
    bloques = []
    for j in s.juegos:
        spec, f = j['spec'], j['spec']['ficha'][l]
        base = '/medios/%s/' % j['id']
        filas = [(t['prensa_l_plataforma'], _e(t['prensa_v_plataforma']))]
        if (spec.get('precio') or {}).get('modo', 'gratis') in ('gratis', 'donar'):
            filas.append((t['prensa_l_precio'], _e(t['prensa_v_gratis'])))
        filas += [(t['prensa_l_idiomas'], _e(nombres_idiomas(spec))), (t['prensa_l_version'], _e(spec['version']))]
        ia = kit_lanzamiento.linea_ia(spec, l)
        if ia:
            filas.append((t['prensa_l_ia'], _e(ia)))
        imagenes = []
        for n in [j['medios']['portada']] + list(j['medios']['capturas']):
            d = dimensiones(s.raiz / 'salida' / j['id'] / 'medios' / n)
            alt = t['alt_portada' if n == j['medios']['portada'] else 'alt_captura'].format(titulo=f['titulo'])
            imagenes.append('<a href="%s%s" title="%s"><img src="%s%s"%s alt="%s" loading="lazy" decoding="async"></a>'
                            % (base, n, _e(t['prensa_abrir']), base, n, ' width="%d" height="%d"' % d if d else '', _e(alt)))
        bloques.append('\n'.join([
            '<section>', '<h2><a href="%s">%s</a></h2>' % (s.ruta_juego(l, j['id']), _e(f['titulo'])), '<p>%s</p>' % _e(f['corta']),
            '<h3>%s</h3>' % _e(t['prensa_datos']),
            '<dl class="datos">%s</dl>' % ''.join('<dt>%s</dt><dd>%s</dd>' % (_e(k), v) for k, v in filas),
            '<h3>%s</h3>' % _e(t['prensa_imagenes']), '<div class="galeria">%s</div>' % ''.join(imagenes), '</section>']))
    cierre = ['<p class="nota">%s</p>' % _e(t['prensa_uso'].replace('{nombre}', s.nombre))]
    if str(s.cfg.get('contacto', '')).strip():
        cierre.append('<p>%s</p>' % _con_contacto(s, t['prensa_contacto']))
    cuerpo = '\n'.join(['<h1>%s</h1>' % _e(t['prensa_titulo']), '<p class="corta">%s</p>' % _e(t['prensa_intro'])] + bloques + cierre)
    return _pagina(s, l, '%s — %s' % (t['prensa_titulo'], s.nombre), t['prensa_intro'], rutas[l], rutas, cuerpo)


def pagina_privacidad(s, l):
    t = s.textos[l]
    rutas = {x: s.ruta_privacidad(x) for x in s.idiomas}
    base = list(t['privacidad_base'])
    parrafos = [base[0], t['privacidad_anuncios'] if s.cfg.get('adsense_publisher') else t['privacidad_sin_anuncios']] + base[1:-1]
    if any(j['spec'].get('apoyo_url') for j in s.juegos):
        parrafos.append(t['privacidad_apoyo'])
    parrafos.append(base[-1])
    fecha = s.cfg.get('privacidad_actualizada', '')
    contacto = _contacto(s.cfg.get('contacto', ''))
    cuerpo = '<h1>%s</h1>\n%s\n<div class="texto">%s</div>' % (
        _e(t['privacidad_titulo']), '<p class="nota">%s</p>' % _e(t['privacidad_actualizada'].format(fecha=fecha)) if fecha else '',
        '\n'.join('<p>%s</p>' % _e(p.replace('{nombre}', s.nombre)).replace('{contacto}', contacto) for p in parrafos))
    return _pagina(s, l, '%s — %s' % (t['privacidad_titulo'], s.nombre), t['privacidad_titulo'], rutas[l], rutas, cuerpo)


def pagina_raiz(s):
    enlaces = ''.join('<li><a href="%s" lang="%s" hreflang="%s">%s</a></li>' % (s.ruta_inicio(l), etiqueta(l), etiqueta(l), _e(s.textos[l]['idioma_nombre'])) for l in s.idiomas)
    destinos = json.dumps({l: s.ruta_inicio(l) for l in s.idiomas}, sort_keys=True)
    script = ("(function(){try{var d=%s;var p=(navigator.languages&&navigator.languages.length?navigator.languages:[navigator.language]);"
              "for(var i=0;i<p.length;i++){var c=String(p[i]||'').slice(0,2).toLowerCase();if(d[c]){location.replace(d[c]);return}}"
              "location.replace(d.en||d[%s])}catch(e){}})();" % (destinos, json.dumps(s.cfg['idioma_inicial'])))
    alternativas = _alternativas(s, dict({l: s.ruta_inicio(l) for l in s.idiomas}, **{'x-default': '/'}))
    return ('<!doctype html>\n<html lang="%s">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            '<title>%s</title>\n<meta name="description" content="%s">\n<link rel="canonical" href="%s/">\n%s\n'
            '<link rel="icon" href="/favicon.svg" type="image/svg+xml">\n<link rel="stylesheet" href="/sitio.css">\n</head>\n<body>\n<div class="envoltura">\n<main>\n'
            '<h1>%s</h1>\n<ul class="eleccion">%s</ul>\n</main>\n</div>\n<script>%s</script>\n</body>\n</html>\n'
            % (etiqueta(s.cfg['idioma_inicial']), _e(s.nombre), _e(s.cfg['lema'][s.cfg['idioma_inicial']]), s.base, alternativas, _e(s.nombre), enlaces, script))


def pagina_404(s):
    destino = s.cfg['idioma_inicial']
    t = s.textos[destino]
    enlaces = ''.join('<li><a href="%s" lang="%s">%s</a></li>' % (s.ruta_inicio(l), etiqueta(l), _e(s.textos[l]['idioma_nombre'])) for l in s.idiomas)
    return ('<!doctype html>\n<html lang="%s">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            '<title>%s — %s</title>\n<meta name="robots" content="noindex">\n<link rel="icon" href="/favicon.svg" type="image/svg+xml">\n<link rel="stylesheet" href="/sitio.css">\n</head>\n'
            '<body>\n<div class="envoltura">\n<main>\n<h1>%s</h1>\n<p class="lema">%s</p>\n<ul class="eleccion">%s</ul>\n</main>\n</div>\n</body>\n</html>\n'
            % (etiqueta(destino), _e(t['no_encontrado_titulo']), _e(s.nombre), _e(t['no_encontrado_titulo']),
               ' / '.join(_e(s.textos[l]['no_encontrado_texto']) for l in s.idiomas), enlaces))


# ---------------------------------------------------------------------------------------------------------------------
# Archivos técnicos
# ---------------------------------------------------------------------------------------------------------------------

def sitemap(s, rutas_por_pagina):
    """rutas_por_pagina: lista de dicts {idioma: ruta} (una entrada por página, con sus equivalentes en los demás idiomas) y '/' suelta."""
    L = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
         '  <url><loc>%s/</loc></url>' % s.base]
    for pagina in rutas_por_pagina:
        for l in s.idiomas:
            L.append('  <url>')
            L.append('    <loc>%s%s</loc>' % (s.base, pagina[l]))
            for x in s.idiomas:
                L.append('    <xhtml:link rel="alternate" hreflang="%s" href="%s%s"/>' % (etiqueta(x), s.base, pagina[x]))
            L.append('  </url>')
    L.append('</urlset>')
    return '\n'.join(L) + '\n'


def cabeceras():
    return ('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: SAMEORIGIN\n\n'
            '/jugar/*\n  X-Robots-Tag: noindex\n')


# ---------------------------------------------------------------------------------------------------------------------
# Generación
# ---------------------------------------------------------------------------------------------------------------------

def construir(s):
    """{ruta relativa: bytes} de todo el sitio, sin tocar el disco."""
    A = {}

    def poner(ruta, texto):
        A[ruta] = texto.encode('utf-8') if isinstance(texto, str) else texto
    poner('sitio.css', CSS)
    poner('favicon.svg', favicon())
    poner('index.html', pagina_raiz(s))
    poner('404.html', pagina_404(s))
    paginas = []
    for l in s.idiomas:
        poner('%s/index.html' % l, pagina_inicio(s, l))
        poner('%s/privacidad/index.html' % l, pagina_privacidad(s, l))
        poner('%s/novedades/index.html' % l, pagina_novedades(s, l))
        poner('%s/prensa/index.html' % l, pagina_prensa(s, l))
    paginas.append({l: s.ruta_inicio(l) for l in s.idiomas})
    paginas.append({l: s.ruta_novedades(l) for l in s.idiomas})
    paginas.append({l: s.ruta_prensa(l) for l in s.idiomas})
    paginas.append({l: s.ruta_privacidad(l) for l in s.idiomas})
    for j in s.juegos:
        jid = j['id']
        for l in s.idiomas:
            poner('%s/juegos/%s/index.html' % (l, jid), pagina_juego(s, l, j))
        paginas.append({l: s.ruta_juego(l, jid) for l in s.idiomas})
        poner('jugar/%s/index.html' % jid, (s.raiz / 'salida' / jid / 'index.html').read_bytes())
        origen = s.raiz / 'salida' / jid / 'medios'
        usados = sorted({n for n in (j['medios']['portada'], j['medios']['tarjeta']) if n} | set(j['medios']['capturas']))
        for n in usados:
            poner('medios/%s/%s' % (jid, n), (origen / n).read_bytes())
    poner('sitemap.xml', sitemap(s, paginas))
    poner('robots.txt', 'User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % s.base)
    poner('_headers', cabeceras())
    poner('%s.txt' % s.clave_indexnow(), s.clave_indexnow() + '\n')
    if s.cfg.get('adsense_publisher'):
        poner('ads.txt', 'google.com, %s, DIRECT, f08c47fec0942fa0\n' % s.cfg['adsense_publisher'])
    return A


def generar(raiz):
    """Escribe dist/sitio y dist/sitio-manifiesto.json (fuera de la carpeta que se publica). Devuelve el manifiesto."""
    from publicacion.nucleo import canonico, huella_carpeta, sha256_archivo
    s = Sitio(raiz)
    archivos = construir(s)
    destino = s.raiz / 'dist' / 'sitio'
    if destino.name != 'sitio' or destino.parent.name != 'dist':
        raise ErrorSitio('ruta de salida inesperada: %s' % destino)
    if destino.exists():
        shutil.rmtree(destino)       # es la carpeta que este mismo generador escribe: se rehace completa para que no queden archivos viejos
    for ruta, datos in sorted(archivos.items()):
        f = destino / ruta
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(datos)
    manifiesto = {'url_base': s.base, 'huella': huella_carpeta(destino),
                  'juegos': {j['id']: {'version': j['spec']['version'], 'sha256': sha256_archivo(s.raiz / 'salida' / j['id'] / 'index.html')} for j in s.juegos}}
    (s.raiz / 'dist' / 'sitio-manifiesto.json').write_text(json.dumps(manifiesto, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return manifiesto
