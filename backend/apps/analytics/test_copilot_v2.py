import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.iot.models import DispositivoSensor

from .models import (
    AccionMejoraAmbiental,
    ActivoOperacional,
    CalculoAmbiental,
    HitoDecisionIA,
    IndicadorAmbiental,
    IndicadorProblematica,
    MemoriaOrganizacion,
    Obra,
    Organizacion,
    ProblematicaAmbiental,
    RecomendacionAgenteAmbiental,
    RestriccionContextual,
    SnapshotIntervencion,
    UsuarioOrganizacion,
    ValorIndicador,
)
from .services.context_gateway import ContextGateway
from .services.copilot_commands import confirm_command, prepare_action
from .services.copilot_v2 import CopilotProposalService
from .services.environmental_agent import EnvironmentalAgentProvider


class CopilotProvider(EnvironmentalAgentProvider):
    name = "mock-v2"
    model = "context-test"

    def __init__(self):
        self.received = []
        self.alternative = False

    def generate(self, *, system_rules, context):
        self.received.append({"rules": system_rules, "context": context})
        restricted = bool(context["context"]["restricciones"])

        return {
            "titulo": (
                "Consolidar cargas" if restricted else "Cambiar proveedor logistico"
            ),
            "descripcion": "Alternativa verificable",
            "justificacion": "Considera KPI y restricciones preparadas.",
            "kpis_afectados": ["intensidad"],
            "requisitos": ["confirmacion humana"],
            "riesgos": ["resultado incierto"],
            "prioridad": "alta",
            "hechos_utilizados": ["El indicador asociado empeoro."],
            "limitaciones": ["No existe evidencia de causalidad."],
            "supuestos": ["La alternativa debe validarse operacionalmente."],
        }


class InvalidProvider(CopilotProvider):
    def generate(self, **kwargs):
        return {"titulo": "incompleta"}


class FailingProvider(CopilotProvider):
    def generate(self, **kwargs):
        raise RuntimeError("provider down")


class CopilotV2Tests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("copilot-v2", password="test-pass")
        self.org = Organizacion.objects.create(nombre="Copilot Uno")
        self.other = Organizacion.objects.create(nombre="Copilot Dos")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org)
        self.client.force_login(self.user)
        self.problem = ProblematicaAmbiental.objects.create(
            organizacion=self.org,
            titulo="Alta intensidad transporte",
            descripcion="KPI empeoro",
            categoria="transporte",
            indicador="intensidad",
            unidad_indicador="kgCO2e/t",
            valor_inicial=10,
            objetivo_meta=9,
            fecha_deteccion=date(2026, 1, 1),
        )
        self.indicator = IndicadorAmbiental.objects.create(
            organizacion=self.org,
            codigo="intensidad",
            nombre="Intensidad",
            tipo="intensidad",
            unidad="kgCO2e/t",
            origen_numerador="impactos_ambientales",
            origen_denominador="masa",
            direccion_deseable="menor_es_mejor",
        )
        IndicadorProblematica.objects.create(
            problematica=self.problem,
            indicador=self.indicator,
            rol="principal",
            direccion_deseada="menor_es_mejor",
        )
        ValorIndicador.objects.create(
            indicador=self.indicator,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 1, 31),
            valor=10,
            unidad=self.indicator.unidad,
            fuente_calculo="test",
        )
        ValorIndicador.objects.create(
            indicador=self.indicator,
            periodo_inicio=date(2026, 2, 1),
            periodo_fin=date(2026, 2, 28),
            valor=Decimal("10.8"),
            unidad=self.indicator.unidad,
            fuente_calculo="test",
        )

    def test_context_gateway_problem_minimo_y_solo_kpis_asociados(self):
        foreign_kpi = IndicadorAmbiental.objects.create(
            organizacion=self.org,
            codigo="no-asociado",
            nombre="No asociado",
            tipo="absoluto",
            unidad="kg",
            origen_numerador="x",
        )
        package = ContextGateway().problem(self.problem, self.org)
        self.assertEqual([item["codigo"] for item in package["kpis"]], ["intensidad"])
        self.assertNotIn(foreign_kpi.codigo, str(package))
        self.assertNotIn("registros_emision", package)
        self.assertLessEqual(len(package["historial_resumido"]), 10)

    def test_contexto_y_endpoints_no_incluyen_otro_tenant(self):
        foreign = ProblematicaAmbiental.objects.create(
            organizacion=self.other,
            titulo="Ajena",
            descripcion="secret",
            categoria="x",
            valor_inicial=1,
            objetivo_meta=0,
            fecha_deteccion=date.today(),
        )
        with self.assertRaises(ValidationError):
            ContextGateway().problem(foreign, self.org)
        self.assertEqual(
            self.client.get(f"/api/context/problems/{foreign.id}/").status_code, 404
        )
        self.assertEqual(
            self.client.get(f"/api/context/problems/{self.problem.id}/").status_code,
            200,
        )

    def test_memoria_persistente_y_restriccion_temporal(self):
        MemoriaOrganizacion.objects.create(
            organizacion=self.org,
            problematica=self.problem,
            tipo="solucion_intentada",
            contenido={"accion": "cambio proveedor"},
            fuente_origen="intervencion",
        )
        active = RestriccionContextual.objects.create(
            organizacion=self.org,
            problematica=self.problem,
            tipo="contrato",
            descripcion="Proveedor fijo",
            vigente_hasta=timezone.now() + timedelta(days=30),
        )
        RestriccionContextual.objects.create(
            organizacion=self.org,
            problematica=self.problem,
            tipo="expirada",
            descripcion="Vieja",
            vigente_hasta=timezone.now() - timedelta(days=1),
        )
        memory = ContextGateway().organization_memory(self.org)
        self.assertEqual(memory["items"][0]["contenido"]["accion"], "cambio proveedor")
        self.assertEqual([item["id"] for item in memory["restricciones"]], [active.id])

    def test_contexto_problema_combina_restriccion_global_y_especifica(self):
        other_problem = ProblematicaAmbiental.objects.create(
            organizacion=self.org,
            titulo="Otra",
            descripcion="Otra",
            categoria="x",
            valor_inicial=1,
            objetivo_meta=0,
            fecha_deteccion=date.today(),
        )
        global_restriction = RestriccionContextual.objects.create(
            organizacion=self.org,
            tipo="contrato",
            descripcion="Proveedor logistico no puede cambiarse",
        )
        specific = RestriccionContextual.objects.create(
            organizacion=self.org,
            problematica=self.problem,
            tipo="operacion",
            descripcion="Proceso continuo",
        )
        RestriccionContextual.objects.create(
            organizacion=self.org,
            problematica=other_problem,
            tipo="otra",
            descripcion="No aplica",
        )
        RestriccionContextual.objects.create(
            organizacion=self.org,
            problematica=self.problem,
            tipo="inactiva",
            descripcion="No aplica",
            activa=False,
        )
        RestriccionContextual.objects.create(
            organizacion=self.org,
            problematica=self.problem,
            tipo="vencida",
            descripcion="No aplica",
            vigente_hasta=timezone.now() - timedelta(days=1),
        )
        package = ContextGateway().problem(self.problem, self.org)
        self.assertEqual(
            {item["id"] for item in package["restricciones"]},
            {global_restriction.id, specific.id},
        )

    def test_sensor_health_json_safe_sin_y_con_activo_y_endpoint_tenant(self):
        sensor_without = DispositivoSensor.objects.create(
            dispositivo_id="HEALTH-EMPTY",
            nombre="Sensor sin activo",
            organizacion=self.org,
        )
        asset = ActivoOperacional.objects.create(
            organizacion=self.org,
            codigo="CAM-HEALTH",
            nombre="Camion health",
            estado="operativo",
        )
        sensor_with = DispositivoSensor.objects.create(
            dispositivo_id="HEALTH-ASSET",
            nombre="Sensor con activo",
            organizacion=self.org,
            activo_operacional=asset,
        )
        gateway = ContextGateway()
        without_package = gateway.sensor_health(sensor_without, self.org)
        with_package = gateway.sensor_health(sensor_with, self.org)
        self.assertIsNone(without_package["sensor"]["activo"])
        self.assertIsNone(without_package["sensor"]["activo_id"])
        self.assertEqual(
            with_package["sensor"]["activo"],
            {
                "id": asset.id,
                "codigo": asset.codigo,
                "nombre": asset.nombre,
                "estado": asset.estado,
            },
        )
        json.dumps(without_package)
        json.dumps(with_package)
        self.assertEqual(
            self.client.get(
                f"/api/context/sensors/{sensor_with.id}/health/"
            ).status_code,
            200,
        )
        foreign = DispositivoSensor.objects.create(
            dispositivo_id="HEALTH-FOREIGN", nombre="Ajeno", organizacion=self.other
        )
        self.assertEqual(
            self.client.get(f"/api/context/sensors/{foreign.id}/health/").status_code,
            404,
        )

    def test_restriccion_global_llega_al_copiloto_y_propuesta(self):
        restriction = RestriccionContextual.objects.create(
            organizacion=self.org,
            tipo="contrato",
            descripcion="Proveedor logistico no puede cambiarse",
        )
        provider = CopilotProvider()
        proposal = CopilotProposalService(provider).propose(
            self.problem, user=self.user
        )
        self.assertEqual(proposal.restricciones_consideradas, [restriction.id])
        self.assertEqual(
            provider.received[0]["context"]["context"]["restricciones"][0]["id"],
            restriction.id,
        )

    def test_propuesta_persistida_hito_y_contexto_minimo_provider(self):
        provider = CopilotProvider()
        proposal = CopilotProposalService(provider).propose(
            self.problem, "Necesito una alternativa", self.user
        )
        self.assertEqual(proposal.estado, "propuesta")
        self.assertEqual(proposal.proveedor, "mock-v2")
        self.assertEqual(AccionMejoraAmbiental.objects.count(), 0)
        self.assertGreaterEqual(
            HitoDecisionIA.objects.filter(propuesta=proposal).count(), 1
        )
        sent = provider.received[0]["context"]
        self.assertEqual(
            set(sent),
            {"context", "additional_context", "user_message", "previous_proposal"},
        )
        self.assertNotIn("archivo", str(sent))
        self.assertNotIn("factor_emision", str(sent))

    def test_caso_obligatorio_refutacion_conserva_y_ajusta(self):
        provider = CopilotProvider()
        service = CopilotProposalService(provider)
        original = service.propose(self.problem, user=self.user)
        restriction, adjusted = service.refute(
            original, "No puedo cambiar proveedor por contrato.", self.user
        )
        original.refresh_from_db()
        self.assertEqual(original.estado, "rechazada")
        self.assertEqual(original.titulo, "Cambiar proveedor logistico")
        self.assertEqual(adjusted.propuesta_anterior, original)
        self.assertEqual(adjusted.version, 2)
        self.assertEqual(adjusted.titulo, "Consolidar cargas")
        self.assertIn(restriction.id, adjusted.restricciones_consideradas)
        self.assertEqual(AccionMejoraAmbiental.objects.count(), 0)

    def test_confirmacion_humana_crea_y_selecciona_accion(self):
        proposal = CopilotProposalService(CopilotProvider()).propose(
            self.problem, user=self.user
        )
        command = prepare_action(proposal)
        self.assertEqual(AccionMejoraAmbiental.objects.count(), 0)
        with self.assertRaises(ValidationError):
            confirm_command(command, self.user)
        self.assertEqual(AccionMejoraAmbiental.objects.count(), 0)
        result = confirm_command(command, self.user, confirmed=True)
        self.assertEqual(result["ciclo"], 1)
        self.assertEqual(AccionMejoraAmbiental.objects.get().estado, "seleccionada")
        proposal.refresh_from_db()
        self.assertEqual(proposal.estado, "convertida_en_accion")

    def test_reevaluacion_ia_no_inicia_ciclo(self):
        provider = CopilotProvider()
        with patch(
            "apps.analytics.views_copilot_v2.default_copilot_service",
            return_value=CopilotProposalService(provider),
        ):
            response = self.client.post(
                f"/api/agent/problems/{self.problem.id}/reevaluation-draft/",
                {},
                format="json",
            )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["ciclo_iniciado"])
        self.assertEqual(self.problem.ciclos_reevaluacion.count(), 0)

    def test_contexto_adicional_solo_pasa_por_gateway(self):
        provider = CopilotProvider()
        service = CopilotProposalService(provider)
        service.propose(
            self.problem, context_categories=["organization_memory", "intervention"]
        )
        self.assertEqual(
            set(provider.received[0]["context"]["additional_context"]),
            {"organization_memory", "intervention"},
        )
        with self.assertRaises(ValidationError):
            service.propose(self.problem, context_categories=["database_dump"])

    def test_fallo_provider_no_rompe_core_y_respuesta_invalida_se_rechaza(self):
        before_values = self.indicator.valores.count()
        with self.assertRaises(RuntimeError):
            CopilotProposalService(FailingProvider()).propose(self.problem)
        with self.assertRaises(ValidationError):
            CopilotProposalService(InvalidProvider()).propose(self.problem)
        self.assertTrue(
            ProblematicaAmbiental.objects.filter(pk=self.problem.pk).exists()
        )
        self.assertEqual(self.indicator.valores.count(), before_values)
        self.assertEqual(RecomendacionAgenteAmbiental.objects.count(), 0)

    def test_ia_no_modifica_calculos_factores_snapshots_ni_inicia_acciones(self):
        counts = (
            CalculoAmbiental.objects.count(),
            SnapshotIntervencion.objects.count(),
            AccionMejoraAmbiental.objects.count(),
        )
        CopilotProposalService(CopilotProvider()).propose(self.problem)
        self.assertEqual(
            (
                CalculoAmbiental.objects.count(),
                SnapshotIntervencion.objects.count(),
                AccionMejoraAmbiental.objects.count(),
            ),
            counts,
        )

    def test_api_propuesta_feedback_y_confirmacion_explicita(self):
        service = CopilotProposalService(CopilotProvider())
        with patch(
            "apps.analytics.views_copilot_v2.default_copilot_service",
            return_value=service,
        ):
            created = self.client.post(
                f"/api/agent/problems/{self.problem.id}/proposals/",
                {"mensaje": "Alternativa"},
                format="json",
            )
        self.assertEqual(created.status_code, 201)
        accepted = self.client.post(
            f"/api/agent/problems/{self.problem.id}/proposals/{created.data['id']}/feedback/",
            {"decision": "aceptar"},
            format="json",
        )
        self.assertTrue(accepted.data["requiere_confirmacion"])
        self.assertEqual(AccionMejoraAmbiental.objects.count(), 0)
        command_id = accepted.data["comando"]
        self.assertEqual(
            self.client.post(
                f"/api/agent/commands/{command_id}/confirm/",
                {"confirmado": False},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                f"/api/agent/commands/{command_id}/confirm/",
                {"confirmado": True},
                format="json",
            ).status_code,
            201,
        )


def test_propuesta_distingue_hechos_supuestos_y_limitaciones(
    self,
):
    provider = CopilotProvider()

    proposal = CopilotProposalService(provider).propose(
        self.problem,
        user=self.user,
    )

    self.assertEqual(
        proposal.diagnostico["hechos"],
        ["El indicador asociado empeoro."],
    )

    self.assertEqual(
        proposal.diagnostico["limitaciones"],
        ["No existe evidencia de causalidad."],
    )

    self.assertEqual(
        proposal.diagnostico["hipotesis"],
        ["La alternativa debe validarse operacionalmente."],
    )


def test_contexto_problema_identifica_obra(
    self,
):
    work = Obra.objects.create(
        organizacion=self.org,
        nombre="Obra Copiloto",
        fecha_inicio=date(
            2026,
            1,
            1,
        ),
    )

    self.problem.obra = work
    self.problem.save()

    package = ContextGateway().problem(
        self.problem,
        self.org,
    )

    self.assertEqual(
        package["references"]["work"],
        work.id,
    )

    self.assertEqual(
        package["obra"]["id"],
        work.id,
    )
