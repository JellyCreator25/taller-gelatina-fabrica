"""Textos de publicación: composición por idioma, conteo de grafemas y enlaces con posiciones en bytes (Bluesky)."""
import re
import sys
import unicodedata

ENLACE = re.compile(r'https://[^\s]+')


def grafemas(s):
    """Aproximación prudente al conteo de grafemas: no cuenta marcas combinantes, selectores de variación ni uniones de emoji,
    y cuenta cada par de indicadores regionales (banderas) como uno."""
    n, i, previo_union, regional = 0, 0, False, False
    for c in s:
        cp = ord(c)
        if c == '‍':
            previo_union = True
            continue
        if unicodedata.category(c).startswith('M') or 0xFE00 <= cp <= 0xFE0F or 0x1F3FB <= cp <= 0x1F3FF:
            continue
        if previo_union:
            previo_union = False
            continue
        if 0x1F1E6 <= cp <= 0x1F1FF:
            regional = not regional
            if not regional:
                continue
        n += 1
    return n


def bytes_utf8(s):
    return len(s.encode('utf-8'))


def facetas_enlaces(texto):
    """Facetas de Bluesky para cada enlace: las posiciones son bytes UTF-8, no letras."""
    caras = []
    for m in ENLACE.finditer(texto):
        url = m.group(0).rstrip('.,;:!?)»”')
        ini = len(texto[:m.start()].encode('utf-8'))
        caras.append({'index': {'byteStart': ini, 'byteEnd': ini + len(url.encode('utf-8'))},
                      'features': [{'$type': 'app.bsky.richtext.facet#link', 'uri': url}]})
    return caras


def componer_post(spec, idioma, url, linea_ia):
    """Texto de `difusion.<idioma>.post_corto` con el enlace real y la línea de IA. Devuelve (texto, problemas)."""
    base = ((spec.get('difusion') or {}).get(idioma) or {}).get('post_corto', '')
    if not base:
        return '', ['falta difusion.%s.post_corto en juego.json' % idioma]
    texto = base.replace('{enlace}', url).replace('{ia}', linea_ia).strip()
    texto = re.sub(r'[ \t]+\n', '\n', texto)
    problemas = []
    if re.search(r'\{[a-z_]+\}|\[ENLACE', texto):
        problemas.append('el texto tiene marcas sin resolver')
    if 'PENDIENTE' in texto:
        problemas.append('el texto dice PENDIENTE')
    if linea_ia and linea_ia not in texto:
        problemas.append('el texto no lleva la línea de IA')
    if url not in texto:
        problemas.append('el texto no lleva el enlace al juego')
    return texto, problemas
