from datetime import date

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import EventoAuditoriaSaaS, Obra, Organizacion, SuscripcionSaaS, UsuarioOrganizacion


class SaaSAdministrationTests(APITestCase):
    def setUp(self):
        self.root = User.objects.create_superuser("platform-root", "root@example.com", "safe-password")
        self.member = User.objects.create_user("tenant-member", password="safe-password")
        self.organization = Organizacion.objects.create(nombre="Cliente SaaS")
        UsuarioOrganizacion.objects.create(user=self.member, organizacion=self.organization, rol=UsuarioOrganizacion.Rol.ADMIN)
        self.work = Obra.objects.create(organizacion=self.organization, nombre="Obra conservada", fecha_inicio=date.today())
        self.detail = f"/api/saas/organizaciones/{self.organization.organizacion_id}/"
        self.actions = f"/api/saas/organizaciones/{self.organization.organizacion_id}/acciones/"

    def test_global_endpoints_are_superuser_only(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get("/api/saas/resumen/").status_code, 403)
        self.client.force_login(self.root)
        response = self.client.get("/api/saas/resumen/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["kpis"]["total"], 1)

    def test_suspend_blocks_tenant_and_preserves_data_then_reactivates(self):
        self.client.force_login(self.root)
        response = self.client.post(self.actions, {"action": "suspender"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["disponibilidad"], "bloqueado")
        self.assertTrue(Obra.objects.filter(pk=self.work.pk).exists())
        self.assertEqual(EventoAuditoriaSaaS.objects.filter(accion="suspender").count(), 1)

        self.client.force_login(self.member)
        blocked = self.client.get(f"/api/organizaciones/{self.organization.organizacion_id}/obras/")
        self.assertEqual(blocked.status_code, 423)
        self.assertEqual(blocked.json()["code"], "saas_access_blocked")

        self.client.force_login(self.root)
        restored = self.client.post(self.actions, {"action": "reactivar"}, format="json")
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.data["disponibilidad"], "operativo")

    def test_invalid_transition_is_rejected(self):
        subscription = SuscripcionSaaS.objects.create(organizacion=self.organization, estado="cancelado", disponibilidad="bloqueado")
        self.client.force_login(self.root)
        response = self.client.post(self.actions, {"action": "pago_pendiente"}, format="json")
        self.assertEqual(response.status_code, 409)
        subscription.refresh_from_db()
        self.assertEqual(subscription.estado, "cancelado")

    def test_detail_patch_cannot_bypass_service_state_transitions(self):
        self.client.force_login(self.root)
        response = self.client.patch(
            self.detail,
            {"estado": "cancelado", "disponibilidad": "bloqueado", "plan": "professional"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["estado"], "activo")
        self.assertEqual(response.data["disponibilidad"], "operativo")
        self.assertEqual(response.data["plan"], "professional")
