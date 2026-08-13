from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    AccionMejoraAmbiental, LimiteNormativoAmbiental, Organizacion,
    ProblematicaAmbiental, UsuarioOrganizacion,
)
from .services.environmental_agent import EnvironmentalAgentService
from .services.environmental_context import normative_context
from .services.environmental_dossier import generate_dossier
from .services.environmental_escalation import apply_escalation, evaluate_escalation
from .test_environmental_agent import MockProvider


class SummaryProvider:
    name = "mock-summary"
    model = "test-summary"

    def __init__(self):
        self.context = None

    def generate(self, *, system_rules, context):
        self.context = context
        return {"resumen_ejecutivo": "Caso escalado para revision profesional; las hipotesis requieren validacion."}


class EnvironmentalEscalationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("professional", password="secret")
        self.org = Organizacion.objects.create(organizacion_id="PRO-A", nombre="Industrial Sur", preset="industrial", region="Biobio")
        self.other = Organizacion.objects.create(organizacion_id="PRO-B", nombre="Forestal Norte", preset="forestal", region="Maule")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org)

    def problem(self, **overrides):
        data = dict(
            organizacion=self.org, titulo="Indicador fuera de objetivo", descripcion="Persistencia operacional",
            categoria="Energia", indicador="co2e_total_kg", valor_inicial=Decimal("100"), objetivo_meta=Decimal("60"),
            valor_posterior=Decimal("90"), mejora_absoluta=Decimal("10"), mejora_porcentaje=Decimal("10"),
            fecha_deteccion=timezone.localdate() - timedelta(days=10), nivel_riesgo="medio",
            estado="no_resuelta", resultado_evaluacion="no_efectiva",
        )
        data.update(overrides)
        return ProblematicaAmbiental.objects.create(**data)

    def test_escalates_after_multiple_failed_actions(self):
        problem = self.problem()
        for index in range(2):
            AccionMejoraAmbiental.objects.create(
                problematica=problem, titulo=f"Accion {index}", descripcion="Implementada sin alcanzar meta",
                implementada_at=timezone.now(),
            )
        result = apply_escalation(problem, user=self.user)
        problem.refresh_from_db()
        self.assertTrue(result["debe_escalar"])
        self.assertTrue(problem.requiere_evaluacion_profesional)
        self.assertEqual(problem.estado, "escalada")
        self.assertIn("acciones_fallidas_repetidas", [item["criterio"] for item in problem.criterios_escalamiento])

    def test_critical_risk_escalates_and_low_risk_open_problem_does_not(self):
        critical = self.problem(titulo="Critico", nivel_riesgo="critico", resultado_evaluacion="pendiente", estado="detectada", valor_posterior=None)
        self.assertTrue(apply_escalation(critical)["debe_escalar"])
        critical.refresh_from_db()
        self.assertEqual(critical.estado, "escalada")

        normal = self.problem(titulo="Normal", nivel_riesgo="bajo", resultado_evaluacion="pendiente", estado="detectada", valor_posterior=None)
        result = apply_escalation(normal)
        normal.refresh_from_db()
        self.assertFalse(result["debe_escalar"])
        self.assertEqual(normal.estado, "detectada")

    def test_agent_is_blocked_after_escalation(self):
        problem = self.problem(nivel_riesgo="critico")
        apply_escalation(problem)
        problem.refresh_from_db()
        with self.assertRaises(ValidationError):
            EnvironmentalAgentService(MockProvider()).recommend(problem)
        self.assertEqual(problem.recomendaciones_agente.count(), 0)

    def test_complete_processed_dossier_has_no_document_dump(self):
        problem = self.problem(nivel_riesgo="critico", metadata={"restricciones_tecnicas": ["Equipo sin reemplazo inmediato"]})
        AccionMejoraAmbiental.objects.create(problematica=problem, titulo="Optimizar", descripcion="Control operacional", implementada_at=timezone.now())
        recommendation = EnvironmentalAgentService(MockProvider()).recommend(problem)
        apply_escalation(problem)
        problem.refresh_from_db()
        provider = SummaryProvider()
        dossier = generate_dossier(problem, provider, user=self.user)
        self.assertEqual(dossier.version, 1)
        self.assertTrue(dossier.contenido_procesado["escalamiento"]["requiere_evaluacion_profesional"])
        self.assertIn("acciones", dossier.contenido_procesado)
        self.assertIn("mediciones", dossier.contenido_procesado)
        self.assertIn("recomendaciones_previas", dossier.contenido_procesado)
        self.assertFalse(dossier.contenido_procesado["limites_contexto"]["documentos_completos_incluidos"])
        self.assertNotIn("TEXTO MASIVO", str(provider.context))

    def test_normative_rules_filter_tenant_preset_region_validity_and_validation(self):
        problem = self.problem(resultado_evaluacion="pendiente", estado="detectada", valor_posterior=None, metadata={"tipo_instalacion": "planta"})
        base = dict(
            organizacion=self.org, variable_id="co2e_total_kg", nombre="Regla configurada", normativa="ISO 14001",
            limite=Decimal("40"), unidad="kgCO2e", comparador=">=", industria="industrial", region="Biobio",
            tipo_instalacion="planta", fuente_normativa="Documento interno validado", activo=True,
        )
        valid = LimiteNormativoAmbiental.objects.create(**base, validado=True)
        LimiteNormativoAmbiental.objects.create(**{**base, "nombre": "No validada", "validado": False})
        LimiteNormativoAmbiental.objects.create(**{**base, "nombre": "Vencida", "validado": True, "vigencia_hasta": timezone.localdate() - timedelta(days=1)})
        LimiteNormativoAmbiental.objects.create(**{**base, "nombre": "Otra region", "region": "Maule", "validado": True})
        LimiteNormativoAmbiental.objects.create(**{**base, "nombre": "Otro rubro", "industria": "forestal", "validado": True})
        rules = normative_context(problem)["reglas_validadas"]
        self.assertEqual([row["id"] for row in rules], [valid.id])
        self.assertTrue(evaluate_escalation(problem)["debe_escalar"])

        valid.validado = False
        valid.save(update_fields=["validado"])
        self.assertFalse(normative_context(problem)["puede_afirmar_cumplimiento"])

    def test_escalation_and_dossier_endpoints_are_tenant_safe(self):
        own = self.problem(nivel_riesgo="critico")
        foreign = self.problem(organizacion=self.other, titulo="Ajena", nivel_riesgo="critico")
        client = APIClient()
        client.force_login(self.user)
        response = client.post(f"/api/problemas/{own.id}/escalamiento/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["requiere_evaluacion_profesional"])
        with patch("apps.analytics.views_environmental_escalation.OpenAIEnvironmentalProvider", return_value=SummaryProvider()):
            dossier = client.post(f"/api/problemas/{own.id}/expediente/", {}, format="json")
        self.assertEqual(dossier.status_code, 201)
        self.assertEqual(client.get(f"/api/problemas/{own.id}/expediente/").status_code, 200)
        self.assertEqual(client.post(f"/api/problemas/{foreign.id}/escalamiento/", {}).status_code, 404)
        self.assertEqual(client.get(f"/api/problemas/{foreign.id}/expediente/").status_code, 404)
