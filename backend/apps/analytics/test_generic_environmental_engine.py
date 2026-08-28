import ast
import inspect
from datetime import date

from django.test import TestCase
from django.utils import timezone

from .models import (
    ActividadOperacional,
    CalculoAmbiental,
    FuenteDatos,
    Obra,
    Organizacion,
    RegistroFlujoAmbiental,
)
from .selectors.environmental_engine import environmental_activity_for_organization
from .services import generic_environmental_engine
from .services.capture import capture_observation
from .services.construction_environment_adapter import project_construction_activity


class GenericEnvironmentalEngineTests(TestCase):
    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Engine Uno")
        self.other_organization = Organizacion.objects.create(nombre="Engine Dos")
        self.work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Obra Engine",
            fecha_inicio=date.today(),
        )
        self.source = FuenteDatos.objects.create(
            organizacion=self.organization, nombre="Manual"
        )

    def activity(self, kind, code="ENGINE-1"):
        return ActividadOperacional.objects.create(
            organizacion=self.organization,
            obra=self.work,
            tipo=kind,
            codigo=code,
            nombre=code,
            timestamp_inicio=timezone.now(),
        )

    def flow_record(self, activity, flow, **values):
        return RegistroFlujoAmbiental.objects.create(
            organizacion=self.organization,
            actividad=activity,
            flujo=flow,
            periodo_inicio=activity.timestamp_inicio,
            granularidad=RegistroFlujoAmbiental.Granularidad.OBRA,
            obra=self.work,
            **values,
        )

    def test_energy_projection_is_traceable_and_does_not_calculate(self):
        activity = self.activity(ActividadOperacional.Tipo.CONSUMO_ENERGIA)
        record = self.flow_record(activity, RegistroFlujoAmbiental.Flujo.ENERGIA)
        observation = capture_observation(
            channel="manual",
            organization=self.organization,
            activity=activity,
            source=self.source,
            concept="consumo_energia",
            numeric_value="100",
            unit="kWh",
            timestamp=activity.timestamp_inicio,
        )
        projection = project_construction_activity(
            activity, "energia", include_eligibility=False
        )
        self.assertEqual(projection["capture"]["estado"], "completo")
        self.assertEqual(projection["classification"]["category"], "energia")
        self.assertEqual(projection["environmental_context"]["record_id"], record.id)
        self.assertEqual(projection["provenance"][0]["observation_id"], observation.id)
        self.assertIsNone(projection["calculation"])
        self.assertFalse(CalculoAmbiental.objects.exists())

    def test_missing_water_value_is_explained_without_invention(self):
        activity = self.activity(ActividadOperacional.Tipo.CONSUMO_AGUA)
        self.flow_record(activity, RegistroFlujoAmbiental.Flujo.AGUA)
        projection = project_construction_activity(
            activity, "agua", include_eligibility=False
        )
        self.assertEqual(projection["capture"]["estado"], "incompleto")
        self.assertIn("observacion:consumo_agua", projection["capture"]["faltantes"])
        self.assertEqual(projection["provenance"], [])

    def test_ambiguous_fuel_remains_unclassified(self):
        activity = self.activity(ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE)
        self.flow_record(
            activity,
            RegistroFlujoAmbiental.Flujo.COMBUSTIBLE,
            destino_operacional=RegistroFlujoAmbiental.DestinoOperacional.MAQUINARIA,
        )
        projection = project_construction_activity(
            activity, "combustibles", include_eligibility=False
        )
        self.assertEqual(
            projection["classification"]["state"], "requiere_clasificacion"
        )
        self.assertIsNone(projection["classification"]["category"])

    def test_selector_never_crosses_tenant_or_work(self):
        activity = self.activity(ActividadOperacional.Tipo.CONSUMO_AGUA)
        self.assertTrue(
            environmental_activity_for_organization(
                self.organization, activity.id, self.work
            ).exists()
        )
        self.assertFalse(
            environmental_activity_for_organization(
                self.other_organization, activity.id
            ).exists()
        )

    def test_generic_engine_has_no_legacy_or_calculation_mutation(self):
        tree = ast.parse(inspect.getsource(generic_environmental_engine))
        imports = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertFalse(any(name.endswith("legacy") for name in imports))
        self.assertFalse(calls & {"save", "create", "update", "delete", "bulk_create"})
