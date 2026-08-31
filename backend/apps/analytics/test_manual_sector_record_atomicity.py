from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from .models import (
    ActividadOperacional,
    AreaOperacional,
    EspacioTrabajoOperacional,
    EvidenciaObra,
    FuenteDatos,
    Obra,
    Observacion,
    Organizacion,
    RegistroFlujoAmbiental,
    UsuarioAreaOperacional,
    UsuarioOrganizacion,
)


class ManualSectorRecordAtomicityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("marcela", first_name="Marcela", password="test-pass")
        self.organization = Organizacion.objects.create(nombre="Constructora Atomicidad", preset="construccion")
        self.membership = UsuarioOrganizacion.objects.create(
            user=self.user,
            organizacion=self.organization,
            rol=UsuarioOrganizacion.Rol.OPERADOR,
        )
        self.work = Obra.objects.create(
            id=71,
            organizacion=self.organization,
            nombre="Edificio Los Robles",
            fecha_inicio="2026-08-25",
        )
        self.area = AreaOperacional.objects.create(
            organizacion=self.organization,
            nombre="Medio ambiente",
            tipo="medio_ambiente_sostenibilidad",
        )
        self.workspace = EspacioTrabajoOperacional.objects.create(
            usuario_organizacion=self.membership,
            area=self.area,
            obra=self.work,
        )
        self.source = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Vale de combustible",
            tipo="manual",
        )
        self.client.force_login(self.user)
        self.url = f"/api/organizaciones/{self.organization.organizacion_id}/flujos-ambientales/registro-manual/"

    def payload(self, **overrides):
        payload = {
            "obra": self.work.id,
            "tipo_actividad": "consumo_combustible_estacionario",
            "codigo_actividad": "manual-combustibles-test",
            "nombre_actividad": "Registro manual · combustibles",
            "flujo": "combustible_estacionario",
            "periodo_inicio": "2026-08-25T12:00:00",
            "concepto": "combustible_consumido",
            "valor_numerico": "20",
            "unidad": "L",
            "fuente": self.source.id,
            "tipo_recurso": "diesel",
            "destino_operacional": "generador",
        }
        payload.update(overrides)
        return payload

    def post(self, payload, organization_id=None):
        url = self.url if organization_id is None else f"/api/organizaciones/{organization_id}/flujos-ambientales/registro-manual/"
        return self.client.post(
            url,
            payload,
            format="multipart",
            HTTP_X_WORKSPACE_ID=str(self.workspace.id),
        )

    def test_registro_sin_evidencia_crea_actividad_y_registro(self):
        response = self.post(self.payload())

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(ActividadOperacional.objects.count(), 1)
        self.assertEqual(RegistroFlujoAmbiental.objects.count(), 1)
        self.assertEqual(EvidenciaObra.objects.count(), 0)

    def test_area_principal_resuelve_y_crea_contexto_sin_workspace_expuesto(self):
        self.workspace.delete()
        UsuarioAreaOperacional.objects.create(
            usuario_organizacion=self.membership,
            area=self.area,
            cargo="Encargada ambiental",
            es_principal=True,
        )

        response = self.client.post(
            self.url,
            self.payload(periodo_inicio="2026-09-03T12:00:00"),
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.data)
        workspace = EspacioTrabajoOperacional.objects.get()
        self.assertEqual(workspace.usuario_organizacion, self.membership)
        self.assertEqual(workspace.area, self.area)
        self.assertEqual(workspace.obra_id, 71)
        self.assertEqual(ActividadOperacional.objects.get().timestamp_inicio.date().isoformat(), "2026-09-03")

    def test_registro_con_evidencia_conserva_todos_los_vinculos(self):
        response = self.post(self.payload(
            evidencia_archivo=SimpleUploadedFile("vale.txt", b"respaldo combustible", content_type="text/plain"),
            evidencia_nombre="Registro de abastecimiento de combustible",
            evidencia_tipo="factura_combustible",
        ))

        self.assertEqual(response.status_code, 201, response.data)
        evidence = EvidenciaObra.objects.get()
        observation = Observacion.objects.select_related("evidencia", "fuente").get()
        self.assertEqual(evidence.obra, self.work)
        self.assertEqual(evidence.area_origen, self.area)
        self.assertEqual(evidence.usuario_origen, self.user)
        self.assertEqual(evidence.metadata_extraccion["workspace_id"], self.workspace.id)
        self.assertEqual(
            evidence.metadata_extraccion["flujo"],
            RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO,
        )
        self.assertEqual(observation.evidencia, evidence)
        self.assertEqual(observation.fuente, self.source)

    def test_fallo_al_crear_registro_revierte_actividad_y_evidencia(self):
        counts_before = (
            EvidenciaObra.objects.count(),
            ActividadOperacional.objects.count(),
            RegistroFlujoAmbiental.objects.count(),
        )
        self.client.raise_request_exception = False
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            with patch(
                "apps.analytics.views_sector_flows_v1.RegistroFlujoAmbientalSerializer.save",
                side_effect=RuntimeError("controlled failure"),
            ):
                response = self.post(self.payload(
                    evidencia_archivo=SimpleUploadedFile("rollback.txt", b"rollback", content_type="text/plain"),
                ))

            self.assertFalse(any(item.is_file() for item in Path(media_root).rglob("*")))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(counts_before, (
            EvidenciaObra.objects.count(),
            ActividadOperacional.objects.count(),
            RegistroFlujoAmbiental.objects.count(),
        ))

    def test_error_de_validacion_no_deja_elementos_parciales(self):
        payload = self.payload()
        payload.pop("fuente")
        response = self.post(payload)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(EvidenciaObra.objects.exists())
        self.assertFalse(ActividadOperacional.objects.exists())
        self.assertFalse(RegistroFlujoAmbiental.objects.exists())

    def test_cross_tenant_no_crea_elementos(self):
        other = Organizacion.objects.create(nombre="Otro tenant")
        response = self.post(self.payload(), organization_id=other.organizacion_id)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(ActividadOperacional.objects.exists())
        self.assertFalse(RegistroFlujoAmbiental.objects.exists())

    def test_usuario_sin_permiso_no_crea_elementos(self):
        self.membership.rol = UsuarioOrganizacion.Rol.LECTOR
        self.membership.save(update_fields=["rol"])
        response = self.post(self.payload())

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ActividadOperacional.objects.exists())
        self.assertFalse(RegistroFlujoAmbiental.objects.exists())

    def test_combustible_persiste_tipo_cantidad_y_destino(self):
        response = self.post(self.payload())

        self.assertEqual(response.status_code, 201, response.data)
        record = RegistroFlujoAmbiental.objects.get()
        observation = record.actividad.observaciones.get()
        self.assertEqual(record.tipo_recurso, "diesel")
        self.assertEqual(record.destino_operacional, "generador")
        self.assertEqual(str(observation.valor_numerico), "20.000000")
        self.assertEqual(observation.unidad, "L")

    def test_respaldo_es_opcional(self):
        response = self.post(self.payload(codigo_actividad="manual-combustibles-sin-respaldo"))

        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(Observacion.objects.get().evidencia_id)

    def test_fecha_anterior_al_inicio_de_obra_es_rechazada(self):
        response = self.post(self.payload(
            codigo_actividad="manual-combustibles-fecha-invalida",
            periodo_inicio="2026-08-24T12:00:00",
        ))

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("inicio de la obra", str(response.data).lower())
        self.assertFalse(ActividadOperacional.objects.exists())
        self.assertFalse(RegistroFlujoAmbiental.objects.exists())
