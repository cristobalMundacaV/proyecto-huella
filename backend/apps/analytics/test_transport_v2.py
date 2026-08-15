from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (ActividadOperacional, ActivoOperacional, CalculoAmbiental,
                     EtapaObra, FuenteDatos, Observacion, Obra, Organizacion,
                     RutaOperacional, TransporteObra, UsuarioOrganizacion,
                     Vehiculo, ViajeOperacional)
from .services.context_gateway import ContextGateway
from .services.transport_v2 import (journey_metrics, save_journey_observations,
                                    transport_indicators)


class TransportV2Tests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("transport-v2", password="test-pass")
        self.org = Organizacion.objects.create(nombre="Transportes Uno", preset="transporte")
        self.other = Organizacion.objects.create(nombre="Transportes Dos", preset="transporte")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org)
        self.client.force_login(self.user); self.base = f"/api/organizaciones/{self.org.organizacion_id}"
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="GPS", tipo="gps")
        self.activity = ActividadOperacional.objects.create(organizacion=self.org, tipo="transporte", codigo="V-001", nombre="Viaje V-001", timestamp_inicio=timezone.now())
        self.asset = ActivoOperacional.objects.create(organizacion=self.org, codigo="CAM-01", nombre="Camion", tipo="vehiculo")
        self.vehicle = Vehiculo.objects.create(activo=self.asset, patente="ABCD12", tipo_vehiculo="camion", combustible="diesel", capacidad_carga=Decimal("20"), unidad_capacidad_carga="t", numero_ejes=3)
        self.route = RutaOperacional.objects.create(organizacion=self.org, codigo="R-01", nombre="Planta a obra", origen_nombre="Planta", destino_nombre="Obra", distancia_planificada=130, fuente_distancia="planificacion")

    def observation(self, concept, value, unit, source=None):
        return Observacion.objects.create(organizacion=self.org, actividad=self.activity, fuente=source or self.source, concepto=concept, valor_numerico=value, unidad=unit, timestamp_observacion=timezone.now(), estado="validada")

    def journey(self, **overrides):
        data = {"organizacion": self.org, "actividad": self.activity, "codigo": "V-001", "vehiculo": self.vehicle, "ruta": self.route, "origen_nombre": "Planta", "destino_nombre": "Obra", "fecha_salida": timezone.now(), "estado": "completado", **overrides}
        return ViajeOperacional.objects.create(**data)

    def test_crear_viaje_valido_ligado_a_activity_core(self):
        response = self.client.post(f"{self.base}/viajes-operacionales/", {"actividad": self.activity.id, "codigo":"V-001", "vehiculo":self.vehicle.id, "ruta":self.route.id, "origen_nombre":"Planta", "destino_nombre":"Obra", "fecha_salida":timezone.now().isoformat(), "distancia":"132", "fuente":self.source.id, "estado":"completado"}, format="json")
        self.assertEqual(response.status_code, 201)
        journey = ViajeOperacional.objects.get(); self.assertEqual(journey.actividad.tipo, "transporte")
        self.assertEqual(journey.observacion_distancia.valor_numerico, Decimal("132"))

    def test_rechaza_actividad_y_vehiculo_cross_tenant(self):
        foreign_activity = ActividadOperacional.objects.create(organizacion=self.other, tipo="transporte", codigo="B", nombre="B", timestamp_inicio=timezone.now())
        foreign_asset = ActivoOperacional.objects.create(organizacion=self.other, codigo="B", nombre="B", tipo="vehiculo")
        foreign_vehicle = Vehiculo.objects.create(activo=foreign_asset)
        with self.assertRaises(ValidationError): self.journey(actividad=foreign_activity, codigo="BAD-A")
        with self.assertRaises(ValidationError): self.journey(vehiculo=foreign_vehicle, codigo="BAD-V")

    def test_viaje_admite_tonelaje_y_combustible_desconocidos(self):
        journey = self.journey()
        self.assertIsNone(journey.observacion_carga); self.assertIsNone(journey.observacion_combustible)
        self.assertIsNone(journey_metrics(journey)["toneladas_km"])

    def test_tkm_y_utilizacion_solo_con_datos_compatibles(self):
        distance = self.observation("distancia_recorrida_km", 132, "km")
        load = self.observation("masa_transportada_t", 18, "t")
        journey = self.journey(observacion_distancia=distance, observacion_carga=load, estado_carga="parcialmente_cargado")
        metrics = journey_metrics(journey)
        self.assertEqual(metrics["toneladas_km"], Decimal("2376")); self.assertEqual(metrics["utilizacion_carga_pct"], Decimal("90"))
        self.vehicle.unidad_capacidad_carga = "kg"; self.vehicle.save(update_fields=["unidad_capacidad_carga"])
        self.assertIsNone(journey_metrics(journey)["utilizacion_carga_pct"])

    def test_retorno_vacio_e_indicadores_tenant(self):
        loaded_distance = self.observation("distancia_recorrida_km", 100, "km")
        self.journey(observacion_distancia=loaded_distance, estado_carga="cargado")
        activity_two = ActividadOperacional.objects.create(organizacion=self.org, tipo="transporte", codigo="V-002", nombre="Retorno", timestamp_inicio=timezone.now())
        empty_distance = Observacion.objects.create(organizacion=self.org, actividad=activity_two, fuente=self.source, concepto="distancia_recorrida_km", valor_numerico=50, unidad="km", timestamp_observacion=timezone.now())
        ViajeOperacional.objects.create(organizacion=self.org, actividad=activity_two, codigo="V-002", vehiculo=self.vehicle, ruta=self.route, origen_nombre="Obra", destino_nombre="Planta", fecha_salida=timezone.now(), tipo_trayecto="retorno", estado_carga="vacio", observacion_distancia=empty_distance, estado="completado")
        summary = transport_indicators(self.org)
        self.assertEqual(summary["km_sin_carga"], Decimal("50")); self.assertEqual(summary["retornos_vacios"], 1)
        self.assertEqual(summary["porcentaje_km_vacios"], Decimal("50") / Decimal("150") * 100)
        self.assertEqual(transport_indicators(self.other)["numero_viajes"], 0)

    def test_multiples_fuentes_discrepantes_permanecen(self):
        gps = self.observation("distancia_recorrida_km", 132, "km")
        odometer_source = FuenteDatos.objects.create(organizacion=self.org, nombre="Odometro", tipo="manual")
        self.observation("distancia_recorrida_km", 129, "km", odometer_source)
        journey = self.journey(observacion_distancia=gps)
        self.assertEqual(journey.actividad.observaciones.filter(concepto="distancia_recorrida_km").count(), 2)
        self.assertEqual({row.fuente.nombre for row in journey.actividad.observaciones.all()}, {"GPS", "Odometro"})

    def test_tercerizado_pendiente_y_contexto_compacto(self):
        journey = self.journey(tipo_gestion="tercerizado", metodologia_tercerizado="cliente_declara")
        self.assertEqual(journey.metodologia_tercerizado, "pendiente_validacion")
        package = ContextGateway().activity(self.activity, self.org)
        self.assertEqual(package["transporte"]["gestion"], "tercerizado")
        self.assertEqual(package["transporte"]["metodologia_tercerizado"], "pendiente_validacion")

    def test_indicadores_no_crean_impactos_ni_suman_metodos(self):
        distance = self.observation("distancia_recorrida_km", 10, "km"); load = self.observation("masa_transportada_t", 2, "t"); fuel = self.observation("combustible_consumido_l", 5, "L")
        self.journey(observacion_distancia=distance, observacion_carga=load, observacion_combustible=fuel)
        self.assertEqual(transport_indicators(self.org)["toneladas_km"], Decimal("20"))
        self.assertEqual(CalculoAmbiental.objects.count(), 0)

    def test_transporte_legacy_permanece_independiente(self):
        stage = EtapaObra.objects.create(organizacion=self.org, nombre="Logistica")
        work = Obra.objects.create(organizacion=self.org, etapa_principal=stage, nombre="Obra legacy", fecha_inicio="2026-01-01")
        legacy = TransporteObra.objects.create(obra=work, etapa=stage, vehiculo="Camion legacy", distancia_km=10, consumo_estimado_litro_km=Decimal("0.3"), fecha_hora=timezone.now())
        self.assertEqual(legacy.distancia_km, Decimal("10")); self.assertEqual(ViajeOperacional.objects.count(), 0)

    def test_viajes_vacios_no_son_retornos_si_no_tienen_tipo_retorno(self):
        for index, trip_type in enumerate(("ida", "interno"), start=1):
            activity = ActividadOperacional.objects.create(organizacion=self.org, tipo="transporte", codigo=f"V-E{index}", nombre="Vacio", timestamp_inicio=timezone.now())
            distance = Observacion.objects.create(organizacion=self.org, actividad=activity, fuente=self.source, concepto="distancia_recorrida_km", valor_numerico=10, unidad="km", timestamp_observacion=timezone.now())
            ViajeOperacional.objects.create(organizacion=self.org, actividad=activity, codigo=f"V-E{index}", vehiculo=self.vehicle, ruta=self.route, origen_nombre="A", destino_nombre="B", fecha_salida=timezone.now(), tipo_trayecto=trip_type, estado_carga="vacio", observacion_distancia=distance, estado="completado")
        summary = transport_indicators(self.org)
        self.assertEqual(summary["km_sin_carga"], Decimal("20"))
        self.assertEqual(summary["retornos_vacios"], 0)

    def test_retorno_vacio_cuenta_y_senal_repetida_excluye_otros_vacios(self):
        for index, trip_type in enumerate(("ida", "retorno", "retorno"), start=1):
            activity = ActividadOperacional.objects.create(organizacion=self.org, tipo="transporte", codigo=f"V-R{index}", nombre="Viaje", timestamp_inicio=timezone.now())
            ViajeOperacional.objects.create(organizacion=self.org, actividad=activity, codigo=f"V-R{index}", vehiculo=self.vehicle, ruta=self.route, origen_nombre="A", destino_nombre="B", fecha_salida=timezone.now(), tipo_trayecto=trip_type, estado_carga="vacio", estado="completado")
        summary = transport_indicators(self.org)
        self.assertEqual(summary["retornos_vacios"], 2)
        repeated = [item for item in summary["oportunidades"] if item["tipo"] == "ruta_repetida_retorno_vacio"]
        self.assertEqual(len(repeated), 1)
        self.assertEqual(repeated[0]["valor"], 2)

    def test_vacio_con_carga_positiva_es_rechazado_tambien_por_servicio(self):
        journey = self.journey(estado_carga="vacio")
        with self.assertRaises(ValidationError):
            save_journey_observations(journey, self.source, {"carga": Decimal("18")})
        self.assertIsNone(ViajeOperacional.objects.get(pk=journey.pk).observacion_carga_id)
        self.assertFalse(Observacion.objects.filter(concepto="masa_transportada_t").exists())

    def test_cargado_y_parcialmente_cargado_rechazan_carga_cero(self):
        zero_load = self.observation("masa_transportada_t", 0, "t")
        for state in ("cargado", "parcialmente_cargado"):
            with self.subTest(state=state), self.assertRaises(ValidationError):
                self.journey(observacion_carga=zero_load, estado_carga=state)

    def test_cargado_sin_observacion_de_carga_es_valido(self):
        journey = self.journey(estado_carga="cargado")
        self.assertIsNone(journey.observacion_carga_id)

    def test_indicadores_solo_incluyen_viajes_completados(self):
        for index, state in enumerate(("planificado", "cancelado", "completado"), start=1):
            activity = ActividadOperacional.objects.create(organizacion=self.org, tipo="transporte", codigo=f"V-S{index}", nombre="Viaje", timestamp_inicio=timezone.now())
            distance = Observacion.objects.create(organizacion=self.org, actividad=activity, fuente=self.source, concepto="distancia_recorrida_km", valor_numerico=index * 10, unidad="km", timestamp_observacion=timezone.now())
            ViajeOperacional.objects.create(organizacion=self.org, actividad=activity, codigo=f"V-S{index}", vehiculo=self.vehicle, ruta=self.route, origen_nombre="A", destino_nombre="B", fecha_salida=timezone.now(), observacion_distancia=distance, estado=state)
        summary = transport_indicators(self.org)
        self.assertEqual(summary["numero_viajes"], 1)
        self.assertEqual(summary["km_totales"], Decimal("30"))

    def test_endpoints_filtran_viajes_e_indicadores_por_obra(self):
        work_a = Obra.objects.create(organizacion=self.org, nombre="Obra A", fecha_inicio="2026-08-01")
        work_b = Obra.objects.create(organizacion=self.org, nombre="Obra B", fecha_inicio="2026-08-01")

        def scoped_journey(code, work, distance):
            activity = ActividadOperacional.objects.create(
                organizacion=self.org, obra=work, tipo="transporte", codigo=code,
                nombre=code, timestamp_inicio=timezone.now(),
            )
            observation = Observacion.objects.create(
                organizacion=self.org, actividad=activity, fuente=self.source,
                concepto="distancia_recorrida_km", valor_numerico=distance,
                unidad="km", timestamp_observacion=timezone.now(),
            )
            return ViajeOperacional.objects.create(
                organizacion=self.org, actividad=activity, codigo=code,
                vehiculo=self.vehicle, ruta=self.route, origen_nombre="A",
                destino_nombre="B", fecha_salida=timezone.now(),
                observacion_distancia=observation, estado="completado",
            )

        scoped_journey("A1", work_a, 10)
        scoped_journey("A2", work_a, 20)
        scoped_journey("B1", work_b, 70)

        response_a = self.client.get(f"{self.base}/viajes-operacionales/?obra={work_a.id}")
        response_b = self.client.get(f"{self.base}/viajes-operacionales/?obra={work_b.id}")
        response_all = self.client.get(f"{self.base}/viajes-operacionales/")
        self.assertEqual({row["codigo"] for row in response_a.data}, {"A1", "A2"})
        self.assertEqual({row["codigo"] for row in response_b.data}, {"B1"})
        self.assertEqual({row["codigo"] for row in response_all.data}, {"A1", "A2", "B1"})

        indicators_a = self.client.get(f"{self.base}/viajes-operacionales/indicadores/?obra={work_a.id}")
        indicators_b = self.client.get(f"{self.base}/viajes-operacionales/indicadores/?obra={work_b.id}")
        indicators_all = self.client.get(f"{self.base}/viajes-operacionales/indicadores/")
        self.assertEqual(indicators_a.data["numero_viajes"], 2)
        self.assertEqual(Decimal(indicators_a.data["km_totales"]), Decimal("30"))
        self.assertEqual(indicators_b.data["numero_viajes"], 1)
        self.assertEqual(Decimal(indicators_b.data["km_totales"]), Decimal("70"))
        self.assertEqual(indicators_all.data["numero_viajes"], 3)
        self.assertEqual(Decimal(indicators_all.data["km_totales"]), Decimal("100"))

    def test_endpoints_obra_rechazan_scope_cross_tenant(self):
        foreign_work = Obra.objects.create(
            organizacion=self.other, nombre="Obra extranjera", fecha_inicio="2026-08-01",
        )
        for endpoint in ("viajes-operacionales/", "viajes-operacionales/indicadores/"):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(f"{self.base}/{endpoint}?obra={foreign_work.id}")
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.data, {"detail": "Recurso no encontrado."})
