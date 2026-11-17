"""Capa de red mínima (solo biblioteca estándar). Los adaptadores reciben una función `http` con esta forma, así las pruebas
pueden sustituirla sin tocar la red. Nunca se registran cabeceras ni cuerpos: pueden llevar secretos."""
import json
import urllib.error
import urllib.request
import uuid


class ErrorRed(Exception):
    """No hubo respuesta (sin conexión, tiempo agotado…). Para una petición que escribe, el resultado es incierto: puede haberse hecho o no."""


class Respuesta:
    def __init__(self, status, cabeceras, cuerpo):
        self.status = status
        self.cabeceras = {k.lower(): v for k, v in (cabeceras or {}).items()}
        self.cuerpo = cuerpo or b''

    def json(self):
        try:
            return json.loads(self.cuerpo.decode('utf-8'))
        except ValueError:
            return {}

    def texto(self, n=300):
        return self.cuerpo.decode('utf-8', 'replace')[:n]


AGENTE = 'ggx-fabrica/1.0 (bot declarado; no es un navegador)'


def solicitar(metodo, url, cabeceras=None, cuerpo=None, tiempo=40, permitir_http=False):
    if not (url.startswith('https://') or (permitir_http and url.startswith('http://'))):
        raise ErrorRed('solo se admiten direcciones https')
    cab = dict(cabeceras or {})
    if not any(k.lower() == 'user-agent' for k in cab):
        # sin esto urllib se anuncia como «Python-urllib», que muchos servicios (Cloudflare incluido) rechazan; se identifica la fábrica con honestidad, sin fingir ser un navegador
        cab['User-Agent'] = AGENTE
    req = urllib.request.Request(url, data=cuerpo, method=metodo, headers=cab)
    try:
        with urllib.request.urlopen(req, timeout=tiempo) as r:
            return Respuesta(r.status, dict(r.headers.items()), r.read())
    except urllib.error.HTTPError as e:
        return Respuesta(e.code, dict(e.headers.items()) if e.headers else {}, e.read())
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ErrorRed(str(e)[:200])


def multipart(campos, archivos):
    """(cuerpo, tipo de contenido) de un formulario multipart. archivos: {nombre: (nombre_archivo, bytes, tipo_mime)}."""
    frontera = 'ggx' + uuid.uuid4().hex
    partes = []
    for k, v in campos.items():
        partes.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n' % (frontera, k)).encode() + str(v).encode('utf-8') + b'\r\n')
    for k, (nombre, datos, mime) in archivos.items():
        partes.append(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\nContent-Type: %s\r\n\r\n' % (frontera, k, nombre, mime)).encode() + datos + b'\r\n')
    partes.append(('--%s--\r\n' % frontera).encode())
    return b''.join(partes), 'multipart/form-data; boundary=' + frontera


def redactar(texto, secretos):
    """Quita de un mensaje cualquier valor secreto antes de mostrarlo o guardarlo."""
    texto = str(texto)
    for s in secretos:
        if s and len(s) >= 4:
            texto = texto.replace(s, '***')
    return texto
