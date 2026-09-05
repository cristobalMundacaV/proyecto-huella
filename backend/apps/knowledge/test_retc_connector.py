import json
from io import StringIO
from unittest.mock import patch
from urllib.error import URLError

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .bootstrap import ensure_environmental_source_registry
from .connectors.retc import RETC_TIMEOUT_SECONDS, RETC_USER_AGENT, RetcCkanConnector
from .models import EnvironmentalSource, ExternalRecord, ExternalSnapshot
from .services import sync_environmental_source


class HttpResponse:
    def __init__(self, document, headers=None):
        self.body = json.dumps(document).encode()
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


def package(identifier="dataset-1", title="Dataset RETC", resources=None, **overrides):
    data = {
        "id": identifier,
        "name": f"slug-{identifier}",
        "title": title,
        "notes": "Descripción oficial",
        "organization": {"id": "org-1", "name": "retc", "title": "RETC", "private": "omitido"},
        "license_id": "cc-by",
        "license_title": "Creative Commons Attribution",
        "license_url": "http://www.opendefinition.org/licenses/cc-by",
        "tags": [{"id": "tag-1", "name": "aire", "display_name": "Aire", "vocabulary_id": None}],
        "groups": [{"id": "group-1", "name": "emisiones", "title": "Emisiones", "description": "omitido"}],
        "metadata_created": "2021-03-10T14:22:27.255091",
        "metadata_modified": "2026-09-04T05:43:37.380131",
        "resources": resources if resources is not None else [resource()],
        "maintainer_email": "no-debe-persistirse@example.test",
    }
    data.update(overrides)
    return data


def resource(identifier="resource-1", datastore_active=False):
    return {
        "id": identifier,
        "name": "Recurso 2024",
        "format": "XLSX",
        "url": f"https://datosretc.mma.gob.cl/download/{identifier}.xlsx",
        "size": 1234,
        "created": "2025-01-01T00:00:00",
        "last_modified": "2026-08-01T00:00:00",
        "datastore_active": datastore_active,
        "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "state": "active",
        "description": "Archivo oficial",
        "package_id": "dataset-1",
        "hash": "omitido",
    }


def response(results, count=None, headers=None, success=True):
    return HttpResponse(
        {"success": success, "result": {"count": len(results) if count is None else count, "results": results}},
        headers,
    )


class RetcCkanConnectorTests(TestCase):
    def setUp(self):
        ensure_environmental_source_registry()
        self.source = EnvironmentalSource.objects.get(codigo="retc")

    @patch("apps.knowledge.connectors.retc.urlopen")
    def test_una_pagina_normaliza_dataset_recursos_y_headers(self, mocked_urlopen):
        mocked_urlopen.return_value = response([package()], headers={"ETag": '"catalog"', "Last-Modified": "Fri, 04 Sep 2026 05:43:37 GMT"})
        batch = RetcCkanConnector(self.source).fetch(self.source.sync_state)
        record = batch.records[0]
        self.assertTrue(batch.authoritative_full_snapshot)
        self.assertEqual((batch.etag, batch.last_modified), ('"catalog"', "Fri, 04 Sep 2026 05:43:37 GMT"))
        self.assertEqual((record.kind, record.canonical_key), ("retc_dataset", "slug-dataset-1"))
        self.assertFalse(record.payload["resources"][0]["datastore_active"])
        self.assertEqual(record.payload["license"]["id"], "cc-by")
        self.assertEqual(record.payload["tags"][0]["name"], "aire")
        self.assertNotIn("maintainer_email", record.payload)
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(mocked_urlopen.call_args.kwargs["timeout"], RETC_TIMEOUT_SECONDS)
        self.assertEqual(request.get_header("User-agent"), RETC_USER_AGENT)

    @patch("apps.knowledge.connectors.retc.RETC_ROWS", 2)
    @patch("apps.knowledge.connectors.retc.urlopen")
    def test_multiples_paginas_recuperan_catalogo_completo(self, mocked_urlopen):
        mocked_urlopen.side_effect = [
            response([package("one"), package("two")], count=3),
            response([package("three")], count=3),
        ]
        batch = RetcCkanConnector(self.source).fetch(self.source.sync_state)
        self.assertEqual([record.external_id for record in batch.records], ["one", "two", "three"])
        self.assertIn("start=0", mocked_urlopen.call_args_list[0].args[0].full_url)
        self.assertIn("start=2", mocked_urlopen.call_args_list[1].args[0].full_url)

    @patch("apps.knowledge.connectors.retc.urlopen")
    def test_catalogo_identico_no_crea_snapshot_y_cambio_metadata_si(self, mocked_urlopen):
        mocked_urlopen.return_value = response([package()])
        first = sync_environmental_source(self.source)
        second = sync_environmental_source(self.source)
        self.assertEqual((first.created, second.unchanged, ExternalSnapshot.objects.count()), (1, 1, 1))
        mocked_urlopen.return_value = response([package(title="Título actualizado")])
        third = sync_environmental_source(self.source)
        self.assertEqual((third.modified, ExternalSnapshot.objects.count()), (1, 2))

    @patch("apps.knowledge.connectors.retc.urlopen")
    def test_recurso_nuevo_crea_snapshot_sin_descargarlo(self, mocked_urlopen):
        mocked_urlopen.return_value = response([package()])
        sync_environmental_source(self.source)
        mocked_urlopen.return_value = response([package(resources=[resource(), resource("resource-2", False)])])
        run = sync_environmental_source(self.source)
        self.assertEqual((run.modified, ExternalSnapshot.objects.count()), (1, 2))
        self.assertEqual(len(ExternalRecord.objects.get().current_snapshot.raw_payload["resources"]), 2)
        self.assertEqual(mocked_urlopen.call_count, 2)

    @patch("apps.knowledge.connectors.retc.urlopen", side_effect=TimeoutError("timeout"))
    def test_timeout_primera_pagina_produce_error(self, mocked_urlopen):
        run = sync_environmental_source(self.source)
        self.assertEqual((run.estado, ExternalRecord.objects.count()), ("error", 0))

    @patch("apps.knowledge.connectors.retc.RETC_ROWS", 1)
    @patch("apps.knowledge.connectors.retc.urlopen")
    def test_error_pagina_intermedia_no_marca_ausentes(self, mocked_urlopen):
        mocked_urlopen.return_value = response([package("existing")])
        sync_environmental_source(self.source)
        mocked_urlopen.side_effect = [response([package("new")], count=2), URLError("fallo página dos")]
        run = sync_environmental_source(self.source)
        existing = ExternalRecord.objects.get(external_id="existing")
        self.assertEqual(run.estado, "error")
        self.assertEqual(existing.estado, ExternalRecord.Status.ACTIVE)
        self.assertFalse(ExternalRecord.objects.filter(external_id="new").exists())

    @patch("apps.knowledge.connectors.retc.urlopen")
    def test_respuesta_invalida_produce_error_sin_persistir(self, mocked_urlopen):
        mocked_urlopen.return_value = HttpResponse({"success": False, "error": {"message": "invalid"}})
        run = sync_environmental_source(self.source)
        self.assertEqual((run.estado, ExternalSnapshot.objects.count()), ("error", 0))

    def test_bootstrap_configura_retc_real_y_preserva_divergencia_manual(self):
        self.assertEqual(self.source.connector_key, "retc_ckan")
        self.assertEqual(self.source.base_url, "https://datosretc.mma.gob.cl")
        self.source.connector_key = "conector-local"
        self.source.base_url = "https://local.example.test"
        self.source.save()
        ensure_environmental_source_registry()
        self.source.refresh_from_db()
        self.assertEqual((self.source.connector_key, self.source.base_url), ("conector-local", "https://local.example.test"))

        self.source.connector_key = "pending-retc"
        self.source.base_url = ""
        self.source.documentation_url = ""
        self.source.licencia_nombre = "Licencia local"
        self.source.save()
        ensure_environmental_source_registry()
        self.source.refresh_from_db()
        self.assertEqual((self.source.connector_key, self.source.licencia_nombre), ("pending-retc", "Licencia local"))

    @patch("apps.knowledge.connectors.retc.urlopen")
    def test_comando_imprime_resumen_y_falla_con_exit_code_no_cero(self, mocked_urlopen):
        mocked_urlopen.return_value = response([package()])
        output = StringIO()
        call_command("sync_environmental_source", "retc", stdout=output)
        self.assertIn("source=retc status=actualizada received=1 created=1", output.getvalue())
        mocked_urlopen.side_effect = TimeoutError("timeout")
        with self.assertRaises(CommandError):
            call_command("sync_environmental_source", "retc")
