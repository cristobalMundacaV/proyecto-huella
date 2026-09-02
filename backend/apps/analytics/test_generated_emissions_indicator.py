from datetime import date, datetime
from decimal import Decimal
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .models import (
    ActividadOperacional,
    CalculoAmbiental,
    FuenteDatos,
    ImpactoAmbiental,
    IndicadorAmbiental,
    Obra,
    Observacion,
    Organizacion,
    RegistroFlujoAmbiental,
    ValorIndicador,
)
from .services.calculation_v2 import calculate_activity, recalculate
from .services.generated_emissions_indicator import (
    INDICATOR_CODE,
    ensure_generated_emissions_indicator,
    sync_generated_emissions_month,
)


class GeneratedEmissionsIndicatorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("bootstrap_calculation_v2", stdout=StringIO())

    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Constructora KPI")
        self.other_organization = Organizacion.objects.create(nombre="Otro tenant KPI")
        self.work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Obra KPI",
            fecha_inicio=date(2026, 1, 1),
        )
        self.other_work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Otra obra KPI",
            fecha_inicio=date(2026, 1, 1),
        )
        self.foreign_work = Obra.objects.create(
            organizacion=self.other_organization,
            nombre="Obra tenant ajeno",
            fecha_inicio=date(2026, 1, 1),
        )
        self.sources = {
            self.organization.id: FuenteDatos.objects.create(
                organizacion=self.organization, nombre="Vale KPI"
            ),
            self.other_organization.id: FuenteDatos.objects.create(
                organizacion=self.other_organization, nombre="Vale KPI ajeno"
            ),
        }
        self.timestamp = timezone.make_aware(datetime(2026, 9, 11, 10, 0))

    def create_fuel_activity(self, work, code, value="250"):
        activity = ActividadOperacional.objects.create(
            organizacion=work.organizacion,
            obra=work,
            codigo=code,
            nombre=code,
            tipo=ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE_ESTACIONARIO,
            timestamp_inicio=self.timestamp,
        )
        RegistroFlujoAmbiental.objects.create(
            organizacion=work.organizacion,
            actividad=activity,
            obra=work,
            flujo=RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO,
            granularidad=RegistroFlujoAmbiental.Granularidad.OBRA,
            periodo_inicio=self.timestamp,
            tipo_recurso="diesel",
            destino_operacional=RegistroFlujoAmbiental.DestinoOperacional.GENERADOR,
        )
        observation = Observacion.objects.create(
            organizacion=work.organizacion,
            actividad=activity,
            fuente=self.sources[work.organizacion_id],
            concepto="combustible_consumido",
            valor_numerico=value,
            unidad="L",
            timestamp_observacion=self.timestamp,
            estado=Observacion.Estado.VALIDADA,
        )
        calculation, _ = calculate_activity(activity)
        return activity, observation, calculation

    def current_value(self, work=None):
        work = work or self.work
        return ValorIndicador.objects.filter(
            indicador__obra=work,
            indicador__codigo=INDICATOR_CODE,
        ).order_by("-version").first()

    def test_two_activities_create_monthly_indicator_and_traceable_sum(self):
        first = self.create_fuel_activity(self.work, "fuel-770")[2]
        second = self.create_fuel_activity(self.work, "fuel-771")[2]

        indicator = IndicadorAmbiental.objects.get(
            organizacion=self.organization, obra=self.work, codigo=INDICATOR_CODE
        )
        value = self.current_value()

        self.assertEqual(indicator.nombre, "Emisiones GEI generadas")
        self.assertEqual(indicator.tipo, IndicadorAmbiental.Tipo.ABSOLUTO)
        self.assertEqual(indicator.unidad, "tCO2e")
        self.assertEqual(value.valor, Decimal("1.3550"))
        self.assertEqual(str(value.periodo_inicio), "2026-09-01")
        self.assertEqual(str(value.periodo_fin), "2026-09-30")
        self.assertEqual(value.metadata["cantidad_fuentes"], 2)
        self.assertEqual(
            set(value.metadata["calculos_fuente_ids"]), {first.id, second.id}
        )
        self.assertEqual(ImpactoAmbiental.objects.count(), 2)

    def test_sync_and_command_are_idempotent_without_source_changes(self):
        self.create_fuel_activity(self.work, "fuel-idempotent")
        before = ValorIndicador.objects.count()

        value, created = sync_generated_emissions_month(
            self.work, self.timestamp.date().replace(day=1), self.timestamp.date().replace(day=30)
        )
        call_command(
            "sync_indicators_v2",
            organization=self.organization.organizacion_id,
            obra=self.work.id,
            stdout=StringIO(),
        )

        self.assertFalse(created)
        self.assertEqual(value.version, 1)
        self.assertEqual(ValorIndicador.objects.count(), before)

    def test_new_activity_and_recalculation_create_versions_without_double_counting(self):
        activity, observation, first = self.create_fuel_activity(
            self.work, "fuel-recalculation", "250"
        )
        self.create_fuel_activity(self.work, "fuel-new", "250")
        self.assertEqual(self.current_value().valor, Decimal("1.3550"))

        observation.valor_numerico = Decimal("300")
        observation.save()
        replacement, _ = recalculate(first, "Lectura corregida")

        current = self.current_value()
        self.assertEqual(current.valor, Decimal("1.4905"))
        self.assertEqual(current.metadata["cantidad_fuentes"], 2)
        self.assertIn(replacement.id, current.metadata["calculos_fuente_ids"])
        self.assertNotIn(first.id, current.metadata["calculos_fuente_ids"])
        self.assertEqual(activity.calculos_ambientales.count(), 2)
        self.assertEqual(activity.impactos_ambientales.count(), 2)

        calculate_activity(activity)
        self.assertEqual(self.current_value().valor, Decimal("1.4905"))
        self.assertEqual(activity.calculos_ambientales.count(), 3)
        self.assertEqual(activity.impactos_ambientales.count(), 3)

    def test_only_generated_tco2e_latest_impacts_contribute(self):
        reduction_activity, _, _ = self.create_fuel_activity(
            self.work, "fuel-reduction"
        )
        unit_activity, _, _ = self.create_fuel_activity(self.work, "fuel-unit")
        ImpactoAmbiental.objects.filter(actividad=reduction_activity).update(
            tipo=ImpactoAmbiental.Tipo.REDUCCION
        )
        ImpactoAmbiental.objects.filter(actividad=unit_activity).update(unidad="kgCO2e")

        value, _ = sync_generated_emissions_month(
            self.work, self.timestamp.date().replace(day=1), self.timestamp.date().replace(day=30)
        )

        self.assertEqual(value.valor, Decimal("0"))
        self.assertEqual(value.metadata["cantidad_fuentes"], 0)

    def test_work_and_tenant_isolation(self):
        self.create_fuel_activity(self.work, "fuel-own")
        self.create_fuel_activity(self.other_work, "fuel-other-work")
        self.create_fuel_activity(self.foreign_work, "fuel-foreign")

        own = self.current_value(self.work)
        other = self.current_value(self.other_work)
        foreign = self.current_value(self.foreign_work)

        self.assertEqual(own.valor, Decimal("0.6775"))
        self.assertEqual(other.valor, Decimal("0.6775"))
        self.assertEqual(foreign.valor, Decimal("0.6775"))
        self.assertNotEqual(own.indicador_id, other.indicador_id)
        self.assertNotEqual(own.indicador.organizacion_id, foreign.indicador.organizacion_id)

    def test_incompatible_existing_indicator_is_not_overwritten(self):
        indicator = IndicadorAmbiental.objects.create(
            organizacion=self.organization,
            obra=self.work,
            codigo=INDICATOR_CODE,
            nombre="Configuracion privada",
            alcance=IndicadorAmbiental.Alcance.OBRA,
            tipo=IndicadorAmbiental.Tipo.ABSOLUTO,
            unidad="kgCO2e",
            origen_numerador="otro_origen",
            direccion_deseable=IndicadorAmbiental.DireccionDeseable.MENOR,
        )

        with self.assertRaises(ValidationError):
            ensure_generated_emissions_indicator(self.work)

        indicator.refresh_from_db()
        self.assertEqual(indicator.unidad, "kgCO2e")
        self.assertEqual(indicator.origen_numerador, "otro_origen")
