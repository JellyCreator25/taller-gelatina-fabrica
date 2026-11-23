"""Pruebas del laboratorio de betas (herramientas/laboratorio.py y herramientas/laboratorio.js; contrato en motor/LABORATORIO.md).

Casi todo es puro (validación, plan, agregación, comparación, guardado) y corre sin navegador con datos inventados. Una prueba de punta a punta usa un Chromium real contra una
página con problemas puestos a propósito (pruebas/fixtures/laboratorio/); se omite sola donde no hay node y playwright (como en la integración continua)."""
import copy
import json
import os
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'herramientas'))
import laboratorio as L  # noqa: E402


def _hay_navegador():
    if not shutil.which('node'):
        return False
    r = subprocess.run(['node', '-e', "require('playwright')"], capture_output=True, env=L._entorno())
    return r.returncode == 0


PERFILES = L.cargar_perfiles(RAIZ)


def experimento_base():
    return {
        'formato': 1, 'id': 'prueba', 'titulo': 'Experimento de prueba', 'pregunta': '¿Funciona el laboratorio con datos inventados?',
        'objeto': {'html': 'pruebas/fixtures/laboratorio/pagina-con-problemas.html'},
        'variantes': [{'id': 'control'}, {'id': 'b'}],
        'perfiles': ['escritorio-rapido', 'mama-ocupada'],
        'pruebas': [{'id': 'auditoria', 'tipo': 'auditoria'}, {'id': 'flujo', 'tipo': 'guion', 'semillas': 5, 'pasos': [{'esperar': '#empezar', 'embudo': 've'}, {'tocar': '#empezar', 'embudo': 'toca'}]}],
    }


def sesion(variante, perfil, prueba, semilla, estado='completo', etapas=('ve', 'toca'), abandono=None, falla=None, a11y=None, errores=None, aislado=True, rep=False, traza=None, extra=None):
    s = {'cell': {'variante': variante, 'perfil': perfil, 'prueba': prueba, 'semilla': semilla, 'repeticion': rep}, 'estado': estado, 'abandono': abandono, 'falla': falla,
         'embudo': [{'etapa': e, 't': 300 + 100 * i} for i, e in enumerate(etapas)], 'datos': {}, 'primera_accion_ms': 400, 'acciones': 2, 'carga_modelada_ms': 120, 'peso_bytes': 3000, 'solicitudes': 1,
         'errores': dict({'pagina': [], 'consola': [], 'red': [], 'bloqueadas': []}, **(errores or {})), 'a11y': a11y or [], 'aislado': aislado,
         'traza': traza or 't-%s-%s-%s-%s' % (variante, perfil, prueba, semilla), 'eventos': [{'t': 0, 'tipo': 'carga'}], 'ms_simulados': 900,
         'medido': {'carga_real_ms': 100 + semilla % 7, 'ritmo_cpu': 0.4, 'pasada_max_ms': 50, 'memoria_mb': 12}}
    s.update(extra or {})
    return s


def plan_para(exp):
    return {'semilla_base': 1000, 'factor': 1.0, 'perfiles': [PERFILES[p] if isinstance(p, str) else p for p in exp['perfiles']], 'pruebas': exp['pruebas']}


def crudo_sano(exp, **kw):
    """Todas las combinaciones, 5 sesiones de guion que completan y una repetición idéntica de la primera."""
    celdas = []
    for v in exp['variantes']:
        for p in exp['perfiles']:
            celdas.append(sesion(v['id'], p, 'auditoria', 1000))
            celdas.append(sesion(v['id'], p, 'auditoria', 1000, rep=True))
            for i in range(5):
                celdas.append(sesion(v['id'], p, 'flujo', 1000 + i))
            celdas.append(sesion(v['id'], p, 'flujo', 1000, rep=True))
    return {'celdas': celdas}


class Perfiles(unittest.TestCase):
    def test_el_catalogo_trae_perfiles_validos_y_con_ids_unicos(self):
        self.assertGreaterEqual(len(PERFILES), 8)
        for pid, p in PERFILES.items():
            self.assertEqual(pid, p['id'])
            self.assertIn(p['entrada'], ('raton', 'tactil', 'teclado'))
        for esperado in ('mama-ocupada', 'cartero-en-ruta', 'teclado-solo', 'escritorio-rapido'):
            self.assertIn(esperado, PERFILES)

    def test_la_entrada_se_deduce_del_dispositivo_y_los_faltantes_toman_el_valor_base(self):
        t = L.normalizar_perfil({'id': 'x', 'dispositivo': {'tactil': True, 'ancho': 390, 'alto': 844}})
        self.assertEqual(t['entrada'], 'tactil')
        self.assertEqual(t['cpu'], 1)
        self.assertEqual(t['conducta']['ritmo'], 1.0)
        self.assertEqual(L.normalizar_perfil({'id': 'y'})['entrada'], 'raton')

    def test_un_perfil_con_cosas_raras_se_rechaza(self):
        for malo in ({'id': 'X'}, {'id': 'x', 'colorcito': 1}, {'id': 'x', 'cpu': 0}, {'id': 'x', 'entrada': 'voz'}, {'id': 'x', 'entrada': 'tactil'},
                     {'id': 'x', 'conducta': {'ritmo': 0}}, {'id': 'x', 'conducta': {'mala': 1}}, {'id': 'x', 'ambiente': {'tema': 'rosa'}},
                     {'id': 'x', 'conducta': {'interrupciones': [{'tras_acciones': 1}]}}, {'id': 'x', 'red': {'bajada_kbps': 0}}):
            with self.assertRaises(L.ErrorLaboratorio, msg=str(malo)):
                L.normalizar_perfil(malo)

    def test_normalizar_no_toca_el_original(self):
        p = {'id': 'x', 'conducta': {'ritmo': 2}}
        copia = copy.deepcopy(p)
        L.normalizar_perfil(p)
        self.assertEqual(p, copia)


class Validacion(unittest.TestCase):
    def test_los_experimentos_que_trae_la_fabrica_son_validos(self):
        ids = L.ids_de_experimentos(RAIZ)
        self.assertIn('rebote-primer-minuto', ids)
        self.assertIn('arena-primer-minuto', ids)
        for i in ids:
            exp = L.cargar_experimento(RAIZ, i)
            self.assertEqual(exp['id'], i, 'el id debe coincidir con el nombre del archivo')
            self.assertEqual(L.validar(RAIZ, exp, PERFILES), [], i)

    def errores(self, cambio):
        exp = experimento_base()
        cambio(exp)
        return L.validar(RAIZ, exp, PERFILES)

    def test_el_experimento_base_de_las_pruebas_es_valido(self):
        self.assertEqual(L.validar(RAIZ, experimento_base(), PERFILES), [])

    def test_hay_que_decir_que_se_quiere_saber(self):
        self.assertTrue(any('pregunta' in e for e in self.errores(lambda e: e.pop('pregunta'))))
        self.assertTrue(any('titulo' in e for e in self.errores(lambda e: e.update(titulo='x'))))

    def test_claves_desconocidas_y_formato(self):
        self.assertTrue(any('desconocidas' in e for e in self.errores(lambda e: e.update(extra=1))))
        self.assertTrue(any('formato' in e for e in self.errores(lambda e: e.update(formato=2))))

    def test_el_objeto_es_siempre_un_archivo_local(self):
        for obj in ({'html': 'https://example.com/x.html'}, {'html': '../afuera.html'}, {'html': 'no/existe.html'}, {'html': 'LEEME.md'}, {'juego': 'no-existe'}, {'juego': 'a', 'html': 'b'}, 'x'):
            self.assertTrue(self.errores(lambda e, o=obj: e.update(objeto=o)), str(obj))

    def test_variantes(self):
        self.assertTrue(any('repetida' in e for e in self.errores(lambda e: e['variantes'].append({'id': 'b'}))))
        self.assertTrue(any('desconocidas' in e for e in self.errores(lambda e: e['variantes'][1].update(color='rojo'))))
        self.assertTrue(any('no encuentra' in e for e in self.errores(lambda e: e['variantes'][1].update(reemplazos=[{'buscar': 'texto que no está', 'poner': 'x'}]))))
        self.assertEqual(self.errores(lambda e: e['variantes'][1].update(reemplazos=[{'buscar': 'Prueba del laboratorio', 'poner': 'Otro'}])), [])
        self.assertTrue(self.errores(lambda e: e['variantes'][1].update(juego='no-es-un-objeto')))
        self.assertTrue(self.errores(lambda e: e.update(variantes=[])))

    def test_perfiles(self):
        self.assertTrue(any('no está' in e for e in self.errores(lambda e: e['perfiles'].append('inventado'))))
        self.assertTrue(any('repetido' in e for e in self.errores(lambda e: e['perfiles'].append('mama-ocupada'))))
        self.assertEqual(self.errores(lambda e: e['perfiles'].append({'id': 'propio', 'cpu': 3})), [])

    def test_pasos_del_guion(self):
        def con(paso):
            return self.errores(lambda e: e['pruebas'][1]['pasos'].append(paso))
        self.assertTrue(any('exactamente un verbo' in x for x in con({'tocar': '#a', 'esperar': '#b'})))
        self.assertTrue(any('exactamente un verbo' in x for x in con({'embudo': 'x'})))
        self.assertTrue(any('no corresponden' in x for x in con({'tocar': '#a', 'colorcito': 1})))
        self.assertTrue(con({'tocar': {'x': 0.5}}))
        self.assertTrue(con({'tocar': {'selector': '#a', 'x': 2}}))
        self.assertTrue(con({'tocar': {'selector': '#a', 'js': 'x', 'ref': [0, 10]}}))
        self.assertTrue(con({'leer': {'id': 'MAL', 'js': '1'}}))
        self.assertTrue(con({'repetir': {'pasos': [{'tocar': '#a'}]}}))
        self.assertTrue(con({'repetir': {'maximo': 3, 'pasos': [{'tocar': '#a', 'raro': 1}]}}))
        self.assertTrue(con({'tecla': 'A', 'veces': 0}))
        self.assertTrue(con({'tecla': 'A', 'veces': {'min': 5, 'max': 2}}))
        self.assertTrue(con({'pasar': -5}))
        self.assertTrue(con({'si': {'entrada': 'voz'}, 'tocar': '#a'}))
        self.assertTrue(con({'verificar': {'mensaje': 'sin js'}}))
        for bueno in ({'tocar': '#a'}, {'tecla': 'A', 'veces': {'min': 1, 'max': 4}}, {'leer': {'id': 'dato_1', 'js': '1'}}, {'si': {'entrada': ['raton', 'tactil']}, 'tocar': '#a'},
                      {'repetir': {'maximo': 3, 'hasta': 'true', 'pasos': [{'tocar': '#a'}]}}, {'arrastrar': {'desde': {'selector': '#c', 'x': 0.1}, 'hasta': '#d', 'pasos': 4}},
                      {'mantener': {'en': '#c', 'ms': 500}}, {'esperar_hasta': 'true', 'max_ms': 100, 'falla_si_no': True}, {'interrumpir': 3000}):
            self.assertEqual(con(bueno), [], str(bueno))

    def test_pruebas(self):
        self.assertTrue(self.errores(lambda e: e['pruebas'].append({'id': 'auditoria', 'tipo': 'auditoria'})))                       # repetida
        self.assertTrue(self.errores(lambda e: e['pruebas'].append({'id': 'x', 'tipo': 'raro'})))
        self.assertTrue(self.errores(lambda e: e['pruebas'].append({'id': 'x', 'tipo': 'guion', 'pasos': []})))
        self.assertTrue(self.errores(lambda e: e['pruebas'][1].update(semillas=0)))
        self.assertTrue(self.errores(lambda e: e['pruebas'][0].update(pasos=[])))                                                  # una auditoría no lleva pasos
        self.assertTrue(any('solo corre sobre un juego' in x for x in self.errores(lambda e: e['pruebas'].append({'id': 'b', 'tipo': 'bots'}))))
        self.assertTrue(self.errores(lambda e: e.update(umbrales={'inventado': 0.5})))


class Plan(unittest.TestCase):
    def test_se_expande_en_celdas_con_semillas_consecutivas_y_una_repeticion(self):
        exp = experimento_base()
        plan = L.planear(RAIZ, exp, PERFILES)
        # 2 variantes × 2 perfiles × (auditoría 1 + 1 repetición + guion 5 + 1 repetición)
        self.assertEqual(len(plan['celdas']), 2 * 2 * (1 + 1 + 5 + 1))
        guion = [c for c in plan['celdas'] if c['variante'] == 'control' and c['perfil']['id'] == 'mama-ocupada' and c['prueba']['id'] == 'flujo']
        self.assertEqual([c['semilla'] for c in guion if not c['repeticion']], [1000, 1001, 1002, 1003, 1004])
        self.assertEqual([c['semilla'] for c in guion if c['repeticion']], [1000])
        self.assertTrue(all(c['perfil']['conducta']['ritmo'] > 0 for c in plan['celdas']))

    def test_el_factor_escala_las_semillas_y_las_banderas_de_filtro_recortan(self):
        exp = experimento_base()
        self.assertEqual(len([c for c in L.planear(RAIZ, exp, PERFILES, factor=2)['celdas'] if c['prueba']['id'] == 'flujo' and not c['repeticion']]), 2 * 2 * 10)
        self.assertEqual(len([c for c in L.planear(RAIZ, exp, PERFILES, factor=0.1)['celdas'] if c['prueba']['id'] == 'flujo' and not c['repeticion']]), 2 * 2 * 1)
        solo = L.planear(RAIZ, exp, PERFILES, solo_perfiles=['mama-ocupada'], solo_pruebas=['flujo'], determinismo=False)
        self.assertEqual({c['perfil']['id'] for c in solo['celdas']}, {'mama-ocupada'})
        self.assertEqual(len(solo['celdas']), 2 * 5)
        with self.assertRaises(L.ErrorLaboratorio):
            L.planear(RAIZ, exp, PERFILES, solo_perfiles=['teclado-solo'])
        with self.assertRaises(L.ErrorLaboratorio):
            L.planear(RAIZ, exp, PERFILES, solo_pruebas=['no-existe'])

    def test_hay_un_tope_de_celdas(self):
        exp = experimento_base()
        exp['pruebas'][1]['semillas'] = 200
        exp['perfiles'] = list(PERFILES)
        with self.assertRaises(L.ErrorLaboratorio):
            L.planear(RAIZ, exp, PERFILES, factor=5)

    def test_las_semillas_base_y_los_reemplazos_pasan_al_plan(self):
        exp = experimento_base()
        exp['variantes'][1].update(reemplazos=[{'buscar': 'Prueba', 'poner': 'Otra'}], juego={'parametros': {'vidas': 9}}, css='h1{color:red}', consulta='x=1')
        plan = L.planear(RAIZ, exp, PERFILES, semilla_base=77)
        self.assertEqual(plan['celdas'][0]['semilla'], 77)
        b = plan['variantes'][1]
        self.assertEqual((b['juego']['parametros']['vidas'], b['css'], b['consulta']), (9, 'h1{color:red}', 'x=1'))
        self.assertEqual(b['reemplazos'][0]['veces'], 1)


class Estadistica(unittest.TestCase):
    def test_wilson(self):
        self.assertEqual(L.wilson(0, 0), [0.0, 1.0])
        lo, hi = L.wilson(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.2775, places=3)
        lo, hi = L.wilson(10, 10)
        self.assertAlmostEqual(lo, 0.7225, places=3)
        self.assertEqual(hi, 1.0)
        lo, hi = L.wilson(5, 10)
        self.assertTrue(lo < 0.5 < hi)

    def test_percentiles(self):
        self.assertIsNone(L._p([], 0.5))
        self.assertEqual(L._p([5], 0.5), 5)
        self.assertEqual(L._p([1, 2, 3, 4], 0.5), 2)
        self.assertEqual(L._p([1, 2, 3, 4], 0.9), 4)


class Informe(unittest.TestCase):
    def setUp(self):
        self.exp = experimento_base()
        self.plan = plan_para(self.exp)

    def rep(self, crudo=None, exp=None):
        exp = exp or self.exp
        return L.informe(exp, plan_para(exp), crudo or crudo_sano(exp), '0.1.0', {'control': 'h1', 'b': 'h2'})

    def test_un_experimento_sano_no_tiene_banderas(self):
        rep, medido = self.rep()
        self.assertEqual(rep['banderas'], [])
        g = next(g for g in rep['grupos'] if (g['variante'], g['perfil'], g['prueba']) == ('control', 'mama-ocupada', 'flujo'))
        self.assertEqual((g['sesiones'], g['completaron'], g['tasa_completa']), (5, 5, 1.0))
        self.assertEqual([(e['etapa'], e['alcanzaron']) for e in g['embudo']], [('ve', 5), ('toca', 5)])
        self.assertTrue(g['determinista'])
        self.assertEqual(len(rep['grupos']), 2 * 2 * 2)
        self.assertEqual(rep['objeto']['version'], '0.1.0')

    def test_el_informe_es_reproducible_y_no_depende_del_orden_ni_de_lo_medido(self):
        crudo = crudo_sano(self.exp)
        a, _ = self.rep(crudo)
        otro = copy.deepcopy(crudo)
        random.Random(3).shuffle(otro['celdas'])
        for c in otro['celdas']:
            c['medido'] = {'carga_real_ms': 9999, 'ritmo_cpu': 7.7, 'pasada_max_ms': 1, 'memoria_mb': 1}
        b, medido = self.rep(otro)
        self.assertEqual(a['huella_resultado'], b['huella_resultado'])
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertNotIn('carga_real_ms', json.dumps(a))
        self.assertEqual(medido['grupos'][0]['carga_real_ms']['p50'], 9999)

    def test_una_variante_que_cambia_los_resultados_cambia_la_huella(self):
        a, _ = self.rep()
        crudo = crudo_sano(self.exp)
        crudo['celdas'][3]['estado'] = 'abandono'
        crudo['celdas'][3]['abandono'] = {'paso': 'p1', 'motivo': 'paciencia'}
        b, _ = self.rep(crudo)
        self.assertNotEqual(a['huella_resultado'], b['huella_resultado'])

    def test_abandono_alto_bloqueo_por_perfil_y_donde_se_traban(self):
        crudo = crudo_sano(self.exp)
        for c in crudo['celdas']:
            if c['cell']['variante'] == 'control' and c['cell']['perfil'] == 'mama-ocupada' and c['cell']['prueba'] == 'flujo' and not c['cell']['repeticion']:
                c.update(estado='abandono', abandono={'paso': 'toca-tapado', 'motivo': 'cubierto'}, embudo=c['embudo'][:1])
        rep, _ = self.rep(crudo)
        cod = {(b['codigo'], b['donde']) for b in rep['banderas']}
        self.assertIn(('abandono-alto', 'control/mama-ocupada/flujo'), cod)
        self.assertIn(('bloqueado-para-perfil', 'control/mama-ocupada/flujo'), cod)
        self.assertNotIn('imposible', {b['codigo'] for b in rep['banderas']})
        g = next(g for g in rep['grupos'] if (g['variante'], g['perfil'], g['prueba']) == ('control', 'mama-ocupada', 'flujo'))
        self.assertEqual(g['abandonos_en'], {'toca-tapado: cubierto': 5})
        self.assertEqual(g['ejemplo_de_fallo']['abandono']['motivo'], 'cubierto')
        self.assertEqual([e['etapa'] for e in g['embudo']], ['ve'])
        texto = '\n'.join(b['texto'] for b in rep['banderas'])
        self.assertIn('toca-tapado: cubierto', texto)

    def test_si_nadie_con_ningun_perfil_completa_es_imposible(self):
        crudo = crudo_sano(self.exp)
        for c in crudo['celdas']:
            if c['cell']['variante'] == 'b' and c['cell']['prueba'] == 'flujo':
                c.update(estado='abandono', abandono={'paso': 'x', 'motivo': 'no-existe'}, embudo=[])
        rep, _ = self.rep(crudo)
        imp = [b for b in rep['banderas'] if b['codigo'] == 'imposible']
        self.assertEqual([b['donde'] for b in imp], ['b/flujo'])
        self.assertEqual(imp[0]['nivel'], 'falla')

    def test_verificaciones_fallidas_errores_internos_y_determinismo_son_fallas(self):
        crudo = crudo_sano(self.exp)
        for c in crudo['celdas']:
            k = c['cell']
            if k['variante'] == 'control' and k['perfil'] == 'escritorio-rapido' and k['prueba'] == 'flujo' and k['semilla'] == 1001 and not k['repeticion']:
                c.update(estado='falla', falla={'paso': 'abre-nivel', 'mensaje': 'Jugar no abrió el nivel 1'})
            if k['variante'] == 'control' and k['perfil'] == 'escritorio-rapido' and k['prueba'] == 'flujo' and k['semilla'] == 1002 and not k['repeticion']:
                c.update(estado='falla', falla={'paso': 'interno', 'mensaje': 'tiempo agotado'})
            if k['variante'] == 'b' and k['perfil'] == 'mama-ocupada' and k['prueba'] == 'flujo' and k['repeticion']:
                c['traza'] = 'otra-cosa'
        rep, _ = self.rep(crudo)
        por = {(b['codigo'], b['donde']): b for b in rep['banderas']}
        self.assertEqual(por[('verificacion-fallida', 'control/escritorio-rapido/flujo')]['nivel'], 'falla')
        self.assertIn('Jugar no abrió el nivel 1', por[('verificacion-fallida', 'control/escritorio-rapido/flujo')]['texto'])
        self.assertEqual(por[('error-interno', 'control/escritorio-rapido/flujo')]['nivel'], 'falla')
        self.assertEqual(por[('no-determinista', 'b/mama-ocupada/flujo')]['nivel'], 'falla')

    def test_los_problemas_de_la_pagina_son_una_bandera_por_variante_no_una_por_grupo(self):
        crudo = crudo_sano(self.exp)
        for c in crudo['celdas']:
            if c['cell']['variante'] == 'control':
                c['errores'] = {'pagina': [], 'consola': ['error de ejemplo'], 'red': ['404 /no-existe.png'], 'bloqueadas': ['example.com/x.json']}
        rep, _ = self.rep(crudo)
        cod = [(b['codigo'], b['donde'], b['nivel']) for b in rep['banderas']]
        self.assertEqual(sorted(cod), [('fallas-de-pagina', 'control', 'falla'), ('recurso-faltante', 'control', 'falla'), ('red-externa', 'control', 'aviso')])
        self.assertIn('en 4 de 4 grupos', rep['banderas'][0]['texto'])

    def test_contexto_sucio_y_carga_lenta(self):
        crudo = crudo_sano(self.exp)
        for c in crudo['celdas']:
            k = c['cell']
            if k['variante'] == 'control' and k['perfil'] == 'mama-ocupada' and k['prueba'] == 'flujo' and k['semilla'] == 1000 and not k['repeticion']:
                c['aislado'] = False
            if k['variante'] == 'b' and k['perfil'] == 'mama-ocupada' and k['prueba'] == 'flujo' and k['semilla'] in (1000, 1001) and not k['repeticion']:
                c.update(estado='abandono', abandono={'paso': 'carga', 'motivo': 'carga-lenta', 'modelada_ms': 4100, 'paciencia_ms': 3000}, embudo=[])
        rep, _ = self.rep(crudo)
        cod = {b['codigo']: b for b in rep['banderas']}
        self.assertEqual(cod['contexto-sucio']['nivel'], 'falla')
        self.assertIn('4100', cod['carga-lenta']['texto'])
        self.assertIn('2 sesión', cod['carga-lenta']['texto'])

    def test_accesibilidad_una_bandera_por_codigo_y_variante_con_los_perfiles(self):
        crudo = crudo_sano(self.exp)
        for c in crudo['celdas']:
            k = c['cell']
            if k['variante'] == 'control' and k['prueba'] == 'auditoria' and not k['repeticion']:
                c['a11y'] = [{'codigo': 'contraste-bajo', 'n': 3, 'ejemplo': 'h1 1.92:1'}] + ([{'codigo': 'objetivo-chico-tactil', 'n': 1, 'ejemplo': 'button 16×16'}] if k['perfil'] == 'mama-ocupada' else [])
        rep, _ = self.rep(crudo)
        a = {(b['codigo'], b['donde']): b for b in rep['banderas'] if b['codigo'].startswith('a11y-')}
        self.assertEqual(set(a), {('a11y-contraste-bajo', 'control'), ('a11y-objetivo-chico-tactil', 'control')})
        self.assertIn('en 2 perfil(es)', a[('a11y-contraste-bajo', 'control')]['texto'])
        self.assertIn('en 1 perfil(es): mama-ocupada', a[('a11y-objetivo-chico-tactil', 'control')]['texto'])
        self.assertTrue(all(b['nivel'] == 'aviso' for b in a.values()))

    def test_los_datos_leidos_se_resumen_como_mediana_o_reparto(self):
        crudo = crudo_sano(self.exp)
        n = 0
        for c in crudo['celdas']:
            if c['cell']['variante'] == 'control' and c['cell']['perfil'] == 'mama-ocupada' and c['cell']['prueba'] == 'flujo' and not c['cell']['repeticion']:
                n += 1
                c['datos'] = {'tiros': n, 'fase': 'ganado' if n % 2 else 'perdido', 'detalle': {'a': 2 * n}, 'ok': True}
        rep, _ = self.rep(crudo)
        g = next(g for g in rep['grupos'] if (g['variante'], g['perfil'], g['prueba']) == ('control', 'mama-ocupada', 'flujo'))
        self.assertEqual(g['datos']['tiros'], {'p50': 3, 'n': 5})
        self.assertEqual(g['datos']['fase']['reparto'], {'ganado': 3, 'perdido': 2})
        self.assertEqual(g['datos']['detalle.a']['p50'], 6)
        self.assertEqual(g['datos']['ok']['reparto'], {'true': 5})

    def test_contrastes_ab_claro_solo_si_los_intervalos_no_se_cruzan(self):
        exp = copy.deepcopy(self.exp)
        exp['pruebas'][1]['semillas'] = 20
        crudo = {'celdas': []}
        for v in exp['variantes']:
            for p in exp['perfiles']:
                for i in range(20):
                    ok = not (v['id'] == 'b' and p == 'mama-ocupada' and i < 18) and not (v['id'] == 'b' and p == 'escritorio-rapido' and i < 2)
                    crudo['celdas'].append(sesion(v['id'], p, 'flujo', 1000 + i, estado='completo' if ok else 'abandono', abandono=None if ok else {'paso': 'x', 'motivo': 'paciencia'}))
                crudo['celdas'].append(sesion(v['id'], p, 'flujo', 1000, rep=True))
        exp['pruebas'] = [exp['pruebas'][1]]
        rep, _ = L.informe(exp, plan_para(exp), crudo)
        c = {x['perfil']: x for x in rep['contrastes']}
        self.assertEqual(c['mama-ocupada']['delta_tasa'], -0.9)
        self.assertTrue(c['mama-ocupada']['claro'])
        self.assertEqual(c['escritorio-rapido']['delta_tasa'], -0.1)
        self.assertFalse(c['escritorio-rapido']['claro'])

    def test_los_bots_dentro_del_laboratorio_reutilizan_las_banderas_del_organo_de_bots(self):
        exp = copy.deepcopy(self.exp)
        exp['pruebas'] = [{'id': 'partidas', 'tipo': 'bots'}, exp['pruebas'][1]]
        exp['perfiles'] = ['mama-ocupada']
        episodios = [{'politica': 'aleatorio', 'escena': 'nivel-1', 'exito': True, 'motivo': 'meta', 'pasos': 3, 'ms_simulados': 900, 'puntaje': 1, 'violaciones': [], 'errores': []} for _ in range(10)]
        episodios += [{'politica': 'oraculo', 'escena': 'nivel-1', 'exito': True, 'motivo': 'meta', 'pasos': 3, 'ms_simulados': 900, 'puntaje': 3, 'violaciones': [], 'errores': []}]
        celda = {'cell': {'variante': 'control', 'perfil': 'mama-ocupada', 'prueba': 'partidas', 'semilla': 0, 'repeticion': False}, 'tipo': 'bots',
                 'config': {'base': 'aleatorio', 'solucionador': 'oraculo', 'humano': None}, 'episodios': episodios, 'deterministas': [{'politica': 'aleatorio', 'escena': 'nivel-1', 'ok': True}],
                 'errores_de_pagina': [], 'aislado': True, 'errores': {'pagina': [], 'consola': [], 'red': [], 'bloqueadas': []}}
        crudo = {'celdas': [celda]}
        for i in range(5):
            crudo['celdas'].append(sesion('control', 'mama-ocupada', 'flujo', 1000 + i))
        crudo['celdas'].append(sesion('control', 'mama-ocupada', 'flujo', 1000, rep=True))
        exp['variantes'] = exp['variantes'][:1]
        rep, _ = L.informe(exp, plan_para(exp), crudo)
        g = next(g for g in rep['grupos'] if g['tipo'] == 'bots')
        self.assertEqual(g['escenas']['nivel-1']['aleatorio']['tasa'], 1.0)
        self.assertEqual([b['codigo'] for b in rep['banderas']], ['bots-trivial'])
        self.assertEqual(rep['banderas'][0]['nivel'], 'aviso')
        self.assertEqual(rep['banderas'][0]['donde'], 'control/partidas/nivel-1')
        self.assertIn('(en 1 de 1 perfil(es))', rep['banderas'][0]['texto'])
        self.assertTrue(g['determinista'])

    def test_la_misma_bandera_de_bots_en_varios_perfiles_se_junta_en_una(self):
        exp = copy.deepcopy(self.exp)
        exp['pruebas'] = [{'id': 'partidas', 'tipo': 'bots'}]
        exp['variantes'] = exp['variantes'][:1]
        exp['perfiles'] = ['escritorio-rapido', 'mama-ocupada', 'teclado-solo']
        crudo = {'celdas': []}
        for perfil in exp['perfiles']:
            facil = perfil != 'mama-ocupada'                          # solo con este perfil el azar no gana siempre
            episodios = [{'politica': 'aleatorio', 'escena': 'nivel-1', 'exito': facil or i < 5, 'motivo': 'meta', 'pasos': 3, 'ms_simulados': 900, 'puntaje': 1, 'violaciones': [], 'errores': []} for i in range(10)]
            episodios += [{'politica': 'oraculo', 'escena': 'nivel-1', 'exito': True, 'motivo': 'meta', 'pasos': 3, 'ms_simulados': 900, 'puntaje': 3, 'violaciones': [], 'errores': []}]
            crudo['celdas'].append({'cell': {'variante': 'control', 'perfil': perfil, 'prueba': 'partidas', 'semilla': 0, 'repeticion': False}, 'tipo': 'bots',
                                    'config': {'base': 'aleatorio', 'solucionador': 'oraculo', 'humano': None}, 'episodios': episodios, 'deterministas': [{'politica': 'aleatorio', 'escena': 'nivel-1', 'ok': True}],
                                    'errores_de_pagina': [], 'aislado': True, 'errores': {'pagina': [], 'consola': [], 'red': [], 'bloqueadas': []}})
        rep, _ = L.informe(exp, plan_para(exp), crudo)
        triviales = [b for b in rep['banderas'] if b['codigo'] == 'bots-trivial']
        self.assertEqual(len(triviales), 1)
        self.assertIn('(en 2 de 3 perfil(es): escritorio-rapido, teclado-solo)', triviales[0]['texto'])

    def test_texto_y_resumen(self):
        rep, _ = self.rep()
        t = '\n'.join(L.texto(rep))
        self.assertIn('Sin banderas.', t)
        self.assertIn('mama-ocupada', t)
        self.assertIn('ve 5 → toca 5', t)
        self.assertEqual(L.resumen_corto(rep), 'laboratorio «prueba»: 2 perfil(es) × 2 variante(s): sin banderas')
        self.assertIsNone(L.resumen_corto(None))


class Comparar(unittest.TestCase):
    def reps(self, cambia):
        exp = experimento_base()
        exp['pruebas'][1]['semillas'] = 10
        exp['variantes'] = exp['variantes'][:1]
        exp['perfiles'] = ['mama-ocupada']

        def crudo(f):
            celdas = [sesion('control', 'mama-ocupada', 'auditoria', 1000), sesion('control', 'mama-ocupada', 'auditoria', 1000, rep=True)]
            for i in range(10):
                celdas.append(sesion('control', 'mama-ocupada', 'flujo', 1000 + i))
            celdas.append(sesion('control', 'mama-ocupada', 'flujo', 1000, rep=True))
            return f({'celdas': celdas})
        a, _ = L.informe(exp, plan_para(exp), crudo(lambda x: x), '0.1.0', {'control': 'a'})
        b, _ = L.informe(exp, plan_para(exp), crudo(cambia), '0.2.0', {'control': 'b'})
        return a, b

    def test_sin_cambios(self):
        a, b = self.reps(lambda x: x)
        cmp = L.comparar(a, b)
        self.assertEqual(cmp['cambios'], [])
        self.assertIn('versión 0.1.0 → 0.2.0', cmp['nota'])
        self.assertIn('Sin cambios', '\n'.join(L.texto_comparacion(cmp)))

    def test_una_regresion_clara_de_completar_y_el_embudo(self):
        def peor(x):
            for c in x['celdas']:
                if c['cell']['prueba'] == 'flujo' and not c['cell']['repeticion'] and c['cell']['semilla'] < 1008:
                    c.update(estado='abandono', abandono={'paso': 'toca', 'motivo': 'paciencia'}, embudo=c['embudo'][:1])
            return x
        a, b = self.reps(peor)
        cmp = L.comparar(a, b)
        textos = [(c['tipo'], c['texto']) for c in cmp['cambios']]
        self.assertTrue(any(t == 'regresion' and 'completan 100 % → 20 %' in x for t, x in textos), textos)
        self.assertTrue(any(t == 'regresion' and 'etapa «toca»' in x for t, x in textos), textos)
        self.assertTrue(any(t == 'cambio' and 'bandera nueva: abandono-alto' in x for t, x in textos), textos)      # un aviso nuevo se anota, no cuenta como regresión
        self.assertGreaterEqual(cmp['resumen']['regresion'], 2)

    def test_mejoras_y_problemas_de_accesibilidad(self):
        def con_a11y(x):
            for c in x['celdas']:
                if c['cell']['prueba'] == 'auditoria' and not c['cell']['repeticion']:
                    c['a11y'] = [{'codigo': 'texto-chico', 'n': 1, 'ejemplo': 'p 10px'}]
            return x
        a, b = self.reps(con_a11y)
        cmp = L.comparar(a, b)
        self.assertTrue(any(c['tipo'] == 'regresion' and 'texto-chico' in c['texto'] for c in cmp['cambios']))
        cmp2 = L.comparar(b, a)
        self.assertTrue(any(c['tipo'] == 'mejora' and 'texto-chico' in c['texto'] for c in cmp2['cambios']))

    def test_una_falla_nueva_es_regresion_y_una_resuelta_es_mejora(self):
        def con_falla(x):
            x['celdas'][0]['errores']['consola'] = ['boom']
            return x
        a, b = self.reps(con_falla)
        self.assertTrue(any(c['tipo'] == 'regresion' and 'fallas-de-pagina' in c['texto'] for c in L.comparar(a, b)['cambios']))
        self.assertTrue(any(c['tipo'] == 'mejora' and 'fallas-de-pagina' in c['texto'] for c in L.comparar(b, a)['cambios']))

    def test_no_se_comparan_experimentos_distintos(self):
        a, b = self.reps(lambda x: x)
        b['experimento'] = 'otro'
        with self.assertRaises(L.ErrorLaboratorio):
            L.comparar(a, b)

    def test_combinaciones_nuevas_o_retiradas(self):
        a, b = self.reps(lambda x: x)
        b['grupos'] = b['grupos'][:1]
        cmp = L.comparar(a, b)
        self.assertTrue(any('ya no se prueba' in c['texto'] for c in cmp['cambios']))


class Guardado(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.exp = experimento_base()

    def hacer(self, version, tocar=None):
        crudo = crudo_sano(self.exp)
        if tocar:
            tocar(crudo)
        return L.informe(self.exp, plan_para(self.exp), crudo, version, {'control': 'h-' + version, 'b': 'h-' + version})

    def test_guardar_leer_y_rotar_al_cambiar_de_version(self):
        r1, m1 = self.hacer('0.1.0')
        ruta = L.guardar(self.tmp, r1, m1)
        self.assertTrue(ruta.exists() and (pathlib.Path(self.tmp) / 'metricas' / 'laboratorio' / 'prueba.medido.json').exists())
        self.assertEqual(L.leer(self.tmp, 'prueba')['huella_resultado'], r1['huella_resultado'])
        self.assertIsNone(L.leer(self.tmp, 'prueba', previo=True))
        # la misma versión y el mismo resultado no rota nada
        L.guardar(self.tmp, r1, m1)
        self.assertIsNone(L.leer(self.tmp, 'prueba', previo=True))
        # otra versión con otro resultado: el anterior pasa a «previo» (con su medido)
        r2, m2 = self.hacer('0.2.0', lambda c: c['celdas'][2].update(estado='abandono', abandono={'paso': 'p', 'motivo': 'paciencia'}))
        L.guardar(self.tmp, r2, m2)
        self.assertEqual(L.leer(self.tmp, 'prueba', previo=True)['objeto']['version'], '0.1.0')
        self.assertEqual(L.leer(self.tmp, 'prueba')['objeto']['version'], '0.2.0')
        self.assertTrue((pathlib.Path(self.tmp) / 'metricas' / 'laboratorio' / 'prueba.previo.medido.json').exists())
        cmp = L.comparar(L.leer(self.tmp, 'prueba', previo=True), L.leer(self.tmp, 'prueba'))
        self.assertEqual(cmp['nota'], 'versión 0.1.0 → 0.2.0')

    def test_lo_que_se_guarda_en_el_informe_no_trae_tiempos_de_reloj(self):
        r1, m1 = self.hacer('0.1.0')
        L.guardar(self.tmp, r1, m1)
        crudo = (pathlib.Path(self.tmp) / 'metricas' / 'laboratorio' / 'prueba.json').read_text(encoding='utf-8')
        for prohibido in ('carga_real_ms', 'ritmo_cpu', 'memoria_mb', 'pasada_max_ms'):
            self.assertNotIn(prohibido, crudo)
        self.assertTrue(crudo.endswith('\n'))


class Fabrica(unittest.TestCase):
    def correr(self, *args):
        return subprocess.run([sys.executable, '-I', str(RAIZ / 'fabrica.py'), 'laboratorio', *args], cwd=str(RAIZ), capture_output=True, text=True)

    def test_validar_todos_los_experimentos_y_listar_perfiles(self):
        r = self.correr('validar', 'todos')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('experimento válido', r.stdout)
        r = self.correr('perfiles')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('mama-ocupada', r.stdout)
        r = self.correr('listar')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('rebote-primer-minuto', r.stdout)

    def test_un_experimento_que_no_existe_o_un_subcomando_raro_avisan(self):
        self.assertNotEqual(self.correr('correr', 'no-existe').returncode, 0)
        self.assertNotEqual(self.correr('inventado').returncode, 0)
        self.assertNotEqual(self.correr('comparar').returncode, 0)


@unittest.skipUnless(_hay_navegador(), 'sin node y playwright no se puede probar el navegador')
class PuntaAPunta(unittest.TestCase):
    """Un Chromium real contra una página con problemas puestos a propósito: el laboratorio tiene que encontrarlos, ser reproducible y no dejar nada afuera."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        (cls.tmp / 'laboratorio' / 'experimentos').mkdir(parents=True)
        shutil.copy(RAIZ / 'laboratorio' / 'perfiles.json', cls.tmp / 'laboratorio' / 'perfiles.json')
        os.symlink(RAIZ / 'herramientas', cls.tmp / 'herramientas')
        shutil.copy(RAIZ / 'pruebas' / 'fixtures' / 'laboratorio' / 'pagina-con-problemas.html', cls.tmp / 'pagina.html')
        (cls.tmp / 'sana.html').write_text('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Sana</title></head><body>'
                                           '<h1>Hola</h1><button id="b" style="width:60px;height:60px">Ir</button><script>window.JUEGO={parametros:{vidas:3}};</script></body></html>', encoding='utf-8')
        exp = {
            'formato': 1, 'id': 'fixture', 'titulo': 'Fixture con problemas a propósito', 'pregunta': '¿El laboratorio detecta lo que le plantamos en la página?',
            'objeto': {'html': 'pagina.html'},
            'variantes': [{'id': 'con-problemas'}, {'id': 'cambiada', 'reemplazos': [{'buscar': 'Prueba del laboratorio', 'poner': 'Texto nuevo'}], 'juego': {'parametros': {'vidas': 5}}}],
            'perfiles': ['escritorio-rapido', 'mama-ocupada', 'teclado-solo',
                         {'id': 'conexion-lenta', 'dispositivo': {'ancho': 360, 'alto': 640, 'tactil': True, 'movil': True, 'escala': 2}, 'red': {'latencia_ms': 800, 'bajada_kbps': 100},
                          'conducta': {'paciencia_carga_ms': 600}}],
            'pruebas': [
                {'id': 'auditoria', 'tipo': 'auditoria', 'observar_ms': 300},
                {'id': 'flujo', 'tipo': 'guion', 'semillas': 3, 'pasos': [
                    {'esperar': '#empezar', 'embudo': 've-empezar'},
                    {'tocar': '#empezar'},
                    {'verificar': {'js': "window.estado() === 'listo'", 'mensaje': 'Empezar no cambió el estado', 'espera': 300}, 'embudo': 'empieza'},
                    {'leer': {'id': 'texto', 'js': "document.querySelector('h1').textContent"}},
                    {'leer': {'id': 'vidas', 'js': 'window.JUEGO.parametros.vidas'}},
                    {'tocar': '#empezar'},
                    {'tocar': '#tapado', 'embudo': 'toca-tapado'},
                ]},
            ],
        }
        (cls.tmp / 'laboratorio' / 'experimentos' / 'fixture.json').write_text(json.dumps(exp), encoding='utf-8')
        cls.rep, cls.medido, cls.lineas = L.correr(cls.tmp, 'fixture')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def grupo(self, v, p, prueba):
        return next(g for g in self.rep['grupos'] if (g['variante'], g['perfil'], g['prueba']) == (v, p, prueba))

    def banderas(self, codigo):
        return [b for b in self.rep['banderas'] if b['codigo'] == codigo]

    def test_encuentra_los_problemas_de_la_pagina(self):
        self.assertTrue(self.banderas('fallas-de-pagina'))
        self.assertIn('error de ejemplo', self.banderas('fallas-de-pagina')[0]['texto'])
        self.assertIn('no-existe.png', self.banderas('recurso-faltante')[0]['texto'])
        self.assertIn('example.com', self.banderas('red-externa')[0]['texto'])
        codigos = {b['codigo'] for b in self.rep['banderas']}
        for a in ('a11y-contraste-bajo', 'a11y-control-sin-nombre', 'a11y-idioma-falta', 'a11y-imagen-sin-alt', 'a11y-titulo-falta', 'a11y-viewport-falta', 'a11y-texto-chico', 'a11y-objetivo-chico', 'a11y-objetivo-chico-tactil'):
            self.assertIn(a, codigos)

    def test_una_persona_no_puede_tocar_lo_que_esta_tapado_y_el_teclado_no_puede_con_el_raton(self):
        g = self.grupo('con-problemas', 'escritorio-rapido', 'flujo')
        self.assertEqual((g['completaron'], g['abandonaron']), (0, 3))
        self.assertEqual(g['abandonos_en'], {'p7: cubierto': 3})
        self.assertEqual([e['etapa'] for e in g['embudo']], ['ve-empezar', 'empieza'])
        self.assertEqual(g['ejemplo_de_fallo']['abandono']['motivo'], 'cubierto')
        teclado = self.grupo('con-problemas', 'teclado-solo', 'flujo')
        self.assertEqual(teclado['abandonos_en'], {'p2: requiere-puntero': 3})
        self.assertEqual([e['etapa'] for e in teclado['embudo']], ['ve-empezar'])

    def test_la_carga_lenta_hace_que_se_rinda_quien_tiene_poca_paciencia(self):
        g = self.grupo('con-problemas', 'conexion-lenta', 'flujo')
        self.assertEqual(g['abandonos_en'], {'carga: carga-lenta': 3})
        self.assertTrue(self.banderas('carga-lenta'))
        self.assertGreater(g['carga_modelada_ms'], 600)

    def test_las_variantes_se_aplican_de_verdad(self):
        g = self.grupo('cambiada', 'escritorio-rapido', 'flujo')
        self.assertEqual(g['datos']['texto']['reparto'], {'Texto nuevo': 3})
        self.assertEqual(g['datos']['vidas']['p50'], 5)
        self.assertEqual(self.grupo('con-problemas', 'escritorio-rapido', 'flujo')['datos']['vidas']['p50'], 3)
        self.assertEqual(self.grupo('con-problemas', 'escritorio-rapido', 'flujo')['datos']['texto']['reparto'], {'Prueba del laboratorio': 3})

    def test_es_determinista_y_cada_sesion_empieza_limpia(self):
        self.assertFalse(self.banderas('no-determinista'))
        self.assertFalse(self.banderas('contexto-sucio'))
        self.assertFalse(self.banderas('error-interno'))
        for g in self.rep['grupos']:
            self.assertIn(g['determinista'], (True, None))

    def test_correr_dos_veces_da_el_mismo_informe(self):
        rep2, medido2, _ = L.correr(self.tmp, 'fixture', determinismo=True)
        self.assertEqual(self.rep['huella_resultado'], rep2['huella_resultado'])
        self.assertEqual(json.dumps(self.rep, sort_keys=True), json.dumps(rep2, sort_keys=True))
        self.assertTrue(self.medido['grupos'][0]['carga_real_ms']['n'] >= 1)

    def test_el_perfil_con_prisa_y_las_interrupciones_dejan_huella_en_la_traza(self):
        g = self.grupo('con-problemas', 'mama-ocupada', 'flujo')
        self.assertGreater(g['ms_simulados_p50'], 20000)       # la interrumpieron 20 s a media sesión
        self.assertEqual(self.grupo('con-problemas', 'escritorio-rapido', 'flujo')['ms_simulados_p50'] < 20000, True)

    def test_una_variante_que_no_se_aplica_se_denuncia(self):
        exp = json.loads((self.tmp / 'laboratorio' / 'experimentos' / 'fixture.json').read_text(encoding='utf-8'))
        exp['id'] = 'sin-juego'
        exp['objeto'] = {'html': 'sana.html'}
        exp['variantes'] = [{'id': 'a'}, {'id': 'b', 'juego': {'parametros': {'nada': 1}}}]
        exp['perfiles'] = ['escritorio-rapido']
        exp['pruebas'] = [{'id': 'flujo', 'tipo': 'guion', 'semillas': 1, 'pasos': [{'esperar': '#b'}]}]
        (self.tmp / 'laboratorio' / 'experimentos' / 'sin-juego.json').write_text(json.dumps(exp), encoding='utf-8')
        rep, _, _ = L.correr(self.tmp, 'sin-juego')
        self.assertEqual(rep['banderas'], [])                      # «nada» sí se mezcla en window.JUEGO.parametros: la variante se aplicó
        exp['variantes'][1] = {'id': 'b', 'juego': {'parametros': {'vidas': 9}}}
        exp['objeto'] = {'html': 'sana.html'}
        sana = (self.tmp / 'sana.html').read_text(encoding='utf-8')
        (self.tmp / 'otra.html').write_text(sana.replace('window.JUEGO={parametros:{vidas:3}};', ''), encoding='utf-8')
        exp['objeto'] = {'html': 'otra.html'}
        (self.tmp / 'laboratorio' / 'experimentos' / 'sin-juego.json').write_text(json.dumps(exp), encoding='utf-8')
        rep, _, _ = L.correr(self.tmp, 'sin-juego')
        malos = [b for b in rep['banderas'] if b['codigo'] == 'error-interno']
        self.assertTrue(malos)
        self.assertIn('no se aplicó', malos[0]['texto'])

    def test_un_reemplazo_que_no_encuentra_nada_se_rechaza_antes_de_correr(self):
        exp = json.loads((self.tmp / 'laboratorio' / 'experimentos' / 'fixture.json').read_text(encoding='utf-8'))
        exp['id'] = 'mal-reemplazo'
        exp['variantes'][1]['reemplazos'] = [{'buscar': 'esto no está', 'poner': 'x'}]
        (self.tmp / 'laboratorio' / 'experimentos' / 'mal-reemplazo.json').write_text(json.dumps(exp), encoding='utf-8')
        with self.assertRaises(L.ErrorLaboratorio) as cm:
            L.correr(self.tmp, 'mal-reemplazo')
        self.assertIn('no encuentra', str(cm.exception))


@unittest.skipUnless(_hay_navegador(), 'sin node y playwright no se puede probar el navegador')
class BotsEnElLaboratorio(unittest.TestCase):
    """Un experimento de verdad (Rebote) con la prueba de bots, en dos perfiles muy distintos y en pocas partidas."""

    def test_las_politicas_que_miden_el_juego_no_dependen_del_perfil(self):
        rep, _, _ = L.correr(RAIZ, 'rebote-primer-minuto', factor=0.1, solo_perfiles=['escritorio-rapido', 'mama-ocupada'], solo_pruebas=['partidas-bots'], determinismo=False)
        grupos = [g for g in rep['grupos'] if g['tipo'] == 'bots' and g['variante'] == 'actual']
        self.assertEqual({g['perfil'] for g in grupos}, {'escritorio-rapido', 'mama-ocupada'})
        a, b = grupos
        self.assertTrue(a['escenas'])
        for escena in a['escenas']:
            for politica in ('aleatorio', 'oraculo'):                       # la débil y la solucionadora: la misma cadencia con cualquier perfil
                self.assertEqual(a['escenas'][escena][politica], b['escenas'][escena][politica], '%s/%s' % (escena, politica))
            self.assertEqual(a['escenas'][escena]['oraculo']['tasa'], 1.0)
        self.assertTrue(all(g['determinista'] for g in grupos))
        self.assertFalse([x for x in rep['banderas'] if x['nivel'] == 'falla'])


if __name__ == '__main__':
    unittest.main()
