"""La insignia del Taller: la Gelatina, dibujada una sola vez.

Esta es la fuente única del emblema. Lo usan el módulo `marca` del motor (motor/modulos/marca.js lleva el mismo dibujo), el ícono del sitio
y los archivos de marca/ (que se regeneran con `python3 herramientas/marca.py`). Si el dibujo cambia aquí, la prueba de coherencia obliga a
cambiarlo también en el módulo; así la gelatina se ve igual en todas partes.

Lo que hace reconocible a la Gelatina en cualquier color: la silueta de domo con la base ancha, el brillo grande arriba a la izquierda con su
puntito, y los dos ojos grandes con un destello clavado. El color cambia (verde de la casa, rosa, amarilla); esos tres rasgos, no.
Dibujada con trazos propios: no copia ningún personaje."""
import pathlib
import sys

COLORES = {                      # (claro, oscuro, cachete)
    'verde': ('#6fe0a6', '#15804f', '#ffc2d8'),
    'rosa': ('#ff9cc4', '#c2337a', '#ff6f9f'),
    'amarilla': ('#ffd36b', '#e39a00', '#ff9f80'),
}
VISTA = '-118 -98 236 208'      # el domo sin sombra: cabe justo, y el emblema se ve igual en 16 px que en 800
TINTA = '#14251b'


def _cuerpo(relleno, tinta=TINTA):
    return ("<path d='M-102 62 C-114 -22 -72 -92 0 -92 C72 -92 114 -22 102 62 C99 88 70 102 0 102 C-70 102 -99 88 -102 62 Z' fill='%s'/>" % relleno)


def emblema(color='verde', id_='e'):
    """SVG autónomo (con xmlns) del emblema a color. `id_` evita que dos emblemas en la misma página compartan el degradado. Sin comillas dobles."""
    claro, oscuro, cachete = COLORES[color]
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='%s' role='img' aria-label='Taller Gelatina'>"
        "<defs><linearGradient id='g%s' x1='0' y1='-1' x2='0' y2='1'><stop offset='0' stop-color='%s'/><stop offset='1' stop-color='%s'/></linearGradient></defs>"
        "%s"
        "<path d='M-102 62 C-99 88 -70 102 0 102 C70 102 99 88 102 62 C80 80 -80 80 -102 62 Z' fill='%s' opacity='.10'/>"
        "<ellipse cx='-48' cy='-50' rx='30' ry='14' transform='rotate(-35 -48 -50)' fill='#fff' opacity='.55'/>"
        "<circle cx='-80' cy='-6' r='5' fill='#fff' opacity='.5'/>"
        "<ellipse cx='-33' cy='6' rx='16' ry='19' fill='#fff'/><ellipse cx='33' cy='6' rx='16' ry='19' fill='#fff'/>"
        "<circle cx='-30' cy='10' r='9' fill='%s'/><circle cx='36' cy='10' r='9' fill='%s'/>"
        "<circle cx='-27' cy='6' r='3' fill='#fff'/><circle cx='39' cy='6' r='3' fill='#fff'/>"
        "<ellipse cx='-58' cy='38' rx='11' ry='7' fill='%s' opacity='.8'/><ellipse cx='58' cy='38' rx='11' ry='7' fill='%s' opacity='.8'/>"
        "<path d='M-15 42 Q0 56 15 42' fill='none' stroke='%s' stroke-width='5' stroke-linecap='round'/>"
        "</svg>" % (VISTA, id_, claro, oscuro, _cuerpo('url(#g%s)' % id_), TINTA, TINTA, TINTA, cachete, cachete, TINTA))


def emblema_mono(id_='m'):
    """Una sola tinta (la del texto que lo rodea, currentColor): la silueta con ojos, brillo y sonrisa recortados. Para sellos, grabados y fondos de un color."""
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='%s' role='img' aria-label='Taller Gelatina'>"
        "<defs><mask id='k%s'><rect x='-118' y='-98' width='236' height='208' fill='#fff'/>"
        "<ellipse cx='-33' cy='6' rx='16' ry='19' fill='#000'/><ellipse cx='33' cy='6' rx='16' ry='19' fill='#000'/>"
        "<ellipse cx='-48' cy='-50' rx='30' ry='14' transform='rotate(-35 -48 -50)' fill='#000'/>"
        "<path d='M-15 42 Q0 56 15 42' fill='none' stroke='#000' stroke-width='6' stroke-linecap='round'/></mask></defs>"
        "<g mask='url(#k%s)'>%s</g></svg>" % (VISTA, id_, id_, _cuerpo('currentColor')))


def plantilla_para_modulo():
    """El emblema verde con {id} en lugar del identificador: el texto que lleva motor/modulos/marca.js."""
    return emblema('verde', '{id}')


def escribir(raiz):
    """Regenera los archivos de marca/ a partir del dibujo. Devuelve las rutas."""
    destino = pathlib.Path(raiz) / 'marca'
    destino.mkdir(exist_ok=True)
    archivos = {'emblema.svg': emblema('verde'), 'emblema-rosa.svg': emblema('rosa'), 'emblema-amarilla.svg': emblema('amarilla'), 'emblema-mono.svg': emblema_mono()}
    for nombre, svg in archivos.items():
        (destino / nombre).write_text(svg + '\n', encoding='utf-8')
    return sorted(destino / n for n in archivos)


if __name__ == '__main__':
    for r in escribir(pathlib.Path(__file__).resolve().parent.parent):
        print('[marca] escrito', r)
    sys.exit(0)
