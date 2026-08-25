from django.contrib.auth.models import User
from django.test import TestCase

from .models import AreaOperacional, Organizacion
from .services.onboarding import apply_onboarding_step, area_catalog_for


class OnboardingStructureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("estructura-admin")
        self.organization = Organizacion.objects.create(
            nombre="Constructora Andina",
            preset="construccion",
            onboarding_step=2,
        )

    def test_construction_catalog_contains_organizational_areas_only(self):
        catalog = area_catalog_for("construccion")
        names = {row["nombre"] for row in catalog}
        self.assertIn("Oficina técnica", names)
        self.assertIn("Prevención de riesgos / HSE", names)
        self.assertNotIn("Producción", names)
        self.assertNotIn("Gestión de obra", names)

    def test_requires_at_least_one_area(self):
        with self.assertRaisesMessage(ValueError, "Selecciona al menos un área"):
            apply_onboarding_step(self.organization, self.user, 2, {"areas": []})

    def test_persists_multiple_and_custom_areas_and_advances_to_flows(self):
        apply_onboarding_step(self.organization, self.user, 2, {"areas": [
            {"tipo": "bodega", "nombre": "Bodega"},
            {"tipo": "oficina_tecnica", "nombre": "Oficina técnica"},
            {"tipo": "personalizada_temporal", "nombre": "  Abastecimiento  "},
        ]})
        self.assertSetEqual(
            set(self.organization.areas_operacionales.filter(activa=True).values_list("nombre", flat=True)),
            {"Bodega", "Oficina técnica", "Abastecimiento"},
        )
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.onboarding_step, 3)

    def test_case_insensitive_duplicate_is_not_created(self):
        AreaOperacional.objects.create(organizacion=self.organization, nombre="Bodega", tipo="bodega")
        apply_onboarding_step(self.organization, self.user, 2, {"areas": [
            {"tipo": "personalizada_1", "nombre": "bodega"},
            {"tipo": "personalizada_2", "nombre": "BODEGA"},
        ]})
        self.assertEqual(self.organization.areas_operacionales.filter(nombre__iexact="bodega").count(), 1)

    def test_areas_remain_scoped_to_the_current_tenant(self):
        other = Organizacion.objects.create(nombre="Empresa externa", preset="construccion")
        apply_onboarding_step(self.organization, self.user, 2, {"areas": [{"tipo": "bodega", "nombre": "Bodega"}]})
        self.assertTrue(self.organization.areas_operacionales.filter(nombre="Bodega").exists())
        self.assertFalse(other.areas_operacionales.exists())
