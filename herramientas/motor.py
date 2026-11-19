"""El motor que crece solo: módulos opcionales, escalera de calidad, piso que solo sube, pruebas del motor y cola de mejoras.

Qué hace cada pieza (todo es de archivos: nada de esto necesita red ni claves):
  motor/modulos.json   los módulos opcionales (accesible, efectos, musica…) y qué piden. Un juego usa los que declara en juego.json → «motor».
                       El núcleo (motor/ggx.js) no cambia nunca por esto: un juego sin «motor» se construye byte por byte como siempre.
  motor/escalera.json  niveles de calidad con requisitos medibles. nivel_de() dice en qué nivel está un juego.
  motor/piso.json      lo mejor ya publicado: el juego nuevo debe subir un nivel por encima, sin pasar del techo (lo que el motor soporta hoy).
                       Solo sube: `sincronizar` lo actualiza desde el libro de publicación (los juegos «heredados» quedan exentos de la regla).
  motor/informe.json   resultado de las pruebas del motor en un navegador real (`python3 fabrica.py motor probar`), atado a la huella del código del motor:
                       si el motor o un módulo cambia y no se vuelven a correr las pruebas, el informe deja de estar vigente y ningún juego que lo use sale.
  motor/ideas.json     respaldo de lo que el motor aún no sabe hacer, en el orden de construcción.
  cola()               la lista de mejoras que sigue, calculada (no escrita a mano): pruebas vencidas, huecos de la escalera, juegos por debajo
                       de su nivel, pedidos de los propios juegos y, cuando el techo ya se alcanzó, la siguiente idea a construir."""
import hashlib
import json
import pathlib
import re


class ErrorMotor(Exception):
    pass


def _json(ruta, defecto=None):
    ruta = pathlib.Path(ruta)
    return json.loads(ruta.read_text(encoding='utf-8')) if ruta.exists() else defecto


def manifiesto(raiz):
    return (_json(pathlib.Path(raiz) / 'motor' / 'modulos.json', {}) or {}).get('modulos', {})


def escalera(raiz):
    return _json(pathlib.Path(raiz) / 'motor' / 'escalera.json', {'requisitos': {}, 'niveles': []})


def modulos_de(raiz, spec):
    """[(nombre, version, fuente)] de los módulos que declara el juego, en el orden de carga del manifiesto. Falla con un motivo claro."""
    pedidos = spec.get('motor') or []
    if not pedidos:
        return []
    man = manifiesto(raiz)
    if not isinstance(pedidos, list) or len(set(pedidos)) != len(pedidos):
        raise ErrorMotor('«motor» debe ser una lista sin repetidos (hoy: %r)' % (pedidos,))
    for n in pedidos:
        if n not in man:
            raise ErrorMotor('el módulo «%s» no existe; módulos disponibles: %s' % (n, ', '.join(man) or 'ninguno'))
        for dep in man[n].get('pide', []):
            if dep not in pedidos:
                raise ErrorMotor('el módulo «%s» pide «%s»: agrégalo a «motor» en juego.json' % (n, dep))
    salida = []
    for n in man:                                   # el orden de carga lo manda el manifiesto, no el orden en que el juego los nombró
        if n in pedidos:
            ruta = pathlib.Path(raiz) / 'motor' / 'modulos' / man[n]['archivo']
            if not ruta.exists():
                raise ErrorMotor('falta el archivo del módulo «%s»: %s' % (n, ruta))
            texto = ruta.read_text(encoding='utf-8')
            if not texto.endswith('\n'):
                texto += '\n'
            salida.append((n, man[n]['version'], texto))
    return salida


# ---------------------------------------------------------------------------------------------------------------------
# Pruebas del motor: informe atado a la huella del código
# ---------------------------------------------------------------------------------------------------------------------

def huella_del_motor(raiz):
    """Huella del código que las pruebas del motor cubren: núcleo, manifiesto, cada módulo y el propio guion de pruebas."""
    raiz = pathlib.Path(raiz)
    h = hashlib.sha256()
    archivos = [raiz / 'motor' / 'ggx.js', raiz / 'motor' / 'modulos.json', raiz / 'herramientas' / 'probar_motor.js']
    archivos += sorted((raiz / 'motor' / 'modulos').glob('*.js')) if (raiz / 'motor' / 'modulos').is_dir() else []
    for a in archivos:
        h.update(a.relative_to(raiz).as_posix().encode() + b'\0')
        h.update(a.read_bytes() if a.exists() else b'')
        h.update(b'\0')
    return h.hexdigest()[:16]


def informe(raiz):
    return _json(pathlib.Path(raiz) / 'motor' / 'informe.json')


def informe_vigente(raiz):
    """(True, '') si las pruebas del motor están al día y pasaron; si no, (False, motivo)."""
    inf = informe(raiz)
    if not inf:
        return False, 'las pruebas del motor nunca se han corrido: `python3 fabrica.py motor probar`'
    if inf.get('fuente') != huella_del_motor(raiz):
        return False, 'el motor o sus pruebas cambiaron desde la última corrida: `python3 fabrica.py motor probar`'
    if not inf.get('ok'):
        malos = [n for n, m in (inf.get('modulos') or {}).items() if m.get('fallas')]
        return False, 'las pruebas del motor fallan%s' % ((' (módulos: %s)' % ', '.join(malos)) if malos else '')
    return True, ''


def escribir_informe(raiz, resultado):
    """Guarda el informe a partir de lo que imprime probar_motor.js. Sin fecha: el mismo código y las mismas pruebas dan el mismo archivo."""
    man = manifiesto(raiz)
    modulos = {}
    for n, m in man.items():
        r = (resultado.get('modulos') or {}).get(n) or {'pruebas': 0, 'fallas': 1, 'fallos': ['no se probó']}
        modulos[n] = {'version': m['version'], 'pruebas': r['pruebas'], 'fallas': r['fallas'], 'fallos': r.get('fallos', [])}
    nuc = resultado.get('nucleo') or {'pruebas': 0, 'fallas': 1, 'fallos': ['no se probó']}
    nucleo = {'version': _version_del_nucleo(raiz), 'pruebas': nuc['pruebas'], 'fallas': nuc['fallas'], 'fallos': nuc.get('fallos', [])}
    ok = nucleo['fallas'] == 0 and all(m['fallas'] == 0 and m['pruebas'] > 0 for m in modulos.values()) and nucleo['pruebas'] > 0
    inf = {'fuente': huella_del_motor(raiz), 'ok': ok, 'nucleo': nucleo, 'modulos': modulos}
    (pathlib.Path(raiz) / 'motor' / 'informe.json').write_text(json.dumps(inf, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    return inf


def _version_del_nucleo(raiz):
    m = re.search(r"version: '([\d.]+)'", (pathlib.Path(raiz) / 'motor' / 'ggx.js').read_text(encoding='utf-8'))
    return m.group(1) if m else '?'


def pagina_de_prueba(raiz):
    """HTML mínimo con el núcleo y TODOS los módulos, para probarlos sin ningún juego."""
    raiz = pathlib.Path(raiz)
    cfg = {'id': 'prueba-motor', 'version': '0', 'idiomas': ['es', 'en', 'zh'], 'titulo': 'Prueba del motor', 'apoyo_url': ''}
    partes = ['<!doctype html><meta charset="utf-8"><title>Prueba del motor</title><body><canvas id="cv" width="200" height="200"></canvas>',
              '<script>window.GGX_CONFIG=%s;window.JUEGO=%s;</script>' % (json.dumps(cfg), json.dumps({'parametros': {}, 'textos': {'es': {}, 'en': {}, 'zh': {}}})),
              '<script>\n%s</script>' % (raiz / 'motor' / 'ggx.js').read_text(encoding='utf-8')]
    for n, _, texto in modulos_de(raiz, {'motor': list(manifiesto(raiz))}):
        partes.append('<script id="mod-%s">\n%s</script>' % (n, texto))
    return '\n'.join(partes) + '\n'


# ---------------------------------------------------------------------------------------------------------------------
# Escalera de calidad
# ---------------------------------------------------------------------------------------------------------------------

def _fuentes_de_juego(raiz, spec):
    base = pathlib.Path(raiz) / 'plantillas' / spec.get('plantilla', '')
    textos = []
    p = base / 'plantilla.html'
    if p.exists():
        textos.append(p.read_text(encoding='utf-8'))
    for paq in spec.get('paquetes', []):
        q = base / 'paquetes' / (paq + '.js')
        if q.exists():
            textos.append(q.read_text(encoding='utf-8'))
    return '\n'.join(textos)


def _cumple(raiz, spec, req):
    motor = set(spec.get('motor') or [])
    if req == 'idiomas':
        return {'es', 'en', 'zh'} <= set(spec.get('idiomas', []))
    if req == 'sonido':
        return ('musica' in motor and _usa(raiz, spec, 'musica')) or bool(re.search(r'\bsfx\(', _fuentes_de_juego(raiz, spec)))
    return req in motor and _usa(raiz, spec, req)


def _usa(raiz, spec, req):
    """Comprobación estática: el código del juego (plantilla y paquetes) llama al módulo. Declararlo sin usarlo no sube de nivel."""
    patron = escalera(raiz)['requisitos'].get(req, {}).get('uso')
    return bool(patron) and bool(re.search(patron, _fuentes_de_juego(raiz, spec)))


def modulo_disponible(raiz, nombre):
    """Un módulo cuenta cuando está en el manifiesto y sus pruebas pasaron con el código de hoy."""
    if nombre not in manifiesto(raiz):
        return False
    vigente, _ = informe_vigente(raiz)
    if not vigente:
        return False
    m = (informe(raiz).get('modulos') or {}).get(nombre) or {}
    return m.get('pruebas', 0) > 0 and m.get('fallas', 1) == 0


def nivel_de(raiz, spec):
    """{'nivel': n, 'nombre': …, 'cumplidos': {req: bool}, 'faltan': [(nivel, req, texto)]} para la ficha de un juego."""
    esc = escalera(raiz)
    reqs = esc['requisitos']
    cumplidos = {}
    for r, d in reqs.items():
        ok = _cumple(raiz, spec, r)
        if ok and d.get('modulo') and not modulo_disponible(raiz, d['modulo']):
            ok = False                                    # lo usa, pero el motor no tiene pruebas vigentes de ese módulo: no cuenta
        cumplidos[r] = ok
    nivel, nombre, faltan = 0, 'Sin nivel', []
    for n in esc['niveles']:
        malos = [r for r in n['requiere'] if not cumplidos.get(r)]
        if malos and not faltan:
            faltan = [(n['n'], r, reqs[r]['texto']) for r in malos]
        if not malos and not faltan:
            nivel, nombre = n['n'], n['nombre']
    return {'nivel': nivel, 'nombre': nombre, 'cumplidos': cumplidos, 'faltan': faltan}


def _faltan_hasta(raiz, spec, tope):
    """Requisitos sin cumplir de los niveles hasta `tope` (para decir qué le falta a un juego publicado frente al techo)."""
    esc = escalera(raiz)
    n = nivel_de(raiz, spec)
    return [(nv['n'], r) for nv in esc['niveles'] if nv['n'] <= tope for r in nv['requiere'] if not n['cumplidos'].get(r)]


def techo(raiz):
    """El nivel más alto que el motor soporta hoy: todos sus requisitos con módulo existen y están probados."""
    esc = escalera(raiz)
    t = 0
    for n in esc['niveles']:
        if all(not esc['requisitos'][r].get('modulo') or modulo_disponible(raiz, esc['requisitos'][r]['modulo']) for r in n['requiere']):
            t = n['n']
        else:
            break
    return t


# ---------------------------------------------------------------------------------------------------------------------
# Piso que solo sube
# ---------------------------------------------------------------------------------------------------------------------

def _piso(raiz):
    return _json(pathlib.Path(raiz) / 'motor' / 'piso.json', {'heredados': [], 'niveles': {}}) or {'heredados': [], 'niveles': {}}


def lanzados(entradas):
    """Juegos con lanzamiento exitoso en el libro de publicación."""
    return sorted({e.get('juego') for e in entradas if e.get('lanzamiento') and e.get('resultado') == 'ok' and e.get('tipo') == 'desplegar' and e.get('juego')})


def _spec_de(raiz, juego):
    return _json(pathlib.Path(raiz) / 'juegos' / juego / 'juego.json')


def sincronizar(raiz, entradas, escribir=True):
    """Sube el piso con los juegos ya lanzados: el nivel de cada uno solo puede subir. Devuelve el contenido de piso.json."""
    datos = _piso(raiz)
    niveles = dict(datos.get('niveles', {}))
    for j in lanzados(entradas):
        spec = _spec_de(raiz, j)
        if spec:
            niveles[j] = max(niveles.get(j, 0), nivel_de(raiz, spec)['nivel'])
    nuevo = {'nota': datos.get('nota', ''), 'heredados': datos.get('heredados', []), 'niveles': dict(sorted(niveles.items()))}
    if escribir and nuevo != datos:
        (pathlib.Path(raiz) / 'motor' / 'piso.json').write_text(json.dumps(nuevo, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return nuevo


def piso_sin(raiz, entradas, juego=None):
    """El nivel del mejor juego ya publicado, sin contar a `juego`."""
    niveles = sincronizar(raiz, entradas, escribir=False)['niveles']
    return max([n for j, n in niveles.items() if j != juego] or [0])


def exigido(raiz, spec, entradas):
    """Nivel mínimo para lanzar este juego: uno por encima del mejor publicado, sin pasar del techo. 0 si es heredado."""
    datos = _piso(raiz)
    if spec['id'] in datos.get('heredados', []):
        return 0
    return min(piso_sin(raiz, entradas, spec['id']) + 1, techo(raiz))


def compuerta(raiz, spec, entradas, tipo):
    """Razones por las que este juego no debe publicarse todavía, desde el punto de vista de la calidad del motor."""
    razones = []
    if spec.get('motor'):
        try:
            modulos_de(raiz, spec)
        except ErrorMotor as e:
            razones.append('motor: %s' % e)
        vigente, motivo = informe_vigente(raiz)
        if not vigente:
            razones.append('motor: %s' % motivo)
    n = nivel_de(raiz, spec)
    if tipo == 'lanzamiento':
        pide = exigido(raiz, spec, entradas)
        if n['nivel'] < pide:
            falta = '; '.join('nivel %d: %s' % (nv, t) for nv, _, t in n['faltan'][:2])
            razones.append('calidad: este juego está en el nivel %d y el motor exige al menos el %d (uno más que el mejor juego ya publicado). Falta → %s' % (n['nivel'], pide, falta or 'subir de nivel'))
    else:
        antes = sincronizar(raiz, entradas, escribir=False)['niveles'].get(spec['id'], 0)
        if n['nivel'] < antes:
            razones.append('calidad: este juego bajó del nivel %d al %d; una actualización no puede quitarle lo que ya tenía' % (antes, n['nivel']))
    return razones


# ---------------------------------------------------------------------------------------------------------------------
# Cola de mejoras: se calcula, no se escribe a mano
# ---------------------------------------------------------------------------------------------------------------------

def cola(raiz, entradas, juegos):
    """Lista ordenada de lo que sigue para el motor: [{'prioridad', 'tipo', 'titulo', 'por_que'}]. `juegos` = lista de fichas (dict)."""
    raiz = pathlib.Path(raiz)
    items = []
    vigente, motivo = informe_vigente(raiz)
    if not vigente:
        items.append({'prioridad': 0, 'tipo': 'pruebas', 'titulo': 'Correr las pruebas del motor', 'por_que': motivo})
    man = manifiesto(raiz)
    esc = escalera(raiz)
    t = techo(raiz)
    lanz = lanzados(entradas)
    mejor = piso_sin(raiz, entradas)
    # 1) juegos que aún no salen y están por debajo de lo que se les exige
    for spec in juegos:
        if spec['id'] in lanz:
            continue
        pide = exigido(raiz, spec, entradas)
        n = nivel_de(raiz, spec)
        if n['nivel'] < pide:
            falta = n['faltan'][0] if n['faltan'] else None
            items.append({'prioridad': 1, 'tipo': 'juego', 'titulo': 'Subir «%s» al nivel %d (hoy %d)' % (spec['id'], pide, n['nivel']),
                          'por_que': 'No puede lanzarse debajo de eso.' + ((' Primero falta: %s' % falta[2]) if falta else '')})
    # 2) el techo: un nivel de la escalera cuyo módulo todavía no existe o no está probado
    for n in esc['niveles']:
        if n['n'] <= t:
            continue
        for r in n['requiere']:
            mod = esc['requisitos'][r].get('modulo')
            if mod and not modulo_disponible(raiz, mod):
                if mod in man:
                    items.append({'prioridad': 2, 'tipo': 'modulo', 'titulo': 'Probar el módulo «%s»' % mod, 'por_que': 'Existe, pero sin pruebas vigentes no cuenta para el nivel %d.' % n['n']})
                else:
                    idea = next((i for i in _json(raiz / 'motor' / 'ideas.json', {}).get('ideas', []) if i.get('modulo') == mod), None)
                    items.append({'prioridad': 2, 'tipo': 'modulo', 'titulo': 'Construir el módulo «%s» (nivel %d)' % (mod, n['n']),
                                  'por_que': (idea or {}).get('por_que') or esc['requisitos'][r]['texto']})
        break
    # 3) pedidos de los propios juegos
    aporta = ' '.join(' '.join(m.get('aporta', [])) for m in man.values()).lower()
    for spec in juegos:
        for need in spec.get('necesidades_motor', []) or []:
            if str(need).lower() not in aporta:
                items.append({'prioridad': 3, 'tipo': 'pedido', 'titulo': 'Pedido de «%s»: %s' % (spec['id'], need), 'por_que': 'Ningún módulo lo ofrece todavía.'})
    # 4) el techo alcanzado: el siguiente juego ya no tiene a dónde subir → abrir un nivel nuevo con la primera idea sin construir
    if t >= len(esc['niveles']) and mejor >= t:
        idea = next((i for i in _json(raiz / 'motor' / 'ideas.json', {}).get('ideas', []) if i.get('modulo') not in man), None)
        if idea:
            items.append({'prioridad': 2, 'tipo': 'nivel', 'titulo': 'Abrir el nivel %d: construir «%s»' % (len(esc['niveles']) + 1, idea['modulo']),
                          'por_que': 'El mejor juego publicado ya está en el techo (%d); el siguiente no tendría cómo mejorar. %s' % (t, idea['por_que'])})
    # 5) juegos ya publicados por debajo del techo: una actualización de calidad es también una novedad que anunciar
    for spec in juegos:
        if spec['id'] in lanz:
            n = nivel_de(raiz, spec)
            if n['nivel'] < t:
                items.append({'prioridad': 4, 'tipo': 'actualizacion', 'titulo': 'Actualizar «%s» del nivel %d al %d' % (spec['id'], n['nivel'], t),
                              'por_que': 'Una versión nueva con lo que le falta (%s) mejora el juego y da una novedad que anunciar.' % ', '.join(f[1] for f in _faltan_hasta(raiz, spec, t))})
    return sorted(items, key=lambda i: (i['prioridad'], i['titulo']))


def cola_con_autonomia(raiz, entradas, juegos):
    """La cola del motor más lo que baja las intervenciones de Max (objetivo secundario: herramientas/autonomia.py). Va después de lo de calidad
    y de los pedidos, y solo trae lo que se puede construir sin que Max decida: lo que depende de una regla suya no entra."""
    items = cola(raiz, entradas, juegos)
    try:
        import autonomia
    except ImportError:
        autonomia = None                            # una copia mínima del proyecto, sin la herramienta: la cola es la de siempre
    if autonomia is not None:
        try:
            items += autonomia.cola_items(raiz)
        except autonomia.ErrorAutonomia:
            pass                                    # sin inventario no hay nada que sumar (el ciclo sí avisa de un inventario dañado)
    return sorted(items, key=lambda i: (i['prioridad'], i['titulo']))


def informe_de_estado(raiz, entradas, juegos):
    """Líneas de texto para PENDIENTE.md y para `fabrica.py motor`."""
    raiz = pathlib.Path(raiz)
    esc = escalera(raiz)
    vigente, motivo = informe_vigente(raiz)
    L = ['Techo del motor hoy: nivel %d de %d. Mejor juego publicado: nivel %d. Pruebas del motor: %s.' % (techo(raiz), len(esc['niveles']), piso_sin(raiz, entradas),
                                                                                                  'al día' if vigente else 'VENCIDAS (%s)' % motivo), '']
    L.append('Niveles: ' + ' · '.join('%d %s' % (n['n'], n['nombre']) for n in esc['niveles']))
    L.append('')
    for spec in juegos:
        n = nivel_de(raiz, spec)
        L.append('- %s: nivel %d (%s)%s' % (spec['id'], n['nivel'], n['nombre'], (' — falta: ' + n['faltan'][0][2]) if n['faltan'] else ''))
    L += ['', 'Lo que sigue para el motor:']
    items = cola_con_autonomia(raiz, entradas, juegos)
    L += ['%d. %s — %s' % (i + 1, it['titulo'], it['por_que']) for i, it in enumerate(items[:5])] or ['(nada pendiente)']
    return L
