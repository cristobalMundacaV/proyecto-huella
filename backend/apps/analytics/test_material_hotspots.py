"""MI-01F — Material Hotspot Intelligence tests. Builds real receptions
through the existing calculation engine (never a second ledger) using the
real "a2" (positive GWP) ÖKOBAUDAT fixture, plus a synthetic negative-factor
material for the negative/net-impact cases."""

from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import (
    ActividadOperacional, EventoMaterial, FactorAmbiental, FuenteDatos,
    MaterialOperacional, Obra, Observacion, Organizacion, VersionFactorAmbiental,
)
from .services.calculation_v2 import calculate_activity, recalculate
from .services.factor_governance import transition_factor_version
from .services.material_candidates import build_material_candidate, promote_material_candidate, review_material_candidate
from .services.material_factor_mapping import approve_material_mapping, propose_material_mapping
from .services.material_hotspots import material_hotspots
from .services.system_environmental_catalog import ensure_system_environmental_catalog
from .test_material_candidates import material_fixture

User = get_user_model()


class MaterialHotspotsTests(TestCase):
    def setUp(self):
        ensure_system_environmental_catalog()
        self.reviewer = User.objects.create_superuser(
            "mi01f-reviewer", "mi01f-reviewer@example.com", "password"
        )
        self.org = Organizacion.objects.create(nombre="MI-01F org")
        self.other_org = Organizacion.objects.create(nombre="MI-01F otro tenant")
        self.work = Obra.objects.create(organizacion=self.org, nombre="Obra 01F", fecha_inicio=date(2026, 1, 1))
        self.other_work = Obra.objects.create(organizacion=self.org, nombre="Obra 01F otra", fecha_inicio=date(2026, 1, 1))
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Guia 01F", tipo="manual")

    def _positive_factor(self):
        fixture_profile = material_fixture("a2")
        candidate, _created, evaluation = build_material_candidate(fixture_profile.pk)
        self.assertTrue(evaluation["compatible"])
        review_material_candidate(candidate.pk, self.reviewer, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.reviewer)
        transition_factor_version(version, "pruebas")
        transition_factor_version(version, "validado")
        transition_factor_version(version, "activo")
        return factor

    def _negative_factor(self):
        factor = FactorAmbiental.objects.create(
            organizacion=self.org, codigo="factor-negativo-01f", nombre="Factor negativo",
            categoria="materiales", unidad_entrada="kg", unidad_resultado="kgCO2e",
        )
        VersionFactorAmbiental.objects.create(
            factor=factor, version=1, valor=Decimal("-1.5"), fuente="test",
            estado=VersionFactorAmbiental.Estado.ACTIVO,
        )
        return factor

    def _material(self, codigo, unit="kg", org=None):
        return MaterialOperacional.objects.create(
            organizacion=org or self.org, codigo=codigo, nombre=f"Material {codigo}",
            categoria="materiales", unidad_base=unit,
        )

    def _receive(self, material, factor, amount, unit="kg", work=None, org=None, at=None):
        org = org or self.org
        work = work or self.work
        at = at or timezone.make_aware(datetime(2026, 2, 1, 10))
        source = self.source if org.pk == self.org.pk else FuenteDatos.objects.create(
            organizacion=org, nombre=f"Guia 01F {org.pk}", tipo="manual",
        )
        mapping = propose_material_mapping(org, material, factor, date(2026, 1, 1), None, self.reviewer)
        approve_material_mapping(mapping.pk, org, self.reviewer)
        activity = ActividadOperacional.objects.create(
            organizacion=org, obra=work, codigo=f"ACT-01F-{material.codigo}-{at.timestamp()}",
            nombre="recepcion", tipo="movimiento_material", timestamp_inicio=at,
        )
        observation = Observacion.objects.create(
            organizacion=org, actividad=activity, fuente=source, concepto="cantidad_material",
            valor_numerico=Decimal(str(amount)), unidad=unit, timestamp_observacion=at,
            estado=Observacion.Estado.VALIDADA,
        )
        EventoMaterial.objects.create(
            organizacion=org, material=material, actividad=activity, obra=work,
            tipo="recepcion", fecha_hora=at, observacion_cantidad=observation, fuente=source,
        )
        calculation, _ = calculate_activity(activity)
        return calculation

    def test_one_dominant_material(self):
        positive = self._positive_factor()
        dominant = self._material("MAT-DOMINANT")
        minor = self._material("MAT-MINOR")
        self._receive(dominant, positive, "1000", unit="kg")
        self._receive(minor, positive, "1", unit="kg")
        result = material_hotspots(self.org, work=self.work)
        rows = result["kgCO2e"]["materiales"]
        self.assertEqual(rows[0]["material_id"], dominant.pk)
        self.assertGreater(rows[0]["hotspot_share"], rows[1]["hotspot_share"])

    def test_several_materials_share_denominator(self):
        positive = self._positive_factor()
        a = self._material("MAT-SHARE-A")
        b = self._material("MAT-SHARE-B")
        self._receive(a, positive, "10", unit="kg")
        self._receive(b, positive, "10", unit="kg")
        result = material_hotspots(self.org, work=self.work)
        rows = result["kgCO2e"]["materiales"]
        self.assertAlmostEqual(float(rows[0]["hotspot_share"]), 0.5, places=6)
        self.assertAlmostEqual(float(rows[1]["hotspot_share"]), 0.5, places=6)

    def test_negative_material_reported_separately(self):
        negative = self._negative_factor()
        material = self._material("MAT-NEG")
        self._receive(material, negative, "10", unit="kg")
        result = material_hotspots(self.org, work=self.work)
        row = result["kgCO2e"]["materiales"][0]
        self.assertEqual(row["positive_gwp"], Decimal("0"))
        self.assertLess(row["negative_gwp"], 0)
        self.assertIsNone(row["hotspot_share"])

    def test_net_impact_combines_positive_and_negative_entries(self):
        positive = self._positive_factor()
        negative = self._negative_factor()
        material_pos = self._material("MAT-NET-POS")
        material_neg = self._material("MAT-NET-NEG")
        self._receive(material_pos, positive, "5", unit="kg")
        self._receive(material_neg, negative, "5", unit="kg")
        result = material_hotspots(self.org, work=self.work)
        rows = {row["material_id"]: row for row in result["kgCO2e"]["materiales"]}
        self.assertGreater(rows[material_pos.pk]["net_gwp"], 0)
        self.assertLess(rows[material_neg.pk]["net_gwp"], 0)

    def test_positive_hotspot_denominator_excludes_negative_contribution(self):
        positive = self._positive_factor()
        negative = self._negative_factor()
        material_pos = self._material("MAT-DENOM-POS")
        material_neg = self._material("MAT-DENOM-NEG")
        self._receive(material_pos, positive, "10", unit="kg")
        self._receive(material_neg, negative, "1000", unit="kg")
        result = material_hotspots(self.org, work=self.work)
        # total_positive must equal only the positive material's contribution,
        # never reduced by the (much larger in magnitude) negative one.
        rows = {row["material_id"]: row for row in result["kgCO2e"]["materiales"]}
        self.assertEqual(result["kgCO2e"]["total_positive"], rows[material_pos.pk]["positive_gwp"])
        self.assertEqual(rows[material_pos.pk]["hotspot_share"], Decimal("1"))

    def test_historical_recalculation_reflected_deterministically(self):
        positive = self._positive_factor()
        material = self._material("MAT-RECALC")
        calculation = self._receive(material, positive, "10", unit="kg")
        before = material_hotspots(self.org, work=self.work)["kgCO2e"]["materiales"][0]["net_gwp"]
        recalculated, _ = recalculate(calculation, "Verificación MI-01F")
        after_totals = material_hotspots(self.org, work=self.work)
        after = after_totals["kgCO2e"]["materiales"][0]["net_gwp"]
        # Recalculation with the same governed inputs is deterministic: the
        # ledger's current (non-superseded) view is unchanged.
        self.assertEqual(before, after)
        self.assertEqual(recalculated.resultado, calculation.resultado)

    def test_tenant_isolation(self):
        positive = self._positive_factor()
        own_material = self._material("MAT-TENANT-OWN")
        foreign_material = self._material("MAT-TENANT-FOREIGN", org=self.other_org)
        foreign_work = Obra.objects.create(organizacion=self.other_org, nombre="Obra ajena", fecha_inicio=date(2026, 1, 1))
        self._receive(own_material, positive, "10", unit="kg")
        self._receive(foreign_material, positive, "999", unit="kg", org=self.other_org, work=foreign_work)
        result = material_hotspots(self.org)
        material_ids = {row["material_id"] for row in result["kgCO2e"]["materiales"]}
        self.assertIn(own_material.pk, material_ids)
        self.assertNotIn(foreign_material.pk, material_ids)

    def test_work_isolation(self):
        positive = self._positive_factor()
        in_scope = self._material("MAT-WORK-IN")
        out_of_scope = self._material("MAT-WORK-OUT")
        self._receive(in_scope, positive, "10", unit="kg", work=self.work)
        self._receive(out_of_scope, positive, "10", unit="kg", work=self.other_work)
        result = material_hotspots(self.org, work=self.work)
        material_ids = {row["material_id"] for row in result["kgCO2e"]["materiales"]}
        self.assertIn(in_scope.pk, material_ids)
        self.assertNotIn(out_of_scope.pk, material_ids)
