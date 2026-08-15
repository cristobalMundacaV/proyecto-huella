from datetime import date

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Obra, Organizacion, UsuarioOrganizacion


class ArchitectureClosureTenantTests(APITestCase):
    def setUp(self):
        self.own = Organizacion.objects.create(nombre="Tenant propio")
        self.foreign = Organizacion.objects.create(nombre="Tenant ajeno")
        self.own_work = Obra.objects.create(organizacion=self.own, nombre="Obra propia", fecha_inicio=date(2026, 1, 1))
        self.foreign_work = Obra.objects.create(organizacion=self.foreign, nombre="Obra ajena", fecha_inicio=date(2026, 1, 1))
        self.user = User.objects.create_user("tenant-closure", password="test")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.own)

    def test_api_requires_authentication_by_default(self):
        self.assertEqual(self.client.get("/api/obras/").status_code, 403)

    def test_legacy_work_collection_and_children_are_tenant_scoped(self):
        self.client.force_login(self.user)
        collection = self.client.get("/api/obras/")
        self.assertEqual([row["id"] for row in collection.data], [self.own_work.id])
        for suffix in ("", "registros-emision/", "evidencias/", "transportes/"):
            response = self.client.get(f"/api/obras/{self.foreign_work.codigo_obra}/{suffix}")
            self.assertEqual(response.status_code, 404)

    def test_dashboard_does_not_aggregate_foreign_tenant(self):
        self.client.force_login(self.user)
        payload = self.client.get("/api/dashboard/").data
        self.assertEqual(payload["organizaciones_count"], 1)
        self.assertEqual(payload["obras_count"], 1)
