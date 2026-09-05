import json
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.utils import timezone

from .base import ConnectorBatch, ConnectorRecord, EnvironmentalConnector


RETC_BASE_URL = "https://datosretc.mma.gob.cl"
RETC_API_URL = f"{RETC_BASE_URL}/api/3/action/package_search"
RETC_ROWS = 100
RETC_TIMEOUT_SECONDS = 30
RETC_USER_AGENT = "Carbono Zero environmental knowledge connector / Mundaca Solutions SpA"


def _datetime(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


def _resource(resource):
    return {
        "id": resource.get("id"),
        "name": resource.get("name"),
        "format": resource.get("format"),
        "url": resource.get("url"),
        "size": resource.get("size"),
        "created": resource.get("created"),
        "last_modified": resource.get("last_modified"),
        "datastore_active": bool(resource.get("datastore_active", False)),
        "mimetype": resource.get("mimetype"),
        "state": resource.get("state"),
        "description": resource.get("description"),
        "package_id": resource.get("package_id"),
    }


def _payload(package):
    organization = package.get("organization") or {}
    return {
        "id": package.get("id"),
        "name": package.get("name"),
        "title": package.get("title"),
        "notes": package.get("notes"),
        "organization": {
            "id": organization.get("id"),
            "name": organization.get("name"),
            "title": organization.get("title"),
        },
        "license": {
            "id": package.get("license_id"),
            "title": package.get("license_title"),
            "url": package.get("license_url"),
        },
        "tags": [
            {"id": tag.get("id"), "name": tag.get("name"), "display_name": tag.get("display_name")}
            for tag in package.get("tags") or []
        ],
        "groups": [
            {"id": group.get("id"), "name": group.get("name"), "title": group.get("title")}
            for group in package.get("groups") or []
        ],
        "metadata_created": package.get("metadata_created"),
        "metadata_modified": package.get("metadata_modified"),
        "resources": [_resource(resource) for resource in package.get("resources") or []],
    }


class RetcCkanConnector(EnvironmentalConnector):
    def fetch(self, sync_state):
        records = []
        start = 0
        total = None
        etag = ""
        last_modified = ""

        while total is None or start < total:
            query = urlencode({"start": start, "rows": RETC_ROWS})
            request = Request(
                f"{RETC_API_URL}?{query}",
                headers={"Accept": "application/json", "User-Agent": RETC_USER_AGENT},
            )
            with urlopen(request, timeout=RETC_TIMEOUT_SECONDS) as response:
                etag = response.headers.get("ETag") or etag
                last_modified = response.headers.get("Last-Modified") or last_modified
                document = json.loads(response.read().decode("utf-8"))

            if document.get("success") is not True or not isinstance(document.get("result"), dict):
                raise ValueError("Respuesta CKAN inválida: falta un resultado exitoso.")
            result = document["result"]
            page = result.get("results")
            count = result.get("count")
            if not isinstance(page, list) or not isinstance(count, int) or count < 0:
                raise ValueError("Respuesta CKAN inválida: paginación ausente o inválida.")
            if total is None:
                total = count
            elif total != count:
                raise ValueError("El catálogo CKAN cambió durante la paginación.")
            if not page and start < total:
                raise ValueError("Respuesta CKAN incompleta antes de alcanzar el total declarado.")

            for package in page:
                package_id = package.get("id")
                if not package_id:
                    raise ValueError("Dataset CKAN sin identificador estable.")
                name = package.get("name") or ""
                records.append(
                    ConnectorRecord(
                        external_id=package_id,
                        kind="retc_dataset",
                        canonical_key=name,
                        title=package.get("title") or name,
                        source_url=f"{RETC_BASE_URL}/dataset/{name}" if name else RETC_BASE_URL,
                        published_at=_datetime(package.get("metadata_created")),
                        upstream_updated_at=_datetime(package.get("metadata_modified")),
                        payload=_payload(package),
                    )
                )
            start += len(page)

        return ConnectorBatch(
            records=records,
            etag=etag,
            last_modified=last_modified,
            authoritative_full_snapshot=True,
            metadata={"endpoint": RETC_API_URL, "dataset_count": total},
        )
