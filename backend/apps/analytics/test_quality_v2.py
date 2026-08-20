from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.iot.models import DispositivoSensor, LecturaSensorV2

from .models import (
    ActividadOperacional,
    DiscrepanciaDato,
    EvaluacionCalidadDato,
    FuenteDatos,
    IndicadorAmbiental,
    LineaBaseAmbiental,
    Observacion,
    Organizacion,
    PeriodoComparable,
    PoliticaConfianzaFuente,
    UsuarioOrganizacion,
    ValorIndicador,
    Obra,
)
from .services.comparison_v2 import compare_values
from .services.indicators_v2 import build_baseline
from .services.observation_resolver import (
    _policy_priority,
    is_technical_duplicate,
    resolve_observation,
)
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
            organizacion=self.org,
            codigo="V-QUALITY",
            nombre="Viaje calidad",
            tipo="transporte",
            timestamp_inicio=timezone.now(),
        )
        self.manual = FuenteDatos.objects.create(
            organizacion=self.org, nombre="Manual", tipo="manual"
        )
        self.gps = FuenteDatos.objects.create(
            organizacion=self.org, nombre="GPS", tipo="gps"
        )
        self.document = FuenteDatos.objects.create(
            organizacion=self.org, nombre="Odometro", tipo="documento"
        )

    def observation(
        self, source, value, concept="distancia_recorrida_km", timestamp=None
    ):
        return Observacion.objects.create(
            organizacion=self.org,
            actividad=self.activity,
            fuente=source,
            concepto=concept,
            valor_numerico=value,
            unidad="km",
            timestamp_observacion=timestamp or timezone.now(),
            estado="validada",
        )

    def test_calidad_manual_es_declarativa_sin_score(self):
        evaluation = evaluate_observation_quality(self.observation(self.manual, "132"))
        self.assertEqual(evaluation.estado, "confiable_con_observaciones")
        self.assertEqual(evaluation.dimensiones["procedencia"], "declarativo")
        self.assertFalse(hasattr(evaluation, "score"))

    def test_sensor_operativo_y_fuera_servicio(self):
        source = FuenteDatos.objects.create(
            organizacion=self.org, nombre="Sensor", tipo="sensor"
        )
        sensor = DispositivoSensor.objects.create(
            dispositivo_id="GPS-Q",
            nombre="GPS Q",
            organizacion=self.org,
            fuente_datos=source,
            estado="operativo",
        )
        first = self.observation(source, "132")
        LecturaSensorV2.objects.create(
            sensor=sensor,
            actividad=self.activity,
            concepto=first.concepto,
            valor_numerico=first.valor_numerico,
            unidad="km",
            observacion=first,
        )
        self.assertEqual(evaluate_observation_quality(first).estado, "confiable")
        sensor.estado = "fuera_servicio"
        sensor.save()
        second = self.observation(source, "134", concept="otra_distancia")
        LecturaSensorV2.objects.create(
            sensor=sensor,
            actividad=self.activity,
            concepto=second.concepto,
            valor_numerico=second.valor_numerico,
            unidad="km",
            observacion=second,
        )
        self.assertIn(
            evaluate_observation_quality(second).estado,
            {"requiere_revision", "no_confiable"},
        )
        self.assertTrue(Observacion.objects.filter(pk=second.pk).exists())

    def test_discrepancia_conserva_observaciones_y_politica_prioriza_gps(self):
        gps = self.observation(self.gps, "132")
        odometer = self.observation(self.document, "134")
        PoliticaConfianzaFuente.objects.create(
            organizacion=self.org, concepto=gps.concepto, tipo_fuente="gps", prioridad=1
        )
        PoliticaConfianzaFuente.objects.create(
            organizacion=self.org,
            concepto=gps.concepto,
            tipo_fuente="documento",
            prioridad=2,
        )
        result = resolve_observation(self.activity, gps.concepto)
        self.assertEqual(result["observacion"], gps)
        self.assertEqual(result["discrepancia"].observaciones.count(), 2)
        self.assertEqual(result["discrepancia"].diferencia_absoluta, Decimal("2"))
        self.assertEqual(
            Observacion.objects.filter(pk__in=[gps.pk, odometer.pk]).count(), 2
        )

    def test_mismo_nivel_contradictorio_no_elige_arbitrariamente(self):
        first = self.observation(self.gps, "132")
        self.observation(self.document, "134")
        for kind in ("gps", "documento"):
            PoliticaConfianzaFuente.objects.create(
                organizacion=self.org,
                concepto=first.concepto,
                tipo_fuente=kind,
                prioridad=1,
            )
        result = resolve_observation(self.activity, first.concepto)
        self.assertEqual(result["estado"], "requiere_revision")
        self.assertIsNone(result["observacion"])

    def test_precedencia_tenant_global_y_aislamiento(self):
        PoliticaConfianzaFuente.objects.create(
            organizacion=None, concepto="distancia", tipo_fuente="gps", prioridad=5
        )
        PoliticaConfianzaFuente.objects.create(
            organizacion=self.org, concepto="distancia", tipo_fuente="gps", prioridad=1
        )
        PoliticaConfianzaFuente.objects.create(
            organizacion=self.other,
            concepto="combustible",
            tipo_fuente="gps",
            prioridad=2,
        )
        self.assertEqual(_policy_priority(self.org, "distancia", "gps"), 1)
        self.assertEqual(_policy_priority(self.other, "distancia", "gps"), 5)
        self.assertIsNone(_policy_priority(self.org, "combustible", "gps"))
        self.assertIsNone(_policy_priority(self.org, "inexistente", "gps"))

    def test_politica_tenant_resuelve_antes_que_global(self):
        gps = self.observation(self.gps, "132")
        odometer = self.observation(self.document, "134")
        PoliticaConfianzaFuente.objects.create(
            organizacion=None, concepto=gps.concepto, tipo_fuente="gps", prioridad=5
        )
        PoliticaConfianzaFuente.objects.create(
            organizacion=self.org, concepto=gps.concepto, tipo_fuente="gps", prioridad=1
        )
        PoliticaConfianzaFuente.objects.create(
            organizacion=self.org,
            concepto=gps.concepto,
            tipo_fuente="documento",
            prioridad=2,
        )
        result = resolve_observation(self.activity, gps.concepto)
        self.assertEqual(result["observacion"], gps)
        self.assertEqual(result["discrepancia"].observaciones.count(), 2)
        self.assertTrue(Observacion.objects.filter(pk=odometer.pk).exists())

    def test_lecturas_iguales_en_timestamps_distintos_no_son_duplicados(self):
        source = FuenteDatos.objects.create(
            organizacion=self.org, nombre="Sensor dedup", tipo="sensor"
        )
        sensor = DispositivoSensor.objects.create(
            dispositivo_id="DEDUP-1",
            nombre="Dedup",
            organizacion=self.org,
            fuente_datos=source,
        )
        first = self.observation(source, "12.5", timestamp=timezone.now())
        second = self.observation(
            source, "12.5", timestamp=first.timestamp_observacion + timedelta(hours=1)
        )
        LecturaSensorV2.objects.create(
            sensor=sensor,
            actividad=self.activity,
            timestamp=first.timestamp_observacion,
            concepto=first.concepto,
            valor_numerico=first.valor_numerico,
            unidad=first.unidad,
            observacion=first,
        )
        LecturaSensorV2.objects.create(
            sensor=sensor,
            actividad=self.activity,
            timestamp=second.timestamp_observacion,
            concepto=second.concepto,
            valor_numerico=second.valor_numerico,
            unidad=second.unidad,
            observacion=second,
        )
        self.assertFalse(is_technical_duplicate(first, second))

    def test_misma_referencia_tecnica_es_duplicado_y_complementarias_no(self):
        source = FuenteDatos.objects.create(
            organizacion=self.org, nombre="Sensor referencia", tipo="sensor"
        )
        sensor = DispositivoSensor.objects.create(
            dispositivo_id="DEDUP-2",
            nombre="Dedup ref",
            organizacion=self.org,
            fuente_datos=source,
        )
        moment = timezone.now()
        first = self.observation(source, "12.5", timestamp=moment)
        duplicate = self.observation(source, "12.5", timestamp=moment)
        for observation in (first, duplicate):
            LecturaSensorV2.objects.create(
                sensor=sensor,
                actividad=self.activity,
                timestamp=moment,
                concepto=observation.concepto,
                valor_numerico=observation.valor_numerico,
                unidad=observation.unidad,
                observacion=observation,
                metadata_tecnica={"message_id": "MSG-001"},
            )
        guide = self.observation(
            self.document, "18", concept="masa_transportada_t", timestamp=moment
        )
        self.assertTrue(is_technical_duplicate(first, duplicate))
        self.assertFalse(is_technical_duplicate(first, guide))

    def test_indicadores_absoluto_e_intensidad_y_serie_historica(self):
        absolute = IndicadorAmbiental.objects.create(
            organizacion=self.org,
            codigo="emisiones",
            nombre="Emisiones",
            tipo="absoluto",
            unidad="kgCO2e",
            origen_numerador="impactos_ambientales",
            direccion_deseable="menor_es_mejor",
        )
        intensity = IndicadorAmbiental.objects.create(
            organizacion=self.org,
            codigo="intensidad",
            nombre="Intensidad",
            tipo="intensidad",
            unidad="kgCO2e/t",
            origen_numerador="impactos_ambientales",
            origen_denominador="masa_transportada_t",
            direccion_deseable="menor_es_mejor",
        )
        ValorIndicador.objects.create(
            indicador=absolute,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 1, 31),
            valor=1000,
            unidad=absolute.unidad,
            fuente_calculo="test",
        )
        ValorIndicador.objects.create(
            indicador=absolute,
            periodo_inicio=date(2026, 2, 1),
            periodo_fin=date(2026, 2, 28),
            valor=1100,
            unidad=absolute.unidad,
            fuente_calculo="test",
        )
        self.assertEqual(absolute.valores.count(), 2)
        self.assertEqual(intensity.tipo, "intensidad")

    def test_sin_historia_construye_linea_base_y_con_historia_la_crea(self):
        indicator = IndicadorAmbiental.objects.create(
            organizacion=self.org,
            codigo="base",
            nombre="Base",
            tipo="absoluto",
            unidad="kg",
            origen_numerador="impactos_ambientales",
        )
        empty = build_baseline(indicator)
        self.assertEqual(empty.estado, "construyendo")
        self.assertIsNone(empty.valor_base)
        ValorIndicador.objects.create(
            indicador=indicator,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 1, 31),
            valor=100,
            unidad="kg",
            fuente_calculo="test",
        )
        built = build_baseline(indicator)
        self.assertEqual(built.cantidad_periodos, 1)
        self.assertEqual(built.valor_base, Decimal("100"))

    def test_periodo_comparable_porcentaje_y_direccion(self):
        indicator = IndicadorAmbiental.objects.create(
            organizacion=self.org,
            codigo="compare",
            nombre="Compare",
            tipo="absoluto",
            unidad="kg",
            origen_numerador="impactos_ambientales",
            direccion_deseable="menor_es_mejor",
        )
        period = PeriodoComparable.objects.create(
            indicador=indicator,
            periodo_actual_inicio=date(2026, 2, 1),
            periodo_actual_fin=date(2026, 2, 28),
            periodo_referencia_inicio=date(2026, 1, 1),
            periodo_referencia_fin=date(2026, 1, 31),
            regla="periodo_anterior_equivalente",
            motivo_comparabilidad="Meses consecutivos equivalentes",
        )
        result = compare_values(indicator, Decimal("90"), Decimal("100"), period)
        self.assertEqual(result["diferencia_porcentual"], Decimal("-10"))
        self.assertEqual(result["estado"], "mejor")

    def test_caso_obligatorio_absoluto_sube_intensidad_mejora(self):
        absolute = IndicadorAmbiental.objects.create(
            organizacion=self.org,
            codigo="abs-case",
            nombre="Absoluto",
            tipo="absoluto",
            unidad="kgCO2e",
            origen_numerador="impactos_ambientales",
            direccion_deseable="menor_es_mejor",
        )
        intensity = IndicadorAmbiental.objects.create(
            organizacion=self.org,
            codigo="int-case",
            nombre="Intensidad",
            tipo="intensidad",
            unidad="kgCO2e/t",
            origen_numerador="impactos_ambientales",
            origen_denominador="masa_transportada_t",
            direccion_deseable="menor_es_mejor",
        )
        absolute_result = compare_values(absolute, Decimal("1100"), Decimal("1000"))
        intensity_result = compare_values(
            intensity, Decimal("1100") / Decimal("130"), Decimal("10")
        )
        self.assertEqual(absolute_result["diferencia_porcentual"], Decimal("10.0"))
        self.assertEqual(absolute_result["estado"], "peor")
        self.assertAlmostEqual(
            float(intensity_result["diferencia_porcentual"]), -15.3846, places=4
        )
        self.assertEqual(intensity_result["estado"], "mejor")

    def test_historico_no_se_sobrescribe(self):
        indicator = IndicadorAmbiental.objects.create(
            organizacion=self.org,
            codigo="history",
            nombre="History",
            tipo="absoluto",
            unidad="kg",
            origen_numerador="impactos_ambientales",
        )
        first = ValorIndicador.objects.create(
            indicador=indicator,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 1, 31),
            valor=100,
            unidad="kg",
            fuente_calculo="v1",
            version=1,
        )
        second = ValorIndicador.objects.create(
            indicador=indicator,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 1, 31),
            valor=110,
            unidad="kg",
            fuente_calculo="v2",
            version=2,
        )
        first.refresh_from_db()
        self.assertEqual(first.valor, Decimal("100"))
        self.assertNotEqual(first.pk, second.pk)

    def test_api_y_aislamiento_tenant(self):
        own = IndicadorAmbiental.objects.create(
            organizacion=self.org,
            codigo="own",
            nombre="Own",
            tipo="absoluto",
            unidad="kg",
            origen_numerador="impactos_ambientales",
        )
        foreign = IndicadorAmbiental.objects.create(
            organizacion=self.other,
            codigo="foreign",
            nombre="Foreign",
            tipo="absoluto",
            unidad="kg",
            origen_numerador="impactos_ambientales",
        )
        response = self.client.get(f"{self.base}/indicadores/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [own.id])
        self.assertEqual(
            self.client.get(f"{self.base}/indicadores/{foreign.id}/serie/").status_code,
            404,
        )
        self.assertEqual(
            self.client.get(f"{self.base}/resumen-ambiental-v2/").status_code, 200
        )

    def test_discrepancia_cross_tenant_no_puede_seleccionar_observacion(self):
        discrepancy = DiscrepanciaDato.objects.create(
            organizacion=self.org,
            actividad=self.activity,
            concepto="distancia_recorrida_km",
        )
        foreign_source = FuenteDatos.objects.create(
            organizacion=self.other, nombre="Foreign"
        )
        foreign = Observacion.objects.create(
            organizacion=self.other,
            fuente=foreign_source,
            concepto="distancia_recorrida_km",
            valor_numerico=1,
            unidad="km",
            timestamp_observacion=timezone.now(),
        )
        response = self.client.patch(
            f"{self.base}/discrepancias/{discrepancy.id}/",
            {"observacion_seleccionada": foreign.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_calidad_y_discrepancias_filtran_por_obra(
        self,
    ):
        obra_a = Obra.objects.create(
            organizacion=self.org,
            nombre="Obra Calidad A",
            fecha_inicio=date(
                2026,
                8,
                1,
            ),
        )

        obra_b = Obra.objects.create(
            organizacion=self.org,
            nombre="Obra Calidad B",
            fecha_inicio=date(
                2026,
                8,
                1,
            ),
        )

        activity_a = ActividadOperacional.objects.create(
            organizacion=self.org,
            obra=obra_a,
            codigo="QA-A",
            nombre="Actividad A",
            tipo="consumo_agua",
            timestamp_inicio=timezone.now(),
        )

        activity_b = ActividadOperacional.objects.create(
            organizacion=self.org,
            obra=obra_b,
            codigo="QA-B",
            nombre="Actividad B",
            tipo="consumo_agua",
            timestamp_inicio=timezone.now(),
        )

        observation_a = Observacion.objects.create(
            organizacion=self.org,
            actividad=activity_a,
            fuente=self.manual,
            concepto="consumo_agua",
            valor_numerico=10,
            unidad="m3",
            timestamp_observacion=timezone.now(),
        )

        observation_b = Observacion.objects.create(
            organizacion=self.org,
            actividad=activity_b,
            fuente=self.manual,
            concepto="consumo_agua",
            valor_numerico=20,
            unidad="m3",
            timestamp_observacion=timezone.now(),
        )

        evaluate_observation_quality(observation_a)

        evaluate_observation_quality(observation_b)

        DiscrepanciaDato.objects.create(
            organizacion=self.org,
            actividad=activity_a,
            concepto="consumo_agua",
        )

        DiscrepanciaDato.objects.create(
            organizacion=self.org,
            actividad=activity_b,
            concepto="consumo_agua",
        )

        quality = self.client.get(
            f"{self.base}/calidad/observaciones/" f"?obra={obra_a.id}"
        )

        self.assertEqual(
            quality.status_code,
            200,
        )

        self.assertEqual(
            {row["observacion_detalle"]["obra"]["id"] for row in quality.data},
            {obra_a.id},
        )

        discrepancies = self.client.get(
            f"{self.base}/discrepancias/" f"?obra={obra_a.id}"
        )

        self.assertEqual(
            discrepancies.status_code,
            200,
        )

        self.assertEqual(
            {row["actividad_detalle"]["obra"] for row in discrepancies.data},
            {obra_a.id},
        )

    def test_discrepancia_solo_se_resuelve_con_observacion_involucrada(
        self,
    ):
        first = self.observation(
            self.gps,
            "132",
        )

        second = self.observation(
            self.document,
            "134",
        )

        unrelated = self.observation(
            self.manual,
            "999",
            concept="otro_concepto",
        )

        discrepancy = DiscrepanciaDato.objects.create(
            organizacion=self.org,
            actividad=self.activity,
            concepto="distancia_recorrida_km",
        )

        discrepancy.observaciones.add(
            first,
            second,
        )

        rejected = self.client.patch(
            f"{self.base}/discrepancias/" f"{discrepancy.id}/",
            {
                "estado": "resuelta",
                "observacion_seleccionada": unrelated.id,
                "resolucion": "Valor seleccionado.",
            },
            format="json",
        )

        self.assertEqual(
            rejected.status_code,
            400,
        )

        accepted = self.client.patch(
            f"{self.base}/discrepancias/" f"{discrepancy.id}/",
            {
                "estado": "resuelta",
                "observacion_seleccionada": first.id,
                "resolucion": "Se valida la lectura GPS según la política de fuente y la revisión realizada.",
            },
            format="json",
        )

        self.assertEqual(
            accepted.status_code,
            200,
        )


class QualityV2TenantAuthorizationTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user("quality-tenant-a", password="test-pass")
        self.user_b = User.objects.create_user("quality-tenant-b", password="test-pass")
        self.inactive_user = User.objects.create_user(
            "quality-inactive", password="test-pass"
        )
        self.superuser = User.objects.create_superuser(
            "quality-root", "root@example.com", "test-pass"
        )
        self.org_a = Organizacion.objects.create(nombre="Tenant quality A")
        self.org_b = Organizacion.objects.create(nombre="Tenant quality B")
        UsuarioOrganizacion.objects.create(
            user=self.user_a, organizacion=self.org_a, activo=True
        )
        UsuarioOrganizacion.objects.create(
            user=self.user_b, organizacion=self.org_b, activo=True
        )
        UsuarioOrganizacion.objects.create(
            user=self.inactive_user, organizacion=self.org_a, activo=False
        )
        self.base_a = f"/api/organizaciones/{self.org_a.organizacion_id}"
        self.base_b = f"/api/organizaciones/{self.org_b.organizacion_id}"

        self.activity_a = ActividadOperacional.objects.create(
            organizacion=self.org_a,
            codigo="QA-A",
            nombre="Quality A",
            tipo="transporte",
            timestamp_inicio=timezone.now(),
        )
        self.activity_b = ActividadOperacional.objects.create(
            organizacion=self.org_b,
            codigo="QA-B",
            nombre="Quality B",
            tipo="transporte",
            timestamp_inicio=timezone.now(),
        )
        source_a = FuenteDatos.objects.create(
            organizacion=self.org_a, nombre="Fuente A", tipo="manual"
        )
        source_b = FuenteDatos.objects.create(
            organizacion=self.org_b, nombre="Fuente B", tipo="manual"
        )
        self.observation_a = Observacion.objects.create(
            organizacion=self.org_a,
            actividad=self.activity_a,
            fuente=source_a,
            concepto="distancia",
            valor_numerico=10,
            unidad="km",
            timestamp_observacion=timezone.now(),
        )
        self.observation_b = Observacion.objects.create(
            organizacion=self.org_b,
            actividad=self.activity_b,
            fuente=source_b,
            concepto="distancia",
            valor_numerico=20,
            unidad="km",
            timestamp_observacion=timezone.now(),
        )
        self.discrepancy_a = DiscrepanciaDato.objects.create(
            organizacion=self.org_a,
            actividad=self.activity_a,
            concepto="distancia",
        )
        self.discrepancy_b = DiscrepanciaDato.objects.create(
            organizacion=self.org_b,
            actividad=self.activity_b,
            concepto="distancia",
        )
        self.indicator_a = IndicadorAmbiental.objects.create(
            organizacion=self.org_a,
            codigo="quality-a",
            nombre="Indicador A",
            tipo="absoluto",
            unidad="kg",
            origen_numerador="impactos_ambientales",
        )
        self.indicator_b = IndicadorAmbiental.objects.create(
            organizacion=self.org_b,
            codigo="quality-b",
            nombre="Indicador B",
            tipo="absoluto",
            unidad="kg",
            origen_numerador="impactos_ambientales",
        )
        for indicator, value in ((self.indicator_a, 10), (self.indicator_b, 20)):
            ValorIndicador.objects.create(
                indicador=indicator,
                periodo_inicio=date(2026, 1, 1),
                periodo_fin=date(2026, 1, 31),
                valor=value,
                unidad="kg",
                fuente_calculo="test",
            )
        self.client.force_login(self.user_a)

    def test_calidad_autorizada_y_ajena_no_muta(self):
        self.assertEqual(
            self.client.get(f"{self.base_a}/calidad/observaciones/").status_code, 200
        )
        EvaluacionCalidadDato.objects.filter(organizacion=self.org_b).delete()
        self.assertEqual(
            self.client.get(f"{self.base_b}/calidad/observaciones/").status_code, 404
        )
        self.assertFalse(
            EvaluacionCalidadDato.objects.filter(organizacion=self.org_b).exists()
        )

    def test_discrepancias_lectura_y_patch_respetan_tenant(self):
        self.assertEqual(
            self.client.get(f"{self.base_a}/discrepancias/").status_code,
            200,
        )

        self.discrepancy_a.observaciones.add(self.observation_a)

        response = self.client.patch(
            f"{self.base_a}/discrepancias/{self.discrepancy_a.id}/",
            {
                "estado": "resuelta",
                "observacion_seleccionada": self.observation_a.id,
                "resolucion": "Revisada",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.get(f"{self.base_b}/discrepancias/").status_code, 404
        )
        for url in (
            f"{self.base_b}/discrepancias/{self.discrepancy_b.id}/",
            f"{self.base_a}/discrepancias/{self.discrepancy_b.id}/",
        ):
            self.assertEqual(
                self.client.patch(
                    url, {"estado": "resuelta"}, format="json"
                ).status_code,
                404,
            )
        self.discrepancy_b.refresh_from_db()
        self.assertNotEqual(self.discrepancy_b.estado, "resuelta")

    def test_politicas_globales_requieren_organizacion_autorizada(self):
        policy = PoliticaConfianzaFuente.objects.create(
            organizacion=None,
            concepto="distancia",
            tipo_fuente="gps",
            prioridad=1,
        )
        response = self.client.get(f"{self.base_a}/politicas-fuente/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(policy.id, [item["id"] for item in response.data])
        self.assertEqual(
            self.client.get(f"{self.base_b}/politicas-fuente/").status_code, 404
        )

    def test_indicadores_series_y_comparacion_respetan_tenant(self):
        self.assertEqual(
            self.client.get(f"{self.base_a}/indicadores/").status_code, 200
        )
        self.assertEqual(
            self.client.get(f"{self.base_b}/indicadores/").status_code, 404
        )
        self.assertEqual(
            self.client.get(
                f"{self.base_a}/indicadores/{self.indicator_a.id}/serie/"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                f"{self.base_b}/indicadores/{self.indicator_b.id}/serie/"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                f"{self.base_a}/indicadores/{self.indicator_b.id}/serie/"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                f"{self.base_a}/indicadores/{self.indicator_a.id}/comparacion/"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                f"{self.base_b}/indicadores/{self.indicator_b.id}/comparacion/"
            ).status_code,
            404,
        )

    def test_lineas_base_y_resumen_respetan_tenant(self):
        self.assertEqual(
            self.client.get(f"{self.base_a}/lineas-base/").status_code, 200
        )
        self.assertEqual(
            self.client.get(f"{self.base_b}/lineas-base/").status_code, 404
        )
        self.assertEqual(
            self.client.post(
                f"{self.base_a}/lineas-base/",
                {"indicador": self.indicator_a.id},
                format="json",
            ).status_code,
            201,
        )
        self.assertEqual(
            self.client.post(
                f"{self.base_a}/lineas-base/",
                {"indicador": self.indicator_b.id},
                format="json",
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                f"{self.base_b}/lineas-base/",
                {"indicador": self.indicator_b.id},
                format="json",
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(f"{self.base_a}/resumen-ambiental-v2/").status_code, 200
        )
        self.assertEqual(
            self.client.get(f"{self.base_b}/resumen-ambiental-v2/").status_code, 404
        )

    def test_superuser_conserva_acceso_y_membresia_inactiva_no(self):
        self.client.force_login(self.superuser)
        self.assertEqual(
            self.client.get(f"{self.base_b}/indicadores/").status_code, 200
        )
        self.client.force_login(self.inactive_user)
        response = self.client.get(f"{self.base_a}/indicadores/")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Tenant quality A", response.content.decode())

    def test_usuario_no_autenticado_no_recibe_datos(self):
        self.client.logout()
        response = self.client.get(f"{self.base_a}/indicadores/")
        self.assertIn(response.status_code, {401, 403, 404})
        self.assertNotIn("Indicador A", response.content.decode())
