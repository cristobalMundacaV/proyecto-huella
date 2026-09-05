from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.knowledge.models import (
    EnvironmentalSource,
    ExternalFileArtifact,
    ExternalRecord,
    ExternalSnapshot,
    HuellaChileEmissionFactorFact,
    SyncRun,
)

from .models import (
    EnvironmentalFactorCandidate,
    FactorAmbiental,
    Organizacion,
    VersionFactorAmbiental,
)
from .services.factor_candidates import (
    apply_candidate_mapping,
    build_huellachile_factor_candidates,
    equivalent_global_factors,
    evaluate_factor_candidate_compatibility,
    parse_emission_factor_unit,
    promote_candidate_to_draft,
)
from .services.factor_governance import transition_factor_version
from .services.fuel_factor_selector import select_fuel_factor


class FactorCandidateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()
        cls.source, _ = EnvironmentalSource.objects.get_or_create(
            codigo="huellachile",
            defaults={
                "nombre": "HuellaChile",
                "organismo": "MMA",
                "connector_key": "pending-huellachile",
                "tipo_acceso": "FILE",
                "nivel_autoridad": "oficial",
            },
        )
        run = SyncRun.objects.create(
            source=cls.source, trigger="manual", started_at=now
        )
        snapshot = ExternalSnapshot.objects.create(
            source=cls.source,
            sync_run=run,
            external_id="workbook",
            record_kind="file",
            retrieved_at=now,
            content_hash="a" * 64,
        )
        record = ExternalRecord.objects.create(
            source=cls.source,
            external_id="workbook",
            kind="file",
            current_snapshot=snapshot,
            first_seen_at=now,
            last_seen_at=now,
        )
        cls.artifact = ExternalFileArtifact.objects.create(
            source=cls.source,
            parent_record=record,
            external_resource_id="hc-2025",
            name="Factores 2025.xlsx",
            source_url="https://example.test/hc.xlsx",
            format="XLSX",
            byte_size=42,
            retrieved_at=now,
            content_sha256="b" * 64,
            is_current=True,
            version=1,
        )
        cls.superuser = get_user_model().objects.create_superuser(
            "root", "root@example.test", "pass"
        )
        cls.user = get_user_model().objects.create_user("tenant", password="pass")
        cls.organization = Organizacion.objects.create(nombre="Tenant")

    def fact(self, row=1, **overrides):
        values = {
            "artifact": self.artifact,
            "sheet_name": "Factores",
            "source_row_number": row,
            "row_hash": f"{row:064x}",
            "raw_row": {},
            "dataset_year": 2025,
            "alcance": "Alcance 1",
            "categoria": "Combustión estacionaria",
            "subcategoria": "Combustible",
            "actividad": "Petróleo 2 (Diésel)",
            "auxiliar": "",
            "unidad_actividad": "metros cúbicos",
            "factor_value": Decimal("2710"),
            "published_value_raw": "2710",
            "unidad_factor": "kgCO2e/metros cúbicos",
            "technical_source_1": "Ministerio de Energía",
            "cached_value_available": True,
        }
        values.update(overrides)
        return HuellaChileEmissionFactorFact.objects.create(**values)

    def candidate(self, row=1, **overrides):
        fact = self.fact(row, **overrides)
        candidate = EnvironmentalFactorCandidate.objects.create(source_fact=fact)
        candidate.compatibility = evaluate_factor_candidate_compatibility(candidate)
        candidate.status = (
            candidate.Status.REQUIRES_MAPPING
            if candidate.compatibility["compatible"]
            else candidate.Status.DETECTED
        )
        candidate.save()
        return candidate

    def map_fuel(self, candidate):
        return apply_candidate_mapping(
            candidate,
            self.superuser,
            "combustible",
            {
                "alcance": 1,
                "categoria_huella": "combustion_estacionaria",
                "combustible": "candidate-diesel",
            },
        )

    def map_energy(self, candidate, system="SEN"):
        return apply_candidate_mapping(
            candidate,
            self.superuser,
            "energia_red",
            {
                "alcance": 2,
                "sistema": system,
                "metodo": "location_based",
                "pais": "Chile",
            },
        )

    def test_unit_parsing_and_mechanical_compatibility(self):
        self.assertEqual(parse_emission_factor_unit("kgCO2e/m3")["input_unit"], "m3")
        self.assertEqual(parse_emission_factor_unit("kgCO2e/MWh")["input_unit"], "MWh")
        self.assertEqual(
            parse_emission_factor_unit("kgCO2e/pasajero-km")["reason"],
            "unidad_no_soportada",
        )
        compatible_conversion = self.candidate(2, unidad_actividad="litros")
        self.assertTrue(compatible_conversion.compatibility["compatible"])
        incompatible = self.candidate(3, unidad_actividad="kilogramos")
        self.assertIn("denominador_incompatible", incompatible.compatibility["reasons"])

    def test_build_is_idempotent_and_pending_is_not_promotable(self):
        self.fact()
        self.fact(
            2,
            factor_value=None,
            published_value_raw="PENDIENTE",
            cached_value_available=False,
        )
        first = build_huellachile_factor_candidates(2025)
        second = build_huellachile_factor_candidates(2025)
        self.assertEqual(
            (first["candidates_created"], second["candidates_created"]), (2, 0)
        )
        pending = EnvironmentalFactorCandidate.objects.get(
            source_fact__source_row_number=2
        )
        with self.assertRaises(ValidationError):
            apply_candidate_mapping(
                pending,
                self.superuser,
                "combustible",
                {
                    "alcance": 1,
                    "categoria_huella": "combustion_movil",
                    "combustible": "diesel",
                },
            )

    def test_mapping_contracts(self):
        candidate = self.candidate()
        with self.assertRaises(ValidationError):
            apply_candidate_mapping(
                candidate, self.superuser, "combustible", {"alcance": 2}
            )
        mapped = self.map_fuel(candidate)
        self.assertEqual(mapped.status, mapped.Status.READY)
        energy = self.candidate(
            2,
            alcance="Alcance 2",
            categoria="Electricidad",
            actividad="SEN",
            unidad_actividad="MWh",
            unidad_factor="kgCO2e/MWh",
        )
        mapped_energy = apply_candidate_mapping(
            energy,
            self.superuser,
            "energia_red",
            {
                "alcance": 2,
                "sistema": "SEN",
                "metodo": "location_based",
                "pais": "Chile",
            },
        )
        self.assertEqual(mapped_energy.mapping_context["sistema"], "SEN")

    def test_sen_candidate_matches_legacy_without_provider(self):
        candidate = self.candidate(
            2,
            alcance="Alcance 2",
            categoria="Electricidad",
            actividad="Sistema Eléctrico Nacional",
            unidad_actividad="MWh",
            unidad_factor="kgCO2e/MWh",
            factor_value=Decimal("246.7249809219505"),
        )
        self.map_energy(candidate)
        equivalence = equivalent_global_factors(candidate)
        self.assertEqual(equivalence["status"], "equivalente_unico")
        self.assertEqual(
            equivalence["factors"][0].codigo, "sen-electricidad-red-location-based-2025"
        )

    def test_create_global_energy_uses_internal_category(self):
        candidate = self.candidate(
            2,
            alcance="Alcance 2",
            categoria="Electricidad",
            actividad="Red aislada",
            unidad_actividad="MWh",
            unidad_factor="kgCO2e/MWh",
        )
        self.map_energy(candidate, system="SISTEMA-PRUEBA")
        factor, version = promote_candidate_to_draft(
            candidate, self.superuser, "create_global"
        )
        self.assertEqual(factor.categoria, "electricidad_red")
        self.assertEqual(version.estado, "borrador")

    def test_duplicate_active_sen_identity_is_blocked_without_provider(self):
        legacy = FactorAmbiental.objects.get(
            codigo="sen-electricidad-red-location-based-2025"
        )
        duplicate = FactorAmbiental.objects.create(
            codigo="sen-duplicate",
            nombre="SEN duplicate",
            categoria="electricidad_red",
            unidad_entrada="MWh",
            unidad_resultado="kgCO2e",
            contexto={
                "proveedor": "HuellaChile",
                "alcance": 2,
                "sistema": "SEN",
                "metodo": "location_based",
                "pais": "Chile",
            },
        )
        version = VersionFactorAmbiental.objects.create(
            factor=duplicate, version=1, valor=Decimal("246.7"), fuente="test"
        )
        transition_factor_version(version, "pruebas")
        transition_factor_version(version, "validado")
        with self.assertRaises(ValidationError):
            transition_factor_version(version, "activo")
        self.assertEqual(legacy.versiones.get(estado="activo").estado, "activo")

    def test_historical_candidate_blocks_mapping_and_promotion_but_remains_readable(
        self,
    ):
        candidate = self.candidate()
        self.artifact.is_current = False
        self.artifact.save(update_fields=["is_current"])
        with self.assertRaisesMessage(
            ValidationError, "fuente_historica_no_promocionable"
        ):
            self.map_fuel(candidate)

        self.artifact.is_current = True
        self.artifact.save(update_fields=["is_current"])
        self.map_fuel(candidate)
        self.artifact.is_current = False
        self.artifact.save(update_fields=["is_current"])
        with self.assertRaisesMessage(
            ValidationError, "fuente_historica_no_promocionable"
        ):
            promote_candidate_to_draft(candidate, self.superuser, "create_global")

        client = APIClient()
        client.force_authenticate(self.superuser)
        response = client.get(
            f"/api/environmental-governance/factor-candidates/{candidate.id}/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["source"]["source_current"])

    def test_create_global_is_draft_preserves_provenance_and_is_single_use(self):
        candidate = self.map_fuel(self.candidate())
        before = candidate.source_fact.raw_row.copy()
        factor, version = promote_candidate_to_draft(
            candidate, self.superuser, "create_global"
        )
        self.assertIsNone(factor.organizacion_id)
        self.assertEqual(version.estado, version.Estado.BORRADOR)
        self.assertEqual(
            version.contexto["knowledge_source"]["artifact_sha256"], "b" * 64
        )
        self.assertIn(
            "Ministerio de Energía",
            version.contexto["knowledge_source"]["technical_sources"],
        )
        candidate.source_fact.refresh_from_db()
        self.assertEqual(candidate.source_fact.raw_row, before)
        with self.assertRaises(ValidationError):
            promote_candidate_to_draft(candidate, self.superuser, "create_global")

    def test_equivalent_new_version_converts_value_and_does_not_touch_active(self):
        candidate = self.map_fuel(self.candidate())
        factor = FactorAmbiental.objects.create(
            codigo="diesel-existing",
            nombre="Diésel",
            categoria="combustion_estacionaria",
            unidad_entrada="m3",
            unidad_resultado="tCO2e",
            contexto=candidate.mapping_context,
        )
        active = VersionFactorAmbiental.objects.create(
            factor=factor,
            version=1,
            valor=Decimal("2.70"),
            fuente="legacy",
            estado="activo",
        )
        self.assertEqual(
            equivalent_global_factors(candidate)["status"], "equivalente_unico"
        )
        _, draft = promote_candidate_to_draft(
            candidate, self.superuser, "new_version", factor
        )
        active.refresh_from_db()
        self.assertEqual(active.estado, "activo")
        self.assertEqual(draft.valor, Decimal("2.71"))
        self.assertEqual(draft.estado, "borrador")

    def test_multiple_equivalents_block_promotion(self):
        candidate = self.map_fuel(self.candidate())
        for suffix in ("one", "two"):
            FactorAmbiental.objects.create(
                codigo=f"equivalent-{suffix}",
                nombre=suffix,
                categoria="combustion_estacionaria",
                unidad_entrada="m3",
                unidad_resultado="tCO2e",
                contexto=candidate.mapping_context,
            )
        self.assertEqual(
            equivalent_global_factors(candidate)["status"], "conflicto_multiple"
        )
        with self.assertRaises(ValidationError):
            promote_candidate_to_draft(candidate, self.superuser, "new_version")

    def test_selector_ignores_until_active_and_global_conflict_is_blocked(self):
        candidate = self.map_fuel(self.candidate())
        factor, version = promote_candidate_to_draft(
            candidate, self.superuser, "create_global"
        )
        args = (
            self.organization,
            {"estado": "clasificado", "categoria": "combustion_estacionaria"},
            "candidate-diesel",
            "m3",
            date(2025, 6, 1),
        )
        self.assertEqual(select_fuel_factor(*args)["estado"], "no_calculable")
        for state in ("pruebas", "validado"):
            transition_factor_version(version, state)
            self.assertEqual(select_fuel_factor(*args)["estado"], "no_calculable")
        transition_factor_version(version, "activo")
        self.assertEqual(select_fuel_factor(*args)["factor_version"].id, version.id)
        other = FactorAmbiental.objects.create(
            codigo="duplicate",
            nombre="Duplicate",
            categoria=factor.categoria,
            unidad_entrada="m3",
            unidad_resultado="kgCO2e",
            contexto=factor.contexto,
        )
        duplicate = VersionFactorAmbiental.objects.create(
            factor=other, version=1, valor=1, fuente="test"
        )
        transition_factor_version(duplicate, "pruebas")
        transition_factor_version(duplicate, "validado")
        with self.assertRaises(ValidationError):
            transition_factor_version(duplicate, "activo")

    def test_write_endpoints_are_superuser_only(self):
        candidate = self.candidate()
        url = f"/api/environmental-governance/factor-candidates/{candidate.id}/mapping/"
        client = APIClient()
        client.force_authenticate(self.user)
        self.assertEqual(
            client.get("/api/environmental-governance/factor-candidates/").status_code,
            403,
        )
        self.assertEqual(
            client.get(
                f"/api/environmental-governance/factor-candidates/{candidate.id}/"
            ).status_code,
            403,
        )
        self.assertEqual(client.post(url, {}, format="json").status_code, 403)
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.assertEqual(client.post(url, {}, format="json").status_code, 403)
        client.force_authenticate(self.superuser)
        self.assertEqual(
            client.get("/api/environmental-governance/factor-candidates/").status_code,
            200,
        )
        response = client.post(
            url,
            {
                "mapping_type": "combustible",
                "mapping_context": {
                    "alcance": 1,
                    "categoria_huella": "combustion_estacionaria",
                    "combustible": "diesel",
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        detail = client.get(
            f"/api/environmental-governance/factor-candidates/{candidate.id}/"
        )
        self.assertEqual(detail.data["source"]["artifact_sha256"], "b" * 64)

    def test_696_facts_build_696_candidates(self):
        facts = []
        for row in range(1, 697):
            facts.append(
                HuellaChileEmissionFactorFact(
                    artifact=self.artifact,
                    sheet_name="Factores",
                    source_row_number=row,
                    row_hash=f"{row:064x}",
                    raw_row={},
                    dataset_year=2025,
                    alcance="Alcance 1",
                    categoria="Combustión",
                    subcategoria="",
                    actividad=f"Actividad {row}",
                    auxiliar="",
                    unidad_actividad="metros cúbicos",
                    factor_value=Decimal("1"),
                    published_value_raw="1",
                    unidad_factor="kgCO2e/metros cúbicos",
                    cached_value_available=True,
                )
            )
        HuellaChileEmissionFactorFact.objects.bulk_create(facts)
        first = build_huellachile_factor_candidates()
        second = build_huellachile_factor_candidates()
        self.assertEqual(first["facts"], 696)
        self.assertEqual(EnvironmentalFactorCandidate.objects.count(), 696)
        self.assertEqual(second["candidates_created"], 0)
