"""Calendario de contenido: publicaciones propias (no son lanzamientos) que se aprueban POR LOTE y salen solas en su fecha.

Cada publicación vive en contenido/calendario.json: juego, canal, fecha (no_antes_de), texto con {enlace} y {ia}, imagen y texto alternativo.
La aprobación es de CADA publicación, con su huella (un hash de todo lo que saldrá: texto ya resuelto, imagen, texto alternativo y fecha).
El dueño aprueba un lote con la huella del lote; eso anota en contenido/aprobaciones.json la huella de cada publicación. Después, una tarea diaria
publica solo lo que cumple las tres condiciones: está aprobada con su huella actual, ya llegó su fecha y no se pasó de la ventana.
Si alguien cambia el texto, la imagen o la fecha después de aprobar, la huella cambia y esa publicación vuelve a pedir aprobación.
Pasa por las mismas barreras que un lanzamiento (nucleo.ejecutar): compuertas, ritmo del canal, libro de registro y «incierto» sin reintentos."""
import datetime
import json
import pathlib
import re

from . import nucleo
from . import texto as tx

CANALES = ('bluesky',)          # canales cuyo formato de publicación con imagen conocemos
VENTANA_DIAS = 3                # una publicación aprobada puede salir hasta 3 días después de su fecha; pasado eso espera una fecha nueva (y otra aprobación)


class ErrorCalendario(Exception):
    pass


def _ruta(raiz, nombre):
    return pathlib.Path(raiz) / 'contenido' / nombre


def cargar(raiz):
    datos = nucleo.cargar_json(_ruta(raiz, 'calendario.json'), {})
    items = datos.get('publicaciones', [])
    vistos = set()
    for it in items:
        if not re.fullmatch(r'[a-z0-9-]{1,60}', str(it.get('id', ''))):
            raise ErrorCalendario('calendario.json: cada publicación necesita un «id» con letras minúsculas, números y guiones (vi «%s»)' % it.get('id'))
        if it['id'] in vistos:
            raise ErrorCalendario('calendario.json: el id «%s» está repetido' % it['id'])
        vistos.add(it['id'])
    return items


def aprobaciones(raiz):
    return dict((nucleo.cargar_json(_ruta(raiz, 'aprobaciones.json'), {}) or {}).get('aprobadas', {}))


def guardar_aprobaciones(raiz, aprobadas):
    ruta = _ruta(raiz, 'aprobaciones.json')
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({'nota': 'Publicaciones del calendario que el dueño aprobó: id → huella. Lo escribe «python3 fabrica.py calendario --aprobar».', 'aprobadas': dict(sorted(aprobadas.items()))},
                               ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _fecha(valor):
    try:
        return datetime.date.fromisoformat(str(valor))
    except ValueError:
        return None


def armar(raiz, item, libro=None):
    """(ctx, acción, problemas). Las acciones tienen la misma forma que las de un adaptador (nucleo.construir_plan)."""
    problemas = []
    canal = item.get('canal', 'bluesky')
    if canal not in CANALES:
        raise ErrorCalendario('«%s»: el canal «%s» todavía no admite el calendario (canales: %s)' % (item['id'], canal, ', '.join(CANALES)))
    try:
        ctx = nucleo.Contexto(raiz, item.get('juego', ''), libro)
    except nucleo.ErrorPlan as e:
        raise ErrorCalendario('«%s»: %s' % (item['id'], e))
    if canal not in ctx.politica.get('canales', []):
        problemas.append('el canal «%s» no está activo en publicacion/politica.json' % canal)
    if not any(e.get('canal') == 'sitio-propio' and e.get('resultado') == 'ok' and e.get('juego') == ctx.id for e in ctx.libro.entradas()):
        problemas.append('el juego «%s» todavía no está publicado en el sitio propio: el calendario solo habla de juegos ya lanzados' % ctx.id)
    idioma = item.get('idioma') or ctx.idioma_de(canal)
    if idioma not in ctx.spec['idiomas']:
        problemas.append('el juego no tiene versión en «%s»' % idioma)
        idioma = ctx.spec['idiomas'][0]
    ia = ctx.linea_ia_corta(idioma) if item.get('ia', True) else ''   # «ia»: false = la publicación no repite la línea (el perfil de la cuenta y el sitio ya lo dicen)
    texto = str(item.get('texto', '')).replace('{enlace}', ctx.url_juego(idioma)).replace('{ia}', ia).strip()
    if not texto:
        problemas.append('falta el texto')
    if re.search(r'\{[a-z_]+\}|\[ENLACE', texto):
        problemas.append('el texto tiene marcas sin resolver')
    if 'PENDIENTE' in texto:
        problemas.append('el texto dice PENDIENTE')
    if ctx.url_juego(idioma) not in texto:
        problemas.append('el texto no lleva el enlace del juego')
    if ia and ia not in texto:
        problemas.append('el texto no lleva la línea de IA (o pon «ia»: false en la publicación)')
    from .adaptadores import bluesky
    n, tope = tx.grafemas(texto), bluesky.limite_para(texto)
    if n > tope or tx.bytes_utf8(texto) > 3000:
        problemas.append('el texto mide %d grafemas (máximo %d) y %d bytes (máximo 3000)' % (n, tope, tx.bytes_utf8(texto)))
    ruta = str(item.get('imagen', ''))
    contenido = (pathlib.Path(raiz) / 'contenido').resolve()
    imagen = None
    if ruta:
        destino = (pathlib.Path(raiz) / ruta).resolve()
        if contenido not in destino.parents:
            problemas.append('la imagen debe estar dentro de contenido/')
        else:
            imagen = ctx.archivo(ruta)
            if not imagen:
                problemas.append('no existe la imagen %s' % ruta)
    else:
        problemas.append('falta la imagen')
    if not str(item.get('alt', '')).strip():
        problemas.append('falta el texto alternativo de la imagen')
    fecha = _fecha(item.get('no_antes_de'))
    if not fecha:
        problemas.append('«no_antes_de» debe ser una fecha AAAA-MM-DD')
    accion = {'id': 'calendario:%s:%s' % (item['id'], canal), 'tipo': 'post', 'canal': canal, 'categoria': 'redes',
              'datos': {'texto': texto, 'idioma': idioma, 'imagen': imagen, 'alt': str(item.get('alt', '')).strip(), 'no_antes_de': str(item.get('no_antes_de', ''))}}
    return ctx, accion, problemas


def huella_de(accion):
    return nucleo.sha256_texto(nucleo.canonico(accion))


def _plan_de(ctx, accion):
    plan = {'version_plan': nucleo.VERSION_PLAN, 'juego': ctx.id, 'version': ctx.version, 'tipo': ctx.tipo, 'acciones': [accion]}
    plan['huella'] = huella_de(accion)
    return plan


def estado(raiz, hoy, libro=None):
    """Una línea por publicación: dict(id, fecha, estado, huella, problemas, accion, ctx).
    estados: hecha · en duda · sin aprobar · cambió tras aprobar · aún no es su fecha · lista · vencida · con problemas"""
    aprobadas = aprobaciones(raiz)
    lineas = []
    for it in sorted(cargar(raiz), key=lambda i: (str(i.get('no_antes_de')), i['id'])):
        ctx, accion, problemas = armar(raiz, it, libro)
        h = huella_de(accion)
        fecha = _fecha(it.get('no_antes_de'))
        if ctx.libro.hecho(accion['id']):
            est = 'hecha'
        elif ctx.libro.incierto(accion['id']):
            est = 'en duda'
        elif problemas:
            est = 'con problemas'
        elif it['id'] not in aprobadas:
            est = 'sin aprobar'
        elif aprobadas[it['id']] != h:
            est = 'cambió tras aprobar'
        elif hoy < fecha:
            est = 'aún no es su fecha'
        elif hoy > fecha + datetime.timedelta(days=VENTANA_DIAS):
            est = 'vencida'
        else:
            est = 'lista'
        lineas.append({'id': it['id'], 'fecha': it.get('no_antes_de'), 'estado': est, 'huella': h, 'problemas': problemas, 'accion': accion, 'ctx': ctx})
    return lineas


def pendientes_de_aprobar(lineas):
    return [l for l in lineas if l['estado'] in ('sin aprobar', 'cambió tras aprobar')]


def huella_del_lote(lineas):
    return nucleo.sha256_texto(nucleo.canonico(sorted((l['id'], l['huella']) for l in lineas)))


def mostrar(lineas):
    if not lineas:
        return 'El calendario está vacío (contenido/calendario.json).'
    L = ['Calendario de contenido', '']
    for l in lineas:
        a = l['accion']
        L.append('%s · %s · %s · huella %s' % (l['fecha'], l['id'], l['estado'].upper(), l['huella'][:12]))
        L += ['     texto:'] + ['       | ' + x for x in a['datos']['texto'].split('\n')]
        L.append('     imagen: %s' % ((a['datos']['imagen'] or {}).get('archivo')))
        L.append('     alt: %s' % a['datos']['alt'])
        for p in l['problemas']:
            L.append('     PROBLEMA: ' + p)
    pend = pendientes_de_aprobar(lineas)
    L.append('')
    if any(l['problemas'] for l in pend):
        L.append('Hay publicaciones con problemas: se arreglan antes de poder aprobar el lote.')
    elif pend:
        lote = huella_del_lote(pend)
        L.append('Lote pendiente de aprobar: %d publicación(es). Huella del lote: %s' % (len(pend), lote))
        L.append('Para aprobarlo: python3 fabrica.py calendario --aprobar %s' % lote[:16])
    else:
        L.append('No hay nada pendiente de aprobar.')
    return '\n'.join(L)


def aprobar(raiz, hoy, huella, libro=None):
    """Aprueba el lote pendiente si la huella coincide. Devuelve los ids aprobados."""
    lineas = estado(raiz, hoy, libro)
    pend = pendientes_de_aprobar(lineas)
    if not pend:
        raise ErrorCalendario('no hay publicaciones pendientes de aprobar')
    malas = [l['id'] for l in lineas if l['estado'] == 'con problemas']
    if malas:
        raise ErrorCalendario('antes de aprobar hay que arreglar: ' + ', '.join(malas))
    lote = huella_del_lote(pend)
    a = (huella or '').strip().lower()
    if not (len(a) >= 12 and re.fullmatch(r'[0-9a-f]+', a) and lote.startswith(a)):
        raise ErrorCalendario('la aprobación no coincide con la huella del lote (%s…): vuelve a leer el calendario y aprueba la huella actual' % lote[:12])
    aprobadas = aprobaciones(raiz)
    for l in pend:
        aprobadas[l['id']] = l['huella']
    guardar_aprobaciones(raiz, aprobadas)
    return [l['id'] for l in pend]


def ejecutar(raiz, hoy, ent, adaptadores, libro=None):
    """Publica lo que está listo (como mucho una publicación por canal y corrida). Devuelve (informe, ok)."""
    informe, ok, por_canal_hoy = [], True, set()
    for l in estado(raiz, hoy, libro):
        if l['estado'] != 'lista':
            informe.append({'accion': l['accion']['id'], 'canal': l['accion']['canal'], 'resultado': 'ya hecho' if l['estado'] == 'hecha' else 'espera', 'detalle': l['estado']})
            if l['estado'] in ('en duda', 'con problemas'):   # una duda o un problema sí son fallos; esperar aprobación, fecha o fecha nueva no lo es
                ok = False
            continue
        canal = l['accion']['canal']
        if canal in por_canal_hoy:
            informe.append({'accion': l['accion']['id'], 'canal': canal, 'resultado': 'espera', 'detalle': 'una publicación por canal y corrida: sale en la siguiente'})
            continue
        por_canal_hoy.add(canal)
        try:
            inf, bien = nucleo.ejecutar(l['ctx'], _plan_de(l['ctx'], l['accion']), [], l['huella'], ent, adaptadores)
        except nucleo.ErrorPublicacion as e:
            informe.append({'accion': l['accion']['id'], 'canal': canal, 'resultado': 'detenido', 'detalle': str(e).replace('\n', ' ')})
            ok = False
            continue
        informe += inf
        ok = ok and bien
    return informe, ok
