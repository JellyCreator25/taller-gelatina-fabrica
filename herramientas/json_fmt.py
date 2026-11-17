"""Escribe JSON legible y estable (sangría de 2, listas y objetos cortos en una sola línea, acentos y chino sin escapar).
Las fichas de los juegos se editan a mano y con herramientas; este formato evita que un cambio automático reacomode todo el archivo."""
import json


def _plano(o):
    return not isinstance(o, (dict, list))


def dump(o, nivel=0, ancho=100):
    pad = '  ' * nivel
    if isinstance(o, dict):
        if not o:
            return '{}'
        if all(_plano(v) for v in o.values()):
            una = '{ ' + ', '.join('%s: %s' % (json.dumps(k, ensure_ascii=False), json.dumps(v, ensure_ascii=False)) for k, v in o.items()) + ' }'
            if len(una) + len(pad) <= ancho:
                return una
        filas = ['%s  %s: %s' % (pad, json.dumps(k, ensure_ascii=False), dump(v, nivel + 1, ancho)) for k, v in o.items()]
        return '{\n' + ',\n'.join(filas) + '\n' + pad + '}'
    if isinstance(o, list):
        if not o:
            return '[]'
        if all(_plano(v) for v in o):
            una = '[' + ', '.join(json.dumps(v, ensure_ascii=False) for v in o) + ']'
            if len(una) + len(pad) <= ancho:
                return una
        filas = ['%s  %s' % (pad, dump(v, nivel + 1, ancho)) for v in o]
        return '[\n' + ',\n'.join(filas) + '\n' + pad + ']'
    return json.dumps(o, ensure_ascii=False)


def guardar(ruta, obj):
    ruta.write_text(dump(obj) + '\n', encoding='utf-8')
