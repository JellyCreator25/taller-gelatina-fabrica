"""Monetización dentro del motor: qué falta para cobrar, cuánto podría dar, y las versiones de cada juego para cada ruta.

Todo es de archivos (nada de esto necesita red ni claves):
  monetizacion/politica.json     rutas (portales, adsense-sitio, donaciones), reglas de anuncios y supuestos de ingresos. TODO empieza apagado.
  motor/modulos/anuncios.js      el módulo del motor: anuncios en cortes naturales, apagado por defecto, con simulaciones de AdSense, CrazyGames y Poki.
  estado()                       por ruta: lo que ya está listo, lo que falta y de quién es cada pendiente (de la fábrica o del dueño).
  escenarios()                   cuentas con la fórmula sesiones × anuncios por sesión × relleno × eCPM / 1000 (con supuestos explícitos).
  configuracion_de()             lo que `construir` le inyecta al juego (GGX_CONFIG.anuncios); sin ruta activa ni variante pedida devuelve None y el juego sale idéntico.
  variantes()                    versiones del juego para un portal (en dist/portales/, que no se publica solo): el archivo que el dueño sube a mano.
  informe()                      el resumen que entra al estado de la fábrica (publicacion/PENDIENTE.md) y a monetizacion/PLAN.md."""
import copy
import json
import pathlib
import re

SDK_PORTAL = {   # solo los portales cuya dirección del SDK está confirmada en su documentación; Poki entrega la suya después de aceptar el juego
    'crazygames': '<script src="https://sdk.crazygames.com/crazygames-sdk-v3.js"></script>\n',
}
ADSENSE_SDK = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client='
USO = re.compile(r'GGX\.ads\.(intermedio|recompensa)\(')


class ErrorMonetizacion(Exception):
    pass


def _json(ruta, defecto=None):
    ruta = pathlib.Path(ruta)
    return json.loads(ruta.read_text(encoding='utf-8')) if ruta.exists() else defecto


def politica(raiz):
    return _json(pathlib.Path(raiz) / 'monetizacion' / 'politica.json', {'rutas': {}, 'reglas_de_anuncios': {}, 'supuestos_de_ingresos': {}})


def problemas_de_politica(pol):
    """Lista de problemas de la política (vacía si está bien)."""
    malos = []
    rutas = pol.get('rutas') or {}
    for n in ('portales', 'adsense-sitio', 'donaciones'):
        if n not in rutas:
            malos.append('falta la ruta «%s»' % n)
        elif not isinstance(rutas[n].get('activa'), bool):
            malos.append('la ruta «%s» debe decir activa: true o false' % n)
    r = pol.get('reglas_de_anuncios') or {}
    for k in ('espera_inicial_s', 'min_entre_s', 'max_por_sesion', 'recompensa_min_entre_s'):
        if not isinstance(r.get(k), int) or r[k] < 0:
            malos.append('reglas_de_anuncios.%s debe ser un entero ≥ 0' % k)
    if set(r.get('momentos_permitidos') or []) & set(r.get('momentos_prohibidos') or []):
        malos.append('un momento no puede estar permitido y prohibido a la vez')
    s = pol.get('supuestos_de_ingresos') or {}
    if not (0 < s.get('relleno', 0) <= 1):
        malos.append('supuestos_de_ingresos.relleno debe estar entre 0 y 1')
    return malos


def juegos_con_ganchos(raiz, fabrica):
    """Juegos que declaran el módulo «anuncios» Y cuyo código lo llama (declararlo sin usarlo no cuenta)."""
    raiz = pathlib.Path(raiz)
    salida = []
    for i in fabrica.ids():
        spec = fabrica.cargar(i)
        if 'anuncios' not in (spec.get('motor') or []):
            continue
        base = raiz / 'plantillas' / spec['plantilla']
        codigo = (base / 'plantilla.html').read_text(encoding='utf-8')
        for p in spec.get('paquetes', []):
            ruta = base / 'paquetes' / (p + '.js')
            codigo += ruta.read_text(encoding='utf-8') if ruta.exists() else ''
        if USO.search(codigo):
            salida.append(i)
    return salida


def configuracion_de(raiz, spec):
    """Qué se le inyecta al juego como GGX_CONFIG.anuncios. None = nada (el juego se construye byte por byte como siempre).
    Una variante pedida (spec['_anuncios']) manda; si no, solo una ruta de anuncios activa en la política, con el módulo declarado y el editor de AdSense puesto."""
    if 'anuncios' not in (spec.get('motor') or []):
        return None
    if spec.get('_anuncios'):
        return spec['_anuncios']
    pol = politica(raiz)
    ruta = (pol.get('rutas') or {}).get('adsense-sitio') or {}
    sitio = _json(pathlib.Path(raiz) / 'publicacion' / 'sitio.json', {})
    pub = sitio.get('adsense_publisher') or ''
    if not (ruta.get('activa') and pub):
        return None
    r = pol.get('reglas_de_anuncios') or {}
    cfg = {'proveedor': 'adsense', 'publicador': 'ca-' + pub, 'sdk_url': ADSENSE_SDK,
           'reglas': {k: r[k] for k in ('espera_inicial_s', 'min_entre_s', 'max_por_sesion', 'recompensa_min_entre_s') if k in r}}
    if ruta.get('modo_prueba', True):
        cfg['prueba'] = True
    return cfg


# ---------------------------------------------------------------------------------------------------------------------
# Qué falta
# ---------------------------------------------------------------------------------------------------------------------

def _modulo_listo(raiz):
    import motor
    man = motor.manifiesto(raiz)
    if 'anuncios' not in man:
        return False, 'el módulo «anuncios» no está en motor/modulos.json'
    ok, motivo = motor.informe_vigente(raiz)
    if not ok:
        return False, motivo
    inf = (motor.informe(raiz) or {}).get('modulos', {}).get('anuncios') or {}
    if not inf.get('pruebas'):
        return False, 'el módulo «anuncios» no tiene pruebas en motor/informe.json'
    return True, 'módulo «anuncios» v%s con %d pruebas del motor vigentes' % (man['anuncios']['version'], inf['pruebas'])


def estado(raiz, fabrica):
    """{ruta: {'activa': bool, 'listo': [..], 'falta_fabrica': [..], 'falta_dueno': [..]}} — sin red, sin claves."""
    raiz = pathlib.Path(raiz)
    pol = politica(raiz)
    sitio = _json(raiz / 'publicacion' / 'sitio.json', {})
    rutas = pol.get('rutas') or {}
    ok_mod, txt_mod = _modulo_listo(raiz)
    ganchos = juegos_con_ganchos(raiz, fabrica)
    publicados = [j for j in (sitio.get('juegos') or [])]

    def base():
        listo, falta = [], []
        (listo if ok_mod else falta).append(txt_mod)
        if ganchos:
            listo.append('juegos con anuncios en cortes naturales: ' + ', '.join(ganchos))
        else:
            falta.append('ningún juego llama al módulo todavía (hay que poner los ganchos en su próxima versión)')
        return listo, falta

    salida = {}
    # portales
    listo, falta_f = base()
    falta_d = []
    if SDK_PORTAL:
        listo.append('SDK confirmado en la documentación del portal: ' + ', '.join(sorted(SDK_PORTAL)))
    falta_d += ['crear la cuenta de desarrollador del portal (primero CrazyGames) y fijar cómo cobrar; el portal pide los datos de pago antes de recibir un juego',
                'subir el archivo del juego (lo armo yo con `python3 fabrica.py monetizar variantes`) y llenar su ficha (la preparo yo)']
    salida['portales'] = {'activa': bool((rutas.get('portales') or {}).get('activa')), 'listo': listo, 'falta_fabrica': falta_f, 'falta_dueno': falta_d}
    # AdSense en el sitio propio
    listo, falta_f = base()
    falta_d = []
    ruta = rutas.get('adsense-sitio') or {}
    dominio = re.sub(r'^https?://', '', sitio.get('url_base') or '').split('/')[0]
    if dominio.endswith('.pages.dev') or not dominio:
        falta_d.append('un dominio propio: hoy el sitio vive en %s, y los reportes de editores indican que AdSense no aprueba subdominios gratuitos' % (dominio or 'ninguna dirección'))
    else:
        listo.append('dominio propio: ' + dominio)
    if sitio.get('adsense_publisher'):
        listo.append('editor de AdSense puesto en sitio.json (el sitio ya publica ads.txt y el texto de privacidad con anuncios)')
    else:
        falta_d.append('cuenta de AdSense aprobada para ese dominio, la solicitud aparte de «H5 Games Ads» y el identificador pub-… en publicacion/sitio.json')
    if ruta.get('consentimiento_listo'):
        listo.append('mensaje de consentimiento para el EEE, el Reino Unido y Suiza confirmado en la política')
    else:
        falta_d.append('configurar en la cuenta de AdSense el mensaje de consentimiento (obligatorio para tráfico del EEE, el Reino Unido y Suiza) y marcar consentimiento_listo en la política')
    if sitio.get('analitica') == 'cloudflare':
        listo.append('analítica de visitas activa (Cloudflare Web Analytics)')
    else:
        falta_d.append('decidir la analítica de visitas (Cloudflare Web Analytics): sin ella no hay forma de saber cuántas sesiones hay ni de medir ingresos por visita')
    if len(publicados) < 3:
        falta_f.append('el sitio muestra %d juego(s); con pocos juegos AdSense puede rechazarlo por contenido escaso' % len(publicados))
    salida['adsense-sitio'] = {'activa': bool(ruta.get('activa')), 'listo': listo, 'falta_fabrica': falta_f, 'falta_dueno': falta_d}
    # donaciones
    listo, falta_f, falta_d = [], [], []
    con_enlace = [j for j in fabrica.ids() if fabrica.cargar(j).get('apoyo_url')]
    if con_enlace:
        listo.append('juegos con enlace de apoyo: ' + ', '.join(con_enlace))
    else:
        falta_d.append('crear la cuenta en un servicio de propinas o pago libre y darme el enlace (lo pongo en `apoyo_url` de cada juego y se publica cada juego con tu aprobación)')
    listo.append('el botón de apoyo ya existe en el motor y se muestra solo cuando hay enlace')
    salida['donaciones'] = {'activa': bool((rutas.get('donaciones') or {}).get('activa')), 'listo': listo, 'falta_fabrica': falta_f, 'falta_dueno': falta_d}
    return salida


# ---------------------------------------------------------------------------------------------------------------------
# Cuentas
# ---------------------------------------------------------------------------------------------------------------------

def escenarios(raiz, sesiones=None):
    """Filas {sesiones_dia, ecpm, mes_usd, dias_a_pago_minimo} con la fórmula y los supuestos de la política."""
    s = politica(raiz).get('supuestos_de_ingresos') or {}
    por_sesion, relleno = s.get('anuncios_por_sesion', 2), s.get('relleno', 0.7)
    minimo = min((p['monto'] for p in (s.get('pago_minimo') or {}).values()), default=0)
    filas = []
    for n in (sesiones or s.get('sesiones_por_dia') or [100, 1000, 10000]):
        for ecpm in s.get('ecpm_usd') or [2, 5]:
            dia = n * por_sesion * relleno * ecpm / 1000.0
            filas.append({'sesiones_dia': n, 'ecpm': ecpm, 'dia_usd': round(dia, 2), 'mes_usd': round(dia * 30, 2),
                          'dias_a_pago_minimo': (round(minimo / dia) if dia else None)})
    return filas


# ---------------------------------------------------------------------------------------------------------------------
# Versiones para un portal
# ---------------------------------------------------------------------------------------------------------------------

def revisar_variante(html, proveedor):
    """Problemas de una versión para portal (lista vacía = bien). Los portales prohíben anuncios propios y enlaces de salida."""
    malos = []
    sdk = SDK_PORTAL.get(proveedor, '')
    sin_sdk = html.replace(sdk, '') if sdk else html
    externos = sorted(set(u for u in re.findall(r'https?://[^\s"\'<>)\\]+', sin_sdk) if not u.startswith('http://www.w3.org/')))
    if externos:
        malos.append('enlaces o llamadas externas en el código: ' + ', '.join(externos))
    if 'googlesyndication' in html:
        malos.append('trae código de AdSense: en un portal solo se permiten los anuncios de su SDK')
    if sdk and sdk not in html:
        malos.append('falta el SDK del portal en la cabecera')
    return malos


def variantes(raiz, fabrica, juego_id, proveedores=None):
    """Arma dist/portales/<juego>/<proveedor>/ (index.html + zip) con el SDK del portal. Devuelve [(proveedor, carpeta, problemas)]."""
    raiz = pathlib.Path(raiz)
    spec = fabrica.cargar(juego_id)
    if juego_id not in juegos_con_ganchos(raiz, fabrica):
        raise ErrorMonetizacion('%s todavía no llama al módulo «anuncios»: sin ganchos no hay dónde mostrar anuncios' % juego_id)
    hechos = []
    for prov in (proveedores or sorted(SDK_PORTAL)):
        if prov not in SDK_PORTAL:
            raise ErrorMonetizacion('no armo «%s»: su SDK no está confirmado (Poki lo entrega después de aceptar el juego)' % prov)
        v = copy.deepcopy(spec)
        v['apoyo_url'] = ''                      # un portal no admite enlaces de salida ni propinas aparte
        v['_anuncios'] = {'proveedor': prov}
        destino = raiz / 'dist' / 'portales' / juego_id / prov
        fabrica.construir(juego_id, spec=v, destino=destino, cabeza_extra=SDK_PORTAL[prov])
        malos = revisar_variante((destino / 'index.html').read_text(encoding='utf-8'), prov)
        hechos.append((prov, destino, malos))
    return hechos


# ---------------------------------------------------------------------------------------------------------------------
# Informe
# ---------------------------------------------------------------------------------------------------------------------

NOMBRES = {'portales': 'Portales con revenue share', 'adsense-sitio': 'AdSense en el sitio propio', 'donaciones': 'Donaciones y pago libre'}


def informe(raiz, fabrica):
    raiz = pathlib.Path(raiz)
    pol = politica(raiz)
    L = []
    malos = problemas_de_politica(pol)
    if malos:
        L += ['**La política de monetización tiene problemas:**'] + ['- ' + m for m in malos] + ['']
    est = estado(raiz, fabrica)
    L.append('Hoy no se muestra ningún anuncio ni se cobra nada: todas las rutas están %s.' % ('apagadas' if not any(e['activa'] for e in est.values()) else 'así: ' + ', '.join('%s=%s' % (n, 'encendida' if e['activa'] else 'apagada') for n, e in est.items())))
    L.append('')
    for n, e in est.items():
        L.append('### %s (%s)' % (NOMBRES.get(n, n), 'encendida' if e['activa'] else 'apagada'))
        L += ['- Listo: ' + x for x in e['listo']]
        L += ['- Falta (fábrica): ' + x for x in e['falta_fabrica']]
        L += ['- Falta (dueño): ' + x for x in e['falta_dueno']]
        L.append('')
    L.append('### Cuentas con la fórmula (supuestos en monetizacion/politica.json)')
    L.append('')
    L.append('| Sesiones por día | eCPM supuesto | Por mes (US$) | Días para juntar 50 (el pago mínimo más bajo de los portales) |')
    L.append('|---|---|---|---|')
    for f in escenarios(raiz):
        L.append('| %s | US$%s | %s | %s |' % (format(f['sesiones_dia'], ','), f['ecpm'], format(f['mes_usd'], ',.2f'), f['dias_a_pago_minimo'] if f['dias_a_pago_minimo'] is not None else '—'))
    L.append('')
    return L
