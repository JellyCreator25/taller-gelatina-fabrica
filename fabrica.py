#!/usr/bin/env python3
"""Fábrica de juegos.

Cada juego es una ficha (juegos/<id>/juego.json) que apunta a una plantilla (plantillas/<nombre>/) y, opcionalmente, a paquetes.
La fábrica construye el juego, lo prueba en un navegador real, prepara el kit y el sitio propio, y publica solo lo que un humano
aprobó con la huella exacta del plan (ver LEEME.md y LEEME-DUENO.md).

Uso:
  python3 fabrica.py lista
  python3 fabrica.py construir [id|todos]
  python3 fabrica.py probar    [id|todos]     (necesita node y playwright)
  python3 fabrica.py kit       [id|todos]
  python3 fabrica.py revisar   [id|todos]     (comprueba que el kit esté completo y coherente)
  python3 fabrica.py todo      [id|todos]
  python3 fabrica.py mapa                     (escribe difusion/MAPA.md: qué canales puede publicar el motor solo)
  python3 fabrica.py novedad   [id|todos] [--estricto]   (¿es un juego distinto o una variante? ver herramientas/novedad.py)
  python3 fabrica.py ideas                    (el cuaderno de ideas frente a los juegos que ya hay)
  python3 fabrica.py nueva-plantilla NOMBRE --genero G --verbo V --objetivo O [--entrada a,b] [--progresion P]   (un género nuevo)
  python3 fabrica.py nuevo ID PLANTILLA       (ficha de juego nueva sobre una plantilla; lo que falte dice PENDIENTE)
  python3 fabrica.py ciclo [--probar]         (el latido semanal: reconstruye, revisa, genera el sitio y deja en publicacion/PENDIENTE.md qué hay listo para aprobar)
  python3 fabrica.py sitio                    (genera dist/sitio: el sitio propio en es/en/zh con los juegos de publicacion/sitio.json)
  python3 fabrica.py sitio --zip              (además deja dist/sitio.zip para arrastrarlo a Cloudflare Pages; se niega con datos de ejemplo)
  python3 fabrica.py perfiles [--texto]       (avatar, banner y textos de perfil de las cuentas de bot: difusion/perfiles/; --texto no usa navegador)
  python3 fabrica.py metricas ver [JUEGO]     (lo que hay en metricas/registro.csv por juego y semana)
  python3 fabrica.py metricas anotar JUEGO METRICA VALOR [--semana esta|pasada|AAAA-MM-DD] [--fuente F] [--nota T]   (agrega un dato al registro)
  python3 fabrica.py metricas cloudflare [--dias N] [--opcional]   (importa las vistas de Cloudflare Web Analytics; --opcional: sin claves, se omite)
  python3 fabrica.py rumbo [--detalle]        (qué construir después, según las métricas; con pocos datos explora; no construye ni publica nada)
  python3 fabrica.py huella ID [--solo canal,canal]       (la huella del plan de publicación, para aprobarlo)
  python3 fabrica.py publicar ID [--solo canal,canal]     (muestra el plan y las compuertas; no publica nada)
  python3 fabrica.py publicar ID --ejecutar --aprobar HUELLA   (publica EXACTAMENTE lo que esa huella cubre)
  python3 fabrica.py resolver ACCION salio|no-salio       (anota qué pasó con un envío que quedó en duda)
  python3 fabrica.py resolver --auto [ACCION]             (lo comprueba solo: lee la cuenta pública, sin claves, y anota lo que se pueda aclarar; corre cada día antes del calendario)
  python3 fabrica.py resolver --verificar                 (solo lectura: comprueba que esa lectura pública funciona con el último post que sí salió)
  python3 fabrica.py calendario [--aprobar HUELLA_DEL_LOTE | --ejecutar | --medir]   (publicaciones propias del calendario: se aprueban por lote y salen en su fecha; --medir anota likes, reposts y respuestas)
  python3 fabrica.py configurar bluesky-bot|bluesky-perfil|mastodon-bot [--ejecutar]   (ajustes en la cuenta del bot; bluesky-perfil pone bio, nombre, avatar y banner)
  python3 fabrica.py motor [probar]           (el motor que crece solo: techo, juegos por nivel y cola de mejoras; «probar» corre las pruebas del motor y guarda motor/informe.json)
  python3 fabrica.py calidad [id|todos]       (en qué nivel de la escalera de calidad está cada juego, qué le falta y qué nivel se le exige para lanzarse)
  python3 fabrica.py monetizar [estado|escenarios [N…]|variantes ID [portal]|envio ID]   (qué falta para cobrar por ruta, cuentas con supuestos, versiones para portales y paquete de envío a CrazyGames; el estado también entra a publicacion/PENDIENTE.md)
  python3 fabrica.py administrador [chequeo|guardia|flujos [--reactivar]|anotar "TEXTO" --resultado R [--commit C]|bitacora [N]]   (el administrador del motor, carta en motor/ADMINISTRADOR.md: mira la salud y la autonomía, y deja constancia en motor/bitacora.jsonl; «flujos --reactivar» vuelve a encender los flujos que GitHub apague por inactividad; no aprueba ni publica)
  python3 fabrica.py autonomia [estado|registrar|revisar]   (objetivo secundario del motor: cuánto corre la fábrica sin Max, qué le toca a él y qué reglas podría autorizar; «registrar» anota la fila de la semana en metricas/autonomia.csv)
"""
import base64
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.parse
import zipfile

RAIZ = pathlib.Path(__file__).resolve().parent
SALIDA = RAIZ / 'salida'
OBLIGATORIOS = ['id', 'plantilla', 'version', 'idiomas', 'ficha']


def ids():
    return sorted(p.parent.name for p in (RAIZ / 'juegos').glob('*/juego.json'))


def cargar(juego_id):
    ruta = RAIZ / 'juegos' / juego_id / 'juego.json'
    if not ruta.exists():
        sys.exit('No existe la ficha %s. Fichas disponibles: %s' % (ruta, ', '.join(ids()) or 'ninguna'))
    spec = json.loads(ruta.read_text(encoding='utf-8'))
    faltan = [k for k in OBLIGATORIOS if k not in spec]
    if faltan:
        sys.exit('%s: faltan campos obligatorios: %s' % (ruta, ', '.join(faltan)))
    if spec['id'] != juego_id:
        sys.exit('%s: el id de la ficha (%s) no coincide con la carpeta (%s)' % (ruta, spec['id'], juego_id))
    for idioma in spec['idiomas']:
        if idioma not in spec['ficha']:
            sys.exit('%s: idiomas incluye "%s" pero ficha no tiene texto en ese idioma' % (ruta, idioma))
    validar_idiomas(ruta, spec)
    return spec


def _cadenas(o):
    """Todas las cadenas de un objeto JSON (para revisar caracteres)."""
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from _cadenas(v)
    elif isinstance(o, list):
        for v in o:
            yield from _cadenas(v)


def chinos_fuera_de_gb2312(texto):
    return {c for c in texto if ('\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf') and not c.encode('gb2312', 'ignore')}


def validar_idiomas(ruta, spec):
    """Todos los idiomas del juego deben tener las mismas claves de texto y las mismas marcas {n}; el chino, solo caracteres que
    cualquier tipografía china trae (se usa el conjunto GB2312: si un carácter queda fuera, algunos dispositivos mostrarían un cuadro vacío)."""
    idiomas = spec['idiomas']
    textos = spec.get('textos') or {}
    if textos:
        for l in idiomas:
            if l not in textos:
                sys.exit('%s: idiomas incluye "%s" pero textos no tiene ese idioma' % (ruta, l))
        base = textos[idiomas[0]]
        for l in idiomas[1:]:
            faltan, sobran = sorted(set(base) - set(textos[l])), sorted(set(textos[l]) - set(base))
            if faltan or sobran:
                sys.exit('%s: textos[%s] no coincide con textos[%s]. Faltan: %s. Sobran: %s' % (ruta, l, idiomas[0], ', '.join(faltan) or '-', ', '.join(sobran) or '-'))
        for k in base:
            marcas = {l: frozenset(re.findall(r'\{(\w+)\}', str(textos[l][k]))) for l in idiomas}
            if len(set(marcas.values())) > 1:
                sys.exit('%s: el texto «%s» usa marcas distintas según el idioma: %s' % (ruta, k, {l: sorted(m) for l, m in marcas.items()}))
            vacios = [l for l in idiomas if not str(textos[l][k]).strip()]
            if vacios:
                sys.exit('%s: el texto «%s» está vacío en %s' % (ruta, k, ', '.join(vacios)))
    if 'zh' in idiomas:
        propios = [textos.get('zh', {}), spec['ficha'].get('zh', {}), (spec.get('difusion') or {}).get('zh', {})]
        extra = [v.get('zh') for v in (spec.get('parametros') or {}).get('_i18n', [])] if isinstance((spec.get('parametros') or {}).get('_i18n'), list) else []
        fuera = set()
        for s in _cadenas(propios + extra):
            for c in s:
                if ('一' <= c <= '鿿' or '㐀' <= c <= '䶿') and not c.encode('gb2312', 'ignore'):
                    fuera.add(c)
        if fuera:
            sys.exit('%s: caracteres chinos fuera de GB2312 (podrían verse como cuadros vacíos): %s' % (ruta, ' '.join(sorted(fuera))))


def seleccion(arg):
    if not arg or arg == 'todos':
        return ids()
    return [arg]


def js_json(obj):
    """JSON seguro para ir dentro de un <script> (no puede cerrar la etiqueta ni romper líneas)."""
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    return s.replace('</', '<\\/').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def fuentes_css(familias):
    mapa = json.loads((RAIZ / 'motor' / 'fuentes' / 'fuentes.json').read_text(encoding='utf-8'))
    css = ''
    for fam in familias:
        if fam not in mapa:
            sys.exit('Tipografía "%s" no está en motor/fuentes/fuentes.json' % fam)
        for peso, archivo in mapa[fam].items():
            b64 = base64.b64encode((RAIZ / 'motor' / 'fuentes' / archivo).read_bytes()).decode()
            css += ("@font-face{font-family:'%s';font-style:normal;font-weight:%s;font-display:swap;"
                    "src:url(data:font/woff2;base64,%s) format('woff2')}\n" % (fam, peso, b64))
    return css


def icono(spec):
    color = (spec.get('portada') or {}).get('color_a', '#2f6bdc')
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
           "<ellipse cx='32' cy='37' rx='27' ry='22' fill='%s'/>"
           "<ellipse cx='23' cy='32' rx='6' ry='7' fill='#fff'/><ellipse cx='41' cy='32' rx='6' ry='7' fill='#fff'/>"
           "<circle cx='24.5' cy='33.5' r='3' fill='#14251b'/><circle cx='42.5' cy='33.5' r='3' fill='#14251b'/></svg>" % color)
    return 'data:image/svg+xml,' + urllib.parse.quote(svg)


def attr(texto):
    return texto.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')


def construir(juego_id, spec=None, destino=None, cabeza_extra=''):
    """Sin argumentos extra construye el juego a salida/<id>/. Una versión para un portal (monetizar variantes) pasa su propia ficha, su carpeta y lo que va en la cabecera."""
    spec = spec if spec is not None else cargar(juego_id)
    base = RAIZ / 'plantillas' / spec['plantilla']
    fuente = (base / 'plantilla.html').read_text(encoding='utf-8')
    if not fuente.startswith('<style>\n'):
        sys.exit('La plantilla %s debe empezar con <style> (sin <html>, <head> ni <title>)' % spec['plantilla'])
    fin_css = fuente.index('</style>\n')
    css = fuente[len('<style>\n'):fin_css]
    cuerpo = fuente[fin_css + len('</style>\n'):]
    if '<style' in cuerpo:
        sys.exit('La plantilla solo puede tener un bloque <style>, al principio')

    # Configuración y motor común, antes del primer <script> de la plantilla
    cfg = {'id': spec['id'], 'version': spec['version'], 'idiomas': spec['idiomas'],
           'titulo': spec['ficha'][spec['idiomas'][0]]['titulo'], 'apoyo_url': spec.get('apoyo_url', '')}
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    import monetizar as monet_mod
    anuncios = monet_mod.configuracion_de(RAIZ, spec)      # None mientras ninguna ruta de anuncios esté encendida: el juego sale idéntico
    if anuncios:
        cfg['anuncios'] = anuncios
    ggx = (RAIZ / 'motor' / 'ggx.js').read_text(encoding='utf-8')
    fuera = chinos_fuera_de_gb2312(fuente)
    if fuera:
        sys.exit('La plantilla %s tiene caracteres chinos fuera de GB2312: %s' % (spec['plantilla'], ' '.join(sorted(fuera))))
    inyeccion = ('<script>window.GGX_CONFIG=%s;window.JUEGO=%s;</script>\n<script id="ggx">\n%s</script>\n'
                 % (js_json(cfg), js_json({'parametros': spec.get('parametros', {}), 'textos': spec.get('textos', {})}), ggx))
    # Módulos opcionales del motor (juego.json → «motor»): después del núcleo y antes del código del juego. Sin «motor», nada cambia.
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    import motor as motor_mod
    try:
        modulos = motor_mod.modulos_de(RAIZ, spec)
    except motor_mod.ErrorMotor as e:
        sys.exit('%s: %s' % (spec['id'], e))
    for nombre, _, texto in modulos:
        fuera = chinos_fuera_de_gb2312(texto)
        if fuera:
            sys.exit('El módulo %s tiene caracteres chinos fuera de GB2312: %s' % (nombre, ' '.join(sorted(fuera))))
        inyeccion += '<script id="mod-%s">\n%s</script>\n' % (nombre, texto)
    m = re.search(r'^<script', cuerpo, re.M)
    cuerpo = (cuerpo[:m.start()] + inyeccion + cuerpo[m.start():]) if m else (cuerpo + inyeccion)

    # Paquetes opcionales de la plantilla (siempre al final, después del núcleo)
    for paquete in spec.get('paquetes', []):
        ruta = base / 'paquetes' / (paquete + '.js')
        if not ruta.exists():
            sys.exit('Paquete "%s" no existe en %s' % (paquete, ruta))
        cuerpo = cuerpo.rstrip('\n') + '\n\n<script id="pack-%s">\n%s</script>\n' % (paquete, ruta.read_text(encoding='utf-8'))

    primero = spec['idiomas'][0]
    html = (RAIZ / 'motor' / 'envoltura.html').read_text(encoding='utf-8')
    if cabeza_extra:
        html = html.replace('<head>', '<head>\n' + cabeza_extra.rstrip('\n'), 1)
    for marca, valor in (('@@LANG@@', primero), ('@@TITULO@@', attr(spec['ficha'][primero]['titulo'])),
                         ('@@DESCRIPCION@@', attr(spec['ficha'][primero]['corta'])), ('@@ICONO@@', icono(spec)),
                         ('@@FUENTES@@', fuentes_css(spec.get('fuentes', ['Fredoka', 'Nunito Sans']))),
                         ('@@CSS@@', css), ('@@CUERPO@@', cuerpo)):
        html = html.replace(marca, valor)

    if 'fonts.googleapis' in html or 'fonts.gstatic' in html or 'claude:' in html:
        sys.exit('El resultado todavía depende de Google Fonts o de metadatos del Artifact')
    externos = sorted(set(u for u in re.findall(r'https?://[^\s"\'<>)\\]+', html) if not u.startswith('http://www.w3.org/')))

    destino = pathlib.Path(destino) if destino else SALIDA / juego_id
    destino.mkdir(parents=True, exist_ok=True)
    (destino / 'index.html').write_text(html, encoding='utf-8')
    zip_ruta = destino / ('%s-web.zip' % juego_id)
    with zipfile.ZipFile(zip_ruta, 'w', zipfile.ZIP_STORED) as z:
        # index.html en la raíz del zip, con fecha y permisos fijos: el mismo juego da siempre el mismo zip (la huella de aprobación lo necesita).
        # Sin compresión a propósito: el resultado de comprimir cambia con la versión de Python y de zlib de cada máquina (GitHub usa otra que
        # la tuya), y entonces «lo guardado» y «lo que se reconstruye» dejarían de coincidir aunque el juego sea el mismo.
        info = zipfile.ZipInfo('index.html', date_time=(2020, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_STORED
        info.external_attr = 0o644 << 16
        z.writestr(info, (destino / 'index.html').read_bytes())
    print('[construir] %s v%s → %s (%d KB) · zip %d KB%s' % (
        juego_id, spec['version'], destino / 'index.html', len(html.encode()) // 1024, zip_ruta.stat().st_size // 1024,
        (' · enlaces externos en el código: ' + ', '.join(externos)) if externos else ' · sin enlaces externos'))
    return destino


def probar(juego_id):
    spec = cargar(juego_id)
    salida = SALIDA / juego_id
    if not (salida / 'index.html').exists():
        construir(juego_id)
    r = subprocess.run(['node', str(RAIZ / 'herramientas' / 'probar.js'), juego_id], cwd=str(RAIZ))
    if r.returncode != 0:
        sys.exit('[probar] %s: hay pruebas que fallaron (ver %s)' % (juego_id, salida / 'informe-pruebas.txt'))
    print('[probar] %s: todo en orden' % spec['id'])


def kit(juego_id):
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    import kit_lanzamiento
    kit_lanzamiento.generar(RAIZ, cargar(juego_id))


def revisar(juego_id):
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    import revisar_kit
    errores, avisos = revisar_kit.revisar(RAIZ, juego_id)
    for a in avisos:
        print('[revisar] %s: AVISO %s' % (juego_id, a))
    if errores:
        sys.exit('[revisar] %s: %s' % (juego_id, '; '.join(errores)))
    print('[revisar] %s: kit coherente' % juego_id)


def mapa():
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    import kit_lanzamiento
    import mapa_canales
    datos = json.loads((RAIZ / 'difusion' / 'canales.json').read_text(encoding='utf-8'))
    problemas = kit_lanzamiento.validar_canales(datos)
    if problemas:
        sys.exit('[mapa] canales.json tiene problemas:\n  - ' + '\n  - '.join(problemas))
    mapa_canales.generar(RAIZ)
    print('[mapa] difusion/MAPA.md escrito (%d canales)' % len(datos['canales']))


def novedad(objetivo, estricto=False):
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    import novedad as nov
    hay_error = hay_variante = False
    for i in seleccion(objetivo):
        r = nov.evaluar(RAIZ, i)
        print(nov.informe(r))
        hay_error |= bool(r['errores'])
        hay_variante |= r['veredicto'] == 'variante'
    if hay_error:
        sys.exit(1)
    if estricto and hay_variante:
        sys.exit(2)


def ideas():
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    import novedad as nov
    print('Cuaderno de ideas frente a los juegos que ya existen (cada idea es un género por construir):')
    for idea, r in nov.evaluar_ideas(RAIZ):
        m = idea['mecanica']
        frente = 'ya construida' if nov.ya_construida(RAIZ, idea) else '; '.join('%s: %s' % (c['con'], c['veredicto']) for c in r['comparaciones'])
        print('  %-9s %-16s %-14s %-13s riesgo %-5s · %s' % (idea['id'], m['genero'], m['verbo'], m['objetivo'], idea.get('riesgo_estimado', '?'), frente))
        for e in r['errores']:
            print('     ERROR', e)


def _opcion(nombre, defecto=None):
    if nombre in sys.argv:
        i = sys.argv.index(nombre)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return defecto


def nueva_plantilla(nombre):
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    import andamio
    faltan = [o for o in ('--genero', '--verbo', '--objetivo') if not _opcion(o)]
    if faltan:
        sys.exit('Faltan %s: una plantilla nueva declara su núcleo desde el principio (valores en catalogo/vocabulario.json).' % ', '.join(faltan))
    d = andamio.nueva_plantilla(RAIZ, nombre, _opcion('--genero'), _opcion('--verbo'), _opcion('--objetivo'),
                                _opcion('--entrada', 'toque').split(','), _opcion('--progresion', 'niveles-fijos'))
    print('[nueva-plantilla] %s creada en %s\n  Siguiente: completa DISENO.md, reemplaza el juego de ejemplo de plantilla.html y prueba.js, y crea el juego con `nuevo ID %s`.' % (nombre, d, nombre))


def nuevo(juego_id, plantilla):
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    import andamio
    d = andamio.nuevo_juego(RAIZ, juego_id, plantilla)
    print('[nuevo] %s creado en %s\n  Completa los campos PENDIENTE y declara mecanica.ambientacion y mecanica.arte; después `python3 fabrica.py todo %s`.' % (juego_id, d, juego_id))


def _zip_del_sitio():
    """dist/sitio.zip, listo para arrastrar a Cloudflare Pages (subida directa): index.html en la raíz del zip y bytes reproducibles."""
    sys.path.insert(0, str(RAIZ))
    from publicacion import nucleo
    cfg = json.loads((RAIZ / 'publicacion' / 'sitio.json').read_text(encoding='utf-8'))
    faltan = []
    if nucleo._marca_de_ejemplo(cfg.get('proyecto')):
        faltan.append('«proyecto» (el nombre del proyecto de Cloudflare Pages)')
    if nucleo._marca_de_ejemplo(cfg.get('url_base')) or not str(cfg.get('url_base', '')).startswith('https://'):
        faltan.append('«url_base» (la dirección https real, hoy dice «%s»)' % cfg.get('url_base'))
    if not str(cfg.get('contacto', '')).strip():
        faltan.append('«contacto» (el contacto público de la política de privacidad)')
    if faltan:
        sys.exit('[sitio] --zip: el zip se niega a salir con datos de ejemplo; completa en publicacion/sitio.json: ' + '; '.join(faltan))
    origen = RAIZ / 'dist' / 'sitio'
    destino = RAIZ / 'dist' / 'sitio.zip'
    with zipfile.ZipFile(destino, 'w') as z:
        for ruta in sorted(p for p in origen.rglob('*') if p.is_file()):
            zi = zipfile.ZipInfo(ruta.relative_to(origen).as_posix(), (1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, ruta.read_bytes())
    print('[sitio] dist/sitio.zip listo (%d KB): arrástralo a tu proyecto de Cloudflare Pages (subida directa). No pasa por la aprobación de «publicar»: subirlo es tu aprobación.' % (destino.stat().st_size // 1024))


def generar_sitio(con_zip=False):
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    sys.path.insert(0, str(RAIZ))
    import sitio as gen
    try:
        m = gen.generar(RAIZ)
    except gen.ErrorSitio as e:
        sys.exit('[sitio] ' + str(e))
    print('[sitio] dist/sitio generado: %d juego(s) (%s) · huella %s…' % (len(m['juegos']), ', '.join(sorted(m['juegos'])) or 'ninguno', m['huella'][:12]))
    if 'CAMBIA' in m['url_base'].upper():
        print('[sitio] AVISO: sitio.json todavía tiene la dirección de ejemplo; sirve para ver el sitio en tu computadora, pero el motor no lo publica así.')
    if con_zip:
        _zip_del_sitio()


def _publicacion():
    sys.path.insert(0, str(RAIZ))
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    from publicacion import nucleo
    from publicacion.adaptadores import ADAPTADORES
    return nucleo, ADAPTADORES


def _plan(juego_id):
    if not juego_id or juego_id == 'todos':
        sys.exit('Indica el juego: ' + ', '.join(ids()))
    nucleo, adaptadores = _publicacion()
    cargar(juego_id)
    ctx = nucleo.Contexto(RAIZ, juego_id)
    solo = set(_opcion('--solo').split(',')) if _opcion('--solo') else None
    plan, problemas = nucleo.construir_plan(ctx, adaptadores, solo)
    return nucleo, adaptadores, ctx, plan, problemas


def huella(juego_id):
    print(_plan(juego_id)[3]['huella'])


def publicar(juego_id):
    nucleo, adaptadores, ctx, plan, problemas = _plan(juego_id)
    ent = nucleo.Entorno()
    razones = nucleo.compuertas(ctx, plan, problemas, ent.ahora())
    print(nucleo.mostrar_plan(ctx, plan, problemas, razones))
    if '--ejecutar' not in sys.argv:
        return
    try:
        informe, ok = nucleo.ejecutar(ctx, plan, problemas, _opcion('--aprobar'), ent, adaptadores)
    except nucleo.ErrorPublicacion as e:
        sys.exit('[publicar] ' + str(e))
    print('\nResultado:')
    for l in informe:
        print('  %-9s %-16s %s — %s' % (l['resultado'], l['canal'], l['accion'], l['detalle']))
    if not ok:
        sys.exit('[publicar] hubo acciones sin completar (ver arriba). Lo que salió quedó anotado en publicacion/libro.jsonl')


def calendario_cmd():
    """calendario | calendario --aprobar HUELLA_DEL_LOTE | calendario --ejecutar | calendario --medir"""
    nucleo, adaptadores = _publicacion()
    from publicacion import calendario, resultados
    ent = nucleo.Entorno()
    hoy = ent.ahora().date()
    try:
        if '--medir' in sys.argv:
            nuevos = resultados.medir(RAIZ, ent.ahora(), ent)
            print('[resultados] %d medición(es) nueva(s)' % len(nuevos))
            print('\n'.join(resultados.resumen(RAIZ)))
            return
        if _opcion('--aprobar'):
            ids = calendario.aprobar(RAIZ, hoy, _opcion('--aprobar'))
            print('[calendario] aprobadas %d publicación(es): %s\nQueda anotado en contenido/aprobaciones.json: súbelo al repositorio para que la tarea diaria lo vea.' % (len(ids), ', '.join(ids)))
            return
        if '--ejecutar' in sys.argv:
            informe, ok = calendario.ejecutar(RAIZ, hoy, ent, adaptadores)
            publicadas = [l for l in informe if l['resultado'] == 'ok']
            print('Calendario del %s: %s' % (hoy.isoformat(), '%d publicada(s)' % len(publicadas) if publicadas else 'nada que publicar hoy'))
            for l in informe:
                print('  %-9s %-9s %s — %s' % (l['resultado'], l['canal'], l['accion'], l['detalle']))
            if not ok:
                sys.exit('[calendario] algo quedó sin completar o en duda (ver arriba). Lo que salió quedó anotado en publicacion/libro.jsonl')
            return
        print(calendario.mostrar(calendario.estado(RAIZ, hoy)))
    except calendario.ErrorCalendario as e:
        sys.exit('[calendario] ' + str(e))
    except resultados.ErrorResultados as e:
        sys.exit('[resultados] ' + str(e))


def resolver(accion_id, resultado):
    nucleo, _ = _publicacion()
    if resultado not in ('salio', 'no-salio'):
        sys.exit('Uso: python3 fabrica.py resolver ACCION salio|no-salio')
    libro = nucleo.Libro(RAIZ / 'publicacion' / 'libro.jsonl')
    try:
        nucleo.resolver(libro, accion_id, resultado == 'salio', nucleo.Entorno().ahora())
    except nucleo.ErrorPublicacion as e:
        sys.exit('[resolver] ' + str(e))
    print('[resolver] %s anotado como «%s»' % (accion_id, 'salió' if resultado == 'salio' else 'no salió (podrá reintentarse)'))


def resolver_auto(modo, accion=None):
    """resolver --auto [ACCION] | --verificar. Lee la cuenta pública (sin claves) y, con --auto, anota en el libro lo que logre aclarar; lo que no, sigue en duda."""
    nucleo, _ = _publicacion()
    from publicacion import comprobar
    libro = nucleo.Libro(RAIZ / 'publicacion' / 'libro.jsonl')
    ent = nucleo.Entorno()
    if modo == '--verificar':
        estado, texto = comprobar.verificar(ent.http, libro.entradas())
        print('[resolver] lectura pública: %s · %s' % (estado, texto))
        if estado == 'falla':
            sys.exit(1)
        return
    if not comprobar.en_duda(libro.entradas()) and not accion:
        print('[resolver] nada en duda: no hay envíos por comprobar')
        return
    try:
        informe = comprobar.resolver_en_duda(libro, ent.http, ent.ahora(), accion)
    except nucleo.ErrorPublicacion as e:
        sys.exit('[resolver] ' + str(e))
    nombres = {'salio': 'SALIÓ (anotado como hecho)', 'no-salio': 'NO SALIÓ (anotado como descartado; podrá reintentarse)', 'sigue-en-duda': 'SIGUE EN DUDA'}
    for r in informe:
        print('[resolver] %s · %s — %s' % (r['accion'], nombres[r['estado']], r['motivo']))
    quedan = [r for r in informe if r['estado'] == 'sigue-en-duda']
    if quedan:
        print('[resolver] %d envío(s) siguen en duda: mira la cuenta y anota con `python3 fabrica.py resolver ACCION salio|no-salio`' % len(quedan))


def configurar(que):
    nucleo, _ = _publicacion()
    from publicacion import red
    from publicacion.adaptadores import bluesky, mastodon
    tareas = {'bluesky-bot': (bluesky.marcar_bot, ['BSKY_IDENTIFIER', 'BSKY_APP_PASSWORD'], 'poner la etiqueta «bot» en el perfil de Bluesky (conserva el resto del perfil)'),
              'bluesky-perfil': (lambda ent, politica: bluesky.actualizar_perfil(ent, politica, RAIZ), ['BSKY_IDENTIFIER', 'BSKY_APP_PASSWORD'],
                                 'poner nombre, biografía, avatar y banner de difusion/perfiles/ en el perfil de Bluesky (conserva la etiqueta «bot» y el resto del perfil)'),
              'mastodon-bot': (mastodon.marcar_bot, ['MASTODON_INSTANCE', 'MASTODON_TOKEN'], 'marcar la cuenta de Mastodon como bot')}
    if que not in tareas:
        sys.exit('Ajustes disponibles: ' + ', '.join(sorted(tareas)))
    funcion, secretos, descripcion = tareas[que]
    print('Va a %s. Claves que lee del entorno: %s.' % (descripcion, ', '.join(secretos)))
    if que == 'bluesky-perfil':   # lo que se pondrá, revisado contra los límites, sin abrir sesión: así la corrida en seco ya sirve para aprobarlo
        try:
            print(bluesky.resumen_de_perfil(RAIZ))
        except nucleo.ErrorPlan as e:
            sys.exit('[configurar] ' + str(e))
    if '--ejecutar' not in sys.argv:
        print('(no cambió nada; agrega --ejecutar para hacerlo)')
        return
    ent = nucleo.Entorno()
    faltan = [x for x in secretos if not ent.env.get(x)]
    if faltan:
        sys.exit('Faltan en el entorno: ' + ', '.join(faltan))
    try:
        print(funcion(ent, nucleo.cargar_json(RAIZ / 'publicacion' / 'politica.json', {})))
    except (nucleo.ErrorPublicacion, red.ErrorRed) as e:
        sys.exit('[configurar] ' + red.redactar(e, [ent.env.get(x) for x in secretos]))


def _herramientas():
    if str(RAIZ / 'herramientas') not in sys.path:
        sys.path.insert(0, str(RAIZ / 'herramientas'))


def _resumen_de_corrida(texto):
    ruta = os.environ.get('GITHUB_STEP_SUMMARY')
    if ruta:
        with open(ruta, 'a', encoding='utf-8') as f:
            f.write(texto + '\n')


def metricas_cmd(args):
    _herramientas()
    import metricas as met
    sub = args[0] if args else ''
    ids_ok = set(ids())
    try:
        if sub == 'ver':
            print(met.tabla(RAIZ, args[1] if len(args) > 1 and not args[1].startswith('--') else None, ids_ok))
        elif sub == 'anotar' and len(args) >= 4:
            f = met.anotar(RAIZ, args[1], args[2], args[3], _opcion('--semana', 'esta'), _opcion('--fuente', 'manual'), _opcion('--nota', ''), ids_ok)
            print('Anotado: %s · %s · %s = %s (fuente %s)%s' % (f['semana'].isoformat(), f['juego'], f['metrica'], f['valor'], f['fuente'],
                  '. Es la semana en curso: no cuenta para decidir hasta que termine.' if f['en_curso'] else ''))
        elif sub == 'cloudflare':
            nucleo, _ = _publicacion()
            ent = nucleo.Entorno()
            if not (ent.env.get(met.VARIABLE_TOKEN) and ent.env.get(met.VARIABLE_CUENTA)) and '--opcional' in args:
                print('[metricas] sin %s y %s: no se importa nada (es opcional).' % (met.VARIABLE_TOKEN, met.VARIABLE_CUENTA))
                return
            try:
                r = met.importar_cloudflare(RAIZ, ent, ids_ok, int(_opcion('--dias', 21)))
            except met.ErrorMetricas as e:
                _resumen_de_corrida('### Importación de Cloudflare Web Analytics\n\nFalló: %s\n' % e)
                raise
            linea = '%s desde %s: %d filas nuevas, %d sin cambio (%d grupos leídos).' % (r['host'], r['desde'].isoformat(), r['escritas'], r['sin_cambio'], r['grupos'])
            print('[metricas] ' + linea)
            if r['aviso']:
                print('[metricas] aviso: ' + r['aviso'])
            _resumen_de_corrida('### Importación de Cloudflare Web Analytics\n\n%s%s\n' % (linea, ('\n\nAviso: ' + r['aviso']) if r['aviso'] else ''))
        else:
            sys.exit('Uso: metricas ver [JUEGO] | metricas anotar JUEGO METRICA VALOR [--semana S] [--fuente F] [--nota T] | metricas cloudflare [--dias N] [--opcional]\n'
                     'Métricas: ' + ', '.join(sorted(met.cargar_politica(RAIZ)['metricas'])))
    except (met.ErrorMetricas, ValueError) as e:
        if isinstance(e, ValueError) and not isinstance(e, met.ErrorMetricas):
            sys.exit('[metricas] valor no válido: %s' % e)
        sys.exit('[metricas] ' + str(e))


def rumbo_cmd(args):
    _herramientas()
    import metricas as met
    import rumbo
    try:
        print('\n'.join(rumbo.informe(rumbo.recomendar(RAIZ), detalle='--detalle' in args)))
    except met.ErrorMetricas as e:
        sys.exit('[rumbo] ' + str(e))


def _captura(paso, *args):
    """Corre un paso que puede terminar con sys.exit; devuelve el mensaje de error o None si salió bien."""
    try:
        paso(*args)
        return None
    except SystemExit as e:
        return str(e.code) if e.code not in (None, 0) else None


def ciclo():
    """Todo lo que se puede hacer sin claves y sin red: reconstruir, revisar, generar el sitio y armar el estado de cada juego."""
    nucleo, adaptadores = _publicacion()
    import novedad as nov
    errores = []
    for i in ids():
        for nombre, paso in (('construir', construir), ('probar', probar), ('kit', kit), ('revisar', revisar)):
            if nombre == 'probar' and '--probar' not in sys.argv:
                continue
            e = _captura(paso, i)
            if e:
                errores.append('%s · %s: %s' % (i, nombre, e))
    e = _captura(generar_sitio)
    if e:
        errores.append('sitio: ' + e)
    ent = nucleo.Entorno()
    sitio = nucleo.cargar_json(RAIZ / 'publicacion' / 'sitio.json', {})
    politica = nucleo.cargar_json(RAIZ / 'publicacion' / 'politica.json', {})
    L = ['# Estado de la fábrica', '', 'Lo escribe `python3 fabrica.py ciclo`. No contiene claves; las únicas fechas son las del calendario aprobado (sección «Autonomía»). Lo que sale en el libro está en `publicacion/libro.jsonl`.', '']
    if errores:
        L += ['## Pasos que fallaron', ''] + ['- ' + x for x in errores] + ['']
    for i in ids():
        spec = cargar(i)
        L += ['## %s (v%s)' % (i, spec['version']), '']
        ctx = nucleo.Contexto(RAIZ, i)
        r = nov.evaluar(RAIZ, i)
        L.append('- Novedad: %s%s' % (r['veredicto'], (' — ' + ' '.join(r['motivos'])) if r['motivos'] else ''))
        if i not in (sitio.get('juegos') or []):
            L += ['- **Fuera del sitio.** Para lanzarlo: agrégalo a `publicacion/sitio.json` → `juegos`, corre `python3 fabrica.py ciclo` y vuelve a leer este archivo.', '']
            continue
        plan, problemas = nucleo.construir_plan(ctx, adaptadores)
        razones = nucleo.compuertas(ctx, plan, problemas, ent.ahora())
        dudosos = [a for a in plan['acciones'] if ctx.libro.incierto(a['id'])]
        pendientes = [a for a in plan['acciones'] if not ctx.libro.hecho(a['id'])]
        if dudosos:
            L.append('- **Hay envíos en duda** (pudieron salir o no). Mira la cuenta y anota qué pasó:')
            L += ['  - `python3 fabrica.py resolver --auto` (o, si sigue en duda, `python3 fabrica.py resolver %s salio|no-salio`)' % a['id'] for a in dudosos]
        if problemas or razones:
            L.append('- **Bloqueado:**')
            L += ['  - ' + x for x in problemas + [x for x in razones if x not in problemas]]
        elif not pendientes:
            L.append('- Al día: todo lo del plan ya salió.')
        elif not dudosos:
            L.append('- **Listo para aprobar** (%d acciones pendientes: %s).' % (len(pendientes), ', '.join(sorted({a['canal'] for a in pendientes}))))
            L.append('  Lee el plan con `python3 fabrica.py publicar %s` y, si está bien: `python3 fabrica.py publicar %s --ejecutar --aprobar %s`' % (i, i, plan['huella'][:16]))
        L.append('')
    L += ['## Qué construir después', '']
    try:
        import rumbo
        L += rumbo.informe(rumbo.recomendar(RAIZ))
    except Exception as e:      # un registro dañado no debe impedir el resto del estado, pero sí quedar a la vista y hacer fallar el ciclo
        errores.append('rumbo: %s' % e)
        L += ['No se pudo calcular el rumbo: %s' % e]
    L += ['', '## Motor: calidad y qué sigue', '']
    try:
        import motor as motor_mod
        juegos, entradas = _juegos_y_libro()
        motor_mod.sincronizar(RAIZ, entradas)      # el piso solo sube: lo mejor ya publicado queda anotado en motor/piso.json
        L += motor_mod.informe_de_estado(RAIZ, entradas, juegos)
    except Exception as e:
        errores.append('motor: %s' % e)
        L += ['No se pudo calcular el estado del motor: %s' % e]
    L += ['', '## Monetización: qué falta para cobrar', '']
    try:
        import monetizar as monet_mod
        L += monet_mod.informe(RAIZ, sys.modules[__name__])
    except Exception as e:
        errores.append('monetizacion: %s' % e)
        L += ['No se pudo calcular el estado de la monetización: %s' % e]
    L += ['', '## Autonomía: cuánto corre la fábrica sin Max', '']
    try:
        sys.path.insert(0, str(RAIZ / 'herramientas'))
        import autonomia as aut
        hoy, lineas, listos = _estado_para_autonomia()
        L += aut.informe(RAIZ, hoy, lineas, listos, completo=False)
        aut.registrar(RAIZ, hoy, aut.medir(aut.catalogo(RAIZ)), aut.dias_aprobados(lineas, hoy)[0])
    except Exception as e:
        errores.append('autonomia: %s' % e)
        L += ['No se pudo calcular la autonomía: %s' % e]
    L += ['', '## Bluesky: qué ha funcionado', '']
    try:
        from publicacion import resultados
        L += resultados.resumen(RAIZ)
    except Exception as e:
        errores.append('resultados: %s' % e)
        L += ['No se pudieron leer los resultados: %s' % e]
    L += ['', 'Canales y qué hace cada uno solo: `difusion/MAPA.md`. Canales activos hoy: %s.' % (', '.join(politica.get('canales', [])) or 'ninguno'), '']
    texto = '\n'.join(L)
    (RAIZ / 'publicacion' / 'PENDIENTE.md').write_text(texto, encoding='utf-8')
    print(texto)
    resumen = os.environ.get('GITHUB_STEP_SUMMARY')
    if resumen:
        with open(resumen, 'a', encoding='utf-8') as f:
            f.write(texto + '\n')
    if errores:
        sys.exit('[ciclo] %d paso(s) fallaron' % len(errores))


def _juegos_y_libro():
    nucleo, _ = _publicacion()
    libro = nucleo.Libro(RAIZ / 'publicacion' / 'libro.jsonl')
    return [cargar(i) for i in ids()], libro.entradas()


def motor_cmd(args):
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    import motor as motor_mod
    if args and args[0] == 'probar':
        import tempfile
        with tempfile.TemporaryDirectory(prefix='ggx-motor-') as tmp:
            pagina = pathlib.Path(tmp) / 'prueba.html'
            pagina.write_text(motor_mod.pagina_de_prueba(RAIZ), encoding='utf-8')
            r = subprocess.run(['node', str(RAIZ / 'herramientas' / 'probar_motor.js'), str(pagina)], cwd=str(RAIZ), capture_output=True, text=True)
        lineas = [l for l in r.stdout.splitlines() if l.startswith('{')]
        if not lineas:
            sys.exit('[motor] las pruebas no devolvieron resultado (¿están node y playwright?):\n%s' % (r.stderr or r.stdout)[-600:])
        inf = motor_mod.escribir_informe(RAIZ, json.loads(lineas[-1]))
        print('[motor] núcleo v%s: %d pruebas, %d fallas' % (inf['nucleo']['version'], inf['nucleo']['pruebas'], inf['nucleo']['fallas']))
        for n, m in inf['modulos'].items():
            print('[motor] módulo %-10s v%s: %d pruebas, %d fallas' % (n, m['version'], m['pruebas'], m['fallas']))
        for fallo in inf['nucleo']['fallos'] + [f for m in inf['modulos'].values() for f in m['fallos']]:
            print('  FALLA · ' + fallo)
        if not inf['ok']:
            sys.exit('[motor] hay pruebas del motor que fallan')
        print('[motor] todo en orden (huella %s)' % inf['fuente'])
        return
    if args and args[0] != 'estado':
        sys.exit('Uso: python3 fabrica.py motor [estado|probar]')
    juegos, entradas = _juegos_y_libro()
    print('\n'.join(motor_mod.informe_de_estado(RAIZ, entradas, juegos)))


def monetizar_cmd(args):
    """monetizar [estado] | escenarios [SESIONES…] | variantes ID [portal] | envio ID (portadas, videos y ficha para CrazyGames)"""
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    import monetizar as monet_mod
    accion = args[0] if args else 'estado'
    if accion == 'estado':
        print('\n'.join(['# Monetización: qué falta y qué sigue', ''] + monet_mod.informe(RAIZ, sys.modules[__name__])))
        return
    if accion == 'escenarios':
        try:
            sesiones = [int(x) for x in args[1:]] or None
        except ValueError:
            sys.exit('Uso: python3 fabrica.py monetizar escenarios [SESIONES_POR_DIA …]')
        for f in monet_mod.escenarios(RAIZ, sesiones):
            print('%7s sesiones/día · eCPM supuesto US$%s → US$%s por mes · días para llegar al pago mínimo: %s' % (format(f['sesiones_dia'], ','), f['ecpm'], format(f['mes_usd'], ',.2f'), f['dias_a_pago_minimo']))
        return
    if accion == 'variantes' and len(args) > 1:
        try:
            hechos = monet_mod.variantes(RAIZ, sys.modules[__name__], args[1], args[2:] or None)
        except monet_mod.ErrorMonetizacion as e:
            sys.exit('[monetizar] ' + str(e))
        malo = False
        for prov, carpeta, problemas in hechos:
            print('[monetizar] %s → %s%s' % (prov, carpeta, '' if not problemas else ' · PROBLEMAS: ' + '; '.join(problemas)))
            malo = malo or bool(problemas)
        if malo:
            sys.exit(1)
        return
    if accion == 'envio' and len(args) > 1:
        try:
            monet_mod.variantes(RAIZ, sys.modules[__name__], args[1], ['crazygames'])
        except monet_mod.ErrorMonetizacion as e:
            sys.exit('[monetizar] ' + str(e))
        r = subprocess.run(['node', str(RAIZ / 'herramientas' / 'envio_portal.js'), args[1], 'crazygames'], cwd=str(RAIZ))
        if r.returncode:
            sys.exit('[monetizar] el paquete de portadas y videos falló (necesita playwright y ffmpeg)')
        kit(args[1])
        return
    sys.exit('Uso: python3 fabrica.py monetizar [estado|escenarios [N…]|variantes ID [portal]|envio ID]')


def _estado_para_autonomia():
    """(líneas del calendario, [(juego, huella corta) listos para aprobar]) leídos del estado real, para el informe de autonomía."""
    nucleo, adaptadores = _publicacion()
    from publicacion import calendario
    ent = nucleo.Entorno()
    lineas = calendario.estado(RAIZ, ent.ahora().date())
    sitio = nucleo.cargar_json(RAIZ / 'publicacion' / 'sitio.json', {})
    listos = []
    for i in ids():
        if i not in (sitio.get('juegos') or []):
            continue
        ctx = nucleo.Contexto(RAIZ, i)
        plan, problemas = nucleo.construir_plan(ctx, adaptadores)
        if problemas or nucleo.compuertas(ctx, plan, problemas, ent.ahora()):
            continue
        if any(not ctx.libro.hecho(a['id']) for a in plan['acciones']) and not any(ctx.libro.incierto(a['id']) for a in plan['acciones']):
            listos.append((i, plan['huella'][:16]))
    return ent.ahora().date(), lineas, listos


def autonomia_cmd(args):
    """autonomia [estado] | registrar | revisar   — el objetivo secundario del motor: que la fábrica necesite cada vez menos de Max (herramientas/autonomia.py)"""
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    import autonomia as aut
    accion = args[0] if args else 'estado'
    if accion not in ('estado', 'registrar', 'revisar'):
        sys.exit('Uso: python3 fabrica.py autonomia [estado|registrar|revisar]')
    try:
        if accion == 'revisar':
            malos = aut.problemas_de_catalogo(aut.catalogo(RAIZ))
            for x in malos:
                print('  PROBLEMA · ' + x)
            if malos:
                sys.exit('[autonomia] el inventario tiene %d problema(s)' % len(malos))
            print('[autonomia] inventario en orden')
            return
        hoy, lineas, listos = _estado_para_autonomia()
        if accion == 'registrar':
            cat = aut.catalogo(RAIZ)
            m = aut.medir(cat)
            dias, _ = aut.dias_aprobados(lineas, hoy)
            fila = aut.registrar(RAIZ, hoy, m, dias)
            print('[autonomia] semana %s: %s de %s pasos sin Max, %s toques al mes (estimado), %s días aprobados por salir' % (fila['semana'], fila['pasos_autonomos'], fila['pasos_totales'], fila['toques_mes'], fila['dias_aprobados']))
            return
        print('\n'.join(['# Autonomía: cuánto corre la fábrica sin Max', ''] + aut.informe(RAIZ, hoy, lineas, listos)))
    except aut.ErrorAutonomia as e:
        sys.exit('[autonomia] ' + str(e))


def administrador_cmd(args):
    """administrador [chequeo] | guardia | flujos [--reactivar] | anotar "TEXTO" --resultado hecho|no-se-pudo|avisado|nada-que-hacer [--commit C] | bitacora [N]
    El administrador del motor (carta: motor/ADMINISTRADOR.md): mira la salud y la autonomía, y deja constancia en motor/bitacora.jsonl. No aprueba ni publica nada."""
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    import administrador as adm
    accion = args[0] if args else 'chequeo'
    try:
        if accion == 'anotar' and len(args) > 1:
            nucleo, _ = _publicacion()
            linea = adm.anotar(RAIZ, nucleo.Entorno().ahora().date(), args[1], _opcion('--resultado'), _opcion('--commit') or '')
            print('[administrador] anotado: %s · %s · %s' % (linea['fecha'], linea['resultado'], linea['que']))
            return
        if accion == 'bitacora':
            try:
                n = int(args[1]) if len(args) > 1 else 10
            except ValueError:
                sys.exit('Uso: python3 fabrica.py administrador bitacora [N]')
            for l in adm.ultimas(RAIZ, n):
                print('%s · %-14s · %s%s' % (l['fecha'], l['resultado'], l['que'], (' (%s)' % l['commit']) if l.get('commit') else ''))
            return
        if accion == 'flujos':
            repo = adm.repo_actual(RAIZ)
            informe = adm.revisar_flujos(adm._gh, repo, '--reactivar' in args)
            nombres = {'activo': 'activo', 'reactivado': 'REACTIVADO (GitHub lo había apagado por inactividad)', 'apagado-por-inactividad': 'APAGADO por inactividad (usa --reactivar)',
                       'no-se-pudo': 'NO SE PUDO REACTIVAR', 'apagado-a-mano': 'APAGADO A MANO (no se toca: avisar a Max)', 'otro-estado': 'EN OTRO ESTADO'}
            for r in informe:
                print('  %-34s %-28s %s%s' % (r['nombre'], r['ruta'].rsplit('/', 1)[-1], nombres[r['resultado']], (' · ' + r['detalle']) if r.get('detalle') else ''))
            malos = adm.flujos_sin_resolver(informe)
            if malos:
                sys.exit('[administrador] %d flujo(s) siguen sin correr: %s' % (len(malos), ', '.join(r['nombre'] for r in malos)))
            print('[administrador] los %d flujos del repositorio están activos' % len(informe))
            return
        if accion == 'guardia':
            nucleo, _ = _publicacion()
            entradas = nucleo.Libro(RAIZ / 'publicacion' / 'libro.jsonl').entradas()
            cambios = adm.cambios_del_administrador(RAIZ)
            malas = adm.violaciones(cambios, entradas)
            for commit, ruta, motivo in malas:
                print('  VIOLACIÓN · %s tocó %s (%s)' % (commit[:10], ruta, motivo))
            if malas:
                sys.exit('[administrador] %d cambio(s) del administrador tocan algo que su carta le prohíbe' % len(malas))
            print('[administrador] guardia en orden: %d cambio(s) firmados como el administrador, ninguno en una ruta protegida' % len(cambios))
            return
        if accion != 'chequeo':
            sys.exit('Uso: python3 fabrica.py administrador [chequeo|guardia|flujos [--reactivar]|anotar "TEXTO" --resultado R [--commit C]|bitacora [N]]')
        hoy, lineas, _ = _estado_para_autonomia()
        nucleo, _ = _publicacion()
        entradas = nucleo.Libro(RAIZ / 'publicacion' / 'libro.jsonl').entradas()
        hallazgos = adm.chequeo(RAIZ, hoy, lineas, entradas)
        print('\n'.join(['# Chequeo del administrador · %s' % hoy.isoformat(), ''] + adm.resumen(hallazgos)))
        recientes = adm.ultimas(RAIZ, 5)
        if recientes:
            print('Últimas anotaciones de la bitácora:')
            for l in recientes:
                print('  %s · %-14s · %s' % (l['fecha'], l['resultado'], l['que']))
    except (adm.ErrorAdministrador, adm.autonomia.ErrorAutonomia) as e:
        sys.exit('[administrador] ' + str(e))


def calidad_cmd(objetivo):
    sys.path.insert(0, str(RAIZ / 'herramientas'))
    import motor as motor_mod
    _, entradas = _juegos_y_libro()
    for i in seleccion(objetivo):
        spec = cargar(i)
        n = motor_mod.nivel_de(RAIZ, spec)
        print('%s: nivel %d (%s) · se le exige %d para lanzarse%s' % (i, n['nivel'], n['nombre'], motor_mod.exigido(RAIZ, spec, entradas),
                                                                      ' (heredado: sin mínimo)' if i in motor_mod._piso(RAIZ).get('heredados', []) else ''))
        for r, ok in n['cumplidos'].items():
            print('   [%s] %s' % ('x' if ok else ' ', motor_mod.escalera(RAIZ)['requisitos'][r]['texto']))


def lista():
    print('Fichas:')
    for i in ids():
        s = cargar(i)
        print('  %-24s plantilla=%-10s v%-7s idiomas=%s paquetes=%s motor=%s' % (i, s['plantilla'], s['version'], ','.join(s['idiomas']), ','.join(s.get('paquetes', [])) or '-', ','.join(s.get('motor', [])) or '-'))
    print('Plantillas:', ', '.join(sorted(p.name for p in (RAIZ / 'plantillas').iterdir() if p.is_dir())))


if __name__ == '__main__':
    orden = sys.argv[1] if len(sys.argv) > 1 else ''
    objetivo = sys.argv[2] if len(sys.argv) > 2 else 'todos'
    if orden == 'lista':
        lista()
    elif orden == 'mapa':
        mapa()
    elif orden == 'novedad':
        novedad(objetivo if objetivo != '--estricto' else 'todos', '--estricto' in sys.argv)
    elif orden == 'ideas':
        ideas()
    elif orden == 'nueva-plantilla' and len(sys.argv) > 2:
        nueva_plantilla(sys.argv[2])
    elif orden == 'nuevo' and len(sys.argv) > 3:
        nuevo(sys.argv[2], sys.argv[3])
    elif orden == 'sitio':
        generar_sitio('--zip' in sys.argv)
    elif orden == 'ciclo':
        ciclo()
    elif orden == 'perfiles':
        sys.path.insert(0, str(RAIZ / 'herramientas'))
        import perfiles
        perfiles.main(sys.argv)
    elif orden == 'metricas':
        metricas_cmd(sys.argv[2:])
    elif orden == 'rumbo':
        rumbo_cmd(sys.argv[2:])
    elif orden == 'motor':
        motor_cmd(sys.argv[2:])
    elif orden == 'monetizar':
        monetizar_cmd(sys.argv[2:])
    elif orden == 'autonomia':
        autonomia_cmd(sys.argv[2:])
    elif orden == 'administrador':
        administrador_cmd(sys.argv[2:])
    elif orden == 'calidad':
        calidad_cmd(objetivo)
    elif orden == 'huella':
        huella(objetivo)
    elif orden == 'publicar':
        publicar(objetivo)
    elif orden == 'resolver' and len(sys.argv) > 2 and sys.argv[2] in ('--auto', '--verificar'):
        resolver_auto(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif orden == 'resolver' and len(sys.argv) > 3:
        resolver(sys.argv[2], sys.argv[3])
    elif orden == 'calendario':
        calendario_cmd()
    elif orden == 'configurar' and len(sys.argv) > 2:
        configurar(sys.argv[2])
    elif orden in ('construir', 'probar', 'kit', 'revisar', 'todo'):
        for i in seleccion(objetivo):
            if orden in ('construir', 'todo'):
                construir(i)
            if orden in ('probar', 'todo'):
                probar(i)
            if orden in ('kit', 'todo'):
                kit(i)
            if orden in ('revisar', 'todo'):
                revisar(i)
    else:
        print(__doc__)
        sys.exit(1 if orden else 0)
