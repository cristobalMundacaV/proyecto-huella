"""EC3-01 — observability summary (capability 13).

Purely derived from persisted state; never a raw credential or upstream
body, only sanitized SyncRun.message codes already produced by ingestion.
"""
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.analytics.models import MaterialOperacional, Organizacion
from apps.ec3.client import Ec3Client, UpstreamError
from apps.ec3.observability import observability_summary
from apps.ec3.services import ingest_epd
from .fixtures import SETTINGS, response, steel_payload


@override_settings(**SETTINGS)
class ObservabilitySummaryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("ec3-obs", "ec3-obs@example.org", "test")
        self.org = Organizacion.objects.create(nombre="EC3 observability synthetic")
        self.material = MaterialOperacional.objects.create(organizacion=self.org, codigo="EC3-OBS",
            nombre="Obs synthetic", categoria="materiales", unidad_base="kg")

    def test_unregistered_source_reports_not_registered(self):
        self.assertEqual(observability_summary(), {"registered": False})

    def test_summary_after_successful_ingestion_never_leaks_secrets(self):
        session = Mock()
        session.get.return_value = response(steel_payload())
        ingest_epd("ec3test1", self.user, client=Ec3Client(session=session, limiter=Mock(), sleep=Mock()))
        summary = observability_summary()
        self.assertTrue(summary["registered"])
        self.assertEqual(summary["requests_total"], 1)
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(summary["epds_known"], 1)
        self.assertEqual(summary["epd_versions_total"], 1)
        self.assertNotIn(str(session), str(summary))

    def test_failure_is_bucketed_by_sanitized_reason(self):
        session = Mock()
        session.get.return_value = response(steel_payload())
        ingest_epd("ec3test1", self.user, client=Ec3Client(session=session, limiter=Mock(), sleep=Mock()))
        session.get.return_value = response({"secret": "do not log"}, status=404)
        with self.assertRaises(UpstreamError):
            ingest_epd("ec3test1", self.user, client=Ec3Client(session=session, limiter=Mock(), sleep=Mock()))
        summary = observability_summary()
        self.assertEqual(summary["errors"], 1)
        self.assertEqual(summary["failure_reasons"], {"ec3_epd_not_found": 1})


@override_settings(**SETTINGS)
class ObservabilityApiTests(TestCase):
    def test_endpoint_requires_superuser(self):
        user = get_user_model().objects.create_superuser("ec3-obs-api", "ec3-obs-api@example.org", "test")
        plain = get_user_model().objects.create_user("ec3-obs-plain", "ec3-obs-plain@example.org", "test")
        api = APIClient()
        self.assertEqual(api.get("/api/integrations/ec3/observability/").status_code, 403)
        api.force_authenticate(plain)
        self.assertEqual(api.get("/api/integrations/ec3/observability/").status_code, 403)
        api.force_authenticate(user)
        result = api.get("/api/integrations/ec3/observability/")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data, {"registered": False})
