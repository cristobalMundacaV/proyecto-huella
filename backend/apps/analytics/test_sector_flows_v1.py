from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (
    ActividadOperacional,
    ActivoOperacional,
    CalculoAmbiental,
    CapacidadAmbiental,
    EtapaObra,
    EvidenciaObra,
    FactorAmbiental,
    FuenteDatos,
    ImpactoAmbiental,
    Maquinaria,
    Obra,
    Observacion,
    Organizacion,
    ProcesoOperacional,
    PuntoAmbientalOperacional,
    RegistroEmision,
    RegistroFlujoAmbiental,
    UnidadOperacional,
    UsuarioOrganizacion,
    ViajeOperacional,
)
from .services.context_gateway import ContextGateway
from .services.foundation import inicializar_capacidades_preset
from .services.onboarding import FLOW_CATALOG
from .services.sector_flows_v1 import sector_summary


class SectorFlowsV1Tests(APITestCase):
    TYPES = {
        "energia": "consumo_energia",
        "generacion_propia": "generacion_energia",
        "agua": "consumo_agua",
        "combustible_estacionario": "consumo_combustible_estacionario",
        "residuo": "gestion_residuo",
        "ruido": "monitoreo_ruido",
        "gestion_hidrica_suelo": "gestion_hidrica_suelo",
    }

    def setUp(self):
        self.user = User.objects.create_user("sector-v1", password="test-pass")
        self.org = Organizacion.objects.create(
            nombre="Sector Uno", preset="construccion"
        )
        self.other = Organizacion.objects.create(
            nombre="Sector Dos", preset="construccion"
        )
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org)
        self.client.force_login(self.user)
        self.base = f"/api/organizaciones/{self.org.organizacion_id}"
        self.manual = FuenteDatos.objects.create(
            organizacion=self.org, nombre="Manual", tipo="manual"
        )
        self.document = FuenteDatos.objects.create(
            organizacion=self.org, nombre="Factura", tipo="documento"
        )
        self.unit = UnidadOperacional.objects.create(
            organizacion=self.org, nombre="Instalacion", tipo="instalacion"
        )
        self.process = ProcesoOperacional.objects.create(
            organizacion=self.org, unidad=self.unit, nombre="Proceso A"
        )
        self.asset = ActivoOperacional.objects.create(
            organizacion=self.org,
            codigo="GEN-1",
            nombre="Generador",
            tipo="maquinaria",
            unidad_operacional=self.unit,
            proceso_operacional=self.process,
        )
        Maquinaria.objects.create(
            activo=self.asset, tipo_maquinaria="Generador", combustible="diesel"
        )
        self.stage = EtapaObra.objects.create(
            organizacion=self.org, nombre="Obra gruesa"
        )
        self.work = Obra.objects.create(
            organizacion=self.org,
            etapa_principal=self.stage,
            nombre="Obra A",
            fecha_inicio="2026-01-01",
        )
        self.sequence = 0

    def activity(self, flow):
        self.sequence += 1
        return ActividadOperacional.objects.create(
            organizacion=self.org,
            tipo=self.TYPES[flow],
            codigo=f"FL-{self.sequence}",
            nombre=f"{flow} {self.sequence}",
            timestamp_inicio=timezone.now(),
        )

    def record(self, flow, **kwargs):
        activity = kwargs.pop("actividad", None) or self.activity(flow)
        return RegistroFlujoAmbiental.objects.create(
            organizacion=self.org,
            actividad=activity,
            flujo=flow,
            periodo_inicio=timezone.now(),
            **kwargs,
        )

    def observation(
        self, record, concept, value=None, unit="", source=None, text="", evidence=None
    ):
        return Observacion.objects.create(
            organizacion=self.org,
            actividad=record.actividad,
            fuente=source or self.manual,
            concepto=concept,
            valor_numerico=value,
            valor_texto=text,
            unidad=unit,
            timestamp_observacion=timezone.now(),
            evidencia=evidence,
        )

    def test_energia_global_sin_submedicion_y_sin_distribucion(self):
        activity = self.activity("energia")
        response = self.client.post(
            f"{self.base}/flujos-ambientales/",
            {
                "actividad": activity.id,
                "flujo": "energia",
                "periodo_inicio": timezone.now().isoformat(),
                "granularidad": "organizacion",
                "concepto": "consumo_energia",
                "valor_numerico": "120",
                "unidad": "kWh",
                "fuente": self.document.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        record = RegistroFlujoAmbiental.objects.get()
        self.assertIsNone(record.proceso_id)
        indicator = sector_summary(self.org, flow="energia")["indicadores"][0]
        self.assertEqual(indicator["total"], Decimal("120"))
        self.assertIsNone(indicator["alcance"]["proceso_id"])

    def test_energia_discrepante_coexiste_y_no_se_suma_doble(self):
        record = self.record("energia")
        self.observation(record, "consumo_energia", 120, "kWh", self.document)
        self.observation(record, "consumo_energia", 118, "kWh", self.manual)
        item = sector_summary(self.org, flow="energia")["indicadores"][0]
        self.assertEqual(record.actividad.observaciones.count(), 2)
        self.assertEqual(item["registros_ambiguos"], 1)
        self.assertEqual(item["total"], 0)

    def test_generacion_es_separada_y_no_crea_reduccion(self):
        consumption = self.record("energia")
        generation = self.record("generacion_propia", tipo_recurso="solar_fotovoltaica")
        self.observation(consumption, "consumo_energia", 100, "kWh")
        self.observation(generation, "energia_generada", 40, "kWh")
        result = sector_summary(self.org)
        self.assertEqual(
            {row["flujo"] for row in result["indicadores"]},
            {"energia", "generacion_propia"},
        )
        self.assertIsNone(result["impacto_ambiental"])
        self.assertEqual(ImpactoAmbiental.objects.count(), 0)

    def test_generacion_autoconsumo_exportacion_conservan_concepto(self):
        record = self.record("generacion_propia")
        self.observation(record, "energia_generada", 50, "kWh")
        self.observation(record, "energia_autoconsumida", 30, "kWh")
        self.observation(record, "energia_exportada", 20, "kWh")
        self.assertEqual(
            {row["concepto"] for row in sector_summary(self.org)["indicadores"]},
            {"energia_generada", "energia_autoconsumida", "energia_exportada"},
        )

    def test_agua_fuentes_multiples_y_dato_cualitativo(self):
        record = self.record(
            "agua",
            granularidad="instalacion",
            unidad_operacional=self.unit,
            tipo_recurso="red_publica",
        )
        for source, value in ((self.document, 120), (self.manual, 118)):
            self.observation(record, "consumo_agua", value, "m3", source)
        self.observation(
            record, "uso_agua", text="Existe uso de agua", source=self.manual
        )
        self.assertEqual(record.actividad.observaciones.count(), 3)
        self.assertIsNone(
            record.actividad.observaciones.get(concepto="uso_agua").valor_numerico
        )
        self.assertEqual(
            sector_summary(self.org)["registros"][0]["alcance"]["granularidad"],
            "instalacion",
        )

    def test_combustible_estacionario_vincula_activo_y_no_viaje(self):
        record = self.record(
            "combustible_estacionario",
            granularidad="activo",
            activo=self.asset,
            proceso=self.process,
            tipo_recurso="diesel",
        )
        self.observation(record, "combustible_consumido", 42, "L")
        self.assertEqual(record.actividad.tipo, "consumo_combustible_estacionario")
        self.assertEqual(record.activo, self.asset)
        self.assertEqual(ViajeOperacional.objects.count(), 0)

    def test_residuo_destino_y_evidencia_trazables(self):
        evidence = EvidenciaObra.objects.create(
            organizacion=self.org,
            obra=self.work,
            nombre="Ticket",
            tipo_evidencia="ticket_pesaje",
            archivo=SimpleUploadedFile("ticket.txt", b"20 t"),
        )
        record = self.record(
            "residuo",
            granularidad="obra",
            obra=self.work,
            destino_operacional="reciclaje",
            proveedor_gestor="Gestor A",
        )
        self.observation(
            record, "cantidad_residuo", 20, "t", self.document, evidence=evidence
        )
        detail = sector_summary(self.org)["registros"][0]
        self.assertEqual(detail["destino_operacional"], "reciclaje")
        self.assertEqual(detail["mediciones"][0]["evidencia_id"], evidence.id)

    def test_destinos_residuo_permanecen_diferenciados_sin_impacto(self):
        destinations = {
            "residuo",
            "reutilizacion",
            "reciclaje",
            "valorizacion",
            "disposicion",
            "subproducto_reutilizado",
        }
        for destination in destinations:
            self.record("residuo", destino_operacional=destination)
        self.assertEqual(
            set(
                RegistroFlujoAmbiental.objects.values_list(
                    "destino_operacional", flat=True
                )
            ),
            destinations,
        )
        self.assertEqual(CalculoAmbiental.objects.count(), 0)
        self.assertEqual(ImpactoAmbiental.objects.count(), 0)

    def test_ruido_conserva_metrica_unidad_y_no_declara_cumplimiento(self):
        point = PuntoAmbientalOperacional.objects.create(
            organizacion=self.org,
            codigo="R-1",
            nombre="Receptor norte",
            tipo="punto_ruido",
            ubicacion="Deslinde norte",
        )
        record = self.record("ruido", granularidad="punto", punto=point, metrica="Leq")
        self.observation(record, "nivel_ruido", 73, "dB(A)")
        result = sector_summary(self.org, flow="ruido")
        self.assertEqual(result["indicadores"][0]["metrica"], "Leq")
        self.assertEqual(result["indicadores"][0]["unidad"], "dB(A)")
        self.assertIsNone(result["cumplimiento_normativo"])

    def test_ruido_separa_puntos(self):
        for index, value in enumerate((60, 73), 1):
            point = PuntoAmbientalOperacional.objects.create(
                organizacion=self.org,
                codigo=f"R-{index}",
                nombre=f"Punto {index}",
                tipo="punto_ruido",
            )
            record = self.record("ruido", granularidad="punto", punto=point)
            self.observation(record, "nivel_ruido", value, "dB")
        self.assertEqual(len(sector_summary(self.org, flow="ruido")["indicadores"]), 2)

    def test_hidrica_suelo_registra_superficie_drenaje_y_senales(self):
        point = PuntoAmbientalOperacional.objects.create(
            organizacion=self.org,
            codigo="D-1",
            nombre="Drenaje norte",
            tipo="punto_drenaje",
        )
        record = self.record("gestion_hidrica_suelo", granularidad="punto", punto=point)
        self.observation(record, "superficie_intervenida", 500, "m2")
        self.observation(record, "desborde", text="si")
        self.observation(record, "erosion_observada", text="presente")
        result = sector_summary(self.org, flow="gestion_hidrica_suelo")
        self.assertEqual(
            {row["tipo"] for row in result["senales"]},
            {"desborde", "erosion_observada"},
        )
        self.assertNotIn(
            "volumen_escorrentia", {row["concepto"] for row in result["indicadores"]}
        )

    def test_indicadores_separan_unidades_y_alcances(self):
        second_work = Obra.objects.create(
            organizacion=self.org,
            etapa_principal=self.stage,
            nombre="Obra B",
            fecha_inicio="2026-01-01",
        )
        for work, value, unit in (
            (self.work, 10, "kg"),
            (self.work, 3, "m3"),
            (second_work, 90, "kg"),
        ):
            record = self.record("residuo", granularidad="obra", obra=work)
            self.observation(record, "cantidad_residuo", value, unit)
        result = sector_summary(self.org, flow="residuo", work=self.work)
        self.assertEqual({row["unidad"] for row in result["indicadores"]}, {"kg", "m3"})
        self.assertEqual(
            {row["alcance"]["obra_id"] for row in result["indicadores"]}, {self.work.id}
        )

    def test_rechaza_referencias_cruzadas_entre_obras(self):
        second_work = Obra.objects.create(
            organizacion=self.org,
            etapa_principal=self.stage,
            nombre="Obra B",
            fecha_inicio="2026-01-01",
        )

        activity = ActividadOperacional.objects.create(
            organizacion=self.org,
            obra=self.work,
            tipo="consumo_agua",
            codigo="CROSS-WORK-ACTIVITY",
            nombre="Consumo agua Obra A",
            timestamp_inicio=timezone.now(),
        )

        foreign_point = PuntoAmbientalOperacional.objects.create(
            organizacion=self.org,
            obra=second_work,
            codigo="P-B",
            nombre="Punto Obra B",
            tipo="otro",
        )

        foreign_evidence = EvidenciaObra.objects.create(
            organizacion=self.org,
            obra=second_work,
            nombre="Evidencia Obra B",
            tipo_evidencia="otro",
            archivo=SimpleUploadedFile(
                "evidencia-b.txt",
                b"evidencia",
            ),
        )

        response = self.client.post(
            f"{self.base}/flujos-ambientales/",
            {
                "actividad": activity.id,
                "obra": self.work.id,
                "punto": foreign_point.id,
                "flujo": "agua",
                "periodo_inicio": timezone.now().isoformat(),
                "granularidad": "punto",
                "concepto": "consumo_agua",
                "valor_numerico": "15",
                "unidad": "m3",
                "fuente": self.manual.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "punto",
            response.data,
        )

        response = self.client.post(
            f"{self.base}/flujos-ambientales/",
            {
                "actividad": activity.id,
                "obra": self.work.id,
                "flujo": "agua",
                "periodo_inicio": timezone.now().isoformat(),
                "granularidad": "obra",
                "concepto": "consumo_agua",
                "valor_numerico": "15",
                "unidad": "m3",
                "fuente": self.manual.id,
                "evidencia": foreign_evidence.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "evidencia",
            response.data,
        )

        foreign_activity = ActividadOperacional.objects.create(
            organizacion=self.org,
            obra=second_work,
            tipo="consumo_agua",
            codigo="CROSS-WORK-ACTIVITY-B",
            nombre="Consumo agua Obra B",
            timestamp_inicio=timezone.now(),
        )

        response = self.client.post(
            f"{self.base}/flujos-ambientales/",
            {
                "actividad": foreign_activity.id,
                "obra": self.work.id,
                "flujo": "agua",
                "periodo_inicio": timezone.now().isoformat(),
                "granularidad": "obra",
                "concepto": "consumo_agua",
                "valor_numerico": "15",
                "unidad": "m3",
                "fuente": self.manual.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "actividad",
            response.data,
        )

    def test_cross_tenant_rechazado_en_dominio_y_api(self):
        foreign_asset = ActivoOperacional.objects.create(
            organizacion=self.other, codigo="X", nombre="X", tipo="medidor"
        )
        with self.assertRaises(ValidationError):
            PuntoAmbientalOperacional.objects.create(
                organizacion=self.org, codigo="BAD", nombre="Bad", activo=foreign_asset
            )
        activity = self.activity("energia")
        response = self.client.post(
            f"{self.base}/flujos-ambientales/",
            {
                "actividad": activity.id,
                "flujo": "energia",
                "periodo_inicio": timezone.now().isoformat(),
                "granularidad": "activo",
                "activo": foreign_asset.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_context_gateway_entrega_resumen_compacto(self):
        record = self.record("agua")
        self.observation(record, "consumo_agua", 12, "m3")
        package = ContextGateway().activity(record.actividad, self.org)[
            "flujo_ambiental"
        ]
        self.assertEqual(package["flujo"], "agua")
        self.assertEqual(len(package["mediciones"]), 1)
        self.assertNotIn("actividad", package)
        self.assertNotIn("queryset", package)

    def test_capacidades_ambientales_usan_catalogo_actual_del_onboarding(self):
        keys = {row.capacidad.clave for row in inicializar_capacidades_preset(self.org)}
        self.assertEqual(keys, set(FLOW_CATALOG))
        self.assertTrue({
            "maquinaria",
            "mantenimiento",
            "generacion_propia",
            "continuidad_operacional",
            "residuos",
            "gestion_hidrica_suelo",
        }.isdisjoint(keys))
        self.assertTrue(CapacidadAmbiental.objects.get(clave="ruido").activa)

    def test_registro_no_crea_metodologias_factores_ni_calculos(self):
        before = (
            FactorAmbiental.objects.count(),
            CalculoAmbiental.objects.count(),
            ImpactoAmbiental.objects.count(),
        )
        record = self.record("energia")
        self.observation(record, "consumo_energia", 10, "kWh")
        sector_summary(self.org)
        self.assertEqual(
            (
                FactorAmbiental.objects.count(),
                CalculoAmbiental.objects.count(),
                ImpactoAmbiental.objects.count(),
            ),
            before,
        )

    def test_legacy_registro_emision_sigue_funcionando(self):
        legacy = RegistroEmision.objects.create(
            organizacion=self.org,
            categoria="Energia",
            fuente_emision="Electricidad legacy",
            cantidad=10,
            unidad="kWh",
            factor_emision=Decimal("0.2"),
        )
        self.assertEqual(legacy.emisiones_kg_co2e, Decimal("2"))
        self.assertEqual(RegistroFlujoAmbiental.objects.count(), 0)

    def test_ruido_compatible_no_suma_y_conserva_extremos(self):
        point = PuntoAmbientalOperacional.objects.create(
            organizacion=self.org,
            codigo="R-C",
            nombre="Punto comparable",
            tipo="punto_ruido",
        )
        for value in (70, 75):
            record = self.record(
                "ruido", granularidad="punto", punto=point, metrica="Leq"
            )
            self.observation(record, "nivel_ruido", value, "dB(A)")
        item = sector_summary(self.org, flow="ruido")["indicadores"][0]
        self.assertIsNone(item["total"])
        self.assertEqual(item["mediciones"], 2)
        self.assertEqual(item["minimo"], Decimal("70"))
        self.assertEqual(item["maximo"], Decimal("75"))

    def test_conceptos_aditivos_energia_y_agua_mantienen_total(self):
        for flow, concept, values, unit in (
            ("energia", "consumo_energia", (10, 15), "kWh"),
            ("agua", "consumo_agua", (3, 4), "m3"),
        ):
            for value in values:
                record = self.record(flow)
                self.observation(record, concept, value, unit)
        result = sector_summary(self.org)
        totals = {
            (row["flujo"], row["concepto"]): row["total"]
            for row in result["indicadores"]
        }
        self.assertEqual(totals[("energia", "consumo_energia")], Decimal("25"))
        self.assertEqual(totals[("agua", "consumo_agua")], Decimal("7"))

    def test_magnitud_no_clasificada_no_es_aditiva(self):
        record = self.record("gestion_hidrica_suelo")
        self.observation(record, "precipitacion_observada", 30, "mm")
        item = sector_summary(self.org)["indicadores"][0]
        self.assertIsNone(item["total"])
        self.assertEqual(item["estrategia_agregacion"], "serie_no_aditiva")

    def test_granularidad_organizacion_rechaza_alcances_especificos(self):
        point = PuntoAmbientalOperacional.objects.create(
            organizacion=self.org, codigo="P-G", nombre="Punto", tipo="otro"
        )
        references = (
            {"unidad_operacional": self.unit},
            {"obra": self.work},
            {"proceso": self.process},
            {"activo": self.asset},
            {"punto": point},
        )
        for reference in references:
            with self.subTest(reference=next(iter(reference))), self.assertRaises(
                ValidationError
            ):
                self.record("energia", granularidad="organizacion", **reference)

    def test_granularidades_exigen_referencia_principal(self):
        cases = (
            ("instalacion", "energia"),
            ("obra", "energia"),
            ("proceso", "energia"),
            ("activo", "combustible_estacionario"),
            ("punto", "ruido"),
        )
        for granularity, flow in cases:
            with self.subTest(granularity=granularity), self.assertRaises(
                ValidationError
            ):
                self.record(flow, granularidad=granularity)

    def test_instalacion_y_obra_rechazan_atribucion_mas_especifica(self):
        with self.assertRaises(ValidationError):
            self.record(
                "energia",
                granularidad="instalacion",
                unidad_operacional=self.unit,
                proceso=self.process,
            )
        with self.assertRaises(ValidationError):
            self.record(
                "energia", granularidad="obra", obra=self.work, activo=self.asset
            )

    def test_contexto_superior_de_proceso_y_activo_debe_ser_coherente(self):
        other_unit = UnidadOperacional.objects.create(
            organizacion=self.org, nombre="Otra instalacion"
        )
        with self.assertRaises(ValidationError):
            self.record(
                "energia",
                granularidad="proceso",
                proceso=self.process,
                unidad_operacional=other_unit,
            )
        with self.assertRaises(ValidationError):
            self.record(
                "combustible_estacionario",
                granularidad="activo",
                activo=self.asset,
                proceso=ProcesoOperacional.objects.create(
                    organizacion=self.org, nombre="Otro proceso"
                ),
            )

    def test_punto_y_registro_rechazan_contexto_contradictorio(self):
        point = PuntoAmbientalOperacional.objects.create(
            organizacion=self.org,
            codigo="P-OBRA",
            nombre="Punto obra A",
            tipo="punto_ruido",
            obra=self.work,
            proceso_operacional=self.process,
            activo=self.asset,
            unidad_operacional=self.unit,
        )
        other_work = Obra.objects.create(
            organizacion=self.org,
            etapa_principal=self.stage,
            nombre="Obra B",
            fecha_inicio="2026-01-01",
        )
        with self.assertRaises(ValidationError):
            self.record("ruido", granularidad="punto", punto=point, obra=other_work)
        valid = self.record(
            "ruido",
            granularidad="punto",
            punto=point,
            obra=self.work,
            proceso=self.process,
            activo=self.asset,
            unidad_operacional=self.unit,
        )
        self.assertEqual(valid.punto, point)

    def test_endpoint_puntos_filtra_por_obra_tipo_y_preserva_listado_organizacional(
        self,
    ):
        work_b = Obra.objects.create(
            organizacion=self.org, nombre="Obra B", fecha_inicio="2026-01-01"
        )
        point_a = PuntoAmbientalOperacional.objects.create(
            organizacion=self.org,
            obra=self.work,
            codigo="PA",
            nombre="Ruido A",
            tipo="punto_ruido",
        )
        point_a_other_type = PuntoAmbientalOperacional.objects.create(
            organizacion=self.org,
            obra=self.work,
            codigo="PA-D",
            nombre="Drenaje A",
            tipo="punto_drenaje",
        )
        point_b = PuntoAmbientalOperacional.objects.create(
            organizacion=self.org,
            obra=work_b,
            codigo="PB",
            nombre="Ruido B",
            tipo="punto_ruido",
        )
        endpoint = f"{self.base}/puntos-ambientales/"

        response_a = self.client.get(endpoint, {"obra": self.work.id})
        response_b = self.client.get(endpoint, {"obra": work_b.id})
        response_type = self.client.get(
            endpoint, {"obra": self.work.id, "tipo": "punto_ruido"}
        )
        response_all = self.client.get(endpoint)
        self.assertEqual(
            {row["id"] for row in response_a.data}, {point_a.id, point_a_other_type.id}
        )
        self.assertEqual({row["id"] for row in response_b.data}, {point_b.id})
        self.assertEqual({row["id"] for row in response_type.data}, {point_a.id})
        self.assertTrue(
            {point_a.id, point_a_other_type.id, point_b.id}.issubset(
                {row["id"] for row in response_all.data}
            )
        )

    def test_endpoint_puntos_rechaza_obra_cross_tenant(self):
        foreign_work = Obra.objects.create(
            organizacion=self.other,
            nombre="Obra extranjera",
            fecha_inicio="2026-01-01",
        )
        response = self.client.get(
            f"{self.base}/puntos-ambientales/", {"obra": foreign_work.id}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, {"detail": "Recurso no encontrado."})
