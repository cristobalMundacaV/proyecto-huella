from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.iot.models import DispositivoSensor, LecturaSensorV2

from .models import (ActividadOperacional, DiscrepanciaDato, FuenteDatos,
                     IndicadorAmbiental, LineaBaseAmbiental, Observacion,
                     Organizacion, PeriodoComparable, PoliticaConfianzaFuente,
                     UsuarioOrganizacion, ValorIndicador)
from .services.comparison_v2 import compare_values
from .services.indicators_v2 import build_baseline
from .services.observation_resolver import is_technical_duplicate, resolve_observation
from .services.quality_v2 import evaluate_observation_quality


class QualityIndicatorsV2Tests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("quality-v2", password="test-pass")
        self.org = Organizacion.objects.create(nombre="Calidad Uno")
        self.other = Organizacion.objects.create(nombre="Calidad Dos")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org)
        self.client.force_login(self.user)
        self.base = f"/api/organizaciones/{self.org.organizacion_id}"
        self.activity = ActividadOperacional.objects.create(
            organizacion=self.org, codigo="V-QUALITY", nombre="Viaje calidad", tipo="transporte", timestamp_inicio=timezone.now(),
        )
        self.manual = FuenteDatos.objects.create(organizacion=self.org, nombre="Manual", tipo="manual")
        self.gps = FuenteDatos.objects.create(organizacion=self.org, nombre="GPS", tipo="gps")
        self.document = FuenteDatos.objects.create(organizacion=self.org, nombre="Odometro", tipo="documento")

    def observation(self, source, value, concept="distancia_recorrida_km", timestamp=None):
        return Observacion.objects.create(
            organizacion=self.org, actividad=self.activity, fuente=source, concepto=concept,
            valor_numerico=value, unidad="km", timestamp_observacion=timestamp or timezone.now(), estado="validada",
        )

    def test_calidad_manual_es_declarativa_sin_score(self):
        evaluation = evaluate_observation_quality(self.observation(self.manual, "132"))
        self.assertEqual(evaluation.estado, "confiable_con_observaciones")
        self.assertEqual(evaluation.dimensiones["procedencia"], "declarativo")
        self.assertFalse(hasattr(evaluation, "score"))

    def test_sensor_operativo_y_fuera_servicio(self):
        source = FuenteDatos.objects.create(organizacion=self.org, nombre="Sensor", tipo="sensor")
        sensor = DispositivoSensor.objects.create(dispositivo_id="GPS-Q", nombre="GPS Q", organizacion=self.org, fuente_datos=source, estado="operativo")
        first = self.observation(source, "132")
        LecturaSensorV2.objects.create(sensor=sensor, actividad=self.activity, concepto=first.concepto, valor_numerico=first.valor_numerico, unidad="km", observacion=first)
        self.assertEqual(evaluate_observation_quality(first).estado, "confiable")
        sensor.estado = "fuera_servicio"; sensor.save()
        second = self.observation(source, "134", concept="otra_distancia")
        LecturaSensorV2.objects.create(sensor=sensor, actividad=self.activity, concepto=second.concepto, valor_numerico=second.valor_numerico, unidad="km", observacion=second)
        self.assertIn(evaluate_observation_quality(second).estado, {"requiere_revision", "no_confiable"})
        self.assertTrue(Observacion.objects.filter(pk=second.pk).exists())

    def test_discrepancia_conserva_observaciones_y_politica_prioriza_gps(self):
        gps = self.observation(self.gps, "132"); odometer = self.observation(self.document, "134")
        PoliticaConfianzaFuente.objects.create(organizacion=self.org, concepto=gps.concepto, tipo_fuente="gps", prioridad=1)
        PoliticaConfianzaFuente.objects.create(organizacion=self.org, concepto=gps.concepto, tipo_fuente="documento", prioridad=2)
        result = resolve_observation(self.activity, gps.concepto)
        self.assertEqual(result["observacion"], gps)
        self.assertEqual(result["discrepancia"].observaciones.count(), 2)
        self.assertEqual(result["discrepancia"].diferencia_absoluta, Decimal("2"))
        self.assertEqual(Observacion.objects.filter(pk__in=[gps.pk, odometer.pk]).count(), 2)

    def test_mismo_nivel_contradictorio_no_elige_arbitrariamente(self):
        first = self.observation(self.gps, "132"); self.observation(self.document, "134")
        for kind in ("gps", "documento"):
            PoliticaConfianzaFuente.objects.create(organizacion=self.org, concepto=first.concepto, tipo_fuente=kind, prioridad=1)
        result = resolve_observation(self.activity, first.concepto)
        self.assertEqual(result["estado"], "requiere_revision"); self.assertIsNone(result["observacion"])

    def test_deduplicacion_tecnica_conservadora_y_complementarias(self):
        moment = timezone.now(); first = self.observation(self.gps, "132", timestamp=moment); duplicate = self.observation(self.gps, "132", timestamp=moment)
        mass = self.observation(self.gps, "18", concept="masa_transportada_t", timestamp=moment)
        self.assertTrue(is_technical_duplicate(first, duplicate))
        self.assertFalse(is_technical_duplicate(first, mass))

    def test_indicadores_absoluto_e_intensidad_y_serie_historica(self):
        absolute = IndicadorAmbiental.objects.create(organizacion=self.org, codigo="emisiones", nombre="Emisiones", tipo="absoluto", unidad="kgCO2e", origen_numerador="impactos_ambientales", direccion_deseable="menor_es_mejor")
        intensity = IndicadorAmbiental.objects.create(organizacion=self.org, codigo="intensidad", nombre="Intensidad", tipo="intensidad", unidad="kgCO2e/t", origen_numerador="impactos_ambientales", origen_denominador="masa_transportada_t", direccion_deseable="menor_es_mejor")
        ValorIndicador.objects.create(indicador=absolute, periodo_inicio=date(2026,1,1), periodo_fin=date(2026,1,31), valor=1000, unidad=absolute.unidad, fuente_calculo="test")
        ValorIndicador.objects.create(indicador=absolute, periodo_inicio=date(2026,2,1), periodo_fin=date(2026,2,28), valor=1100, unidad=absolute.unidad, fuente_calculo="test")
        self.assertEqual(absolute.valores.count(), 2); self.assertEqual(intensity.tipo, "intensidad")

    def test_sin_historia_construye_linea_base_y_con_historia_la_crea(self):
        indicator = IndicadorAmbiental.objects.create(organizacion=self.org, codigo="base", nombre="Base", tipo="absoluto", unidad="kg", origen_numerador="impactos_ambientales")
        empty = build_baseline(indicator)
        self.assertEqual(empty.estado, "construyendo"); self.assertIsNone(empty.valor_base)
        ValorIndicador.objects.create(indicador=indicator, periodo_inicio=date(2026,1,1), periodo_fin=date(2026,1,31), valor=100, unidad="kg", fuente_calculo="test")
        built = build_baseline(indicator)
        self.assertEqual(built.cantidad_periodos, 1); self.assertEqual(built.valor_base, Decimal("100"))

    def test_periodo_comparable_porcentaje_y_direccion(self):
        indicator = IndicadorAmbiental.objects.create(organizacion=self.org, codigo="compare", nombre="Compare", tipo="absoluto", unidad="kg", origen_numerador="impactos_ambientales", direccion_deseable="menor_es_mejor")
        period = PeriodoComparable.objects.create(indicador=indicator, periodo_actual_inicio=date(2026,2,1), periodo_actual_fin=date(2026,2,28), periodo_referencia_inicio=date(2026,1,1), periodo_referencia_fin=date(2026,1,31), regla="periodo_anterior_equivalente", motivo_comparabilidad="Meses consecutivos equivalentes")
        result = compare_values(indicator, Decimal("90"), Decimal("100"), period)
        self.assertEqual(result["diferencia_porcentual"], Decimal("-10")); self.assertEqual(result["estado"], "mejor")

    def test_caso_obligatorio_absoluto_sube_intensidad_mejora(self):
        absolute = IndicadorAmbiental.objects.create(organizacion=self.org, codigo="abs-case", nombre="Absoluto", tipo="absoluto", unidad="kgCO2e", origen_numerador="impactos_ambientales", direccion_deseable="menor_es_mejor")
        intensity = IndicadorAmbiental.objects.create(organizacion=self.org, codigo="int-case", nombre="Intensidad", tipo="intensidad", unidad="kgCO2e/t", origen_numerador="impactos_ambientales", origen_denominador="masa_transportada_t", direccion_deseable="menor_es_mejor")
        absolute_result = compare_values(absolute, Decimal("1100"), Decimal("1000"))
        intensity_result = compare_values(intensity, Decimal("1100")/Decimal("130"), Decimal("10"))
        self.assertEqual(absolute_result["diferencia_porcentual"], Decimal("10.0")); self.assertEqual(absolute_result["estado"], "peor")
        self.assertAlmostEqual(float(intensity_result["diferencia_porcentual"]), -15.3846, places=4); self.assertEqual(intensity_result["estado"], "mejor")

    def test_historico_no_se_sobrescribe(self):
        indicator = IndicadorAmbiental.objects.create(organizacion=self.org, codigo="history", nombre="History", tipo="absoluto", unidad="kg", origen_numerador="impactos_ambientales")
        first = ValorIndicador.objects.create(indicador=indicator, periodo_inicio=date(2026,1,1), periodo_fin=date(2026,1,31), valor=100, unidad="kg", fuente_calculo="v1", version=1)
        second = ValorIndicador.objects.create(indicador=indicator, periodo_inicio=date(2026,1,1), periodo_fin=date(2026,1,31), valor=110, unidad="kg", fuente_calculo="v2", version=2)
        first.refresh_from_db(); self.assertEqual(first.valor, Decimal("100")); self.assertNotEqual(first.pk, second.pk)

    def test_api_y_aislamiento_tenant(self):
        own = IndicadorAmbiental.objects.create(organizacion=self.org, codigo="own", nombre="Own", tipo="absoluto", unidad="kg", origen_numerador="impactos_ambientales")
        foreign = IndicadorAmbiental.objects.create(organizacion=self.other, codigo="foreign", nombre="Foreign", tipo="absoluto", unidad="kg", origen_numerador="impactos_ambientales")
        response = self.client.get(f"{self.base}/indicadores/")
        self.assertEqual(response.status_code, 200); self.assertEqual([item["id"] for item in response.data], [own.id])
        self.assertEqual(self.client.get(f"{self.base}/indicadores/{foreign.id}/serie/").status_code, 404)
        self.assertEqual(self.client.get(f"{self.base}/resumen-ambiental-v2/").status_code, 200)

    def test_discrepancia_cross_tenant_no_puede_seleccionar_observacion(self):
        discrepancy = DiscrepanciaDato.objects.create(organizacion=self.org, actividad=self.activity, concepto="distancia_recorrida_km")
        foreign_source = FuenteDatos.objects.create(organizacion=self.other, nombre="Foreign")
        foreign = Observacion.objects.create(organizacion=self.other, fuente=foreign_source, concepto="distancia_recorrida_km", valor_numerico=1, unidad="km", timestamp_observacion=timezone.now())
        response = self.client.patch(f"{self.base}/discrepancias/{discrepancy.id}/", {"observacion_seleccionada": foreign.id}, format="json")
        self.assertEqual(response.status_code, 400)
