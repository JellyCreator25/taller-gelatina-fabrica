"""Kit de lanzamiento: convierte la ficha de un juego (juego.json) en los textos y planes que hacen falta para publicarlo y darlo a conocer.
Genera, dentro de salida/<id>/kit/: ficha-itch.md (para quien use itch.io), publicaciones.md, plan-lanzamiento.md, difusion.md, registro-creacion.md y metricas.csv.
Los textos creativos (descripciones, posts, guion) los escribe quien crea el juego en juego.json; aquí solo se ordenan, se completan
con los datos reales del juego y se revisa que no falte nada. Las reglas de cada canal viven en difusion/canales.json (cada una con su fuente
y la fecha en que se leyó) y el banco de respuestas en difusion/respuestas.json. Nada de esto publica por sí solo."""
import json
import pathlib
import re
import struct
import sys

TIPOS_IA = {'codigo': ('Code', {'es': 'código', 'en': 'code', 'zh': '代码'}), 'graficos': ('Graphics', {'es': 'gráficos', 'en': 'graphics', 'zh': '图形'}),
            'sonido': ('Sound', {'es': 'sonido', 'en': 'sound', 'zh': '声音'}), 'texto': ('Text & Dialog', {'es': 'texto', 'en': 'text', 'zh': '文字'})}
IDIOMAS = {'es': 'español', 'en': 'inglés', 'zh': 'chino', 'pt': 'portugués', 'hi': 'hindi'}
GRUPOS = ['ahora', 'despues', 'manual', 'no_por_ahora']
ESTADO = {'ahora': 'Se prepara para el lanzamiento', 'despues': 'Cuando haya datos', 'manual': 'Solo tú, a mano',
          'no_por_ahora': 'No por ahora', 'bloqueado': 'Bloqueado por ahora'}
NIVELES = {'total': 'total', 'parcial': 'parcial', 'manual': 'manual', 'bloqueado': 'bloqueada'}
TEXTOS = {'mensaje_clase': 'Mensaje para tu grupo de clase o amigos (WhatsApp, Telegram)',
          'post_corto': 'Post corto (X, Threads, Bluesky, Mastodon, Telegram, Discord, Facebook)',
          'post_comunidad': 'Post para comunidades que permitan compartir proyectos (sirve también para el tablero Release announcements de itch.io)',
          'devlog': 'Devlog de lanzamiento en itch.io',
          'guion_video': 'Video corto (Shorts, Reels, TikTok): guion'}
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def _unir(items, idioma):
    if len(items) <= 1:
        return ''.join(items)
    if idioma == 'zh':
        return '、'.join(items[:-1]) + '和' + items[-1]
    y = {'es': ' y ', 'pt': ' e '}.get(idioma, ' and ')
    return ', '.join(items[:-1]) + y + items[-1]


def _largo_x(texto):
    """Largo como lo cuenta X (twitter-text v3): casi todo pesa 1; chino, japonés, coreano, emojis y símbolos pesan 2. El límite es 280."""
    ligeros = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))
    return sum(1 if any(a <= ord(c) <= b for a, b in ligeros) else 2 for c in texto)


def linea_ia(spec, idioma):
    """La frase de transparencia que acompaña a cada publicación."""
    usados = [TIPOS_IA[k][1][idioma] for k in ('codigo', 'graficos', 'texto', 'sonido') if spec.get('ia', {}).get(k)]
    if not usados:
        return ''
    if idioma == 'es':
        return 'Hecho con ayuda de IA (%s).' % _unir(usados, 'es')
    if idioma == 'zh':
        return '借助 AI 制作（%s）。' % _unir(usados, 'zh')
    return 'Made with the help of AI (%s).' % _unir(usados, 'en')


def linea_ia_corta(spec, idioma):
    """La misma transparencia, en pocas palabras, para el cierre de una publicación en redes (la lista de qué hizo la IA va en el sitio, la prensa y los portales)."""
    if not any((spec.get('ia') or {}).get(k) for k in ('codigo', 'graficos', 'texto', 'sonido')):
        return ''
    return {'es': 'Hecho con ayuda de IA.', 'zh': '借助 AI 制作。'}.get(idioma, 'Made with the help of AI.')


def texto_precio(spec):
    p = spec.get('precio') or {'modo': 'gratis'}
    modo, sug = p.get('modo', 'gratis'), p.get('sugerido_usd')
    if modo == 'donar':
        return 'Gratis con donación opcional («$0 or Donate»)%s. El jugador puede saltarse la donación.' % (', sugerida US$%s' % sug if sug else '')
    if modo == 'pagar':
        return 'Pago libre («pay what you want»): el precio que pongas es el mínimo%s.' % (' (US$%s)' % sug if sug else '')
    return 'Gratis, sin donación sugerida.'


def texto_embed(spec):
    e = spec.get('embed', 'fullscreen')
    if e == 'fullscreen':
        return '«Click to launch in fullscreen» (no pide dimensiones; el juego se adapta al tamaño de la pantalla).'
    return '«Embed in page» con %s × %s px.' % (e.get('ancho'), e.get('alto'))


def _sustituir(texto, spec, idioma):
    return texto.replace('{ia}', linea_ia(spec, idioma)).replace('{enlace}', '[ENLACE DEL JUEGO]')


def _para_que(nombre):
    if nombre == 'portada.png':
        return 'imagen de portada'
    if nombre.startswith('captura-'):
        return 'captura para la galería de la página'
    if nombre == 'clip.gif':
        return 'GIF corto para la página o las publicaciones'
    if nombre == 'clip-vertical.mp4':
        return 'video vertical para Shorts, Reels y TikTok'
    if nombre.endswith('.mp4'):
        return 'video corto para redes'
    return ''


def _medios(salida):
    """Lista de medios con su uso. portada-fuente.png solo es la materia prima de la portada y no se sube."""
    carpeta = salida / 'medios'
    if not carpeta.exists():
        return ['(todavía no hay medios: corre «python3 fabrica.py probar» para generarlos)']
    L = []
    for p in sorted(carpeta.iterdir()):
        if p.suffix not in ('.png', '.mp4', '.gif') or p.name == 'portada-fuente.png':
            continue
        uso = _para_que(p.name)
        L.append('`medios/%s`%s' % (p.name, (' — ' + uso) if uso else ''))
    return L


def _sugerencia_medios(salida):
    """Qué adjuntar a un post que exige imagen o video: el GIF y una captura de juego, si existen."""
    carpeta = salida / 'medios'
    if not carpeta.exists():
        return '(corre «python3 fabrica.py probar» para generar los medios)'
    nombres = sorted(p.name for p in carpeta.iterdir())
    elegidos = [n for n in nombres if n == 'clip.gif']
    for clave in ('juego', 'batalla', 'colocar', 'final'):   # la captura de escritorio que mejor muestra el juego, si existe
        if 'captura-%s-escritorio.png' % clave in nombres:
            elegidos.append('captura-%s-escritorio.png' % clave)
            break
    return ' y '.join('`medios/%s`' % n for n in elegidos) if elegidos else '(no hay medios todavía: corre «python3 fabrica.py probar»)'


def portada_itch(salida):
    """(estado, texto) de la portada frente a lo que pide itch.io: proporción 315:250 y mínimo 315×250 px."""
    ruta = salida / 'medios' / 'portada.png'
    try:
        cab = ruta.read_bytes()[:24]
    except OSError:
        cab = b''
    if cab[:8] != b'\x89PNG\r\n\x1a\n':
        return 'falta', '- Portada: todavía no existe (corre «python3 fabrica.py probar»).'
    w, h = struct.unpack('>II', cab[16:24])
    if w * 250 == h * 315 and w >= 315:
        return 'ok', '- Portada: `medios/portada.png` (%d×%d px). Cumple la proporción 315:250 que pide itch.io (mínimo 315×250).' % (w, h)
    return 'mal', '- Portada: `medios/portada.png` (%d×%d px). OJO: itch.io pide la proporción 315:250 y un mínimo de 315×250; hay que rehacerla.' % (w, h)


def ficha_itch(spec, salida):
    L = ['# Ficha de itch.io · %s (v%s)' % (spec['ficha'][spec['idiomas'][0]]['titulo'], spec['version']), '',
         'Se copia y pega en «Edit game». Los ajustes salen de la documentación de itch.io (revísalos si su panel cambió).', '',
         '## Ajustes', '',
         '- Kind of project: HTML (no «Downloadable»).',
         '- Archivo a subir: `%s-web.zip` (tiene `index.html` en la raíz). Después de subirlo, marcar «This file will be played in the browser».' % spec['id'],
         '- Embed options: ' + texto_embed(spec),
         '- Mobile friendly: activarlo solo si el juego se maneja bien con el dedo (probado en 390×844 por la fábrica).',
         '- Precio: ' + texto_precio(spec),
         '- Reparto con itch.io: por defecto se queda el 10 %; el creador puede fijarlo de 0 a 100 %.',
         '- Hacer público el proyecto solo al final, después de ver la vista previa en celular y en computadora.',
         portada_itch(salida)[1], '',
         '## Medios para subir', ''] + ['- ' + m for m in _medios(salida)] + ['']
    for idioma in spec['idiomas']:
        f = spec['ficha'][idioma]
        L += ['## Texto en %s' % IDIOMAS.get(idioma, idioma), '',
              '**Título:** ' + f['titulo'], '', '**Descripción corta:** ' + f['corta'], '',
              '**Controles:** ' + f.get('controles', '(falta)'), '', '**Descripción larga (Markdown, copiar tal cual):**', '', '```markdown',
              f['larga'].rstrip() + '\n\n' + linea_ia(spec, idioma), '```', '']
    L += ['## Etiquetas sugeridas', '', ', '.join(spec.get('etiquetas', [])) or '(falta)', '',
          'Se usan solo estas: itch.io avisa de que marcar todas las clasificaciones posibles puede hacer que trate la página como spam.', '',
          '## Contenido', '', spec.get('clasificacion', '(falta describir el contenido)'), '',
          '## Declaración de IA (campo del proyecto en itch.io)', '']
    tipos = [TIPOS_IA[k][0] for k in ('codigo', 'graficos', 'texto', 'sonido') if spec.get('ia', {}).get(k)]
    if tipos:
        L += ['Marcar **Yes** y seleccionar: ' + ', '.join(tipos) + '.',
              'itch.io pide declararlo aunque el contenido se haya retocado a mano. La etiqueta «AI Generated» se coloca sola; no hay que añadirla en las etiquetas.',
              'Además, la descripción del proyecto debe decir con claridad qué se hizo con IA: la línea ya va al final de cada texto de arriba.']
    else:
        L += ['Marcar **No** solo si de verdad nada se hizo con IA.']
    L += ['', 'Si algún día va a Steam: en el cuestionario de contenido, la sección de IA generativa pide declarar el contenido creado con ayuda de IA que viaja con el juego («Pre-Generated»).', '']
    return '\n'.join(L)


def publicaciones(spec, salida):
    L = ['# Publicaciones · %s' % spec['ficha'][spec['idiomas'][0]]['titulo'], '',
         '## Reglas de difusión (valen para todo lo de abajo)', '',
         '- Honesta: solo se dice lo que el juego hace de verdad. Sin cuentas falsas, reseñas inventadas, votos comprados ni respuestas fingidas.',
         '- El uso de IA siempre se declara (la línea ya viene en cada texto).',
         '- Cada comunidad tiene sus propias reglas de autopromoción: se leen antes de publicar y, si no permiten promocionar, no se publica ahí.',
         '- No se anuncia el juego en los comentarios ni en las comunidades de otros proyectos de itch.io: sus pautas lo prohíben.',
         '- Se enseña el juego y se pide opinión; nunca se pide un voto.',
         '- Nada se hace público ni se paga sin el «sí» del dueño de la cuenta.',
         '- Cuando exista el enlace real del juego, se sustituye [ENLACE DEL JUEGO] en todos los textos.',
         '- Canales, reglas verificadas, calendario y banco de respuestas: ver `difusion.md`.', '',
         '## Medios disponibles', ''] + ['- ' + m for m in _medios(salida)] + ['']
    for idioma in spec['idiomas']:
        d = (spec.get('difusion') or {}).get(idioma)
        if not d:
            L += ['(Falta el bloque difusion.%s en juego.json.)' % idioma, '']
            continue
        L += ['## Textos en %s' % IDIOMAS.get(idioma, idioma), '']
        if d.get('mensaje_clase'):
            L += ['### ' + TEXTOS['mensaje_clase'], '', _sustituir(d['mensaje_clase'], spec, idioma), '']
        if d.get('post_corto'):
            L += ['### ' + TEXTOS['post_corto'], '', _sustituir(d['post_corto'], spec, idioma), '']
        if d.get('post_comunidad'):
            L += ['### ' + TEXTOS['post_comunidad'], '', '**Título:** ' + _sustituir(d.get('post_comunidad_titulo', ''), spec, idioma), '',
                  _sustituir(d['post_comunidad'], spec, idioma), '',
                  'Adjuntar al menos una imagen o video (el tablero de itch.io lo exige): ' + _sugerencia_medios(salida) + '.', '']
        if d.get('devlog'):
            L += ['### ' + TEXTOS['devlog'], '', '**Título:** ' + d.get('devlog_titulo', ''), '', _sustituir(d['devlog'], spec, idioma), '']
        if d.get('guion_video'):
            L += ['### ' + TEXTOS['guion_video'], ''] + ['%d. %s' % (i + 1, x) for i, x in enumerate(d['guion_video'])] + [
                '', 'Archivo vertical listo: `medios/clip-vertical.mp4`.', '',
                'Descripción sugerida: ' + _sustituir(d.get('descripcion_video', ''), spec, idioma) + ' #indiegame #juegosweb #' + ''.join(w.capitalize() for w in spec['ficha'][idioma]['titulo'].split()), '']
    return '\n'.join(L)


def plan(spec):
    nombre = spec['ficha'][spec['idiomas'][0]]['titulo']
    return '\n'.join([
        '# Plan de lanzamiento · %s' % nombre, '',
        'Quién hace qué: **Yo** = Claude; **Tú** = el dueño de las cuentas; **Ambos** = yo preparo, tú apruebas.',
        'El camino principal es el **sitio propio** más las redes con cuenta de bot declarada: lo prepara y lo ejecuta la fábrica (`python3 fabrica.py publicar`), y nada sale sin tu aprobación de un plan exacto. '
        'itch.io y los portales son caminos opcionales y, en buena parte, manuales.',
        'Los canales, sus reglas, el calendario y el banco de respuestas están en `difusion.md`; el mapa de todos los canales, en `difusion/MAPA.md`; cómo se creó el juego, en `registro-creacion.md`.', '',
        '## Una sola vez (la primera vez que publicas)', '',
        '| Paso | Quién | Detalle |', '|---|---|---|',
        '| Cuenta de Cloudflare y proyecto de Pages | Tú | Es el sitio. Con su token de API como secreto (nunca en archivos del proyecto). Pasos exactos en `LEEME-DUENO.md`. |',
        '| Fijar los datos reales del sitio | Ambos | `publicacion/sitio.json`: dirección (`url_base`), `proyecto` y `contacto`. Mientras tengan el valor de ejemplo, la fábrica se niega a publicar. |',
        '| Cuentas de redes (opcional) | Tú | Bluesky, Mastodon, Telegram, Discord, YouTube: una cuenta de bot por canal, declarada como bot. Los secretos van al entorno de GitHub, no al chat. |',
        '| Cobros (solo si usas itch.io o anuncios) | Tú | PayPal o Stripe directo, o cobro por itch.io; AdSense si activas anuncios. Lo fiscal, con tu contador. |',
        '', '## Por cada juego', '',
        '| Paso | Quién | Detalle |', '|---|---|---|',
        '| Construir y probar | Yo | `python3 fabrica.py todo %s` → informe-pruebas.txt, medios y este kit. |' % spec['id'],
        '| Agregarlo al sitio | Ambos | Añadir el id a `publicacion/sitio.json → juegos` (si ya hay otro lanzado, respetar la pausa entre lanzamientos). |',
        '| Ver el plan | Yo | `python3 fabrica.py publicar`: muestra cada acción, el texto exacto de cada publicación y una huella del plan. No ejecuta nada. |',
        '| Aprobar | Tú | Un «sí» con la huella del plan que leíste. Si algo del plan cambia, la huella cambia y hay que aprobar de nuevo. |',
        '| Ejecutar | Yo | `python3 fabrica.py publicar --ejecutar --aprobar <huella>`: sitio, aviso a buscadores y publicaciones en los canales que tengan secretos. Cada resultado queda en `publicacion/libro.jsonl`. |',
        '| Probar la página como visitante | Yo | Celular y computadora, con una ventana limpia. |',
        '| Itch.io o portales (opcional) | Ambos | Texto y archivos listos en `ficha-itch.md` y el zip; la página se crea a mano. Con butler: `butler push salida/%s/%s-web.zip tuusuario/tujuego:html5` y marcar HTML5 en «Edit game». |' % (spec['id'], spec['id']),
        '', '## Después del lanzamiento', '',
        '| Cuándo | Quién | Qué |', '|---|---|---|',
        '| Cada 3 días, 2 semanas | Yo | Leer métricas y comentarios; anotarlos con `python3 fabrica.py metricas anotar` (las vistas de Cloudflare entran solas si la medición está activada); proponer respuestas (tú apruebas). |',
        '| Semana 2 | Yo | Parche con lo que repita la gente (error, balance, claridad). Subir la versión y volver a pasar por «publicar»: un parche actualiza el sitio sin volver a publicar en redes. |',
        '| Semana 3-4 | Ambos | Paquete nuevo si hay interés. |',
        '| Semana 4 | Tú | Decidir con datos: seguir, cambiar de enfoque o lanzar el siguiente juego. |',
        '', '## Reglas para no gastar de más ni de menos', '',
        'No se lanza el siguiente juego hasta tener 2 a 4 semanas de datos del anterior (la fábrica lo hace cumplir con la pausa entre lanzamientos). Más juegos no traen más jugadores por sí solos; lo que decide es que alguien los encuentre.', ''])


# ---------------------------------------------------------------------------------------------------------------------
# Difusión: canales con reglas verificadas, calendario, banco de respuestas y registro de creación
# ---------------------------------------------------------------------------------------------------------------------

def cargar_json(raiz, nombre):
    return json.loads((pathlib.Path(raiz) / 'difusion' / nombre).read_text(encoding='utf-8'))


def _fecha_larga(iso):
    a, m, d = (int(x) for x in iso.split('-'))
    return '%d de %s de %d' % (d, MESES[m - 1], a)


def _titulo_de(raiz, juego_id):
    try:
        s = json.loads((pathlib.Path(raiz) / 'juegos' / juego_id / 'juego.json').read_text(encoding='utf-8'))
        return s['ficha'][s['idiomas'][0]]['titulo']
    except (OSError, KeyError, ValueError):
        return juego_id


def validar_canales(datos):
    """Revisa que los datos de canales estén completos: cada regla con su fuente, cada canal en un grupo válido."""
    problemas, vistos = [], set()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(datos.get('verificado', ''))):
        problemas.append('canales.json: falta la fecha «verificado» (AAAA-MM-DD)')
    for c in datos.get('canales', []):
        cid = c.get('id', '(sin id)')
        if cid in vistos:
            problemas.append('canal repetido: ' + cid)
        vistos.add(cid)
        if c.get('grupo') not in GRUPOS:
            problemas.append('%s: grupo no válido (%s)' % (cid, c.get('grupo')))
        for k in ('nombre', 'cuando', 'quien', 'para_que'):
            if not c.get(k):
                problemas.append('%s: falta «%s»' % (cid, k))
        for r in c.get('reglas', []):
            if not str(r.get('fuente', '')).startswith('https://') or not r.get('texto'):
                problemas.append('%s: una regla no tiene texto o fuente https' % cid)
        if c.get('texto') and c['texto'] not in TEXTOS:
            problemas.append('%s: el texto «%s» no existe' % (cid, c['texto']))
        a = c.get('automatizacion')
        if not a:
            problemas.append('%s: falta «automatizacion»' % cid)
            continue
        if a.get('nivel') not in datos.get('niveles', {}):
            problemas.append('%s: nivel de automatización no válido (%s)' % (cid, a.get('nivel')))
        for k in ('via', 'una_vez', 'cada_vez'):
            if k not in a:
                problemas.append('%s: automatizacion sin «%s»' % (cid, k))
        for s in a.get('secretos', []):
            if not re.fullmatch(r'[A-Z][A-Z0-9_]+', s):
                problemas.append('%s: «%s» debe ser un NOMBRE de variable en mayúsculas, nunca un valor' % (cid, s))
        for h in a.get('hechos', []) + a.get('humano', []):
            if not str(h.get('fuente', '')).startswith('https://') or not h.get('texto'):
                problemas.append('%s: un hecho de automatización no tiene texto o fuente https' % cid)
        if a['nivel'] in ('total', 'parcial') and c['grupo'] == 'no_por_ahora':
            problemas.append('%s: un canal «no por ahora» no puede tener automatización %s' % (cid, a['nivel']))
    return problemas


def precio_jugador(spec, idioma):
    """Cómo se le explica el precio a un jugador (para el banco de respuestas)."""
    p = spec.get('precio') or {'modo': 'gratis'}
    modo, sug = p.get('modo', 'gratis'), p.get('sugerido_usd')
    es = idioma == 'es'
    if idioma == 'zh':
        if modo == 'donar':
            return '免费。如果你想支持这个项目，可以自愿捐赠%s；玩游戏不需要付任何钱。' % ('（建议 %s 美元）' % sug if sug else '')
        if modo == 'pagar':
            return '自选价格：%s' % ('最低 %s 美元，想多付也可以。' % sug if sug else '从页面上标明的最低价开始，你想付多少都行。')
        return '免费。'
    if modo == 'donar':
        if es:
            return 'Es gratis. Hay una donación opcional%s para quien quiera apoyar el proyecto; no hace falta pagar nada para jugar.' % (' (sugerida: US$%s)' % sug if sug else '')
        return "It's free. There's an optional donation%s if you'd like to support the project; you don't need to pay anything to play." % (' (suggested: US$%s)' % sug if sug else '')
    if modo == 'pagar':
        if es:
            return 'Es de pago libre: %s' % ('el mínimo es US$%s y puedes pagar más si quieres.' % sug if sug else 'pagas lo que quieras a partir del mínimo que marca la página.')
        return "It's pay-what-you-want: %s" % ('the minimum is US$%s and you can pay more if you like.' % sug if sug else 'you pay what you like, starting from the minimum shown on the page.')
    return 'Es gratis.' if es else "It's free."


def sin_anuncios(spec, idioma):
    """Respuesta sobre anuncios, cuentas y datos. Solo es cierta mientras el juego no integre anuncios (campo «anuncios» de la ficha)."""
    if spec.get('anuncios'):
        return 'REVISAR: este juego declara anuncios; escribe esta respuesta a mano.'
    if idioma == 'zh':
        return ('没有：游戏没有广告，不需要账号，也不会连接外部网络（测试会检查这一点）。你的进度（最高分或关卡）只保存在你自己的设备上。'
                '发布平台会自行统计页面的访问量。')
    if idioma == 'es':
        return ('No: el juego no tiene anuncios, no pide cuenta y no hace conexiones externas (las pruebas lo comprueban). Tu progreso (mejor marca o nivel) '
                'se guarda solo en tu dispositivo. La plataforma donde está publicado sí mide por su cuenta las visitas a la página.')
    return ("No: the game has no ads, doesn't ask for an account and makes no external connections (the tests check that). Your progress (best score or level) "
            "is stored only on your device. The platform it's published on does measure page visits on its own.")


def _diferenciador(spec, idioma):
    d = (spec.get('originalidad') or {}).get('diferenciador') or {}
    return d.get(idioma) or ''


def _rellenar(texto, spec, idioma):
    orig = spec.get('originalidad') or {}
    return (texto.replace('{ia_frase}', linea_ia(spec, idioma)).replace('{precio}', precio_jugador(spec, idioma))
            .replace('{sin_anuncios}', sin_anuncios(spec, idioma)).replace('{diferenciador}', _diferenciador(spec, idioma))
            .replace('{referencias}', _unir(orig.get('referencias', []), idioma)).replace('{titulo}', spec['ficha'][idioma]['titulo']))


def evaluar(canal, spec, nov=None):
    """(grupo para este juego, avisos). Un canal «después de datos» pasa a «bloqueado» si al juego le falta un requisito
    o si el comprobador de novedad (herramientas/novedad.py) no lo declara apto para portales."""
    grupo, avisos = canal['grupo'], []
    if canal.get('sensible_a_clon') and nov is not None and not nov['apto']['portales'] and grupo in ('ahora', 'despues'):
        avisos.append('No apto para portales según el comprobador de novedad: ' + ' '.join(nov['motivos']))
        grupo = 'bloqueado'
    falta = [i for i in canal.get('requiere_idiomas', []) if i not in spec['idiomas']]
    if falta:
        avisos.append('Falta la versión en %s.' % _unir([IDIOMAS.get(i, i) for i in falta], 'es'))
        if grupo == 'despues':
            grupo = 'bloqueado'
    riesgo = (spec.get('originalidad') or {}).get('riesgo_portales')
    if canal.get('sensible_a_clon') and riesgo in ('medio', 'alto'):
        avisos.append('Riesgo %s de que lo vean como variante de un género conocido.' % riesgo)
    mejor = canal.get('mejor_en')
    if mejor and mejor not in spec['idiomas']:
        avisos.append('Sin versión en %s llegará a menos gente (suposición mía).' % IDIOMAS.get(mejor, mejor))
    return grupo, avisos


def _estado_texto(canal, spec, nov=None):
    grupo, avisos = evaluar(canal, spec, nov)
    return ESTADO[grupo] + (' (opcional)' if canal.get('opcional') else '') + ((' — ' + ' '.join(avisos)) if avisos else '')


def calendario(spec, titulo_previo):
    """Filas (día, qué, quién, ¿necesita tu «sí»?). D0 es el día en que la página queda pública."""
    nombre = spec['ficha'][spec['idiomas'][0]]['titulo']
    filas = [
        ('Antes', 'Cuenta de Cloudflare, datos reales en `sitio.json` y secretos de cada red (una sola vez; itch.io solo si lo quieres)', 'Tú', 'Tú lo haces'),
        ('D-3', 'Construir, probar y regenerar el kit; añadir el juego al sitio; `publicar` para ver el plan completo', 'Yo', 'No'),
        ('D-2', 'Revisar el sitio en local (idiomas, enlaces, medios) y corregir lo que falle', 'Yo', 'No'),
        ('D-1', 'Revisión final: el texto exacto de cada publicación está en el plan. Te dejo la huella del plan', 'Yo', 'Sí: un «sí» con esa huella'),
        ('D0', 'Ejecutar el plan aprobado: sitio, aviso a buscadores y publicaciones. Mensaje a tu grupo', 'Yo ejecuto; tú mandas lo de tu grupo', 'Sí (la huella)'),
        ('D0', 'Si usas itch.io: página pública, tema en «Release announcements» y devlog (a mano, con los textos listos)', 'Tú', 'Tú lo haces'),
        ('D1', 'Leer comentarios y métricas; proponer respuestas del banco', 'Yo', 'Sí, por cada respuesta pública'),
        ('D3', 'Métricas. Con muchas vistas y pocas partidas, probar otra portada o descripción corta', 'Yo', 'Sí, para cambiar el sitio'),
        ('D4-D5', 'Video corto (clip vertical listo): el canal de YouTube si está configurado; TikTok e Instagram, a mano', 'Yo / tú', 'Sí'),
        ('D6', 'Métricas y comentarios', 'Yo', 'No'),
        ('D7', 'Resumen de la semana 1: qué se repite en los comentarios y qué parche toca', 'Yo', 'Tú decides el parche'),
        ('D9', 'Métricas y comentarios', 'Yo', 'No'),
        ('D10-D13', 'Parche con lo que repita la gente (error, balance o claridad), con pruebas completas', 'Yo', 'Sí, para publicar la versión'),
        ('D12', 'Métricas y comentarios', 'Yo', 'No'),
        ('D14', 'Aviso del parche (solo si activas `avisar_parches`) y segundo video', 'Yo / tú', 'Sí'),
        ('D15-D21', 'Con los datos a la vista: ¿conviene otro idioma, un portal, o seguir parchando?', 'Yo propongo', 'Tú decides'),
        ('D28', 'Decisión con datos: seguir con parches, cambiar de enfoque o lanzar el siguiente juego', 'Tú', 'Tú decides'),
    ]
    cab = []
    espera = (spec.get('lanzamiento') or {}).get('espera_semanas')
    if (spec.get('lanzamiento') or {}).get('despues_de'):
        cab = ['**Este juego espera su turno:** no sale antes de que «%s» lleve %s semanas de datos (regla de la casa). Los días de abajo cuentan desde el D0 de «%s».' % (titulo_previo, espera or '2 a 4', nombre), '']
    else:
        cab = ['D0 es el día en que apruebas el plan y el sitio de «%s» queda público.' % nombre, '']
    return cab + ['| Día | Qué pasa | Quién | ¿Necesita tu «sí»? |', '|---|---|---|---|'] + ['| %s | %s | %s | %s |' % f for f in filas]


def banco_respuestas(spec, resp):
    L = ['**Reglas para responder**', ''] + ['- ' + r for r in resp['reglas']] + ['']
    orig = spec.get('originalidad') or {}
    for idioma in spec['idiomas']:
        L += ['### Respuestas en %s' % IDIOMAS.get(idioma, idioma), '']
        for it in resp.get(idioma, []):
            if it.get('requiere') == 'originalidad' and not (orig.get('referencias') and _diferenciador(spec, idioma)):
                continue
            L += ['**%s**' % it['pregunta'], '', '> ' + _rellenar(it['respuesta'], spec, idioma), '']
    return L


def difusion(spec, salida, datos, resp, titulo_previo, nov=None):
    nombre = spec['ficha'][spec['idiomas'][0]]['titulo']
    orig = spec.get('originalidad') or {}
    lan = spec.get('lanzamiento') or {}
    canales = [c for g in GRUPOS for c in datos['canales'] if c['grupo'] == g]
    fecha = _fecha_larga(datos['verificado'])
    ia_total = sum(1 for k in ('codigo', 'graficos', 'texto', 'sonido') if spec.get('ia', {}).get(k))
    L = ['# Difusión · %s (v%s)' % (nombre, spec['version']), '',
         'Qué es: el plan para que este juego llegue a la gente. Trae las reglas de cada canal tal como las leí el %s en sus páginas oficiales, '
         'el texto que corresponde a cada uno, un calendario y un banco de respuestas. Nada de esto publica por sí solo: lo público lleva tu «sí» (ver `plan-lanzamiento.md`).' % fecha, '',
         '## En una mirada', '',
         '- **Idiomas del juego:** %s.' % _unir([IDIOMAS.get(i, i) for i in spec['idiomas']], 'es')]
    if lan.get('despues_de'):
        L.append('- **Orden de lanzamiento:** va después de «%s». No sale antes de que ese juego lleve %s semanas de datos.' % (titulo_previo, lan.get('espera_semanas', '2 a 4')))
    else:
        L.append('- **Orden de lanzamiento:** es el primero de la fábrica.')
    for g in GRUPOS:
        nombres = [c['nombre'] for c in canales if c['grupo'] == g]
        if nombres:
            L.append('- **%s:** %s.' % (datos['grupos'][g], '; '.join(nombres)))
    if orig.get('riesgo_portales'):
        L.append('- **Originalidad (mi evaluación, no la de ninguna plataforma):** riesgo **%s** de que un portal lo vea como variante de un género conocido. %s' % (orig['riesgo_portales'], orig.get('motivo', '')))
    if ia_total >= 3:
        partes = 'sus 4 partes' if ia_total == 4 else '%d de sus 4 partes' % ia_total
        L.append('- **Lo que puede frenarlo:** el juego está hecho con IA en %s (código, gráficos, texto y sonido) e itch.io no acepta proyectos con poca intervención humana. '
                 'Por eso `registro-creacion.md` deja constancia de quién decidió qué. Detalle en «Página del juego en itch.io».' % partes)
    solos = [c['nombre'] for c in canales if c['grupo'] == 'ahora' and c['automatizacion']['nivel'] == 'total']
    if solos:
        L.append('- **Se publican sin pasos manuales, después de tus pasos de una sola vez:** %s.' % '; '.join(solos))
    L.append('- **Para empezar necesito de ti (una sola vez):** crear las cuentas y los permisos de los canales que quieras usar y guardar sus claves en tu entorno de GitHub; '
             'canal por canal, qué hace falta está abajo en «Una sola vez (solo tú)», y el resumen de todos los canales en `difusion/MAPA.md`. Yo nunca pido ni escribo tus contraseñas.')
    L += ['', '## Canales, en orden', '', '| # | Canal | Cuándo | Automatización | Para este juego |', '|---|---|---|---|---|']
    for n, c in enumerate(canales, 1):
        L.append('| %d | %s | %s | %s | %s |' % (n, c['nombre'], c['cuando'], NIVELES[c['automatizacion']['nivel']].capitalize(), _estado_texto(c, spec, nov)))
    L += ['', '## Reglas de cada canal', '',
          'Verificado el %s. %s' % (fecha, datos.get('nota', '')), '']
    for n, c in enumerate(canales, 1):
        L += ['### %d. %s' % (n, c['nombre']), '',
              '- **Para este juego:** ' + _estado_texto(c, spec, nov),
              '- **Cuándo:** ' + c['cuando'], '- **Quién:** ' + c['quien'], '- **Para qué:** ' + c['para_que'], '']
        if c.get('reglas'):
            L += ['**Reglas verificadas** (cada una con su fuente):', ''] + ['- %s ([fuente](%s))' % (r['texto'], r['fuente']) for r in c['reglas']] + ['']
        if c.get('casa'):
            L += ['**Reglas de la casa:**', ''] + ['- ' + x for x in c['casa']] + ['']
        if c.get('pendiente_tecnico'):
            L += ['**Trabajo técnico previo (mío, todavía sin hacer):**', ''] + ['- ' + x for x in c['pendiente_tecnico']] + ['']
        a = c['automatizacion']
        L += ['**Automatización: %s.** %s' % (NIVELES[a['nivel']], a['via']), '']
        if a.get('una_vez'):
            L += ['Una sola vez (solo tú):', ''] + ['- ' + x for x in a['una_vez']] + ['']
        if a.get('cada_vez'):
            L += ['Cada vez (el motor):', ''] + ['- ' + x for x in a['cada_vez']] + ['']
        if a.get('secretos'):
            L += ['Secretos que necesita (solo sus nombres; los valores van únicamente en tu entorno de GitHub, nunca en el chat ni en un archivo): ' + ', '.join('`%s`' % s for s in a['secretos']), '']
        if a.get('ingresos'):
            L += ['Ingresos: ' + a['ingresos'] + '.', '']
        if a.get('hechos'):
            L += ['Hechos verificados sobre esta vía:', ''] + ['- %s ([fuente](%s))' % (h['texto'], h['fuente']) for h in a['hechos']] + ['']
        if a.get('humano'):
            L += ['Lo que siempre hace una persona:', ''] + ['- %s ([fuente](%s))' % (h['texto'], h['fuente']) for h in a['humano']] + ['']
        if a.get('nota'):
            L += [a['nota'], '']
        if c.get('riesgos'):
            L += ['**Riesgos:**', ''] + ['- ' + x for x in c['riesgos']] + ['']
        if c.get('no_verificado'):
            L += ['**Sin verificar:**', ''] + ['- ' + x for x in c['no_verificado']] + ['']
        if c.get('texto'):
            d = (spec.get('difusion') or {}).get(spec['idiomas'][0]) or {}
            if d.get(c['texto']):
                extra = ''
                if c['texto'] == 'post_comunidad':
                    extra = ' Adjunta al menos una imagen o video: ' + _sugerencia_medios(salida) + '.'
                L += ['**Texto listo:** `publicaciones.md` → «%s».%s' % (TEXTOS[c['texto']], extra), '']
            else:
                L += ['**Texto listo:** falta `difusion.%s.%s` en `juego.json`.' % (spec['idiomas'][0], c['texto']), '']
    L += ['## Calendario', ''] + calendario(spec, titulo_previo) + ['',
          'Los portales (CrazyGames, Poki, Playgama) se evalúan desde el D28: cada uno se prepara solo si el juego cumple sus requisitos y hay datos de itch.io que lo justifiquen.', '',
          '## Banco de respuestas', ''] + banco_respuestas(spec, resp) + [
          '## Qué se mide y cómo se decide', '',
          'Se anota en el registro de la fábrica (`metricas/registro.csv`, con `python3 fabrica.py metricas anotar JUEGO METRICA VALOR`) cada 3 días durante 2 semanas y después una vez por semana: vistas del juego y de la ficha, comentarios favorables y desfavorables, donaciones e ingresos en dólares y de dónde llegó la gente (la fuente). Ese registro es lo que lee `python3 fabrica.py rumbo` para recomendar qué construir después; `metricas.csv` de esta carpeta queda como libreta para notas libres. '
          'Cómo leer los números (criterio mío, no de las plataformas):', '',
          '| Lo que ves | Probable causa | Qué se cambia |', '|---|---|---|',
          '| Pocas vistas | Nadie encuentra la página | La difusión (devlog, video, comunidades, inglés), no el juego |',
          '| Muchas vistas y pocas partidas | La portada, el título o la descripción corta no convencen | Portada y texto corto |',
          '| Muchas partidas, partidas muy cortas o comentarios que repiten un problema | El inicio del juego | Un parche sobre los primeros minutos |',
          '| Las vistas vienen casi solo de tu grupo | El juego no ha salido de tu círculo | Probar otro canal antes de crear otro juego |',
          '| Casi sin donaciones aunque haya partidas | Suele pasar; no indica por sí solo que el juego falle | Esperar más datos; evaluar un portal con publicidad |', '',
          'En el D28 decides tú, con estos números a la vista: seguir con parches, cambiar de enfoque (inglés o un portal) o lanzar el siguiente juego. No hay un umbral mágico: antes de decidir se mira qué canal trajo a la gente y qué dijo.', '',
          '## Lo que no se hace', '',
          '- No se crean cuentas, no se aceptan términos y no se configuran cobros por ti.',
          '- No se compran visitas, seguidores, reseñas ni votos, y no se usan cuentas falsas.',
          '- No se publica ni se gasta nada sin tu «sí».',
          '- No se promociona el juego en los comentarios ni en las comunidades de otros proyectos de itch.io.', '']
    return '\n'.join(L)


def registro_creacion(spec):
    c = spec.get('creacion') or {}
    nombre = spec['ficha'][spec['idiomas'][0]]['titulo']
    partes = {'codigo': 'Código', 'graficos': 'Gráficos', 'texto': 'Texto', 'sonido': 'Sonido'}
    L = ['# Registro de creación · %s (v%s)' % (nombre, spec['version']), '',
         'Para qué sirve: algunas plataformas piden poder enseñar cómo se hizo un juego con IA (Poki pide las herramientas usadas y, si lo solicitan, '
         'un resumen del proceso, los prompts y las iteraciones), e itch.io no acepta proyectos con poca intervención humana. Este archivo deja constancia, '
         'con hechos, de quién decidió qué. Se mantiene al día con cada versión. Dónde queda la línea lo decide cada plataforma, no este archivo.', '',
         'Estado: borrador redactado por Claude a partir de la conversación de creación. El dueño lo revisa y lo corrige antes de enseñárselo a cualquier plataforma.', '',
         '## Herramientas', ''] + ['- ' + x for x in c.get('herramientas', ['(falta)'])] + ['', '## Qué se hizo con IA', '']
    L += ['- %s: %s' % (v, 'con IA' if spec.get('ia', {}).get(k) else 'sin IA') for k, v in partes.items()]
    L += ['', '## Decisiones del dueño', ''] + ['- ' + x for x in c.get('decisiones_dueno', ['(falta)'])]
    L += ['', '## Decisiones de Claude dentro de esas instrucciones', ''] + ['- ' + x for x in c.get('decisiones_claude', ['(falta)'])]
    L += ['', '## Cómo se prueba', '',
          '- Pruebas automáticas en un navegador real (escritorio y celular simulado): `salida/%s/informe-pruebas.txt`.' % spec['id'],
          '- Las pruebas demuestran que el juego funciona, no que sea divertido: eso lo dicen los jugadores.', '',
          '## Qué falta registrar', '',
          '- Las decisiones nuevas del dueño sobre este juego (cambios pedidos, ideas aceptadas o rechazadas) se añaden aquí cuando ocurran, con la fecha.', '']
    return '\n'.join(L)


def _grafemas_con_enlace_del_sitio(raiz, spec, idioma, post_corto):
    """Cuántos grafemas mide el post ya con el enlace real del sitio (o uno de largo parecido si el sitio aún tiene la dirección de ejemplo)."""
    sys.path.insert(0, str(raiz))
    from publicacion import texto as tx
    ruta = pathlib.Path(raiz) / 'publicacion' / 'sitio.json'
    base = (json.loads(ruta.read_text(encoding='utf-8')).get('url_base') or '').rstrip('/') if ruta.exists() else ''
    largo = len('%s/%s/juegos/%s/' % (base, idioma, spec['id'])) + (10 if (not base or 'CAMBIA' in base.upper()) else 0)
    return tx.grafemas(post_corto.replace('{enlace}', 'x' * largo).replace('{ia}', linea_ia(spec, idioma)))


def generar(raiz, spec):
    raiz = pathlib.Path(raiz)
    salida = raiz / 'salida' / spec['id']
    kit = salida / 'kit'
    kit.mkdir(parents=True, exist_ok=True)
    datos, resp = cargar_json(raiz, 'canales.json'), cargar_json(raiz, 'respuestas.json')
    previo = (spec.get('lanzamiento') or {}).get('despues_de')
    titulo_previo = _titulo_de(raiz, previo) if previo else ''
    problemas = validar_canales(datos)
    for idioma in spec['idiomas']:
        if not resp.get(idioma):
            problemas.append('respuestas.json: no hay respuestas en «%s»' % idioma)
    (kit / 'ficha-itch.md').write_text(ficha_itch(spec, salida), encoding='utf-8')
    (kit / 'publicaciones.md').write_text(publicaciones(spec, salida), encoding='utf-8')
    (kit / 'plan-lanzamiento.md').write_text(plan(spec), encoding='utf-8')
    try:
        import novedad
        nov = novedad.evaluar(raiz, spec['id'])
    except (ImportError, KeyError, OSError, ValueError):
        nov = None
    texto_difusion = difusion(spec, salida, datos, resp, titulo_previo, nov)
    (kit / 'difusion.md').write_text(texto_difusion, encoding='utf-8')
    (kit / 'registro-creacion.md').write_text(registro_creacion(spec), encoding='utf-8')
    ficha_cg = kit / 'ficha-crazygames.md'
    if 'anuncios' in (spec.get('motor') or []) and (salida / 'medios' / 'crazygames').is_dir() and (spec.get('originalidad') or {}).get('riesgo_portales') != 'alto':   # solo con ganchos de anuncios, paquete de portadas y videos ya hecho y sin choque con la regla de originalidad
        import monetizar
        ficha_cg.write_text(monetizar.ficha_crazygames(raiz, spec, linea_ia(spec, 'en')), encoding='utf-8')
    elif ficha_cg.exists():
        ficha_cg.unlink()
    (kit / 'metricas.csv').write_text('fecha,juego,vistas,partidas_o_descargas,ingresos_usd,donaciones_usd,comentarios,fuente_de_trafico,notas\n', encoding='utf-8')
    for nombre in ('difusion.md', 'registro-creacion.md', 'publicaciones.md'):
        sobras = sorted(set(re.findall(r'\{[a-z_]+\}', (kit / nombre).read_text(encoding='utf-8'))))
        if sobras:
            problemas.append('%s: quedaron marcas sin resolver: %s' % (nombre, ', '.join(sobras)))
    if 'REVISAR' in texto_difusion:
        problemas.append('difusion.md: hay una respuesta marcada REVISAR (el juego declara anuncios)')
    faltan = []
    for idioma in spec['idiomas']:
        f = spec['ficha'][idioma]
        for k in ('titulo', 'corta', 'larga', 'controles'):
            if not f.get(k):
                faltan.append('ficha.%s.%s' % (idioma, k))
        d = (spec.get('difusion') or {}).get(idioma)
        if not d:
            faltan.append('difusion.' + idioma)
        else:
            for k in ('mensaje_clase', 'post_comunidad', 'devlog', 'guion_video'):
                if not d.get(k):
                    faltan.append('difusion.%s.%s' % (idioma, k))
    if not spec.get('etiquetas'):
        faltan.append('etiquetas')
    for k in ('originalidad', 'creacion', 'lanzamiento'):
        if not spec.get(k):
            faltan.append(k)
    orig = spec.get('originalidad') or {}
    for idioma in spec['idiomas']:
        if orig and not _diferenciador(spec, idioma):
            faltan.append('originalidad.diferenciador.' + idioma)
    avisos = []
    if portada_itch(salida)[0] == 'mal':
        avisos.append('la portada no tiene la proporción 315:250 que pide itch.io')
    for idioma in spec['idiomas']:
        pc = ((spec.get('difusion') or {}).get(idioma) or {}).get('post_corto')
        if pc:
            n = _largo_x(pc.replace('{enlace}', 'x' * 23).replace('{ia}', linea_ia(spec, idioma)))
            if n > 280:
                avisos.append('post_corto.%s pesa %d en X (límite 280: el chino y los emojis cuentan doble, el enlace cuenta 23)' % (idioma, n))
            g = _grafemas_con_enlace_del_sitio(raiz, spec, idioma, pc)
            if g > 285:
                avisos.append('post_corto.%s mide %d grafemas con el enlace del sitio y Bluesky admite 300: acórtalo para dejar margen a dominios más largos' % (idioma, g))
    print('[kit] %s → %s%s%s%s' % (spec['id'], kit, (' · FALTAN: ' + ', '.join(faltan)) if faltan else ' · completo',
                                 (' · AVISOS: ' + '; '.join(avisos)) if avisos else '',
                                 (' · PROBLEMAS: ' + '; '.join(problemas)) if problemas else ''))
    if problemas:
        sys.exit('[kit] %s: hay problemas que corregir antes de usar el kit' % spec['id'])
