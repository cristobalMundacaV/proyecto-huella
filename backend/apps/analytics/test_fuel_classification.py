from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import (
    ActividadOperacional,
    AreaOperacional,
    EspacioTrabajoOperacional,
    FactorAmbiental,
    FormulaAmbiental,
    FuenteDatos,
    MetodologiaAmbiental,
    Obra,
    Organizacion,
    RegistroFlujoAmbiental,
    UsuarioOrganizacion,
    VariableFormula,
    VersionFactorAmbiental,
    VersionMetodologia,
)
from .services.eligibility_v2 import evaluate_formula
from .services.fuel_classification import classify_fuel
from .services.unit_conversion import convert_value


class FuelClassificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("fuel-classifier", password="test-pass")
        self.organization = Organizacion.objects.create(nombre="Clasificación combustible")
        membership = UsuarioOrganizacion.objects.create(
            user=self.user,
            organizacion=self.organization,
            rol=UsuarioOrganizacion.Rol.OPERADOR,
        )
        self.work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Obra combustible",
            fecha_inicio="2026-08-26",
        )
        area = AreaOperacional.objects.create(
            organizacion=self.organization,
            nombre="Operación",
        )
        self.workspace = EspacioTrabajoOperacional.objects.create(
            usuario_organizacion=membership,
            area=area,
            obra=self.work,
        )
        self.source = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Vale de combustible",
            tipo=FuenteDatos.Tipo.MANUAL,
        )
        self.client.force_login(self.user)
        self.url = (
            f"/api/organizaciones/{self.organization.organizacion_id}/"
            "flujos-ambientales/registro-manual/"
        )

    def post_fuel(self, destination, **overrides):
        payload = {
            "obra": self.work.id,
            "tipo_actividad": ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE_ESTACIONARIO,
            "codigo_actividad": f"manual-combustibles-{destination}",
            "nombre_actividad": "Registro manual · combustibles",
            "flujo": RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO,
            "periodo_inicio": "2026-08-26T12:00:00",
            "concepto": "combustible_consumido",
            "valor_numerico": "20",
            "unidad": "L",
            "fuente": self.source.id,
            "tipo_recurso": "diesel",
            "destino_operacional": destination,
        }
        payload.update(overrides)
        return self.client.post(
            self.url,
            payload,
            format="multipart",
            HTTP_X_WORKSPACE_ID=str(self.workspace.id),
        )

    def test_generator_is_stationary(self):
        result = classify_fuel("generador")
        self.assertEqual(result["estado"], "clasificado")
        self.assertEqual(result["categoria"], "combustion_estacionaria")
        self.assertEqual(result["alcance"], 1)

    def test_heating_is_stationary(self):
        self.assertEqual(
            classify_fuel("calefaccion")["categoria"],
            "combustion_estacionaria",
        )

    def test_vehicle_is_mobile(self):
        self.assertEqual(classify_fuel("vehiculo")["categoria"], "combustion_movil")

    def test_machinery_requires_classification(self):
        self.assertEqual(
            classify_fuel("maquinaria")["estado"],
            "requiere_clasificacion",
        )

    def test_small_equipment_requires_classification(self):
        self.assertEqual(
            classify_fuel("equipo_menor")["estado"],
            "requiere_clasificacion",
        )

    def test_other_requires_classification(self):
        self.assertEqual(classify_fuel("otro")["estado"], "requiere_clasificacion")

    def test_classifier_does_not_modify_observation_value_or_unit(self):
        response = self.post_fuel("generador")
        self.assertEqual(response.status_code, 201, response.data)
        observation = ActividadOperacional.objects.get().observaciones.get()

        classify_fuel("generador")
        observation.refresh_from_db()

        self.assertEqual(observation.valor_numerico, Decimal("20"))
        self.assertEqual(observation.unidad, "L")

    def test_generator_keeps_liters_and_normalizes_to_cubic_meters(self):
        response = self.post_fuel("generador")
        self.assertEqual(response.status_code, 201, response.data)
        record = RegistroFlujoAmbiental.objects.get()
        observation = record.actividad.observaciones.get()

        normalized = convert_value(observation.valor_numerico, observation.unidad, "m3")

        self.assertEqual(record.flujo, RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO)
        self.assertEqual(record.metadata["clasificacion_ambiental"]["categoria"], "combustion_estacionaria")
        self.assertEqual(normalized["valor_normalizado"], Decimal("0.020"))

    def test_vehicle_is_persisted_as_mobile(self):
        response = self.post_fuel("vehiculo")
        self.assertEqual(response.status_code, 201, response.data)
        record = RegistroFlujoAmbiental.objects.get()

        self.assertEqual(record.flujo, RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_MOVIL)
        self.assertEqual(record.actividad.tipo, ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE)
        self.assertEqual(record.metadata["clasificacion_ambiental"]["categoria"], "combustion_movil")

    def test_machinery_blocks_eligibility(self):
        response = self.post_fuel("maquinaria")
        self.assertEqual(response.status_code, 201, response.data)
        record = RegistroFlujoAmbiental.objects.get()
        factor = FactorAmbiental.objects.create(
            codigo="fuel-classification-test",
            nombre="Factor de prueba",
            categoria="combustibles",
            unidad_entrada="m3",
            unidad_resultado="tCO2e",
        )
        VersionFactorAmbiental.objects.create(
            factor=factor,
            version=1,
            valor="2.71",
            fuente="PRUEBA",
            estado=VersionFactorAmbiental.Estado.ACTIVO,
        )
        methodology = MetodologiaAmbiental.objects.create(
            codigo="fuel-classification-method",
            nombre="Método de prueba",
            categoria="combustibles",
            flujo="combustible",
        )
        version = VersionMetodologia.objects.create(
            metodologia=methodology,
            version=1,
            estado=VersionMetodologia.Estado.BORRADOR,
        )
        formula = FormulaAmbiental.objects.create(
            version_metodologia=version,
            factor_ambiental=factor,
            codigo="fuel-classification-formula",
            tipo=FormulaAmbiental.Tipo.TRANSPORTE_COMBUSTIBLE,
            expresion_legible="combustible x factor",
        )
        VariableFormula.objects.create(
            formula=formula,
            clave="combustible",
            concepto_observacion="combustible_consumido",
            unidad_esperada="m3",
        )

        eligibility = evaluate_formula(record.actividad, formula)

        self.assertEqual(record.flujo, RegistroFlujoAmbiental.Flujo.COMBUSTIBLE)
        self.assertEqual(eligibility["estado"], "no_calculable")
        self.assertIn(
            "El uso del combustible requiere clasificación como fuente móvil o estacionaria antes de calcular emisiones.",
            eligibility["motivos"],
        )

    def test_client_flow_cannot_force_incompatible_category(self):
        response = self.post_fuel(
            "vehiculo",
            flujo=RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO,
        )
        self.assertEqual(response.status_code, 201, response.data)
        record = RegistroFlujoAmbiental.objects.get()

        self.assertEqual(record.flujo, RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_MOVIL)
        self.assertEqual(
            record.metadata["flujo_declarado_cliente"],
            RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO,
        )

    def test_historical_contradiction_requires_review_without_mutation(self):
        result = classify_fuel(
            "vehiculo",
            declared_flow=RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO,
        )

        self.assertEqual(result["estado"], "requiere_revision")
        self.assertEqual(result["categoria"], "combustion_movil")
