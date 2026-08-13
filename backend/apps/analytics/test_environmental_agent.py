import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    DatoACV, EvidenciaObra, MaterialConstruccion, Organizacion,
    ProblematicaAmbiental, RegistroEmision, UsuarioOrganizacion,
)
from .services.environmental_agent import EnvironmentalAgentProvider, EnvironmentalAgentService
from .services.environmental_context import minimal_agent_context


class MockProvider(EnvironmentalAgentProvider):
    name = "mock"
    model = "test-model"

    def __init__(self):
        self.received = None

    def generate(self, *, system_rules, context):
        self.received = {"rules": system_rules, "context": context}
        return {
            "diagnostico": {
                "hechos": ["El backend reporta 50 kgCO2e."],
                "correlaciones": [],
                "hipotesis": ["El consumo podria reducirse; requiere verificacion."],
            },
            "accion": "Revisar la operacion y definir un control medible.",
            "justificacion": "El indicador procesado supera la meta configurada.",
            "indicador_afectado": "co2e_total_kg",
            "resultado_esperado": "Obtener una medicion posterior comparable; no implica efectividad anticipada.",
            "prioridad": "alta",
            "periodo_seguimiento": "30 dias",
            "nivel_confianza": "media",
        }


class EnvironmentalAgentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("agent-user", password="secret")
        self.org = Organizacion.objects.create(organizacion_id="AGENT-A", nombre="Agent A", preset="industrial")
        self.other = Organizacion.objects.create(organizacion_id="AGENT-B", nombre="Agent B", preset="forestal")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org)
        self.problem = ProblematicaAmbiental.objects.create(
            organizacion=self.org, titulo="Consumo elevado", descripcion="Analizar indicador",
            categoria="Energia", indicador="co2e_total_kg", valor_inicial=Decimal("80"),
            objetivo_meta=Decimal("40"), fecha_deteccion=timezone.localdate() - timedelta(days=2), nivel_riesgo="alto",
        )
        RegistroEmision.objects.create(
            organizacion=self.org, fuente_emision="Electricidad", categoria="Energia", cantidad=10,
            unidad="kWh", factor_emision=5, fecha=timezone.localdate(), estado_validacion="validado", contabilizable=True,
        )

    def test_compact_context_excludes_raw_documents_and_records(self):
        evidence = EvidenciaObra.objects.create(
            organizacion=self.org, tipo_evidencia="boleta_electrica", nombre="Boleta",
            archivo=SimpleUploadedFile("boleta.txt", b"contenido completo secreto"),
            texto_extraido="TEXTO MASIVO QUE NO DEBE SALIR", metadata_extraccion={"raw": "DUMP"},
        )
        evidence.registros_emision.add(self.org.registros_emision.first())
        context = minimal_agent_context(self.problem)
        encoded = json.dumps(context, default=str)
        self.assertNotIn("TEXTO MASIVO", encoded)
        self.assertNotIn("contenido completo", encoded)
        self.assertNotIn("factor_emision", encoded)
        self.assertEqual(context["fuentes"]["total_registros"], 1)
        self.assertEqual(context["historial_reciente"]["limit"], 10)

    def test_structured_recommendation_is_persisted_with_mock_provider(self):
        provider = MockProvider()
        result = EnvironmentalAgentService(provider).recommend(self.problem)
        row = result.recommendation
        self.assertEqual(row.problematica, self.problem)
        self.assertEqual(row.indicador_afectado, self.problem.indicador)
        self.assertEqual(row.prioridad, "alta")
        self.assertEqual(row.proveedor, "mock")
        self.assertIn("no implica efectividad", row.resultado_esperado)
        self.assertNotIn("registros_emision", provider.received["context"])

    def test_problem_endpoints_enforce_tenant_and_remain_compact(self):
        foreign = ProblematicaAmbiental.objects.create(
            organizacion=self.other, titulo="Ajena", descripcion="No visible", categoria="Energia",
            valor_inicial=10, objetivo_meta=5, fecha_deteccion=timezone.localdate(),
        )
        client = APIClient()
        client.force_login(self.user)
        response = client.get(f"/api/problemas/{self.problem.id}/contexto/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("metadata", response.data)
        for suffix in ["historial", "fuentes", "acciones-previas", "evidencias-resumen", "contexto-normativo"]:
            compact = client.get(f"/api/problemas/{self.problem.id}/{suffix}/")
            self.assertEqual(compact.status_code, 200, suffix)
        self.assertEqual(client.get(f"/api/problemas/{foreign.id}/contexto/").status_code, 404)
        self.assertEqual(client.get(f"/api/problemas/{foreign.id}/historial/").status_code, 404)

    def test_organization_context_and_kpis_are_tenant_safe(self):
        client = APIClient()
        client.force_login(self.user)
        context = client.get(f"/api/organizaciones/{self.org.organizacion_id}/contexto/")
        self.assertEqual(context.status_code, 200)
        self.assertEqual(context.data["kpis"]["co2e_total_kg"], Decimal("50"))
        self.assertEqual(client.get(f"/api/organizaciones/{self.other.organizacion_id}/kpis/").status_code, 404)

    def test_material_lifecycle_requires_tenant_and_returns_partial_lca(self):
        material = MaterialConstruccion.objects.create(nombre="Acero", categoria="Metal")
        DatoACV.objects.create(
            organizacion=self.org, material_producto="Acero", etapa="materia_prima", valor=12,
            unidad="kgCO2e", fuente="EPD", calidad_dato="medido", origen_dato="proveedor",
        )
        client = APIClient()
        client.force_login(self.user)
        url = f"/api/materiales/{material.id}/ciclo-vida/?organizacion_id={self.org.organizacion_id}"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["material"]["nombre"], "Acero")
        self.assertFalse(response.data["completo"])
        foreign_url = f"/api/materiales/{material.id}/ciclo-vida/?organizacion_id={self.other.organizacion_id}"
        self.assertEqual(client.get(foreign_url).status_code, 404)

    def test_recommendation_endpoint_works_without_real_llm(self):
        client = APIClient()
        client.force_login(self.user)
        service = EnvironmentalAgentService(MockProvider())
        with patch("apps.analytics.views_environmental_context.default_agent_service", return_value=service):
            response = client.post(f"/api/problemas/{self.problem.id}/recomendaciones/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["nivel_confianza"], "media")
        self.assertEqual(self.problem.recomendaciones_agente.count(), 1)

    def test_agent_rejects_unsupported_success_or_legal_claims(self):
        class UnsafeProvider(MockProvider):
            def generate(self, **kwargs):
                payload = super().generate(**kwargs)
                payload["resultado_esperado"] = "La accion es efectiva y cumple la normativa."
                return payload

        with self.assertRaises(ValidationError):
            EnvironmentalAgentService(UnsafeProvider()).recommend(self.problem)
        self.assertEqual(self.problem.recomendaciones_agente.count(), 0)
