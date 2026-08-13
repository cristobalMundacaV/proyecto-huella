from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import ConfiguracionOrganizacion, DatoACV, Organizacion, RegistroEmision, UsuarioOrganizacion
from .services.environmental_engine import calculate_environmental_metrics, calculate_partial_lca


class EnvironmentalEngineTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(organizacion_id="ENGINE_A", nombre="Engine A")
        self.other = Organizacion.objects.create(organizacion_id="ENGINE_B", nombre="Engine B")

    def record(self, org=None, **values):
        defaults = dict(
            organizacion=org or self.org, fecha=date(2026, 1, 10), fuente_emision="Electricidad",
            categoria="Energia", cantidad=Decimal("100"), unidad="kWh",
            factor_emision=Decimal("1"), estado_validacion=RegistroEmision.EstadoValidacion.VALIDADO,
            contabilizable=True,
        )
        defaults.update(values)
        return RegistroEmision.objects.create(**defaults)

    def test_duplicados_no_afectan_kpis_y_agregaciones_son_correctas(self):
        self.record()
        self.record(fuente_emision="Diesel", categoria="Transporte", cantidad=Decimal("50"), factor_emision=Decimal("2"))
        self.record(contabilizable=False, cantidad=Decimal("999"), factor_emision=Decimal("10"))
        self.record(estado_validacion=RegistroEmision.EstadoValidacion.PENDIENTE, cantidad=Decimal("500"))
        result = calculate_environmental_metrics(self.org)
        self.assertEqual(result["co2e_total_kg"], Decimal("200"))
        self.assertEqual(result["registros_contabilizados"], 2)
        self.assertEqual(result["por_categoria"]["Energia"], Decimal("100"))
        self.assertEqual(result["por_actividad"]["Diesel"], Decimal("100"))

    def test_tendencias_intensidad_linea_base_y_antes_despues(self):
        self.record(fecha=date(2026, 1, 10), cantidad=Decimal("100"))
        self.record(fecha=date(2026, 2, 10), cantidad=Decimal("80"))
        result = calculate_environmental_metrics(self.org, intensity_denominator=20, intensity_unit="m2")
        self.assertEqual(result["linea_base"], Decimal("100"))
        self.assertEqual(result["tendencia"]["variacion_pct"], Decimal("-20.00"))
        self.assertEqual(result["antes_despues"]["variacion_pct"], Decimal("-20.00"))
        self.assertEqual(result["intensidad"]["valor"], Decimal("9"))

    def test_comparacion_con_meta_y_cobertura(self):
        ConfiguracionOrganizacion.objects.create(organizacion=self.org, meta_emisiones_kg_co2e=Decimal("150"))
        self.record(cantidad=Decimal("100"))
        result = calculate_environmental_metrics(self.org)
        self.assertTrue(result["meta"]["cumple"])
        self.assertEqual(result["cobertura_datos_pct"], Decimal("100.00"))

    def test_acv_parcial_no_inventa_etapas_y_reporta_cobertura(self):
        DatoACV.objects.create(organizacion=self.org, material_producto="Acero", etapa=DatoACV.Etapa.MATERIA_PRIMA, valor=10, unidad="kgCO2e", fuente="EPD", calidad_dato="referencial")
        DatoACV.objects.create(organizacion=self.org, material_producto="Acero", etapa=DatoACV.Etapa.TRANSPORTE, valor=2, unidad="kgCO2e", fuente="Guia", calidad_dato="medido")
        result = calculate_partial_lca(self.org, material_producto="Acero")
        self.assertEqual(set(result["etapas"]), {"materia_prima", "transporte"})
        self.assertEqual(result["cobertura_etapas_pct"], Decimal("28.57"))
        self.assertFalse(result["completo"])
        self.assertIn("fabricacion", result["etapas_faltantes"])

    def test_aislamiento_multi_tenant_en_servicio_y_endpoint(self):
        self.record(cantidad=Decimal("25"))
        self.record(org=self.other, cantidad=Decimal("900"))
        self.assertEqual(calculate_environmental_metrics(self.org)["co2e_total_kg"], Decimal("25"))
        user = User.objects.create_user("engine-user", password="segura-123")
        UsuarioOrganizacion.objects.create(user=user, organizacion=self.org)
        client = APIClient()
        client.force_login(user)
        own = client.get(f"/api/organizaciones/{self.org.organizacion_id}/motor-ambiental/")
        foreign = client.get(f"/api/organizaciones/{self.other.organizacion_id}/motor-ambiental/")
        self.assertEqual(own.status_code, 200)
        self.assertEqual(Decimal(own.data["co2e_total_kg"]), Decimal("25"))
        self.assertEqual(foreign.status_code, 404)
