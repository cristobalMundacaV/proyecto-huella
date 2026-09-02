from datetime import date, datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from .models import (
    ActividadOperacional,
    FuenteDatos,
    ImpactoAmbiental,
    IndicadorAmbiental,
    LineaBaseAmbiental,
    Obra,
    Observacion,
    Organizacion,
    ValorIndicador,
)
from .services.operational_indicators import (
    calendar_month,
    sync_operational_indicator_month,
    sync_operational_indicators_for_observation,
)


class OperationalWaterIndicatorTests(TestCase):
    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Indicadores agua")
        self.other_organization = Organizacion.objects.create(nombre="Otro tenant agua")
        self.work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Obra 71",
            fecha_inicio=date(2026, 1, 1),
        )
        self.other_work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Otra obra",
            fecha_inicio=date(2026, 1, 1),
        )
        self.foreign_work = Obra.objects.create(
            organizacion=self.other_organization,
            nombre="Obra otro tenant",
            fecha_inicio=date(2026, 1, 1),
        )
        self.sources = {
            organization.id: FuenteDatos.objects.create(
                organizacion=organization, nombre=f"Medidor {organization.id}"
            )
            for organization in (self.organization, self.other_organization)
        }
        self.timestamp = timezone.make_aware(datetime(2026, 9, 11, 10, 0))

    def observation(self, work, code, value, unit="m3", concept="consumo_agua"):
        activity = ActividadOperacional.objects.create(
            organizacion=work.organizacion,
            obra=work,
            codigo=code,
            nombre=code,
            tipo=ActividadOperacional.Tipo.CONSUMO_AGUA,
            timestamp_inicio=self.timestamp,
        )
        return Observacion.objects.create(
            organizacion=work.organizacion,
            actividad=activity,
            fuente=self.sources[work.organizacion_id],
            concepto=concept,
            valor_numerico=Decimal(value),
            unidad=unit,
            timestamp_observacion=self.timestamp,
            estado=Observacion.Estado.VALIDADA,
        )

    def test_water_creates_operational_indicator_with_traceable_month_value(self):
        observation = self.observation(self.work, "water-25", "25")

        value, created = sync_operational_indicators_for_observation(observation)

        self.assertTrue(created)
        indicator = value.indicador
        self.assertEqual(indicator.codigo, "consumo-agua")
        self.assertEqual(indicator.nombre, "Consumo de agua")
        self.assertEqual(indicator.tipo, IndicadorAmbiental.Tipo.OPERACIONAL)
        self.assertEqual(indicator.alcance, IndicadorAmbiental.Alcance.OBRA)
        self.assertEqual(indicator.unidad, "m3")
        self.assertEqual(indicator.origen_numerador, "consumo_agua")
        self.assertEqual(value.valor, Decimal("25"))
        self.assertEqual(value.periodo_inicio, date(2026, 9, 1))
        self.assertEqual(value.periodo_fin, date(2026, 9, 30))
        self.assertEqual(value.metadata["obra_id"], self.work.id)
        self.assertEqual(value.metadata["concepto"], "consumo_agua")
        self.assertEqual(value.metadata["unidad_agregada"], "m3")
        self.assertEqual(value.metadata["observaciones_fuente_ids"], [observation.id])
        self.assertEqual(value.metadata["actividades_fuente_ids"], [observation.actividad_id])
        self.assertEqual(value.metadata["cantidad_fuentes"], 1)
        self.assertFalse(LineaBaseAmbiental.objects.exists())
        self.assertFalse(ImpactoAmbiental.objects.exists())

    def test_liters_normalize_and_new_source_versions_without_duplicate_sync(self):
        first = self.observation(self.work, "water-m3", "25")
        initial, _ = sync_operational_indicators_for_observation(first)
        same, created = sync_operational_indicators_for_observation(first)
        self.assertFalse(created)
        self.assertEqual(same.id, initial.id)
        self.assertEqual(same.version, 1)

        liters = self.observation(self.work, "water-liters", "1000", "L")
        updated, created = sync_operational_indicators_for_observation(liters)

        self.assertTrue(created)
        self.assertEqual(updated.version, 2)
        self.assertEqual(updated.valor, Decimal("26"))
        converted = next(
            source
            for source in updated.metadata["fuentes"]
            if source["observacion_id"] == liters.id
        )
        self.assertEqual(converted["valor_original"], "1000.000000")
        self.assertEqual(converted["unidad_original"], "L")
        self.assertEqual(Decimal(converted["valor_normalizado"]), Decimal("1"))
        self.assertEqual(converted["regla_conversion"], "L → m3")

    def test_concept_work_and_tenant_are_isolated(self):
        water = self.observation(self.work, "water-own", "25")
        self.observation(self.work, "other-concept", "900", concept="nivel_estanque")
        self.observation(self.other_work, "water-other-work", "40")
        self.observation(self.foreign_work, "water-foreign", "60")

        value, _ = sync_operational_indicators_for_observation(water)

        self.assertEqual(value.valor, Decimal("25"))
        self.assertEqual(value.metadata["cantidad_fuentes"], 1)

    def test_effective_correction_creates_version_and_keeps_history(self):
        observation = self.observation(self.work, "water-corrected", "25")
        first, _ = sync_operational_indicators_for_observation(observation)
        observation.valor_numerico = Decimal("30")
        observation.save(update_fields=["valor_numerico", "updated_at"])

        second, created = sync_operational_indicators_for_observation(observation)

        self.assertTrue(created)
        self.assertEqual(first.version, 1)
        self.assertEqual(first.valor, Decimal("25"))
        self.assertEqual(second.version, 2)
        self.assertEqual(second.valor, Decimal("30"))
        self.assertEqual(ValorIndicador.objects.count(), 2)

    def test_existing_ghg_indicator_remains_untouched(self):
        gei = IndicadorAmbiental.objects.create(
            organizacion=self.organization,
            obra=self.work,
            codigo="emisiones-gei-generadas",
            nombre="Emisiones GEI generadas",
            tipo=IndicadorAmbiental.Tipo.ABSOLUTO,
            alcance=IndicadorAmbiental.Alcance.OBRA,
            unidad="tCO2e",
            origen_numerador="impactos_gei_generados",
        )
        observation = self.observation(self.work, "water-with-gei", "25")

        sync_operational_indicators_for_observation(observation)

        gei.refresh_from_db()
        self.assertEqual(gei.valores.count(), 0)
        self.assertTrue(
            IndicadorAmbiental.objects.filter(
                obra=self.work, codigo="consumo-agua"
            ).exists()
        )

    def test_explicit_month_sync_is_idempotent(self):
        self.observation(self.work, "water-sync", "25")
        start, end = calendar_month(self.timestamp)
        first, _ = sync_operational_indicator_month(
            self.work, "consumo_agua", start, end
        )
        second, created = sync_operational_indicator_month(
            self.work, "consumo_agua", start, end
        )
        self.assertFalse(created)
        self.assertEqual(first.id, second.id)
