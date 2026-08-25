from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Organizacion, UsuarioOrganizacion


class TenantConfigurationAuthorizationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user("tenant-admin", password="secret-pass")
        self.other_admin = User.objects.create_user("other-admin", password="secret-pass")
        self.superuser = User.objects.create_superuser("platform-admin", "admin@example.com", "secret-pass")
        self.organization = Organizacion.objects.create(nombre="Tenant autorizado")
        self.other = Organizacion.objects.create(nombre="Tenant ajeno")
        UsuarioOrganizacion.objects.create(user=self.admin, organizacion=self.organization, rol="admin", activo=True)
        UsuarioOrganizacion.objects.create(user=self.other_admin, organizacion=self.other, rol="admin", activo=True)
        self.client.force_login(self.admin)

    def url(self, organization):
        return f"/api/organizaciones/{organization.organizacion_id}/"

    def test_tenant_admin_lee_y_edita_su_organizacion(self):
        self.assertEqual(self.client.get(self.url(self.organization)).status_code, 200)
        response = self.client.patch(self.url(self.organization), {"contacto": "Responsable ambiental"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.contacto, "Responsable ambiental")

    def test_listado_responde_y_devuelve_solo_organizaciones_autorizadas(self):
        response = self.client.get("/api/organizaciones/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["organizacion_id"], self.organization.organizacion_id)
        self.assertNotIn("codigo_interno", response.data[0])

    def test_serializer_de_organizacion_cumple_con_el_modelo(self):
        response = self.client.get(self.url(self.organization))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.data),
            {
                "id", "organizacion_id", "nombre", "nombre_comercial", "rut",
                "region", "comuna", "direccion", "rubro", "preset", "activa",
                "email", "telefono", "contacto", "observaciones", "pais",
                "onboarding_step", "onboarding_completado", "etapas_count",
                "obras_count", "registros_count", "evidencias_count", "created_at",
                "updated_at",
            },
        )

    def test_tenant_admin_no_edita_organizacion_ajena(self):
        self.assertEqual(self.client.patch(self.url(self.other), {"nombre": "Cambio indebido"}, format="json").status_code, 404)
        self.other.refresh_from_db()
        self.assertEqual(self.other.nombre, "Tenant ajeno")

    def test_tenant_admin_no_crea_ni_elimina_tenants(self):
        self.assertEqual(self.client.post("/api/organizaciones/", {"nombre": "Nuevo tenant"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.url(self.organization)).status_code, 403)
        self.assertTrue(Organizacion.objects.filter(pk=self.organization.pk).exists())

    def test_superuser_conserva_acceso_tecnico(self):
        self.client.force_login(self.superuser)
        created = self.client.post("/api/organizaciones/", {"nombre": "Tenant plataforma"}, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.client.patch(self.url(self.other), {"contacto": "Plataforma"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(self.url(self.other)).status_code, 200)
