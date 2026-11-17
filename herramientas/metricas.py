"""Registro de métricas de la fábrica.

Todo lo que el motor sabe de cómo les va a los juegos vive en un solo archivo, `metricas/registro.csv`, que crece por el final y se guarda en el repositorio
(cada cambio queda en el historial de git). Una fila es un dato:

    semana,juego,metrica,valor,fuente,nota
    2026-11-16,guerreros-gelatina,vistas_juego,120,cloudflare,

· semana: el lunes de la semana (AAAA-MM-DD). Los datos se llevan por semana completa; la semana en curso se anota pero no cuenta para decidir.
· metrica: una de las que define `metricas/politica.json` (vistas, comentarios, donaciones…).
· fuente: de dónde salió el número (`cloudflare`, `manual`, `itch`, `portal-nombre`…). Varias fuentes de la misma métrica se suman.
· Si el mismo dato (semana, juego, métrica, fuente) aparece dos veces, vale la última fila: así se corrigen errores y se vuelve a importar sin duplicar.

Lo único que se mide solo es lo que Cloudflare Web Analytics ve en las páginas HTML del sitio (vistas de la ficha y de la página donde se juega). No hay
medición dentro del juego: ni partidas, ni tiempo de juego. Lo demás (comentarios, dinero, lo que digan itch.io o un portal) se anota a mano.

El recolector de Cloudflare está construido con la documentación y con ejemplos públicos de la API, y se probó contra respuestas simuladas, no contra el
servicio real: la primera corrida real hay que mirarla."""
import csv
import datetime
import json
import math
import pathlib
import re
import sys

ENCABEZADO = ['semana', 'juego', 'metrica', 'valor', 'fuente', 'nota']
FUENTE_RE = re.compile(r'[a-z0-9][a-z0-9:_-]{0,39}')
ID_RE = re.compile(r'[a-z0-9][a-z0-9-]{0,60}')
MAX_NOTA = 200
ENDPOINT_GRAPHQL = 'https://api.cloudflare.com/client/v4/graphql'
VENTANA_MAXIMA_DIAS = 27       # el conjunto de datos de Web Analytics limita el rango de cada consulta; se pide menos de un mes
VARIABLE_TOKEN = 'CLOUDFLARE_ANALITICA_TOKEN'
VARIABLE_CUENTA = 'CLOUDFLARE_ACCOUNT_ID'


class ErrorMetricas(Exception):
    pass


def ruta_registro(raiz):
    return pathlib.Path(raiz) / 'metricas' / 'registro.csv'


def cargar_politica(raiz):
    ruta = pathlib.Path(raiz) / 'metricas' / 'politica.json'
    if not ruta.exists():
        raise ErrorMetricas('falta %s' % ruta)
    try:
        return json.loads(ruta.read_text(encoding='utf-8'))
    except ValueError as e:
        raise ErrorMetricas('%s no es JSON válido: %s' % (ruta, e))


def _publicacion():
    """Módulos de publicación (red, núcleo): viven en la raíz del repositorio, que no siempre está en la ruta de búsqueda."""
    raiz = str(pathlib.Path(__file__).resolve().parent.parent)
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    from publicacion import nucleo, red
    return nucleo, red


def hoy_utc():
    return datetime.datetime.now(datetime.timezone.utc).date()


def lunes(d):
    return d - datetime.timedelta(days=d.weekday())


def _fecha(texto):
    try:
        return datetime.date.fromisoformat(str(texto).strip())
    except ValueError:
        return None


def interpretar_semana(texto, hoy):
    """«esta», «pasada» o una fecha AAAA-MM-DD (cualquier día de la semana) → el lunes de esa semana."""
    t = str(texto or 'esta').strip().lower()
    if t == 'esta':
        return lunes(hoy)
    if t == 'pasada':
        return lunes(hoy) - datetime.timedelta(days=7)
    d = _fecha(t)
    if d is None:
        raise ErrorMetricas('semana «%s»: usa esta, pasada o una fecha AAAA-MM-DD' % texto)
    return lunes(d)


def _seguro(texto):
    """Evita que una nota se interprete como fórmula si alguien abre el CSV en una hoja de cálculo."""
    texto = str(texto or '')
    return ("'" + texto) if texto[:1] in ('=', '+', '-', '@', '\t', '\r') else texto


def normalizar_valor(politica, metrica, valor):
    """(texto canónico, número) o ErrorMetricas."""
    meta = (politica.get('metricas') or {}).get(metrica)
    if not meta:
        raise ErrorMetricas('métrica «%s» desconocida (las que hay: %s)' % (metrica, ', '.join(sorted(politica.get('metricas', {})))))
    try:
        n = float(str(valor).strip().replace(',', '.'))
    except ValueError:
        raise ErrorMetricas('%s: «%s» no es un número' % (metrica, valor))
    if not math.isfinite(n) or n < 0:
        raise ErrorMetricas('%s: el valor debe ser un número mayor o igual a cero' % metrica)
    if meta['tipo'] == 'conteo':
        if n != int(n):
            raise ErrorMetricas('%s es un conteo: usa un número entero' % metrica)
        return str(int(n)), int(n)
    if round(n, 2) != n:
        raise ErrorMetricas('%s es dinero: máximo dos decimales' % metrica)
    return '%.2f' % n, n


def leer(raiz, ids_validos=None):
    """Todas las filas del registro, validadas. ErrorMetricas con las primeras fallas si algo está mal."""
    ruta = ruta_registro(raiz)
    if not ruta.exists():
        return []
    politica = cargar_politica(raiz)
    filas, fallas = [], []
    with open(ruta, encoding='utf-8', newline='') as f:
        lector = csv.reader(f)
        try:
            enc = next(lector)
        except StopIteration:
            return []
        if enc != ENCABEZADO:
            raise ErrorMetricas('%s: el encabezado debe ser %s' % (ruta.name, ','.join(ENCABEZADO)))
        for num, r in enumerate(lector, start=2):
            if not r:
                continue
            if len(r) != len(ENCABEZADO):
                fallas.append('línea %d: se esperaban %d columnas y hay %d' % (num, len(ENCABEZADO), len(r)))
                continue
            semana, juego, metrica, valor, fuente, nota = [c.strip() for c in r[:6]]
            d = _fecha(semana)
            if d is None or d != lunes(d):
                fallas.append('línea %d: «%s» no es un lunes AAAA-MM-DD' % (num, semana))
                continue
            if not ID_RE.fullmatch(juego) or (ids_validos is not None and juego not in ids_validos):
                fallas.append('línea %d: el juego «%s» no existe en juegos/' % (num, juego))
                continue
            if not FUENTE_RE.fullmatch(fuente):
                fallas.append('línea %d: fuente «%s» no válida (minúsculas, números, : _ -)' % (num, fuente))
                continue
            if len(nota) > MAX_NOTA or '\n' in nota or '\r' in nota:
                fallas.append('línea %d: la nota debe caber en una línea de %d caracteres' % (num, MAX_NOTA))
                continue
            try:
                texto, numero = normalizar_valor(politica, metrica, valor)
            except ErrorMetricas as e:
                fallas.append('línea %d: %s' % (num, e))
                continue
            filas.append({'semana': d, 'juego': juego, 'metrica': metrica, 'valor': numero, 'texto': texto, 'fuente': fuente, 'nota': nota})
    if fallas:
        raise ErrorMetricas('%s tiene filas inválidas:\n  ' % ruta.name + '\n  '.join(fallas[:6]) + ('\n  … y %d más' % (len(fallas) - 6) if len(fallas) > 6 else ''))
    return filas


def vigentes(filas):
    """Una fila por (semana, juego, métrica, fuente): la última que se anotó."""
    v = {}
    for f in filas:
        v[(f['semana'], f['juego'], f['metrica'], f['fuente'])] = f
    return v


def sumas(filas):
    """{(semana, juego, métrica): total entre fuentes} con la fila vigente de cada fuente."""
    s = {}
    for (semana, juego, metrica, _), f in vigentes(filas).items():
        s[(semana, juego, metrica)] = s.get((semana, juego, metrica), 0) + f['valor']
    return s


def anotar(raiz, juego, metrica, valor, semana='esta', fuente='manual', nota='', ids_validos=None, hoy=None):
    """Agrega una fila al registro. Devuelve la fila escrita."""
    politica = cargar_politica(raiz)
    hoy = hoy or hoy_utc()
    if ids_validos is not None and juego not in ids_validos:
        raise ErrorMetricas('no existe el juego «%s» (hay: %s)' % (juego, ', '.join(sorted(ids_validos)) or 'ninguno'))
    if not FUENTE_RE.fullmatch(str(fuente)):
        raise ErrorMetricas('fuente «%s» no válida (minúsculas, números, : _ -)' % fuente)
    nota = str(nota or '').strip()
    if len(nota) > MAX_NOTA or '\n' in nota or '\r' in nota:
        raise ErrorMetricas('la nota debe caber en una línea de %d caracteres' % MAX_NOTA)
    lun = interpretar_semana(semana, hoy)
    texto, _ = normalizar_valor(politica, metrica, valor)
    _agregar(raiz, [[lun.isoformat(), juego, metrica, texto, fuente, _seguro(nota)]])
    return {'semana': lun, 'juego': juego, 'metrica': metrica, 'valor': texto, 'fuente': fuente, 'nota': nota, 'en_curso': lun >= lunes(hoy)}


def _agregar(raiz, filas):
    ruta = ruta_registro(raiz)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not ruta.exists() or ruta.stat().st_size == 0:
        ruta.write_text(','.join(ENCABEZADO) + '\n', encoding='utf-8')
    else:   # el archivo termina en salto de línea; si alguien lo editó a mano y no, se arregla antes de agregar
        contenido = ruta.read_bytes()
        if not contenido.endswith(b'\n'):
            with open(ruta, 'ab') as f:
                f.write(b'\n')
    with open(ruta, 'a', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        for fila in filas:
            w.writerow(fila)


def tabla(raiz, juego=None, ids_validos=None, hoy=None, semanas=8):
    """Texto con lo que hay en el registro por juego y semana (la fila vigente de cada fuente, sumadas)."""
    hoy = hoy or hoy_utc()
    politica = cargar_politica(raiz)
    filas = [f for f in leer(raiz, ids_validos) if juego in (None, f['juego'])]
    if not filas:
        return 'Todavía no hay métricas registradas%s.' % (' de «%s»' % juego if juego else '')
    s = sumas(filas)
    desde = lunes(hoy) - datetime.timedelta(days=7 * (semanas - 1))
    metricas = sorted({m for (_, _, m) in s})
    L = []
    for j in sorted({f['juego'] for f in filas}):
        L.append(j)
        sem = sorted({w for (w, jj, _) in s if jj == j and w >= desde})
        if not sem:
            L.append('  (nada en las últimas %d semanas)' % semanas)
            continue
        L.append('  %-12s ' % 'semana' + ' '.join('%-15s' % m for m in metricas if any((w, j, m) in s for w in sem)))
        for w in sem:
            celdas = []
            for m in metricas:
                if not any((x, j, m) in s for x in sem):
                    continue
                v = s.get((w, j, m))
                celdas.append('%-15s' % ('-' if v is None else (('%.2f' % v) if politica['metricas'][m]['tipo'] == 'dinero' else '%d' % v)))
            L.append('  %-12s ' % (w.isoformat() + ('*' if w >= lunes(hoy) else '')) + ' '.join(celdas))
    L.append('')
    L.append('* semana en curso: se anota pero no cuenta para decidir hasta que termina.')
    return '\n'.join(L)


# ---------------------------------------------------------------------------------------------------------------------
# Cloudflare Web Analytics
# ---------------------------------------------------------------------------------------------------------------------

def host_del_sitio(sitio):
    from urllib.parse import urlparse
    host = urlparse(str(sitio.get('url_base', ''))).netloc.lower()
    if not re.fullmatch(r'[a-z0-9.-]+', host):
        raise ErrorMetricas('sitio.json: «url_base» no tiene un dominio válido')
    return host


def consulta_graphql(cuenta, host, desde, hasta, con_bot=True):
    """Texto de la consulta: vistas de página (HTML) por día y ruta, de un dominio, entre dos instantes UTC. Los valores van como literales (ya validados)
    para no depender del nombre de tipo de cada variable en el esquema."""
    if not re.fullmatch(r'[0-9a-f]{32}', cuenta or ''):
        raise ErrorMetricas('%s no tiene la forma de un Account ID de Cloudflare (32 caracteres hexadecimales)' % VARIABLE_CUENTA)
    filtro = 'requestHost: %s, datetime_geq: %s, datetime_lt: %s' % (
        json.dumps(host), json.dumps(desde.strftime('%Y-%m-%dT%H:%M:%SZ')), json.dumps(hasta.strftime('%Y-%m-%dT%H:%M:%SZ')))
    if con_bot:
        filtro += ', bot: 0'
    return ('{ viewer { accounts(filter: {accountTag: %s}) { rumPageloadEventsAdaptiveGroups(limit: 10000, filter: {%s}) '
            '{ count dimensions { date requestPath } } } } }') % (json.dumps(cuenta), filtro)


_JUEGO_RE = re.compile(r'^/jugar/([a-z0-9-]+)(?:/index\.html)?/?$')
_FICHA_RE = re.compile(r'^/(?:es|en|zh)/juegos/([a-z0-9-]+)(?:/index\.html)?/?$')


def clasificar_ruta(ruta):
    """('vistas_juego'|'vistas_ficha', id) o None si la ruta no es de un juego."""
    m = _JUEGO_RE.match(ruta or '')
    if m:
        return 'vistas_juego', m.group(1)
    m = _FICHA_RE.match(ruta or '')
    if m:
        return 'vistas_ficha', m.group(1)
    return None


def _preguntar(ent, consulta, token):
    cuerpo = json.dumps({'query': consulta}).encode('utf-8')
    r = ent.http('POST', ENDPOINT_GRAPHQL, {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}, cuerpo)
    return r


def _mensaje_error(r, secretos):
    _, red = _publicacion()
    if r.status in (401, 403):
        return 'Cloudflare respondió %d: el token no es válido o no tiene el permiso «Account Analytics: Read» sobre esa cuenta' % r.status
    datos = r.json()
    errores = datos.get('errors') or []
    if errores:
        return 'Cloudflare rechazó la consulta: %s' % red.redactar((errores[0] or {}).get('message', '?'), secretos)[:200]
    return 'Cloudflare respondió %d: %s' % (r.status, red.redactar(r.texto(120), secretos))


def importar_cloudflare(raiz, ent, ids_validos, dias=21, hoy=None):
    """Lee las vistas de página de las últimas semanas y las agrega al registro (fuente «cloudflare»).
    La ventana empieza siempre en lunes, así cada semana que se escribe está completa (salvo la en curso). Devuelve un resumen."""
    nucleo, _ = _publicacion()
    hoy = hoy or hoy_utc()
    token = (ent.env.get(VARIABLE_TOKEN) or '').strip()
    cuenta = (ent.env.get(VARIABLE_CUENTA) or '').strip()
    if not token or not cuenta:
        raise ErrorMetricas('faltan %s y %s en el entorno' % (VARIABLE_TOKEN, VARIABLE_CUENTA))
    dias = max(7, min(int(dias), VENTANA_MAXIMA_DIAS))
    sitio = nucleo.cargar_json(pathlib.Path(raiz) / 'publicacion' / 'sitio.json', {})
    host = host_del_sitio(sitio)
    inicio = lunes(hoy - datetime.timedelta(days=dias))
    desde = datetime.datetime.combine(inicio, datetime.time(0, 0))
    hasta = datetime.datetime.combine(hoy + datetime.timedelta(days=1), datetime.time(0, 0))
    secretos = [token, cuenta]
    nota = ''
    r = _preguntar(ent, consulta_graphql(cuenta, host, desde, hasta, con_bot=True), token)
    datos = r.json() if r.status == 200 else {}
    if r.status == 200 and datos.get('errors') and 'bot' in json.dumps(datos['errors']).lower():
        nota = 'sin filtro de bots'      # el esquema no aceptó el filtro de bots: se reintenta sin él y queda dicho en la nota
        r = _preguntar(ent, consulta_graphql(cuenta, host, desde, hasta, con_bot=False), token)
        datos = r.json() if r.status == 200 else {}
    if r.status != 200 or datos.get('errors'):
        raise ErrorMetricas(_mensaje_error(r, secretos))
    cuentas = (((datos.get('data') or {}).get('viewer') or {}).get('accounts')) or []
    if not cuentas:
        raise ErrorMetricas('Cloudflare no devolvió la cuenta: revisa que %s sea la de este sitio y que el token pueda leerla' % VARIABLE_CUENTA)
    grupos = cuentas[0].get('rumPageloadEventsAdaptiveGroups') or []
    if not grupos:
        return {'escritas': 0, 'sin_cambio': 0, 'grupos': 0, 'host': host, 'desde': inicio,
                'aviso': 'Cloudflare no devolvió ninguna vista de %s desde %s. ¿Está activado Web Analytics en el proyecto de Pages y hubo un despliegue después de activarlo?' % (host, inicio.isoformat())}
    total = {}
    for g in grupos:
        clase = clasificar_ruta((g.get('dimensions') or {}).get('requestPath'))
        d = _fecha((g.get('dimensions') or {}).get('date'))
        if not clase or d is None or clase[1] not in ids_validos:
            continue
        clave = (lunes(d), clase[1], clase[0])
        total[clave] = total.get(clave, 0) + int(g.get('count') or 0)
    existentes = {k: f['valor'] for k, f in vigentes(leer(raiz, ids_validos)).items() if k[3] == 'cloudflare'}
    nuevas, sin_cambio = [], 0
    semana = inicio
    while semana <= lunes(hoy):
        for juego in sorted(ids_validos):
            for metrica in ('vistas_juego', 'vistas_ficha'):
                valor = total.get((semana, juego, metrica), 0)
                if existentes.get((semana, juego, metrica, 'cloudflare')) == valor:
                    sin_cambio += 1
                else:
                    nuevas.append([semana.isoformat(), juego, metrica, str(valor), 'cloudflare', nota])
        semana += datetime.timedelta(days=7)
    if nuevas:
        _agregar(raiz, nuevas)
    return {'escritas': len(nuevas), 'sin_cambio': sin_cambio, 'grupos': len(grupos), 'host': host, 'desde': inicio, 'aviso': ''}
