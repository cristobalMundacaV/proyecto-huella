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
        self.environment = AreaOperacional.objects.create(
            organizacion=self.organization,
            nombre="Medio ambiente",
        )
        # El middleware de tenant valida al usuario antes de la autenticación de DRF.
        self.client.force_login(self.admin)

    def assignment_url(self, area):
        return (
            f"/api/organizaciones/{self.organization.organizacion_id}"
            f"/areas-operacionales/{area.id}/usuarios/"
        )

    def assignment_detail_url(self, area, assignment_id):
        return f"{self.assignment_url(area)}{assignment_id}/"

    def test_changing_primary_area_leaves_only_one_for_user(self):
        first = self.client.post(
            self.assignment_url(self.administration),
            {"user_id": self.marcela.id, "cargo": "Administradora", "es_principal": False},
            format="json",
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            self.assignment_url(self.environment),
            {"user_id": self.marcela.id, "cargo": "Encargada ambiental", "es_principal": False},
            format="json",
        )
        self.assertEqual(second.status_code, 201)

        environment_primary = self.client.patch(
            self.assignment_detail_url(self.environment, second.data["id"]),
            {"es_principal": True},
            format="json",
        )
        self.assertEqual(environment_primary.status_code, 200)

        administration_primary = self.client.patch(
            self.assignment_detail_url(self.administration, first.data["id"]),
            {"es_principal": True},
            format="json",
        )
        self.assertEqual(administration_primary.status_code, 200)

        assignments = UsuarioAreaOperacional.objects.filter(
            usuario_organizacion=self.membership,
            activo=True,
        )
        self.assertEqual(assignments.count(), 2)
        self.assertEqual(assignments.filter(es_principal=True).count(), 1)
        administration = assignments.get(area=self.administration)
        environment = assignments.get(area=self.environment)
        self.assertEqual(administration.id, first.data["id"])
        self.assertEqual(environment.id, second.data["id"])
        self.assertEqual(administration.cargo, "Administradora")
        self.assertEqual(environment.cargo, "Encargada ambiental")
        self.assertTrue(administration.es_principal)
        self.assertFalse(environment.es_principal)

        administration_users = self.client.get(self.assignment_url(self.administration))
        environment_users = self.client.get(self.assignment_url(self.environment))
        self.assertTrue(administration_users.data[0]["es_principal"])
        self.assertFalse(environment_users.data[0]["es_principal"])

    def test_patch_can_explicitly_unmark_primary_assignment(self):
        created = self.client.post(
            self.assignment_url(self.administration),
            {"user_id": self.marcela.id, "cargo": "Administradora", "es_principal": True},
            format="json",
        )

        response = self.client.patch(
            self.assignment_detail_url(self.administration, created.data["id"]),
            {"es_principal": False},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["es_principal"])
