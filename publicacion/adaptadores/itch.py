"""itch.io con butler (la herramienta oficial): `butler push ARCHIVO usuario/juego:canal --userversion VERSION`. Fuente: itch.io/docs/butler/pushing.html.
La página del juego se crea a mano una vez (itch.io no ofrece forma programática) y el canal HTML5 se marca a mano en «Edit game» la primera vez."""
from ..nucleo import ErrorPlan, ErrorPublicacion, sha256_archivo


class ItchButler:
    canal = 'itch-pagina'
    categoria = 'portales'
    secretos = ['BUTLER_API_KEY']

    def acciones(self, ctx):
        cfg = (ctx.spec.get('publicacion') or {}).get('itch') or {}
        if not cfg.get('destino') or '/' not in cfg['destino']:
            raise ErrorPlan('falta publicacion.itch.destino («usuario/juego») en juego.json: la página se crea a mano primero')
        zip_rel = 'salida/%s/%s-web.zip' % (ctx.id, ctx.id)
        z = ctx.archivo(zip_rel)
        if not z:
            raise ErrorPlan('falta %s (corre «python3 fabrica.py construir %s»)' % (zip_rel, ctx.id))
        return [{'id': '%s:%s:itch:empujar' % (ctx.id, ctx.version), 'tipo': 'empujar',
                 'datos': {'archivo': z['archivo'], 'sha256': z['sha256'], 'destino': cfg['destino'], 'canal_itch': cfg.get('canal', 'html5'), 'version': ctx.version}}]

    def ejecutar(self, a, ent, ctx):
        d = a['datos']
        ruta = ctx.raiz / d['archivo']
        if sha256_archivo(ruta) != d['sha256']:
            raise ErrorPublicacion('el zip cambió después de aprobar el plan: se detiene')
        rc, salida, err = ent.cmd(['butler', 'push', str(ruta), '%s:%s' % (d['destino'], d['canal_itch']), '--userversion', d['version']], cwd=str(ctx.raiz), env=dict(ent.env))
        if rc != 0:
            raise ErrorPublicacion('butler terminó con error (código %s): %s' % (rc, (err or salida)[-300:].strip()), incierto=False)
        return {'detalle': 'butler empujó la versión %s a %s:%s' % (d['version'], d['destino'], d['canal_itch'])}
