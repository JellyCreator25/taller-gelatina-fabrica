"""Mapa de canales: convierte difusion/canales.json en difusion/MAPA.md, una sola página que dice, canal por canal, qué hace el motor
solo, qué solo puede hacer el dueño (cuentas, permisos, cobros) y qué se sabe de los ingresos. No inventa nada: todo sale de canales.json,
donde cada hecho lleva su fuente y la fecha en que se leyó."""
import json
import pathlib

ORDEN_NIVEL = ['total', 'parcial', 'manual', 'bloqueado']
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def _fecha(iso):
    a, m, d = (int(x) for x in iso.split('-'))
    return '%d de %s de %d' % (d, MESES[m - 1], a)


def _celda(texto):
    return str(texto).replace('|', '/').replace('\n', ' ')


def mapa(datos):
    canales = datos['canales']
    por_nivel = {n: [c for c in canales if c['automatizacion']['nivel'] == n] for n in ORDEN_NIVEL}
    L = ['# Mapa de canales: qué puede hacer el motor solo', '',
         'Verificado el %s en las páginas oficiales de cada canal (las fuentes están en `difusion.md` de cada juego y en `investigar/notas-2026-11-12.md`). '
         'Las plataformas cambian sus reglas: pasados 30 días, `fabrica.py revisar` pide volver a leerlas.' % _fecha(datos['verificado']), '',
         '## Cómo leerlo', '']
    L += ['- **%s:** %s' % tuple(datos['niveles'][n].split(': ', 1)) for n in ORDEN_NIVEL]
    L += ['', '## Resumen', '', '| Nivel | Canales |', '|---|---|']
    for n in ORDEN_NIVEL:
        if por_nivel[n]:
            L.append('| %s | %s |' % (n.capitalize(), '; '.join(c['nombre'] for c in por_nivel[n])))
    L += ['', '## Canal por canal', '',
          '| Canal | Nivel | Vía | Una sola vez (solo tú) | Cada vez (el motor) | Ingresos |', '|---|---|---|---|---|---|']
    for n in ORDEN_NIVEL:
        for c in por_nivel[n]:
            a = c['automatizacion']
            L.append('| %s | %s | %s | %s | %s | %s |' % (
                _celda(c['nombre'] + (' (opcional)' if c.get('opcional') else '')), n.capitalize(), _celda(a['via']),
                _celda(' · '.join(a['una_vez']) or '—'), _celda(' · '.join(a['cada_vez']) or '—'), _celda(a.get('ingresos', 'no verificado'))))
    secretos = sorted({s for c in canales for s in c['automatizacion'].get('secretos', [])})
    L += ['', '## Secretos que usa el motor', '',
          'Solo existen en el entorno «produccion» de tu repositorio de GitHub (Settings → Environments), con revisores obligatorios. '
          'Nunca van en el chat, en `juego.json` ni en ningún archivo del repositorio. Nombres: ' + ', '.join('`%s`' % s for s in secretos) + '.', '',
          '## Lo que siempre queda en manos de una persona', '',
          '- Crear cuentas, aceptar términos y configurar cobros: son tuyos y de tu identidad; el motor no los hace por ti.']
    for c in canales:
        for h in c['automatizacion'].get('humano', []):
            L.append('- **%s:** %s ([fuente](%s))' % (c['nombre'], h['texto'], h['fuente']))
    L += ['', '## Ingresos: lo que sí y lo que no se puede decir', '',
          '- Ningún canal de esta lista garantiza ingresos. Un sitio o una cuenta nueva no tiene visitas, y sin visitas no hay anuncios ni donaciones.',
          '- Los porcentajes de reparto de Poki, CrazyGames y Playgama no están en páginas oficiales que haya podido leer completas (ver `investigar/notas-2026-11-12.md`).',
          '- Lo fiscal (cobrar desde México, facturar, impuestos) se ve con tu contador antes de activar cualquier cobro.', '']
    return '\n'.join(L)


def generar(raiz):
    raiz = pathlib.Path(raiz)
    datos = json.loads((raiz / 'difusion' / 'canales.json').read_text(encoding='utf-8'))
    texto = mapa(datos)
    (raiz / 'difusion' / 'MAPA.md').write_text(texto, encoding='utf-8')
    return texto
