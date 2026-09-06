from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from threading import Barrier, Thread
from .bootstrap import ensure_environmental_source_registry

from .legal_evidence import (
    activate_legal_evidence_requirement_version,
    create_legal_evidence_requirement,
    create_legal_evidence_requirement_version,
    get_legal_evidence_requirement_freshness,
    update_legal_evidence_requirement_draft,
    validate_legal_evidence_requirement_version,
)
from .legal_governance import (
    activate_legal_obligation_version,
    promote_legal_candidate,
    validate_legal_obligation_version,
)
from .models import LegalEvidenceRequirement, LegalEvidenceRequirementVersion, LegalObligationVersion
from .test_legal_governance import LegalGovernanceTests


VALID_FIELDS = {
    "title": "Mediciones del periodo",
    "requirement_statement": "Debe poder demostrarse la medicion realizada.",
    "proof_objective": "Demostrar que el monitoreo fue realizado.",
    "evidence_mode": "any_of",
    "evidence_classes": ["report", "measurement"],
    "accepted_evidence_descriptions": ["Informe de medicion", "Registro instrumental"],
    "temporal_scope": "periodic",
    "notes": "Interpretacion interna gobernada.",
}


class LegalEvidenceRequirementTests(LegalGovernanceTests):
    def active_obligation(self, candidate=None, target=None):
        obligation, version, _ = promote_legal_candidate(
            candidate or self.candidates[0], self.superuser,
            "new_version" if target else "create_obligation", target, [],
            modality="obligation", canonical_statement="Declaracion gobernada.",
            applicability_level="organization", applicability_mode="unconditional",
        )
        validate_legal_obligation_version(version, self.superuser)
        activate_legal_obligation_version(version, self.superuser)
        version.refresh_from_db()
        return obligation, version

    def requirement(self):
        obligation, legal_version = self.active_obligation()
        requirement, version = create_legal_evidence_requirement(
            obligation, legal_version, self.superuser, **VALID_FIELDS
        )
        return obligation, legal_version, requirement, version

    def govern(self, version):
        validate_legal_evidence_requirement_version(version, self.superuser)
        activate_legal_evidence_requirement_version(version, self.superuser)
        version.refresh_from_db()

    def test_create_active_only_stable_identity_and_frozen_basis(self):
        obligation, legal_version = self.active_obligation()
        for state in ("draft", "validated", "obsolete"):
            LegalObligationVersion.objects.filter(pk=legal_version.pk).update(state=state)
            legal_version.refresh_from_db()
            with self.assertRaises(ValidationError):
                create_legal_evidence_requirement(obligation, legal_version, self.superuser, **VALID_FIELDS)
        LegalObligationVersion.objects.filter(pk=legal_version.pk).update(state="active")
        legal_version.refresh_from_db()
        requirement, version = create_legal_evidence_requirement(
            obligation, legal_version, self.superuser, **VALID_FIELDS
        )
        self.assertTrue(requirement.code.startswith("ERQ-"))
        self.assertEqual((version.version, version.state), (1, "draft"))
        self.assertEqual(version.legal_basis_snapshot["obligation_code"], obligation.code)
        self.assertEqual(version.legal_basis_snapshot["source_provenance"], legal_version.source_provenance)

    def test_direct_creation_and_bulk_bypasses_are_blocked(self):
        obligation, legal_version, requirement, _ = self.requirement()
        base = dict(requirement=requirement, version=2, legal_obligation_version=legal_version, legal_basis_snapshot={}, created_by=self.superuser, **VALID_FIELDS)
        for state in ("validated", "active", "obsolete"):
            with self.assertRaises(ValidationError):LegalEvidenceRequirementVersion.objects.create(**base, state=state)
        LegalObligationVersion.objects.filter(pk=legal_version.pk).update(state="obsolete")
        legal_version.refresh_from_db()
        stale_base = {**base, "legal_obligation_version": legal_version}
        with self.assertRaises(ValidationError):LegalEvidenceRequirementVersion.objects.create(**stale_base)
        with self.assertRaises(ValidationError):LegalEvidenceRequirement.objects.bulk_create([LegalEvidenceRequirement(obligation=obligation)])
        with self.assertRaises(ValidationError):LegalEvidenceRequirementVersion.objects.bulk_create([])

    def test_stale_draft_and_validated_cannot_be_published(self):
        obligation, legal_v1, requirement, draft = self.requirement()
        _, legal_v2 = self.active_obligation(self.candidates[1], target=obligation)
        with self.assertRaises(ValidationError):validate_legal_evidence_requirement_version(draft, self.superuser)

        # Repeat with a validated requirement that becomes stale before activation.
        LegalObligationVersion.objects.filter(pk=legal_v2.pk).update(state="obsolete")
        LegalObligationVersion.objects.filter(pk=legal_v1.pk).update(state="active")
        second = create_legal_evidence_requirement_version(requirement, legal_v1, self.superuser, **VALID_FIELDS)
        validate_legal_evidence_requirement_version(second, self.superuser)
        LegalObligationVersion.objects.filter(pk=legal_v1.pk).update(state="obsolete")
        LegalObligationVersion.objects.filter(pk=legal_v2.pk).update(state="active")
        with self.assertRaises(ValidationError):activate_legal_evidence_requirement_version(second, self.superuser)

    def test_permissions_mismatch_and_validation_fail_closed(self):
        obligation, legal_version = self.active_obligation()
        with self.assertRaises(ValidationError):
            create_legal_evidence_requirement(obligation, legal_version, self.user, **VALID_FIELDS)
        requirement, version = create_legal_evidence_requirement(obligation, legal_version, self.superuser, **VALID_FIELDS)
        invalid = [
            {"evidence_mode": "inventado"}, {"evidence_classes": []},
            {"evidence_classes": ["inventada"]}, {"accepted_evidence_descriptions": []},
            {"proof_objective": ""}, {"requirement_statement": ""},
            {"temporal_scope": "inventado"},
        ]
        for changes in invalid:
            update_legal_evidence_requirement_draft(version, self.superuser, **changes)
            with self.assertRaises(ValidationError):
                validate_legal_evidence_requirement_version(version, self.superuser)
            update_legal_evidence_requirement_draft(version, self.superuser, **{key: VALID_FIELDS[key] for key in changes})

    def test_lifecycle_immutability_one_active_and_version_switch(self):
        obligation, legal_v1, requirement, v1 = self.requirement()
        update_legal_evidence_requirement_draft(v1, self.superuser, title="Titulo editado")
        self.govern(v1)
        v1.title = "No editable"
        with self.assertRaises(ValidationError):v1.save()
        v1.state = "obsolete"
        with self.assertRaises(ValidationError):v1.save()
        with self.assertRaises(ValidationError):v1.delete()
        with self.assertRaises(ValidationError):LegalEvidenceRequirementVersion.objects.filter(pk=v1.pk).delete()
        with self.assertRaises(ValidationError):requirement.delete()
        obligation, legal_v2 = self.active_obligation(self.candidates[1], target=obligation)
        v2 = create_legal_evidence_requirement_version(requirement, legal_v2, self.superuser, **VALID_FIELDS)
        self.govern(v2)
        v1.refresh_from_db()
        self.assertEqual((v1.state, v2.state), ("obsolete", "active"))
        self.assertEqual(requirement.versions.filter(state="active").count(), 1)

    def test_freshness_legal_version_contract_and_no_auto_obsolete(self):
        obligation, legal_v1, requirement, version = self.requirement()
        self.govern(version)
        self.assertEqual(get_legal_evidence_requirement_freshness(version), "fresh")
        obligation, legal_v2 = self.active_obligation(self.candidates[1], target=obligation)
        version.refresh_from_db()
        self.assertEqual(version.state, "active")
        self.assertEqual(get_legal_evidence_requirement_freshness(version), "stale_legal_version")
        LegalObligationVersion.objects.filter(pk=legal_v2.pk).update(canonical_statement="Corrupcion simulada")
        replacement = create_legal_evidence_requirement_version(requirement, legal_v2, self.superuser, **VALID_FIELDS)
        LegalObligationVersion.objects.filter(pk=legal_v2.pk).update(canonical_statement="Otra corrupcion")
        self.assertEqual(get_legal_evidence_requirement_freshness(replacement), "stale_legal_contract")

    def test_api_reads_writes_pagination_and_filters(self):
        obligation, legal_version, requirement, version = self.requirement()
        self.govern(version)
        client = APIClient()
        self.assertIn(client.get("/api/knowledge/legal-evidence-requirements/").status_code, (401, 403))
        client.force_authenticate(self.user)
        response = client.get("/api/knowledge/legal-evidence-requirements/?evidence_class=report&temporal_scope=periodic&freshness=fresh")
        self.assertEqual((response.status_code, response.data["count"]), (200, 1))
        self.assertNotIn("legal_basis_snapshot", response.data["results"][0])
        url = f"/api/knowledge/legal-obligations/{obligation.id}/evidence-requirements/"
        self.assertEqual(client.post(url, {"legal_obligation_version_id": legal_version.id}, format="json").status_code, 403)
        client.force_authenticate(self.superuser)
        payload = {**VALID_FIELDS, "legal_obligation_version_id": legal_version.id}
        self.assertEqual(client.post(url, payload, format="json").status_code, 201)
        self.assertEqual(client.post(url, {**payload, "campo_inventado": True}, format="json").status_code, 400)

    def test_three_requirement_smoke(self):
        obligation_a, legal_a = self.active_obligation(self.candidates[0])
        obligation_b, legal_b = self.active_obligation(self.candidates[1])
        specifications = [
            (obligation_a, legal_a, VALID_FIELDS),
            (obligation_b, legal_b, {**VALID_FIELDS, "evidence_classes": ["certificate"], "temporal_scope": "one_time"}),
            (obligation_a, legal_a, {**VALID_FIELDS, "evidence_mode": "all_of", "evidence_classes": ["manifest", "report"], "temporal_scope": "event_based"}),
        ]
        versions = []
        for obligation, legal_version, fields in specifications:
            _, version = create_legal_evidence_requirement(obligation, legal_version, self.superuser, **fields)
            self.govern(version)
            versions.append(version)
        self.assertEqual(LegalEvidenceRequirement.objects.count(), 3)
        self.assertEqual(LegalEvidenceRequirementVersion.objects.filter(state="active").count(), 3)
        self.assertEqual([get_legal_evidence_requirement_freshness(item) for item in versions], ["fresh"] * 3)


class LegalEvidenceConcurrencyTests(TransactionTestCase):
    _candidate = LegalGovernanceTests._candidate

    def _fixture_teardown(self):
        if connection.vendor != "postgresql":
            return super()._fixture_teardown()
        tables = connection.introspection.table_names()
        if tables:
            quoted = ", ".join(connection.ops.quote_name(table) for table in tables)
            with connection.cursor() as cursor:
                cursor.execute(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE")

    def setUp(self):
        ensure_environmental_source_registry()
        LegalGovernanceTests.setUp(self)
        obligation, legal_version, _ = promote_legal_candidate(
            self.candidates[0], self.superuser, "create_obligation", None, [],
            modality="obligation", canonical_statement="Base concurrente.",
            applicability_level="organization", applicability_mode="unconditional",
        )
        validate_legal_obligation_version(legal_version, self.superuser)
        activate_legal_obligation_version(legal_version, self.superuser)
        legal_version.refresh_from_db()
        requirement, _ = create_legal_evidence_requirement(
            obligation, legal_version, self.superuser, **VALID_FIELDS
        )
        self.requirement_id = requirement.id
        self.legal_version_id = legal_version.id

    def test_concurrent_version_numbers_are_serialized(self):
        if connection.vendor != "postgresql":
            self.skipTest("Concurrency locking is verified on PostgreSQL.")
        barrier = Barrier(2)
        errors = []

        def create_version():
            close_old_connections()
            try:
                barrier.wait()
                create_legal_evidence_requirement_version(
                    LegalEvidenceRequirement.objects.get(pk=self.requirement_id),
                    LegalObligationVersion.objects.get(pk=self.legal_version_id),
                    type(self.superuser).objects.get(pk=self.superuser.pk),
                    **VALID_FIELDS,
                )
            except Exception as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [Thread(target=create_version), Thread(target=create_version)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(20)
        self.assertEqual(errors, [])
        self.assertEqual(
            list(LegalEvidenceRequirementVersion.objects.filter(requirement_id=self.requirement_id).order_by("version").values_list("version", flat=True)),
            [1, 2, 3],
        )
        self.assertLessEqual(LegalEvidenceRequirementVersion.objects.filter(requirement_id=self.requirement_id, state="active").count(), 1)

    def test_concurrent_activation_is_serialized(self):
        if connection.vendor != "postgresql":
            self.skipTest("Concurrency locking is verified on PostgreSQL.")
        requirement = LegalEvidenceRequirement.objects.get(pk=self.requirement_id)
        legal_version = LegalObligationVersion.objects.get(pk=self.legal_version_id)
        versions = [requirement.versions.get(version=1), create_legal_evidence_requirement_version(requirement, legal_version, self.superuser, **VALID_FIELDS)]
        for version in versions:validate_legal_evidence_requirement_version(version, self.superuser)
        barrier = Barrier(2);errors = []
        def activate(pk):
            close_old_connections()
            try:
                barrier.wait();activate_legal_evidence_requirement_version(LegalEvidenceRequirementVersion.objects.get(pk=pk), type(self.superuser).objects.get(pk=self.superuser.pk))
            except Exception as exc:errors.append(exc)
            finally:close_old_connections()
        threads=[Thread(target=activate,args=(item.pk,)) for item in versions]
        for thread in threads:thread.start()
        for thread in threads:thread.join(20)
        self.assertEqual(errors, [])
        states=list(requirement.versions.values_list("state",flat=True))
        self.assertEqual((states.count("active"),states.count("obsolete")),(1,1))
