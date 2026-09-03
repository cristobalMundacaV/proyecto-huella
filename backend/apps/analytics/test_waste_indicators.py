from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (
    ActividadOperacional,
    FuenteDatos,
    ImpactoAmbiental,
    IndicadorAmbiental,
    Obra,
    Observacion,
    Organizacion,
    RegistroFlujoAmbiental,
    UsuarioOrganizacion,
    ValorIndicador,
)
from .services.operational_indicators import calendar_month
from .services.waste_catalog import WASTE_INDICATOR_SERIES
from .services.waste_indicators import sync_waste_indicator_month


class WasteIndicatorTests(TestCase):
    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Residuos tenant")
        self.other_organization = Organizacion.objects.create(nombre="Otro tenant")
        self.work = Obra.objects.create(
            id=71,
            organizacion=self.organization,
            nombre="Edificio Parque Norte",
            fecha_inicio=date(2026, 1, 1),
        )
        self.other_work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Otra obra",
            fecha_inicio=date(2026, 1, 1),
        )
        self.foreign_work = Obra.objects.create(
            organizacion=self.other_organization,
            nombre="Obra tenant externo",
            fecha_inicio=date(2026, 1, 1),
        )
        self.sources = {
            organization.pk: FuenteDatos.objects.create(
                organizacion=organization, nombre=f"Retiro {organization.pk}"
            )
            for organization in (self.organization, self.other_organization)
        }
        self.timestamp = timezone.make_aware(datetime(2026, 9, 11, 12, 0))
        self.start, self.end = calendar_month(self.timestamp)
        self.sequence = 0

    def waste(
        self,
        work,
        value,
        unit,
        destination="reciclaje",
        classification="no_peligroso",
        waste_type="madera",
    ):
        self.sequence += 1
        activity = ActividadOperacional.objects.create(
            organizacion=work.organizacion,
            obra=work,
            codigo=f"waste-{work.pk}-{self.sequence}",
            nombre="Residuo",
            tipo=ActividadOperacional.Tipo.GESTION_RESIDUO,
            timestamp_inicio=self.timestamp,
        )
        record = RegistroFlujoAmbiental.objects.create(
            organizacion=work.organizacion,
            obra=work,
            actividad=activity,
            flujo=RegistroFlujoAmbiental.Flujo.RESIDUO,
            periodo_inicio=self.timestamp,
            granularidad=RegistroFlujoAmbiental.Granularidad.OBRA,
            clasificacion_residuo=classification,
            tipo_residuo=waste_type,
            destino_operacional=destination,
        )
        observation = Observacion.objects.create(
            organizacion=work.organizacion,
            actividad=activity,
            fuente=self.sources[work.organizacion_id],
            concepto="cantidad_residuo",
            valor_numerico=Decimal(value),
            unidad=unit,
            timestamp_observacion=self.timestamp,
            estado=Observacion.Estado.VALIDADA,
        )
        return record, observation

    def values(self, work=None):
        return {
            value.indicador.codigo: value
            for value in ValorIndicador.objects.filter(
                indicador__obra=work or self.work
            ).select_related("indicador")
        }

    def test_e2e_mass_generated_valued_and_rate_exclude_disposal(self):
        recycled, _ = self.waste(self.work, "1000", "kg", "reciclaje")
        disposed, _ = self.waste(self.work, "1500", "kg", "disposicion")

        results = sync_waste_indicator_month(self.work, self.start, self.end)
        values = self.values()

        self.assertEqual(set(results), {
            "masa_generada", "masa_valorizada", "tasa_valorizacion_masa"
        })
        self.assertEqual(values[WASTE_INDICATOR_SERIES["masa_generada"]["codigo"]].valor, Decimal("2500"))
        valued = values[WASTE_INDICATOR_SERIES["masa_valorizada"]["codigo"]]
        self.assertEqual(valued.valor, Decimal("1000"))
        self.assertEqual(
            valued.metadata["registros_valorizados_ids"], [recycled.id]
        )
        disposed_source = next(
            source for source in valued.metadata["fuentes"]
            if source["registro_id"] == disposed.id
        )
        self.assertFalse(disposed_source["incluido_en_serie"])
        self.assertEqual(values[WASTE_INDICATOR_SERIES["tasa_valorizacion_masa"]["codigo"]].valor, Decimal("40"))
        for value in values.values():
            self.assertEqual(value.indicador.tipo, IndicadorAmbiental.Tipo.OPERACIONAL)
            self.assertEqual(value.indicador.alcance, IndicadorAmbiental.Alcance.OBRA)
            self.assertEqual(value.indicador.organizacion, self.organization)
            self.assertEqual(value.indicador.obra, self.work)
        self.assertFalse(
            IndicadorAmbiental.objects.filter(
                obra=self.work,
                codigo=WASTE_INDICATOR_SERIES["volumen_generado"]["codigo"],
            ).exists()
        )
        self.assertFalse(ImpactoAmbiental.objects.exists())

        source = values[WASTE_INDICATOR_SERIES["masa_generada"]["codigo"]].metadata["fuentes"][0]
        self.assertEqual(source["unidad_original"], "kg")
        self.assertEqual(source["unidad_normalizada"], "kg")
        self.assertEqual(source["destino_operacional"], "reciclaje")
        self.assertEqual(source["clasificacion_residuo"], "no_peligroso")

    def test_tonnes_normalize_to_kg_and_dimensions_do_not_mix(self):
        _, tonnes = self.waste(self.work, "1", "t")
        self.waste(self.work, "1000", "kg")
        self.waste(self.work, "1000", "L")
        self.waste(self.work, "8", "kWh")

        sync_waste_indicator_month(self.work, self.start, self.end)
        values = self.values()

        mass = values[WASTE_INDICATOR_SERIES["masa_generada"]["codigo"]]
        volume = values[WASTE_INDICATOR_SERIES["volumen_generado"]["codigo"]]
        self.assertEqual(mass.valor, Decimal("2000"))
        self.assertEqual(volume.valor, Decimal("1"))
        converted = next(
            source for source in mass.metadata["fuentes"]
            if source["observacion_id"] == tonnes.id
        )
        self.assertEqual(converted["regla_conversion"], "t → kg")
        self.assertEqual(mass.metadata["cantidad_fuentes"], 2)
        self.assertEqual(volume.metadata["cantidad_fuentes"], 1)

    def test_work_and_tenant_are_isolated(self):
        self.waste(self.work, "1000", "kg")
        self.waste(self.other_work, "2000", "kg")
        self.waste(self.foreign_work, "3000", "kg")

        sync_waste_indicator_month(self.work, self.start, self.end)

        mass = self.values()[WASTE_INDICATOR_SERIES["masa_generada"]["codigo"]]
        self.assertEqual(mass.valor, Decimal("1000"))
        self.assertEqual(mass.metadata["cantidad_fuentes"], 1)
        self.assertFalse(self.other_work.indicadores_ambientales.exists())
        self.assertFalse(self.foreign_work.indicadores_ambientales.exists())

    def test_zero_mass_does_not_create_misleading_rate(self):
        self.waste(self.work, "0", "kg", "reciclaje")

        results = sync_waste_indicator_month(self.work, self.start, self.end)

        self.assertIn("masa_generada", results)
        self.assertIn("masa_valorizada", results)
        self.assertNotIn("tasa_valorizacion_masa", results)
        self.assertFalse(
            IndicadorAmbiental.objects.filter(
                obra=self.work,
                codigo=WASTE_INDICATOR_SERIES["tasa_valorizacion_masa"]["codigo"],
            ).exists()
        )

    def test_sync_is_idempotent_and_real_change_versions_values(self):
        self.waste(self.work, "1000", "kg", "reciclaje")
        first = sync_waste_indicator_month(self.work, self.start, self.end)
        same = sync_waste_indicator_month(self.work, self.start, self.end)

        self.assertTrue(all(created for _, created in first.values()))
        self.assertTrue(all(not created for _, created in same.values()))
        self.assertEqual(ValorIndicador.objects.count(), 3)

        self.waste(self.work, "500", "kg", "reciclaje")
        changed = sync_waste_indicator_month(self.work, self.start, self.end)

        self.assertTrue(all(created for _, created in changed.values()))
        self.assertEqual(ValorIndicador.objects.count(), 6)
        for value, _ in changed.values():
            self.assertEqual(value.version, 2)

    def test_command_backfills_existing_waste_records(self):
        self.waste(self.work, "1000", "kg", "reciclaje")
        self.waste(self.work, "1500", "kg", "disposicion")
        self.assertFalse(self.work.indicadores_ambientales.exists())

        call_command(
            "sync_indicators_v2",
            organization=str(self.organization.organizacion_id),
            obra=self.work.id,
            stdout=StringIO(),
        )

        values = self.values()
        self.assertEqual(values[WASTE_INDICATOR_SERIES["masa_generada"]["codigo"]].valor, Decimal("2500"))
        self.assertEqual(values[WASTE_INDICATOR_SERIES["masa_valorizada"]["codigo"]].valor, Decimal("1000"))
        self.assertEqual(values[WASTE_INDICATOR_SERIES["tasa_valorizacion_masa"]["codigo"]].valor, Decimal("40"))


class WasteIndicatorPatchTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("waste-editor", password="test-pass")
        self.organization = Organizacion.objects.create(nombre="Residuos editables")
        UsuarioOrganizacion.objects.create(
            user=self.user,
            organizacion=self.organization,
            rol=UsuarioOrganizacion.Rol.OPERADOR,
        )
        self.work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Edificio Parque Norte",
            fecha_inicio=date(2026, 1, 1),
        )
        self.source = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Registro de retiro",
        )
        self.timestamp = timezone.make_aware(datetime(2026, 9, 11, 12, 0))
        self.start, self.end = calendar_month(self.timestamp)
        self.client.force_login(self.user)
        self.sequence = 0

    def waste(self, value, destination):
        self.sequence += 1
        activity = ActividadOperacional.objects.create(
            organizacion=self.organization,
            obra=self.work,
            codigo=f"waste-edit-{self.sequence}",
            nombre="Residuo",
            tipo=ActividadOperacional.Tipo.GESTION_RESIDUO,
            timestamp_inicio=self.timestamp,
        )
        record = RegistroFlujoAmbiental.objects.create(
            organizacion=self.organization,
            obra=self.work,
            actividad=activity,
            flujo=RegistroFlujoAmbiental.Flujo.RESIDUO,
            periodo_inicio=self.timestamp,
            granularidad=RegistroFlujoAmbiental.Granularidad.OBRA,
            clasificacion_residuo="no_peligroso",
            tipo_residuo="madera",
            destino_operacional=destination,
        )
        Observacion.objects.create(
            organizacion=self.organization,
            actividad=activity,
            fuente=self.source,
            concepto="cantidad_residuo",
            valor_numerico=Decimal(value),
            unidad="kg",
            timestamp_observacion=self.timestamp,
            estado=Observacion.Estado.VALIDADA,
        )
        return record

    def url(self, record):
        return (
            f"/api/organizaciones/{self.organization.organizacion_id}/"
            f"flujos-ambientales/{record.id}/"
        )

    def latest(self, series_key, start=None):
        return ValorIndicador.objects.filter(
            indicador__obra=self.work,
            indicador__codigo=WASTE_INDICATOR_SERIES[series_key]["codigo"],
            periodo_inicio=start or self.start,
        ).order_by("-version").first()

    def test_patch_reconciles_destination_quantity_unit_and_both_months(self):
        edited = self.waste("1000", "reciclaje")
        self.waste("1500", "disposicion")
        sync_waste_indicator_month(self.work, self.start, self.end)

        response = self.client.patch(
            self.url(edited), {"destino_operacional": "disposicion"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.latest("masa_generada").valor, Decimal("2500"))
        self.assertEqual(self.latest("masa_valorizada").valor, Decimal("0"))
        self.assertEqual(self.latest("tasa_valorizacion_masa").valor, Decimal("0"))

        self.client.patch(
            self.url(edited), {"destino_operacional": "disposicion"}, format="json"
        )
        self.assertEqual(self.latest("masa_generada").version, 2)

        response = self.client.patch(
            self.url(edited),
            {"destino_operacional": "reciclaje", "valor_numerico": "2", "unidad": "t"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(edited.actividad.observaciones.count(), 1)
        self.assertEqual(self.latest("masa_generada").valor, Decimal("3500"))
        self.assertEqual(self.latest("masa_valorizada").valor, Decimal("2000"))

        october = timezone.make_aware(datetime(2026, 10, 2, 12, 0))
        october_start, _ = calendar_month(october)
        response = self.client.patch(
            self.url(edited), {"periodo_inicio": october.isoformat()}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.latest("masa_generada").valor, Decimal("1500"))
        self.assertEqual(self.latest("masa_valorizada").valor, Decimal("0"))
        self.assertEqual(self.latest("masa_generada", october_start).valor, Decimal("2000"))
        self.assertEqual(self.latest("masa_valorizada", october_start).valor, Decimal("2000"))

    def test_indicator_failure_keeps_patch_and_backfill_repairs(self):
        record = self.waste("1000", "reciclaje")
        sync_waste_indicator_month(self.work, self.start, self.end)

        with patch(
            "apps.analytics.views_sector_flows_v1.sync_waste_indicator_month",
            side_effect=RuntimeError("fallo controlado"),
        ):
            response = self.client.patch(
                self.url(record), {"destino_operacional": "disposicion"}, format="json"
            )

        self.assertEqual(response.status_code, 200, response.data)
        record.refresh_from_db()
        self.assertEqual(record.destino_operacional, "disposicion")
        self.assertEqual(self.latest("masa_valorizada").valor, Decimal("1000"))

        sync_waste_indicator_month(self.work, self.start, self.end)
        self.assertEqual(self.latest("masa_valorizada").valor, Decimal("0"))
        self.assertEqual(self.latest("tasa_valorizacion_masa").valor, Decimal("0"))
