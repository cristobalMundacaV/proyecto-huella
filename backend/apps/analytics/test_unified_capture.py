import ast
import inspect
from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from .models import (
    ActividadOperacional,
    EvidenciaObra,
    FuenteDatos,
    Obra,
    Observacion,
    Organizacion,
    VersionEvidencia,
)
from .policies import capture as capture_policy
from .services import capture as capture_service
from .services.capture import capture_observation


class UnifiedCaptureContractTests(TestCase):
    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Capture Uno")
        self.other_organization = Organizacion.objects.create(nombre="Capture Dos")
        self.work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Obra Capture",
            fecha_inicio=date.today(),
        )
        self.activity = ActividadOperacional.objects.create(
            organizacion=self.organization,
            obra=self.work,
            codigo="CAP-1",
            nombre="Captura",
            timestamp_inicio=timezone.now(),
        )
        self.manual_source = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Formulario manual",
            tipo=FuenteDatos.Tipo.MANUAL,
        )
        self.sensor_source = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Sensor S-1",
            tipo=FuenteDatos.Tipo.SENSOR,
        )
        self.actor = User.objects.create_user("capture-user")
        self.evidence = EvidenciaObra.objects.create(
            organizacion=self.organization,
            obra=self.work,
            archivo=SimpleUploadedFile("capture.csv", b"value"),
            nombre="capture.csv",
        )
        self.version = VersionEvidencia.objects.create(
            evidencia=self.evidence,
            organizacion=self.organization,
            version=1,
            archivo=SimpleUploadedFile("capture-v1.csv", b"value"),
            nombre_original="capture.csv",
            checksum_sha256="a" * 64,
        )

    def test_channels_converge_on_canonical_observation(self):
        manual = capture_observation(
            channel="manual",
            organization=self.organization,
            activity=self.activity,
            source=self.manual_source,
            concept="consumo",
            numeric_value="10",
            unit="L",
            timestamp=timezone.now(),
            actor=self.actor,
        )
        document = capture_observation(
            channel="document",
            organization=self.organization,
            activity=self.activity,
            source=self.manual_source,
            concept="consumo",
            numeric_value="11",
            unit="L",
            timestamp=timezone.now(),
            evidence=self.evidence,
            evidence_version=self.version,
        )
        sensor = capture_observation(
            channel="sensor",
            organization=self.organization,
            activity=self.activity,
            source=self.sensor_source,
            concept="consumo",
            numeric_value="12",
            unit="L",
            timestamp=timezone.now(),
            state=Observacion.Estado.VALIDADA,
        )

        self.assertEqual(Observacion.objects.count(), 3)
        self.assertEqual(manual.actor, self.actor)
        self.assertEqual(document.version_evidencia, self.version)
        self.assertEqual(sensor.naturaleza, Observacion.Naturaleza.INSTRUMENTAL)
        self.assertTrue(
            all(row.actividad == self.activity for row in (manual, document, sensor))
        )

    def test_document_capture_requires_provenance(self):
        with self.assertRaises(ValidationError):
            capture_observation(
                channel="document",
                organization=self.organization,
                source=self.manual_source,
                concept="consumo",
                numeric_value="10",
                timestamp=timezone.now(),
            )
        self.assertFalse(Observacion.objects.exists())

    def test_sensor_capture_requires_technical_source(self):
        with self.assertRaises(ValidationError):
            capture_observation(
                channel="sensor",
                organization=self.organization,
                source=self.manual_source,
                concept="nivel",
                numeric_value="10",
                timestamp=timezone.now(),
            )

    def test_capture_rejects_cross_tenant_relations_atomically(self):
        foreign_source = FuenteDatos.objects.create(
            organizacion=self.other_organization, nombre="Foreign"
        )
        with self.assertRaises(ValidationError):
            capture_observation(
                channel="manual",
                organization=self.organization,
                activity=self.activity,
                source=foreign_source,
                concept="consumo",
                numeric_value="10",
                timestamp=timezone.now(),
            )
        self.assertFalse(Observacion.objects.exists())

    def test_capture_boundary_has_no_downstream_or_legacy_dependency(self):
        forbidden = ("legacy", "calculations", "environmental_flows", "intelligence")
        for module in (capture_policy, capture_service):
            tree = ast.parse(inspect.getsource(module))
            imports = {
                node.module or ""
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            }
            self.assertFalse(any(name.endswith(forbidden) for name in imports))
