"""Revisión del kit de un juego (salida/<id>/kit/): marcas sin resolver, tablas bien formadas, enlaces de fuente que existen en
difusion/canales.json, encabezados de publicaciones.md y medios citados que de verdad existen, y antigüedad de las reglas.
Devuelve (errores, avisos). Los errores impiden usar el kit; los avisos piden una comprobación humana."""
import datetime
import json
import pathlib
import re

DIAS_MAXIMOS = 30   # pasado este tiempo, las reglas de las plataformas se vuelven a leer antes de publicar


def revisar(raiz, juego_id, hoy=None):
    raiz = pathlib.Path(raiz)
    juego = raiz / 'salida' / juego_id
    kit = juego / 'kit'
    errores, avisos = [], []
    if not kit.exists():
        return ['no hay kit: corre «python3 fabrica.py kit %s»' % juego_id], avisos
    datos = json.loads((raiz / 'difusion' / 'canales.json').read_text(encoding='utf-8'))
    fuentes = {r['fuente'] for c in datos['canales'] for r in c.get('reglas', [])}
    fuentes |= {h['fuente'] for c in datos['canales'] for k in ('hechos', 'humano') for h in c.get('automatizacion', {}).get(k, [])}
    publicaciones = (kit / 'publicaciones.md').read_text(encoding='utf-8')

    hoy = hoy or datetime.date.today()
    try:
        edad = (hoy - datetime.date.fromisoformat(datos['verificado'])).days
        if edad > DIAS_MAXIMOS:
            avisos.append('las reglas de los canales se leyeron hace %d días (el %s): vuelve a leer las fuentes antes de publicar' % (edad, datos['verificado']))
    except (KeyError, ValueError):
        errores.append('canales.json no tiene una fecha «verificado» válida')

    for md in sorted(kit.glob('*.md')):
        texto = md.read_text(encoding='utf-8')
        for marca in sorted(set(re.findall(r'\{[a-z_]+\}', texto))):
            errores.append('%s: marca sin resolver %s' % (md.name, marca))
        if re.search(r'\bTODO\b|\bREVISAR\b|\bPENDIENTE\b|\bundefined\b|\bNone\b', texto):
            errores.append('%s: contiene TODO, REVISAR, PENDIENTE, undefined o None' % md.name)
        bloque = []
        for linea in texto.split('\n') + ['']:
            if linea.startswith('|'):
                bloque.append(linea)
                continue
            if bloque and len({l.count('|') for l in bloque}) != 1:
                errores.append('%s: una tabla tiene filas de distinto ancho' % md.name)
            bloque = []
        if md.name == 'difusion.md':
            for encabezado in re.findall(r'→ «(.+?)»\.', texto):
                if '### ' + encabezado not in publicaciones:
                    errores.append('difusion.md cita «%s», que no está en publicaciones.md' % encabezado)
            for url in re.findall(r'\]\((https://[^)]+)\)', texto):
                if url not in fuentes:
                    errores.append('difusion.md enlaza %s, que no está en canales.json' % url)
        for medio in sorted(set(re.findall(r'`medios/([^`]+)`', texto))):
            if not (juego / 'medios' / medio).exists():
                errores.append('%s cita medios/%s, que no existe' % (md.name, medio))
    return errores, avisos
