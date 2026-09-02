from datetime import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from .models import ActividadOperacional, Organizacion, RegistroFlujoAmbiental
from .services.evidence_taxonomy import evidence_types_for_domain
from .services.unit_conversion import UnitConversionError, convert_value
from .services.waste_catalog import (
    WASTE_INDICATOR_SERIES,
    construction_waste_types,
    is_valued_waste_destination,
)


class WasteCoreTests(TestCase):
    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Waste core")
        self.timestamp = timezone.make_aware(datetime(2026, 9, 11, 10, 0))

    def activity(self, code):
        return ActividadOperacional.objects.create(
            organizacion=self.organization,
            codigo=code,
            nombre=code,
            tipo=ActividadOperacional.Tipo.GESTION_RESIDUO,
            timestamp_inicio=self.timestamp,
        )

    def test_waste_classification_and_material_type_persist_separately(self):
        record = RegistroFlujoAmbiental.objects.create(
            organizacion=self.organization,
            actividad=self.activity("waste-new"),
            flujo=RegistroFlujoAmbiental.Flujo.RESIDUO,
            periodo_inicio=self.timestamp,
            clasificacion_residuo=RegistroFlujoAmbiental.ClasificacionResiduo.PELIGROSO,
            tipo_residuo="aceites_lubricantes",
            destino_operacional=RegistroFlujoAmbiental.DestinoOperacional.RECICLAJE,
        )

        record.refresh_from_db()
        self.assertEqual(record.clasificacion_residuo, "peligroso")
        self.assertEqual(record.tipo_residuo, "aceites_lubricantes")
        self.assertEqual(record.tipo_recurso, "")
        self.assertEqual(record.destino_operacional, "reciclaje")

    def test_historical_resource_classification_remains_readable_without_reinterpretation(self):
        record = RegistroFlujoAmbiental.objects.create(
            organizacion=self.organization,
            actividad=self.activity("waste-historic"),
            flujo=RegistroFlujoAmbiental.Flujo.RESIDUO,
            periodo_inicio=self.timestamp,
            tipo_recurso="no_peligroso",
            destino_operacional=RegistroFlujoAmbiental.DestinoOperacional.RESIDUO,
        )

        record.refresh_from_db()
        self.assertEqual(record.tipo_recurso, "no_peligroso")
        self.assertEqual(record.clasificacion_residuo, "")
        self.assertEqual(record.tipo_residuo, "")

    def test_waste_catalog_has_material_families_and_custom_option(self):
        values = {item["value"] for item in construction_waste_types()}
        self.assertTrue(
            {
                "hormigon_ceramicos",
                "madera",
                "metales",
                "plasticos",
                "yeso",
                "tierras_escombros",
                "aceites_lubricantes",
                "pinturas_solventes",
                "otro",
            }.issubset(values)
        )

    def test_physical_unit_families_are_strict(self):
        self.assertEqual(
            convert_value(Decimal("1000"), "kg", "t")["valor_normalizado"],
            Decimal("1"),
        )
        self.assertEqual(
            convert_value(Decimal("1"), "t", "kg")["valor_normalizado"],
            Decimal("1000"),
        )
        self.assertEqual(
            convert_value(Decimal("1000"), "L", "m3")["valor_normalizado"],
            Decimal("1"),
        )
        with self.assertRaises(UnitConversionError):
            convert_value(Decimal("1"), "kg", "L")

    def test_valuation_rule_is_explicit_and_excludes_pending_and_disposal(self):
        for destination in (
            "reutilizacion",
            "reciclaje",
            "valorizacion",
            "subproducto_reutilizado",
        ):
            self.assertTrue(is_valued_waste_destination(destination))
        self.assertFalse(is_valued_waste_destination("disposicion"))
        self.assertFalse(is_valued_waste_destination("residuo"))
        self.assertFalse(is_valued_waste_destination("sin_clasificar"))
        self.assertEqual(
            WASTE_INDICATOR_SERIES["tasa_valorizacion_masa"]["dimension"], "masa"
        )
        self.assertEqual(
            WASTE_INDICATOR_SERIES["volumen_generado"]["dimension"], "volumen"
        )

    def test_waste_evidence_taxonomy_remains_scoped(self):
        values = {item["value"] for item in evidence_types_for_domain("residuos")}
        self.assertEqual(
            values,
            {
                "ticket_pesaje",
                "manifiesto_retiro",
                "certificado_disposicion_final",
                "registro_retiro_residuos",
                "informe_gestor_residuos",
                "otro",
            },
        )
        self.assertNotIn("factura_agua", values)
        self.assertNotIn("boleta_electrica", values)
        self.assertNotIn("factura_combustible", values)
