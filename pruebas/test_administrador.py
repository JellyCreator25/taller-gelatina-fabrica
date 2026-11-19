"""Pruebas del administrador del motor: el chequeo avisa lo que debe avisar y resuelve lo que puede, la bitácora solo agrega,
la guardia detecta cuando el administrador toca algo que su carta le prohíbe y la carta nombra todos los límites.
Ninguna toca la red ni abre un navegador.
Correr: python3 -I -m unittest discover -s pruebas   (desde la carpeta de la fábrica)"""
import datetime
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / 'herramientas'))

import administrador  # noqa: E402
import autonomia  # noqa: E402
import motor  # noqa: E402

HOY = datetime.date(2026, 11, 18)


def linea(estado, fecha, id_=None):
    return {'id': id_ or 'x-' + fecha, 'estado': estado, 'fecha': fecha}


def ids(hallazgos, nivel=None):
    return [h['id'] for h in hallazgos if nivel in (None, h['nivel'])]


class Chequeo(unittest.TestCase):
    def chequeo(self, lineas=None, entradas=None):
        return administrador.chequeo(RAIZ, HOY, lineas, entradas or [])

    def test_con_el_calendario_al_dia_no_hay_nada_que_avisar(self):
        h = self.chequeo([linea('lista', '2026-11-18'), linea('aún no es su fecha', '2026-12-10')])
        self.assertEqual(ids(h, 'avisar'), [])
        self.assertNotIn('inventario-roto', ids(h))

    def test_el_calendario_detenido_se_avisa_y_dice_que_hacer(self):
        h = self.chequeo([linea('hecha', '2026-11-10')])
        malo = [x for x in h if x['id'] == 'calendario-detenido'][0]
        self.assertEqual(malo['nivel'], 'avisar')
        self.assertIn('preparar un lote nuevo', malo['accion'])
        h = self.chequeo([linea('sin aprobar', '2026-11-20')])
        self.assertIn('apruebe el lote pendiente', [x for x in h if x['id'] == 'calendario-detenido'][0]['accion'])

    def test_algo_que_sale_hoy_no_es_un_calendario_detenido(self):
        h = self.chequeo([linea('lista', '2026-11-18')])
        self.assertNotIn('calendario-detenido', ids(h))
        self.assertIn('calendario-por-agotarse', ids(h, 'avisar'))

    def test_la_reserva_perenne_autorizada_pero_vacia_o_baja_se_anota(self):
        perenne = lambda estado: dict(linea(estado, '2026-01-01'), perenne=True, fecha=None)
        con_fecha = [linea('aún no es su fecha', '2026-12-30')]
        h = self.chequeo(con_fecha)
        self.assertIn('reserva-vacia', ids(h, 'info'))
        self.assertIn('la rutina de los lunes la prepare', [x for x in h if x['id'] == 'reserva-vacia'][0]['accion'])
        h = self.chequeo(con_fecha + [perenne('sin aprobar')])
        self.assertIn('que Max apruebe la reserva', [x for x in h if x['id'] == 'reserva-vacia'][0]['accion'])
        h = self.chequeo(con_fecha + [perenne('en reserva') for _ in range(2)])
        self.assertIn('reserva-baja', ids(h, 'info'))
        h = self.chequeo(con_fecha + [perenne('en reserva') for _ in range(administrador.RESERVA_MINIMA)])
        self.assertFalse([x for x in ids(h) if x.startswith('reserva-')])

    def test_quedar_con_pocos_dias_avisa_y_con_una_semana_solo_informa(self):
        self.assertIn('calendario-por-agotarse', ids(self.chequeo([linea('aún no es su fecha', '2026-11-20')]), 'avisar'))
        h = self.chequeo([linea('aún no es su fecha', '2026-11-24')])
        self.assertIn('lote-por-preparar', ids(h, 'info'))
        self.assertFalse([x for x in ids(h, 'avisar') if x.startswith('calendario')])

    def test_un_lote_esperando_a_max_no_se_vuelve_urgente_si_sobran_dias(self):
        h = self.chequeo([linea('aún no es su fecha', '2026-12-10'), linea('sin aprobar', '2026-12-12')])
        self.assertIn('lote-esperando', ids(h, 'info'))
        self.assertEqual([x for x in ids(h, 'avisar') if x.startswith('calendario')], [])

    def test_una_publicacion_vencida_o_con_problemas_se_avisa(self):
        h = self.chequeo([linea('lista', '2026-11-30'), linea('vencida', '2026-11-10', 'a'), linea('con problemas', '2026-11-12', 'b'), linea('en duda', '2026-11-13', 'c')])
        for esperado in ('calendario-vencida', 'calendario-con-problemas', 'calendario-en-duda'):
            self.assertIn(esperado, ids(h, 'avisar'))

    def test_un_envio_en_duda_se_avisa_hasta_que_se_resuelve(self):
        duda = [{'accion': 'a1', 'resultado': 'incierto', 'ts': '2026-11-17T10:00:00Z'}]
        self.assertEqual(administrador.en_duda(duda), ['a1'])
        self.assertIn('envio-en-duda', ids(self.chequeo(entradas=duda), 'avisar'))
        resuelto = duda + [{'accion': 'a1', 'resultado': 'ok', 'ts': '2026-11-17T12:00:00Z'}]
        self.assertEqual(administrador.en_duda(resuelto), [])
        self.assertNotIn('envio-en-duda', ids(self.chequeo(entradas=resuelto)))

    def test_una_falla_reciente_se_avisa_y_una_vieja_o_ya_resuelta_no(self):
        falla = {'accion': 'a2', 'resultado': 'fallo', 'ts': '2026-11-17T10:00:00Z'}
        self.assertEqual(administrador.fallas_recientes([falla], HOY), ['a2'])
        self.assertEqual(administrador.fallas_recientes([dict(falla, ts='2026-11-01T10:00:00Z')], HOY), [])
        self.assertEqual(administrador.fallas_recientes([falla, {'accion': 'a2', 'resultado': 'ok', 'ts': '2026-11-17T11:00:00Z'}], HOY), [])
        self.assertEqual(administrador.fallas_recientes([dict(falla, ts='sin fecha')], HOY), ['a2'], 'sin fecha legible se prefiere avisar de más')

    def test_las_pruebas_vencidas_las_resuelve_el_administrador(self):
        with mock.patch.object(motor, 'informe_vigente', return_value=(False, 'el motor cambió')):
            h = self.chequeo()
        x = [y for y in h if y['id'] == 'pruebas-vencidas'][0]
        self.assertEqual(x['nivel'], 'resolver')
        self.assertIn('motor probar', x['accion'])

    def test_lo_automatizable_pendiente_es_trabajo_del_administrador(self):
        pendiente = {'prioridad': 3, 'tipo': 'autonomia', 'titulo': 'Automatizar: algo que hoy hace Max', 'por_que': 'x'}
        with mock.patch.object(autonomia, 'cola_items', return_value=[pendiente]):         # hoy no queda ningún paso abierto: se simula uno
            x = [y for y in self.chequeo() if y['id'] == 'autonomia-por-construir']
        self.assertEqual(len(x), 1)
        self.assertEqual(x[0]['nivel'], 'resolver')
        self.assertIn('algo que hoy hace Max', x[0]['texto'])

    def test_sin_pasos_automatizables_abiertos_el_administrador_no_inventa_trabajo(self):
        with mock.patch.object(autonomia, 'cola_items', return_value=[]):
            self.assertEqual([y for y in self.chequeo() if y['id'] == 'autonomia-por-construir'], [])

    def test_un_inventario_roto_se_nota(self):
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / 'motor').mkdir()
            cat = json.loads((RAIZ / 'motor' / 'autonomia.json').read_text(encoding='utf-8'))
            cat['pasos'][0]['quien'] = 'nadie'
            (pathlib.Path(tmp) / 'motor' / 'autonomia.json').write_text(json.dumps(cat), encoding='utf-8')
            self.assertIn('inventario-roto', ids(administrador.chequeo(tmp, HOY, None, [])))
            (pathlib.Path(tmp) / 'motor' / 'autonomia.json').unlink()
            self.assertIn('inventario-falta', ids(administrador.chequeo(tmp, HOY, None, [])))

    def test_un_ciclo_semanal_parado_se_avisa(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(RAIZ / 'motor', pathlib.Path(tmp) / 'motor', ignore=shutil.ignore_patterns('__pycache__'))
            m = autonomia.medir(autonomia.catalogo(tmp))
            autonomia.registrar(tmp, datetime.date(2026, 10, 12), m, 5)
            self.assertIn('ciclo-semanal-parado', ids(administrador.chequeo(tmp, HOY, None, []), 'avisar'))
            autonomia.registrar(tmp, datetime.date(2026, 11, 16), m, 5)
            self.assertNotIn('ciclo-semanal-parado', ids(administrador.chequeo(tmp, HOY, None, [])))

    def test_el_orden_es_avisar_resolver_info(self):
        h = self.chequeo([linea('hecha', '2026-11-10')], [{'accion': 'a1', 'resultado': 'incierto', 'ts': '2026-11-17T10:00:00Z'}])
        orden = [administrador.NIVELES.index(x['nivel']) for x in h]
        self.assertEqual(orden, sorted(orden))

    def test_el_resumen_agrupa_y_dice_cuando_todo_esta_en_orden(self):
        self.assertEqual(administrador.resumen([]), ['Todo en orden: nada que arreglar ni que avisar.'])
        pendiente = {'prioridad': 3, 'tipo': 'autonomia', 'titulo': 'Automatizar: algo que hoy hace Max', 'por_que': 'x'}
        with mock.patch.object(autonomia, 'cola_items', return_value=[pendiente]):
            texto = '\n'.join(administrador.resumen(self.chequeo([linea('hecha', '2026-11-10')])))
        self.assertIn('Para avisar a Max', texto)
        self.assertIn('Para resolver sin Max', texto)
        self.assertIn('Solo para saber', texto)


class Bitacora(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='bitacora-test-'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_solo_agrega_y_conserva_lo_anterior(self):
        administrador.anotar(self.tmp, HOY, 'primera', 'hecho', 'abc1234')
        antes = (self.tmp / 'motor' / 'bitacora.jsonl').read_text(encoding='utf-8')
        administrador.anotar(self.tmp, HOY, 'segunda  con   espacios', 'nada-que-hacer')
        despues = (self.tmp / 'motor' / 'bitacora.jsonl').read_text(encoding='utf-8')
        self.assertTrue(despues.startswith(antes))
        filas = administrador.bitacora(self.tmp)
        self.assertEqual([f['que'] for f in filas], ['primera', 'segunda con espacios'])
        self.assertEqual(filas[0]['commit'], 'abc1234')
        self.assertNotIn('commit', filas[1])
        self.assertEqual(administrador.ultimas(self.tmp, 1)[0]['que'], 'segunda con espacios')

    def test_rechaza_resultados_raros_y_notas_vacias_o_enormes(self):
        for resultado, texto in (('listo', 'x'), ('hecho', ''), ('hecho', '   '), ('hecho', 'x' * (administrador.MAX_TEXTO + 1))):
            with self.assertRaises(administrador.ErrorAdministrador):
                administrador.anotar(self.tmp, HOY, texto, resultado)
        self.assertEqual(administrador.bitacora(self.tmp), [])

    def test_la_bitacora_real_es_json_valido_por_linea(self):
        for f in administrador.bitacora(RAIZ):
            self.assertIn(f['resultado'], ('hecho', 'no-se-pudo', 'avisado', 'nada-que-hacer'))
            self.assertTrue(f['fecha'] and f['que'])


class Guardia(unittest.TestCase):
    """Un repositorio de juguete con commits firmados por el administrador y por otro."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='guardia-test-'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.git('init', '-q')

    def git(self, *args):
        r = subprocess.run(['git', '-C', str(self.tmp), '-c', 'user.name=x', '-c', 'user.email=x@example.com', '-c', 'commit.gpgsign=false'] + list(args), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def commit(self, autor, *rutas):
        for r in rutas:
            f = self.tmp / r
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(f.read_text(encoding='utf-8') + 'x\n' if f.exists() else 'x\n', encoding='utf-8')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'cambio', '--author=%s <%s@users.noreply.github.com>' % (autor, autor))

    def malas(self, libro=None):
        return administrador.violaciones(administrador.cambios_del_administrador(self.tmp), libro or [])

    def test_lo_permitido_pasa(self):
        self.commit(administrador.IDENTIDAD, 'herramientas/x.py', 'motor/autonomia.json', 'motor/bitacora.jsonl', 'pruebas/test_x.py')
        self.assertEqual(self.malas(), [])

    def test_tocar_una_ruta_protegida_se_detecta(self):
        for ruta in administrador.RUTAS_PROTEGIDAS:
            self.commit(administrador.IDENTIDAD, ruta)
        rutas = {m[1] for m in self.malas()}
        self.assertEqual(rutas, set(administrador.RUTAS_PROTEGIDAS))

    def test_los_cambios_de_otros_no_cuentan(self):
        self.commit('fabrica-de-juegos', 'contenido/aprobaciones.json', 'publicacion/politica.json')
        self.assertEqual(self.malas(), [])

    def test_un_juego_publicado_esta_protegido_y_uno_sin_publicar_no(self):
        libro = [{'juego': 'guerreros-gelatina', 'lanzamiento': True, 'resultado': 'ok', 'tipo': 'desplegar'}]
        self.commit(administrador.IDENTIDAD, 'salida/guerreros-gelatina/index.html', 'juegos/guerreros-gelatina/juego.json', 'salida/compas-gelatina/index.html', 'juegos/compas-gelatina/juego.json')
        rutas = sorted(m[1] for m in self.malas(libro))
        self.assertEqual(rutas, ['juegos/guerreros-gelatina/juego.json', 'salida/guerreros-gelatina/index.html'])
        self.assertEqual(self.malas([]), [], 'sin lanzamiento en el libro, nada está publicado todavía')

    def test_el_comando_corre_sobre_el_repositorio_real(self):
        r = subprocess.run([sys.executable, '-I', str(RAIZ / 'fabrica.py'), 'administrador', 'guardia'], capture_output=True, text=True, cwd=str(RAIZ))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('guardia en orden', r.stdout)


class Carta(unittest.TestCase):
    def setUp(self):
        self.carta = (RAIZ / 'motor' / 'ADMINISTRADOR.md').read_text(encoding='utf-8')

    def test_nombra_cada_limite_del_inventario(self):
        for clave in autonomia.catalogo(RAIZ)['limites']:
            self.assertIn('`%s`' % clave, self.carta, 'la carta debe nombrar el límite «%s»' % clave)

    def test_nombra_lo_que_tiene_prohibido_tocar_y_su_firma(self):
        for ruta in administrador.RUTAS_PROTEGIDAS:
            if ruta not in ('publicacion/libro.jsonl', 'motor/ggx.js', 'motor/ADMINISTRADOR.md'):      # el libro y el núcleo se describen con palabras; la carta no se nombra a sí misma
                self.assertTrue(ruta in self.carta or ruta.split('/')[-1] in self.carta, ruta)
        self.assertIn('contenido/aprobaciones.json', self.carta)
        self.assertIn(administrador.IDENTIDAD, self.carta)
        self.assertIn('Solo Max la cambia', self.carta)

    def test_el_orden_de_la_corrida_no_manda_mensaje_si_no_hay_nada(self):
        self.assertIn('Una corrida sin hallazgos no manda nada', self.carta)


class GhFalso:
    """`gh` simulado: responde a la lista de flujos y a «enable», y guarda cada llamada. Los flujos que se reactivan pasan a «active»."""

    def __init__(self, flujos, falla_al_listar=False, falla_enable=(), enable_no_surte_efecto=()):
        self.flujos = [dict(f) for f in flujos]
        self.llamadas = []
        self.falla_al_listar = falla_al_listar
        self.falla_enable = set(falla_enable)
        self.no_surte = set(enable_no_surte_efecto)

    def __call__(self, argv):
        self.llamadas.append(list(argv))
        if argv[:2] == ['api', 'repos/o/r/actions/workflows?per_page=100']:
            if self.falla_al_listar:
                return 1, '', 'HTTP 403'
            return 0, json.dumps({'total_count': len(self.flujos), 'workflows': self.flujos}), ''
        if argv[:3] == ['api', '-X', 'PUT'] and argv[3].endswith('/enable'):
            ident = int(argv[3].split('/')[-2])
            if ident in self.falla_enable:
                return 1, '', 'HTTP 422'
            if ident not in self.no_surte:
                for f in self.flujos:
                    if f['id'] == ident:
                        f['state'] = 'active'
            return 0, '', ''
        raise AssertionError('llamada a gh no prevista: %r' % (argv,))

    def puts(self):
        return [a for a in self.llamadas if a[:3] == ['api', '-X', 'PUT']]


def wf(ident, nombre, estado):
    return {'id': ident, 'name': nombre, 'path': '.github/workflows/%s.yml' % nombre.lower(), 'state': estado}


class Flujos(unittest.TestCase):
    """GitHub apaga los flujos programados de un repositorio sin actividad. El administrador los vuelve a encender, y solo esos."""

    def revisar(self, gh, reactivar=False):
        return administrador.revisar_flujos(gh, 'o/r', reactivar)

    def resultados(self, informe):
        return {r['nombre']: r['resultado'] for r in informe}

    def test_sin_pedir_reactivar_solo_mira(self):
        gh = GhFalso([wf(1, 'Calendario', 'active'), wf(2, 'Ciclo', 'disabled_inactivity')])
        r = self.resultados(self.revisar(gh))
        self.assertEqual(r, {'Calendario': 'activo', 'Ciclo': 'apagado-por-inactividad'})
        self.assertEqual(gh.puts(), [])

    def test_reactiva_solo_lo_que_github_apago_por_inactividad(self):
        gh = GhFalso([wf(1, 'Calendario', 'disabled_inactivity'), wf(2, 'Ciclo', 'disabled_manually'), wf(3, 'Pruebas', 'active'), wf(4, 'Viejo', 'deleted')])
        r = self.resultados(self.revisar(gh, True))
        self.assertEqual(r, {'Calendario': 'reactivado', 'Ciclo': 'apagado-a-mano', 'Pruebas': 'activo'})      # el borrado ni aparece
        self.assertEqual(gh.puts(), [['api', '-X', 'PUT', 'repos/o/r/actions/workflows/1/enable']])             # el apagado a mano no se toca
        self.assertEqual([f['state'] for f in gh.flujos if f['id'] == 2], ['disabled_manually'])

    def test_un_flujo_apagado_a_mano_se_cuenta_como_sin_resolver_para_avisar(self):
        informe = self.revisar(GhFalso([wf(2, 'Ciclo', 'disabled_manually'), wf(3, 'Pruebas', 'active')]), True)
        self.assertEqual([r['nombre'] for r in administrador.flujos_sin_resolver(informe)], ['Ciclo'])

    def test_si_la_orden_falla_se_dice_y_no_se_da_por_reactivado(self):
        informe = self.revisar(GhFalso([wf(1, 'Calendario', 'disabled_inactivity')], falla_enable=[1]), True)
        self.assertEqual(self.resultados(informe), {'Calendario': 'no-se-pudo'})
        self.assertIn('422', informe[0]['detalle'])
        self.assertEqual(len(administrador.flujos_sin_resolver(informe)), 1)

    def test_reactivado_solo_si_github_lo_muestra_activo_despues(self):
        informe = self.revisar(GhFalso([wf(1, 'Calendario', 'disabled_inactivity')], enable_no_surte_efecto=[1]), True)
        self.assertEqual(self.resultados(informe), {'Calendario': 'no-se-pudo'})
        self.assertIn('no figura activo', informe[0]['detalle'])

    def test_con_todo_activo_no_hace_nada_mas_que_mirar(self):
        gh = GhFalso([wf(1, 'Calendario', 'active'), wf(2, 'Ciclo', 'active')])
        informe = self.revisar(gh, True)
        self.assertEqual(administrador.flujos_sin_resolver(informe), [])
        self.assertEqual(len(gh.llamadas), 1)

    def test_si_no_se_puede_listar_es_un_error_claro(self):
        with self.assertRaises(administrador.ErrorAdministrador) as c:
            self.revisar(GhFalso([], falla_al_listar=True))
        self.assertIn('no pude listar los flujos de o/r', str(c.exception))
        sin_forma = lambda argv: (0, '{"otra": 1}', '')
        with self.assertRaises(administrador.ErrorAdministrador):
            administrador.listar_flujos(sin_forma, 'o/r')

    def test_el_repositorio_sale_del_remoto_o_de_la_variable_de_los_flujos(self):
        for url in ('https://github.com/JellyCreator25/taller-gelatina-fabrica', 'https://github.com/JellyCreator25/taller-gelatina-fabrica.git',
                    'git@github.com:JellyCreator25/taller-gelatina-fabrica.git', 'https://github.com/JellyCreator25/taller-gelatina-fabrica/\n'):
            self.assertEqual(administrador.repo_de_remoto(url), 'JellyCreator25/taller-gelatina-fabrica', url)
        with self.assertRaises(administrador.ErrorAdministrador):
            administrador.repo_de_remoto('https://ejemplo.org/otro.git')
        self.assertEqual(administrador.repo_actual(RAIZ, {'GITHUB_REPOSITORY': 'a/b'}), 'a/b')

    def test_usa_solo_la_api_rest_de_gh(self):
        gh = GhFalso([wf(1, 'Calendario', 'disabled_inactivity')])
        self.revisar(gh, True)
        for argv in gh.llamadas:
            self.assertEqual(argv[0], 'api', argv)        # nunca `gh workflow ...`, que en estas sesiones pide GraphQL y se rechaza
            self.assertNotIn('graphql', ' '.join(argv))


if __name__ == '__main__':
    unittest.main()
