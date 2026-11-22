"""Núcleo de la publicación: plan, huella, compuertas, ritmo, libro de registro y ejecución.

Cómo funciona (en este orden):
  1. PLAN. Con la ficha del juego, la política (`publicacion/politica.json`) y el sitio (`publicacion/sitio.json`) se arma la lista exacta de acciones:
     qué se despliega, qué texto sale en cada canal, con qué imagen o video. El plan no toca la red ni necesita claves.
  2. HUELLA. Es el SHA-256 de todo el plan (textos, enlaces, hash de cada archivo, política). Si cambia una coma, cambia la huella.
  3. APROBACIÓN. Solo se ejecuta con `--aprobar HUELLA` (o con el entorno de GitHub aprobado por ti): el trabajo vuelve a calcular el plan y
     se detiene si la huella no coincide. Quien aprueba aprueba exactamente lo que se verá publicado.
  4. COMPUERTAS. Antes de cualquier acción: comprobador de novedad (¿es otro juego o una variante?), kit sin marcas pendientes, sitio configurado de
     verdad, textos con el enlace real y la línea de IA, y ritmo (máximos por día y por canal, separación entre lanzamientos).
  5. EJECUCIÓN. Las claves salen solo de variables de entorno; si falta una, esa acción falla con un mensaje claro. Cada resultado se anota en el libro
     (`publicacion/libro.jsonl`); repetir la misma ejecución no duplica nada (lo ya hecho se salta). Si un envío queda en duda (corte de red), se anota
     «incierto» y no se reintenta solo: una persona mira primero si salió.
Qué nunca hace: crear cuentas, aceptar términos, configurar cobros, dar me gusta, seguir cuentas, responder o escribir mensajes privados."""
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

from . import red

VERSION_PLAN = 1
ORDEN_CATEGORIA = {'sitio': 0, 'redes': 2, 'portales': 3}
ORDEN_TIPO = {'desplegar': 0, 'avisar': 1, 'post': 2, 'video': 3, 'empujar': 4}


class ErrorPublicacion(Exception):
    """Una acción falló. incierto=True cuando pudo haberse hecho aunque no haya respuesta (no se reintenta sola)."""

    def __init__(self, mensaje, incierto=False, extra=None):
        super().__init__(mensaje)
        self.incierto = incierto
        self.extra = dict(extra or {})   # datos sin secretos que sirven para comprobar después qué pasó (por ejemplo la cuenta, «did»)


class ErrorPlan(Exception):
    """El plan de un canal no se puede armar (texto demasiado largo, falta un archivo…). Se muestra al dueño y bloquea la ejecución."""


def canonico(o):
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def sha256_texto(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def sha256_archivo(ruta):
    h = hashlib.sha256()
    with open(ruta, 'rb') as f:
        for bloque in iter(lambda: f.read(1 << 20), b''):
            h.update(bloque)
    return h.hexdigest()


def huella_carpeta(carpeta):
    """Huella de todos los archivos de una carpeta (rutas y contenidos); None si no existe."""
    carpeta = pathlib.Path(carpeta)
    if not carpeta.is_dir():
        return None
    return sha256_texto(canonico([[str(p.relative_to(carpeta)).replace('\\', '/'), sha256_archivo(p)] for p in sorted(carpeta.rglob('*')) if p.is_file()]))


def cargar_json(ruta, defecto=None):
    ruta = pathlib.Path(ruta)
    if not ruta.exists():
        return defecto
    return json.loads(ruta.read_text(encoding='utf-8'))


def _version(v):
    return tuple(int(x) for x in re.findall(r'\d+', str(v))[:3])


def _hora(iso):
    return datetime.datetime.fromisoformat(iso.replace('Z', '+00:00'))


# ---------------------------------------------------------------------------------------------------------------------
# Entorno inyectable (claves, red, comandos y reloj): las pruebas lo sustituyen
# ---------------------------------------------------------------------------------------------------------------------

def _ejecutar_cmd(argv, cwd=None, env=None, tiempo=900):
    r = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=tiempo)
    return r.returncode, r.stdout, r.stderr


class Entorno:
    def __init__(self, env=None, http=None, cmd=None, ahora=None, dormir=None):
        self.env = dict(os.environ if env is None else env)
        self.http = http or (lambda metodo, url, cabeceras=None, cuerpo=None: red.solicitar(metodo, url, cabeceras, cuerpo))
        self.cmd = cmd or _ejecutar_cmd
        self.ahora = ahora or (lambda: datetime.datetime.now(datetime.timezone.utc))
        self.dormir = dormir or time.sleep


# ---------------------------------------------------------------------------------------------------------------------
# Libro de registro
# ---------------------------------------------------------------------------------------------------------------------

class Libro:
    def __init__(self, ruta):
        self.ruta = pathlib.Path(ruta)

    def entradas(self):
        if not self.ruta.exists():
            return []
        return [json.loads(l) for l in self.ruta.read_text(encoding='utf-8').splitlines() if l.strip()]

    def agregar(self, ahora, **campos):
        campos['ts'] = ahora.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ruta, 'a', encoding='utf-8') as f:
            f.write(json.dumps(campos, sort_keys=True, ensure_ascii=False) + '\n')

    def hecho(self, accion_id):
        return any(e.get('accion') == accion_id and e.get('resultado') == 'ok' for e in self.entradas())

    def ultima(self, accion_id):
        previas = [e for e in self.entradas() if e.get('accion') == accion_id]
        return previas[-1] if previas else None

    def incierto(self, accion_id):
        """True si lo último que se anotó de esta acción fue un resultado dudoso: nadie sabe si salió."""
        u = self.ultima(accion_id)
        return bool(u) and u.get('resultado') == 'incierto'


# ---------------------------------------------------------------------------------------------------------------------
# Contexto: todo lo que un adaptador necesita para armar sus acciones
# ---------------------------------------------------------------------------------------------------------------------

class Contexto:
    def __init__(self, raiz, juego_id, libro=None):
        self.raiz = pathlib.Path(raiz)
        self.id = juego_id
        herramientas = str(self.raiz / 'herramientas')
        if herramientas not in sys.path:
            sys.path.insert(0, herramientas)
        ruta = self.raiz / 'juegos' / juego_id / 'juego.json'
        if not ruta.exists():
            raise ErrorPlan('no existe la ficha %s' % ruta)
        self.spec = json.loads(ruta.read_text(encoding='utf-8'))
        self.version = self.spec['version']
        self.politica = cargar_json(self.raiz / 'publicacion' / 'politica.json', {})
        self.sitio = cargar_json(self.raiz / 'publicacion' / 'sitio.json', {})
        self.libro = libro or Libro(self.raiz / 'publicacion' / 'libro.jsonl')
        self.salida = self.raiz / 'salida' / juego_id
        self.dist = self.raiz / 'dist' / 'sitio'
        previas = [e for e in self.libro.entradas() if e.get('juego') == juego_id and e.get('canal') == 'sitio-propio' and e.get('resultado') == 'ok']
        if not previas:
            self.tipo = 'lanzamiento'
        else:
            ultima = max(_version(e['version']) for e in previas)
            self.tipo = 'parche' if _version(self.version) > ultima else 'sin-cambios'

    # direcciones del sitio propio
    def base(self):
        return str(self.sitio.get('url_base', '')).rstrip('/')

    def url_juego(self, idioma):
        return '%s/%s/juegos/%s/' % (self.base(), idioma, self.id)

    def idioma_de(self, canal):
        idioma = (self.politica.get('idioma') or {}).get(canal) or self.spec['idiomas'][0]
        if idioma not in self.spec['idiomas']:
            raise ErrorPlan('%s: el juego no tiene versión en «%s» (idiomas: %s)' % (canal, idioma, ', '.join(self.spec['idiomas'])))
        return idioma

    def archivo(self, ruta_relativa):
        ruta = self.raiz / ruta_relativa
        if not ruta.exists():
            return None
        return {'archivo': ruta_relativa, 'sha256': sha256_archivo(ruta)}

    def imagen_social(self):
        """Portada del juego; si falta, la mejor captura de escritorio; si no hay nada, None (se publica solo texto)."""
        medios = self.salida / 'medios'
        candidatas = (['portada.png'] + sorted(p.name for p in medios.glob('captura-*-escritorio.png'))) if medios.exists() else []
        for nombre in candidatas:
            a = self.archivo('salida/%s/medios/%s' % (self.id, nombre))
            if a:
                return a
        return None

    def texto_alternativo(self, idioma):
        f = self.spec['ficha'][idioma]
        return ('%s: %s' % (f['titulo'], f['corta']))[:300]

    def linea_ia(self, idioma):
        import kit_lanzamiento
        return kit_lanzamiento.linea_ia(self.spec, idioma)

    def linea_ia_corta(self, idioma):
        import kit_lanzamiento
        return kit_lanzamiento.linea_ia_corta(self.spec, idioma)


# ---------------------------------------------------------------------------------------------------------------------
# Plan y huella
# ---------------------------------------------------------------------------------------------------------------------

def huella_de(plan):
    """La huella cubre todo lo que se publicará. No incluye `tipo` (lanzamiento/parche/sin-cambios): se deduce del libro y cambia después de una
    ejecución parcial; así, repetir un trabajo que falló a medias sigue cubierto por la misma aprobación."""
    return sha256_texto(canonico({k: v for k, v in plan.items() if k not in ('huella', 'tipo')}))


def construir_plan(ctx, adaptadores, solo=None):
    """(plan, problemas). Los problemas son cosas que impiden ejecutar (el plan se puede leer igualmente).
    solo: conjunto de canales a los que limitar el plan. Un parche no se anuncia en redes salvo que politica.json lo pida (avisar_parches)."""
    problemas, acciones = [], []
    activos = ctx.politica.get('canales', [])
    conocidos = {a.canal for a in adaptadores}
    for c in activos:
        if c not in conocidos:
            problemas.append('politica.json: el canal «%s» no tiene adaptador (canales con adaptador: %s)' % (c, ', '.join(sorted(conocidos))))
    for c in sorted(solo or []):
        if c not in activos:
            problemas.append('--solo: el canal «%s» no está activo en publicacion/politica.json' % c)
    for ad in adaptadores:
        if ad.canal not in activos or (solo and ad.canal not in solo):
            continue
        try:
            for a in ad.acciones(ctx):
                if ctx.tipo == 'parche' and a['tipo'] in ('post', 'video') and not ctx.politica.get('avisar_parches'):
                    continue
                a.setdefault('canal', ad.canal)
                a.setdefault('categoria', ad.categoria)
                acciones.append(a)
        except ErrorPlan as e:
            problemas.append('%s: %s' % (ad.canal, e))
    acciones.sort(key=lambda a: (ORDEN_CATEGORIA.get(a['categoria'], 9), ORDEN_TIPO.get(a['tipo'], 9), a['canal']))
    plan = {'version_plan': VERSION_PLAN, 'juego': ctx.id, 'version': ctx.version, 'tipo': ctx.tipo, 'politica': sha256_texto(canonico({k: v for k, v in ctx.politica.items() if k != 'nota'})),
            'sitio': sha256_texto(canonico({k: v for k, v in ctx.sitio.items() if k != 'nota'})), 'acciones': acciones}
    plan['huella'] = huella_de(plan)
    return plan, problemas


# ---------------------------------------------------------------------------------------------------------------------
# Compuertas
# ---------------------------------------------------------------------------------------------------------------------

def _marca_de_ejemplo(valor):
    return (not valor) or 'CAMBIA' in str(valor).upper()


def compuertas(ctx, plan, plan_problemas, ahora):
    """Lista de razones por las que NO se debe ejecutar el plan. Vacía = se puede."""
    p = list(plan_problemas)
    sys.path.insert(0, str(ctx.raiz / 'herramientas'))
    import novedad
    import revisar_kit
    if novedad.es_beta(ctx.spec):
        p.append('es una beta (estado «beta» en su ficha): un prototipo para probar con bots no se publica; hay que promoverla primero')
    nov = novedad.evaluar(ctx.raiz, ctx.id)
    p += nov['errores']
    for cat in sorted({a['categoria'] for a in plan['acciones']}):
        if not nov['apto'].get(cat, True):
            p.append('el comprobador de novedad no declara apto este juego para «%s»: %s' % (cat, ' '.join(nov['motivos']) or 'sin motivo'))
    if novedad.pendientes(ctx.spec):
        p.append('la ficha todavía tiene campos PENDIENTE')
    errores, _ = revisar_kit.revisar(ctx.raiz, ctx.id)
    p += ['kit: %s' % e for e in errores]
    import motor as motor_calidad
    p += motor_calidad.compuerta(ctx.raiz, ctx.spec, ctx.libro.entradas(), ctx.tipo)
    activos = set(ctx.politica.get('canales', []))
    if 'sitio-propio' in activos:
        if _marca_de_ejemplo(ctx.sitio.get('proyecto')):
            p.append('sitio.json: falta el nombre real del proyecto de Cloudflare Pages («proyecto»)')
        if not str(ctx.sitio.get('contacto', '')).strip():
            p.append('sitio.json: falta el contacto público de la política de privacidad («contacto»)')
    if activos and (_marca_de_ejemplo(ctx.sitio.get('url_base')) or not str(ctx.sitio.get('url_base', '')).startswith('https://')):
        p.append('sitio.json: «url_base» debe ser la dirección https real del sitio (hoy dice «%s»)' % ctx.sitio.get('url_base'))
    if any(a['categoria'] == 'redes' for a in plan['acciones']):
        en_plan = any(a['canal'] == 'sitio-propio' for a in plan['acciones'])
        antes = any(e.get('canal') == 'sitio-propio' and e.get('resultado') == 'ok' and e.get('juego') == ctx.id for e in ctx.libro.entradas())
        if not (en_plan or antes):
            p.append('los textos de redes enlazan al sitio propio, pero este juego todavía no está publicado ahí: activa «sitio-propio» en politica.json')
    if ctx.tipo == 'lanzamiento':
        dias = (ctx.politica.get('ritmo') or {}).get('min_dias_entre_lanzamientos', 0)
        otros = [e for e in ctx.libro.entradas() if e.get('lanzamiento') and e.get('resultado') == 'ok' and e.get('juego') != ctx.id and e.get('tipo') == 'desplegar']
        if dias and otros:
            ult = max(_hora(e['ts']) for e in otros)
            if ahora - ult < datetime.timedelta(days=dias):
                p.append('ritmo: el último lanzamiento fue el %s; la política pide al menos %d días entre juegos nuevos' % (ult.date().isoformat(), dias))
    return p


def revisar_ritmo(ctx, accion, ahora):
    """None si la acción cabe en el ritmo del canal; si no, la razón."""
    r = ((ctx.politica.get('ritmo') or {}).get('canales') or {}).get(accion['canal'])
    if not r or accion['tipo'] not in ('post', 'video'):
        return None
    previas = sorted(_hora(e['ts']) for e in ctx.libro.entradas() if e.get('canal') == accion['canal'] and e.get('resultado') == 'ok' and e.get('tipo') in ('post', 'video'))
    if len([t for t in previas if ahora - t < datetime.timedelta(hours=24)]) >= r.get('max_por_dia', 10 ** 6):
        return 'ritmo: ya hay %d publicaciones en las últimas 24 h (máximo %d)' % (r['max_por_dia'], r['max_por_dia'])
    if previas and ahora - previas[-1] < datetime.timedelta(hours=r.get('min_horas_entre', 0)):
        return 'ritmo: la última fue hace menos de %d h' % r['min_horas_entre']
    return None


# ---------------------------------------------------------------------------------------------------------------------
# Ejecución
# ---------------------------------------------------------------------------------------------------------------------

def aprobada(plan, aprobar):
    a = (aprobar or '').strip().lower()
    return len(a) >= 12 and re.fullmatch(r'[0-9a-f]+', a) is not None and plan['huella'].startswith(a)


def ejecutar(ctx, plan, plan_problemas, aprobar, ent, adaptadores):
    """Ejecuta un plan aprobado. Devuelve (informe, ok). Cada línea del informe: dict(accion, canal, resultado, detalle)."""
    informe = []
    if not aprobada(plan, aprobar):
        raise ErrorPublicacion('la aprobación no coincide con la huella del plan (%s…): vuelve a leer el plan y aprueba la huella actual' % plan['huella'][:12])
    razones = compuertas(ctx, plan, plan_problemas, ent.ahora())
    if razones:
        raise ErrorPublicacion('no se ejecuta nada; antes hay que resolver:\n  - ' + '\n  - '.join(razones))
    por_canal = {a.canal: a for a in adaptadores}
    todo_ok = True
    for acc in plan['acciones']:
        ad = por_canal[acc['canal']]
        base = {'accion': acc['id'], 'canal': acc['canal'], 'tipo': acc['tipo'], 'juego': ctx.id, 'version': ctx.version, 'huella': plan['huella'],
                'lanzamiento': ctx.tipo == 'lanzamiento'}
        texto_post = (acc.get('datos') or {}).get('texto')
        if acc['tipo'] == 'post' and isinstance(texto_post, str):
            base['texto_sha256'] = sha256_texto(texto_post)   # con esto se puede comprobar después, sin las claves, si ese texto llegó a salir

        def anotar(resultado, detalle='', ref=None, url=None, mas=None):
            informe.append({'accion': acc['id'], 'canal': acc['canal'], 'resultado': resultado, 'detalle': detalle})
            extra = {k: v for k, v in (('ref', ref), ('url', url)) if v}
            extra.update({k: v for k, v in (mas or {}).items() if isinstance(v, (str, int)) and v != ''})
            ctx.libro.agregar(ent.ahora(), resultado=resultado, detalle=detalle, **dict(base, **extra))
        if ctx.libro.hecho(acc['id']):
            informe.append({'accion': acc['id'], 'canal': acc['canal'], 'resultado': 'ya hecho', 'detalle': 'esta misma acción ya salió (libro)'})
            continue
        if ctx.libro.incierto(acc['id']):
            informe.append({'accion': acc['id'], 'canal': acc['canal'], 'resultado': 'detenido',
                            'detalle': 'una ejecución anterior quedó en duda (puede haber salido). Mira la cuenta y anota qué pasó: python3 fabrica.py resolver %s salio|no-salio' % acc['id']})
            todo_ok = False
            if acc['categoria'] == 'sitio':
                break
            continue
        faltan = [s for s in ad.secretos if not ent.env.get(s)]
        if faltan:
            anotar('error', 'faltan secretos en el entorno: ' + ', '.join(faltan))
            todo_ok = False
            if acc['categoria'] == 'sitio':
                break
            continue
        razon = revisar_ritmo(ctx, acc, ent.ahora())
        if razon:
            anotar('omitido', razon)
            continue
        valores = [ent.env.get(s) for s in ad.secretos]
        try:
            r = ad.ejecutar(acc, ent, ctx) or {}
            anotar('ok', red.redactar(r.get('detalle', ''), valores), r.get('ref'), r.get('url'))
        except ErrorPublicacion as e:
            anotar('incierto' if e.incierto else 'error', red.redactar(str(e), valores), mas=e.extra if e.incierto else None)
            todo_ok = False
            if acc['categoria'] == 'sitio':
                break
        except red.ErrorRed as e:
            anotar('incierto' if acc['tipo'] in ('post', 'video', 'empujar') else 'error', red.redactar('sin respuesta de la red: %s' % e, valores))
            todo_ok = False
            if acc['categoria'] == 'sitio':
                break
    return informe, todo_ok


def resolver(libro, accion_id, salio, ahora, quien='persona', extra=None):
    """Una persona (o la comprobación automática, publicacion/comprobar.py) dice qué pasó con una acción dudosa.
    salio=True → se da por hecha; False → se descarta y podrá reintentarse. `extra`: datos que se anotan (por ejemplo ref y url del post hallado)."""
    u = libro.ultima(accion_id)
    if not u or u.get('resultado') != 'incierto':
        raise ErrorPublicacion('«%s» no tiene un resultado dudoso en el libro; nada que resolver' % accion_id)
    campos = {k: u[k] for k in ('accion', 'canal', 'tipo', 'juego', 'version', 'huella', 'lanzamiento', 'texto_sha256') if k in u}
    campos.update({k: v for k, v in (extra or {}).items() if v})
    libro.agregar(ahora, resultado='ok' if salio else 'descartado', detalle='resuelto por %s: %s' % (quien, 'sí salió' if salio else 'no salió'), **campos)


# ---------------------------------------------------------------------------------------------------------------------
# Presentación del plan
# ---------------------------------------------------------------------------------------------------------------------

def mostrar_plan(ctx, plan, problemas, razones):
    L = ['Plan de publicación · %s v%s · %s' % (plan['juego'], plan['version'], plan['tipo']), 'Huella: %s' % plan['huella'], '']
    if not plan['acciones']:
        L.append('(el plan no tiene acciones: ' + ('mira abajo por qué no se pudo armar)' if problemas else 'no hay canales activos en publicacion/politica.json)'))
    for i, a in enumerate(plan['acciones'], 1):
        L.append('%d. [%s] %s · %s%s' % (i, a['canal'], a['tipo'], a['id'], '   (YA HECHO: el libro lo registra; se salta)' if ctx.libro.hecho(a['id']) else ''))
        d = a['datos']
        for k in sorted(d):
            v = d[k]
            if k == 'texto':
                L += ['     texto:'] + ['       | ' + linea for linea in v.split('\n')]
            else:
                L.append('     %s: %s' % (k, json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v))
    if problemas or razones:
        L += ['', 'NO SE PUEDE EJECUTAR TODAVÍA:'] + ['  - ' + x for x in problemas + [r for r in razones if r not in problemas]]
    else:
        L += ['', 'Compuertas: todo en orden. Para publicar: python3 fabrica.py publicar %s --ejecutar --aprobar %s' % (plan['juego'], plan['huella'][:16])]
    return '\n'.join(L)
