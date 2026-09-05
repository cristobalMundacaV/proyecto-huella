from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.knowledge.models import (
    EnvironmentalSource,
    ExternalFileArtifact,
    ExternalRecord,
    ExternalSnapshot,
    HuellaChileEmissionFactorFact,
    SyncRun,
)

from .models import (
    ActividadOperacional,
    CalculoAmbiental,
    EnvironmentalFactorCandidate,
    EnvironmentalFactorReconciliation,
    FactorAmbiental,
    Organizacion,
    VersionFactorAmbiental,
)
from .services.factor_candidates import build_huellachile_factor_candidates
from .services.factor_reconciliation import (
    EXPECTED_SHA,
    RECONCILIATION_MANIFEST,
    advance_reconciliation,
    prepare_reconciliation,
    reconciliation_report,
    switch_reconciliation,
)
from .services.fuel_factor_selector import select_fuel_factor
from .services.system_environmental_catalog import ensure_system_environmental_catalog


class FactorReconciliationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()
        cls.user = get_user_model().objects.create_superuser(
            "reviewer", "r@example.test", "pass"
        )
        source = EnvironmentalSource.objects.get(codigo="huellachile")
        run = SyncRun.objects.create(source=source, trigger="manual", started_at=now)
        snapshot = ExternalSnapshot.objects.create(
            source=source,
            sync_run=run,
            external_id="hc-2025",
            record_kind="file",
            retrieved_at=now,
            content_hash="c" * 64,
        )
        record = ExternalRecord.objects.create(
            source=source,
            external_id="hc-2025",
            kind="file",
            current_snapshot=snapshot,
            first_seen_at=now,
            last_seen_at=now,
        )
        cls.artifact = ExternalFileArtifact.objects.create(
            source=source,
            parent_record=record,
            external_resource_id="hc-2025",
            name="HuellaChile 2025",
            source_url="https://example.test/hc.xlsx",
            format="XLSX",
            byte_size=1,
            retrieved_at=now,
            content_sha256=EXPECTED_SHA,
            is_current=True,
            version=1,
        )
        values = {
            28: "1674.6640209139498",
            30: "1.9804687688971803",
            36: "2714.5332574466397",
            42: "2740.160339286552",
            44: "1717.6115899106999",
            46: "2.09326078848132",
            187: "246.7249809219505",
        }
        for entry in RECONCILIATION_MANIFEST:
            HuellaChileEmissionFactorFact.objects.create(
                artifact=cls.artifact,
                sheet_name="RESUMEN",
                source_row_number=entry["row"],
                row_hash=f"{entry['row']:064x}",
                raw_row={},
                dataset_year=2025,
                alcance=entry["scope"],
                categoria=(
                    "2.1 Electricidad"
                    if entry["row"] == 187
                    else (
                        "1.1 Combustión estacionaria"
                        if entry["row"] < 40
                        else "1.2 Combustión móvil"
                    )
                ),
                subcategoria="",
                actividad=entry["activity"],
                auxiliar="2025" if entry["row"] == 187 else "-",
                unidad_actividad=entry["activity_unit"],
                factor_value=Decimal(values[entry["row"]]),
                published_value_raw=values[entry["row"]],
                unidad_factor=entry["factor_unit"],
                cached_value_available=True,
                technical_source_1="Fuente técnica",
            )
        build_huellachile_factor_candidates()
        legacy_values = {
            "huellachile-combustion-estacionaria-glp": "1.59",
            "huellachile-combustion-estacionaria-gas-natural": "1.98",
            "huellachile-combustion-estacionaria-diesel": "2.71",
            "huellachile-combustion-movil-glp": "1.72",
            "huellachile-combustion-movil-gas-natural": "2.09",
            "huellachile-combustion-movil-diesel": "2.74",
            "sen-electricidad-red-location-based-2025": "0.2466",
        }
        for code, value in legacy_values.items():
            factor = FactorAmbiental.objects.get(codigo=code)
            VersionFactorAmbiental.objects.create(
                factor=factor,
                version=1,
                valor=Decimal(value),
                fuente="Legacy",
                referencia="Legacy hardcoded",
                estado="activo",
            )

    def prepare_and_validate(self):
        result = prepare_reconciliation(self.user, 2025, EXPECTED_SHA)
        self.assertEqual(result["created"], 7)
        advance_reconciliation(self.user, "pruebas")
        advance_reconciliation(self.user, "validado")

    def test_dry_run_prepare_idempotence_governance_switch_and_bootstrap(self):
        before = (
            EnvironmentalFactorCandidate.objects.count(),
            VersionFactorAmbiental.objects.count(),
        )
        report = reconciliation_report()
        self.assertEqual(len(report), 7)
        self.assertTrue(all(row["readiness"] == "ready" for row in report))
        self.assertEqual(
            before,
            (
                EnvironmentalFactorCandidate.objects.count(),
                VersionFactorAmbiental.objects.count(),
            ),
        )
        self.assertEqual(
            prepare_reconciliation(self.user, 2025, EXPECTED_SHA)["created"], 7
        )
        self.assertEqual(
            prepare_reconciliation(self.user, 2025, EXPECTED_SHA),
            {"created": 0, "existing": 7},
        )
        self.assertEqual(
            VersionFactorAmbiental.objects.filter(
                version=1,
                estado="activo",
                factor__codigo__in=[e["factor_code"] for e in RECONCILIATION_MANIFEST],
            ).count(),
            7,
        )
        advance_reconciliation(self.user, "pruebas")
        advance_reconciliation(self.user, "validado")
        organization = Organizacion.objects.create(nombre="Histórico")
        activity = ActividadOperacional.objects.create(
            organizacion=organization,
            codigo="HIST-1",
            nombre="Histórico",
            tipo="consumo_energia",
            timestamp_inicio=timezone.now(),
        )
        legacy_sen = VersionFactorAmbiental.objects.get(
            factor__codigo="sen-electricidad-red-location-based-2025", version=1
        )
        methodology = legacy_sen.factor.formulas.get().version_metodologia
        historical = CalculoAmbiental.objects.create(
            organizacion=organization,
            actividad=activity,
            version_metodologia=methodology,
            formula=methodology.formula,
            version_factor=legacy_sen,
            resultado=Decimal("0.2466"),
            unidad_resultado="tCO2e",
            formula_aplicada="fixture",
            completitud="completo",
            snapshot_tecnico={
                "version_factor_id": legacy_sen.id,
                "resultado": "0.2466",
            },
        )
        historical_snapshot = historical.snapshot_tecnico.copy()
        switch_reconciliation(self.user, 2025, EXPECTED_SHA)
        self.assertEqual(
            VersionFactorAmbiental.objects.filter(
                version=1,
                estado="obsoleto",
                factor__codigo__in=[e["factor_code"] for e in RECONCILIATION_MANIFEST],
            ).count(),
            7,
        )
        self.assertEqual(
            VersionFactorAmbiental.objects.filter(
                version=2,
                estado="activo",
                factor__codigo__in=[e["factor_code"] for e in RECONCILIATION_MANIFEST],
            ).count(),
            7,
        )
        self.assertEqual(
            EnvironmentalFactorReconciliation.objects.filter(status="cambiado").count(),
            7,
        )
        historical.refresh_from_db()
        self.assertEqual(historical.version_factor_id, legacy_sen.id)
        self.assertEqual(historical.resultado, Decimal("0.2466"))
        self.assertEqual(historical.snapshot_tecnico, historical_snapshot)
        for category in ("combustion_estacionaria", "combustion_movil"):
            selected = select_fuel_factor(
                organization,
                {"estado": "clasificado", "categoria": category},
                "diesel",
                "m3",
                date(2025, 6, 1),
            )
            self.assertEqual(selected["estado"], "seleccionado")
            self.assertEqual(selected["factor_version"].version, 2)
        self.assertEqual(
            VersionFactorAmbiental.objects.get(
                factor__codigo="sen-electricidad-red-location-based-2025",
                estado="activo",
            ).version,
            2,
        )
        ensure_system_environmental_catalog()
        ensure_system_environmental_catalog()
        self.assertEqual(
            VersionFactorAmbiental.objects.filter(
                factor__codigo__in=[e["factor_code"] for e in RECONCILIATION_MANIFEST]
            ).count(),
            14,
        )

    def test_sha_historical_and_unexpected_fact_fail_closed(self):
        with self.assertRaises(ValidationError):
            prepare_reconciliation(self.user, 2025, "0" * 64)
        self.artifact.is_current = False
        self.artifact.save(update_fields=["is_current"])
        with self.assertRaises(ValidationError):
            prepare_reconciliation(self.user, 2025, EXPECTED_SHA)
        self.artifact.is_current = True
        self.artifact.save(update_fields=["is_current"])
        fact = HuellaChileEmissionFactorFact.objects.get(source_row_number=28)
        fact.actividad = "Actividad inesperada"
        fact.save(update_fields=["actividad"])
        with self.assertRaises(ValidationError):
            reconciliation_report()

    def test_switch_rolls_back_if_seventh_transition_fails(self):
        self.prepare_and_validate()
        from .services.factor_governance import (
            transition_factor_version as real_transition,
        )

        calls = {"count": 0}

        def failing_transition(version, target):
            calls["count"] += 1
            if calls["count"] == 13:
                raise ValidationError("fallo séptimo controlado")
            return real_transition(version, target)

        with patch(
            "apps.analytics.services.factor_reconciliation.transition_factor_version",
            side_effect=failing_transition,
        ):
            with self.assertRaises(ValidationError):
                switch_reconciliation(self.user, 2025, EXPECTED_SHA)
        self.assertEqual(
            VersionFactorAmbiental.objects.filter(
                version=1,
                estado="activo",
                factor__codigo__in=[e["factor_code"] for e in RECONCILIATION_MANIFEST],
            ).count(),
            7,
        )
        self.assertEqual(
            VersionFactorAmbiental.objects.filter(
                version=2,
                estado="validado",
                factor__codigo__in=[e["factor_code"] for e in RECONCILIATION_MANIFEST],
            ).count(),
            7,
        )

    def test_clean_catalog_has_shells_without_numeric_versions_and_legacy_command_fails(
        self,
    ):
        versions = VersionFactorAmbiental.objects.filter(
            factor__codigo__in=[e["factor_code"] for e in RECONCILIATION_MANIFEST]
        )
        versions.update(estado="borrador")
        versions.delete()
        ensure_system_environmental_catalog()
        self.assertEqual(
            FactorAmbiental.objects.filter(
                codigo__in=[e["factor_code"] for e in RECONCILIATION_MANIFEST]
            ).count(),
            7,
        )
        self.assertEqual(
            VersionFactorAmbiental.objects.filter(
                factor__codigo__in=[e["factor_code"] for e in RECONCILIATION_MANIFEST]
            ).count(),
            0,
        )
        with self.assertRaises(Exception):
            call_command("import_huellachile_factors", stdout=StringIO())
