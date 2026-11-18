"""Pruebas del motor que crece solo: módulos opcionales, escalera de calidad, piso que solo sube, informe de pruebas atado al código y cola de mejoras.
Ninguna toca la red ni abre un navegador (las pruebas del motor en navegador son `python3 fabrica.py motor probar`; aquí se comprueba que su informe esté vigente).
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

import motor  # noqa: E402

LANZADO = [{'juego': 'guerreros-gelatina', 'lanzamiento': True, 'resultado': 'ok', 'tipo': 'desplegar'}]


def real(juego):
    return json.loads((RAIZ / 'juegos' / juego / 'juego.json').read_text(encoding='utf-8'))


def como_la_1_4_0(spec):
    """Guerreros Gelatina tal como salió el 20 de noviembre (1.4.0): sin motor y solo con el paquete de audio. La 1.5.0, preparada, lo declara entero;
    estas pruebas hablan de un juego publicado que está en el nivel 2, así que parten de esa forma."""
    if spec.get('id') == 'guerreros-gelatina':
        spec = dict(spec, version='1.4.0', paquetes=['audio'])
        spec.pop('motor', None)
    return spec


def ficha(juego='guerreros-gelatina'):
    return como_la_1_4_0(real(juego))


class Proyecto(unittest.TestCase):
    """Una copia de la fábrica que cada prueba puede romper sin tocar la real."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='ggx-motor-test-'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        for carpeta in ('motor', 'juegos', 'plantillas', 'herramientas', 'catalogo'):
            shutil.copytree(RAIZ / carpeta, self.tmp / carpeta, ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copy(RAIZ / 'fabrica.py', self.tmp / 'fabrica.py')
        ruta = self.tmp / 'juegos' / 'guerreros-gelatina' / 'juego.json'
        ruta.write_text(json.dumps(como_la_1_4_0(json.loads(ruta.read_text(encoding='utf-8'))), ensure_ascii=False, indent=1), encoding='utf-8')

    def usar(self, *modulos):
        """El código de la plantilla (en la copia) llama a los módulos: la escalera solo cuenta lo que se usa, no lo que se declara."""
        llamadas = {'accesible': 'GGX.a11y.reducedMotion();', 'efectos': 'GGX.fx.count();', 'musica': 'GGX.music.start("alegre");', 'marca': 'GGX.marca.sello();'}
        ruta = self.tmp / 'plantillas' / 'gelatina' / 'plantilla.html'
        ruta.write_text(ruta.read_text(encoding='utf-8') + '\n<script>' + ''.join(llamadas[m] for m in modulos) + '</script>\n', encoding='utf-8')

    def escribir(self, ruta, datos):
        (self.tmp / ruta).write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding='utf-8')

    def json(self, ruta):
        return json.loads((self.tmp / ruta).read_text(encoding='utf-8'))


class PruebasDelMotorReal(unittest.TestCase):
    """El motor que está en el repositorio."""

    def test_el_informe_de_pruebas_del_motor_esta_vigente_y_paso(self):
        vigente, motivo = motor.informe_vigente(RAIZ)
        self.assertTrue(vigente, motivo)                       # si cambias el motor o un módulo sin correr `fabrica.py motor probar`, esto falla a propósito

    def test_cada_modulo_del_manifiesto_tiene_archivo_pruebas_y_dependencias_validas(self):
        man = motor.manifiesto(RAIZ)
        self.assertTrue(man)
        inf = motor.informe(RAIZ)
        orden = list(man)
        for n, m in man.items():
            with self.subTest(n):
                self.assertTrue((RAIZ / 'motor' / 'modulos' / m['archivo']).exists())
                self.assertGreater(inf['modulos'][n]['pruebas'], 0)
                self.assertEqual(inf['modulos'][n]['fallas'], 0)
                self.assertEqual(inf['modulos'][n]['version'], m['version'])
                for d in m['pide']:
                    self.assertIn(d, man)
                    self.assertLess(orden.index(d), orden.index(n), 'una dependencia se carga antes que quien la pide')
        self.assertEqual(sorted(p.name for p in (RAIZ / 'motor' / 'modulos').glob('*.js')), sorted(m['archivo'] for m in man.values()), 'ningún módulo suelto fuera del manifiesto')

    def test_los_textos_chinos_de_los_modulos_caben_en_gb2312(self):
        import fabrica
        for n, _, texto in motor.modulos_de(RAIZ, {'motor': list(motor.manifiesto(RAIZ))}):
            with self.subTest(n):
                self.assertEqual(fabrica.chinos_fuera_de_gb2312(texto), set())

    def test_los_juegos_publicados_no_cambian_con_el_motor_nuevo(self):
        for i in ('guerreros-gelatina', 'torre-gelatina'):   # los ya publicados; un juego en construcción sí declara su motor
            with self.subTest(i):
                html = (RAIZ / 'salida' / i / 'index.html').read_text(encoding='utf-8')
                if i == 'guerreros-gelatina' and real(i)['version'] != '1.4.0':
                    # Guerreros 1.5.0: actualización aprobada por Max, se publica después de Compás con su propio plan
                    self.assertEqual(sorted(real(i)['motor']), ['accesible', 'efectos', 'marca', 'musica'])
                    self.assertIn('id="mod-marca"', html)
                else:
                    self.assertFalse(real(i).get('motor'), 'un juego ya publicado no cambia por que el motor crezca')
                    self.assertNotIn('id="mod-', html)

    def test_el_tercer_juego_nace_en_lo_alto_de_la_escalera(self):
        n = motor.nivel_de(RAIZ, ficha('compas-gelatina'))
        self.assertGreaterEqual(n['nivel'], 4, n)
        self.assertEqual({m[0] for m in motor.modulos_de(RAIZ, ficha('compas-gelatina'))}, {'accesible', 'efectos', 'musica', 'marca', 'anuncios'})

    def test_la_escalera_es_coherente(self):
        esc = motor.escalera(RAIZ)
        self.assertEqual([n['n'] for n in esc['niveles']], list(range(1, len(esc['niveles']) + 1)))
        usados = [r for n in esc['niveles'] for r in n['requiere']]
        self.assertEqual(sorted(usados), sorted(set(usados)), 'un requisito no se pide en dos niveles')
        self.assertEqual(set(usados), set(esc['requisitos']))
        for r, d in esc['requisitos'].items():
            self.assertTrue(d['texto'])
            self.assertTrue(d['modulo'] is None or isinstance(d['modulo'], str))
        for idea in json.loads((RAIZ / 'motor' / 'ideas.json').read_text(encoding='utf-8'))['ideas']:
            self.assertTrue(idea['por_que'] and idea['modulo'] and idea['titulo'])

    def test_los_juegos_ya_publicados_estan_en_el_nivel_2_y_son_herederos(self):
        for i in ('guerreros-gelatina', 'torre-gelatina'):
            self.assertEqual(motor.nivel_de(RAIZ, ficha(i))['nivel'], 2, i)
            self.assertEqual(motor.exigido(RAIZ, ficha(i), LANZADO), 0, i)

    def test_guerreros_1_5_0_llega_al_nivel_5_y_sigue_siendo_heredado(self):
        spec = real('guerreros-gelatina')
        self.assertEqual(spec['version'], '1.5.0')
        self.assertEqual(motor.nivel_de(RAIZ, spec)['nivel'], 5, 'la actualización de calidad debía llegar al techo de la escalera')
        self.assertEqual(motor.exigido(RAIZ, spec, LANZADO), 0, 'es un juego heredado: no tiene mínimo, pero tampoco puede bajar')

    def test_la_corrida_semanal_guarda_el_piso(self):
        yml = (RAIZ / '.github' / 'workflows' / 'ciclo.yml').read_text(encoding='utf-8')
        self.assertIn('motor/piso.json', yml)


class PruebasDeMarca(unittest.TestCase):
    """La insignia: un solo dibujo, usado igual en el módulo, los archivos de marca/ y el ícono del sitio."""

    def test_el_modulo_lleva_exactamente_el_dibujo_de_marca_py(self):
        import marca
        fuente = (RAIZ / 'motor' / 'modulos' / 'marca.js').read_text(encoding='utf-8')
        plantilla = marca.plantilla_para_modulo()
        self.assertNotIn('"', plantilla)
        self.assertIn('"%s"' % plantilla, fuente, 'si cambia el dibujo en herramientas/marca.py hay que cambiarlo igual en motor/modulos/marca.js')
        for color, (claro, oscuro, cachete) in marca.COLORES.items():
            if color != 'verde':
                self.assertIn("'%s', '%s', '%s'" % (claro, oscuro, cachete), fuente, 'el color %s del módulo coincide con marca.py' % color)

    def test_los_archivos_de_marca_estan_al_dia_y_son_svg_validos(self):
        import marca
        import xml.etree.ElementTree as ET
        esperado = {'emblema.svg': marca.emblema('verde'), 'emblema-rosa.svg': marca.emblema('rosa'), 'emblema-amarilla.svg': marca.emblema('amarilla'), 'emblema-mono.svg': marca.emblema_mono()}
        for nombre, svg in esperado.items():
            with self.subTest(nombre):
                texto = (RAIZ / 'marca' / nombre).read_text(encoding='utf-8')
                self.assertEqual(texto, svg + '\n', 'regenera con `python3 herramientas/marca.py`')
                raiz = ET.fromstring(texto)
                self.assertTrue(raiz.tag.endswith('svg'))
        self.assertIn('currentColor', esperado['emblema-mono.svg'])
        self.assertNotIn('#', esperado['emblema-mono.svg'].replace('url(#', '').replace("fill='#000'", '').replace("fill='#fff'", '').replace("stroke='#000'", ''), 'la versión de una tinta no lleva colores propios')

    def test_dos_emblemas_en_una_pagina_no_comparten_degradado(self):
        import marca
        self.assertNotEqual(marca.emblema('verde', 'a'), marca.emblema('verde', 'b'))
        self.assertIn("id='ga'", marca.emblema('verde', 'a'))

    def test_el_icono_del_sitio_es_la_gelatina(self):
        import sitio
        self.assertIn('Taller Gelatina', sitio.favicon())
        self.assertIn('linearGradient', sitio.favicon())

    def test_el_modulo_esta_en_el_manifiesto_y_la_escalera_lo_pide(self):
        man = motor.manifiesto(RAIZ)
        self.assertEqual(man['marca']['pide'], ['accesible'])
        self.assertEqual(list(man)[:4], ['accesible', 'efectos', 'musica', 'marca'])
        self.assertEqual(motor.escalera(RAIZ)['requisitos']['marca']['modulo'], 'marca')

    def test_la_guia_de_marca_dice_lo_que_esta_hecho_y_lo_que_espera_decision(self):
        guia = (RAIZ / 'marca' / 'guia.md').read_text(encoding='utf-8')
        for tema in ('## La idea', '## Los elementos', '## Cómo se usa', '## Dónde ya está y dónde falta', '## Decisiones'):
            self.assertIn(tema, guia)
        for pieza in ('GGX.marca.sello', 'GGX.marca.blup', 'GGX.marca.distintivo', 'marca/*.svg', 'difusion/voz.md'):
            self.assertIn(pieza, guia)
        for archivo in ('emblema.svg', 'emblema-rosa.svg', 'emblema-amarilla.svg', 'emblema-mono.svg'):
            self.assertTrue((RAIZ / 'marca' / archivo).exists())


class PruebasDeNivel(Proyecto):
    def spec(self, motores):
        s = ficha()
        s['motor'] = motores
        return s

    def test_declarar_un_modulo_sin_usarlo_no_sube_de_nivel(self):
        self.assertEqual(motor.nivel_de(self.tmp, self.spec(['accesible', 'efectos', 'musica']))['nivel'], 2)
        faltan = motor.nivel_de(self.tmp, self.spec(['accesible', 'efectos', 'musica']))['faltan']
        self.assertIn('llamado por el código del juego', faltan[0][2])
        self.usar('accesible')
        self.assertEqual(motor.nivel_de(self.tmp, self.spec(['accesible', 'efectos']))['nivel'], 2, 'usa uno de los dos que pide el nivel 3')
        self.usar('efectos')
        self.assertEqual(motor.nivel_de(self.tmp, self.spec(['accesible', 'efectos']))['nivel'], 3)
        self.assertEqual(motor.nivel_de(self.tmp, self.spec(['accesible']))['nivel'], 2, 'usarlo en el código no basta si el juego no lo declara en «motor»')

    def test_el_nivel_sube_con_los_modulos_que_el_juego_usa(self):
        self.usar('accesible', 'efectos', 'musica', 'marca')
        self.assertEqual(motor.nivel_de(self.tmp, self.spec([]))['nivel'], 2)
        self.assertEqual(motor.nivel_de(self.tmp, self.spec(['accesible']))['nivel'], 2)            # un nivel pide todos sus requisitos
        self.assertEqual(motor.nivel_de(self.tmp, self.spec(['accesible', 'efectos']))['nivel'], 3)
        self.assertEqual(motor.nivel_de(self.tmp, self.spec(['accesible', 'efectos', 'musica']))['nivel'], 4)
        self.assertEqual(motor.nivel_de(self.tmp, self.spec(['accesible', 'efectos', 'musica', 'marca']))['nivel'], 5)
        self.assertEqual(motor.techo(self.tmp), 5)

    def test_sin_sonido_propio_un_juego_se_queda_en_el_nivel_1_y_sin_los_tres_idiomas_en_el_0(self):
        s = ficha()
        s['paquetes'] = []                                       # la plantilla de gelatina saca su sonido del paquete «audio»
        self.assertEqual(motor.nivel_de(self.tmp, s)['nivel'], 1)
        self.usar('accesible', 'efectos', 'musica', 'marca')
        self.assertEqual(motor.nivel_de(self.tmp, dict(s, motor=['accesible', 'efectos']))['nivel'], 1, 'los niveles son una escalera: sin el 2 no se llega al 3')
        self.assertEqual(motor.nivel_de(self.tmp, dict(s, motor=['musica']))['nivel'], 2, 'la música cuenta como sonido')
        self.assertEqual(motor.nivel_de(self.tmp, ficha('torre-gelatina'))['nivel'], 2, 'la plantilla de la torre llama a GGX.sfx')
        self.assertEqual(motor.nivel_de(self.tmp, dict(s, idiomas=['es', 'en']))['nivel'], 0)

    def test_el_modulo_no_cuenta_si_el_codigo_cambio_y_no_se_volvio_a_probar(self):
        self.usar('accesible', 'efectos')
        antes = motor.techo(self.tmp)
        with open(self.tmp / 'motor' / 'modulos' / 'efectos.js', 'a', encoding='utf-8') as f:
            f.write('// un cambio cualquiera\n')
        vigente, motivo = motor.informe_vigente(self.tmp)
        self.assertFalse(vigente)
        self.assertIn('probar', motivo)
        self.assertEqual(motor.nivel_de(self.tmp, self.spec(['accesible', 'efectos']))['nivel'], 2)
        self.assertLess(motor.techo(self.tmp), antes)

    def test_un_informe_con_fallas_no_deja_pasar(self):
        inf = self.json('motor/informe.json')
        inf['ok'] = False
        inf['modulos']['musica']['fallas'] = 1
        self.escribir('motor/informe.json', inf)
        vigente, motivo = motor.informe_vigente(self.tmp)
        self.assertFalse(vigente)
        self.assertIn('musica', motivo)

    def test_modulos_de_valida_nombres_dependencias_y_repetidos(self):
        with self.assertRaisesRegex(motor.ErrorMotor, 'no existe'):
            motor.modulos_de(self.tmp, {'motor': ['no-existe']})
        with self.assertRaisesRegex(motor.ErrorMotor, 'pide «accesible»'):
            motor.modulos_de(self.tmp, {'motor': ['efectos']})
        with self.assertRaisesRegex(motor.ErrorMotor, 'sin repetidos'):
            motor.modulos_de(self.tmp, {'motor': ['accesible', 'accesible']})
        self.assertEqual([n for n, _, _ in motor.modulos_de(self.tmp, {'motor': ['efectos', 'musica', 'accesible']})], ['accesible', 'efectos', 'musica'],
                         'el orden de carga lo manda el manifiesto')
        self.assertEqual(motor.modulos_de(self.tmp, {}), [])


class PruebasDeConstruccion(Proyecto):
    def construir(self, motores, juego='guerreros-gelatina'):
        import fabrica
        spec = ficha(juego)
        if motores is not None:
            spec['motor'] = motores
        self.escribir('juegos/%s/juego.json' % juego, spec)
        anterior = (fabrica.RAIZ, fabrica.SALIDA)
        fabrica.RAIZ, fabrica.SALIDA = self.tmp, self.tmp / 'salida'
        self.addCleanup(lambda: setattr(fabrica, 'RAIZ', anterior[0]) or setattr(fabrica, 'SALIDA', anterior[1]))
        fabrica.construir(juego)
        return (self.tmp / 'salida' / juego / 'index.html').read_text(encoding='utf-8')

    def test_sin_motor_el_resultado_es_exactamente_el_publicado(self):
        # Torre Gelatina: publicada, sin motor y con una plantilla que no cambia. (La plantilla de Guerreros sí cambió en la 1.5.0, a propósito.)
        html = self.construir(None, 'torre-gelatina')
        publicado = (RAIZ / 'salida' / 'torre-gelatina' / 'index.html').read_text(encoding='utf-8')
        self.assertEqual(html, publicado)

    def test_guerreros_publicado_en_salida_es_lo_que_se_reconstruye(self):
        import fabrica
        spec = real('guerreros-gelatina')
        self.escribir('juegos/guerreros-gelatina/juego.json', spec)
        anterior = (fabrica.RAIZ, fabrica.SALIDA)
        fabrica.RAIZ, fabrica.SALIDA = self.tmp, self.tmp / 'salida'
        self.addCleanup(lambda: setattr(fabrica, 'RAIZ', anterior[0]) or setattr(fabrica, 'SALIDA', anterior[1]))
        fabrica.construir('guerreros-gelatina')
        self.assertEqual((self.tmp / 'salida' / 'guerreros-gelatina' / 'index.html').read_text(encoding='utf-8'),
                         (RAIZ / 'salida' / 'guerreros-gelatina' / 'index.html').read_text(encoding='utf-8'))

    def test_con_motor_los_modulos_van_despues_del_nucleo_y_antes_del_juego_y_es_reproducible(self):
        html = self.construir(['musica', 'efectos', 'accesible'])
        pos = [html.index('<script id="%s"' % s) for s in ('ggx', 'mod-accesible', 'mod-efectos', 'mod-musica', 'pack-audio')]
        self.assertEqual(pos, sorted(pos))
        self.assertLess(pos[3], html.index('<script', html.index('id="mod-musica"') + 20) + 1)
        primero = html
        self.assertEqual(self.construir(['accesible', 'musica', 'efectos']), primero, 'el orden en que el juego nombra los módulos no cambia el resultado')

    def test_un_modulo_inexistente_detiene_la_construccion_con_un_motivo(self):
        with self.assertRaises(SystemExit) as e:
            self.construir(['no-existe'])
        self.assertIn('no existe', str(e.exception.code))


class PruebasDeCompuerta(Proyecto):
    def setUp(self):
        super().setUp()
        self.usar('accesible', 'efectos', 'musica', 'marca')

    def nuevo(self, motores, id='compas'):
        s = ficha()
        s['id'] = id
        s['motor'] = motores
        return s

    def test_el_juego_nuevo_debe_subir_un_nivel_sobre_el_mejor_publicado(self):
        self.assertEqual(motor.exigido(self.tmp, self.nuevo([]), LANZADO), 3)
        razones = motor.compuerta(self.tmp, self.nuevo([]), LANZADO, 'lanzamiento')
        self.assertEqual(len(razones), 1)
        self.assertIn('nivel 2', razones[0])
        self.assertIn('al menos el 3', razones[0])
        self.assertIn('accesible', razones[0].lower())
        self.assertEqual(motor.compuerta(self.tmp, self.nuevo(['accesible', 'efectos']), LANZADO, 'lanzamiento'), [])

    def test_sin_juegos_publicados_el_primero_solo_necesita_el_nivel_1(self):
        piso = self.json('motor/piso.json')
        piso['niveles'] = {}                                       # una fábrica recién nacida: ni el libro ni el piso guardado tienen juegos
        self.escribir('motor/piso.json', piso)
        self.assertEqual(motor.exigido(self.tmp, self.nuevo([]), []), 1)
        self.assertEqual(motor.compuerta(self.tmp, self.nuevo([]), [], 'lanzamiento'), [])

    def test_la_exigencia_nunca_pasa_del_techo_del_motor(self):
        piso = self.json('motor/piso.json')
        piso['niveles'] = {'otro': 4}
        self.escribir('motor/piso.json', piso)
        self.assertEqual(motor.exigido(self.tmp, self.nuevo([]), LANZADO), 5)
        piso['niveles'] = {'otro': 5}
        self.escribir('motor/piso.json', piso)
        self.assertEqual(motor.exigido(self.tmp, self.nuevo([]), LANZADO), 5, 'el techo es 5: no se puede exigir un 6 que el motor no soporta')

    def test_un_juego_heredado_no_tiene_minimo_pero_no_puede_bajar(self):
        s = ficha()
        self.assertEqual(motor.compuerta(self.tmp, s, LANZADO, 'lanzamiento'), [])
        piso = self.json('motor/piso.json')
        piso['niveles'] = {'guerreros-gelatina': 3}
        self.escribir('motor/piso.json', piso)
        razones = motor.compuerta(self.tmp, s, LANZADO, 'parche')
        self.assertEqual(len(razones), 1)
        self.assertIn('bajó del nivel 3 al 2', razones[0])

    def test_el_piso_solo_sube(self):
        piso = self.json('motor/piso.json')
        piso['niveles'] = {'guerreros-gelatina': 4}
        self.escribir('motor/piso.json', piso)
        self.assertEqual(motor.sincronizar(self.tmp, LANZADO)['niveles']['guerreros-gelatina'], 4, 'el nivel del juego hoy es 2, pero lo ya alcanzado no se pierde')
        self.assertEqual(self.json('motor/piso.json')['niveles']['guerreros-gelatina'], 4)
        s = ficha()
        s['motor'] = ['accesible', 'efectos', 'musica', 'marca']
        self.escribir('juegos/guerreros-gelatina/juego.json', s)
        piso['niveles'] = {'guerreros-gelatina': 2}
        self.escribir('motor/piso.json', piso)
        self.assertEqual(motor.sincronizar(self.tmp, LANZADO)['niveles']['guerreros-gelatina'], 5, 'si el juego mejora, el piso sube')
        self.assertEqual(self.json('motor/piso.json')['niveles']['guerreros-gelatina'], 5)

    def test_solo_cuentan_los_lanzamientos_que_de_verdad_salieron(self):
        malos = [{'juego': 'a', 'lanzamiento': True, 'resultado': 'error', 'tipo': 'desplegar'}, {'juego': 'b', 'lanzamiento': False, 'resultado': 'ok', 'tipo': 'desplegar'},
                 {'juego': 'c', 'lanzamiento': True, 'resultado': 'ok', 'tipo': 'post'}]
        self.assertEqual(motor.lanzados(malos), [])
        self.assertEqual(motor.lanzados(LANZADO + LANZADO), ['guerreros-gelatina'])

    def test_usar_modulos_con_el_motor_sin_probar_detiene_la_publicacion(self):
        with open(self.tmp / 'motor' / 'modulos' / 'musica.js', 'a', encoding='utf-8') as f:
            f.write('// sin probar\n')
        razones = motor.compuerta(self.tmp, self.nuevo(['accesible', 'efectos', 'musica']), LANZADO, 'lanzamiento')
        self.assertTrue(any('motor:' in r and 'probar' in r for r in razones), razones)

    def test_una_dependencia_que_falta_detiene_la_publicacion(self):
        razones = motor.compuerta(self.tmp, self.nuevo(['efectos']), LANZADO, 'lanzamiento')
        self.assertTrue(any('pide «accesible»' in r for r in razones), razones)

    def test_la_compuerta_de_publicacion_la_aplica(self):
        sys.path.insert(0, str(RAIZ))
        from publicacion import nucleo
        fuente = (RAIZ / 'publicacion' / 'nucleo.py').read_text(encoding='utf-8')
        self.assertIn('motor_calidad.compuerta(ctx.raiz, ctx.spec, ctx.libro.entradas(), ctx.tipo)', fuente)
        self.assertTrue(hasattr(nucleo, 'compuertas'))


class PruebasDeCola(Proyecto):
    def setUp(self):
        super().setUp()
        self.usar('accesible', 'efectos', 'musica', 'marca')

    def cola(self, juegos=None, entradas=None):
        return motor.cola(self.tmp, LANZADO if entradas is None else entradas, juegos if juegos is not None else [ficha()])

    def test_sin_pruebas_vigentes_lo_primero_es_correrlas(self):
        (self.tmp / 'motor' / 'informe.json').unlink()
        c = self.cola()
        self.assertEqual(c[0]['tipo'], 'pruebas')
        self.assertIn('probar', c[0]['por_que'])

    def nivel_sin_modulo(self):
        """Agrega a la copia un nivel 6 que pide un módulo que aún no existe («retos», que sí está en el respaldo de ideas)."""
        esc = self.json('motor/escalera.json')
        esc['niveles'].append({'n': 6, 'nombre': 'Con retos', 'requiere': ['retos']})
        esc['requisitos']['retos'] = {'texto': 'Módulo «retos».', 'modulo': 'retos', 'uso': r'GGX\.retos\.'}
        self.escribir('motor/escalera.json', esc)

    def test_con_el_motor_al_dia_lo_siguiente_es_el_modulo_que_falta_del_siguiente_nivel(self):
        self.nivel_sin_modulo()
        c = self.cola()
        self.assertEqual([i['tipo'] for i in c][:2], ['modulo', 'actualizacion'])
        self.assertIn('retos', c[0]['titulo'])
        self.assertIn('nivel 6', c[0]['titulo'])
        self.assertIn('Da una razón para volver mañana', c[0]['por_que'])        # la razón sale del respaldo de ideas
        self.assertIn('accesible', c[1]['por_que'])                              # lo que le falta al juego publicado para llegar al techo (5)

    def test_con_todo_construido_solo_queda_actualizar_los_juegos_publicados(self):
        self.assertEqual([i['tipo'] for i in self.cola()], ['actualizacion'])

    def test_un_juego_por_salir_por_debajo_de_lo_exigido_es_lo_primero(self):
        nuevo = ficha()
        nuevo['id'] = 'compas'
        c = self.cola([ficha(), nuevo])
        self.assertEqual(c[0]['tipo'], 'juego')
        self.assertIn('«compas» al nivel 3 (hoy 2)', c[0]['titulo'])

    def test_un_pedido_de_un_juego_sin_modulo_entra_a_la_cola_y_uno_ya_ofrecido_no(self):
        s = ficha()
        s['necesidades_motor'] = ['partículas', 'rebotes con física de cuerpos blandos']
        pedidos = [i['titulo'] for i in self.cola([s]) if i['tipo'] == 'pedido']
        self.assertEqual(len(pedidos), 1)
        self.assertIn('rebotes con física', pedidos[0])

    def test_al_llegar_al_techo_se_abre_un_nivel_con_la_primera_idea_sin_construir(self):
        piso = self.json('motor/piso.json')
        piso['niveles'] = {'otro': 5}
        self.escribir('motor/piso.json', piso)
        c = self.cola(entradas=[])
        niveles = [i for i in c if i['tipo'] == 'nivel']
        self.assertEqual(len(niveles), 1)
        self.assertIn('Abrir el nivel 6', niveles[0]['titulo'])
        self.assertIn('retos', niveles[0]['titulo'])
        self.assertNotIn('marca', ''.join(i['modulo'] for i in json.loads((self.tmp / 'motor' / 'ideas.json').read_text(encoding='utf-8'))['ideas']),
                         'una idea que ya es módulo sale del respaldo')

    def test_el_resumen_de_estado_se_puede_leer(self):
        texto = '\n'.join(motor.informe_de_estado(self.tmp, LANZADO, [ficha(), ficha('torre-gelatina')]))
        self.assertIn('Techo del motor hoy: nivel 5 de 5', texto)
        self.assertIn('Pruebas del motor: al día', texto)
        self.assertIn('guerreros-gelatina: nivel 2', texto)
        self.assertIn('Lo que sigue para el motor', texto)


class PruebasDeInforme(Proyecto):
    def test_escribir_informe_marca_ok_solo_si_todo_paso_y_todo_se_probo(self):
        man = motor.manifiesto(self.tmp)
        bien = {'nucleo': {'pruebas': 3, 'fallas': 0, 'fallos': []}, 'modulos': {n: {'pruebas': 2, 'fallas': 0, 'fallos': []} for n in man}}
        self.assertTrue(motor.escribir_informe(self.tmp, bien)['ok'])
        self.assertEqual(motor.informe_vigente(self.tmp), (True, ''))
        falla = copy.deepcopy(bien)
        falla['modulos']['efectos']['fallas'] = 1
        self.assertFalse(motor.escribir_informe(self.tmp, falla)['ok'])
        sin = copy.deepcopy(bien)
        del sin['modulos']['musica']
        self.assertFalse(motor.escribir_informe(self.tmp, sin)['ok'], 'un módulo que no se probó no pasa')
        self.assertTrue(motor.escribir_informe(self.tmp, bien)['ok'])
        self.assertEqual(motor.escribir_informe(self.tmp, bien), self.json('motor/informe.json'))

    def test_la_huella_cambia_con_el_nucleo_los_modulos_y_el_guion_de_pruebas(self):
        base = motor.huella_del_motor(self.tmp)
        for ruta in ('motor/ggx.js', 'motor/modulos/musica.js', 'herramientas/probar_motor.js', 'motor/modulos.json'):
            with self.subTest(ruta):
                p = self.tmp / ruta
                original = p.read_bytes()
                p.write_bytes(original + b'\n// x\n')
                self.assertNotEqual(motor.huella_del_motor(self.tmp), base)
                p.write_bytes(original)
                self.assertEqual(motor.huella_del_motor(self.tmp), base)

    def test_la_pagina_de_prueba_trae_el_nucleo_y_todos_los_modulos(self):
        html = motor.pagina_de_prueba(self.tmp)
        for n in motor.manifiesto(self.tmp):
            self.assertIn('id="mod-%s"' % n, html)
        self.assertIn('window.GGX_CONFIG', html)


if __name__ == '__main__':
    unittest.main()
