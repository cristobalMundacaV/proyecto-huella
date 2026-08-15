import json
from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase

from .models import (AccionMejoraAmbiental, ActividadOperacional,
                     AlcanceProblematica, CasoConocimientoAmbiental,
                     FactorAmbiental, FormulaAmbiental, Organizacion,
                     ProblematicaAmbiental, ResultadoIntervencion,
                     SnapshotIntervencion, UsuarioOrganizacion)
from .services.context_gateway import ContextGateway
from .services.knowledge_v1 import (aggregate_knowledge,
                                    create_knowledge_case)


class KnowledgeV1Tests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("knowledge-user", password="test-pass")
        self.org_a = Organizacion.objects.create(nombre="Empresa Privada Alfa", preset="construccion")
        self.org_b = Organizacion.objects.create(nombre="Empresa Privada Beta", preset="construccion")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org_a, rol="analista")
        self.client.force_login(self.user)
        self.result_a = self._result(self.org_a, "positiva", "consolidacion_cargas")
        self.result_b = self._result(self.org_b, "parcial", "consolidacion_cargas")

    def _result(self, organization, state, action_type):
        activity = ActividadOperacional.objects.create(organizacion=organization, tipo="transporte", codigo=f"ACT-{organization.id}-{state}", nombre="Actividad privada", timestamp_inicio="2026-01-01T10:00:00Z")
        problem = ProblematicaAmbiental.objects.create(organizacion=organization, titulo=f"Problema privado {organization.nombre}", descripcion="Privada", categoria="transporte", valor_inicial=10, objetivo_meta=8, fecha_deteccion=date(2026, 1, 1), metadata={"tipo_problematica": "alta_intensidad"})
        AlcanceProblematica.objects.create(problematica=problem, actividad_operacional=activity)
        action = AccionMejoraAmbiental.objects.create(problematica=problem, titulo=f"Accion privada {organization.nombre}", descripcion="Privada", estado="evaluada", implementada_at="2026-02-01T10:00:00Z", metadata={"tipo_accion": action_type})
        base = SnapshotIntervencion.objects.create(problematica=problem, accion=action, ciclo=1, tipo="base", fecha=date(2026, 1, 31), congelado=True)
        final = SnapshotIntervencion.objects.create(problematica=problem, accion=action, ciclo=1, tipo="resultado", fecha=date(2026, 3, 31), congelado=True)
        return ResultadoIntervencion.objects.create(problematica=problem, accion=action, ciclo=1, snapshot_base=base, snapshot_resultado=final, estado=state, fecha_evaluacion=date(2026, 3, 31), metricas_comparadas=[{"indicador": 987654, "base": "10", "resultado": "8", "diferencia": "-2", "porcentaje": "-20", "estado": "mejoro", "meta_cumplida": True}])

    def test_crea_caso_valido_resumido_y_utilizable(self):
        case, created = create_knowledge_case(self.result_a, self.org_a)
        self.assertTrue(created); self.assertEqual(case.estado, "utilizable")
        self.assertEqual(case.resultado, "exitoso"); self.assertEqual(case.fuerza_evidencia, "media")
        self.assertEqual(case.metricas_comparadas[0]["base"], "10")
        self.assertEqual(case.metricas_comparadas[0]["resultado"], "8")
        self.assertNotIn("indicador", case.metricas_comparadas[0])

    def test_rechaza_intervencion_otro_tenant(self):
        with self.assertRaises(ValidationError): create_knowledge_case(self.result_b, self.org_a)

    def test_no_implementado_y_no_viable_no_son_fracaso(self):
        not_done = self._result(self.org_a, "no_implementada", "accion_pendiente")
        not_viable = self._result(self.org_a, "no_viable", "accion_inviable")
        first, _ = create_knowledge_case(not_done, self.org_a)
        second, _ = create_knowledge_case(not_viable, self.org_a)
        self.assertEqual((first.resultado, first.grado_implementacion), ("no_implementado", "no_implementado"))
        self.assertEqual((second.resultado, second.viabilidad), ("no_viable", "no_viable"))
        self.assertNotEqual(first.resultado, "sin_efecto"); self.assertNotEqual(second.resultado, "negativo")

    def test_origen_ia_profesional_e_idempotencia_versionada(self):
        ia, created = create_knowledge_case(self.result_a, self.org_a, "ia")
        same, repeated = create_knowledge_case(self.result_a, self.org_a, "ia")
        self.assertTrue(created); self.assertFalse(repeated); self.assertEqual(ia.id, same.id)
        professional, changed = create_knowledge_case(self.result_a, self.org_a, "profesional")
        self.assertTrue(changed); self.assertEqual(professional.version, 2)
        self.assertEqual({ia.origen_conocimiento, professional.origen_conocimiento}, {"ia", "profesional"})

    def test_agregado_cross_tenant_es_anonimo(self):
        create_knowledge_case(self.result_a, self.org_a)
        create_knowledge_case(self.result_b, self.org_b)
        summary = aggregate_knowledge(preset="construccion", categoria_ambiental="transporte", tipo_accion="consolidacion_cargas")
        self.assertEqual(summary["casos_comparables"], 2)
        self.assertEqual(summary["resultados"], {"exitoso": 1, "parcialmente_exitoso": 1})
        content = json.dumps(summary)
        for private in (self.org_a.nombre, self.org_b.nombre, "documento"):
            self.assertNotIn(private, content)
        self.assertNotIn("organizacion", summary)
        self.assertNotIn("resultado_origen", summary)

    def test_context_gateway_entrega_resumen_compacto(self):
        create_knowledge_case(self.result_a, self.org_a)
        package = ContextGateway().problem(self.result_a.problematica, self.org_a)
        knowledge = package["conocimiento_comparable"]
        self.assertEqual(knowledge["casos_comparables"], 1)
        self.assertIn("no garantiza", knowledge["mensaje"])
        self.assertNotIn("casos", knowledge)
        self.assertNotIn(self.org_a.nombre, json.dumps(knowledge))

    def test_endpoints_privados_aislados_y_agregado_general(self):
        case_a, _ = create_knowledge_case(self.result_a, self.org_a)
        create_knowledge_case(self.result_b, self.org_b)
        base = f"/api/organizaciones/{self.org_a.organizacion_id}/conocimiento"
        own = self.client.get(f"{base}/casos/")
        self.assertEqual(own.status_code, 200); self.assertEqual([row["id"] for row in own.data], [case_a.id])
        self.assertEqual(self.client.get(f"{base}/casos/{self.result_b.casos_conocimiento.first().id}/").status_code, 404)
        aggregate = self.client.get(f"{base}/agregado/?preset=construccion")
        self.assertEqual(aggregate.status_code, 200); self.assertEqual(aggregate.data["casos_comparables"], 2)
        self.assertNotIn("organizacion", json.dumps(aggregate.data))
        post = self.client.post(f"{base}/casos/", {"intervencion": self.result_b.id}, format="json")
        self.assertEqual(post.status_code, 404)

    def test_generar_conocimiento_no_modifica_motor(self):
        counts = (FactorAmbiental.objects.count(), FormulaAmbiental.objects.count())
        create_knowledge_case(self.result_a, self.org_a)
        self.assertEqual((FactorAmbiental.objects.count(), FormulaAmbiental.objects.count()), counts)

    def test_resultados_restantes_se_distinguen(self):
        expected = {"implementada_sin_efecto": "sin_efecto", "negativa": "negativo", "inconclusa": "inconcluso"}
        for state, mapped in expected.items():
            case, _ = create_knowledge_case(self._result(self.org_a, state, f"accion_{state}"), self.org_a)
            self.assertEqual(case.resultado, mapped)
