from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.analytics.models import (ActividadOperacional, CalculoAmbiental, EventoMaterial, FuenteDatos,
    MaterialOperacional, Obra, Observacion, Organizacion, UsuarioOrganizacion)
from apps.analytics.services.calculation_v2 import calculate_activity
from apps.analytics.services.factor_governance import transition_factor_version
from apps.analytics.services.material_factor_mapping import approve_material_mapping, revoke_material_mapping
from apps.analytics.services.material_factor_selector import select_material_factor
from apps.analytics.services.material_ledger import ledger_entry_provenance
from apps.analytics.services.system_environmental_catalog import ensure_system_environmental_catalog
from apps.ec3.client import Ec3Client, UpstreamError
from apps.ec3.models import Candidate, EpdVersion, Review
from apps.ec3.services import (candidate_data, evaluate_version, ingest_epd, promote_candidate,
    propose_candidate, propose_mapping, provenance, review_candidate)
from apps.knowledge.models import ExternalSnapshot, SyncRun
from .fixtures import CONTEXT, SETTINGS, response, search_payload, steel_payload


@override_settings(**SETTINGS)
class GovernanceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("ec3-reviewer", "ec3@example.org", "test")
        self.org = Organizacion.objects.create(nombre="EC3 synthetic E2E")
        self.material = MaterialOperacional.objects.create(organizacion=self.org, codigo="EC3-STEEL",
            nombre="Acero estructural sintético", categoria="materiales", unidad_base="kg")
        self.session = Mock()
        self.session.get.return_value = response(steel_payload())
        self.client = Ec3Client(session=self.session, limiter=Mock(), sleep=Mock())
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def ingest(self, payload=None):
        if payload is not None:
            self.session.get.return_value = response(payload)
        return ingest_epd("ec3test1", self.user, client=self.client)

    def approved(self):
        version = self.ingest()
        candidate = propose_candidate(self.material, version, self.user)
        review_candidate(candidate.pk, self.user, "approved", "EF 3.0", CONTEXT)
        return candidate

    def mapped(self):
        candidate = promote_candidate(self.approved().pk, self.user)
        for state in ("pruebas", "validado", "activo"):
            transition_factor_version(candidate.promoted_version, state)
        candidate = propose_mapping(candidate.pk, self.user, date(2020, 1, 1))
        approve_material_mapping(candidate.mapping_id, self.org, self.user, "Explicit synthetic mapping approval")
        candidate.refresh_from_db()
        return candidate

    def test_ingestion_dedup_versions_projection_and_non_authoritative_run(self):
        one = self.ingest()
        again = self.ingest()
        self.assertEqual(one.pk, again.pk)
        two = self.ingest(steel_payload(version=2, mean=1700))
        self.assertEqual(two.local_version, 2)
        self.assertNotEqual(one.snapshot.content_hash, two.snapshot.content_hash)
        self.assertIsNone(one.snapshot.raw_payload)
        self.assertEqual(one.snapshot.raw_text, "")
        self.assertNotIn("lca_discussion", one.evidence)
        self.assertEqual(SyncRun.objects.filter(snapshot_autoritativo=False).count(), 3)
        self.assertFalse(one.record.source.permite_poll_automatico)
        self.assertEqual(one.record.source.sync_state.metadata["sync_scope"], "targeted_epd")
        self.assertIn("source_version_changed", evaluate_version(one, "EF 3.0")["reasons"])

    def test_payload_changes_without_upstream_version_are_new_local_versions(self):
        one = self.ingest()
        two = self.ingest(steel_payload(mean=1700))
        self.assertEqual(one.upstream_version, two.upstream_version)
        self.assertEqual(two.local_version, 2)

    def test_reappearance_of_old_payload_does_not_resurrect_approval(self):
        candidate = self.mapped()
        self.ingest(steel_payload(version=2, mean=1700))
        returned = self.ingest(steel_payload())
        self.assertEqual(returned.local_version, 3)
        self.assertEqual(returned.snapshot_id, candidate.epd_version.snapshot_id)
        self.assertNotEqual(returned.pk, candidate.epd_version_id)
        self.assertIsNone(select_material_factor(self.org, self.material, "kg", date.today())["factor_version"])

    def test_same_version_refresh_restores_freshness_not_original_retrieval_date(self):
        version = self.ingest()
        original = provenance(version)["retrieved_at"]
        version.record.last_seen_at = timezone.now() - timedelta(days=8)
        version.record.save(update_fields=["last_seen_at"])
        self.assertIn("source_stale", evaluate_version(version, "EF 3.0")["reasons"])
        refreshed = self.ingest()
        self.assertTrue(evaluate_version(refreshed, "EF 3.0")["compatible"])
        self.assertEqual(original, provenance(refreshed)["retrieved_at"])

    def test_search_is_not_evidence_and_never_applies_factor(self):
        self.session.get.return_value = response(search_payload())
        self.client.search('!EC3 search("StructuralSteel") !pragma oMF("1.0/1")', page_size=1)
        self.assertFalse(EpdVersion.objects.exists())
        self.assertFalse(Candidate.objects.exists())
        self.assertIsNone(select_material_factor(self.org, self.material, "kg", date.today())["factor_version"])

    def test_source_watch_connection_is_read_only_and_never_bulk_polls(self):
        from apps.knowledge.connectors.registry import connector_for
        from apps.knowledge.watch_policy import describe_watch_policy
        source = self.ingest().record.source
        source.full_clean()
        self.assertFalse(describe_watch_policy(source)["safe_to_auto_watch"])
        with self.assertRaises(ValueError):
            connector_for(source).fetch(source.sync_state)

    def test_missing_metadata_and_lcia_block_human_approval(self):
        payload = steel_payload()
        payload.pop("pcr")
        candidate = propose_candidate(self.material, self.ingest(payload), self.user)
        with self.assertRaises(ValidationError):
            review_candidate(candidate.pk, self.user, "approved", "EF 3.0", CONTEXT)
        review_candidate(candidate.pk, self.user, "rejected", "EF 3.0", CONTEXT)
        self.assertEqual(candidate_data(candidate)["status"], "REJECTED")

    def test_ai_context_cannot_confirm_or_skip_governance(self):
        candidate = propose_candidate(self.material, self.ingest(), self.user)
        with self.assertRaises(ValidationError):
            promote_candidate(candidate.pk, self.user)
        with self.assertRaises(ValidationError):
            review_candidate(candidate.pk, self.user, "approved", "EF 3.0", {"ai_confirmed": True})
        self.assertFalse(Review.objects.exists())

    def test_promote_only_draft_idempotent_proposal_and_no_double_promotion(self):
        candidate = self.approved()
        self.assertEqual(candidate.pk, propose_candidate(self.material, candidate.epd_version, self.user).pk)
        promoted = promote_candidate(candidate.pk, self.user)
        self.assertEqual(promoted.promoted_version.estado, "borrador")
        with self.assertRaises(ValidationError):
            promote_candidate(candidate.pk, self.user)

    def test_stale_updated_expired_disabled_rights_and_revoked_mapping_block_selection(self):
        candidate = self.mapped()
        self.assertEqual(candidate_data(candidate)["status"], "MAPPED")
        with self.settings(EC3_ENABLED=False):
            self.assertIsNone(select_material_factor(self.org, self.material, "kg", date.today())["factor_version"])
        with self.settings(EC3_STORAGE_ALLOWED=False):
            self.assertIsNone(select_material_factor(self.org, self.material, "kg", date.today())["factor_version"])
        self.ingest(steel_payload(version=2))
        self.assertEqual(candidate_data(candidate)["status"], "STALE")
        self.assertIsNone(select_material_factor(self.org, self.material, "kg", date.today())["factor_version"])
        revoke_material_mapping(candidate.mapping_id, self.org, self.user, "Synthetic revocation")
        self.assertIsNone(select_material_factor(self.org, self.material, "kg", date.today())["factor_version"])

    def test_expired_epd_never_eligible(self):
        payload = steel_payload()
        payload["valid_until"] = "2020-01-02T00:00:00Z"
        version = self.ingest(payload)
        self.assertIn("epd_expired", evaluate_version(version, "EF 3.0")["reasons"])

    def test_failure_run_does_not_withdraw_record(self):
        version = self.ingest()
        self.session.get.return_value = response({"secret": "do not log"}, status=404)
        with self.assertRaises(UpstreamError):
            self.ingest()
        version.record.refresh_from_db()
        self.assertEqual(version.record.estado, "activo")
        self.assertEqual(SyncRun.objects.latest("pk").message, "ec3_epd_not_found")
        self.assertIn("source_revalidation_failed", evaluate_version(version, "EF 3.0")["reasons"])
        self.assertEqual(version.record.source.sync_state.estado, "error")
        self.ingest(steel_payload())
        self.assertNotIn("source_revalidation_failed", evaluate_version(version, "EF 3.0")["reasons"])

    def test_evidence_and_review_history_immutable_orm_and_sql(self):
        candidate = self.approved()
        with self.assertRaises(ValidationError):
            EpdVersion.objects.filter(pk=candidate.epd_version_id).update(evidence={})
        with self.assertRaises(ValidationError):
            candidate.reviews.first().delete()
        if connection.vendor == "postgresql":
            with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
                cursor.execute("UPDATE ec3_epdversion SET evidence = '{}'::jsonb WHERE id = %s", [candidate.epd_version_id])
            with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
                cursor.execute("UPDATE ec3_candidate SET created_by_id = NULL WHERE id = %s", [candidate.pk])

    def test_promoted_factor_and_snapshot_cannot_be_rewritten(self):
        candidate = self.mapped()
        if connection.vendor != "postgresql":
            self.skipTest("Database guards require PostgreSQL")
        for sql, pk in [
            ("UPDATE analytics_factorambiental SET contexto = '{}'::jsonb WHERE id = %s", candidate.promoted_version.factor_id),
            ("UPDATE analytics_versionfactorambiental SET valor = 1 WHERE id = %s", candidate.promoted_version_id),
            ("UPDATE knowledge_externalsnapshot SET content_hash = 'tampered' WHERE id = %s", candidate.epd_version.snapshot_id),
        ]:
            with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(sql, [pk])

    def test_api_permissions_disabled_validation_no_secrets(self):
        self.api.force_authenticate(None)
        self.assertIn(self.api.get("/api/integrations/ec3/search/").status_code, (401, 403))
        user = get_user_model().objects.create_user("tenant-admin", password="test", is_staff=True)
        UsuarioOrganizacion.objects.create(user=user, organizacion=self.org, rol="admin", activo=True)
        self.api.force_authenticate(user)
        self.assertEqual(self.api.get("/api/integrations/ec3/search/").status_code, 403)
        self.api.force_authenticate(self.user)
        with self.settings(EC3_ENABLED=False):
            self.assertEqual(self.api.get("/api/integrations/ec3/search/").status_code, 400)
        invalid = self.api.post("/api/integrations/ec3/candidates/", {"material_id": True, "ai_confirmed": True}, format="json")
        self.assertEqual(invalid.status_code, 400)
        self.assertNotIn("synthetic-token", str(invalid.data))

    def test_api_full_governed_sequence_and_status(self):
        with patch("apps.ec3.services.Ec3Client", return_value=self.client):
            imported = self.api.post("/api/integrations/ec3/epds/ec3test1/ingest/", {}, format="json")
        self.assertEqual(imported.status_code, 201, imported.data)
        proposed = self.api.post("/api/integrations/ec3/candidates/", {"material_id": self.material.pk,
            "epd_version_id": imported.data["epd_version_id"]}, format="json")
        self.assertEqual(proposed.status_code, 201, proposed.data)
        pk = proposed.data["id"]
        reviewed = self.api.post(f"/api/integrations/ec3/candidates/{pk}/review/",
            {"decision": "approved", "lcia_method": "EF 3.0", "context": CONTEXT}, format="json")
        self.assertEqual(reviewed.status_code, 200, reviewed.data)
        promoted = self.api.post(f"/api/integrations/ec3/candidates/{pk}/promote/", {}, format="json")
        self.assertEqual(promoted.status_code, 201, promoted.data)
        mapped = self.api.post(f"/api/integrations/ec3/candidates/{pk}/mapping/", {"vigencia_desde": "2026-01-01"}, format="json")
        self.assertEqual(mapped.status_code, 201, mapped.data)
        self.assertEqual(mapped.data["status"], "REVIEW_REQUIRED")
        listing = self.api.get("/api/integrations/ec3/candidates/", {"material_id": self.material.pk})
        self.assertEqual(listing.data["count"], 1)

    def test_steel_e2e_work_activity_search_epd_mapping_eligible_calculation_provenance(self):
        ensure_system_environmental_catalog()
        at = timezone.make_aware(datetime(2026, 9, 12, 10))
        work = Obra.objects.create(organizacion=self.org, nombre="Obra acero EC3 mock", fecha_inicio=date(2026, 1, 1))
        source = FuenteDatos.objects.create(organizacion=self.org, nombre="Synthetic guide", tipo="manual")
        activity = ActividadOperacional.objects.create(organizacion=self.org, obra=work, codigo="EC3-E2E-ACT",
            nombre="Recepción de acero", tipo="movimiento_material", timestamp_inicio=at)
        observation = Observacion.objects.create(organizacion=self.org, actividad=activity, fuente=source,
            concepto="cantidad_material", valor_numerico=Decimal(1000), unidad="kg", timestamp_observacion=at,
            estado=Observacion.Estado.VALIDADA)
        EventoMaterial.objects.create(organizacion=self.org, material=self.material, actividad=activity, obra=work,
            tipo="recepcion", fecha_hora=at, observacion_cantidad=observation, fuente=source)
        self.session.get.return_value = response(search_payload())
        found = self.client.search('!EC3 search("StructuralSteel") !pragma oMF("1.0/1")', page_size=1)
        self.assertEqual(found["data"]["payload"][0]["id"], "ec3test1")
        self.session.get.return_value = response(steel_payload())
        candidate = self.mapped()
        selected = select_material_factor(self.org, self.material, "kg", date(2026, 9, 12))
        self.assertIsNotNone(selected["factor_version"], selected["reason"])
        calculation, _ = calculate_activity(activity)
        self.assertEqual(calculation.resultado, Decimal(1800))
        self.assertEqual(calculation.version_factor_id, candidate.promoted_version_id)
        historical_id = calculation.pk
        trace = calculation.version_factor.contexto["knowledge_source"]
        ledger = ledger_entry_provenance(calculation)
        self.assertEqual(ledger["external_source"], trace)
        self.assertEqual(ledger["ec3_candidate_id"], candidate.pk)
        self.assertEqual(ledger["quality"]["known"]["external_id"], "ec3test1")
        for key in ("source", "external_id", "epd", "upstream_version", "local_version", "retrieved_at",
                    "declared_unit", "lifecycle_scope", "checksum", "quality", "epd_version_id"):
            self.assertIsNotNone(trace[key], key)
        self.ingest(steel_payload(version=2, mean=1600))
        self.assertIsNone(select_material_factor(self.org, self.material, "kg", date(2026, 9, 12))["factor_version"])
        historical = CalculoAmbiental.objects.get(pk=historical_id)
        self.assertEqual(historical.resultado, Decimal(1800))
        self.assertEqual(historical.version_factor.contexto["knowledge_source"], trace)
        self.assertEqual(ledger_entry_provenance(historical)["external_source"], trace)
