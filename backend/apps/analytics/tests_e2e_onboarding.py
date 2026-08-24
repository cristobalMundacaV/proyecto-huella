import re

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings, TestCase
from rest_framework.test import APIClient

from .models import AreaCapacidadAmbiental, AreaOperacional, CapacidadOrganizacion, DiagnosticoAmbientalInicial, ElementoDiagnosticoAmbiental, EventoAuditoriaSaaS, Observacion, Organizacion, ProblematicaAmbiental, RegistroEmision, SuscripcionSaaS, UsuarioOrganizacion


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", RESEND_API_KEY="", FRONTEND_URL="http://frontend.test")
class SaaSOnboardingE2ETests(TestCase):
    def setUp(self):
        self.platform_admin = User.objects.create_superuser("platform", "platform@example.com", "Admin-password-123")
        self.client = APIClient(); self.client.force_authenticate(self.platform_admin)

    def provision(self):
        response = self.client.post("/api/saas/organizaciones/provisionar/", {"nombre": "Constructora Andina del Biobío SpA", "sector": "construccion", "plan": "professional", "estado": "piloto", "admin_nombre": "Marcela", "admin_apellido": "Rojas", "admin_email": "marcela@example.com", "admin_cargo": "Administradora"}, format="json")
        self.assertEqual(response.status_code, 201, response.data); return response

    def test_full_provision_activation_and_onboarding(self):
        provisioned = self.provision(); organization = Organizacion.objects.get(organizacion_id=provisioned.data["organizacion_id"])
        subscription = SuscripcionSaaS.objects.get(organizacion=organization); admin = User.objects.get(email="marcela@example.com")
        self.assertEqual(subscription.plan, "professional"); self.assertFalse(admin.is_active)
        self.assertEqual(UsuarioOrganizacion.objects.get(user=admin, organizacion=organization).rol, UsuarioOrganizacion.Rol.ADMIN)
        self.assertEqual(EventoAuditoriaSaaS.objects.filter(organizacion=organization, accion="alta_saas").count(), 1); self.assertEqual(len(mail.outbox), 1)
        match = re.search(r"/activar-cuenta/([^/]+)/([^\s<]+)", mail.outbox[0].body)
        self.assertIsNotNone(match); uid, token = match.groups()
        response = self.client.post(f"/api/auth/activar/{uid}/{token}/", {"password": "Secure-access-481!", "confirmation": "Secure-access-481!"}, format="json")
        self.assertEqual(response.status_code, 200); admin.refresh_from_db(); self.assertTrue(admin.is_active); self.assertIsNotNone(authenticate(username=admin.username, password="Secure-access-481!"))
        self.client.force_authenticate(admin); headers = {"HTTP_X_ORGANIZATION_ID": organization.organizacion_id}
        steps = [
            (1, {"nombre": organization.nombre, "rut": "21.683.264-7", "pais": "Chile", "preset": "construccion", "region": "Biobío"}),
            (2, {"areas": ["bodega", "maquinaria_operaciones", "logistica_transporte", "administracion_compras", "medio_ambiente", "gestion_obra"]}),
            (3, {"flujos": {"materiales": "regular", "combustibles": "regular", "energia": "parcial", "agua": "sin_informacion", "residuos": "regular"}}),
            (4, {"metodos": "PDF, Excel", "centralizacion": "parcial", "revision": "medio_ambiente", "frecuencia": "mensual"}),
            (5, {"confirmado": True}),
        ]
        for step, data in steps:
            response = self.client.patch("/api/onboarding/", {"step": step, "data": data}, format="json", **headers)
            self.assertEqual(response.status_code, 200, response.data)
        organization.refresh_from_db(); self.assertTrue(organization.onboarding_completado)
        self.assertEqual(AreaOperacional.objects.filter(organizacion=organization, activa=True).count(), 6)
        self.assertEqual(CapacidadOrganizacion.objects.filter(organizacion=organization).exclude(estado="no_aplica").count(), 5)
        self.assertGreater(AreaCapacidadAmbiental.objects.filter(area__organizacion=organization).count(), 0)
        diagnostic = DiagnosticoAmbientalInicial.objects.get(organizacion=organization, obra=None)
        self.assertGreater(ElementoDiagnosticoAmbiental.objects.filter(diagnostico=diagnostic).count(), 0)
        self.assertFalse(RegistroEmision.objects.filter(organizacion=organization).exists()); self.assertFalse(Observacion.objects.filter(organizacion=organization).exists()); self.assertFalse(ProblematicaAmbiental.objects.filter(organizacion=organization).exists())

    def test_onboarding_is_tenant_isolated(self):
        self.provision(); first = Organizacion.objects.get(nombre__startswith="Constructora")
        other = Organizacion.objects.create(nombre="Otra empresa"); user = User.objects.create_user("other-admin", password="password")
        UsuarioOrganizacion.objects.create(user=user, organizacion=other, rol=UsuarioOrganizacion.Rol.ADMIN)
        self.client.force_authenticate(user)
        response = self.client.get("/api/onboarding/", HTTP_X_ORGANIZATION_ID=first.organizacion_id)
        self.assertEqual(response.status_code, 404)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", RESEND_API_KEY="", FRONTEND_URL="http://frontend.test")
class PasswordResetE2ETests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("marcela", "marcela@example.com", "Old-password-123!"); self.client = APIClient()

    def test_reset_is_neutral_and_token_is_single_use(self):
        unknown = self.client.post("/api/auth/password-reset/", {"email": "missing@example.com"}, format="json")
        known = self.client.post("/api/auth/password-reset/", {"email": self.user.email}, format="json")
        self.assertEqual(unknown.data, known.data); self.assertEqual(len(mail.outbox), 1)
        match = re.search(r"/restablecer-contrasena/([^/]+)/([^\s<]+)", mail.outbox[0].body); uid, token = match.groups()
        payload = {"password": "New-password-456!", "confirmation": "New-password-456!"}
        first = self.client.post(f"/api/auth/password-reset/{uid}/{token}/", payload, format="json")
        second = self.client.post(f"/api/auth/password-reset/{uid}/{token}/", payload, format="json")
        self.assertEqual(first.status_code, 200); self.assertEqual(second.status_code, 400)
        self.assertIsNone(authenticate(username="marcela", password="Old-password-123!")); self.assertIsNotNone(authenticate(username="marcela", password="New-password-456!")); self.assertEqual(len(mail.outbox), 2)

    def test_authenticated_password_change_keeps_access_and_notifies(self):
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/auth/cambiar-contrasena/", {"current_password": "Old-password-123!", "password": "Safer-password-789!", "confirmation": "Safer-password-789!"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNotNone(authenticate(username="marcela", password="Safer-password-789!"))
        self.assertEqual(len(mail.outbox), 1)


class EditableOperationalStructureTests(TestCase):
    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Tenant editable", onboarding_step=5, onboarding_completado=True)
        self.user = User.objects.create_user("tenant-admin", "tenant@example.com", "Secure-password-123!")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.organization, rol=UsuarioOrganizacion.Rol.ADMIN)
        self.client = APIClient(); self.client.force_authenticate(self.user)
        self.headers = {"HTTP_X_ORGANIZATION_ID": self.organization.organizacion_id}

    def save(self, step, data, expected=200):
        response = self.client.patch("/api/onboarding/", {"step": step, "data": data}, format="json", **self.headers)
        self.assertEqual(response.status_code, expected, response.data)
        return response

    def test_matrix_is_editable_idempotent_and_tenant_safe(self):
        areas = {"areas": ["bodega", "administracion_compras"]}
        flows = {"flujos": {"materiales": "regular", "energia": "parcial"}, "relaciones": {"bodega": ["materiales"], "administracion_compras": ["energia"]}}
        self.save(2, areas); self.save(2, areas); self.save(3, flows); self.save(3, flows)
        self.assertEqual(AreaOperacional.objects.filter(organizacion=self.organization, activa=True).count(), 2)
        self.assertEqual(CapacidadOrganizacion.objects.filter(organizacion=self.organization).exclude(estado="no_aplica").count(), 2)
        self.assertEqual(AreaCapacidadAmbiental.objects.filter(area__organizacion=self.organization).count(), 2)
        response = self.client.get("/api/onboarding/", **self.headers)
        self.assertEqual(response.data["relaciones"], flows["relaciones"])
        self.save(3, {"flujos": flows["flujos"], "relaciones": {"area_ajena": ["materiales"]}}, expected=400)
        self.assertEqual(AreaCapacidadAmbiental.objects.filter(area__organizacion=self.organization).count(), 2)

    def test_configuration_change_regenerates_diagnostic_without_obsolete_rows(self):
        self.save(2, {"areas": ["bodega", "administracion_compras"]})
        self.save(3, {"flujos": {"materiales": "regular", "energia": "parcial"}, "relaciones": {"bodega": ["materiales"], "administracion_compras": ["energia"]}})
        self.save(4, {"metodos": "Excel", "centralizacion": "parcial"})
        diagnostic = DiagnosticoAmbientalInicial.objects.get(organizacion=self.organization, obra=None)
        self.assertEqual(diagnostic.elementos.count(), 6)
        self.save(3, {"flujos": {"agua": "sin_informacion"}, "relaciones": {"bodega": ["agua"], "administracion_compras": []}})
        diagnostic.refresh_from_db()
        self.assertEqual(diagnostic.elementos.count(), 4)
        self.assertFalse(diagnostic.elementos.filter(nombre__in=["Materiales e insumos", "Energia"]).exists())
        self.assertEqual(diagnostic.elementos.filter(nombre="Agua").count(), 2)
