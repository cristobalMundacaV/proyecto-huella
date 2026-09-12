"""MI-01H — Environmental Opportunity Detection tests. Combines a real
reception (so the material is a positive-GWP hotspot, MI-01F) with an
approved application profile/suitability/functional-use chain (so it is
comparability-eligible, MI-01D/E) using the real "a2" ÖKOBAUDAT fixture."""

from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import (
    ActividadOperacional, EventoMaterial, FuenteDatos, MaterialOperacional,
    Obra, Observacion, Organizacion, UsuarioOrganizacion,
)
from .services.calculation_v2 import calculate_activity
from .services.factor_governance import transition_factor_version
from .services.material_application_profile import approve_profile, create_profile
from .services.material_candidates import build_material_candidate, promote_material_candidate, review_material_candidate
from .services.material_factor_mapping import approve_material_mapping, propose_material_mapping
from .services.material_functional_use import approve_functional_use, create_functional_use
from .services.material_opportunities import detect_opportunities
from .services.material_suitability import decide_human_approval, record_assessment
from .services.material_technical_property import approve_assertion, create_assertion
from .services.system_environmental_catalog import ensure_system_environmental_catalog
from .test_material_candidates import material_fixture

User = get_user_model()


class MaterialOpportunitiesTests(TestCase):
    def setUp(self):
        ensure_system_environmental_catalog()
        self.reviewer = User.objects.create_superuser(
            "mi01h-reviewer", "mi01h-reviewer@example.com", "password"
        )
        self.org = Organizacion.objects.create(nombre="MI-01H org")
        self.work = Obra.objects.create(organizacion=self.org, nombre="Obra 01H", fecha_inicio=date(2026, 1, 1))
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Guia 01H", tipo="manual")
        UsuarioOrganizacion.objects.create(
            user=self.reviewer, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN,
        )
        profile = create_profile(
            self.org, self.reviewer, "PERFIL-01H", "Perfil oportunidad", Decimal("1"), "m2",
            requisitos=[{"key": "cumple_norma", "type": "boolean", "operator": "is_true"}],
        )
        self.profile = approve_profile(profile.pk, self.org, self.reviewer)
        self._factor = None

    def _activated_factor(self):
        if self._factor is not None:
            return self._factor
        fixture_profile = material_fixture("a2")
        candidate, _created, evaluation = build_material_candidate(fixture_profile.pk)
        review_material_candidate(candidate.pk, self.reviewer, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.reviewer)
        transition_factor_version(version, "pruebas")
        transition_factor_version(version, "validado")
        transition_factor_version(version, "activo")
        self._factor = factor
        return factor

    def _comparable_material(self, codigo, quantity):
        factor = self._activated_factor()
        material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo=codigo, nombre=f"Material {codigo}",
            categoria="materiales", unidad_base="kg",
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
            self.org, self.reviewer, material, self.profile, Decimal(str(quantity)), "kg", "Justificación",
        )
        approve_functional_use(functional_use.pk, self.org, self.reviewer)
        return material, factor

    def _receive(self, material, factor, amount):
        at = timezone.make_aware(datetime(2026, 4, 1, 10))
        activity = ActividadOperacional.objects.create(
            organizacion=self.org, obra=self.work, codigo=f"ACT-01H-{material.codigo}",
            nombre="recepcion", tipo="movimiento_material", timestamp_inicio=at,
        )
        observation = Observacion.objects.create(
            organizacion=self.org, actividad=activity, fuente=self.source, concepto="cantidad_material",
            valor_numerico=Decimal(str(amount)), unidad="kg", timestamp_observacion=at,
            estado=Observacion.Estado.VALIDADA,
        )
        EventoMaterial.objects.create(
            organizacion=self.org, material=material, actividad=activity, obra=self.work,
            tipo="recepcion", fecha_hora=at, observacion_cantidad=observation, fuente=self.source,
        )
        calculate_activity(activity)

    def test_hotspot_with_lower_impact_comparable_alternative(self):
        hotspot, factor = self._comparable_material("MAT-01H-HOTSPOT", "10")
        alt, _ = self._comparable_material("MAT-01H-ALT", "6")
        self._receive(hotspot, factor, "1000")
        opportunities = detect_opportunities(self.org, work=self.work)
        self.assertEqual(len(opportunities), 1)
        opportunity = opportunities[0]
        self.assertEqual(opportunity["hotspot_material_id"], hotspot.pk)
        self.assertEqual(len(opportunity["alternatives"]), 1)
        self.assertEqual(opportunity["alternatives"][0]["alternative_material_id"], alt.pk)
        self.assertLess(opportunity["alternatives"][0]["absolute_delta"], 0)

    def test_no_comparable_alternatives_still_reports_hotspot(self):
        hotspot, factor = self._comparable_material("MAT-01H-ALONE", "10")
        self._receive(hotspot, factor, "1000")
        opportunities = detect_opportunities(self.org, work=self.work)
        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0]["alternatives"], [])

    def test_alternative_with_higher_impact_still_listed_not_hidden(self):
        hotspot, factor = self._comparable_material("MAT-01H-HISRC", "6")
        worse_alt, _ = self._comparable_material("MAT-01H-WORSE", "10")
        self._receive(hotspot, factor, "1000")
        opportunities = detect_opportunities(self.org, work=self.work)
        alternatives = opportunities[0]["alternatives"]
        self.assertEqual(len(alternatives), 1)
        self.assertGreater(alternatives[0]["absolute_delta"], 0)

    def test_deterministic_ordering_by_impact_only(self):
        hotspot, factor = self._comparable_material("MAT-01H-ORDER-SRC", "10")
        low, _ = self._comparable_material("MAT-01H-ORDER-LOW", "2")
        high, _ = self._comparable_material("MAT-01H-ORDER-HIGH", "20")
        self._receive(hotspot, factor, "1000")
        opportunities = detect_opportunities(self.org, work=self.work)
        alternatives = opportunities[0]["alternatives"]
        self.assertEqual(alternatives[0]["alternative_material_id"], low.pk)
        self.assertEqual(alternatives[-1]["alternative_material_id"], high.pk)

    def test_negative_gwp_material_is_not_a_hotspot(self):
        # A material with net-negative contribution never appears as a
        # hotspot candidate (V1 denominator is positive contribution only).
        hotspot, factor = self._comparable_material("MAT-01H-ONLYNEG", "10")
        from .models import FactorAmbiental, VersionFactorAmbiental

        negative_factor = FactorAmbiental.objects.create(
            organizacion=self.org, codigo="factor-neg-01h", nombre="Factor negativo",
            categoria="materiales", unidad_entrada="kg", unidad_resultado="kgCO2e",
        )
        VersionFactorAmbiental.objects.create(
            factor=negative_factor, version=1, valor=Decimal("-1"), fuente="test",
            estado=VersionFactorAmbiental.Estado.ACTIVO,
        )
        neg_material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-01H-NEGONLY", nombre="Solo negativo",
            categoria="materiales", unidad_base="kg",
        )
        neg_mapping = propose_material_mapping(
            self.org, neg_material, negative_factor, date(2026, 1, 1), None, self.reviewer,
        )
        approve_material_mapping(neg_mapping.pk, self.org, self.reviewer)
        self._receive(neg_material, negative_factor, "10")
        opportunities = detect_opportunities(self.org, work=self.work)
        hotspot_ids = {op["hotspot_material_id"] for op in opportunities}
        self.assertNotIn(neg_material.pk, hotspot_ids)

    def test_tenant_isolation(self):
        other_org = Organizacion.objects.create(nombre="MI-01H otro tenant")
        hotspot, factor = self._comparable_material("MAT-01H-TENANT", "10")
        self._receive(hotspot, factor, "1000")
        opportunities = detect_opportunities(other_org)
        self.assertEqual(opportunities, [])
