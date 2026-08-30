from datetime import date

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AreaOperacional, EspacioTrabajoOperacional, EvidenciaObra, Obra, Organizacion, UsuarioAreaOperacional, UsuarioObraAcceso, UsuarioOrganizacion
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


class OperationalAreaPrimaryAssignmentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.organization = Organizacion.objects.create(nombre="Carbono Zero")
        self.admin = User.objects.create_user("admin-estructura")
        UsuarioOrganizacion.objects.create(
            user=self.admin,
            organizacion=self.organization,
            rol=UsuarioOrganizacion.Rol.ADMIN,
        )
        self.marcela = User.objects.create_user(
            "marcela",
            first_name="Marcela",
            last_name="Rojas",
        )
        self.membership = UsuarioOrganizacion.objects.create(
            user=self.marcela,
            organizacion=self.organization,
        )
        self.administration = AreaOperacional.objects.create(
            organizacion=self.organization,
            nombre="Administración",
        )
        self.logistics = AreaOperacional.objects.create(
            organizacion=self.organization,
            nombre="Logística / Transporte",
        )
        # El middleware de tenant valida al usuario antes de la autenticación de DRF.
        self.client.force_login(self.admin)

    def assignment_url(self, area):
        return (
            f"/api/organizaciones/{self.organization.organizacion_id}"
            f"/areas-operacionales/{area.id}/usuarios/"
        )

    def test_changing_primary_area_leaves_only_one_for_user(self):
        first = self.client.post(
            self.assignment_url(self.administration),
            {"user_id": self.marcela.id, "cargo": "Administradora", "es_principal": True},
            format="json",
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            self.assignment_url(self.logistics),
            {"user_id": self.marcela.id, "cargo": "Coordinadora", "es_principal": True},
            format="json",
        )
        self.assertEqual(second.status_code, 201)

        assignments = UsuarioAreaOperacional.objects.filter(
            usuario_organizacion=self.membership,
            activo=True,
        )
        self.assertEqual(assignments.count(), 2)
        self.assertEqual(assignments.filter(es_principal=True).count(), 1)
        self.assertFalse(assignments.get(area=self.administration).es_principal)
        self.assertTrue(assignments.get(area=self.logistics).es_principal)

        administration_users = self.client.get(self.assignment_url(self.administration))
        logistics_users = self.client.get(self.assignment_url(self.logistics))
        self.assertFalse(administration_users.data[0]["es_principal"])
        self.assertTrue(logistics_users.data[0]["es_principal"])
