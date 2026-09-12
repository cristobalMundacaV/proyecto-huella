"""MI-01J — MATERIAL-INTELLIGENCE closure E2E.

Walks the complete chain end to end using real ÖKOBAUDAT fixtures already
captured by MATERIAL-DATA (never inventing new upstream facts): ÖKOBAUDAT
profile -> governed factor -> MaterialOperacional -> explicit factor mapping
-> application profile -> requirements -> technical evidence -> suitability
-> functional quantity -> comparable alternative -> environmental comparison
-> actual reception/ledger -> hotspot -> substitution scenario -> opportunity
detection -> Copilot explanation, with at least two comparable materials.

Also demonstrates, explicitly and with automated assertions, the two
"never" invariants: a same-looking material without approved suitability is
NOT comparable, and A1 vs A2 is NOT directly comparable in V1 — and that a
historical result is not rewritten by later changes.
"""

from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import (
    ActividadOperacional, EventoMaterial, FuenteDatos, MaterialOperacional,
    Obra, Observacion, Organizacion, UsuarioOrganizacion,
)
from .models.material_functional_use import MaterialApplicationAssessment
from .models.material_substitution_scenario import MaterialSubstitutionScenario
from .services.calculation_v2 import calculate_activity
from .services.factor_governance import transition_factor_version
from .services.material_application_profile import approve_profile, create_profile
from .services.material_candidates import build_material_candidate, promote_material_candidate, review_material_candidate
from .services.material_comparable_sets import comparable_alternatives
from .services.material_environmental_comparison import compare_materials
from .services.material_factor_mapping import approve_material_mapping, propose_material_mapping
from .services.material_functional_use import approve_functional_use, create_functional_use
from .services.material_hotspots import material_hotspots
from .services.material_intelligence_copilot import MaterialIntelligenceCopilotService
from .services.material_opportunities import detect_opportunities
from .services.material_substitution_scenario import evaluate_scenario
from .services.material_suitability import decide_human_approval, record_assessment
from .services.material_technical_property import approve_assertion, create_assertion
from .services.environmental_agent import EnvironmentalAgentProvider
from .services.system_environmental_catalog import ensure_system_environmental_catalog
from .test_material_candidates import material_fixture

User = get_user_model()


class StubProvider(EnvironmentalAgentProvider):
    name = "stub-e2e"
    model = "test"

    def generate(self, *, system_rules, context):
        return {
            "hechos": ["Hallazgo determinista disponible."],
            "hallazgos_deterministas": ["El material tiene un perfil aprobado."],
            "advertencias": [],
            "explicacion_asistiva": "Resumen basado únicamente en el contexto entregado.",
        }


class MaterialIntelligenceEndToEndTests(TestCase):
    def setUp(self):
        ensure_system_environmental_catalog()
        self.admin = User.objects.create_superuser(
            "mi01j-e2e-admin", "mi01j-e2e-admin@example.com", "password"
        )
        self.org = Organizacion.objects.create(nombre="MI-01J E2E org")
        self.work = Obra.objects.create(organizacion=self.org, nombre="Obra 01J", fecha_inicio=date(2026, 1, 1))
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Guia 01J", tipo="manual")

    def _activated_factor(self, label):
        fixture_profile = material_fixture(label)
        candidate, created, evaluation = build_material_candidate(fixture_profile.pk)
        self.assertTrue(evaluation["compatible"])
        review_material_candidate(candidate.pk, self.admin, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.admin)
        transition_factor_version(version, "pruebas")
        transition_factor_version(version, "validado")
        version = transition_factor_version(version, "activo")
        return factor, version, fixture_profile

    def _material_with_full_chain(self, factor, codigo, resistencia_value, functional_quantity, profile, unit="kg"):
        material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo=codigo, nombre=f"Material {codigo}",
            categoria="materiales", unidad_base=unit,
        )
        mapping = propose_material_mapping(self.org, material, factor, date(2026, 1, 1), None, self.admin)
        mapping = approve_material_mapping(mapping.pk, self.org, self.admin)

        assertion = create_assertion(
            self.org, self.admin, material, "resistencia", "numeric",
            "technical_spec", date(2026, 1, 1), value_numeric=Decimal(str(resistencia_value)), unit="kg",
        )
        approve_assertion(assertion.pk, self.org, self.admin)
        assertion2 = create_assertion(
            self.org, self.admin, material, "clase", "categorical",
            "manual_professional_assertion", date(2026, 1, 1), value_text="estructural",
        )
        approve_assertion(assertion2.pk, self.org, self.admin)

        assessment = record_assessment(self.org, self.admin, material, profile)
        decided = decide_human_approval(assessment.pk, self.org, self.admin, approved=True)

        functional_use = create_functional_use(
            self.org, self.admin, material, profile, Decimal(str(functional_quantity)), unit, "Ficha técnica del fabricante",
        )
        functional_use = approve_functional_use(functional_use.pk, self.org, self.admin)

        return {
            "material": material, "mapping": mapping, "assessment": decided,
            "functional_use": functional_use,
        }

    def test_comparable_end_to_end_with_two_materials(self):
        factor, factor_version, fixture_profile = self._activated_factor("a2")

        profile = create_profile(
            self.org, self.admin, "PERFIL-01J-MURO", "Muro estructural", Decimal("1"), "m2",
            requisitos=[
                {"key": "resistencia", "type": "numeric", "operator": "gte", "value": 20, "unit": "kg"},
                {"key": "clase", "type": "categorical", "operator": "equals", "value": "estructural"},
            ],
        )
        profile = approve_profile(profile.pk, self.org, self.admin)

        chain_a = self._material_with_full_chain(factor, "MAT-01J-A", 30, 10, profile)
        chain_b = self._material_with_full_chain(factor, "MAT-01J-B", 35, 6, profile)

        # Comparable set (MI-01D): B is a directly comparable alternative to A.
        comparable = comparable_alternatives(self.org, chain_a["material"], profile, [chain_b["material"]])
        self.assertTrue(comparable["source_eligible"])
        self.assertEqual([c["material_id"] for c in comparable["comparable_candidates"]], [chain_b["material"].pk])

        # Deterministic comparison (MI-01E): A(10kg/FU) vs B(6kg/FU), same
        # per-kg factor — B must show the lower per-functional-unit impact.
        comparison = compare_materials(self.org, chain_a["material"], chain_b["material"], profile)
        self.assertTrue(comparison["comparable"])
        self.assertLess(
            comparison["alternative"]["impact_a1a3_per_functional_unit"],
            comparison["baseline"]["impact_a1a3_per_functional_unit"],
        )

        # Actual reception + ledger (existing MATERIAL-DATA authority, reused).
        at = timezone.make_aware(datetime(2026, 5, 1, 10))
        activity = ActividadOperacional.objects.create(
            organizacion=self.org, obra=self.work, codigo="ACT-01J-A", nombre="recepcion",
            tipo="movimiento_material", timestamp_inicio=at,
        )
        observation = Observacion.objects.create(
            organizacion=self.org, actividad=activity, fuente=self.source, concepto="cantidad_material",
            valor_numerico=Decimal("1000"), unidad="kg", timestamp_observacion=at,
            estado=Observacion.Estado.VALIDADA,
        )
        reception = EventoMaterial.objects.create(
            organizacion=self.org, material=chain_a["material"], actividad=activity, obra=self.work,
            tipo="recepcion", fecha_hora=at, observacion_cantidad=observation, fuente=self.source,
        )
        calculation, _ = calculate_activity(activity)
        self.assertGreater(calculation.resultado, 0)

        # Hotspot (MI-01F): material A dominates (only receiver in this work).
        hotspots = material_hotspots(self.org, work=self.work)
        top_row = hotspots["kgCO2e"]["materiales"][0]
        self.assertEqual(top_row["material_id"], chain_a["material"].pk)

        # Substitution scenario (MI-01G): hypothetical, immutable, read-only.
        scenario = evaluate_scenario(
            self.org, self.admin, profile, chain_a["material"], chain_b["material"],
            basis=MaterialSubstitutionScenario.Basis.RECEPTION, reception=reception,
        )
        self.assertEqual(scenario.resultado, MaterialSubstitutionScenario.Resultado.LOWER_IMPACT)

        # Opportunity detection (MI-01H): the hotspot lists B as an alternative.
        opportunities = detect_opportunities(self.org, work=self.work)
        matching = [o for o in opportunities if o["hotspot_material_id"] == chain_a["material"].pk]
        self.assertEqual(len(matching), 1)
        self.assertEqual(
            [a["alternative_material_id"] for a in matching[0]["alternatives"]], [chain_b["material"].pk],
        )

        # Copilot explanation (MI-01I): bounded, deterministic, stub provider only.
        copilot = MaterialIntelligenceCopilotService(StubProvider())
        explanation = copilot.explain_material(chain_a["material"], self.org, work=self.work)
        self.assertEqual(explanation["provenance"]["material"], chain_a["material"].pk)
        self.assertIn("explicacion_asistiva", explanation)

    def test_non_comparable_lookalike_material_without_suitability(self):
        factor, _, _ = self._activated_factor("a2")
        profile = create_profile(
            self.org, self.admin, "PERFIL-01J-LOOKALIKE", "Muro", Decimal("1"), "m2",
            requisitos=[
                {"key": "resistencia", "type": "numeric", "operator": "gte", "value": 20, "unit": "kg"},
                {"key": "clase", "type": "categorical", "operator": "equals", "value": "estructural"},
            ],
        )
        profile = approve_profile(profile.pk, self.org, self.admin)
        source = self._material_with_full_chain(factor, "HORMIGON-G30-ORIG", 30, 10, profile)

        # A same-looking material (near-identical name/code) with NO governed
        # suitability chain at all — comparability must never be inferred
        # from the resemblance.
        lookalike = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="HORMIGON-G30-COPIA", nombre="Hormigón G30",
            categoria="materiales", unidad_base="kg",
        )
        mapping = propose_material_mapping(self.org, lookalike, factor, date(2026, 1, 1), None, self.admin)
        approve_material_mapping(mapping.pk, self.org, self.admin)
        # Deliberately no property assertion, no assessment, no functional use.

        comparable = comparable_alternatives(self.org, source["material"], profile, [lookalike])
        self.assertEqual(comparable["comparable_candidates"], [])
        reasons = comparable["excluded_candidates"][0]["reasons"]
        self.assertIn("suitability_not_approved", reasons)
        self.assertIn("functional_use_not_approved", reasons)

        comparison = compare_materials(self.org, source["material"], lookalike, profile)
        self.assertFalse(comparison["comparable"])

    def test_a1_vs_a2_not_directly_comparable_v1(self):
        factor_a1, _, _ = self._activated_factor("a1")
        factor_a2, _, _ = self._activated_factor("a2")
        profile = create_profile(
            self.org, self.admin, "PERFIL-01J-STD", "Muro estandar", Decimal("1"), "m2",
            requisitos=[{"key": "cumple_norma", "type": "boolean", "operator": "is_true"}],
        )
        profile = approve_profile(profile.pk, self.org, self.admin)

        def _simple_chain(factor, codigo, unit):
            material = MaterialOperacional.objects.create(
                organizacion=self.org, codigo=codigo, nombre=f"Material {codigo}",
                categoria="materiales", unidad_base=unit,
            )
            mapping = propose_material_mapping(self.org, material, factor, date(2026, 1, 1), None, self.admin)
            approve_material_mapping(mapping.pk, self.org, self.admin)
            assertion = create_assertion(
                self.org, self.admin, material, "cumple_norma", "boolean",
                "manual_professional_assertion", date(2026, 1, 1), value_boolean=True,
            )
            approve_assertion(assertion.pk, self.org, self.admin)
            assessment = record_assessment(self.org, self.admin, material, profile)
            decide_human_approval(assessment.pk, self.org, self.admin, approved=True)
            functional_use = create_functional_use(
                self.org, self.admin, material, profile, Decimal("1"), unit, "Justificación",
            )
            approve_functional_use(functional_use.pk, self.org, self.admin)
            return material

        material_a1 = _simple_chain(factor_a1, "MAT-01J-STD-A1", "m3")
        material_a2 = _simple_chain(factor_a2, "MAT-01J-STD-A2", "kg")

        comparable = comparable_alternatives(self.org, material_a1, profile, [material_a2])
        self.assertEqual(comparable["comparable_candidates"], [])
        self.assertIn("standard_mismatch", comparable["excluded_candidates"][0]["reasons"])

        comparison = compare_materials(self.org, material_a1, material_a2, profile)
        self.assertFalse(comparison["comparable"])
        self.assertEqual(comparison["reason"], "standard_mismatch")

    def test_historical_reconstruction_survives_later_changes(self):
        factor, _, _ = self._activated_factor("a2")
        profile = create_profile(
            self.org, self.admin, "PERFIL-01J-HIST", "Muro histórico", Decimal("1"), "m2",
            requisitos=[{"key": "cumple_norma", "type": "boolean", "operator": "is_true"}],
        )
        profile = approve_profile(profile.pk, self.org, self.admin)
        chain_a = self._material_chain_boolean(factor, "MAT-01J-HIST-A", 10, profile_override=profile)
        chain_b = self._material_chain_boolean(factor, "MAT-01J-HIST-B", 6, profile_override=profile)

        scenario = evaluate_scenario(
            self.org, self.admin, profile, chain_a, chain_b,
            basis=MaterialSubstitutionScenario.Basis.AGGREGATE_QUANTITY,
            aggregate_quantity="10", aggregate_unit="kg",
        )
        frozen_impact = scenario.baseline_impact_per_functional_unit
        frozen_delta = scenario.absolute_delta
        scenario_id = scenario.pk

        # Later changes: a new (superseding) property assertion and a new
        # (superseding) functional use for the baseline material.
        new_assertion = create_assertion(
            self.org, self.admin, chain_a, "cumple_norma", "boolean",
            "manual_professional_assertion", date(2026, 6, 1), value_boolean=True,
        )
        approve_assertion(new_assertion.pk, self.org, self.admin)
        new_use = create_functional_use(
            self.org, self.admin, chain_a, profile, Decimal("999"), "kg", "Cambio posterior",
        )
        approve_functional_use(new_use.pk, self.org, self.admin)

        # Reconstruct strictly by ID — the historical scenario is unchanged.
        from .models.material_substitution_scenario import MaterialSubstitutionScenario as Model

        reconstructed = Model.objects.get(pk=scenario_id)
        self.assertEqual(reconstructed.baseline_impact_per_functional_unit, frozen_impact)
        self.assertEqual(reconstructed.absolute_delta, frozen_delta)

    def _material_chain_boolean(self, factor, codigo, quantity, profile_override=None):
        material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo=codigo, nombre=f"Material {codigo}",
            categoria="materiales", unidad_base="kg",
        )
        mapping = propose_material_mapping(self.org, material, factor, date(2026, 1, 1), None, self.admin)
        approve_material_mapping(mapping.pk, self.org, self.admin)
        profile = profile_override or create_profile(
            self.org, self.admin, f"PERFIL-{codigo}", "Perfil", Decimal("1"), "m2",
            requisitos=[{"key": "cumple_norma", "type": "boolean", "operator": "is_true"}],
        )
        if profile_override is None:
            profile = approve_profile(profile.pk, self.org, self.admin)
        assertion = create_assertion(
            self.org, self.admin, material, "cumple_norma", "boolean",
            "manual_professional_assertion", date(2026, 1, 1), value_boolean=True,
        )
        approve_assertion(assertion.pk, self.org, self.admin)
        assessment = record_assessment(self.org, self.admin, material, profile)
        decide_human_approval(assessment.pk, self.org, self.admin, approved=True)
        functional_use = create_functional_use(
            self.org, self.admin, material, profile, Decimal(str(quantity)), "kg", "Justificación",
        )
        approve_functional_use(functional_use.pk, self.org, self.admin)
        return material
