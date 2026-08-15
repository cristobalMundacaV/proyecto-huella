from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (ActividadOperacional, CalculoAmbiental, CompatibilidadVersionMetodologia,
                     FactorAmbiental, FormulaAmbiental, FuenteDatos, MetodologiaAmbiental,
                     Observacion, Organizacion, UsuarioOrganizacion, VariableFormula,
                     VersionFactorAmbiental, VersionMetodologia)
from .services.calculation_v2 import calculate_activity, recalculate
from .services.methodology_governance import structural_errors, transition_version
from .services.methodology_selector import select_methodology


class MethodologyGovernanceV1Tests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("method-admin", password="test", is_staff=True)
        self.member = User.objects.create_user("method-member", password="test")
        self.org = Organizacion.objects.create(nombre="Gobernanza Uno")
        self.other = Organizacion.objects.create(nombre="Gobernanza Dos")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org)
        UsuarioOrganizacion.objects.create(user=self.member, organizacion=self.org)
        self.client.force_login(self.user)
        self.base = f"/api/organizaciones/{self.org.organizacion_id}"
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Fuente trazable")
        self.activity = ActividadOperacional.objects.create(
            organizacion=self.org, codigo="T-14", nombre="Transporte gobernado", tipo="transporte",
            timestamp_inicio=timezone.now(),
        )

    def method(self, *, state="borrador", organization=None, applicability=None, priority=10,
               result_type="emision", source="Referencia técnica de prueba"):
        organization = self.org if organization is None else organization
        factor = FactorAmbiental.objects.create(
            organizacion=organization, codigo=f"factor-{FactorAmbiental.objects.count()}", nombre="Factor de prueba",
            categoria="transporte", unidad_entrada="t.km", unidad_resultado="kgCO2e",
        )
        VersionFactorAmbiental.objects.create(
            factor=factor, version=1, valor=Decimal("0.10"), fuente="Fuente de factor de prueba", estado="activo",
        )
        method = MetodologiaAmbiental.objects.create(
            organizacion=organization, codigo=f"met-{MetodologiaAmbiental.objects.count()}", nombre="Método gobernado",
            categoria="transporte", flujo="transporte_tkm",
        )
        version = VersionMetodologia.objects.create(
            metodologia=method, version=1, fuente_referencia=source,
            aplicabilidad=applicability or {"tipos_actividad": ["transporte"]}, prioridad=priority,
            tipo_resultado=result_type,
        )
        formula = FormulaAmbiental.objects.create(
            version_metodologia=version, factor_ambiental=factor, codigo="producto-transporte",
            tipo="transporte_tkm", expresion_legible="masa x distancia x factor",
        )
        VariableFormula.objects.create(formula=formula, clave="masa", concepto_observacion="masa_transportada_t", unidad_esperada="t")
        VariableFormula.objects.create(formula=formula, clave="distancia", concepto_observacion="distancia_recorrida_km", unidad_esperada="km")
        if state != "borrador": VersionMetodologia.objects.filter(pk=version.pk).update(estado=state); version.refresh_from_db()
        return version

    def observe(self, concept, value, unit):
        return Observacion.objects.create(
            organizacion=self.org, actividad=self.activity, fuente=self.source, concepto=concept,
            valor_numerico=value, unidad=unit, timestamp_observacion=timezone.now(), estado="validada",
        )

    def test_lifecycle_only_allows_explicit_sequence(self):
        version = self.method()
        with self.assertRaises(ValidationError): transition_version(version, "activa", self.user)
        transition_version(version, "pruebas", self.user)
        transition_version(version, "validada", self.user)
        transition_version(version, "activa", self.user)
        transition_version(version, "obsoleta", self.user)
        self.assertEqual(version.estado, "obsoleta")

    def test_activation_requires_formula_variables_reference_and_factor(self):
        version = self.method(source="")
        self.assertTrue(any("referencia" in row.lower() for row in structural_errors(version)))
        transition_version(version, "pruebas", self.user)
        with self.assertRaises(ValidationError): transition_version(version, "validada", self.user)

    def test_critical_complementary_and_optional_semantics(self):
        version = self.method(state="activa")
        VariableFormula.objects.filter(formula=version.formula, clave="masa").update(criticidad="complementaria", obligatoria=False)
        self.observe("distancia_recorrida_km", "10", "km")
        selection = select_methodology(self.activity)
        self.assertEqual(selection["seleccion"]["elegibilidad"]["estado"], "calculable_incompleto")
        self.assertTrue(selection["seleccion"]["elegibilidad"]["advertencias"])

    def test_applicability_priority_and_private_tenant_isolation(self):
        lower = self.method(state="activa", priority=20)
        preferred = self.method(state="activa", priority=5)
        self.method(state="activa", organization=self.other, priority=1)
        self.observe("masa_transportada_t", "2", "t"); self.observe("distancia_recorrida_km", "5", "km")
        selected = select_methodology(self.activity)["seleccion"]["version_metodologia"]
        self.assertEqual(selected, preferred); self.assertNotEqual(selected, lower)

    def test_non_applicable_and_missing_method_are_explicit(self):
        self.method(state="activa", applicability={"tipos_actividad": ["energia"]})
        selection = select_methodology(self.activity)
        self.assertIsNone(selection["seleccion"])
        self.assertEqual(selection["candidatos"][0]["estado"], "no_aplicable")

    def test_unit_mismatch_and_ambiguity_do_not_calculate(self):
        self.method(state="activa")
        self.observe("masa_transportada_t", "2", "kg")
        self.observe("distancia_recorrida_km", "5", "km")
        self.observe("distancia_recorrida_km", "6", "km")
        selection = select_methodology(self.activity)
        self.assertIsNone(selection["seleccion"])
        self.assertIn(selection["candidatos"][0]["estado"], {"no_calculable", "requiere_revision"})

    def test_snapshot_and_recalculation_preserve_history(self):
        self.method(state="activa")
        distance = self.observe("distancia_recorrida_km", "5", "km")
        self.observe("masa_transportada_t", "2", "t")
        original, _ = calculate_activity(self.activity)
        newer, _ = recalculate(original, "Nueva corrida controlada")
        original.refresh_from_db()
        self.assertEqual(newer.recalculo_de, original)
        self.assertEqual(newer.motivo_recalculo, "Nueva corrida controlada")
        self.assertEqual(original.snapshot_tecnico["inputs"][1]["observacion_id"], distance.id)
        self.assertEqual(CalculoAmbiental.objects.count(), 2)

    def test_reduction_requires_strong_context(self):
        self.method(state="activa", result_type="reduccion")
        self.observe("masa_transportada_t", "2", "t"); self.observe("distancia_recorrida_km", "5", "km")
        with self.assertRaises(ValidationError): calculate_activity(self.activity)
        context = {"referencia": "BASE-1", "metodo": "comparación", "evidencia": "EV-1", "periodo": "2026-01", "alcance": "obra"}
        calculation, _ = calculate_activity(self.activity, result_context=context)
        self.assertEqual(calculation.tipo_resultado, "reduccion")
        self.assertEqual(calculation.snapshot_tecnico["contexto_resultado"], context)

    def test_compatibility_is_explicit_and_unique(self):
        first = self.method(); second = VersionMetodologia.objects.create(
            metodologia=first.metodologia, version=2, fuente_referencia="segunda")
        relation = CompatibilidadVersionMetodologia.objects.create(
            version_origen=first, version_destino=second, estado="requiere_revision", detalle="Cambió alcance")
        self.assertEqual(relation.estado, "requiere_revision")

    def test_api_permissions_global_and_calculation_immutability(self):
        version = self.method(state="activa")
        self.observe("masa_transportada_t", "2", "t"); self.observe("distancia_recorrida_km", "5", "km")
        calculation, _ = calculate_activity(self.activity)
        calculation.resultado = Decimal("0")
        with self.assertRaises(ValidationError): calculation.save()
        self.client.force_login(self.member)
        response = self.client.post(f"{self.base}/metodologias/{version.metodologia_id}/", {}, format="json")
        self.assertEqual(response.status_code, 403)
        foreign_base = f"/api/organizaciones/{self.other.organizacion_id}"
        self.assertEqual(self.client.get(f"{foreign_base}/metodologias/").status_code, 404)

    def test_recalculation_and_snapshot_endpoints(self):
        self.method(state="activa")
        self.observe("masa_transportada_t", "2", "t"); self.observe("distancia_recorrida_km", "5", "km")
        calculation, _ = calculate_activity(self.activity)
        snapshot = self.client.get(f"{self.base}/calculos/{calculation.id}/snapshot/")
        self.assertEqual(snapshot.status_code, 200); self.assertIn("version_factor_id", snapshot.data)
        response = self.client.post(f"{self.base}/calculos/{calculation.id}/recalcular/", {"motivo": "Nueva fuente"}, format="json")
        self.assertEqual(response.status_code, 201)
