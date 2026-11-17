"""Pruebas del comprobador de novedad (herramientas/novedad.py): variantes, parecidos, vocabulario y plantilla.
Uso: python3 -m unittest discover -s pruebas   (desde la carpeta de la fábrica)"""
import copy
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'herramientas'))
import novedad  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='ggx-novedad-'))
        shutil.copytree(RAIZ / 'catalogo', self.tmp / 'catalogo')
        shutil.copytree(RAIZ / 'juegos', self.tmp / 'juegos')
        for p in (RAIZ / 'plantillas').glob('*/plantilla.json'):
            (self.tmp / 'plantillas' / p.parent.name).mkdir(parents=True, exist_ok=True)
            shutil.copy(p, self.tmp / 'plantillas' / p.parent.name / 'plantilla.json')
        self.base = json.loads((RAIZ / 'juegos' / 'guerreros-gelatina' / 'juego.json').read_text(encoding='utf-8'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def nuevo(self, juego_id, cambios=None, orden=3):
        s = copy.deepcopy(self.base)
        s['id'] = juego_id
        s['lanzamiento'] = {'orden': orden}
        s['ficha'] = {i: {'titulo': juego_id, 'corta': 'otra cosa %s' % juego_id, 'larga': 'texto distinto sobre %s y nada más que eso' % juego_id, 'controles': 'x'} for i in s['idiomas']}
        for k, v in (cambios or {}).items():
            if isinstance(v, dict) and isinstance(s.get(k), dict):
                s[k].update(v)
            else:
                s[k] = v
        d = self.tmp / 'juegos' / juego_id
        d.mkdir(parents=True, exist_ok=True)
        (d / 'juego.json').write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
        return s


class PruebasReales(Base):
    def test_los_juegos_actuales_son_distintos(self):
        for i in ('guerreros-gelatina', 'torre-gelatina'):
            r = novedad.evaluar(RAIZ, i)
            self.assertEqual(r['errores'], [], r['errores'])
            self.assertEqual(r['veredicto'], 'distinto')

    def test_torre_no_va_a_portales_por_riesgo_alto(self):
        r = novedad.evaluar(RAIZ, 'torre-gelatina')
        self.assertTrue(r['apto']['sitio'] and r['apto']['redes'])
        self.assertFalse(r['apto']['portales'])

    def test_las_ideas_del_cuaderno_son_validas_y_distintas(self):
        for idea, r in novedad.evaluar_ideas(RAIZ):
            self.assertEqual(r['errores'], [], idea['id'])
            self.assertEqual(r['veredicto'], 'distinto', idea['id'])


class Variantes(Base):
    def test_mismo_nucleo_con_otro_tema_es_variante_y_no_se_publica_aparte(self):
        self.nuevo('guerreros-dinosaurio', {'mecanica': {'ambientacion': 'dinosaurios', 'arte': 'pixel-art'}})
        r = novedad.evaluar(self.tmp, 'guerreros-dinosaurio')
        self.assertEqual(r['veredicto'], 'variante')
        self.assertEqual(r['padre'], 'guerreros-gelatina')
        self.assertEqual(r['apto'], {'sitio': False, 'redes': False, 'portales': False})
        self.assertIn('paquete o modo', ' '.join(r['motivos']))

    def test_el_original_no_se_bloquea_porque_exista_su_variante(self):
        self.nuevo('guerreros-dinosaurio', {'mecanica': {'ambientacion': 'dinosaurios'}})
        r = novedad.evaluar(self.tmp, 'guerreros-gelatina')
        self.assertEqual(r['veredicto'], 'distinto')
        self.assertTrue(r['apto']['sitio'])

    def test_cambiar_solo_progresion_o_entrada_sigue_siendo_variante(self):
        self.nuevo('guerreros-v2', {'mecanica': {'entrada': ['teclado'], 'progresion': 'puntaje-infinito'}})
        self.assertEqual(novedad.evaluar(self.tmp, 'guerreros-v2')['veredicto'], 'variante')

    def test_mismo_genero_con_otro_verbo_y_objetivo_es_parecido_y_no_va_a_portales(self):
        self.nuevo('guerreros-control', {'mecanica': {'verbo': 'controlar-personaje', 'objetivo': 'sobrevivir'}, 'plantilla': 'gelatina'},)
        s = json.loads((self.tmp / 'juegos' / 'guerreros-control' / 'juego.json').read_text(encoding='utf-8'))
        s['mecanica']['justificacion'] = 'cambia el verbo y el objetivo de la plantilla'
        (self.tmp / 'juegos' / 'guerreros-control' / 'juego.json').write_text(json.dumps(s), encoding='utf-8')
        r = novedad.evaluar(self.tmp, 'guerreros-control')
        self.assertEqual(r['errores'], [])
        self.assertEqual(r['veredicto'], 'parecido')
        self.assertTrue(r['apto']['sitio'])
        self.assertFalse(r['apto']['portales'])

    def test_una_idea_con_el_nucleo_de_un_juego_existente_es_variante(self):
        r = novedad.evaluar(self.tmp, spec={'id': 'idea-x', 'mecanica': {'genero': 'simulador-batalla', 'verbo': 'colocar', 'objetivo': 'eliminar-rival'}})
        self.assertEqual(r['veredicto'], 'variante')


class Validacion(Base):
    def test_un_valor_fuera_del_vocabulario_es_error(self):
        self.nuevo('juego-raro', {'mecanica': {'genero': 'simulador-de-batallas'}})
        r = novedad.evaluar(self.tmp, 'juego-raro')
        self.assertTrue(any('no está en catalogo/vocabulario.json' in e for e in r['errores']), r['errores'])
        self.assertEqual(r['apto'], {'sitio': False, 'redes': False, 'portales': False})

    def test_falta_la_mecanica(self):
        s = self.nuevo('sin-mecanica')
        s.pop('mecanica')
        (self.tmp / 'juegos' / 'sin-mecanica' / 'juego.json').write_text(json.dumps(s), encoding='utf-8')
        self.assertTrue(any('falta la sección «mecanica»' in e for e in novedad.evaluar(self.tmp, 'sin-mecanica')['errores']))

    def test_declarar_otro_nucleo_que_la_plantilla_exige_justificacion(self):
        self.nuevo('mismo-codigo-otro-juego', {'mecanica': {'genero': 'apilador', 'verbo': 'soltar', 'objetivo': 'altura-maxima'}})
        r = novedad.evaluar(self.tmp, 'mismo-codigo-otro-juego')
        self.assertTrue(any('mecanica.justificacion' in e for e in r['errores']), r['errores'])

    def test_textos_casi_identicos_avisan(self):
        s = self.nuevo('texto-copiado', {'mecanica': {'genero': 'apilador', 'verbo': 'soltar', 'objetivo': 'altura-maxima', 'justificacion': 'prueba'}})
        s['ficha'] = copy.deepcopy(self.base['ficha'])
        (self.tmp / 'juegos' / 'texto-copiado' / 'juego.json').write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
        r = novedad.evaluar(self.tmp, 'texto-copiado')
        self.assertTrue(any('se parecen mucho' in a for a in r['avisos']), r['avisos'])


if __name__ == '__main__':
    unittest.main()
