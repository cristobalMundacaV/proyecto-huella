import hashlib
from urllib.parse import urljoin, urlparse

from django.conf import settings
import requests

from ..downloads import KNOWLEDGE_USER_AGENT

SNIFA_HOSTS = {"snifa.sma.gob.cl"}
SEA_HOSTS = {"seia.sea.gob.cl"}
SNIFA_PATHS = ("/DatosAbiertos", "/UnidadFiscalizable", "/Fiscalizacion", "/Sancionatorio", "/RegistroPublico", "/Sancion")
SEA_PATHS = ("/busqueda/", "/expediente/", "/proyecto/", "/Expediente/", "/Proyecto/")


def validate_public_url(url, hosts, paths):
    parsed = urlparse(str(url))
    if parsed.scheme != "https" or parsed.hostname not in hosts or parsed.username or parsed.password or not any(parsed.path.startswith(prefix) for prefix in paths):
        raise ValueError("URL regulatoria publica no permitida.")
    return str(url)


def validate_snifa_url(url):
    return validate_public_url(url, SNIFA_HOSTS, SNIFA_PATHS)


def validate_sea_url(url):
    return validate_public_url(url, SEA_HOSTS, SEA_PATHS)


def fetch_html(url, validator, data=None):
    validator(url)
    connect_timeout = getattr(settings, "KNOWLEDGE_DOCUMENT_INDEX_CONNECT_TIMEOUT_SECONDS", 10)
    read_timeout = getattr(settings, "KNOWLEDGE_DOCUMENT_INDEX_READ_TIMEOUT_SECONDS", 30)
    maximum = getattr(settings, "KNOWLEDGE_DOCUMENT_INDEX_MAX_BYTES", 5 * 1024 * 1024)
    method = "POST" if data is not None else "GET"; current = url
    headers = {"Accept": "text/html,application/xhtml+xml", "User-Agent": KNOWLEDGE_USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"}
    for _ in range(4):
        response = requests.request(method, current, data=data, headers=headers, timeout=(connect_timeout, read_timeout), allow_redirects=False, stream=True)
        if response.is_redirect:
            target = urljoin(current, response.headers.get("Location", "")); validator(target); current = target
            if response.status_code in (301, 302, 303): method, data = "GET", None
            response.close(); continue
        response.raise_for_status(); validator(response.url)
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type: response.close(); raise ValueError("Content-Type regulatorio no soportado.")
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > maximum: response.close(); raise ValueError("Respuesta regulatoria excede el limite.")
        response.raw.decode_content = True; body = response.raw.read(maximum + 1); response.close()
        if len(body) > maximum: raise ValueError("Respuesta regulatoria excede el limite.")
        encoding = response.encoding or "utf-8"; text = body.decode(encoding, errors="strict")
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        return text, hashlib.sha256(normalized).hexdigest(), response.url
    raise ValueError("Demasiadas redirecciones regulatorias.")
