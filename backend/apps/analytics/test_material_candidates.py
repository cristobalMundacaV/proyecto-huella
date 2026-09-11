import copy
import json
from decimal import Decimal
from io import StringIO
from threading import Barrier, Thread
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import (
    connection,
    transaction,
    DatabaseError,
    IntegrityError,
    close_old_connections,
)
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.knowledge.bootstrap import ensure_environmental_source_registry
from apps.knowledge.models import (
    ExternalRecord,
    SourceState,
    EnvironmentalSource,
    OekobaudatEnvironmentalProfileFact as Profile,
)
from apps.knowledge.okobaudat_detail_sync import hydrate_process
from apps.knowledge import test_okobaudat_detail as detail_tests
from apps.knowledge.test_okobaudat_detail import make_process, fetch
from .models import (
    MaterialEnvironmentalFactorCandidate as Candidate,
    MaterialFactorCandidateReview as Review,
    FactorAmbiental,
    VersionFactorAmbiental,
    Organizacion,
    UsuarioOrganizacion,
)
from .services.material_candidates import (
    build_material_candidate,
    build_material_candidates,
    evaluate_material_profile,
    review_material_candidate,
    promote_material_candidate,
    governed_write,
)


def material_fixture(label="a2"):
    ensure_environmental_source_registry()
    process, run = make_process(label)
    now = timezone.now()
    ExternalRecord.objects.create(
        source=run.source,
        external_id=process.snapshot.external_id,
        kind="okobaudat_process",
        current_snapshot=process.snapshot,
        first_seen_at=now,
        last_seen_at=now,
    )
    SourceState.objects.filter(source=run.source).update(
        estado="actualizada", last_successful_sync_at=now
    )
    with patch(
        "apps.knowledge.okobaudat_detail_sync.fetch_detail_bytes", side_effect=fetch
    ):
        result = hydrate_process(process, run, delay=0)
    assert result["status"] == "materialized", result
    return Profile.objects.get(process=process)


class MaterialCandidateTests(TestCase):
    def setUp(self):
        self.profile = material_fixture()
        self.user = get_user_model().objects.create_superuser(
            "material-reviewer", "", "password"
        )

    def build(self):
        return build_material_candidate(self.profile.pk)[0]

    def approve(self):
        candidate = self.build()
        return review_material_candidate(
            candidate.pk,
            self.user,
            "approved",
            "Verified A1-A3",
            {"intended_use": "Inventory research"},
        )

    def test_real_a2_1000_kg_total_only_and_provenance(self):
        candidate = self.build()
        result = candidate.normalization
        self.assertEqual(result["normalized_factor_value"], "0.847351015163189")
        self.assertEqual(result["raw_gwp_value"], "847.351015163189")
        self.assertEqual(result["declared_quantity"], "1000")
        self.assertEqual(
            (
                result["normalized_input_unit"],
                result["normalized_result_unit"],
                result["standard"],
                result["boundary"],
            ),
            ("kg", "kgCO2e", "EN 15804+A2", "A1-A3"),
        )
        self.assertEqual(len(candidate.provenance["references"]), 3)
        self.assertEqual(len(candidate.provenance["gwp_components"]), 3)
        self.assertEqual(candidate.source_indicator.code, "GWP-total")
        self.assertEqual(candidate.provenance["snapshot_id"], self.profile.snapshot_id)
        self.assertTrue(candidate.initial_eligibility["compatible"])
        self.assertEqual(candidate.status, Candidate.Status.REVIEW)
        self.assertIsNone(candidate.promoted_factor_id)

    def test_a1_legacy_remains_separate_and_negative_value(self):
        first = self.build()
        profile = material_fixture("a1")
        second, _, _ = build_material_candidate(profile.pk)
        self.assertEqual(second.normalization["standard"], "EN 15804+A1")
        self.assertEqual(second.normalization["indicator"], "GWP")
        self.assertEqual(Decimal(second.normalization["declared_quantity"]), 1)
        self.assertEqual(
            Decimal(second.normalization["normalized_factor_value"]),
            Decimal("-647.4201396839651"),
        )
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(second.functional_context["functional_equivalence"], "unknown")

    def test_missing_total_neither_fossil_nor_sum_is_substitute(self):
        rows = list(self.profile.indicators.exclude(code="GWP-total"))
        with patch.object(type(self.profile.indicators), "all", return_value=rows):
            result = evaluate_material_profile(self.profile)
        self.assertFalse(result["compatible"])
        self.assertIn("missing_gwp", result["reasons"])
        self.assertIsNone(result["normalization"]["normalized_factor_value"])
        self.assertEqual(len(result["provenance"]["gwp_components"]), 3)

    def test_a2_refuses_legacy_indicator_and_identity_conflict(self):
        rows = list(self.profile.indicators.all())
        indicator = next(row for row in rows if row.code == "GWP-total")
        indicator.standard = "EN 15804+A1"
        with patch.object(type(self.profile.indicators), "all", return_value=rows):
            self.assertIn(
                "invalid_indicator_identity",
                evaluate_material_profile(self.profile)["reasons"],
            )

    def test_declared_quantity_greater_than_one(self):
        self.profile.declared_amount = "2"
        result = evaluate_material_profile(self.profile)
        self.assertEqual(
            Decimal(result["normalization"]["normalized_factor_value"]),
            Decimal("847.351015163189") / 2,
        )

    def test_invalid_quantity(self):
        for quantity in ("0", "-1", "NaN", "Infinity", "bad"):
            self.profile.declared_amount = quantity
            self.assertIn(
                "invalid_declared_quantity",
                evaluate_material_profile(self.profile)["reasons"],
            )

    def test_unknown_input_and_result_unit_fail_closed(self):
        self.profile.declared_unit = "bucket"
        self.assertIn(
            "unsupported_unit", evaluate_material_profile(self.profile)["reasons"]
        )
        self.profile.declared_unit = "kg"
        rows = list(self.profile.indicators.all())
        next(row for row in rows if row.code == "GWP-total").unit = "kg fossil"
        with patch.object(type(self.profile.indicators), "all", return_value=rows):
            self.assertIn(
                "unsupported_unit", evaluate_material_profile(self.profile)["reasons"]
            )

    def test_incomplete_provenance(self):
        for missing in ({}, None, [], {"references": None}):
            self.profile.provenance = missing
            self.assertIn(
                "incomplete_provenance",
                evaluate_material_profile(self.profile)["reasons"],
            )

    def test_incomplete_boundary_wrong_unit_identity_and_storage_limits(self):
        rows = list(self.profile.indicators.all())
        indicator = next(row for row in rows if row.code == "GWP-total")
        for field, value, reason in (
            ("module", "A4", "incomplete_a1a3"),
            ("unit_uuid", "00000000-0000-0000-0000-000000000000", "unsupported_unit"),
            ("value", "NaN", "invalid_gwp"),
            ("value", "1e30", "factor_storage_out_of_range"),
            ("value", "1e-30", "factor_storage_out_of_range"),
        ):
            original = getattr(indicator, field)
            setattr(indicator, field, value)
            with self.subTest(field=field, value=value), patch.object(
                type(self.profile.indicators), "all", return_value=rows
            ):
                self.assertIn(
                    reason, evaluate_material_profile(self.profile)["reasons"]
                )
            setattr(indicator, field, original)

    def test_historical_detection_is_consultable_but_cannot_be_approved(self):
        ExternalRecord.objects.filter(
            current_snapshot=self.profile.process.snapshot
        ).update(estado="no_observado")
        candidate, created, result = build_material_candidate(self.profile.pk)
        self.assertTrue(created)
        self.assertFalse(result["compatible"])
        self.assertEqual(candidate.status, Candidate.Status.DETECTED)
        with self.assertRaises(ValidationError):
            review_material_candidate(candidate.pk, self.user, "approved")
        review_material_candidate(
            candidate.pk, self.user, "rejected", "Historical source"
        )
        self.assertEqual(build_material_candidates()["existing"], 1)
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, Candidate.Status.REJECTED)

    def test_a1_promotion_preserves_legacy_standard_and_unknown_equivalence(self):
        profile = material_fixture("a1")
        candidate = build_material_candidate(profile.pk)[0]
        review_material_candidate(candidate.pk, self.user, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.user)
        version.refresh_from_db()
        self.assertEqual(version.valor, Decimal("-647.4201396840"))
        self.assertEqual(factor.contexto["standard"], "EN 15804+A1")
        self.assertEqual(version.contexto["indicator"], "GWP")
        self.assertEqual(
            factor.contexto["functional_context"]["functional_equivalence"], "unknown"
        )
        self.assertEqual(version.estado, "borrador")

    def test_unknown_standard_and_missing_technical_metadata(self):
        result = evaluate_material_profile(self.profile)
        for field in (
            "technical_properties",
            "functional_equivalence",
            "intended_use",
            "owner_manufacturer",
        ):
            self.assertEqual(result["functional_context"][field], "unknown")
        self.profile.standard = "unknown"
        self.assertFalse(evaluate_material_profile(self.profile)["compatible"])

    def test_historical_withdrawn_and_source_disabled_fail_closed(self):
        candidate = self.approve()
        ExternalRecord.objects.filter(
            current_snapshot=self.profile.process.snapshot
        ).update(estado="retirado")
        self.assertIn(
            "historical_source", evaluate_material_profile(self.profile)["reasons"]
        )
        with self.assertRaises(ValidationError):
            promote_material_candidate(candidate.pk, self.user)
        self.assertTrue(Candidate.objects.filter(pk=candidate.pk).exists())
        ExternalRecord.objects.update(estado="activo")
        EnvironmentalSource.objects.filter(codigo="okobaudat").update(activa=False)
        self.assertFalse(evaluate_material_profile(self.profile)["source_current"])

    def test_newer_published_version_and_syncing_block_promotion(self):
        candidate = self.approve()
        process, run = make_process(version="00.01.001")
        ExternalRecord.objects.create(
            source=run.source,
            external_id=process.snapshot.external_id,
            kind="okobaudat_process",
            current_snapshot=process.snapshot,
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        self.assertFalse(evaluate_material_profile(self.profile)["source_current"])
        with self.assertRaises(ValidationError):
            promote_material_candidate(candidate.pk, self.user)
        ExternalRecord.objects.filter(current_snapshot=process.snapshot).delete()
        SourceState.objects.filter(source=run.source).update(estado="sincronizando")
        with self.assertRaises(ValidationError):
            promote_material_candidate(candidate.pk, self.user)

    def test_build_is_idempotent_and_preserves_review(self):
        candidate = self.approve()
        original = copy.deepcopy(candidate.provenance)
        self.assertEqual(build_material_candidates()["existing"], 1)
        candidate.refresh_from_db()
        self.assertEqual(candidate.provenance, original)
        self.assertEqual(candidate.status, Candidate.Status.READY)
        self.assertEqual(candidate.reviews.count(), 1)

    def test_review_reject_reapprove_append_only(self):
        candidate = self.approve()
        review_material_candidate(candidate.pk, self.user, "rejected", "Unsuitable")
        with self.assertRaises(ValidationError):
            promote_material_candidate(candidate.pk, self.user)
        review_material_candidate(
            candidate.pk, self.user, "approved", "New human review"
        )
        self.assertEqual(
            list(candidate.reviews.order_by("pk").values_list("decision", flat=True)),
            ["approved", "rejected", "approved"],
        )
        with self.assertRaises(ValidationError):
            candidate.reviews.first().save()
        with self.assertRaises(ValidationError):
            Review.objects.all().update(note="rewrite")

    def test_no_functional_mapping_inferred_or_accepted(self):
        candidate = self.build()
        with self.assertRaises(ValidationError):
            review_material_candidate(
                candidate.pk,
                self.user,
                "approved",
                context={"equivalent_material_id": 1},
            )
        with self.assertRaises(ValidationError):
            review_material_candidate(
                candidate.pk,
                self.user,
                "approved",
                context={"intended_use": {"strength": 40}},
            )
        self.assertEqual(
            candidate.functional_context["comparison_status"], "requires_review"
        )

    def test_unauthorized_and_inactive_service_users(self):
        candidate = self.build()
        user = get_user_model().objects.create_user("tenant-admin", is_staff=True)
        for actor in (user, None):
            with self.assertRaises(PermissionDenied):
                review_material_candidate(candidate.pk, actor, "approved")
            with self.assertRaises(PermissionDenied):
                promote_material_candidate(candidate.pk, actor)
        self.user.is_active = False
        with self.assertRaises(PermissionDenied):
            promote_material_candidate(candidate.pk, self.user)

    def test_promotion_requires_review_and_never_activates(self):
        candidate = self.build()
        with self.assertRaises(ValidationError):
            promote_material_candidate(candidate.pk, self.user)
        self.approve()
        factor, version = promote_material_candidate(candidate.pk, self.user)
        candidate.refresh_from_db()
        version.refresh_from_db()
        self.assertEqual(version.estado, VersionFactorAmbiental.Estado.BORRADOR)
        self.assertEqual(version.valor, Decimal("0.8473510152"))
        self.assertEqual(
            factor.contexto["normalized_factor_value"], "0.847351015163189"
        )
        self.assertIsNone(factor.organizacion_id)
        self.assertEqual(factor.material_source_candidate, candidate)
        self.assertEqual(version.material_source_candidate, candidate)
        self.assertEqual(candidate.promoted_by, self.user)
        self.assertEqual(candidate.reviews.first().note, "Verified A1-A3")
        with self.assertRaises(ValidationError):
            promote_material_candidate(candidate.pk, self.user)
        with self.assertRaises(ValidationError):
            review_material_candidate(candidate.pk, self.user, "rejected")
        self.assertEqual(factor.versiones.count(), 1)
        self.assertFalse(factor.versiones.filter(estado="activo").exists())

    def test_promotion_transaction_rolls_back_after_factor_insert(self):
        candidate = self.approve()
        before = FactorAmbiental.objects.count()
        with patch.object(
            VersionFactorAmbiental.objects,
            "create",
            side_effect=RuntimeError("injected"),
        ):
            with self.assertRaises(RuntimeError):
                promote_material_candidate(candidate.pk, self.user)
        self.assertEqual(FactorAmbiental.objects.count(), before)
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, Candidate.Status.READY)
        self.assertIsNone(candidate.promoted_factor_id)

    def test_orm_evidence_and_factor_provenance_cannot_be_rewritten(self):
        candidate = self.approve()
        factor, version = promote_material_candidate(candidate.pk, self.user)
        factor.contexto = {}
        with self.assertRaises(ValidationError):
            factor.save()
        version.valor = 7
        with self.assertRaises(ValidationError):
            version.save()
        candidate.normalization = {}
        with governed_write(), self.assertRaises(ValidationError):
            candidate.save()
        with self.assertRaises(ValidationError):
            Candidate.objects.all().delete()

    def test_command_summary_and_no_automatic_promotion(self):
        for expected in ("created", "existing"):
            output = StringIO()
            call_command("build_okobaudat_material_factor_candidates", stdout=output)
            result = json.loads(output.getvalue())
            self.assertEqual(result[expected], 1)
            self.assertEqual(result["a2"], 1)
            self.assertEqual(result["eligible"], 1)
        self.assertFalse(
            Candidate.objects.filter(promoted_factor__isnull=False).exists()
        )

    def test_api_auth_rbac_no_idor_filters_explicit_actions(self):
        item = self.build()
        client = APIClient()
        base = "/api/environmental-governance/material-factor-candidates/"
        paths = [
            base,
            base + f"{item.pk}/",
            base + f"{item.pk}/eligibility/",
            base + "999999/",
        ]
        for path in paths:
            self.assertIn(client.get(path).status_code, (401, 403))
        tenant_user = get_user_model().objects.create_user("ordinary", is_staff=True)
        own_tenant = Organizacion.objects.create(nombre="Material tenant A")
        other_tenant = Organizacion.objects.create(nombre="Material tenant B")
        UsuarioOrganizacion.objects.create(
            user=tenant_user, organizacion=own_tenant, rol="admin"
        )
        client.force_authenticate(tenant_user)
        for tenant in (own_tenant, other_tenant):
            self.assertEqual(
                client.get(base, {"organizacion": tenant.pk}).status_code, 403
            )
        for path in paths:
            self.assertEqual(client.get(path).status_code, 403)
        for action in ("review", "promote"):
            for pk in (item.pk, 999999):
                self.assertEqual(
                    client.post(
                        base + f"{pk}/{action}/", {}, format="json"
                    ).status_code,
                    403,
                )
        client.force_authenticate(self.user)
        for key, value in {
            "status": item.status,
            "standard": "EN 15804+A2",
            "uuid": str(self.profile.process_uuid),
            "dataset_version": self.profile.dataset_version,
            "classification": "fixture",
            "input_unit": "kg",
        }.items():
            response = client.get(base, {key: value})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["count"], 1)
        self.assertEqual(client.get(base, {"standard": "EN 15804+A1"}).data["count"], 0)
        self.assertEqual(client.get(base, {"classification": "fixt"}).data["count"], 0)
        self.assertEqual(client.get(base, {"location": "unknown"}).data["count"], 0)
        self.assertEqual(client.get(base, {"uuid": "bad"}).status_code, 400)
        self.assertEqual(client.get(base + "999999/").status_code, 404)
        self.assertEqual(
            client.patch(
                base + f"{item.pk}/", {"status": "promoted_to_draft"}
            ).status_code,
            405,
        )
        self.assertEqual(
            client.post(
                base + f"{item.pk}/review/",
                {"decision": "approved", "note": "API human"},
                format="json",
            ).status_code,
            200,
        )
        self.assertEqual(
            client.post(
                base + f"{item.pk}/promote/", {"organizacion": 1}, format="json"
            ).status_code,
            400,
        )
        response = client.post(base + f"{item.pk}/promote/", {}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["estado"], "borrador")
        self.assertEqual(
            client.post(base + f"{item.pk}/promote/", {}, format="json").status_code,
            400,
        )


class MaterialPostgresTests(TransactionTestCase):
    _fixture_teardown = detail_tests.DetailPostgresTests._fixture_teardown

    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("Requires PostgreSQL")
        self.profile = material_fixture()
        self.user = get_user_model().objects.create_superuser(
            "concurrent-reviewer", "", "password"
        )

    def concurrent(self, action):
        barrier = Barrier(2)
        results = []
        errors = []

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                results.append(action())
            except Exception as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        workers = [Thread(target=worker) for _ in range(2)]
        for thread in workers:
            thread.start()
        for thread in workers:
            thread.join(20)
        self.assertTrue(all(not thread.is_alive() for thread in workers))
        return results, errors

    def test_concurrent_build_unique_profile(self):
        results, errors = self.concurrent(
            lambda: build_material_candidate(self.profile.pk)[1]
        )
        self.assertFalse(errors, errors)
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(Candidate.objects.count(), 1)

    def test_concurrent_promotion_one_draft(self):
        candidate = build_material_candidate(self.profile.pk)[0]
        review_material_candidate(candidate.pk, self.user, "approved")
        results, errors = self.concurrent(
            lambda: promote_material_candidate(candidate.pk, self.user)[1].pk
        )
        self.assertEqual(len(results), 1, errors)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ValidationError)
        candidate.refresh_from_db()
        self.assertEqual(candidate.promoted_version_id, results[0])
        self.assertEqual(candidate.promoted_factor.versiones.count(), 1)
        self.assertEqual(candidate.promoted_version.estado, "borrador")

    def test_sql_constraints_and_immutable_provenance(self):
        candidate = build_material_candidate(self.profile.pk)[0]
        table = Candidate._meta.db_table
        for assignment, constraint in (
            ("status='invalid'", "material_candidate_valid_status"),
            ("promoted_at=NOW()", "material_candidate_promotion_pair"),
        ):
            with self.assertRaises(
                IntegrityError
            ) as caught, transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(f"UPDATE {table} SET {assignment}")
            self.assertEqual(
                caught.exception.__cause__.diag.constraint_name, constraint
            )
        for sql in (
            f"UPDATE {table} SET status='ready_for_review'",
            f"UPDATE {table} SET normalization='{{}}'",
            f"DELETE FROM {table}",
        ):
            with self.assertRaises(
                DatabaseError
            ), transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(sql)
        columns = ", ".join(
            connection.ops.quote_name(f.column)
            for f in Candidate._meta.fields
            if not f.primary_key
        )
        with self.assertRaises(
            IntegrityError
        ), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {table} ({columns}) SELECT {columns} FROM {table}"
            )
        review_material_candidate(candidate.pk, self.user, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.user)
        for sql in (
            f"UPDATE {table} SET status='rejected'",
            f"UPDATE {Review._meta.db_table} SET note='rewrite'",
            f"DELETE FROM {Review._meta.db_table}",
            f"UPDATE analytics_factorambiental SET contexto='{{}}' WHERE id={factor.pk}",
            f"UPDATE analytics_versionfactorambiental SET valor=2 WHERE id={version.pk}",
        ):
            with self.assertRaises(
                DatabaseError
            ), transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(sql)
