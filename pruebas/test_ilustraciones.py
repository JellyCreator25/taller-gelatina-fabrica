"""Pruebas de las ilustraciones de caricatura (herramientas/ilustraciones.js y su carpeta). No abren navegador: revisan las escenas como datos,
las imágenes ya dibujadas y su enlace con el calendario.
Lo que se comprueba (cada prueba nombra la regla que protege):
  · cada escena arma sus capas, usa personajes que existen, no escribe texto (solo cifras) y trae su alt en español e inglés
  · cada escena tiene su imagen dibujada: PNG de 1200×675 y menos de 900 KB (Bluesky admite 1 MB)
  · toda publicación que usa una ilustración lleva el alt de esa escena en el idioma de la publicación
  · lo que aún no se publica ya no usa capturas del juego (el arte nuevo es una decisión de Max del 23 de noviembre de 2026)
  · las publicaciones ya hechas conservan su imagen: el libro y las huellas aprobadas no se tocan
Correr: python3 -I -m unittest discover -s pruebas   (desde la carpeta de la fábrica)"""
import json
import pathlib
import struct
import subprocess
import unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
IMG = RAIZ / 'contenido' / 'imagenes'
PUBLICADAS_ANTES_DEL_ARTE_NUEVO = {'gta-vispera', 'gta-dia', 'antes-despues', 'sabado-1', 'merlin', 'premios', 'medusa-en'}


def node(*args, entrada=None):
    return subprocess.run(['node', *args], cwd=RAIZ, capture_output=True, text=True, input=entrada, timeout=120)


def escenas():
    r = node('-e', "const E=require('./herramientas/ilustraciones/escenas.js');console.log(JSON.stringify(Object.fromEntries(Object.entries(E).map(([k,v])=>[k,v.alt]))))")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def tamano_png(ruta):
    d = ruta.read_bytes()[:32]
    assert d[:8] == b'\x89PNG\r\n\x1a\n', ruta.name
    return struct.unpack('>II', d[16:24])


class Escenas(unittest.TestCase):
    def test_verificacion_sin_navegador_pasa(self):
        r = node('herramientas/ilustraciones.js', '--verificar')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('escenas', r.stdout)

    def test_la_verificacion_atrapa_los_errores_que_importan(self):
        codigo = """
const { verificar } = require('./herramientas/ilustraciones.js');
const malas = {
  'con-texto': { alt: { es: 'Ilustración de caricatura: x', en: 'Cartoon illustration: x' }, hacer: (S, L) => ['<text x="1" y="1">Hola</text>'] },
  'personaje-raro': { alt: { es: 'Ilustración de caricatura: x', en: 'Cartoon illustration: x' }, hacer: (S, L) => [S('dragon', 0, 1, 1, 50)] },
  'sin-ingles': { alt: { es: 'Ilustración de caricatura: x', en: '' }, hacer: (S, L) => ['<g/>'] },
  'nan': { alt: { es: 'Ilustración de caricatura: x', en: 'Cartoon illustration: x' }, hacer: (S, L) => ['<g x="NaN"/>'] },
  'cifras-bien': { alt: { es: 'Ilustración de caricatura: x', en: 'Cartoon illustration: x' }, hacer: (S, L) => ['<text>-100%</text>', S('zeus', 1, 10, 10, 50)] },
};
console.log(JSON.stringify(verificar(malas)));
"""
        r = node('-e', codigo)
        self.assertEqual(r.returncode, 0, r.stderr)
        problemas = json.loads(r.stdout)
        txt = '\n'.join(problemas)
        self.assertIn('con-texto: escribe texto', txt)
        self.assertIn('personaje desconocido «dragon»', txt)
        self.assertIn('sin-ingles: falta el alt en «en»', txt)
        self.assertIn('nan: hay NaN', txt)
        self.assertNotIn('cifras-bien', txt)

    def test_cada_escena_tiene_su_imagen_dibujada(self):
        for id_ in escenas():
            ruta = IMG / ('ilustracion-%s.png' % id_)
            self.assertTrue(ruta.exists(), 'falta dibujar «%s»: node herramientas/ilustraciones.js %s' % (id_, id_))
            self.assertEqual(tamano_png(ruta), (1200, 675), id_)
            self.assertLess(ruta.stat().st_size, 900_000, id_ + ' pesa demasiado para Bluesky')

    def test_no_sobran_imagenes_sin_escena(self):
        ids = set(escenas())
        sobran = sorted(p.name for p in IMG.glob('ilustracion-*.png') if p.stem[len('ilustracion-'):] not in ids)
        self.assertEqual(sobran, [], 'imágenes sin escena (bórralas o agrega su escena)')


class ConElCalendario(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pubs = json.loads((RAIZ / 'contenido' / 'calendario.json').read_text(encoding='utf-8'))['publicaciones']
        cls.alts = escenas()

    def test_las_publicaciones_con_ilustracion_llevan_el_alt_de_su_escena_en_su_idioma(self):
        n = 0
        for p in self.pubs:
            nombre = pathlib.Path(p['imagen']).name
            if not nombre.startswith('ilustracion-'):
                continue
            n += 1
            esc = nombre[len('ilustracion-'):-len('.png')]
            self.assertIn(esc, self.alts, p['id'])
            self.assertEqual(p['alt'], self.alts[esc][p['idioma']], p['id'])
        self.assertGreaterEqual(n, 30)

    def test_lo_que_aun_no_sale_usa_ilustraciones(self):
        for p in self.pubs:
            if p['id'] in PUBLICADAS_ANTES_DEL_ARTE_NUEVO:
                continue
            self.assertTrue(pathlib.Path(p['imagen']).name.startswith('ilustracion-'), '%s sigue con una captura: %s' % (p['id'], p['imagen']))

    def test_las_ya_publicadas_conservan_su_imagen(self):
        por_id = {p['id']: p for p in self.pubs}
        for i in PUBLICADAS_ANTES_DEL_ARTE_NUEVO:
            self.assertFalse(pathlib.Path(por_id[i]['imagen']).name.startswith('ilustracion-'), i)
            self.assertTrue((RAIZ / por_id[i]['imagen']).exists(), i)

    def test_las_versiones_es_y_en_de_una_imagen_no_llevan_texto_en_un_idioma(self):
        # una imagen compartida entre idiomas solo es válida si no escribe texto: lo garantiza --verificar; aquí se confirma que el alt de cada idioma no está en el otro
        for p in self.pubs:
            nombre = pathlib.Path(p['imagen']).name
            if nombre.startswith('ilustracion-'):
                esc = nombre[len('ilustracion-'):-len('.png')]
                otro = 'en' if p['idioma'] == 'es' else 'es'
                self.assertNotEqual(p['alt'], self.alts[esc][otro], p['id'])


if __name__ == '__main__':
    unittest.main()
