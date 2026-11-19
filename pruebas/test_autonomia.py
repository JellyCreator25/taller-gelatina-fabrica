"""Pruebas del objetivo secundario del motor, la autonomía: el inventario es coherente, lo «reducible» nunca se hace pasar por autorización,
solo lo construible sin Max entra a la cola del motor, los días aprobados se cuentan solo con lo vigente y el registro semanal no se duplica.
Ninguna toca la red ni abre un navegador.
Correr: python3 -I -m unittest discover -s pruebas   (desde la carpeta de la fábrica)"""
import copy
import datetime
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / 'herramientas'))

import autonomia  # noqa: E402
import motor  # noqa: E402

HOY = datetime.date(2026, 11, 18)


def linea(estado, fecha):
    return {'id': 'x-' + fecha, 'estado': estado, 'fecha': fecha}


class Inventario(unittest.TestCase):
    def setUp(self):
        self.cat = autonomia.catalogo(RAIZ)

    def test_el_inventario_real_es_coherente(self):
        self.assertEqual(autonomia.problemas_de_catalogo(self.cat), [])

    def test_cada_propuesta_autorizada_tiene_su_autorizacion_y_las_otras_no(self):
        por = {a['propuesta'] for a in self.cat['autorizaciones_vigentes'] if a.get('propuesta')}
        for x in self.cat['propuestas']:
            self.assertEqual(x['estado'] == 'autorizada', x['id'] in por, x['id'])
        for a in self.cat['autorizaciones_vigentes']:
            self.assertTrue(a['origen'] and a['fecha'], a['id'])

    def test_solo_estan_autorizadas_las_reglas_que_max_eligio(self):
        """Max eligió «Reserva perenne» y «Construir el siguiente juego» el 18 de noviembre de 2026; los lotes de cuatro semanas no."""
        estados = {x['id']: x['estado'] for x in self.cat['propuestas']}
        self.assertEqual(estados, {'lotes-de-4-semanas': 'propuesta', 'reserva-de-contenido-perenne': 'autorizada', 'construir-el-siguiente-recomendado': 'autorizada'})

    def test_una_propuesta_que_se_hace_pasar_por_autorizacion_se_nota(self):
        cat = copy.deepcopy(self.cat)
        cat['propuestas'][0]['estado'] = 'autorizada'      # sin autorización registrada
        cat['autorizaciones_vigentes'].append({'id': 'x', 'propuesta': 'no-existe', 'fecha': '2026-11', 'texto': 'x', 'origen': 'y'})
        malos = ' | '.join(autonomia.problemas_de_catalogo(cat))
        self.assertIn('figura como autorizada pero no hay una autorización suya', malos)
        self.assertIn('que no existe', malos)
        cat = copy.deepcopy(self.cat)
        cat['autorizaciones_vigentes'].append({'id': 'y', 'propuesta': 'lotes-de-4-semanas', 'fecha': '2026-11', 'texto': 'x', 'origen': 'y'})
        self.assertIn('ya tiene una autorización pero sigue como «propuesta»', ' | '.join(autonomia.problemas_de_catalogo(cat)))
        cat = copy.deepcopy(self.cat)
        cat['propuestas'][0]['estado'] = 'quizá'
        self.assertIn('«propuesta» o «autorizada»', ' | '.join(autonomia.problemas_de_catalogo(cat)))

    def test_un_paso_reducible_solo_se_resuelve_si_max_autorizo_su_regla(self):
        cat = copy.deepcopy(self.cat)
        p = {x['id']: x for x in cat['pasos']}
        p['d-aprobar-lote']['estado'] = 'resuelta'            # su regla «reserva perenne» sí está autorizada
        p['d-aprobar-lote']['resuelta_por'] = 'prueba'
        self.assertEqual(autonomia.problemas_de_catalogo(cat), [])
        p['d-aprobar-lote']['regla'] = ['lotes-de-4-semanas']   # esta no
        self.assertIn('solo queda «resuelta» si Max autorizó', ' | '.join(autonomia.problemas_de_catalogo(cat)))

    def test_los_errores_del_inventario_se_notan(self):
        cat = copy.deepcopy(self.cat)
        p = {x['id']: x for x in cat['pasos']}
        p['d-aprobar-lote']['regla'] = ['no-existe']
        p['d-aprobar-lanzamiento']['ancla'] = 'inventado'
        p['d-resolver-envio-incierto']['veces_con_regla'] = 9
        del p['d-reactivar-flujos']['construible']
        p['f-ciclo-semanal']['requiere'] = ['a-estado']
        p['u-impi']['por_que'] = ''
        del p['a-informe']['donde']
        cat['pasos'].append(dict(p['a-informe'], id='d-aprobar-lote'))
        malos = ' | '.join(autonomia.problemas_de_catalogo(cat))
        for esperado in ('«regla» debe nombrar propuestas que existan', 'se ancla en uno de los límites', 'no puede ser mayor', '«construible»',
                         'solo se puede requerir un paso del dueño', 'dice por qué es suyo', 'falta «donde»', 'id» único'):
            self.assertIn(esperado, malos)

    def test_lo_obligatorio_no_se_puede_volver_automatizable_sin_decirlo(self):
        """Los límites de la política están anclados: ninguna obligación queda sin un límite que la respalde."""
        for x in self.cat['pasos']:
            if x['quien'] == 'dueno' and x['clase'] == 'obligatoria':
                self.assertIn(x['ancla'], self.cat['limites'], x['id'])

    def test_los_limites_que_no_cambian_estan_todos(self):
        for clave in ('cuentas-y-pagos', 'secretos', 'huella', 'juegos-publicados', 'politica', 'sin-interaccion', 'ia', 'borrado', 'monetizacion', 'legal'):
            self.assertIn(clave, self.cat['limites'])


class Medicion(unittest.TestCase):
    def setUp(self):
        self.cat = autonomia.catalogo(RAIZ)

    def test_los_numeros_salen_del_inventario(self):
        m = autonomia.medir(self.cat)
        recurrentes = [x for x in self.cat['pasos'] if x['quien'] == 'dueno' and x['estado'] == 'abierta' and x['frecuencia'] != 'una-vez']
        self.assertAlmostEqual(m['toques_mes'], sum(x['veces_por_mes'] for x in recurrentes), places=2)
        self.assertLess(m['toques_con_reglas_mes'], m['toques_mes'])
        self.assertLessEqual(m['toques_evitables_mes'], m['toques_mes'])
        self.assertEqual(m['pasos_totales'], len([x for x in self.cat['pasos'] if x['quien'] != 'dueno']) + len(recurrentes))
        self.assertIn('f-metricas-cloudflare', m['detenidos_por_dueno'])
        self.assertEqual(m['detenidos_por_dueno']['f-reserva-perenne'], ['u-aprobar-reserva'], 'la reserva perenne solo corre sola cuando Max la apruebe')

    def test_resolver_lo_que_falta_del_dueno_pone_a_correr_el_paso(self):
        antes = autonomia.medir(self.cat)
        cat = copy.deepcopy(self.cat)
        for x in cat['pasos']:
            if x['id'] in ('u-token-analitica', 'u-desplegar-sitio'):
                x['estado'] = 'resuelta'
        despues = autonomia.medir(cat)
        self.assertEqual(despues['pasos_autonomos'], antes['pasos_autonomos'] + 1)
        self.assertNotIn('f-metricas-cloudflare', despues['detenidos_por_dueno'])

    def test_automatizar_un_paso_baja_los_toques(self):
        """El paso «d-resolver-envio-incierto» ya se automatizó (19 de noviembre de 2026): se reabre en una copia y se vuelve a cerrar."""
        abierto = copy.deepcopy(self.cat)
        for x in abierto['pasos']:
            if x['id'] == 'd-resolver-envio-incierto':
                x['estado'] = 'abierta'
                x.pop('resuelta_por')
        self.assertEqual(autonomia.problemas_de_catalogo(abierto), [])
        self.assertLess(autonomia.medir(self.cat)['toques_mes'], autonomia.medir(abierto)['toques_mes'])

    def test_un_paso_resuelto_dice_como_y_cuando(self):
        cat = copy.deepcopy(self.cat)
        for x in cat['pasos']:
            if x['id'] == 'u-desplegar-sitio':
                x.pop('resuelta_por')
        self.assertIn('u-desplegar-sitio: un paso «resuelta» dice cómo y cuándo', ' | '.join(autonomia.problemas_de_catalogo(cat)))

    def test_lo_que_el_inventario_dice_que_corre_solo_existe(self):
        for x in self.cat['pasos']:
            if x['quien'] == 'fabrica' and str(x.get('donde', '')).startswith('.github/workflows/'):
                self.assertTrue((RAIZ / x['donde'].split(' ')[0]).exists(), '%s: %s' % (x['id'], x['donde']))

    def test_aclarar_envios_en_duda_corre_cada_dia_antes_del_calendario_sin_claves_ni_publicar(self):
        """La comprobación vive en su propio flujo: los que publican (calendario.yml, publicar.yml) son de Max y no se tocan."""
        paso = next(x for x in self.cat['pasos'] if x['id'] == 'f-resolver-envio-incierto')
        flujo = (RAIZ / '.github' / 'workflows' / 'comprobar.yml').read_text(encoding='utf-8')
        cal = (RAIZ / '.github' / 'workflows' / 'calendario.yml').read_text(encoding='utf-8')
        self.assertIn('resolver --auto', flujo)
        self.assertIn('resolver --verificar', flujo, 'la corrida manual «verificar» no anota nada')
        self.assertIn('comprobar.yml', paso['donde'])
        self.assertNotIn('secrets.', flujo, 'solo lee la cuenta pública: no recibe ninguna clave')
        self.assertNotIn('environment:', flujo.replace('«environment»', ''), 'sin el entorno de producción no ve las claves')
        self.assertNotIn('--ejecutar', flujo, 'no publica nada')
        self.assertNotIn('resolver', cal, 'el flujo del calendario no cambió')
        grupo = 'group: publicar'
        self.assertIn(grupo, flujo)
        self.assertIn(grupo, cal, 'comparten grupo: nunca escriben el libro a la vez')
        hora = lambda t: int(re.search(r"cron: '(\d+) (\d+) ", t).group(2)) * 60 + int(re.search(r"cron: '(\d+) (\d+) ", t).group(1))
        self.assertLess(hora(flujo), hora(cal), 'primero se aclara la duda, después corre el calendario')

    def test_el_latido_de_los_flujos_esta_en_el_inventario_en_la_carta_y_en_los_avisos(self):
        paso = next(x for x in self.cat['pasos'] if x['id'] == 'a-reactivar-flujos')
        self.assertIn('administrador flujos --reactivar', paso['donde'])
        self.assertIn('Mantener el latido', (RAIZ / 'motor' / 'ADMINISTRADOR.md').read_text(encoding='utf-8'))      # la carta (de Max) ya lo manda
        self.assertIn('flujos --reactivar', (RAIZ / 'herramientas' / 'administrador.py').read_text(encoding='utf-8'))

    def test_dias_aprobados_solo_cuenta_lo_vigente(self):
        lineas = [linea('hecha', '2026-11-18'), linea('lista', '2026-11-19'), linea('aún no es su fecha', '2026-11-25'),
                  linea('sin aprobar', '2026-12-20'), linea('cambió tras aprobar', '2026-12-25'), linea('vencida', '2026-12-30')]
        self.assertEqual(autonomia.dias_aprobados(lineas, HOY), (7, datetime.date(2026, 11, 25)))

    def test_la_reserva_perenne_aprobada_llena_los_dias_sin_nada(self):
        reserva = [dict(linea('en reserva', '2026-01-01'), perenne=True, fecha=None) for _ in range(3)]
        solo = autonomia.dias_aprobados(reserva, HOY)
        self.assertEqual(solo, (2, datetime.date(2026, 11, 20)), 'tres perennes son tres días: hoy, mañana y pasado')
        mezcla = [linea('lista', '2026-11-19'), linea('aún no es su fecha', '2026-11-25')] + reserva
        self.assertEqual(autonomia.dias_aprobados(mezcla, HOY), (7, datetime.date(2026, 11, 25)), 'la reserva ocupa los huecos y no estira el calendario')
        con_mas = mezcla + [dict(linea('en reserva', '2026-01-01'), perenne=True, fecha=None) for _ in range(5)]
        self.assertEqual(autonomia.dias_aprobados(con_mas, HOY), (9, datetime.date(2026, 11, 27)), 'lo que sobra de la reserva sigue después de la última con fecha')
        sin_aprobar = [dict(linea('sin aprobar', '2026-01-01'), perenne=True, fecha=None)]
        self.assertEqual(autonomia.dias_aprobados(sin_aprobar, HOY), (0, None))

    def test_sin_nada_aprobado_la_fabrica_se_detiene(self):
        self.assertEqual(autonomia.dias_aprobados([], HOY), (0, None))
        self.assertEqual(autonomia.dias_aprobados([linea('sin aprobar', '2026-12-01')], HOY), (0, None))
        self.assertEqual(autonomia.dias_aprobados([linea('hecha', '2026-11-10')], HOY), (0, None))


class ColaDelMotor(unittest.TestCase):
    def test_solo_entra_lo_que_se_puede_construir_sin_max(self):
        cat = autonomia.catalogo(RAIZ)
        titulos = [i['titulo'] for i in autonomia.cola_items(RAIZ)]
        for x in cat['pasos']:
            if x['quien'] != 'dueno':
                continue
            en_cola = ('Automatizar: ' + x['titulo']) in titulos
            esperado = x['clase'] == 'automatizable' and x['estado'] == 'abierta' and bool(x.get('construible'))
            self.assertEqual(en_cola, esperado, x['id'])

    def test_un_paso_nuevo_automatizable_y_construible_entra_a_la_cola(self):
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / 'motor').mkdir()
            cat = autonomia.catalogo(RAIZ)
            cat['pasos'].append({'id': 'd-nuevo', 'quien': 'dueno', 'titulo': 'Algo repetitivo', 'frecuencia': 'eventual', 'clase': 'automatizable', 'estado': 'abierta',
                                 'veces_por_mes': 1, 'veces_con_regla': 0, 'construible': True, 'por_que': 'x', 'como_se_reduce': 'un comando'})
            (pathlib.Path(tmp) / 'motor' / 'autonomia.json').write_text(json.dumps(cat), encoding='utf-8')
            self.assertEqual([i['titulo'] for i in autonomia.cola_items(tmp)], ['Automatizar: Algo repetitivo'])
            cat['pasos'][-1]['construible'] = False
            (pathlib.Path(tmp) / 'motor' / 'autonomia.json').write_text(json.dumps(cat), encoding='utf-8')
            self.assertEqual(autonomia.cola_items(tmp), [], 'lo que no se puede construir sin Max no entra')

    def test_lo_reducible_nunca_entra_a_la_cola(self):
        for x in autonomia.catalogo(RAIZ)['pasos']:
            if x['quien'] == 'dueno' and x['clase'] == 'reducible':
                self.assertNotIn('Automatizar: ' + x['titulo'], [i['titulo'] for i in autonomia.cola_items(RAIZ)])

    def test_la_cola_del_motor_la_incluye_despues_de_la_calidad(self):
        piso = json.loads((RAIZ / 'motor' / 'piso.json').read_text(encoding='utf-8'))
        entradas = [{'juego': j, 'lanzamiento': True, 'resultado': 'ok'} for j in piso.get('lanzados', [])] or []
        juegos = [json.loads((RAIZ / 'juegos' / d.name / 'juego.json').read_text(encoding='utf-8')) for d in sorted((RAIZ / 'juegos').iterdir()) if (d / 'juego.json').exists()]
        sola = motor.cola(RAIZ, entradas, juegos)
        pendiente = {'prioridad': 3, 'tipo': 'autonomia', 'titulo': 'Automatizar: algo que hoy hace Max', 'por_que': 'x'}
        with mock.patch.object(autonomia, 'cola_items', return_value=[pendiente]):        # hoy ya no queda nada automatizable abierto: se simula uno
            con = motor.cola_con_autonomia(RAIZ, entradas, juegos)
        self.assertFalse([i for i in sola if i['tipo'] == 'autonomia'], 'la cola de calidad no cambia')
        extra = [i for i in con if i['tipo'] == 'autonomia']
        self.assertTrue(extra)
        indices = [con.index(i) for i in extra]
        for i in sola:
            if i['prioridad'] < 3:
                self.assertLess(con.index(i), min(indices), 'la calidad va antes que la autonomía: es el objetivo secundario')

    def test_sin_inventario_la_cola_es_la_de_siempre(self):
        with tempfile.TemporaryDirectory() as tmp:
            for carpeta in ('motor', 'juegos', 'plantillas', 'herramientas', 'catalogo'):
                shutil.copytree(RAIZ / carpeta, pathlib.Path(tmp) / carpeta, ignore=shutil.ignore_patterns('__pycache__'))
            (pathlib.Path(tmp) / 'motor' / 'autonomia.json').unlink()
            self.assertFalse([i for i in motor.cola_con_autonomia(tmp, [], []) if i['tipo'] == 'autonomia'])


class RegistroSemanal(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='autonomia-test-'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.m = autonomia.medir(autonomia.catalogo(RAIZ))

    def test_correr_dos_veces_en_la_misma_semana_no_duplica(self):
        autonomia.registrar(self.tmp, HOY, self.m, 12)
        autonomia.registrar(self.tmp, HOY + datetime.timedelta(days=1), self.m, 11)
        filas = autonomia.historial(self.tmp)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]['semana'], '2026-W47')
        self.assertEqual(filas[0]['dias_aprobados'], '11')

    def test_las_semanas_quedan_en_orden(self):
        autonomia.registrar(self.tmp, HOY + datetime.timedelta(days=7), self.m, 5)
        autonomia.registrar(self.tmp, HOY, self.m, 12)
        self.assertEqual([r['semana'] for r in autonomia.historial(self.tmp)], ['2026-W47', '2026-W48'])

    def test_avisa_si_la_fabrica_empieza_a_pedir_mas(self):
        autonomia.registrar(self.tmp, HOY, self.m, 12)
        peor = dict(self.m, toques_mes=self.m['toques_mes'] + 1, pasos_autonomos=self.m['pasos_autonomos'] - 1)
        avisos = ' | '.join(autonomia.avisos(self.tmp, HOY + datetime.timedelta(days=7), peor))
        self.assertIn('subieron', avisos)
        self.assertIn('Bajaron los pasos', avisos)
        self.assertEqual(autonomia.avisos(self.tmp, HOY + datetime.timedelta(days=7), self.m), [])

    def test_sin_historial_no_hay_avisos(self):
        self.assertEqual(autonomia.avisos(self.tmp, HOY, self.m), [])


class Informe(unittest.TestCase):
    def test_el_informe_dice_lo_esencial(self):
        lineas = [linea('lista', '2026-11-19'), linea('aún no es su fecha', '2026-11-30'), linea('sin aprobar', '2026-12-05')]
        texto = '\n'.join(autonomia.informe(RAIZ, HOY, lineas, [('guerreros-gelatina', 'abc123')]))
        for esperado in ('hasta el 2026-11-30 (12 días)', 'Esperan su aprobación 1 publicación', '«guerreros-gelatina» (huella abc123)', 'no están autorizadas'.replace('no están', 'NO están'),
                         'Lo que solo Max puede hacer', 'Límites que no cambian', 'estimado del inventario, no medido'):
            self.assertIn(esperado, texto)

    def test_la_version_corta_remite_al_detalle(self):
        texto = '\n'.join(autonomia.informe(RAIZ, HOY, [], [], completo=False))
        self.assertIn('python3 fabrica.py autonomia', texto)
        self.assertNotIn('Límites que no cambian', texto)
        self.assertIn('nada. El calendario está detenido', texto)

    def test_el_comando_revisa_el_inventario_real(self):
        r = subprocess.run([sys.executable, '-I', str(RAIZ / 'fabrica.py'), 'autonomia', 'revisar'], capture_output=True, text=True, cwd=str(RAIZ))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('inventario en orden', r.stdout)


if __name__ == '__main__':
    unittest.main()
