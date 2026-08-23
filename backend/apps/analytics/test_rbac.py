from datetime import date

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Obra, Organizacion, UsuarioObraAcceso, UsuarioOrganizacion
from .permissions import Permission, ROLE_PERMISSIONS, has_tenant_permission


class RolePermissionMapTests(APITestCase):
    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Organización RBAC")
        self.user = User.objects.create_user("role-user", password="safe-password")

    def membership(self, role):
        return UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.organization, rol=role)

    def test_critical_role_permissions(self):
        self.assertIn(Permission.SETTINGS_MANAGE, ROLE_PERMISSIONS[UsuarioOrganizacion.Rol.ADMIN])
        self.assertIn(Permission.PROFILE_MANAGE, ROLE_PERMISSIONS[UsuarioOrganizacion.Rol.RESPONSABLE_AMBIENTAL])
        self.assertIn(Permission.IMPORT_CREATE, ROLE_PERMISSIONS[UsuarioOrganizacion.Rol.ANALISTA])
        self.assertIn(Permission.DATA_CREATE, ROLE_PERMISSIONS[UsuarioOrganizacion.Rol.OPERADOR])
        self.assertNotIn(Permission.EVIDENCE_VALIDATE, ROLE_PERMISSIONS[UsuarioOrganizacion.Rol.OPERADOR])
        self.assertIn(Permission.EVIDENCE_VALIDATE, ROLE_PERMISSIONS[UsuarioOrganizacion.Rol.REVISOR_AMBIENTAL])
        self.assertNotIn(Permission.ORGANIZATION_UPDATE, ROLE_PERMISSIONS[UsuarioOrganizacion.Rol.REVISOR_AMBIENTAL])
        self.assertTrue(all(permission.endswith(".view") for permission in ROLE_PERMISSIONS[UsuarioOrganizacion.Rol.LECTOR]))

    def test_unknown_role_and_permission_are_denied(self):
        membership = self.membership(UsuarioOrganizacion.Rol.LECTOR)
        membership.rol = "invalid-role"
        membership.save(update_fields=["rol"])
        self.assertFalse(has_tenant_permission(self.user, self.organization, Permission.WORK_VIEW))
        self.assertFalse(has_tenant_permission(self.user, self.organization, "unknown.permission"))


class TenantRBACTests(APITestCase):
    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Tenant A")
        self.other = Organizacion.objects.create(nombre="Tenant B")
        self.admin = User.objects.create_user("admin-a", password="safe-password")
        self.membership = UsuarioOrganizacion.objects.create(
            user=self.admin, organizacion=self.organization, rol=UsuarioOrganizacion.Rol.ADMIN
        )
        self.work_a = Obra.objects.create(organizacion=self.organization, nombre="Obra A", fecha_inicio=date.today())
        self.work_b = Obra.objects.create(organizacion=self.organization, nombre="Obra B", fecha_inicio=date.today())
        self.other_work = Obra.objects.create(organizacion=self.other, nombre="Obra ajena", fecha_inicio=date.today())
        self.client.force_login(self.admin)

    def test_auth_me_exposes_capabilities(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        membership = response.data["user"]["organizaciones"][0]
        self.assertEqual(membership["role"], "admin")
        self.assertEqual(membership["scope"], "organizacion")
        self.assertIn(Permission.TEAM_MANAGE, membership["permissions"])

    def test_cross_tenant_team_and_work_are_hidden(self):
        self.assertEqual(self.client.get(f"/api/organizaciones/{self.other.organizacion_id}/usuarios/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/obras/{self.other_work.codigo_obra}/").status_code, 404)

    def test_work_scope_filters_list_and_detail(self):
        operator = User.objects.create_user("operator", password="safe-password")
        scoped = UsuarioOrganizacion.objects.create(
            user=operator, organizacion=self.organization, rol=UsuarioOrganizacion.Rol.OPERADOR,
            alcance=UsuarioOrganizacion.Alcance.OBRAS,
        )
        UsuarioObraAcceso.objects.create(usuario_organizacion=scoped, obra=self.work_a)
        self.client.force_login(operator)
        response = self.client.get(f"/api/organizaciones/{self.organization.organizacion_id}/obras/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [self.work_a.id])
        self.assertEqual(self.client.get(f"/api/obras/{self.work_a.codigo_obra}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/obras/{self.work_b.codigo_obra}/").status_code, 404)

    def test_reader_is_read_only_on_protected_endpoints(self):
        reader = User.objects.create_user("reader", password="safe-password")
        UsuarioOrganizacion.objects.create(user=reader, organizacion=self.organization, rol=UsuarioOrganizacion.Rol.LECTOR)
        self.client.force_login(reader)
        self.assertEqual(self.client.get(f"/api/organizaciones/{self.organization.organizacion_id}/obras/").status_code, 200)
        response = self.client.post(
            f"/api/organizaciones/{self.organization.organizacion_id}/obras/",
            {"nombre": "No autorizada", "fecha_inicio": str(date.today())}, format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_last_admin_cannot_be_downgraded_disabled_or_deleted(self):
        url = f"/api/organizaciones/{self.organization.organizacion_id}/usuarios/{self.admin.id}/"
        self.assertEqual(self.client.patch(url, {"rol": "lector"}, format="json").status_code, 409)
        self.assertEqual(self.client.patch(url, {"activo": False}, format="json").status_code, 409)
        self.assertEqual(self.client.delete(url).status_code, 409)
        second = User.objects.create_user("second-admin", password="safe-password")
        UsuarioOrganizacion.objects.create(user=second, organizacion=self.organization, rol=UsuarioOrganizacion.Rol.ADMIN)
        self.assertEqual(self.client.patch(url, {"rol": "lector"}, format="json").status_code, 200)

    def test_membership_payload_cannot_escalate_django_user(self):
        response = self.client.post(
            f"/api/organizaciones/{self.organization.organizacion_id}/usuarios/",
            {"username": "new-user", "password": "safe-password", "rol": "operador", "is_staff": True, "is_superuser": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="new-user").exists())
