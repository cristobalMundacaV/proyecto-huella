from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db.models.signals import post_migrate
from django.test import TestCase
from django.utils import timezone

from .management.commands.bootstrap_calculation_v2 import METHODOLOGY_CODE
from .models import (
    ActividadOperacional,
    FactorAmbiental,
    FuenteDatos,
    MetodologiaAmbiental,
    Obra,
    Observacion,
    Organizacion,
    RegistroFlujoAmbiental,
    VersionFactorAmbiental,
)
from .services.calculation_v2 import calculate_activity
from .services.system_environmental_catalog import (
    ENERGY_FACTOR_CODE,
    ENERGY_METHODOLOGY_CODE,
    SYSTEM_ENVIRONMENTAL_CATALOG_VERSION,
    TRANSPORT_FUEL_METHODOLOGY_CODE,
    MATERIAL_METHODOLOGY_CODE,
    ensure_system_environmental_catalog,
)


class SystemEnvironmentalCatalogTests(TestCase):
    def setUp(self):
        self.timestamp = timezone.make_aware(datetime(2026, 9, 11, 10, 0))

    def _tenant_context(self):
        organization = Organizacion.objects.create(nombre="Tenant posterior al catalogo")
        work = Obra.objects.create(
            organizacion=organization,
            nombre="Obra catalogo nativo",
            fecha_inicio=date(2026, 1, 1),
        )
        source = FuenteDatos.objects.create(
            organizacion=organization,
            nombre="Lectura manual",
            tipo=FuenteDatos.Tipo.MANUAL,
        )
        return organization, work, source

    def _activity(self, organization, work, source, *, energy):
        activity = ActividadOperacional.objects.create(
            organizacion=organization,
            obra=work,
            codigo="energy-native" if energy else "fuel-native",
            nombre="Actividad catalogo nativo",
            tipo=(
                ActividadOperacional.Tipo.CONSUMO_ENERGIA
                if energy
                else ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE_ESTACIONARIO
            ),
            timestamp_inicio=self.timestamp,
        )
        RegistroFlujoAmbiental.objects.create(
            organizacion=organization,
            actividad=activity,
            obra=work,
            flujo=(
                RegistroFlujoAmbiental.Flujo.ENERGIA
                if energy
                else RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO
            ),
            granularidad=RegistroFlujoAmbiental.Granularidad.OBRA,
            periodo_inicio=self.timestamp,
            tipo_recurso="red_electrica" if energy else "diesel",
            destino_operacional=(
                RegistroFlujoAmbiental.DestinoOperacional.SIN_CLASIFICAR
                if energy
                else RegistroFlujoAmbiental.DestinoOperacional.GENERADOR
            ),
        )
        Observacion.objects.create(
            organizacion=organization,
            actividad=activity,
            fuente=source,
            concepto="consumo_energia" if energy else "combustible_consumido",
            valor_numerico=Decimal("1000") if energy else Decimal("250"),
            unidad="kWh" if energy else "L",
            timestamp_observacion=self.timestamp,
            estado=Observacion.Estado.VALIDADA,
        )
        return activity

    def test_post_migrate_catalog_exists_without_any_tenant(self):
        self.assertFalse(Organizacion.objects.exists())
        self.assertEqual(
            FactorAmbiental.objects.filter(
                organizacion__isnull=True, codigo__startswith="huellachile-"
            ).count(),
            6,
        )
        self.assertTrue(
            FactorAmbiental.objects.filter(
                organizacion__isnull=True, codigo=ENERGY_FACTOR_CODE
            ).exists()
        )
        self.assertEqual(
            set(
                MetodologiaAmbiental.objects.filter(
                    organizacion__isnull=True,
                    codigo__in=[
                        METHODOLOGY_CODE,
                        ENERGY_METHODOLOGY_CODE,
                        TRANSPORT_FUEL_METHODOLOGY_CODE,
                        MATERIAL_METHODOLOGY_CODE,
                    ],
                ).values_list("codigo", flat=True)
            ),
            {
                METHODOLOGY_CODE,
                ENERGY_METHODOLOGY_CODE,
                TRANSPORT_FUEL_METHODOLOGY_CODE,
                MATERIAL_METHODOLOGY_CODE,
            },
        )

    def test_repeated_provisioning_has_zero_duplicates(self):
        before = (
            FactorAmbiental.objects.count(),
            VersionFactorAmbiental.objects.count(),
            MetodologiaAmbiental.objects.count(),
        )
        first = ensure_system_environmental_catalog()
        second = ensure_system_environmental_catalog()
        self.assertEqual(first["catalog_version"], SYSTEM_ENVIRONMENTAL_CATALOG_VERSION)
        self.assertEqual(first, second)
        self.assertEqual(
            before,
            (
                FactorAmbiental.objects.count(),
                VersionFactorAmbiental.objects.count(),
                MetodologiaAmbiental.objects.count(),
            ),
        )

    def test_tenant_created_later_calculates_fuel_and_energy_without_commands(self):
        organization, work, source = self._tenant_context()
        fuel, _ = calculate_activity(
            self._activity(organization, work, source, energy=False)
        )
        energy, _ = calculate_activity(
            self._activity(organization, work, source, energy=True)
        )
        self.assertEqual(fuel.resultado, Decimal("0.6775"))
        self.assertEqual(energy.resultado, Decimal("0.2466"))
        self.assertIsNone(fuel.version_factor.factor.organizacion_id)
        self.assertIsNone(energy.version_factor.factor.organizacion_id)

    def test_new_factor_version_does_not_change_historical_version_or_calculation(self):
        organization, work, source = self._tenant_context()
        calculation, _ = calculate_activity(
            self._activity(organization, work, source, energy=True)
        )
        historical = calculation.version_factor
        historical_snapshot = calculation.snapshot_tecnico.copy()
        factor = historical.factor

        future = VersionFactorAmbiental.objects.create(
            factor=factor,
            version=2,
            valor=Decimal("0.2000"),
            fuente="Release futuro controlado",
            referencia="Factor oficial SEN 2026",
            region="Chile",
            vigencia_desde=date(2027, 1, 1),
            contexto={**historical.contexto, "factor_year": 2026},
            estado=VersionFactorAmbiental.Estado.ACTIVO,
        )

        historical.refresh_from_db()
        calculation.refresh_from_db()
        self.assertEqual(historical.valor, Decimal("0.2466"))
        self.assertEqual(historical.contexto["factor_year"], 2025)
        self.assertEqual(calculation.version_factor_id, historical.id)
        self.assertEqual(calculation.snapshot_tecnico, historical_snapshot)
        self.assertNotEqual(future.id, historical.id)

    def test_incompatible_global_contract_is_not_overwritten(self):
        factor = FactorAmbiental.objects.get(codigo=ENERGY_FACTOR_CODE)
        original_version = factor.versiones.get(version=1)
        FactorAmbiental.objects.filter(pk=factor.pk).update(nombre="Contrato incompatible")

        with self.assertRaisesRegex(ImproperlyConfigured, "Contrato global incompatible"):
            ensure_system_environmental_catalog()

        factor.refresh_from_db()
        original_version.refresh_from_db()
        self.assertEqual(factor.nombre, "Contrato incompatible")
        self.assertEqual(original_version.valor, Decimal("0.2466"))
        self.assertEqual(factor.versiones.count(), 1)

    def test_commands_are_wrappers_over_catalog_services(self):
        result = {
            "catalog_version": SYSTEM_ENVIRONMENTAL_CATALOG_VERSION,
            "huellachile_factors": 6,
            "methodologies": 4,
        }
        with patch(
            "apps.analytics.management.commands.bootstrap_calculation_v2.ensure_system_environmental_catalog",
            return_value=result,
        ) as ensure:
            call_command("bootstrap_calculation_v2", stdout=StringIO())
        ensure.assert_called_once_with()
        with patch(
            "apps.analytics.management.commands.import_huellachile_factors.ensure_huellachile_factor_catalog",
            return_value=[object()] * 6,
        ) as ensure_fuels:
            call_command("import_huellachile_factors", stdout=StringIO())
        ensure_fuels.assert_called_once_with()

    def test_app_ready_only_connects_signal_and_performs_no_provisioning(self):
        config = apps.get_app_config("analytics")
        with patch.object(post_migrate, "connect") as connect, patch(
            "apps.analytics.signals.ensure_system_environmental_catalog"
        ) as ensure:
            config.ready()
        connect.assert_called_once()
        ensure.assert_not_called()

    def test_repeated_migrate_has_zero_duplicates(self):
        before = (
            FactorAmbiental.objects.count(),
            VersionFactorAmbiental.objects.count(),
            MetodologiaAmbiental.objects.count(),
        )
        call_command("migrate", interactive=False, verbosity=0)
        call_command("migrate", interactive=False, verbosity=0)
        self.assertEqual(
            before,
            (
                FactorAmbiental.objects.count(),
                VersionFactorAmbiental.objects.count(),
                MetodologiaAmbiental.objects.count(),
            ),
        )
