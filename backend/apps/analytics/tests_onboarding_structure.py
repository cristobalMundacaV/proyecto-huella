from django.contrib.auth.models import User
from django.test import TestCase

from .models import AreaCapacidadAmbiental, AreaOperacional, DiagnosticoAmbientalInicial, Organizacion
from .services.onboarding import FLOW_CATALOG, apply_onboarding_step, area_catalog_for


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

    def test_environmental_catalog_excludes_assets_and_processes(self):
        self.assertNotIn("maquinaria", FLOW_CATALOG)
        self.assertNotIn("procesos_productivos", FLOW_CATALOG)
        self.assertIn("residuos_no_peligrosos", FLOW_CATALOG)
        self.assertIn("residuos_peligrosos", FLOW_CATALOG)
        self.assertIn("emisiones_atmosfericas", FLOW_CATALOG)
        self.assertIn("suelo", FLOW_CATALOG)

    def test_requires_at_least_one_environmental_aspect(self):
        with self.assertRaisesMessage(ValueError, "Selecciona al menos un aspecto ambiental"):
            apply_onboarding_step(self.organization, self.user, 3, {"flujos": {}})

    def test_onboarding_flow_selection_does_not_assign_areas(self):
        AreaOperacional.objects.create(organizacion=self.organization, nombre="Bodega", tipo="bodega")
        apply_onboarding_step(self.organization, self.user, 3, {"flujos": {"residuos_peligrosos": "no_seguro"}})
        self.assertFalse(AreaCapacidadAmbiental.objects.filter(area__organizacion=self.organization).exists())

    def _prepare_diagnostic(self):
        apply_onboarding_step(self.organization, self.user, 3, {"flujos": {"agua": "no_seguro"}})
        return {"flujos": {"agua": {"disponibilidad": "suficiente", "fuentes": ["documentos", "medidores"], "evidencia": "si", "trazabilidad": {"origen": "si", "fecha": "si", "responsable": "parcial", "historico": "si"}, "validacion_profesional": "no"}}}

    def test_diagnostic_progress_and_multiple_sources_are_persisted(self):
        payload = self._prepare_diagnostic()
        apply_onboarding_step(self.organization, self.user, 4, {**payload, "subfase": 2})
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.onboarding_step, 4)
        self.assertEqual(self.organization.onboarding_data["4"]["flujos"]["agua"]["fuentes"], ["documentos", "medidores"])

    def test_diagnostic_completion_is_idempotent_and_scoped_to_tenant(self):
        payload = self._prepare_diagnostic()
        apply_onboarding_step(self.organization, self.user, 4, {**payload, "subfase": 4, "completado": True})
        apply_onboarding_step(self.organization, self.user, 4, {**payload, "subfase": 4, "completado": True})
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.onboarding_step, 5)
        self.assertEqual(DiagnosticoAmbientalInicial.objects.filter(organizacion=self.organization).count(), 1)
        self.assertFalse(DiagnosticoAmbientalInicial.objects.exclude(organizacion=self.organization).exists())

    def test_flow_without_information_does_not_require_sources(self):
        apply_onboarding_step(self.organization, self.user, 3, {"flujos": {"ruido": "no_seguro"}})
        payload = {"flujos": {"ruido": {"disponibilidad": "sin_informacion", "fuentes": [], "evidencia": "no"}}, "subfase": 4, "completado": True}
        apply_onboarding_step(self.organization, self.user, 4, payload)
        self.assertTrue(DiagnosticoAmbientalInicial.objects.filter(organizacion=self.organization).exists())
