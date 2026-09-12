"""EC3-01 — refresh_known_ec3_epds management command (capability 10).

Never discovers new EPDs, never bulk-downloads the EC3 catalog — only
re-validates EPDs Carbono Zero already knows about, one at a time, through
the same audited targeted ingestion `ingest_ec3_epd` already uses.
"""
import io
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.analytics.models import MaterialOperacional, Organizacion
from apps.ec3.client import Ec3Client
from apps.ec3.services import ingest_epd
from .fixtures import SETTINGS, response, steel_payload


@override_settings(**SETTINGS)
class RefreshKnownEc3EpdsCommandTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("ec3-refresh", "ec3-refresh@example.org", "test")
        self.org = Organizacion.objects.create(nombre="EC3 refresh synthetic")
        self.material = MaterialOperacional.objects.create(organizacion=self.org, codigo="EC3-REFRESH",
            nombre="Refresh synthetic", categoria="materiales", unidad_base="kg")

    def _run(self, session, **options):
        out, err = io.StringIO(), io.StringIO()
        with patch("apps.ec3.management.commands.refresh_known_ec3_epds.Ec3Client",
                   return_value=Ec3Client(session=session, limiter=Mock(), sleep=Mock())):
            call_command("refresh_known_ec3_epds", actor_id=self.user.pk, stdout=out, stderr=err, **options)
        return out.getvalue(), err.getvalue()

    def test_no_known_epds_reports_zero(self):
        out, _ = self._run(Mock())
        self.assertIn("known_epds=0 refreshed=0 changed=0 errors=0", out)

    def test_unknown_actor_id_is_a_command_error(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command("refresh_known_ec3_epds", actor_id=999999)

    def test_refresh_unchanged_epd_reports_refreshed_without_change(self):
        seed_session = Mock()
        seed_session.get.return_value = response(steel_payload())
        ingest_epd("ec3test1", self.user, client=Ec3Client(session=seed_session, limiter=Mock(), sleep=Mock()))

        refresh_session = Mock()
        refresh_session.get.return_value = response(steel_payload())
        out, _ = self._run(refresh_session)
        self.assertIn("known_epds=1 refreshed=1 changed=0 errors=0", out)

    def test_refresh_detects_real_upstream_change(self):
        seed_session = Mock()
        seed_session.get.return_value = response(steel_payload())
        ingest_epd("ec3test1", self.user, client=Ec3Client(session=seed_session, limiter=Mock(), sleep=Mock()))

        refresh_session = Mock()
        refresh_session.get.return_value = response(steel_payload(version=2, mean=1700))
        out, _ = self._run(refresh_session)
        self.assertIn("known_epds=1 refreshed=1 changed=1 errors=0", out)

    def test_one_failing_epd_does_not_abort_the_batch(self):
        seed_session = Mock()
        seed_session.get.return_value = response(steel_payload())
        ingest_epd("ec3test1", self.user, client=Ec3Client(session=seed_session, limiter=Mock(), sleep=Mock()))
        other_payload = steel_payload()
        other_payload["id"] = "ec3test2"
        seed_session.get.return_value = response(other_payload)
        ingest_epd("ec3test2", self.user, client=Ec3Client(session=seed_session, limiter=Mock(), sleep=Mock()))

        refresh_session = Mock()
        refresh_session.get.side_effect = [response({"secret": "no"}, status=404), response(other_payload)]
        out, _ = self._run(refresh_session)
        self.assertIn("known_epds=2 refreshed=1 changed=0 errors=1", out)
