"""AI-INTELLIGENCE-01 — seed_ai_demo_tenant: idempotent, produces every
scenario the demo/test-matrix docs rely on (hotspot, alert, EC3 mapping,
EC3 potential opportunity, an incomplete indicator)."""
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.analytics.models import IndicadorAmbiental, MaterialOperacional, Organizacion, ProblematicaAmbiental
from apps.ai.tools import get_material_hotspots


class SeedAiDemoTenantTests(TestCase):
    def test_seed_is_idempotent_and_produces_every_required_scenario(self):
        call_command("seed_ai_demo_tenant")
        call_command("seed_ai_demo_tenant")  # must not raise or duplicate

        org = Organizacion.objects.get(organizacion_id="DEMO_HORIZONTE")
        self.assertEqual(MaterialOperacional.objects.filter(organizacion=org).count(), 6)

        alerts = ProblematicaAmbiental.objects.filter(organizacion=org).exclude(estado="cerrada")
        self.assertEqual(alerts.count(), 1)

        material = MaterialOperacional.objects.get(organizacion=org, codigo="HORIZONTE-HORMIGON")
        self.assertTrue(material.ec3_candidates.filter(promoted_version__isnull=False).exists())
        self.assertTrue(material.ec3_candidates.filter(promoted_version__isnull=True).exists())

        incomplete = IndicadorAmbiental.objects.get(organizacion=org, codigo="agua_intensidad_demo")
        self.assertFalse(incomplete.valores.exists())

        admin = get_user_model().objects.get(username="demo-horizonte-admin")
        hotspots = get_material_hotspots(org, admin)["data"]
        rows = hotspots["kgCO2e"]["materiales"]
        self.assertEqual(rows[0]["material_label"], "HORIZONTE-HORMIGON")
        self.assertGreater(float(rows[0]["hotspot_share"]), 0.5)

    def test_reset_removes_the_demo_tenant(self):
        call_command("seed_ai_demo_tenant")
        call_command("seed_ai_demo_tenant", "--reset")
        self.assertTrue(Organizacion.objects.filter(organizacion_id="DEMO_HORIZONTE").exists())
