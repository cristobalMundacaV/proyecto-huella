from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from threading import Barrier, Thread
from unittest.mock import patch

from .models import LegalEvidenceOperationalLink, LegalEvidenceRequirementSufficiencyReview, Organizacion, UsuarioOrganizacion, VersionEvidencia
from .services.legal_applicability import evaluate_active_legal_obligations_for_organization
from .services.legal_evidence_mapping import create_operational_evidence_link, publish_legal_evidence_operational_mapping, withdraw_legal_evidence_link
from .services.legal_evidence_sufficiency import build_evidence_class_coverage, get_legal_evidence_sufficiency_review_freshness, review_legal_evidence_sufficiency
from .test_legal_evidence_mapping import LegalEvidenceMappingConcurrencyTests, LegalEvidenceMappingTests


class LegalEvidenceSufficiencyTests(LegalEvidenceMappingTests):
    def setup_basis(self, with_link=True):
        requirement, version = self.governed()
        mapping, _ = publish_legal_evidence_operational_mapping(version, [{"evidence_class": "report", "evidence_type": "informe_medicion_ruido", "note": ""}, {"evidence_class": "measurement", "evidence_type": "registro_sonometro", "note": ""}], self.superuser)
        link = None
        if with_link:
            evidence, evidence_version = self.evidence()
            link, _ = create_operational_evidence_link(requirement.code, self.organization, None, evidence, evidence_version, self.superuser)
        return requirement, version, mapping, link

    def test_zero_links_contract_and_human_decision(self):
        requirement, _, _, _ = self.setup_basis(False)
        pending, created = review_legal_evidence_sufficiency(requirement.code, self.organization, None, "pending", "Revision humana pendiente", self.superuser)
        self.assertTrue(created); self.assertEqual(pending.evidence_bundle_snapshot["coverage"]["link_count"], 0)
        insufficient, _ = review_legal_evidence_sufficiency(requirement.code, self.organization, None, "insufficient", "No hay evidencia", self.superuser)
        self.assertEqual(insufficient.revision, 2)
        with self.assertRaises(ValidationError):
            review_legal_evidence_sufficiency(requirement.code, self.organization, None, "sufficient", "Basta", self.superuser)

    def test_snapshot_hash_idempotency_revisions_and_immutability(self):
        requirement, _, _, link = self.setup_basis()
        first, created = review_legal_evidence_sufficiency(requirement.code, self.organization, None, "sufficient", "Revision documental humana", self.superuser)
        same, created_again = review_legal_evidence_sufficiency(requirement.code, self.organization, None, "sufficient", "Revision documental humana", self.superuser)
        self.assertTrue(created); self.assertFalse(created_again); self.assertEqual(first.pk, same.pk)
        self.assertEqual(first.evidence_bundle_snapshot["links"][0]["link_id"], link.id)
        self.assertEqual(first.evidence_bundle_snapshot["coverage"], {"required_classes": ["measurement", "report"], "linked_classes": ["report"], "unlinked_classes": ["measurement"], "link_count": 1, "coverage_complete": False})
        second, _ = review_legal_evidence_sufficiency(requirement.code, self.organization, None, "insufficient", "Revision humana distinta", self.superuser)
        first.refresh_from_db(); self.assertFalse(first.is_latest); self.assertEqual(second.revision, 2)
        with self.assertRaises(ValidationError): first.save()
        with self.assertRaises(ValidationError): first.delete()
        with self.assertRaises(ValidationError): LegalEvidenceRequirementSufficiencyReview.objects.filter(pk=first.pk).delete()
        with self.assertRaises(ValidationError): LegalEvidenceRequirementSufficiencyReview.objects.bulk_create([])

    def test_freshness_evidence_version_and_link_set(self):
        requirement, _, _, link = self.setup_basis()
        review, _ = review_legal_evidence_sufficiency(requirement.code, self.organization, None, "sufficient", "Evidencia revisada", self.superuser)
        self.assertEqual(get_legal_evidence_sufficiency_review_freshness(review), "fresh")
        VersionEvidencia.objects.create(evidencia=link.evidence, organizacion=self.organization, version=2, archivo=link.evidence_version.archivo, nombre_original="next.pdf", checksum_sha256="b" * 64)
        self.assertEqual(get_legal_evidence_sufficiency_review_freshness(review), "stale_evidence_version")

    def test_withdraw_and_add_make_link_set_stale(self):
        requirement, _, _, link = self.setup_basis()
        review, _ = review_legal_evidence_sufficiency(requirement.code, self.organization, None, "sufficient", "Evidencia revisada", self.superuser)
        withdraw_legal_evidence_link(link, self.superuser, "Retiro")
        self.assertEqual(get_legal_evidence_sufficiency_review_freshness(review), "stale_link_set")

    def test_direct_fake_snapshot_rejected(self):
        requirement, version, mapping, _ = self.setup_basis(False)
        assessment = version.requirement.obligation.applicability_assessments.get(is_latest=True, organization=self.organization)
        with self.assertRaises(ValidationError):
            LegalEvidenceRequirementSufficiencyReview.objects.create(organization=self.organization, scope_level="organization", requirement=requirement, requirement_version=version, mapping_revision=mapping, applicability_assessment=assessment, revision=1, decision="pending", rationale="Humana", requirement_snapshot={"fake": True}, mapping_snapshot={}, applicability_snapshot={}, evidence_bundle_snapshot={"links": []}, basis_hash="a" * 64, review_hash="b" * 64, reviewed_by=self.superuser, reviewed_at=assessment.evaluated_at)

    def test_api_and_service_rbac_and_strict_payload(self):
        requirement, _, _, _ = self.setup_basis(False)
        User = get_user_model()
        reader = User.objects.create_user("suff-reader")
        manager = User.objects.create_user("suff-manager")
        reviewer = User.objects.create_user("suff-reviewer")
        for user, role in ((reader, "lector"), (manager, "responsable_ambiental"), (reviewer, "revisor_ambiental")):
            UsuarioOrganizacion.objects.create(user=user, organizacion=self.organization, rol=role, alcance="organizacion")
        base = f"/api/organizaciones/{self.organization.organizacion_id}/evidencia-legal/requisitos/{requirement.code}/suficiencia"
        client = APIClient()
        self.assertIn(client.get(base + "/").status_code, (401, 403))
        client.force_authenticate(reader); self.assertEqual(client.get(base + "/").status_code, 200); self.assertEqual(client.post(base + "/revisar/", {"decision": "pending", "rationale": "Humana"}, format="json").status_code, 403)
        client.force_authenticate(manager); self.assertEqual(client.post(base + "/revisar/", {"decision": "pending", "rationale": "Humana"}, format="json").status_code, 403)
        with self.assertRaises(Exception): review_legal_evidence_sufficiency(requirement.code, self.organization, None, "pending", "Humana", manager)
        client.force_authenticate(reviewer)
        self.assertEqual(client.post(base + "/revisar/", {"decision": "pending", "rationale": "Humana", "link_ids": []}, format="json").status_code, 400)
        response = client.post(base + "/revisar/", {"decision": "pending", "rationale": "Decision humana"}, format="json")
        self.assertEqual(response.status_code, 201); self.assertEqual(response.data["decision"], "pending")
        self.assertEqual(client.get(base + "/historial/").status_code, 200)

    def test_failed_supersession_rolls_back_latest(self):
        requirement, _, _, _ = self.setup_basis(False)
        first, _ = review_legal_evidence_sufficiency(requirement.code, self.organization, None, "pending", "Primera revision", self.superuser)
        with patch.object(LegalEvidenceRequirementSufficiencyReview, "save", side_effect=ValidationError("fallo simulado")):
            with self.assertRaises(ValidationError):
                review_legal_evidence_sufficiency(requirement.code, self.organization, None, "insufficient", "Segunda revision", self.superuser)
        first.refresh_from_db()
        self.assertTrue(first.is_latest); self.assertEqual(LegalEvidenceRequirementSufficiencyReview.objects.count(), 1)


class LegalEvidenceSufficiencyPostgresTests(LegalEvidenceMappingConcurrencyTests):
    def test_review_concurrency_is_serial_and_idempotent(self):
        if connection.vendor != "postgresql": self.skipTest("PostgreSQL locking regression")
        publish_legal_evidence_operational_mapping(self.requirement_version, [{"evidence_class": "report", "evidence_type": "informe_medicion_ruido", "note": ""}, {"evidence_class": "measurement", "evidence_type": "registro_sonometro", "note": ""}], self.superuser)
        barrier = Barrier(2); results = []; errors = []
        def review(rationale):
            close_old_connections()
            try:
                barrier.wait()
                results.append(review_legal_evidence_sufficiency(self.requirement_obj.code, Organizacion.objects.get(pk=self.organization.pk), None, "pending", rationale, type(self.superuser).objects.get(pk=self.superuser.pk))[1])
            except Exception as exc: errors.append(exc)
            finally: close_old_connections()
        threads = [Thread(target=review, args=("Misma revision humana",)) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(20)
        self.assertEqual(errors, []); self.assertEqual(sorted(results), [False, True])
        self.assertEqual(LegalEvidenceRequirementSufficiencyReview.objects.filter(is_latest=True).count(), 1)
        self.assertEqual(LegalEvidenceRequirementSufficiencyReview.objects.count(), 1)

        barrier = Barrier(2); results = []; errors = []
        threads = [Thread(target=review, args=(text,)) for text in ("Revision A", "Revision B")]
        for thread in threads: thread.start()
        for thread in threads: thread.join(20)
        self.assertEqual(errors, []); self.assertEqual(len(results), 2)
        self.assertEqual(list(LegalEvidenceRequirementSufficiencyReview.objects.order_by("revision").values_list("revision", flat=True)), [1, 2, 3])
        self.assertEqual(LegalEvidenceRequirementSufficiencyReview.objects.filter(is_latest=True).count(), 1)
