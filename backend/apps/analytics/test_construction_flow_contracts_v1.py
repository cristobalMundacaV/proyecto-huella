from datetime import date

from django.test import TestCase
from django.utils import timezone

from .models import (
    ActividadOperacional,
    FuenteDatos,
    Obra,
    Observacion,
    Organizacion,
    RegistroFlujoAmbiental,
)
from .policies.construction_flows_v1 import (
    CONSTRUCTION_V1_FLOW_CONTRACTS,
    capture_completeness,
)
from .services.capture import capture_observation


class ConstructionV1FlowContractTests(TestCase):
    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Construction Contracts")
        self.other_organization = Organizacion.objects.create(nombre="Other Contracts")
        self.work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Obra Uno",
            fecha_inicio=date.today(),
        )
        self.other_work = Obra.objects.create(
            organizacion=self.other_organization,
            nombre="Obra Ajena",
            fecha_inicio=date.today(),
        )
        self.source = FuenteDatos.objects.create(
            organizacion=self.organization, nombre="Manual"
        )

    def activity(self, kind, code="FLOW-1", work=None):
        return ActividadOperacional.objects.create(
            organizacion=self.organization,
            obra=work or self.work,
            tipo=kind,
            codigo=code,
            nombre=code,
            timestamp_inicio=timezone.now(),
        )

    def test_catalog_contains_exactly_the_seven_construction_flows(self):
        self.assertEqual(
            set(CONSTRUCTION_V1_FLOW_CONTRACTS),
            {
                "combustibles",
                "maquinaria",
                "transporte",
                "materiales",
                "energia",
                "agua",
                "residuos",
            },
        )

    def test_missing_observation_remains_missing(self):
        activity = self.activity(ActividadOperacional.Tipo.CONSUMO_AGUA)
        RegistroFlujoAmbiental.objects.create(
            organizacion=self.organization,
            actividad=activity,
            flujo=RegistroFlujoAmbiental.Flujo.AGUA,
            periodo_inicio=activity.timestamp_inicio,
            granularidad=RegistroFlujoAmbiental.Granularidad.OBRA,
            obra=self.work,
        )
        status = capture_completeness(activity, CONSTRUCTION_V1_FLOW_CONTRACTS["agua"])
        self.assertEqual(status["estado"], "incompleto")
        self.assertIn("observacion:consumo_agua", status["faltantes"])
        self.assertFalse(activity.observaciones.exists())

    def test_unified_capture_completes_energy_without_calculating(self):
        activity = self.activity(ActividadOperacional.Tipo.CONSUMO_ENERGIA)
        RegistroFlujoAmbiental.objects.create(
            organizacion=self.organization,
            actividad=activity,
            flujo=RegistroFlujoAmbiental.Flujo.ENERGIA,
            periodo_inicio=activity.timestamp_inicio,
            granularidad=RegistroFlujoAmbiental.Granularidad.OBRA,
            obra=self.work,
        )
        capture_observation(
            channel="manual",
            organization=self.organization,
            activity=activity,
            source=self.source,
            concept="consumo_energia",
            numeric_value="100",
            unit="kWh",
            timestamp=activity.timestamp_inicio,
        )
        status = capture_completeness(
            activity, CONSTRUCTION_V1_FLOW_CONTRACTS["energia"]
        )
        self.assertEqual(status["estado"], "completo")
        self.assertEqual(status["elegibilidad_calculo"], "delegada")
        self.assertFalse(hasattr(activity, "calculo_ambiental"))

    def test_rejected_observation_does_not_complete_flow(self):
        activity = self.activity(ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE)
        RegistroFlujoAmbiental.objects.create(
            organizacion=self.organization,
            actividad=activity,
            flujo=RegistroFlujoAmbiental.Flujo.COMBUSTIBLE,
            periodo_inicio=activity.timestamp_inicio,
            granularidad=RegistroFlujoAmbiental.Granularidad.OBRA,
            obra=self.work,
        )
        capture_observation(
            channel="manual",
            organization=self.organization,
            activity=activity,
            source=self.source,
            concept="combustible_consumido",
            numeric_value="20",
            unit="L",
            timestamp=activity.timestamp_inicio,
            state=Observacion.Estado.RECHAZADA,
        )
        status = capture_completeness(
            activity, CONSTRUCTION_V1_FLOW_CONTRACTS["combustibles"]
        )
        self.assertEqual(status["estado"], "incompleto")

    def test_material_lifecycle_is_explicitly_optional(self):
        contract = CONSTRUCTION_V1_FLOW_CONTRACTS["materiales"]
        self.assertTrue(contract.lifecycle_optional)
        self.assertEqual(contract.required_observation_groups, ())

    def test_contract_does_not_read_another_work(self):
        local = self.activity(ActividadOperacional.Tipo.CONSUMO_AGUA, "LOCAL")
        RegistroFlujoAmbiental.objects.create(
            organizacion=self.organization,
            actividad=local,
            flujo=RegistroFlujoAmbiental.Flujo.AGUA,
            periodo_inicio=local.timestamp_inicio,
            granularidad=RegistroFlujoAmbiental.Granularidad.OBRA,
            obra=self.work,
        )
        foreign_activity = ActividadOperacional.objects.create(
            organizacion=self.other_organization,
            obra=self.other_work,
            tipo=ActividadOperacional.Tipo.CONSUMO_AGUA,
            codigo="FOREIGN",
            nombre="Foreign",
            timestamp_inicio=timezone.now(),
        )
        foreign_source = FuenteDatos.objects.create(
            organizacion=self.other_organization, nombre="Foreign"
        )
        capture_observation(
            channel="manual",
            organization=self.other_organization,
            activity=foreign_activity,
            source=foreign_source,
            concept="consumo_agua",
            numeric_value="99",
            unit="m3",
            timestamp=foreign_activity.timestamp_inicio,
        )
        status = capture_completeness(local, CONSTRUCTION_V1_FLOW_CONTRACTS["agua"])
        self.assertEqual(status["estado"], "incompleto")
