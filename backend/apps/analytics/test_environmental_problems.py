from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Organizacion, ProblematicaAmbiental, RegistroEmision, UsuarioOrganizacion
from .services.environmental_problems import (
    add_measurement, evaluate_problem, implement_action, measure_from_engine,
    recommend_action, transition_problem,
)


class EnvironmentalProblemsTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(organizacion_id="ORG-A", nombre="Organizacion A", preset="industrial")
        self.other = Organizacion.objects.create(organizacion_id="ORG-B", nombre="Organizacion B", preset="forestal")
        self.today = timezone.localdate()

    def problem(self, **overrides):
        data = dict(
            organizacion=self.org, titulo="Emisiones elevadas", descripcion="Desviacion del indicador",
            categoria="Energia", indicador="co2e_total_kg", valor_inicial=Decimal("100"),
            objetivo_meta=Decimal("70"), fecha_deteccion=self.today - timedelta(days=5), nivel_riesgo="alto",
        )
        data.update(overrides)
        return ProblematicaAmbiental.objects.create(**data)

    def prepare_followup(self, **overrides):
        problem = self.problem(**overrides)
        transition_problem(problem, "en_analisis")
        action = recommend_action(problem, titulo="Reducir consumo", descripcion="Optimizar equipos")
        implement_action(action)
        return problem, action

    def test_complete_cycle_and_effective_evaluation(self):
        problem, action = self.prepare_followup()
        add_measurement(problem, fecha=self.today, valor=Decimal("60"), accion=action)
        evaluate_problem(problem)
        problem.refresh_from_db()
        self.assertEqual(problem.estado, "resuelta")
        self.assertEqual(problem.resultado_evaluacion, "efectiva")
        self.assertEqual(problem.mejora_absoluta, Decimal("40"))
        self.assertEqual(problem.mejora_porcentaje, Decimal("40"))
        self.assertGreaterEqual(problem.historial.count(), 8)

    def test_partial_and_not_effective_results(self):
        partial, _ = self.prepare_followup(titulo="Parcial")
        add_measurement(partial, fecha=self.today, valor=Decimal("80"))
        evaluate_problem(partial)
        self.assertEqual(partial.resultado_evaluacion, "parcialmente_efectiva")
        self.assertEqual(partial.estado, "mejora_insuficiente")

        failed, _ = self.prepare_followup(titulo="Fallida")
        add_measurement(failed, fecha=self.today, valor=Decimal("110"))
        evaluate_problem(failed)
        self.assertEqual(failed.resultado_evaluacion, "no_efectiva")
        self.assertEqual(failed.estado, "no_resuelta")

    def test_invalid_transition_and_no_measurement_cannot_succeed(self):
        problem = self.problem()
        with self.assertRaises(ValidationError):
            transition_problem(problem, "resuelta")
        problem, _ = self.prepare_followup(titulo="Sin medicion")
        transition_problem(problem, "en_seguimiento")
        with self.assertRaises(ValidationError):
            evaluate_problem(problem)
        self.assertEqual(problem.resultado_evaluacion, "pendiente")

    def test_engine_measurement_uses_only_valid_accountable_records(self):
        problem, _ = self.prepare_followup(valor_inicial=Decimal("100"), objetivo_meta=Decimal("70"))
        RegistroEmision.objects.create(
            organizacion=self.org, fuente_emision="Electricidad", categoria="Energia", cantidad=10,
            unidad="kWh", factor_emision=6, fecha=self.today, estado_validacion="validado", contabilizable=True,
        )
        RegistroEmision.objects.create(
            organizacion=self.org, fuente_emision="Duplicado", categoria="Energia", cantidad=100,
            unidad="kWh", factor_emision=6, fecha=self.today, estado_validacion="validado", contabilizable=False,
        )
        measurement = measure_from_engine(problem, fecha=self.today)
        self.assertEqual(measurement.valor, Decimal("60"))
        self.assertEqual(measurement.fuente, "motor_ambiental")

    def test_api_is_tenant_safe(self):
        user = User.objects.create_user("analista", password="secret")
        UsuarioOrganizacion.objects.create(user=user, organizacion=self.org)
        foreign = self.problem(organizacion=self.other)
        client = APIClient()
        client.force_login(user)
        own_url = f"/api/organizaciones/{self.org.organizacion_id}/problematicas/"
        response = client.post(own_url, {
            "titulo": "Nueva", "descripcion": "Detalle", "categoria": "Agua", "indicador": "co2e_total_kg",
            "valor_inicial": "20", "objetivo_meta": "10", "fecha_deteccion": str(self.today), "nivel_riesgo": "medio",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        foreign_url = f"/api/organizaciones/{self.other.organizacion_id}/problematicas/{foreign.id}/"
        self.assertIn(client.get(foreign_url).status_code, {403, 404})
        self.assertEqual(ProblematicaAmbiental.objects.filter(organizacion=self.org).count(), 1)
