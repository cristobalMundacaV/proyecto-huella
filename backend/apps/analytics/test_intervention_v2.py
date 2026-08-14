from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (AccionMejoraAmbiental, ActivoOperacional,
                     AlcanceProblematica, IndicadorAmbiental,
                     IndicadorProblematica, Organizacion, ProblematicaAmbiental,
                     ProcesoOperacional, ResultadoIntervencion,
                     SnapshotValorIndicador, UnidadOperacional,
                     UsuarioOrganizacion, ValorIndicador)
from .services.intervention_v2 import (change_target, escalate_problem,
                                       evaluate_intervention, select_action,
                                       start_action)


class InterventionV2Tests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("intervention-v2", password="test-pass")
        self.org = Organizacion.objects.create(nombre="Intervenciones Uno")
        self.other = Organizacion.objects.create(nombre="Intervenciones Dos")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org)
        self.client.force_login(self.user)
        self.base = f"/api/organizaciones/{self.org.organizacion_id}"
        self.unit = UnidadOperacional.objects.create(organizacion=self.org, nombre="Logistica")
        self.process = ProcesoOperacional.objects.create(organizacion=self.org, unidad=self.unit, nombre="Transporte")
        self.asset = ActivoOperacional.objects.create(organizacion=self.org, codigo="CAM-7", nombre="Camion 7")

    def problem(self, title="Alta intensidad de emisiones en transporte"):
        return ProblematicaAmbiental.objects.create(
            organizacion=self.org, titulo=title, descripcion="Intensidad superior a objetivo", categoria="transporte",
            indicador="intensidad", unidad_indicador="kgCO2e/t", valor_inicial=Decimal("10"), objetivo_meta=Decimal("9"),
            fecha_deteccion=date(2026, 1, 1), estado="detectada", objetivo_ambiental="Reducir intensidad sin ocultar emisiones absolutas",
        )

    def indicator(self, code="intensidad"):
        return IndicadorAmbiental.objects.create(
            organizacion=self.org, codigo=code, nombre="kgCO2e por tonelada", tipo="intensidad", unidad="kgCO2e/t",
            origen_numerador="impactos_ambientales", origen_denominador="masa_transportada_t", direccion_deseable="menor_es_mejor",
        )

    def value(self, indicator, value, month=1, version=1):
        return ValorIndicador.objects.create(
            indicador=indicator, periodo_inicio=date(2026, month, 1), periodo_fin=date(2026, month, 28),
            valor=value, unidad=indicator.unidad, fuente_calculo=f"test-v{version}", version=version,
        )

    def prepare(self, base=Decimal("10"), title="Consolidar cargas"):
        problem = self.problem(); indicator = self.indicator(); self.value(indicator, base)
        link = IndicadorProblematica.objects.create(problematica=problem, indicador=indicator, rol="principal", direccion_deseada="menor_es_mejor", valor_objetivo=Decimal("9"))
        AlcanceProblematica.objects.create(problematica=problem, unidad_operacional=self.unit, proceso_operacional=self.process, activo_operacional=self.asset, indicador=indicator)
        action = AccionMejoraAmbiental.objects.create(problematica=problem, titulo=title, descripcion="Consolidar despachos", justificacion="Reducir viajes parciales")
        return problem, indicator, link, action

    def test_crear_problematica_alcance_compuesto_y_kpi_principal(self):
        problem, indicator, link, _ = self.prepare()
        scope = problem.alcances_v2.get()
        self.assertEqual((scope.unidad_operacional, scope.proceso_operacional, scope.activo_operacional), (self.unit, self.process, self.asset))
        self.assertEqual(link.indicador, indicator); self.assertEqual(link.rol, "principal")

    def test_alcance_e_indicador_cross_tenant_bloqueados_por_api(self):
        problem = self.problem()
        foreign_unit = UnidadOperacional.objects.create(organizacion=self.other, nombre="Ajena")
        foreign_indicator = IndicadorAmbiental.objects.create(organizacion=self.other, codigo="foreign", nombre="Foreign", tipo="absoluto", unidad="kg", origen_numerador="impactos_ambientales")
        self.assertEqual(self.client.post(f"{self.base}/problematicas/{problem.id}/alcance/", {"unidad_operacional": foreign_unit.id}, format="json").status_code, 400)
        self.assertEqual(self.client.post(f"{self.base}/problematicas/{problem.id}/indicadores/", {"indicador": foreign_indicator.id, "direccion_deseada": "menor_es_mejor"}, format="json").status_code, 400)

    def test_seleccionar_crea_base_e_iniciar_congela_scope(self):
        problem, _, _, action = self.prepare()
        cycle = select_action(action, self.user); base = cycle.snapshot_base
        self.assertFalse(base.congelado); self.assertEqual(base.valores.get().valor, Decimal("10"))
        with self.assertRaises(ValidationError): start_action(action, confirmed=False, user=self.user)
        start_action(action, confirmed=True, user=self.user); base.refresh_from_db()
        self.assertTrue(base.congelado); frozen_scope = base.alcance_congelado.copy()
        AlcanceProblematica.objects.create(problematica=problem, activo_operacional=ActivoOperacional.objects.create(organizacion=self.org, codigo="NEW", nombre="Nuevo"))
        base.refresh_from_db(); self.assertEqual(base.alcance_congelado, frozen_scope)
        value = base.valores.get(); value.valor = Decimal("99")
        with self.assertRaises(ValidationError): value.save()

    def test_seguimiento_registra_kpi_y_valor_existente(self):
        problem, indicator, _, action = self.prepare(); select_action(action); start_action(action, confirmed=True)
        tracked = self.value(indicator, Decimal("9.2"), month=2)
        response = self.client.post(f"{self.base}/problematicas/{problem.id}/seguimientos/", {
            "accion": action.id, "fecha": timezone.localdate().isoformat(), "indicador_v2": indicator.id, "valor_indicador": tracked.id,
            "valor": "9.2", "unidad": "kgCO2e/t", "fuente": "serie_indicador", "referencia": "mes-2",
        }, format="json")
        self.assertEqual(response.status_code, 201); self.assertEqual(response.data["valor_indicador"], tracked.id)

    def test_caso_obligatorio_resultado_positivo_menos_16_por_ciento(self):
        problem, indicator, _, action = self.prepare(); cycle = select_action(action); start_action(action, confirmed=True)
        self.value(indicator, Decimal("8.4"), month=2)
        result = evaluate_intervention(problem)
        self.assertEqual(result.estado, "positiva"); self.assertEqual(result.snapshot_base, cycle.snapshot_base)
        self.assertEqual(Decimal(result.metricas_comparadas[0]["porcentaje"]), Decimal("-16.00"))
        self.assertTrue(result.snapshot_resultado.congelado)

    def test_resultado_negativo_se_conserva(self):
        problem, indicator, _, action = self.prepare(); select_action(action); start_action(action, confirmed=True)
        self.value(indicator, Decimal("10.8"), month=2)
        result = evaluate_intervention(problem)
        self.assertEqual(result.estado, "negativa"); self.assertTrue(ResultadoIntervencion.objects.filter(pk=result.pk).exists())
        self.assertEqual(Decimal(result.metricas_comparadas[0]["porcentaje"]), Decimal("8.00"))

    def test_inconclusa_y_solo_kpis_asociados_participan(self):
        problem = self.problem(); indicator = self.indicator(); unrelated = self.indicator("unrelated")
        IndicadorProblematica.objects.create(problematica=problem, indicador=indicator, direccion_deseada="menor_es_mejor")
        self.value(unrelated, 999)
        action = AccionMejoraAmbiental.objects.create(problematica=problem, titulo="Sin datos", descripcion="Prueba")
        select_action(action); start_action(action, confirmed=True)
        result = evaluate_intervention(problem)
        self.assertEqual(result.estado, "inconclusa"); self.assertEqual(result.metricas_comparadas, [])

    def test_segundo_ciclo_no_sobrescribe_primero(self):
        problem, indicator, _, action = self.prepare(); first = select_action(action); start_action(action, confirmed=True)
        self.value(indicator, Decimal("10.8"), month=2); first_result = evaluate_intervention(problem)
        second = select_action(action); self.assertEqual(second.numero, 2); self.assertNotEqual(first.snapshot_base_id, second.snapshot_base_id)
        first_result.refresh_from_db(); self.assertEqual(first_result.estado, "negativa")

    def test_maximo_tres_ciclos_cuarto_bloqueado_y_escalamiento(self):
        problem, indicator, _, action = self.prepare()
        for number in range(1, 4):
            select_action(action); start_action(action, confirmed=True)
            self.value(indicator, Decimal("10") + number, month=number + 1)
            evaluate_intervention(problem)
        with self.assertRaises(ValidationError): select_action(action)
        escalated = escalate_problem(problem, "Tres ciclos sin resolucion", self.user)
        self.assertEqual(escalated.estado, "escalada_profesional"); self.assertTrue(escalated.requiere_evaluacion_profesional)
        self.assertEqual(problem.ciclos_reevaluacion.count(), 3)

    def test_cambio_meta_exige_justificacion_y_genera_historial(self):
        problem, _, link, _ = self.prepare()
        with self.assertRaises(ValidationError): change_target(link, Decimal("8"), "", "ajuste", self.user)
        history = change_target(link, Decimal("8"), "Nueva exigencia tecnica", "Revision normativa", self.user)
        link.refresh_from_db(); self.assertEqual(link.valor_objetivo, Decimal("8")); self.assertEqual(history.problematica, problem)

    def test_endpoints_workspace_y_tenant_isolation(self):
        problem, _, _, action = self.prepare()
        selected = self.client.post(f"{self.base}/problematicas/{problem.id}/acciones/{action.id}/seleccionar/", {}, format="json")
        self.assertEqual(selected.status_code, 201)
        self.assertEqual(self.client.get(f"{self.base}/problematicas/{problem.id}/snapshot-base/").status_code, 200)
        self.assertEqual(self.client.post(f"{self.base}/problematicas/{problem.id}/acciones/{action.id}/iniciar/", {"confirmado": True}, format="json").status_code, 200)
        foreign = ProblematicaAmbiental.objects.create(organizacion=self.other, titulo="Foreign", descripcion="x", categoria="x", valor_inicial=1, objetivo_meta=0, fecha_deteccion=timezone.localdate())
        self.assertEqual(self.client.get(f"{self.base}/problematicas/{foreign.id}/ciclos/").status_code, 404)
