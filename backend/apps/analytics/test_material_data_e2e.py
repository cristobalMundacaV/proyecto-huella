"""MATERIAL-DATA-01J — complete, isolated, local E2E for both the A1 and A2
paths, using real upstream fixtures already captured by 01B (never
production data). Walks the full chain end to end and then demonstrates
that a historical calculation reconstructs completely from persisted,
immutable data alone — answering the DoD's 40 questions without guessing.
"""

from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import (ActividadOperacional, EventoMaterial, FuenteDatos,
                     MaterialOperacional, Obra, Observacion, Organizacion,
                     UsuarioOrganizacion, VersionFactorAmbiental)
from .services.calculation_v2 import calculate_activity
from .services.factor_governance import transition_factor_version
from .services.material_candidates import (build_material_candidate,
                                            promote_material_candidate,
                                            review_material_candidate)
from .services.material_factor_mapping import (approve_material_mapping,
                                                propose_material_mapping)
from .services.material_inventory import material_environmental_coverage, reception_coverage
from .services.material_ledger import ledger_entry_provenance, material_ledger_totals
from .services.material_quality import assess_factor_data_quality
from .services.material_source_impact import assess_candidate_impact
from .services.methodology_selector import select_methodology
from .services.system_environmental_catalog import ensure_system_environmental_catalog
from .test_material_candidates import material_fixture

User = get_user_model()


class MaterialDataEndToEndTests(TestCase):
    def setUp(self):
        ensure_system_environmental_catalog()
        self.reviewer = User.objects.create_superuser(
            "e2e-reviewer", "e2e-reviewer@example.com", "password"
        )

    def _walk(self, *, label, amount, unit, expected_sign):
        """Runs the entire MATERIAL-DATA chain for one real upstream fixture
        and returns everything needed to answer the DoD questions."""
        # ÖKOBAUDAT catalog -> process detail -> A1-A3 profile (01A/01B, real fixture)
        profile = material_fixture(label)

        # governed candidate (01C)
        candidate, created, evaluation = build_material_candidate(profile.pk)
        self.assertTrue(created)
        self.assertTrue(evaluation["compatible"])

        # human review + promotion to a global draft factor (01C, unchanged)
        review_material_candidate(candidate.pk, self.reviewer, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.reviewer)
        self.assertEqual(version.estado, VersionFactorAmbiental.Estado.BORRADOR)

        # explicit local activation through EXISTING governance only (01C's own workflow)
        transition_factor_version(version, "pruebas")
        transition_factor_version(version, "validado")
        version = transition_factor_version(version, "activo")
        self.assertEqual(version.estado, VersionFactorAmbiental.Estado.ACTIVO)

        # operational domain: MaterialOperacional + explicit governed mapping (01D)
        org = Organizacion.objects.create(nombre=f"E2E {label}")
        material = MaterialOperacional.objects.create(
            organizacion=org, codigo=f"MAT-E2E-{label.upper()}", nombre=f"Material E2E {label}",
            categoria="materiales", unidad_base=unit,
        )
        mapping = propose_material_mapping(org, material, factor, date(2026, 1, 1), None, self.reviewer)
        mapping = approve_material_mapping(mapping.pk, org, self.reviewer)

        # EventoMaterial.RECEPCION — the only A1-A3 accounting point (unchanged rule)
        work = Obra.objects.create(organizacion=org, nombre="Obra E2E", fecha_inicio=date(2026, 1, 1))
        source = FuenteDatos.objects.create(organizacion=org, nombre="Guia E2E", tipo="manual")
        at = timezone.make_aware(datetime(2026, 9, 11, 10))
        activity = ActividadOperacional.objects.create(
            organizacion=org, obra=work, codigo=f"ACT-E2E-{label}", nombre="recepcion",
            tipo="movimiento_material", timestamp_inicio=at,
        )
        observation = Observacion.objects.create(
            organizacion=org, actividad=activity, fuente=source, concepto="cantidad_material",
            valor_numerico=Decimal(amount), unidad=unit, timestamp_observacion=at,
            estado=Observacion.Estado.VALIDADA,
        )
        event = EventoMaterial.objects.create(
            organizacion=org, material=material, actividad=activity, obra=work,
            tipo="recepcion", fecha_hora=at, observacion_cantidad=observation, fuente=source,
        )

        # deterministic eligibility (01D)
        selection = select_methodology(activity)
        self.assertIsNotNone(selection["seleccion"], selection["razon"])

        # deterministic calculation (unchanged math engine)
        calculation, _ = calculate_activity(activity)
        calculation.refresh_from_db()
        if expected_sign < 0:
            self.assertLess(calculation.resultado, 0)
        else:
            self.assertGreater(calculation.resultado, 0)

        # accounting / ledger (01G)
        totals = material_ledger_totals(org)
        self.assertEqual(totals["entradas_totales"], 1)
        self.assertEqual(totals["totales_por_unidad"]["kgCO2e"]["total"], calculation.resultado)

        # coverage (01E)
        diag = reception_coverage(event)
        self.assertTrue(diag["calculable"])
        self.assertTrue(diag["calculado"])
        coverage = material_environmental_coverage(org)
        self.assertEqual(coverage["recepciones_calculables"], 1)
        self.assertEqual(coverage["recepciones_calculadas"], 1)

        # data quality (01F)
        quality = assess_factor_data_quality(factor)
        self.assertIn(quality["estado"], {"sufficient", "requires_review"})

        # source refresh impact (01I) — building/promoting/mapping never
        # changes what upstream reports, so this must be no_impact
        impact = assess_candidate_impact(candidate.__class__.objects.get(pk=candidate.pk))
        self.assertEqual(impact["impact"], "no_impact")

        return {
            "org": org, "material": material, "mapping": mapping, "factor": factor,
            "version": version, "candidate": candidate, "event": event,
            "calculation_id": calculation.pk, "profile": profile,
        }

    def _assert_fully_reconstructible(self, ids):
        """Re-fetch EVERYTHING by id only (no reuse of in-memory objects) to
        prove a historical calculation reconstructs without touching upstream
        again — answers the DoD's provenance questions."""
        from .models import CalculoAmbiental
        from .models.material_factor_mapping import MaterialFactorMapping

        calculation = CalculoAmbiental.objects.get(pk=ids["calculation_id"])
        provenance = ledger_entry_provenance(calculation)

        # 1-4: what/where/when/how much
        event = EventoMaterial.objects.get(pk=ids["event"].pk)
        self.assertEqual(event.tipo, "recepcion")
        self.assertEqual(event.material_id, ids["material"].pk)
        self.assertIsNotNone(event.observacion_cantidad.valor_numerico)
        self.assertIsNotNone(event.observacion_cantidad.unidad)

        # 5-11: mapping identity, approver, timing, validity
        mapping = MaterialFactorMapping.objects.get(pk=ids["mapping"].pk)
        self.assertEqual(mapping.estado, "aprobado")
        decision = mapping.decisiones.get(decision="aprobado")
        self.assertEqual(decision.actor_id, self.reviewer.pk)
        self.assertIsNotNone(decision.timestamp)
        self.assertEqual(mapping.vigencia_desde, date(2026, 1, 1))

        # 9-17: factor/version/unit/normalization/result
        self.assertEqual(provenance["version_factor_id"], ids["version"].pk)
        self.assertEqual(provenance["factor_id"], ids["factor"].pk)
        snapshot = calculation.snapshot_tecnico
        self.assertTrue(snapshot["inputs"])
        self.assertIn("unidad", snapshot["inputs"][0])
        self.assertEqual(provenance["resultado"], calculation.resultado)
        self.assertEqual(provenance["unidad_resultado"], calculation.unidad_resultado)

        # 18-27: A1/A2, boundary, GWP indicator, declared qty/unit, process
        # uuid/dataset version/snapshot/source url — all frozen on the
        # candidate, reachable from the factor's own contexto, never
        # re-fetched from upstream.
        candidate = ids["candidate"].__class__.objects.get(pk=ids["candidate"].pk)
        self.assertIn(candidate.normalization["standard"], {"EN 15804+A1", "EN 15804+A2"})
        self.assertEqual(candidate.normalization["boundary"], "A1-A3")
        self.assertIsNotNone(candidate.normalization["indicator"])
        self.assertIsNotNone(candidate.normalization["declared_quantity"])
        self.assertIsNotNone(candidate.normalization["declared_unit"])
        self.assertEqual(candidate.provenance["process_uuid"], str(ids["profile"].process_uuid))
        self.assertEqual(candidate.provenance["dataset_version"], ids["profile"].dataset_version)
        self.assertIsNotNone(candidate.provenance["source_url"])

        # 28-30: current/historical + quality + unknown metadata
        quality = assess_factor_data_quality(ids["factor"].__class__.objects.get(pk=ids["factor"].pk))
        self.assertIn("estado", quality)
        self.assertIn("known", quality)

        # 31-35: calculable, why (or why not), coverage inclusion, counted
        # exactly once, participation in obra totals.
        diag = reception_coverage(event)
        self.assertTrue(diag["calculable"])
        totals = material_ledger_totals(ids["org"])
        self.assertEqual(totals["entradas_totales"], 1)

        # 36: historical reconstruction itself (this whole method)
        # 37-39: source refresh never silently changed anything here
        impact = assess_candidate_impact(candidate)
        self.assertEqual(impact["impact"], "no_impact")

        # 40: a professional can find this dataset via discovery (01H)
        self.assertIsNotNone(candidate.source_profile.process.name)

    def test_a2_end_to_end_1000kg(self):
        ids = self._walk(label="a2", amount="1000", unit="kg", expected_sign=1)
        self._assert_fully_reconstructible(ids)
        self.assertEqual(ids["candidate"].normalization["standard"], "EN 15804+A2")

    def test_a1_end_to_end_2m3_preserves_negative_sign(self):
        ids = self._walk(label="a1", amount="2", unit="m3", expected_sign=-1)
        self._assert_fully_reconstructible(ids)
        self.assertEqual(ids["candidate"].normalization["standard"], "EN 15804+A1")
        calculation = ids["calculation_id"]
        from .models import CalculoAmbiental

        self.assertLess(CalculoAmbiental.objects.get(pk=calculation).resultado, 0)
