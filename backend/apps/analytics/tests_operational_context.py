from datetime import date

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AreaOperacional, EspacioTrabajoOperacional, EvidenciaObra, Obra, Organizacion, UsuarioObraAcceso, UsuarioOrganizacion
from .services.operational_context import resolve_operational_context


class OperationalContextTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.organization = Organizacion.objects.create(nombre="Constructora Andina")
        self.other_organization = Organizacion.objects.create(nombre="Empresa Externa")
        self.work = Obra.objects.create(organizacion=self.organization, nombre="Los Robles", fecha_inicio=date.today())
        self.other_work = Obra.objects.create(organizacion=self.organization, nombre="Ruta Q-180", fecha_inicio=date.today())
        self.user = User.objects.create_user("pablo", password="test-password")
        self.membership = UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.organization, rol=UsuarioOrganizacion.Rol.OPERADOR, alcance=UsuarioOrganizacion.Alcance.OBRAS)
        UsuarioObraAcceso.objects.create(usuario_organizacion=self.membership, obra=self.work)
        self.area = AreaOperacional.objects.create(organizacion=self.organization, nombre="Bodega", tipo=AreaOperacional.Tipo.BODEGA)
        self.workspace = EspacioTrabajoOperacional.objects.create(usuario_organizacion=self.membership, area=self.area, obra=self.work)
        self.client.force_authenticate(self.user)

    def test_single_workspace_is_resolved_automatically(self):
        response = self.client.get("/api/contexto-operativo/actual/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["obra"]["id"], self.work.id)

    def test_foreign_workspace_is_hidden(self):
        outsider = User.objects.create_user("outsider")
        outsider_membership = UsuarioOrganizacion.objects.create(user=outsider, organizacion=self.other_organization)
        outsider_area = AreaOperacional.objects.create(organizacion=self.other_organization, nombre="Bodega")
        outsider_workspace = EspacioTrabajoOperacional.objects.create(usuario_organizacion=outsider_membership, area=outsider_area)
        response = self.client.get("/api/contexto-operativo/actual/", HTTP_X_WORKSPACE_ID=str(outsider_workspace.id))
        self.assertEqual(response.status_code, 404)

    def test_area_does_not_grant_review_permission(self):
        response = self.client.get("/api/contexto-operativo/actual/", HTTP_X_WORKSPACE_ID=str(self.workspace.id))
        self.assertNotIn("evidence.validate", response.data["permisos"])

    def test_multiple_workspaces_require_selection(self):
        area = AreaOperacional.objects.create(organizacion=self.organization, nombre="Administracion", tipo=AreaOperacional.Tipo.ADMINISTRACION_COMPRAS)
        EspacioTrabajoOperacional.objects.create(usuario_organizacion=self.membership, area=area, obra=self.work)
        response = self.client.get("/api/contexto-operativo/actual/")
        self.assertEqual(response.status_code, 400)

    def test_upload_ignores_spoofed_origin_and_keeps_provenance(self):
        foreign_area = AreaOperacional.objects.create(organizacion=self.other_organization, nombre="Compras")
        upload = SimpleUploadedFile("guia.pdf", b"document", content_type="application/pdf")
        response = self.client.post("/api/contexto-operativo/subir-informacion/", {"archivo": upload, "area_id": foreign_area.id, "usuario_id": 999}, format="multipart", HTTP_X_WORKSPACE_ID=str(self.workspace.id))
        self.assertEqual(response.status_code, 201)
        evidence = EvidenciaObra.objects.get(pk=response.data["id"])
        self.assertEqual(evidence.organizacion, self.organization)
        self.assertEqual(evidence.obra, self.work)
        self.assertEqual(evidence.area_origen, self.area)
        self.assertEqual(evidence.usuario_origen, self.user)
