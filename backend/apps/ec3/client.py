import hashlib
import json
import random
import time
from datetime import timedelta
from decimal import Decimal
from email.utils import parsedate_to_datetime

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from .conf import ATTRIBUTION, BASE_URL, enabled, storage_allowed
from .models import ResponseCache
from .rate_limit import DatabaseRateLimiter, RateLimited
from .schemas import checksum, external_id, project_epd, project_search


class UpstreamError(Exception):
    def __init__(self, code, status=502):
        self.code, self.status = code, status
        super().__init__(code)


def retry_after(value, default):
    try:
        seconds = float(value)
        if seconds >= 0 and seconds < float("inf"):
            return max(1, seconds)
    except (TypeError, ValueError):
        pass
    try:
        return max(1, (parsedate_to_datetime(value) - timezone.now()).total_seconds())
    except (TypeError, ValueError, OverflowError):
        return default


class Ec3Client:
    def __init__(self, *, session=None, limiter=None, sleep=time.sleep):
        self.session = session or requests.Session()
        self.session.trust_env = False  # No implicit netrc credentials/proxies.
        self.limiter = limiter or DatabaseRateLimiter()
        self.sleep = sleep

    def close(self):
        self.session.close()

    def search(self, omf, *, page_number=1, page_size=5, refresh=False):
        if not isinstance(omf, str) or not omf.strip() or len(omf) > 4000:
            raise ValidationError("Se requiere una consulta oMF explícita de hasta 4000 caracteres.")
        # Smaller local page cap is deliberate; never enumerate the entire database.
        if type(page_number) is not int or not 1 <= page_number <= 1000 or type(page_size) is not int or not 1 <= page_size <= 25:
            raise ValidationError("Página inválida: page_number 1..1000, page_size 1..25.")
        return self._get("/v2/epds/search", {"omf": omf, "page_number": page_number, "page_size": page_size},
                         lambda data: project_search(data, page_number, page_size), refresh=refresh)

    def detail(self, epd_id, *, refresh=False):
        epd_id = external_id(epd_id)

        def validate(data):
            evidence = project_epd(data, detail=True)
            if evidence["id"] != epd_id:
                raise ValidationError("El ID de respuesta no corresponde a la EPD solicitada.")
            return evidence

        return self._get(f"/epds/{epd_id}", {}, validate, refresh=refresh)

    @sensitive_variables("token", "headers", "response", "body", "data")
    def _get(self, path, params, validate, *, refresh):
        enabled()
        token = getattr(settings, "EC3_API_TOKEN", "")
        if not token or any(c in token for c in "\r\n"):
            raise ValidationError("Configure EC3_API_TOKEN exclusivamente en el backend.")
        # Credentials only travel to the documented fixed origin. No URL supplied by callers.
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "CarbonoZero/EC3-01"}
        key = checksum({"contract": "ec3-01/v1", "path": path, "params": params,
                        "credential_partition": hashlib.sha256(token.encode()).hexdigest(),
                        "rights": getattr(settings, "EC3_RIGHTS_REFERENCE", "")})
        cache_on = storage_allowed() and getattr(settings, "EC3_CACHE_TTL_SECONDS", 300) > 0
        if cache_on and not refresh:
            row = ResponseCache.objects.filter(key=key, expires_at__gt=timezone.now()).first()
            if row:
                return {**row.value, "cache_hit": True}
        attempts = 3
        for attempt in range(attempts):
            self.limiter.acquire(1)  # Official Get OpenEPD / Get Material List costs.
            response = None
            wait = min(8, 2 ** attempt) + random.uniform(0, 0.25)
            try:
                response = self.session.get(BASE_URL + path, params=params, headers=headers,
                                            timeout=(5, 20), allow_redirects=False, stream=True)
                status = response.status_code
                if status == 429:
                    wait = retry_after(response.headers.get("Retry-After"), 60)
                    self.limiter.defer(wait)
                    if attempt == attempts - 1 or wait > 8:
                        raise RateLimited(wait)
                elif 500 <= status <= 599:
                    wait = retry_after(response.headers.get("Retry-After"), wait)
                    if wait > 8:
                        self.limiter.defer(wait)
                        raise RateLimited(wait)
                    if attempt == attempts - 1:
                        raise UpstreamError("ec3_unavailable")
                elif status != 200:
                    code = {401: "ec3_authentication_failed", 403: "ec3_access_denied", 404: "ec3_epd_not_found"}.get(status, "ec3_request_rejected")
                    raise UpstreamError(code, 404 if status == 404 else 502)
                else:
                    if "application/json" not in response.headers.get("Content-Type", "").lower():
                        raise UpstreamError("ec3_invalid_content_type")
                    chunks, size = [], 0
                    for chunk in response.iter_content(65536):
                        size += len(chunk)
                        if size > 2 * 1024 * 1024:
                            raise UpstreamError("ec3_response_too_large")
                        chunks.append(chunk)
                    body = b"".join(chunks)
                    try:
                        data = json.loads(body, parse_float=Decimal,
                                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                        projection = validate(data)
                    except (ValueError, TypeError, RecursionError, ValidationError):
                        raise UpstreamError("ec3_schema_invalid") from None
                    result = {"data": projection, "payload_checksum": hashlib.sha256(body).hexdigest(),
                              "checksum_algorithm": "sha256/http-decoded-body", "retrieved_at": timezone.now().isoformat(),
                              "source_url": BASE_URL + path, "cache_hit": False, "attribution": ATTRIBUTION}
                    if cache_on and storage_allowed():
                        ttl = min(max(0, settings.EC3_CACHE_TTL_SECONDS), 3600)
                        ResponseCache.objects.update_or_create(key=key, defaults={"value": result, "expires_at": timezone.now() + timedelta(seconds=ttl)})
                    return result
            except (requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError):
                if attempt == attempts - 1:
                    raise UpstreamError("ec3_network_timeout") from None
            except requests.RequestException:
                raise UpstreamError("ec3_transport_error") from None
            finally:
                if response is not None:
                    response.close()
            self.sleep(wait)
        raise UpstreamError("ec3_unavailable")
