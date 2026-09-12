from datetime import date
from decimal import Decimal
from threading import Barrier, Thread

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections
from django.test import TestCase, TransactionTestCase
from rest_framework.exceptions import PermissionDenied

from apps.knowledge import test_okobaudat_detail as detail_tests

from .models import MaterialOperacional, Organizacion, UsuarioOrganizacion
from .models.material_application_profile import MaterialApplicationProfile
from .models.material_functional_use import MaterialApplicationAssessment, MaterialFunctionalUse
from .services.material_application_profile import approve_profile, create_profile
from .services.material_functional_use import (
    approve_functional_use,
    create_functional_use,
    reject_functional_use,
)
from .services.material_suitability import decide_human_approval, evaluate_application, record_assessment
from .services.material_technical_property import approve_assertion, create_assertion

User = get_user_model()
Tipo = None  # set in setUp via import to avoid unused-import churn


class SuitabilityEvaluationTests(TestCase):
    def setUp(self):
        from .models.material_technical_property import MaterialTechnicalPropertyAssertion

        self.Tipo = MaterialTechnicalPropertyAssertion.TipoPropiedad
        self.Provenance = MaterialTechnicalPropertyAssertion.TipoProvenance

        self.org = Organizacion.objects.create(nombre="Suitability org")
        self.other_org = Organizacion.objects.create(nombre="Otro tenant suitability")
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-SUIT", nombre="Hormigón", categoria="hormigon", unidad_base="kg",
        )
        self.manager = User.objects.create_user("gestor-suit", "gestor-suit@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.manager, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ANALISTA,
        )
        self.approver = User.objects.create_user("aprobador-suit", "aprobador-suit@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.approver, organizacion=self.org, rol=UsuarioOrganizacion.Rol.REVISOR_AMBIENTAL,
        )
        self.reader = User.objects.create_user("lector-suit", "lector-suit@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.reader, organizacion=self.org, rol=UsuarioOrganizacion.Rol.LECTOR,
        )

        profile = create_profile(
            self.org, self.manager, "MURO-SUIT", "Muro estructural", Decimal("1"), "m2",
            requisitos=[
                {"key": "resistencia", "type": "numeric", "operator": "gte", "value": 25, "unit": "kg"},
                {"key": "clase", "type": "categorical", "operator": "equals", "value": "estructural"},
            ],
        )
        self.profile = approve_profile(profile.pk, self.org, self.approver)

    def _approve_numeric(self, key, value, unit="kg"):
        assertion = create_assertion(
            self.org, self.manager, self.material, key, self.Tipo.NUMERIC,
            self.Provenance.TECHNICAL_SPEC, date(2026, 1, 1), value_numeric=Decimal(str(value)), unit=unit,
        )
        return approve_assertion(assertion.pk, self.org, self.approver)

    def _approve_categorical(self, key, value):
        assertion = create_assertion(
            self.org, self.manager, self.material, key, self.Tipo.CATEGORICAL,
            self.Provenance.CERTIFICATE, date(2026, 1, 1), value_text=value,
        )
        return approve_assertion(assertion.pk, self.org, self.approver)

    def test_all_satisfied_is_suitable_candidate(self):
        self._approve_numeric("resistencia", 30)
        self._approve_categorical("clase", "estructural")
        outcome = evaluate_application(self.org, self.material, self.profile)
        self.assertEqual(outcome["resultado"], MaterialApplicationAssessment.Resultado.SUITABLE_CANDIDATE)
        self.assertEqual(outcome["failed_requirements"], [])
        self.assertEqual(outcome["missing_properties"], [])

    def test_one_failed_is_not_suitable(self):
        self._approve_numeric("resistencia", 10)  # below gte 25
        self._approve_categorical("clase", "estructural")
        outcome = evaluate_application(self.org, self.material, self.profile)
        self.assertEqual(outcome["resultado"], MaterialApplicationAssessment.Resultado.NOT_SUITABLE)
        self.assertIn("resistencia", outcome["failed_requirements"])

    def test_one_unknown_critical_is_requires_review(self):
        self._approve_categorical("clase", "estructural")
        # resistencia has no approved assertion at all
        outcome = evaluate_application(self.org, self.material, self.profile)
        self.assertEqual(outcome["resultado"], MaterialApplicationAssessment.Resultado.REQUIRES_REVIEW)
        self.assertIn("resistencia", outcome["missing_properties"])

    def test_draft_property_ignored(self):
        create_assertion(
            self.org, self.manager, self.material, "resistencia", self.Tipo.NUMERIC,
            self.Provenance.TECHNICAL_SPEC, date(2026, 1, 1), value_numeric=Decimal("40"), unit="kg",
        )  # never approved
        self._approve_categorical("clase", "estructural")
        outcome = evaluate_application(self.org, self.material, self.profile)
        self.assertIn("resistencia", outcome["missing_properties"])
        self.assertEqual(outcome["resultado"], MaterialApplicationAssessment.Resultado.REQUIRES_REVIEW)

    def test_approved_property_used(self):
        self._approve_numeric("resistencia", 30)
        self._approve_categorical("clase", "estructural")
        outcome = evaluate_application(self.org, self.material, self.profile)
        self.assertTrue(all(item["status"] == "satisfied" for item in outcome["requirement_results"]))

    def test_numeric_conversion_applied(self):
        self._approve_numeric("resistencia", 30000, unit="kg")
        self._approve_categorical("clase", "estructural")
        # Requirement declared in kg; assertion also in kg here — add a second
        # profile requirement in tonnes to force a real conversion path.
        profile = create_profile(
            self.org, self.manager, "MURO-CONV", "Muro conversion", Decimal("1"), "m2",
            requisitos=[{"key": "resistencia", "type": "numeric", "operator": "gte", "value": 20, "unit": "t"}],
        )
        approved = approve_profile(profile.pk, self.org, self.approver)
        outcome = evaluate_application(self.org, self.material, approved)
        self.assertEqual(outcome["resultado"], MaterialApplicationAssessment.Resultado.SUITABLE_CANDIDATE)

    def test_incompatible_unit_between_assertion_and_requirement_is_unknown(self):
        self._approve_numeric("resistencia", 30, unit="L")
        self._approve_categorical("clase", "estructural")
        outcome = evaluate_application(self.org, self.material, self.profile)
        self.assertIn("resistencia", outcome["missing_properties"])

    def test_categorical_exact_match_required(self):
        self._approve_numeric("resistencia", 30)
        self._approve_categorical("clase", "arquitectonico")
        outcome = evaluate_application(self.org, self.material, self.profile)
        self.assertEqual(outcome["resultado"], MaterialApplicationAssessment.Resultado.NOT_SUITABLE)

    def test_evaluate_requires_approved_profile(self):
        draft_profile = create_profile(
            self.org, self.manager, "MURO-DRAFT", "Muro draft", Decimal("1"), "m2",
        )
        with self.assertRaises(ValidationError):
            evaluate_application(self.org, self.material, draft_profile)

    def test_tenant_isolation_on_evaluation(self):
        other_material = MaterialOperacional.objects.create(
            organizacion=self.other_org, codigo="MAT-OTRO-S", nombre="Otro", categoria="otro", unidad_base="kg",
        )
        with self.assertRaises(ValidationError):
            evaluate_application(self.org, other_material, self.profile)

    def test_record_assessment_persists_immutable_snapshot(self):
        self._approve_numeric("resistencia", 30)
        self._approve_categorical("clase", "estructural")
        assessment = record_assessment(self.org, self.manager, self.material, self.profile)
        self.assertEqual(assessment.resultado, MaterialApplicationAssessment.Resultado.SUITABLE_CANDIDATE)
        self.assertEqual(assessment.profile_version, self.profile.version)

    def test_historical_assessment_not_rewritten_by_later_property_change(self):
        approved = self._approve_numeric("resistencia", 30)
        self._approve_categorical("clase", "estructural")
        first_assessment = record_assessment(self.org, self.manager, self.material, self.profile)
        self.assertEqual(first_assessment.resultado, MaterialApplicationAssessment.Resultado.SUITABLE_CANDIDATE)

        # A later property change (superseding the approved assertion) must
        # not alter the already-recorded historical assessment.
        self._approve_numeric("resistencia", 5)  # now fails gte 25
        first_assessment.refresh_from_db()
        self.assertEqual(first_assessment.resultado, MaterialApplicationAssessment.Resultado.SUITABLE_CANDIDATE)
        self.assertEqual(first_assessment.assertion_ids_used, sorted(first_assessment.assertion_ids_used))

    def test_human_decision_requires_suitable_candidate(self):
        self._approve_categorical("clase", "estructural")  # resistencia missing -> requires_review
        assessment = record_assessment(self.org, self.manager, self.material, self.profile)
        with self.assertRaises(ValidationError):
            decide_human_approval(assessment.pk, self.org, self.approver, approved=True)

    def test_human_decision_approve(self):
        self._approve_numeric("resistencia", 30)
        self._approve_categorical("clase", "estructural")
        assessment = record_assessment(self.org, self.manager, self.material, self.profile)
        decided = decide_human_approval(assessment.pk, self.org, self.approver, approved=True, note="ok")
        self.assertEqual(decided.decision_humana, MaterialApplicationAssessment.DecisionHumana.APROBADO)

    def test_human_decision_cannot_repeat(self):
        self._approve_numeric("resistencia", 30)
        self._approve_categorical("clase", "estructural")
        assessment = record_assessment(self.org, self.manager, self.material, self.profile)
        decide_human_approval(assessment.pk, self.org, self.approver, approved=True)
        with self.assertRaises(ValidationError):
            decide_human_approval(assessment.pk, self.org, self.approver, approved=True)


class FunctionalUseLifecycleTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Uso funcional org")
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-FU", nombre="Hormigón", categoria="hormigon", unidad_base="kg",
        )
        self.manager = User.objects.create_user("gestor-fu", "gestor-fu@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.manager, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ANALISTA,
        )
        self.approver = User.objects.create_user("aprobador-fu", "aprobador-fu@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.approver, organizacion=self.org, rol=UsuarioOrganizacion.Rol.REVISOR_AMBIENTAL,
        )
        profile = create_profile(self.org, self.manager, "MURO-FU", "Muro", Decimal("1"), "m2")
        self.profile = approve_profile(profile.pk, self.org, self.approver)

    def test_create_functional_use_requires_approved_profile(self):
        draft_profile = create_profile(self.org, self.manager, "MURO-FU2", "Muro 2", Decimal("1"), "m2")
        with self.assertRaises(ValidationError):
            create_functional_use(
                self.org, self.manager, self.material, draft_profile, Decimal("12.5"), "kg", "Ficha técnica",
            )

    def test_create_and_approve(self):
        functional_use = create_functional_use(
            self.org, self.manager, self.material, self.profile, Decimal("12.5"), "kg", "Ficha técnica",
        )
        approved = approve_functional_use(functional_use.pk, self.org, self.approver)
        self.assertEqual(approved.estado, MaterialFunctionalUse.Estado.APROBADO)

    def test_missing_rationale_rejected(self):
        with self.assertRaises(ValidationError):
            create_functional_use(
                self.org, self.manager, self.material, self.profile, Decimal("12.5"), "kg", "",
            )

    def test_new_approval_supersedes_previous(self):
        first = create_functional_use(
            self.org, self.manager, self.material, self.profile, Decimal("12.5"), "kg", "Ficha v1",
        )
        approve_functional_use(first.pk, self.org, self.approver)
        second = create_functional_use(
            self.org, self.manager, self.material, self.profile, Decimal("13.0"), "kg", "Ficha v2",
        )
        approve_functional_use(second.pk, self.org, self.approver)
        first.refresh_from_db()
        self.assertEqual(first.estado, MaterialFunctionalUse.Estado.REEMPLAZADO)

    def test_reject(self):
        functional_use = create_functional_use(
            self.org, self.manager, self.material, self.profile, Decimal("12.5"), "kg", "Ficha técnica",
        )
        rejected = reject_functional_use(functional_use.pk, self.org, self.approver)
        self.assertEqual(rejected.estado, MaterialFunctionalUse.Estado.RECHAZADO)


class FunctionalUseConcurrencyTests(TransactionTestCase):
    _fixture_teardown = detail_tests.DetailPostgresTests._fixture_teardown

    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Uso funcional concurrencia")
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-FU-CONC", nombre="Concreto", categoria="concreto", unidad_base="kg",
        )
        self.user = User.objects.create_superuser(
            "concurrencia-fu-admin", "concurrencia-fu-admin@example.com", "password"
        )
        profile = create_profile(self.org, self.user, "MURO-FU-CONC", "Muro", Decimal("1"), "m2")
        self.profile = approve_profile(profile.pk, self.org, self.user)

    def concurrent(self, actions):
        barrier = Barrier(len(actions))
        results, errors = [], []

        def worker(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                results.append(action())
            except Exception as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [Thread(target=worker, args=(action,)) for action in actions]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(20)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        return results, errors

    def test_concurrent_approval_leaves_one_approved(self):
        first = create_functional_use(self.org, self.user, self.material, self.profile, Decimal("10"), "kg", "A")
        second = create_functional_use(self.org, self.user, self.material, self.profile, Decimal("11"), "kg", "B")
        results, errors = self.concurrent(
            [
                lambda: approve_functional_use(first.pk, self.org, self.user).pk,
                lambda: approve_functional_use(second.pk, self.org, self.user).pk,
            ]
        )
        # Two outcomes are both correct depending on actual thread timing:
        # a genuine race is rejected by the DB (one result, one error), or a
        # non-overlapping run has the second gracefully supersede the first
        # (two results, no error). Either way exactly one row must end up
        # approved — that invariant, not the race outcome itself, is what
        # this test guards.
        self.assertEqual(len(results) + len(errors), 2, (results, errors))
        for error in errors:
            self.assertIsInstance(error, (ValidationError, IntegrityError))
        approved_count = MaterialFunctionalUse.objects.filter(
            organizacion=self.org, material=self.material, profile=self.profile,
            estado=MaterialFunctionalUse.Estado.APROBADO,
        ).count()
        self.assertEqual(approved_count, 1)
