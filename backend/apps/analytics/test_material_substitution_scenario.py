"""MI-01G — Substitution Scenario Engine tests. Strictly read-only/
hypothetical: evaluating a scenario must never mutate EventoMaterial, the
ledger, or a mapping, and must never approve anything."""

from datetime import date, datetime
from decimal import Decimal
from threading import Barrier, Thread

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.knowledge import test_okobaudat_detail as detail_tests

from .models import (
    ActividadOperacional, EventoMaterial, FuenteDatos, MaterialFactorMapping,
    MaterialOperacional, Observacion, Organizacion, UsuarioOrganizacion,
)
from .models.material_substitution_scenario import MaterialSubstitutionScenario
from .services.factor_governance import transition_factor_version
from .services.material_application_profile import approve_profile, create_profile
from .services.material_candidates import build_material_candidate, promote_material_candidate, review_material_candidate
from .services.material_factor_mapping import approve_material_mapping, propose_material_mapping
from .services.material_functional_use import approve_functional_use, create_functional_use
from .services.material_ledger import material_ledger_totals
from .services.material_substitution_scenario import evaluate_scenario
from .services.material_suitability import decide_human_approval, record_assessment
from .services.material_technical_property import approve_assertion, create_assertion
from .services.system_environmental_catalog import ensure_system_environmental_catalog
from .test_material_candidates import material_fixture

User = get_user_model()
Basis = MaterialSubstitutionScenario.Basis
Resultado = MaterialSubstitutionScenario.Resultado


class SubstitutionScenarioTests(TestCase):
    def setUp(self):
        ensure_system_environmental_catalog()
        self.reviewer = User.objects.create_superuser(
            "mi01g-reviewer", "mi01g-reviewer@example.com", "password"
        )
        self.org = Organizacion.objects.create(nombre="MI-01G org")
        UsuarioOrganizacion.objects.create(
            user=self.reviewer, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN,
        )
        profile = create_profile(
            self.org, self.reviewer, "PERFIL-01G", "Perfil escenario", Decimal("1"), "m2",
            requisitos=[{"key": "cumple_norma", "type": "boolean", "operator": "is_true"}],
        )
        self.profile = approve_profile(profile.pk, self.org, self.reviewer)
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Guia 01G", tipo="manual")
        self._factor_cache = {}

    def _activated_factor(self, label):
        if label in self._factor_cache:
            return self._factor_cache[label]
        fixture_profile = material_fixture(label)
        candidate, _created, evaluation = build_material_candidate(fixture_profile.pk)
        self.assertTrue(evaluation["compatible"])
        review_material_candidate(candidate.pk, self.reviewer, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.reviewer)
        transition_factor_version(version, "pruebas")
        transition_factor_version(version, "validado")
        transition_factor_version(version, "activo")
        self._factor_cache[label] = factor
        return factor

    def _eligible_material(self, label, codigo, quantity, unit=None):
        factor = self._activated_factor(label)
        unit = unit or ("kg" if label == "a2" else "m3")
        material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo=codigo, nombre=f"Material {codigo}",
            categoria="materiales", unidad_base=unit,
        )
        mapping = propose_material_mapping(self.org, material, factor, date(2026, 1, 1), None, self.reviewer)
        approve_material_mapping(mapping.pk, self.org, self.reviewer)
        assertion = create_assertion(
            self.org, self.reviewer, material, "cumple_norma", "boolean",
            "manual_professional_assertion", date(2026, 1, 1), value_boolean=True,
        )
        approve_assertion(assertion.pk, self.org, self.reviewer)
        assessment = record_assessment(self.org, self.reviewer, material, self.profile)
        decide_human_approval(assessment.pk, self.org, self.reviewer, approved=True)
        functional_use = create_functional_use(
            self.org, self.reviewer, material, self.profile, Decimal(str(quantity)), unit, "Justificación",
        )
        approve_functional_use(functional_use.pk, self.org, self.reviewer)
        return material

    def _real_reception(self, material, amount, unit):
        at = timezone.make_aware(datetime(2026, 3, 1, 10))
        activity = ActividadOperacional.objects.create(
            organizacion=self.org, codigo=f"ACT-01G-{material.codigo}", nombre="recepcion",
            tipo="movimiento_material", timestamp_inicio=at,
        )
        observation = Observacion.objects.create(
            organizacion=self.org, actividad=activity, fuente=self.source, concepto="cantidad_material",
            valor_numerico=Decimal(str(amount)), unidad=unit, timestamp_observacion=at,
            estado=Observacion.Estado.VALIDADA,
        )
        return EventoMaterial.objects.create(
            organizacion=self.org, material=material, actividad=activity,
            tipo="recepcion", fecha_hora=at, observacion_cantidad=observation, fuente=self.source,
        )

    def test_real_reception_baseline(self):
        baseline = self._eligible_material("a2", "MAT-01G-BASE", "10")
        alternative = self._eligible_material("a2", "MAT-01G-ALT", "8")
        reception = self._real_reception(baseline, "100", "kg")
        scenario = evaluate_scenario(
            self.org, self.reviewer, self.profile, baseline, alternative,
            basis=Basis.RECEPTION, reception=reception,
        )
        self.assertTrue(scenario.pk)
        self.assertEqual(scenario.functional_units, Decimal("10"))
        self.assertEqual(scenario.alternative_quantity_equivalent, Decimal("80"))

    def test_aggregate_quantity_baseline(self):
        baseline = self._eligible_material("a2", "MAT-01G-BASE2", "10")
        alternative = self._eligible_material("a2", "MAT-01G-ALT2", "8")
        scenario = evaluate_scenario(
            self.org, self.reviewer, self.profile, baseline, alternative,
            basis=Basis.AGGREGATE_QUANTITY, aggregate_quantity="100", aggregate_unit="kg",
        )
        self.assertEqual(scenario.functional_units, Decimal("10"))

    def test_different_quantities_produce_different_functional_units(self):
        baseline = self._eligible_material("a2", "MAT-01G-BASE3", "5")
        alternative = self._eligible_material("a2", "MAT-01G-ALT3", "5")
        scenario_small = evaluate_scenario(
            self.org, self.reviewer, self.profile, baseline, alternative,
            basis=Basis.AGGREGATE_QUANTITY, aggregate_quantity="5", aggregate_unit="kg",
        )
        scenario_large = evaluate_scenario(
            self.org, self.reviewer, self.profile, baseline, alternative,
            basis=Basis.AGGREGATE_QUANTITY, aggregate_quantity="50", aggregate_unit="kg",
        )
        self.assertLess(scenario_small.functional_units, scenario_large.functional_units)

    def test_lower_impact_alternative(self):
        baseline = self._eligible_material("a2", "MAT-01G-BASE4", "10")
        alternative = self._eligible_material("a2", "MAT-01G-ALT4", "6")
        scenario = evaluate_scenario(
            self.org, self.reviewer, self.profile, baseline, alternative,
            basis=Basis.AGGREGATE_QUANTITY, aggregate_quantity="10", aggregate_unit="kg",
        )
        self.assertEqual(scenario.resultado, Resultado.LOWER_IMPACT)
        self.assertLess(scenario.absolute_delta, 0)

    def test_higher_impact_alternative(self):
        baseline = self._eligible_material("a2", "MAT-01G-BASE5", "6")
        alternative = self._eligible_material("a2", "MAT-01G-ALT5", "10")
        scenario = evaluate_scenario(
            self.org, self.reviewer, self.profile, baseline, alternative,
            basis=Basis.AGGREGATE_QUANTITY, aggregate_quantity="6", aggregate_unit="kg",
        )
        self.assertEqual(scenario.resultado, Resultado.HIGHER_IMPACT)
        self.assertGreater(scenario.absolute_delta, 0)

    def test_negative_factor_scenario(self):
        baseline = self._eligible_material("a1", "MAT-01G-A1-BASE", "2")
        alternative = self._eligible_material("a1", "MAT-01G-A1-ALT", "3")
        scenario = evaluate_scenario(
            self.org, self.reviewer, self.profile, baseline, alternative,
            basis=Basis.AGGREGATE_QUANTITY, aggregate_quantity="2", aggregate_unit="m3",
        )
        self.assertLess(scenario.baseline_impact_per_functional_unit, 0)
        self.assertIn("negative_gwp_present_sign_preserved", scenario.warnings)

    def test_zero_source_quantity_yields_zero_functional_units(self):
        # A degenerate but valid input: zero material used means zero
        # functional units and zero equivalent alternative quantity — not a
        # crash, and the baseline/alternative per-FU impact (independent of
        # source quantity) is still reported.
        baseline = self._eligible_material("a2", "MAT-01G-ZERO", "10")
        alternative = self._eligible_material("a2", "MAT-01G-ZEROALT", "10")
        scenario = evaluate_scenario(
            self.org, self.reviewer, self.profile, baseline, alternative,
            basis=Basis.AGGREGATE_QUANTITY, aggregate_quantity="0", aggregate_unit="kg",
        )
        self.assertEqual(scenario.functional_units, Decimal("0"))
        self.assertEqual(scenario.alternative_quantity_equivalent, Decimal("0"))
        self.assertIsNotNone(scenario.baseline_impact_per_functional_unit)

    def test_invalid_comparability_recorded_as_not_comparable(self):
        baseline = self._eligible_material("a1", "MAT-01G-A1-NC", "2")
        alternative = self._eligible_material("a2", "MAT-01G-A2-NC", "10")
        scenario = evaluate_scenario(
            self.org, self.reviewer, self.profile, baseline, alternative,
            basis=Basis.AGGREGATE_QUANTITY, aggregate_quantity="2", aggregate_unit="m3",
        )
        self.assertEqual(scenario.resultado, Resultado.NOT_COMPARABLE)
        self.assertEqual(scenario.not_comparable_reason, "standard_mismatch")
        self.assertIsNone(scenario.functional_units)

    def test_scenario_never_mutates_ledger_or_mapping(self):
        baseline = self._eligible_material("a2", "MAT-01G-NOMUT", "10")
        alternative = self._eligible_material("a2", "MAT-01G-NOMUT-ALT", "8")
        mapping_count_before = MaterialFactorMapping.objects.filter(organizacion=self.org).count()
        totals_before = material_ledger_totals(self.org)
        evaluate_scenario(
            self.org, self.reviewer, self.profile, baseline, alternative,
            basis=Basis.AGGREGATE_QUANTITY, aggregate_quantity="10", aggregate_unit="kg",
        )
        mapping_count_after = MaterialFactorMapping.objects.filter(organizacion=self.org).count()
        totals_after = material_ledger_totals(self.org)
        self.assertEqual(mapping_count_before, mapping_count_after)
        self.assertEqual(totals_before, totals_after)

    def test_scenario_is_immutable(self):
        baseline = self._eligible_material("a2", "MAT-01G-IMMUT", "10")
        alternative = self._eligible_material("a2", "MAT-01G-IMMUT-ALT", "8")
        scenario = evaluate_scenario(
            self.org, self.reviewer, self.profile, baseline, alternative,
            basis=Basis.AGGREGATE_QUANTITY, aggregate_quantity="10", aggregate_unit="kg",
        )
        scenario.resultado = Resultado.HIGHER_IMPACT
        with self.assertRaises(Exception):
            scenario.save()
        with self.assertRaises(Exception):
            scenario.delete()

    def test_changed_future_factor_does_not_rewrite_scenario(self):
        baseline = self._eligible_material("a2", "MAT-01G-FROZEN", "10")
        alternative = self._eligible_material("a2", "MAT-01G-FROZEN-ALT", "8")
        scenario = evaluate_scenario(
            self.org, self.reviewer, self.profile, baseline, alternative,
            basis=Basis.AGGREGATE_QUANTITY, aggregate_quantity="10", aggregate_unit="kg",
        )
        frozen_impact = scenario.baseline_impact_per_functional_unit
        # A later revision to the functional use (a new approved value) must
        # never rewrite this already-evaluated scenario.
        new_use = create_functional_use(
            self.org, self.reviewer, baseline, self.profile, Decimal("999"), "kg", "Cambio posterior",
        )
        approve_functional_use(new_use.pk, self.org, self.reviewer)
        scenario.refresh_from_db()
        self.assertEqual(scenario.baseline_impact_per_functional_unit, frozen_impact)

    def test_tenant_isolation(self):
        other_org = Organizacion.objects.create(nombre="MI-01G otro tenant")
        baseline = self._eligible_material("a2", "MAT-01G-TEN-BASE", "10")
        alternative = self._eligible_material("a2", "MAT-01G-TEN-ALT", "8")
        scenario = evaluate_scenario(
            self.org, self.reviewer, self.profile, baseline, alternative,
            basis=Basis.AGGREGATE_QUANTITY, aggregate_quantity="10", aggregate_unit="kg",
        )
        self.assertEqual(
            MaterialSubstitutionScenario.objects.filter(organizacion=other_org, pk=scenario.pk).count(), 0,
        )


class SubstitutionScenarioConcurrencyTests(TransactionTestCase):
    _fixture_teardown = detail_tests.DetailPostgresTests._fixture_teardown

    def setUp(self):
        ensure_system_environmental_catalog()
        self.reviewer = User.objects.create_superuser(
            "mi01g-conc-reviewer", "mi01g-conc-reviewer@example.com", "password"
        )
        self.org = Organizacion.objects.create(nombre="MI-01G concurrencia")
        profile = create_profile(self.org, self.reviewer, "PERFIL-01G-CONC", "Perfil", Decimal("1"), "m2")
        self.profile = approve_profile(profile.pk, self.org, self.reviewer)

        fixture_profile = material_fixture("a2")
        candidate, _created, evaluation = build_material_candidate(fixture_profile.pk)
        review_material_candidate(candidate.pk, self.reviewer, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.reviewer)
        transition_factor_version(version, "pruebas")
        transition_factor_version(version, "validado")
        transition_factor_version(version, "activo")

        self.baseline = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-01G-CONC-BASE", nombre="Base",
            categoria="materiales", unidad_base="kg",
        )
        self.alternative = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-01G-CONC-ALT", nombre="Alt",
            categoria="materiales", unidad_base="kg",
        )
        for material, quantity in ((self.baseline, "10"), (self.alternative, "8")):
            mapping = propose_material_mapping(self.org, material, factor, date(2026, 1, 1), None, self.reviewer)
            approve_material_mapping(mapping.pk, self.org, self.reviewer)
            functional_use = create_functional_use(
                self.org, self.reviewer, material, self.profile, Decimal(quantity), "kg", "Justificación",
            )
            approve_functional_use(functional_use.pk, self.org, self.reviewer)

    def test_concurrent_evaluation_produces_two_independent_immutable_scenarios(self):
        barrier = Barrier(2)
        results, errors = [], []

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                results.append(
                    evaluate_scenario(
                        self.org, self.reviewer, self.profile, self.baseline, self.alternative,
                        basis=Basis.AGGREGATE_QUANTITY, aggregate_quantity="10", aggregate_unit="kg",
                    ).pk
                )
            except Exception as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(20)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(len(results), 2)
        self.assertNotEqual(results[0], results[1])
