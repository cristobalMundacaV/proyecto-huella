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
    ActivoOperacional,
    AreaOperacional,
    EspacioTrabajoOperacional,
    EvidenciaObra,
    FuenteDatos,
    Obra,
    Observacion,
    Organizacion,
    ProcesoOperacional,
    UnidadOperacional,
    UsuarioOrganizacion,
    VersionEvidencia,
)
from .models import assets, operational_context, operational_data, provenance
from .policies.activity_core import activity_relation_errors


class OperationalKernelContractTests(TestCase):
    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Kernel Uno")
        self.other_organization = Organizacion.objects.create(nombre="Kernel Dos")
        self.work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Obra Uno",
            fecha_inicio=date.today(),
        )
        self.unit = UnidadOperacional.objects.create(
            organizacion=self.organization, nombre="Unidad Uno"
        )
        self.process = ProcesoOperacional.objects.create(
            organizacion=self.organization, unidad=self.unit, nombre="Proceso Uno"
        )
        self.asset = ActivoOperacional.objects.create(
            organizacion=self.organization, codigo="ACT-1", nombre="Activo Uno"
        )
        self.source = FuenteDatos.objects.create(
            organizacion=self.organization, nombre="Fuente Uno"
        )
        self.activity = ActividadOperacional.objects.create(
            organizacion=self.organization,
            obra=self.work,
            unidad_operacional=self.unit,
            proceso_operacional=self.process,
            codigo="ACTIVITY-1",
            nombre="Actividad Uno",
            timestamp_inicio=timezone.now(),
        )

    def evidence(self, organization, name):
        return EvidenciaObra.objects.create(
            organizacion=organization,
            archivo=SimpleUploadedFile(f"{name}.txt", b"evidence"),
            nombre=name,
        )

    def version(self, evidence, version=1):
        return VersionEvidencia.objects.create(
            evidencia=evidence,
            organizacion=evidence.organizacion,
            version=version,
            archivo=SimpleUploadedFile(f"v{version}.txt", b"version"),
            nombre_original=f"v{version}.txt",
            checksum_sha256=str(version) * 64,
        )

    def test_kernel_model_modules_do_not_depend_on_downstream_or_legacy_layers(self):
        forbidden = ("legacy", "calculations", "environmental_flows", "intelligence")
        for module in (operational_context, assets, operational_data, provenance):
            tree = ast.parse(inspect.getsource(module))
            imports = {
                node.module or ""
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            }
            self.assertFalse(
                any(name.endswith(forbidden) for name in imports), module.__name__
            )

    def test_canonical_identity_constraints_are_tenant_scoped(self):
        expected = {
            FuenteDatos: ("organizacion", "nombre"),
            ActividadOperacional: ("organizacion", "codigo"),
            ActivoOperacional: ("organizacion", "codigo"),
            AreaOperacional: ("organizacion", "nombre"),
            VersionEvidencia: ("evidencia", "version"),
        }
        for model, fields in expected.items():
            constraints = {
                tuple(constraint.fields) for constraint in model._meta.constraints
            }
            self.assertIn(fields, constraints, model.__name__)

    def test_activity_rejects_cross_tenant_context_and_assets(self):
        foreign_unit = UnidadOperacional.objects.create(
            organizacion=self.other_organization, nombre="Unidad Ajena"
        )
        self.activity.unidad_operacional = foreign_unit
        with self.assertRaises(ValidationError):
            self.activity.full_clean()
        self.assertIsNotNone(
            activity_relation_errors(
                organization=self.organization,
                assets=[
                    ActivoOperacional.objects.create(
                        organizacion=self.other_organization,
                        codigo="FOREIGN",
                        nombre="Activo Ajeno",
                    )
                ],
            )
        )

    def test_observation_is_atomic_and_provenance_is_tenant_consistent(self):
        evidence = self.evidence(self.organization, "evidence")
        version = self.version(evidence)
        observation = Observacion(
            organizacion=self.organization,
            actividad=self.activity,
            fuente=self.source,
            concepto="consumo_combustible",
            valor_numerico="10",
            timestamp_observacion=timezone.now(),
            evidencia=evidence,
            version_evidencia=version,
        )
        observation.full_clean()

        observation.valor_texto = "diez"
        with self.assertRaises(ValidationError):
            observation.full_clean()

        foreign_evidence = self.evidence(self.other_organization, "foreign")
        observation.valor_texto = ""
        observation.evidencia = foreign_evidence
        with self.assertRaises(ValidationError):
            observation.full_clean()

    def test_workspace_and_evidence_version_reject_cross_tenant_context(self):
        user = User.objects.create_user("kernel-user")
        membership = UsuarioOrganizacion.objects.create(
            user=user, organizacion=self.organization
        )
        foreign_area = AreaOperacional.objects.create(
            organizacion=self.other_organization, nombre="Area Ajena"
        )
        workspace = EspacioTrabajoOperacional(
            usuario_organizacion=membership, area=foreign_area
        )
        with self.assertRaises(ValidationError):
            workspace.full_clean()

        evidence = self.evidence(self.organization, "local")
        foreign_version = VersionEvidencia(
            evidencia=evidence,
            organizacion=self.other_organization,
            version=1,
            archivo=SimpleUploadedFile("foreign-version.txt", b"version"),
            nombre_original="foreign-version.txt",
            checksum_sha256="f" * 64,
        )
        with self.assertRaises(ValidationError):
            foreign_version.full_clean()
