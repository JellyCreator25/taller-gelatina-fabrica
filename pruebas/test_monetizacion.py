"""Pruebas de la monetización del motor: política apagada por defecto, qué se le inyecta a un juego, qué falta por ruta, las cuentas y las versiones para portales.
Ninguna toca la red ni abre un navegador (las del módulo en un navegador son `python3 fabrica.py motor probar`).
Correr: python3 -I -m unittest discover -s pruebas   (desde la carpeta de la fábrica)"""
import copy
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / 'herramientas'))

import fabrica  # noqa: E402
import monetizar  # noqa: E402


def ficha(juego):
    return json.loads((RAIZ / 'juegos' / juego / 'juego.json').read_text(encoding='utf-8'))


class PoliticaApagada(unittest.TestCase):
    def test_la_politica_real_es_valida_y_todo_empieza_apagado(self):
        pol = monetizar.politica(RAIZ)
        self.assertEqual(monetizar.problemas_de_politica(pol), [])
        self.assertEqual({n: r['activa'] for n, r in pol['rutas'].items()}, {'portales': False, 'adsense-sitio': False, 'donaciones': False})

    def test_una_politica_rota_se_nota(self):
        pol = copy.deepcopy(monetizar.politica(RAIZ))
        pol['reglas_de_anuncios']['momentos_prohibidos'].append('fin_de_partida')
        pol['rutas']['portales']['activa'] = 'si'
        del pol['rutas']['donaciones']
        pol['supuestos_de_ingresos']['relleno'] = 1.5
        malos = ' | '.join(monetizar.problemas_de_politica(pol))
        for esperado in ('permitido y prohibido', 'activa: true o false', 'falta la ruta «donaciones»', 'relleno'):
            self.assertIn(esperado, malos)

    def test_la_regla_de_momentos_coincide_con_la_del_modulo(self):
        """El módulo lleva la lista de momentos permitidos en su código; la política la repite para que se lea sin abrir JavaScript. Deben decir lo mismo."""
        codigo = (RAIZ / 'motor' / 'modulos' / 'anuncios.js').read_text(encoding='utf-8')
        for m in monetizar.politica(RAIZ)['reglas_de_anuncios']['momentos_permitidos']:
            self.assertIn("'%s'" % m, codigo)
        for k, v in monetizar.politica(RAIZ)['reglas_de_anuncios'].items():
            if isinstance(v, int):
                self.assertIn('%s: %d' % (k, v), codigo, 'los valores de reglas_de_anuncios.%s no coinciden con los de respaldo del módulo' % k)


class LoQueSeLeInyectaAUnJuego(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='ggx-monetizar-'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / 'monetizacion').mkdir()
        (self.tmp / 'publicacion').mkdir()
        self.spec = {'motor': ['accesible', 'anuncios']}

    def escribir(self, activa, publicador, modo_prueba=True):
        pol = copy.deepcopy(monetizar.politica(RAIZ))
        pol['rutas']['adsense-sitio'].update({'activa': activa, 'modo_prueba': modo_prueba})
        (self.tmp / 'monetizacion' / 'politica.json').write_text(json.dumps(pol), encoding='utf-8')
        (self.tmp / 'publicacion' / 'sitio.json').write_text(json.dumps({'adsense_publisher': publicador}), encoding='utf-8')

    def test_apagado_no_se_inyecta_nada(self):
        self.escribir(False, 'pub-1234567890123456')
        self.assertIsNone(monetizar.configuracion_de(self.tmp, self.spec))

    def test_encendido_pero_sin_editor_de_adsense_tampoco(self):
        self.escribir(True, '')
        self.assertIsNone(monetizar.configuracion_de(self.tmp, self.spec))

    def test_un_juego_sin_el_modulo_nunca_recibe_anuncios(self):
        self.escribir(True, 'pub-1234567890123456')
        self.assertIsNone(monetizar.configuracion_de(self.tmp, {'motor': ['accesible']}))
        self.assertIsNone(monetizar.configuracion_de(self.tmp, {}))

    def test_encendido_con_editor_va_en_modo_de_prueba_hasta_que_el_dueno_diga(self):
        self.escribir(True, 'pub-1234567890123456')
        cfg = monetizar.configuracion_de(self.tmp, self.spec)
        self.assertEqual(cfg['proveedor'], 'adsense')
        self.assertEqual(cfg['publicador'], 'ca-pub-1234567890123456')
        self.assertTrue(cfg['prueba'])
        self.assertTrue(cfg['sdk_url'].startswith('https://pagead2.googlesyndication.com/'))
        self.assertEqual(set(cfg['reglas']), {'espera_inicial_s', 'min_entre_s', 'max_por_sesion', 'recompensa_min_entre_s'})
        self.escribir(True, 'pub-1234567890123456', modo_prueba=False)
        self.assertNotIn('prueba', monetizar.configuracion_de(self.tmp, self.spec))

    def test_una_variante_pedida_manda_sobre_la_politica(self):
        self.escribir(False, '')
        spec = dict(self.spec, _anuncios={'proveedor': 'crazygames'})
        self.assertEqual(monetizar.configuracion_de(self.tmp, spec), {'proveedor': 'crazygames'})


class LosJuegosRealesSalenComoSiempre(unittest.TestCase):
    def test_solo_compas_tiene_los_ganchos_y_los_publicados_no_cambian(self):
        self.assertEqual(monetizar.juegos_con_ganchos(RAIZ, fabrica), ['compas-gelatina'])
        for publicado in ('guerreros-gelatina', 'torre-gelatina'):
            self.assertNotIn('anuncios', ficha(publicado).get('motor', []), '%s ya está publicado: sumarle anuncios es una versión nueva y la aprueba el dueño' % publicado)

    def test_con_la_politica_apagada_el_juego_no_lleva_configuracion_de_anuncios(self):
        html = (RAIZ / 'salida' / 'compas-gelatina' / 'index.html').read_text(encoding='utf-8')
        # assertFalse(x in html) y no assertNotIn: si falla, no vuelca 200 KB de HTML en pantalla
        self.assertFalse('"anuncios":' in html, 'no debe llevar configuración de anuncios con la política apagada')
        self.assertFalse('googlesyndication' in html, 'no debe llevar la dirección del script de AdSense')
        self.assertFalse('sdk.crazygames.com' in html, 'no debe llevar la dirección del SDK de ningún portal')
        self.assertTrue('id="mod-anuncios"' in html, 'el módulo va dentro, apagado')


class QueFalta(unittest.TestCase):
    def setUp(self):
        self.est = monetizar.estado(RAIZ, fabrica)

    def test_hay_tres_rutas_y_ninguna_encendida(self):
        self.assertEqual(set(self.est), {'portales', 'adsense-sitio', 'donaciones'})
        self.assertFalse(any(e['activa'] for e in self.est.values()))

    def test_el_modulo_esta_listo_en_las_rutas_de_anuncios(self):
        for ruta in ('portales', 'adsense-sitio'):
            self.assertTrue(any('módulo «anuncios»' in x and 'pruebas del motor vigentes' in x for x in self.est[ruta]['listo']), self.est[ruta])

    def test_adsense_dice_que_falta_dominio_cuenta_consentimiento_y_analitica(self):
        faltan = ' | '.join(self.est['adsense-sitio']['falta_dueno'])
        for esperado in ('dominio propio', 'cuenta de AdSense', 'consentimiento', 'analítica'):
            self.assertIn(esperado, faltan)

    def test_donaciones_pide_solo_el_enlace(self):
        self.assertEqual(len(self.est['donaciones']['falta_dueno']), 1)
        self.assertIn('enlace', self.est['donaciones']['falta_dueno'][0])

    def test_el_informe_se_arma_y_no_afirma_que_se_cobre(self):
        texto = '\n'.join(monetizar.informe(RAIZ, fabrica))
        self.assertIn('Hoy no se muestra ningún anuncio ni se cobra nada', texto)
        self.assertIn('| Sesiones por día |', texto)


class Cuentas(unittest.TestCase):
    def test_la_formula(self):
        filas = monetizar.escenarios(RAIZ, [1000])
        f2 = next(f for f in filas if f['ecpm'] == 2)
        self.assertEqual(f2['dia_usd'], 2.8)           # 1000 sesiones × 2 anuncios × 0,7 de relleno × US$2 / 1000
        self.assertEqual(f2['mes_usd'], 84.0)
        self.assertEqual(f2['dias_a_pago_minimo'], 18)  # 50 / 2,8
        self.assertEqual(next(f for f in filas if f['ecpm'] == 5)['mes_usd'], 210.0)

    def test_mas_sesiones_nunca_da_menos(self):
        filas = [f for f in monetizar.escenarios(RAIZ) if f['ecpm'] == 2]
        self.assertEqual([f['mes_usd'] for f in filas], sorted(f['mes_usd'] for f in filas))


class VersionesParaPortales(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(RAIZ / 'dist' / 'portales' / 'compas-gelatina', ignore_errors=True)

    def test_la_version_de_crazygames_lleva_su_sdk_y_ninguna_otra_salida(self):
        [(prov, carpeta, problemas)] = monetizar.variantes(RAIZ, fabrica, 'compas-gelatina')
        self.assertEqual((prov, problemas), ('crazygames', []))
        html = (carpeta / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<script src="https://sdk.crazygames.com/crazygames-sdk-v3.js"></script>', html)
        self.assertIn('"anuncios":{"proveedor":"crazygames"}', html)
        self.assertNotIn('googlesyndication', html)
        self.assertTrue((carpeta / 'compas-gelatina-web.zip').exists())

    def test_la_version_para_portal_no_lleva_enlace_de_apoyo(self):
        spec = fabrica.cargar('compas-gelatina')
        spec['apoyo_url'] = 'https://ejemplo.invalid/apoyo'     # aunque el juego tuviera uno
        v = copy.deepcopy(spec)
        v['apoyo_url'] = ''
        self.assertEqual(v['apoyo_url'], '')

    def test_sin_ganchos_no_hay_version(self):
        with self.assertRaises(monetizar.ErrorMonetizacion):
            monetizar.variantes(RAIZ, fabrica, 'guerreros-gelatina')

    def test_poki_no_se_arma_hasta_tener_su_documentacion(self):
        with self.assertRaises(monetizar.ErrorMonetizacion):
            monetizar.variantes(RAIZ, fabrica, 'compas-gelatina', ['poki'])

    def test_la_revision_atrapa_anuncios_ajenos_y_salidas(self):
        sdk = monetizar.SDK_PORTAL['crazygames']
        self.assertEqual(monetizar.revisar_variante('<head>' + sdk + '</head>', 'crazygames'), [])
        malos = ' | '.join(monetizar.revisar_variante('<head>' + sdk + '<script src="https://pagead2.googlesyndication.com/x.js"></script></head>', 'crazygames'))
        self.assertIn('AdSense', malos)
        self.assertIn('externas', malos)
        self.assertIn('falta el SDK', ' | '.join(monetizar.revisar_variante('<head></head>', 'crazygames')))


if __name__ == '__main__':
    unittest.main()
