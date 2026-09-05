import hashlib
import os
import tempfile
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.conf import settings

DEFAULT_MAX_RESOURCE_BYTES = 100 * 1024 * 1024
DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 60
KNOWLEDGE_USER_AGENT = "Carbono Zero environmental knowledge / Mundaca Solutions SpA"


@dataclass(frozen=True)
class DownloadedExternalFile:
    path: str
    byte_size: int
    sha256: str
    final_url: str
    content_type: str
    etag: str
    last_modified: str


def validate_external_url(url, allowed_hosts):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts or parsed.username or parsed.password:
        raise ValueError("URL de recurso externo no permitida.")


class AllowlistedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allowed_hosts):
        super().__init__()
        self.allowed_hosts = allowed_hosts

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        validate_external_url(newurl, self.allowed_hosts)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def _open_url(request, timeout, allowed_hosts):
    return build_opener(AllowlistedRedirectHandler(allowed_hosts)).open(request, timeout=timeout)


def download_external_file(url, allowed_hosts, accept, allowed_content_types, expected_size=None, timeout=DEFAULT_DOWNLOAD_TIMEOUT_SECONDS, max_bytes=None, suffix=""):
    validate_external_url(url, allowed_hosts)
    maximum = max_bytes or getattr(settings, "KNOWLEDGE_MAX_RESOURCE_BYTES", DEFAULT_MAX_RESOURCE_BYTES)
    if expected_size is not None and int(expected_size) > maximum:
        raise ValueError("El recurso excede el tamaño máximo permitido.")
    request = Request(url, headers={"Accept": accept, "User-Agent": KNOWLEDGE_USER_AGENT})
    temp = tempfile.NamedTemporaryFile(prefix="carbonozero-knowledge-", suffix=suffix, delete=False)
    digest = hashlib.sha256()
    size = 0
    try:
        with temp, _open_url(request, timeout, allowed_hosts) as response:
            final_url = response.geturl()
            validate_external_url(final_url, allowed_hosts)
            content_type = (response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
            if content_type not in {value.lower() for value in allowed_content_types}:
                raise ValueError("Content-Type externo no permitido.")
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > maximum:
                raise ValueError("El recurso excede el tamaño máximo permitido.")
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > maximum:
                    raise ValueError("El recurso excede el tamaño máximo permitido.")
                digest.update(chunk)
                temp.write(chunk)
            return DownloadedExternalFile(temp.name, size, digest.hexdigest(), final_url, content_type, response.headers.get("ETag") or "", response.headers.get("Last-Modified") or "")
    except Exception:
        temp.close()
        if os.path.exists(temp.name):
            os.unlink(temp.name)
        raise


def remove_download(download):
    if download and os.path.exists(download.path):
        os.unlink(download.path)
