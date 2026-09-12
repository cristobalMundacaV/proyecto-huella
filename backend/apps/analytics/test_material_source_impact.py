from datetime import date
from threading import Barrier, Thread
from unittest.mock import patch
from urllib.parse import urlparse

from defusedxml import ElementTree as ET
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.knowledge import test_okobaudat_detail as detail_tests
from apps.knowledge.connectors.okobaudat_detail import NS
from apps.knowledge.models import ExternalRecord, OekobaudatEnvironmentalProfileFact as Profile
from apps.knowledge.okobaudat_detail_sync import hydrate_process
from apps.knowledge.test_okobaudat_detail import fetch, fixture, make_process


def _mutate_version_and_gwp(label, *, new_version, new_gwp=None):
    """Mutate BOTH the detail's own declared dataset version (so
    parse_profile's identity check passes for a synthetic newer version)
    and, optionally, the GWP amount, in a single fixture body."""
    root = ET.fromstring(fixture(label))
    version_node = root.find(
        "p:administrativeInformation/p:publicationAndOwnership/c:dataSetVersion", NS
    )
    version_node.text = new_version
    if new_gwp is not None:
        amount_node = root.find("p:LCIAResults/p:LCIAResult/c:other/e:amount", NS)
        amount_node.text = str(new_gwp)
    return ET.tostring(root)

from .models import FactorAmbiental, MaterialOperacional, Organizacion, VersionFactorAmbiental
from .services.calculation_v2 import calculate_activity
from .services.material_candidates import build_material_candidate, promote_material_candidate, review_material_candidate
from .services.material_factor_mapping import approve_material_mapping, propose_material_mapping
from .services.material_source_impact import (NO_IMPACT, REVIEW_REQUIRED, REVIEW_RECOMMENDED,
                                               assess_all_candidates, assess_candidate_impact)
from .services.system_environmental_catalog import ensure_system_environmental_catalog
from .test_material_candidates import material_fixture

User = get_user_model()


def _fetch_for_version(new_version, new_gwp=None):
    def _fetch(url):
        kind = urlparse(url).path.split("/")[-2]
        if kind == "processes":
            return _mutate_version_and_gwp("a2", new_version=new_version, new_gwp=new_gwp)
        return fetch(url)

    return _fetch


class MaterialSourceImpactTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("impact-admin", "impact-admin@example.com", "password")

    def hydrate_new_version(self, *, version="00.02.000", gwp=None):
        process, run = make_process("a2", version=version)
        now = timezone.now()
        ExternalRecord.objects.create(
            source=run.source, external_id=process.snapshot.external_id, kind="okobaudat_process",
            current_snapshot=process.snapshot, first_seen_at=now, last_seen_at=now,
        )
        side_effect = _fetch_for_version(version, gwp)
        with patch("apps.knowledge.okobaudat_detail_sync.fetch_detail_bytes", side_effect=side_effect):
            result = hydrate_process(process, run, delay=0)
        assert result["status"] == "materialized", result
        return Profile.objects.get(process=process)

    def test_unchanged_version_is_no_impact(self):
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        result = assess_candidate_impact(candidate)
        self.assertEqual(result["impact"], NO_IMPACT)
        self.assertEqual(result["reasons"], [])

    def test_new_dataset_version_not_yet_hydrated_is_review_recommended(self):
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        now = timezone.now()
        process2, run2 = make_process("a2", version="00.02.000")
        ExternalRecord.objects.create(
            source=run2.source, external_id=process2.snapshot.external_id, kind="okobaudat_process",
            current_snapshot=process2.snapshot, first_seen_at=now, last_seen_at=now,
        )
        result = assess_candidate_impact(candidate)
        self.assertEqual(result["impact"], REVIEW_RECOMMENDED)
        self.assertIn("nueva_version_disponible", result["reasons"])
        self.assertIn("nueva_version_no_hidratada_localmente", result["reasons"])
        self.assertEqual(result["upstream_dataset_version"], "00.02.000")

    def test_new_version_hydrated_but_not_built_as_candidate(self):
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        self.hydrate_new_version()
        result = assess_candidate_impact(candidate)
        self.assertEqual(result["impact"], REVIEW_RECOMMENDED)
        self.assertIn("nueva_version_no_evaluada_como_candidato", result["reasons"])

    def test_new_version_with_unchanged_gwp_is_review_recommended_only(self):
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        newer_profile = self.hydrate_new_version()
        build_material_candidate(newer_profile.pk)
        result = assess_candidate_impact(candidate)
        self.assertEqual(result["impact"], REVIEW_RECOMMENDED)
        self.assertNotIn("gwp_modificado", result["reasons"])

    def test_changed_gwp_is_review_required(self):
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        newer_profile = self.hydrate_new_version(gwp="999.0")
        build_material_candidate(newer_profile.pk)
        result = assess_candidate_impact(candidate)
        self.assertEqual(result["impact"], REVIEW_REQUIRED)
        self.assertIn("gwp_modificado", result["reasons"])

    def test_missing_active_process_is_review_required(self):
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        ExternalRecord.objects.filter(
            current_snapshot_id=profile.process.snapshot_id
        ).update(estado="retirado")
        result = assess_candidate_impact(candidate)
        self.assertEqual(result["impact"], REVIEW_REQUIRED)
        self.assertIn("proceso_no_activo", result["reasons"])

    def test_republish_same_version_different_hash_is_review_required(self):
        import hashlib

        from apps.knowledge.models import EnvironmentalSource, ExternalSnapshot, SyncRun

        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        now = timezone.now()
        source = EnvironmentalSource.objects.get(codigo="okobaudat")
        run2 = SyncRun.objects.create(source=source, trigger="manual", started_at=now)
        payload = {
            "process_uuid": str(profile.process_uuid), "dataset_version": profile.dataset_version,
            "datastock_uuid": str(profile.process.datastock_uuid),
            "name": "Republished fixture", "source_url": profile.process.source_url,
            "compliance_standard_raw": profile.process.compliance_standard_raw,
            "classification": [{"name": "fixture"}], "languages": {"en": ["Republished fixture"]},
            "process_metadata": {"fixture": "a2-republished"},
        }
        snapshot2 = ExternalSnapshot.objects.create(
            source=source, sync_run=run2, external_id=f"catalog-republish:{profile.process_uuid}:{profile.dataset_version}",
            record_kind="okobaudat_process", retrieved_at=now,
            content_hash=hashlib.sha256(str(payload).encode()).hexdigest(), raw_payload=payload,
        )
        # Real republish: the *same* ExternalRecord's pointer moves to a new
        # snapshot with a different hash, not a brand new record.
        ExternalRecord.objects.filter(
            current_snapshot_id=profile.process.snapshot_id
        ).update(current_snapshot=snapshot2, last_seen_at=now)
        result = assess_candidate_impact(candidate)
        self.assertEqual(result["impact"], REVIEW_REQUIRED)
        self.assertIn("republicacion_detectada_mismo_dataset_version", result["reasons"])

    def test_assessment_never_mutates_candidate_factor_or_mapping(self):
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        review_material_candidate(candidate.pk, self.user, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.user)
        org = Organizacion.objects.create(nombre="Impacto tenant")
        material = MaterialOperacional.objects.create(
            organizacion=org, codigo="MAT-IMPACT", nombre="Material", categoria="cemento", unidad_base="kg",
        )
        mapping = propose_material_mapping(org, material, factor, date(2026, 1, 1), None, self.user)
        approve_material_mapping(mapping.pk, org, self.user)
        self.hydrate_new_version(gwp="999.0")

        before_factor = FactorAmbiental.objects.get(pk=factor.pk).contexto
        before_version_estado = VersionFactorAmbiental.objects.get(pk=version.pk).estado
        result = assess_candidate_impact(candidate.__class__.objects.get(pk=candidate.pk))
        after_factor = FactorAmbiental.objects.get(pk=factor.pk).contexto
        after_version_estado = VersionFactorAmbiental.objects.get(pk=version.pk).estado
        mapping.refresh_from_db()

        self.assertEqual(before_factor, after_factor)
        self.assertEqual(before_version_estado, after_version_estado)
        self.assertEqual(mapping.estado, "aprobado")
        self.assertIn(factor.pk, [result["affected"]["promoted_factor_id"]])
        self.assertIn(mapping.pk, result["affected"]["mapping_ids"])

    def test_historical_calculation_preserved_after_impact_assessment(self):
        ensure_system_environmental_catalog()
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        review_material_candidate(candidate.pk, self.user, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.user)
        version.estado = "pruebas"
        version.save()
        version.estado = "validado"
        version.save()
        version.estado = "activo"
        version.save()

        org = Organizacion.objects.create(nombre="Impacto historico")
        from apps.analytics.models import ActividadOperacional, EventoMaterial, FuenteDatos, Obra, Observacion
        from decimal import Decimal

        work = Obra.objects.create(organizacion=org, nombre="Obra", fecha_inicio=date(2026, 1, 1))
        source = FuenteDatos.objects.create(organizacion=org, nombre="Guia", tipo="manual")
        material = MaterialOperacional.objects.create(
            organizacion=org, codigo="MAT-HIST", nombre="Material", categoria="cemento", unidad_base="kg",
        )
        mapping = propose_material_mapping(org, material, factor, date(2026, 1, 1), None, self.user)
        approve_material_mapping(mapping.pk, org, self.user)
        at = timezone.now()
        activity = ActividadOperacional.objects.create(
            organizacion=org, obra=work, codigo="ACT-HIST", nombre="recepcion",
            tipo="movimiento_material", timestamp_inicio=at,
        )
        observation = Observacion.objects.create(
            organizacion=org, actividad=activity, fuente=source, concepto="cantidad_material",
            valor_numerico=Decimal("100"), unidad="kg", timestamp_observacion=at,
            estado=Observacion.Estado.VALIDADA,
        )
        EventoMaterial.objects.create(
            organizacion=org, material=material, actividad=activity, obra=work,
            tipo="recepcion", fecha_hora=at, observacion_cantidad=observation, fuente=source,
        )
        calculation, _ = calculate_activity(activity)
        original_result = calculation.resultado

        self.hydrate_new_version(gwp="999.0")
        assess_candidate_impact(candidate.__class__.objects.get(pk=candidate.pk))

        calculation.refresh_from_db()
        self.assertEqual(calculation.resultado, original_result)

    def test_idempotent_assessment(self):
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        self.hydrate_new_version(gwp="999.0")
        first = assess_candidate_impact(candidate.__class__.objects.get(pk=candidate.pk))
        second = assess_candidate_impact(candidate.__class__.objects.get(pk=candidate.pk))
        self.assertEqual(first, second)

    def test_assess_all_candidates_summary(self):
        build_material_candidate(material_fixture("a1").pk)
        build_material_candidate(material_fixture("a2").pk)
        report = assess_all_candidates()
        self.assertEqual(report["total"], 2)
        self.assertEqual(report["resumen"][NO_IMPACT], 2)
        self.assertEqual(len(report["resultados"]), 2)


class MaterialSourceImpactConcurrencyTests(TransactionTestCase):
    _fixture_teardown = detail_tests.DetailPostgresTests._fixture_teardown

    def test_concurrent_assessment_produces_consistent_results(self):
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        now = timezone.now()
        process2, run2 = make_process("a2", version="00.02.000")
        ExternalRecord.objects.create(
            source=run2.source, external_id=process2.snapshot.external_id, kind="okobaudat_process",
            current_snapshot=process2.snapshot, first_seen_at=now, last_seen_at=now,
        )
        barrier = Barrier(2)
        results, errors = [], []

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                fresh = candidate.__class__.objects.get(pk=candidate.pk)
                results.append(assess_candidate_impact(fresh))
            except Exception as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(20)
        self.assertTrue(all(not t.is_alive() for t in threads))
        self.assertFalse(errors, errors)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], results[1])
