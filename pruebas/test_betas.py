"""Pruebas de las betas (juegos de prueba que nunca se publican) y del informe de pruebas con bots (herramientas/bots.py).
Los bots mismos juegan en un Chromium real: eso lo prueba `python3 fabrica.py motor probar` (módulo «bots») y `python3 fabrica.py bots`; aquí se prueba
todo lo que no necesita navegador: cómo se resumen los episodios, qué banderas salen, y cómo se comporta el resto de la fábrica ante una beta.
Uso: python3 -I -m unittest discover -s pruebas   (desde la carpeta de la fábrica)"""
import copy
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'herramientas'))
import andamio  # noqa: E402
import bots  # noqa: E402
import novedad  # noqa: E402
import rumbo  # noqa: E402


def ep(escena, politica, exito, motivo=None, **extra):
    d = {'escena': escena, 'politica': politica, 'exito': exito, 'motivo': motivo or ('meta' if exito else 'derrota'), 'pasos': 10, 'ms_simulados': 1000, 'puntaje': 1 if exito else 0,
         'violaciones': [], 'errores': []}
    d.update(extra)
    return d


def resultado(episodios, **extra):
    r = {'config': {'semilla_base': 1000, 'factor': 1, 'base': 'aleatorio', 'solucionador': 'oraculo', 'humano': 'novato', 'descripcion': 'x'},
         'episodios': episodios, 'deterministas': [], 'errores_de_pagina': []}
    r.update(extra)
    return r


def partidas(escena, politica, ganadas, total, motivo_perdida='derrota'):
    return [ep(escena, politica, i < ganadas, None if i < ganadas else motivo_perdida) for i in range(total)]


def codigos(res):
    escenas, banderas = bots.resumir(res)
    return sorted(b['codigo'] for b in banderas), escenas, banderas


class Resumen(unittest.TestCase):
    def test_un_juego_sano_no_tiene_banderas(self):
        res = resultado(partidas('n1', 'aleatorio', 2, 20) + partidas('n1', 'oraculo', 1, 1) + partidas('n1', 'novato', 12, 20))
        c, escenas, _ = codigos(res)
        self.assertEqual(c, [])
        self.assertEqual(escenas['n1']['aleatorio']['tasa'], 0.1)
        self.assertEqual(escenas['n1']['novato']['partidas'], 20)

    def test_trivial_si_la_politica_debil_gana_casi_siempre(self):
        res = resultado(partidas('n1', 'aleatorio', 20, 20) + partidas('n1', 'oraculo', 1, 1) + partidas('n1', 'novato', 20, 20))
        c, _, b = codigos(res)
        self.assertEqual(c, ['trivial'])
        self.assertEqual(b[0]['nivel'], 'aviso')

    def test_trivial_pide_al_menos_cinco_partidas(self):
        res = resultado(partidas('n1', 'aleatorio', 3, 3) + partidas('n1', 'oraculo', 1, 1) + partidas('n1', 'novato', 10, 20))
        self.assertNotIn('trivial', codigos(res)[0])

    def test_imposible_si_el_solucionador_no_gana_ni_una_vez(self):
        res = resultado(partidas('n1', 'aleatorio', 0, 20) + partidas('n1', 'oraculo', 0, 1) + partidas('n1', 'novato', 0, 20))
        c, _, b = codigos(res)
        self.assertIn('imposible', c)
        self.assertEqual([x['nivel'] for x in b if x['codigo'] == 'imposible'], ['falla'])

    def test_dificil_si_solo_el_solucionador_gana(self):
        res = resultado(partidas('n1', 'aleatorio', 0, 20) + partidas('n1', 'oraculo', 1, 1) + partidas('n1', 'novato', 1, 20))
        self.assertEqual(codigos(res)[0], ['dificil'])

    def test_se_corta_no_se_marca_en_la_politica_debil_pero_si_en_la_humana(self):
        debil = resultado(partidas('n1', 'aleatorio', 0, 20, 'limite') + partidas('n1', 'oraculo', 1, 1) + partidas('n1', 'novato', 10, 20))
        self.assertNotIn('se-corta', codigos(debil)[0])       # una política débil por diseño no termina casi nunca en un juego sin derrota
        humana = resultado(partidas('n1', 'aleatorio', 2, 20) + partidas('n1', 'oraculo', 1, 1) + partidas('n1', 'novato', 5, 20, 'limite'))
        self.assertIn('se-corta', codigos(humana)[0])

    def test_fallas_que_rompen_el_comando(self):
        res = resultado(partidas('n1', 'aleatorio', 2, 20) + partidas('n1', 'oraculo', 1, 1) + partidas('n1', 'novato', 12, 20),
                        deterministas=[{'escena': 'n1', 'politica': 'novato', 'ok': False}], errores_de_pagina=['pageerror: boom'])
        res['episodios'][0]['violaciones'] = ['la materia no se conserva']
        c, _, b = codigos(res)
        for esperado in ('no-determinista', 'fallas-de-pagina', 'violaciones'):
            self.assertIn(esperado, c)
        self.assertTrue(all(x['nivel'] == 'falla' for x in b if x['codigo'] in ('no-determinista', 'fallas-de-pagina', 'violaciones')))

    def test_un_episodio_con_error_del_juego_es_una_falla(self):
        res = resultado(partidas('n1', 'aleatorio', 2, 20) + partidas('n1', 'oraculo', 1, 1) + partidas('n1', 'novato', 12, 20))
        res['episodios'][3]['motivo'] = 'error-del-juego'
        res['episodios'][3]['errores'] = ['avanzar: x']
        self.assertIn('errores-del-juego', codigos(res)[0])

    def test_sin_solucionador_imposible_solo_si_nadie_gana(self):
        res = resultado(partidas('n1', 'aleatorio', 0, 6), )
        res['config']['solucionador'] = None
        self.assertIn('imposible', codigos(res)[0])
        res2 = resultado(partidas('n1', 'aleatorio', 2, 6))
        res2['config']['solucionador'] = None
        self.assertNotIn('imposible', codigos(res2)[0])

    def test_agrega_los_numeros_del_resumen_del_juego(self):
        eps = partidas('mundo', 'explorador', 3, 3)
        for i, e in enumerate(eps):
            e['resumen'] = {'descubrimientos': 4, 'cuando': {'montana': 100 + 10 * i, 'isla': 700}, 'nota': 'texto', 'listo': True}
        eps[2]['resumen']['cuando'].pop('isla')
        _, escenas, _ = codigos(resultado(eps))
        r = escenas['mundo']['explorador']['resumen']
        self.assertEqual(r['descubrimientos'], {'p50': 4, 'n': 3})
        self.assertEqual(r['cuando.montana'], {'p50': 110, 'n': 3})
        self.assertEqual(r['cuando.isla'], {'p50': 700, 'n': 2})
        self.assertNotIn('nota', r)                      # lo que no es número no se agrega
        self.assertNotIn('listo', r)                     # un booleano no es un número

    def test_sin_resumen_no_hay_campo(self):
        _, escenas, _ = codigos(resultado(partidas('n1', 'oraculo', 1, 1)))
        self.assertNotIn('resumen', escenas['n1']['oraculo'])

    def test_el_informe_es_determinista_y_trae_la_huella(self):
        res = resultado(partidas('n1', 'aleatorio', 2, 20) + partidas('n1', 'oraculo', 1, 1) + partidas('n1', 'novato', 12, 20))
        a = bots.informe('j', '1.0.0', 'abc', copy.deepcopy(res))
        b = bots.informe('j', '1.0.0', 'abc', copy.deepcopy(res))
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(a['huella_html'], 'abc')
        self.assertTrue(a['determinista'])

    def test_texto_y_resumen_corto(self):
        sano = bots.informe('j', '1', 'h', resultado(partidas('n1', 'aleatorio', 2, 20) + partidas('n1', 'oraculo', 1, 1) + partidas('n1', 'novato', 12, 20)))
        self.assertIn('  Sin banderas.', bots.texto(sano))
        self.assertEqual(bots.resumen_corto(sano), '1 escena(s) probadas con bots: sin banderas')
        mal = bots.informe('j', '1', 'h', resultado(partidas('n1', 'aleatorio', 0, 20) + partidas('n1', 'oraculo', 0, 1) + partidas('n1', 'novato', 0, 20)))
        self.assertIn('1 falla(s)', bots.resumen_corto(mal))
        self.assertIsNone(bots.resumen_corto(None))


class Betas(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='ggx-betas-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for d in ('catalogo', 'juegos', 'motor', 'ideas', 'metricas'):
            if (RAIZ / d).exists():
                shutil.copytree(RAIZ / d, self.tmp / d, ignore=shutil.ignore_patterns('bitacora.jsonl', 'bots'))
        for p in (RAIZ / 'plantillas').glob('*/'):
            (self.tmp / 'plantillas' / p.name).mkdir(parents=True, exist_ok=True)
            for f in p.iterdir():
                if f.name in ('plantilla.json', 'bots.js'):
                    shutil.copy(f, self.tmp / 'plantillas' / p.name / f.name)

    def test_las_betas_de_hoy_estan_declaradas_y_completas(self):
        b = novedad.betas(RAIZ)
        self.assertIn('rebote-gelatina', b)
        self.assertIn('arena-gelatina', b)
        for i, s in b.items():
            self.assertIn('bots', s['motor'], i)
            self.assertTrue((RAIZ / 'plantillas' / s['plantilla'] / 'bots.js').exists(), i)
            self.assertTrue((RAIZ / 'salida' / i / 'index.html').exists(), '%s: falta construirla (python3 fabrica.py construir %s)' % (i, i))
        self.assertIn('rebote-gelatina', bots.juegos_con_bots(RAIZ))
        self.assertIn('arena-gelatina', bots.juegos_con_bots(RAIZ))

    def test_el_informe_guardado_de_cada_beta_es_de_su_version_actual(self):
        import hashlib
        for i in ('rebote-gelatina', 'arena-gelatina'):
            rep = bots.leer(RAIZ, i)
            self.assertIsNotNone(rep, '%s: falta correr «python3 fabrica.py bots %s»' % (i, i))
            actual = hashlib.sha256((RAIZ / 'salida' / i / 'index.html').read_bytes()).hexdigest()
            self.assertEqual(rep['huella_html'], actual, '%s: el informe de bots es de otra versión del juego; vuelve a correr «python3 fabrica.py bots %s»' % (i, i))
            self.assertEqual([b for b in rep['banderas'] if b['nivel'] == 'falla'], [], i)
            self.assertTrue(rep['determinista'], i)

    def test_una_beta_no_cuenta_para_la_novedad_de_los_demas(self):
        base = json.loads((RAIZ / 'juegos' / 'guerreros-gelatina' / 'juego.json').read_text(encoding='utf-8'))

        def copia(beta):
            s = copy.deepcopy(base)
            s['id'] = 'copia-previa'
            s['lanzamiento'] = {'orden': 0}
            s['ficha'] = {i: {'titulo': 'x', 'corta': 'otra cosa', 'larga': 'texto distinto y nada más que eso', 'controles': 'x'} for i in s['idiomas']}
            if beta:
                s['estado'] = 'beta'
            d = self.tmp / 'juegos' / 'copia-previa'
            d.mkdir(parents=True, exist_ok=True)
            (d / 'juego.json').write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
        copia(beta=False)
        self.assertNotEqual(novedad.evaluar(self.tmp, 'guerreros-gelatina')['veredicto'], 'distinto')   # la prueba de la prueba: sin «beta», la copia anterior sí cuenta
        copia(beta=True)
        self.assertEqual(novedad.evaluar(self.tmp, 'guerreros-gelatina')['veredicto'], 'distinto')

    def test_una_idea_con_beta_se_queda_en_el_ranking_y_una_construida_no(self):
        r = rumbo.recomendar(RAIZ)
        ids = {c['id']: c for c in r['ranking']}
        self.assertEqual(ids['rebote']['beta'], 'rebote-gelatina')
        self.assertEqual(ids['arena']['beta'], 'arena-gelatina')
        self.assertIn('bots', ids['rebote'])
        self.assertNotIn('compas', ids)                      # compas es un juego real: ya está construida
        self.assertNotIn('rebote-gelatina', r['datos'])      # las betas no son «juegos medibles» del rumbo

    def test_los_bots_no_cambian_el_puntaje_del_ranking(self):
        antes = {c['id']: c['puntaje'] for c in rumbo.recomendar(self.tmp)['ranking']}
        carpeta = self.tmp / 'metricas' / 'bots'
        carpeta.mkdir(parents=True, exist_ok=True)
        rep = bots.informe('rebote-gelatina', '0.1.0', 'x', resultado(partidas('n1', 'aleatorio', 0, 20) + partidas('n1', 'oraculo', 0, 1) + partidas('n1', 'novato', 0, 20)))
        (carpeta / 'rebote-gelatina.json').write_text(json.dumps(rep), encoding='utf-8')
        despues = rumbo.recomendar(self.tmp)
        self.assertIn('falla', {c['id']: c['bots'] for c in despues['ranking']}['rebote'])        # el ranking lo muestra…
        self.assertEqual(antes, {c['id']: c['puntaje'] for c in despues['ranking']})               # …pero no lo usa para puntuar

    def test_el_informe_del_rumbo_muestra_la_beta(self):
        texto = '\n'.join(rumbo.informe(rumbo.recomendar(RAIZ), n=5))
        self.assertIn('Beta: `rebote-gelatina`', texto)
        self.assertIn('Ya existe la beta', texto)

    def test_ya_construida_una_plantilla_que_solo_usan_betas_no_lo_esta(self):
        self.assertFalse(novedad.ya_construida(self.tmp, {'id': 'rebote'}))
        ruta = self.tmp / 'juegos' / 'rebote-gelatina' / 'juego.json'
        s = json.loads(ruta.read_text(encoding='utf-8'))
        s.pop('estado')
        ruta.write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
        self.assertTrue(novedad.ya_construida(self.tmp, {'id': 'rebote'}))        # promovida: ahora sí es un juego construido

    def test_nuevo_beta_declara_solo_el_modulo_de_bots_y_no_se_publica(self):
        d = andamio.nuevo_juego(self.tmp, 'mi-prueba', 'rebote', beta=True)
        s = json.loads((d / 'juego.json').read_text(encoding='utf-8'))
        self.assertEqual(s['estado'], 'beta')
        self.assertEqual(s['motor'], ['bots'])
        self.assertTrue(novedad.es_beta(s))

    def test_un_juego_nuevo_normal_solo_declara_bots_si_su_plantilla_trae_politicas(self):
        con = andamio.nuevo_juego(self.tmp, 'con-politicas', 'rebote')
        self.assertIn('bots', json.loads((con / 'juego.json').read_text(encoding='utf-8'))['motor'])
        sin = andamio.nuevo_juego(self.tmp, 'sin-politicas', 'torre')
        self.assertNotIn('bots', json.loads((sin / 'juego.json').read_text(encoding='utf-8'))['motor'])

    def test_kit_y_revisar_se_saltan_una_beta(self):
        for orden in ('kit', 'revisar'):
            r = subprocess.run([sys.executable, '-I', str(RAIZ / 'fabrica.py'), orden, 'rebote-gelatina'], capture_output=True, text=True, cwd=str(RAIZ))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('es una beta', r.stdout)
        self.assertFalse((RAIZ / 'salida' / 'rebote-gelatina' / 'kit').exists())

    def test_bots_se_niega_si_el_juego_no_declara_el_modulo_o_no_hay_politicas(self):
        ruta = self.tmp / 'juegos' / 'rebote-gelatina' / 'juego.json'
        s = json.loads(ruta.read_text(encoding='utf-8'))
        s['motor'] = []
        ruta.write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
        (self.tmp / 'salida' / 'rebote-gelatina').mkdir(parents=True)
        (self.tmp / 'salida' / 'rebote-gelatina' / 'index.html').write_text('<html></html>', encoding='utf-8')
        with self.assertRaises(bots.ErrorBots) as e:
            bots.correr(self.tmp, 'rebote-gelatina')
        self.assertIn('no declara el módulo «bots»', str(e.exception))
        with self.assertRaises(bots.ErrorBots) as e:
            bots.correr(self.tmp, 'torre-gelatina')
        self.assertIn('no define pruebas con bots', str(e.exception))


if __name__ == '__main__':
    unittest.main()
