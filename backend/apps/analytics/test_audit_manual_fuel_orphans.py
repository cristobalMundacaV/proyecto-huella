from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import (
    ActividadOperacional,
    EvidenciaObra,
    FuenteDatos,
    Obra,
    Observacion,
    Organizacion,
    RegistroFlujoAmbiental,
)


class AuditManualFuelOrphansCommandTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._media_directory = TemporaryDirectory()
        cls._media_settings = override_settings(MEDIA_ROOT=cls._media_directory.name)
        cls._media_settings.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_settings.disable()
        cls._media_directory.cleanup()

    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Auditoría combustible")
        self.work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Obra auditada",
            fecha_inicio="2026-08-25",
        )
        self.source = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Registro manual",
            tipo=FuenteDatos.Tipo.MANUAL,
        )

    def evidence(self, name, metadata=None):
        return EvidenciaObra.objects.create(
            organizacion=self.organization,
            obra=self.work,
            nombre=name,
            archivo=SimpleUploadedFile(f"{name}.txt", b"respaldo"),
            metadata_extraccion=metadata or {},
        )

    def fuel_metadata(self, **overrides):
        metadata = {
            "registro_manual": True,
            "origen_operacional": True,
            "flujo": RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO,
        }
        metadata.update(overrides)
        return metadata

    def run_command(self, **options):
        output = StringIO()
        call_command(
            "audit_manual_fuel_orphans",
            organization=str(self.organization.organizacion_id),
            stdout=output,
            **options,
        )
        return output.getvalue()

    def test_evidencia_manual_operacional_de_combustible_aparece(self):
        candidate = self.evidence("candidato-combustible", self.fuel_metadata())

        output = self.run_command()

        self.assertIn(f"id={candidate.id}", output)
        self.assertIn("candidato-combustible", output)

    def test_evidencia_documental_generica_no_aparece(self):
        generic = self.evidence("documento-generico")

        output = self.run_command()

        self.assertNotIn(f"id={generic.id}", output)
        self.assertNotIn("documento-generico", output)

    def test_evidencia_no_operacional_no_aparece(self):
        evidence = self.evidence(
            "manual-no-operacional",
            self.fuel_metadata(origen_operacional=False),
        )

        output = self.run_command()

        self.assertNotIn(f"id={evidence.id}", output)

    def test_evidencia_vinculada_a_observacion_no_aparece(self):
        evidence = self.evidence("combustible-vinculado", self.fuel_metadata())
        activity = ActividadOperacional.objects.create(
            organizacion=self.organization,
            obra=self.work,
            tipo=ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE_ESTACIONARIO,
            codigo="manual-combustibles-vinculado",
            nombre="Combustible vinculado",
            timestamp_inicio=timezone.now(),
        )
        Observacion.objects.create(
            organizacion=self.organization,
            actividad=activity,
            fuente=self.source,
            concepto="combustible_consumido",
            valor_numerico=10,
            unidad="L",
            timestamp_observacion=timezone.now(),
            evidencia=evidence,
        )

        output = self.run_command()

        self.assertNotIn(f"id={evidence.id}", output)

    def test_solo_el_flujo_combustible_aparece(self):
        fuel = self.evidence("flujo-combustible", self.fuel_metadata())
        energy = self.evidence(
            "flujo-energia",
            self.fuel_metadata(flujo=RegistroFlujoAmbiental.Flujo.ENERGIA),
        )

        output = self.run_command()

        self.assertIn(f"id={fuel.id}", output)
        self.assertNotIn(f"id={energy.id}", output)
        self.assertNotIn("flujo-energia", output)

    def test_modo_auditoria_no_elimina(self):
        candidate = self.evidence("solo-auditoria", self.fuel_metadata())

        output = self.run_command()

        self.assertTrue(EvidenciaObra.objects.filter(pk=candidate.pk).exists())
        self.assertIn("Modo auditoría: no se eliminó ningún registro.", output)

    def test_rechaza_eliminar_id_que_no_es_candidato(self):
        generic = self.evidence("no-candidato", {})

        with self.assertRaises(CommandError):
            self.run_command(delete_confirmed=True, evidence_id=[generic.id])

        self.assertTrue(EvidenciaObra.objects.filter(pk=generic.pk).exists())

    def test_elimina_solo_el_candidato_confirmado(self):
        candidate = self.evidence("eliminar-confirmado", self.fuel_metadata())
        untouched = self.evidence("mantener-generico", {})
        candidate_path = Path(candidate.archivo.path)

        output = self.run_command(
            delete_confirmed=True,
            evidence_id=[candidate.id],
        )

        self.assertFalse(EvidenciaObra.objects.filter(pk=candidate.pk).exists())
        self.assertTrue(EvidenciaObra.objects.filter(pk=untouched.pk).exists())
        self.assertFalse(candidate_path.exists())
        self.assertIn("1 evidencias", output)
