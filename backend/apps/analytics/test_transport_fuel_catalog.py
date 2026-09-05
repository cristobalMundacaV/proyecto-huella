from datetime import date, datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from .models import (
    ActividadOperacional,
    ActivoOperacional,
    CalculoAmbiental,
    FactorAmbiental,
    FuenteDatos,
    MetodologiaAmbiental,
    Obra,
    Observacion,
    Organizacion,
    Vehiculo,
    VersionFactorAmbiental,
    ViajeOperacional,
)
from .services.calculation_v2 import calculate_activity
from .services.fuel_classification import (
    activity_fuel_classification,
    activity_fuel_type,
)
from .services.methodology_selector import select_methodology
from .services.system_environmental_catalog import (
    TRANSPORT_FUEL_METHODOLOGY_CODE,
    ensure_system_environmental_catalog,
)


class TransportFuelCatalogTests(TestCase):
    def setUp(self):
        ensure_system_environmental_catalog()
        factor = FactorAmbiental.objects.get(
            codigo="huellachile-combustion-movil-diesel"
        )
        if not factor.versiones.filter(
            estado=VersionFactorAmbiental.Estado.ACTIVO
        ).exists():
            VersionFactorAmbiental.objects.create(
                factor=factor,
                version=1,
                valor=Decimal("2.74"),
                fuente="Fixture gobernado",
                estado=VersionFactorAmbiental.Estado.ACTIVO,
            )
        self.organization = Organizacion.objects.create(nombre="Transporte catalogo")
        self.work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Edificio Parque Norte",
            fecha_inicio=date(2026, 1, 1),
        )
        self.source = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Guia de despacho / transporte",
            tipo=FuenteDatos.Tipo.MANUAL,
        )
        self.timestamp = timezone.make_aware(datetime(2026, 9, 11, 10, 0))
        self.sequence = 0

    def journey_activity(self, *, fuel="diesel", amount="12", unit="L"):
        self.sequence += 1
        suffix = str(self.sequence)
        activity = ActividadOperacional.objects.create(
            organizacion=self.organization,
            obra=self.work,
            codigo=f"transport-fuel-{suffix}",
            nombre="Viaje proveedor a obra",
            tipo=ActividadOperacional.Tipo.TRANSPORTE,
            timestamp_inicio=self.timestamp,
        )
        asset = ActivoOperacional.objects.create(
            organizacion=self.organization,
            codigo=f"truck-{suffix}",
            nombre=f"Camion {suffix}",
            tipo=ActivoOperacional.Tipo.VEHICULO,
        )
        vehicle = Vehiculo.objects.create(activo=asset, combustible=fuel)
        observation = None
        if amount is not None:
            observation = Observacion.objects.create(
                organizacion=self.organization,
                actividad=activity,
                fuente=self.source,
                concepto="combustible_consumido_l",
                valor_numerico=Decimal(amount),
                unidad=unit,
                timestamp_observacion=self.timestamp,
                estado=Observacion.Estado.VALIDADA,
            )
        ViajeOperacional.objects.create(
            organizacion=self.organization,
            actividad=activity,
            codigo=f"journey-{suffix}",
            vehiculo=vehicle,
            origen_nombre="Bodega proveedor",
            destino_nombre="Edificio Parque Norte",
            fecha_salida=self.timestamp,
            observacion_combustible=observation,
            estado=ViajeOperacional.Estado.COMPLETADO,
        )
        return activity

    def test_diesel_journey_selects_mobile_factor_and_calculates(self):
        activity = self.journey_activity()

        classification = activity_fuel_classification(activity)
        selection = select_methodology(activity)
        calculation, _ = calculate_activity(activity)

        self.assertEqual(classification["categoria"], "combustion_movil")
        self.assertEqual(classification["alcance"], 1)
        self.assertEqual(activity_fuel_type(activity), "diesel")
        self.assertEqual(
            selection["seleccion"]["version_metodologia"].metodologia.codigo,
            TRANSPORT_FUEL_METHODOLOGY_CODE,
        )
        self.assertEqual(
            calculation.version_factor.factor.codigo,
            "huellachile-combustion-movil-diesel",
        )
        self.assertEqual(calculation.resultado, Decimal("0.03288"))
        self.assertEqual(CalculoAmbiental.objects.filter(actividad=activity).count(), 1)
        snapshot = calculation.snapshot_tecnico
        self.assertEqual(
            snapshot["metodologia_codigo"], TRANSPORT_FUEL_METHODOLOGY_CODE
        )
        self.assertEqual(snapshot["factor_valor"], "2.7400000000")
        self.assertEqual(snapshot["inputs"][0]["valor_original"], "12.000000")
        self.assertEqual(snapshot["inputs"][0]["unidad_original"], "L")
        self.assertEqual(Decimal(snapshot["inputs"][0]["valor"]), Decimal("0.012"))
        self.assertEqual(snapshot["inputs"][0]["unidad"], "m3")

    def test_tenant_factor_precedes_huellachile(self):
        factor = FactorAmbiental.objects.create(
            organizacion=self.organization,
            codigo="tenant-mobile-diesel",
            nombre="Factor movil diesel tenant",
            categoria="combustion_movil",
            unidad_entrada="m3",
            unidad_resultado="tCO2e",
            contexto={
                "alcance": 1,
                "categoria_huella": "combustion_movil",
                "combustible": "diesel",
            },
        )
        tenant_version = VersionFactorAmbiental.objects.create(
            factor=factor,
            version=1,
            valor=Decimal("3.00"),
            fuente="Tenant",
            contexto=factor.contexto,
            estado=VersionFactorAmbiental.Estado.ACTIVO,
        )
        activity = self.journey_activity()

        calculation, _ = calculate_activity(activity)

        self.assertEqual(calculation.version_factor_id, tenant_version.id)
        self.assertEqual(calculation.resultado, Decimal("0.036"))

    def test_missing_or_unknown_vehicle_fuel_is_not_calculable(self):
        for fuel, expected in (
            ("", "no informa combustible"),
            ("gasolina", "gasolina"),
        ):
            activity = self.journey_activity(fuel=fuel)
            selection = select_methodology(activity)
            self.assertIsNone(selection["seleccion"])
            reasons = " ".join(
                reason
                for candidate in selection["candidatos"]
                for reason in candidate["motivos"]
            ).lower()
            self.assertIn(expected, reasons)

    def test_missing_fuel_observation_reports_critical_variable(self):
        selection = select_methodology(self.journey_activity(amount=None))
        self.assertIsNone(selection["seleccion"])
        self.assertTrue(
            any(
                "falta la variable critica combustible_consumido_l" in reason.lower()
                for candidate in selection["candidatos"]
                for reason in candidate["motivos"]
            )
        )

    def test_transport_without_vehicle_requires_classification(self):
        activity = ActividadOperacional.objects.create(
            organizacion=self.organization,
            obra=self.work,
            codigo="transport-without-vehicle",
            nombre="Viaje sin vehiculo",
            tipo=ActividadOperacional.Tipo.TRANSPORTE,
            timestamp_inicio=self.timestamp,
        )
        Observacion.objects.create(
            organizacion=self.organization,
            actividad=activity,
            fuente=self.source,
            concepto="combustible_consumido_l",
            valor_numerico=Decimal("12"),
            unidad="L",
            timestamp_observacion=self.timestamp,
            estado=Observacion.Estado.VALIDADA,
        )

        selection = select_methodology(activity)

        self.assertIsNone(selection["seleccion"])
        self.assertTrue(
            any(
                "no tiene un vehiculo asociado" in reason.lower()
                for candidate in selection["candidatos"]
                for reason in candidate["motivos"]
            )
        )

    def test_transport_methodology_provisioning_is_idempotent(self):
        ensure_system_environmental_catalog()
        ensure_system_environmental_catalog()
        methodology = MetodologiaAmbiental.objects.get(
            organizacion__isnull=True,
            codigo=TRANSPORT_FUEL_METHODOLOGY_CODE,
        )
        self.assertEqual(methodology.versiones.count(), 1)
        self.assertEqual(methodology.versiones.get().formula.variables.count(), 1)
