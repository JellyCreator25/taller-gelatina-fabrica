"""Sitio propio: despliegue en Cloudflare Pages con `wrangler pages deploy` (subida directa). Fuente: developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/
La guía de CI solo documenta --project-name; --branch y --commit-dirty son opciones habituales de wrangler que no pude releer hoy: el primer despliegue real se hace supervisado."""
import re

from ..nucleo import ErrorPlan, ErrorPublicacion, cargar_json, huella_carpeta, sha256_archivo


class CloudflarePages:
    canal = 'sitio-propio'
    categoria = 'sitio'
    secretos = ['CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_ACCOUNT_ID']

    def acciones(self, ctx):
        h = huella_carpeta(ctx.dist)
        manifiesto = cargar_json(ctx.raiz / 'dist' / 'sitio-manifiesto.json')
        if not h or not manifiesto:
            raise ErrorPlan('no existe el sitio generado (dist/sitio): corre primero «python3 fabrica.py sitio»')
        if manifiesto.get('huella') != h:
            raise ErrorPlan('dist/sitio cambió después de generarse: vuelve a correr «python3 fabrica.py sitio»')
        if manifiesto.get('url_base') != ctx.base():
            raise ErrorPlan('el sitio se generó para %s pero sitio.json dice %s: vuelve a correr «python3 fabrica.py sitio»' % (manifiesto.get('url_base'), ctx.base()))
        if ctx.id not in (ctx.sitio.get('juegos') or []):
            raise ErrorPlan('«%s» no está en sitio.json → juegos: agregarlo ahí es la decisión de lanzarlo' % ctx.id)
        hecho = (manifiesto.get('juegos') or {}).get(ctx.id)
        if not hecho:
            raise ErrorPlan('el sitio generado no incluye «%s»: vuelve a correr «python3 fabrica.py sitio»' % ctx.id)
        if not (ctx.salida / 'index.html').exists() or hecho.get('sha256') != sha256_archivo(ctx.salida / 'index.html'):
            raise ErrorPlan('el sitio trae una versión vieja de «%s»: vuelve a correr «python3 fabrica.py sitio»' % ctx.id)
        return [{'id': 'sitio:%s' % h[:12], 'tipo': 'desplegar',
                 'datos': {'proyecto': ctx.sitio.get('proyecto', ''), 'rama': ctx.sitio.get('rama_produccion', 'main'), 'carpeta': 'dist/sitio',
                           'huella_sitio': h, 'juegos': sorted(manifiesto.get('juegos', {})), 'comprobar': ctx.url_juego(ctx.spec['idiomas'][0])}}]

    def ejecutar(self, a, ent, ctx):
        d = a['datos']
        cuenta = (ent.env.get('CLOUDFLARE_ACCOUNT_ID') or '').strip()      # un espacio o salto de línea al pegar es el error más común: se quita
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', cuenta):
            # se dice qué tiene de mal sin mostrar el valor: solo la longitud y los signos de puntuación que sobran
            raros = sorted({c for c in cuenta if not c.isalnum() and c not in '_-'})
            raise ErrorPublicacion('CLOUDFLARE_ACCOUNT_ID no tiene la forma de un Account ID (una cadena de 32 letras y números): %s. Edítalo en GitHub → Settings → Environments → produccion '
                                   'y pega solo el identificador.' % ('está vacío' if not cuenta else 'tiene %d caracteres%s' % (
                                       len(cuenta), '; signos que no corresponden: ' + ' '.join(repr(c) for c in raros) if raros else '')))
        token = (ent.env.get('CLOUDFLARE_API_TOKEN') or '').strip()
        if not token:
            raise ErrorPublicacion('CLOUDFLARE_API_TOKEN está vacío: guárdalo en GitHub → Settings → Environments → produccion')
        if not re.fullmatch(r'[A-Za-z0-9_.~+/=-]{8,300}', token):
            # solo cuentas, nunca el contenido: el token es un secreto
            blancos = len(re.findall(r'\s', token))
            otros = len(re.findall(r'[^A-Za-z0-9_.~+/=\s-]', token))
            raise ErrorPublicacion('CLOUDFLARE_API_TOKEN no tiene la forma de un token de Cloudflare (una sola línea, sin espacios): tiene %d caracteres, %d espacios o saltos de línea en medio y %d caracteres '
                                   'raros. Suele pasar al copiar de más (por ejemplo, el comando de ejemplo que Cloudflare muestra debajo del token). Vuelve a copiar solo el token y guárdalo en '
                                   'GitHub → Settings → Environments → produccion.' % (len(token), blancos, otros))
        env = dict(ent.env, WRANGLER_SEND_METRICS='false', CI='true', CLOUDFLARE_ACCOUNT_ID=cuenta, CLOUDFLARE_API_TOKEN=token)
        rc, salida, err = ent.cmd(['npx', '--yes', 'wrangler@4', 'pages', 'deploy', str(ctx.raiz / d['carpeta']), '--project-name=' + d['proyecto'],
                                   '--branch=' + d['rama'], '--commit-dirty=true'], cwd=str(ctx.raiz), env=env)
        if rc != 0:
            raise ErrorPublicacion('wrangler terminó con error (código %s): %s' % (rc, re.sub(r'\x1b\[[0-9;]*m', '', (err or salida))[-400:].strip()))   # sin los colores de la terminal
        for _ in range(12):   # el sitio tarda unos segundos en responder
            try:
                if ent.http('GET', d['comprobar']).status == 200:
                    return {'detalle': 'desplegado y comprobado: ' + d['comprobar'], 'url': d['comprobar']}
            except Exception:   # sin red o sin DNS todavía: se vuelve a intentar
                pass
            ent.dormir(5)
        raise ErrorPublicacion('wrangler terminó bien, pero %s no respondió 200 en un minuto' % d['comprobar'])
