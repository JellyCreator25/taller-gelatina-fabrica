"""Imagen para redes: de la portada PNG a un JPEG liviano. Se hace al publicar, no al planear: la huella usa el PNG original, así no depende de la versión de Pillow."""
import io

from ..nucleo import ErrorPublicacion


def preparar_imagen(ruta, max_bytes=900000, ancho_max=1200):
    try:
        from PIL import Image
    except ImportError:
        raise ErrorPublicacion('falta Pillow para preparar la imagen (pip install pillow)')
    im = Image.open(ruta).convert('RGB')
    if im.width > ancho_max:
        im = im.resize((ancho_max, round(im.height * ancho_max / im.width)))
    for calidad in (88, 80, 72, 64, 56, 48):
        b = io.BytesIO()
        im.save(b, 'JPEG', quality=calidad, optimize=True)
        if b.tell() <= max_bytes:
            return b.getvalue(), 'image/jpeg'
    raise ErrorPublicacion('la imagen no cabe en %d bytes ni con la calidad más baja' % max_bytes)
