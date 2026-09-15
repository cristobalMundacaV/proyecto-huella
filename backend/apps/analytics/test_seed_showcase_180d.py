from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.analytics.models import ActividadOperacional, Obra, Organizacion, RegistroFlujoAmbiental, ValorIndicador
from apps.analytics.services.obra_environmental_dashboard import build_obra_dashboard
from apps.analytics.services.organization_environmental_dashboard import build_organization_dashboard
from apps.analytics.services.obra_report import build_report_sections
from apps.iot.models import DispositivoSensor, LecturaSensorV2


class Showcase180DSeedTests(TestCase):
    def test_seed_is_idempotent_tenant_scoped_and_covers_six_months(self):
        foreign = Organizacion.objects.create(
            organizacion_id="TENANT_AJENO_SHOWCASE", nombre="Tenant ajeno", preset="construccion",
        )
        output = StringIO()
        call_command("seed_showcase_180d", end_date="2026-09-15", stdout=output)
        print("SHOWCASE SUMMARY", output.getvalue().strip())
        org = Organizacion.objects.get(organizacion_id="DEMO_HORIZONTE")
        self.assertTrue(org.onboarding_completado)
        self.assertEqual(Obra.objects.filter(organizacion=org).count(), 3)
        self.assertEqual(org.usuarios.count(), 6)
        self.assertGreaterEqual(org.activos_operacionales.count(), 12)
        self.assertGreaterEqual(DispositivoSensor.objects.filter(organizacion=org).count(), 8)
        self.assertGreater(LecturaSensorV2.objects.filter(sensor__organizacion=org).count(), 100)
        rows = ActividadOperacional.objects.filter(organizacion=org, codigo__startswith="CZ180")
        self.assertGreater(rows.count(), 300)
        self.assertEqual((rows.order_by("-timestamp_inicio").first().timestamp_inicio.date() -
                          rows.order_by("timestamp_inicio").first().timestamp_inicio.date()).days, 179)
        north = Obra.objects.get(organizacion=org, nombre="Edificio Horizonte Norte")
        self.assertEqual(north.diagnosticos_ambientales.get().estado, "completado")
        self.assertGreaterEqual(ValorIndicador.objects.filter(indicador__organizacion=org,
            indicador__obra=north, indicador__codigo="cz180-energia").count(), 6)
        self.assertGreater(org.documentos_ambientales.count(), 10)
        admin = org.usuarios.get(rol="admin").user
        obra_dashboard = build_obra_dashboard(org, admin, north, date_from="2026-03-20", date_to="2026-09-15")
        portfolio = build_organization_dashboard(org, admin, date_from="2026-03-20", date_to="2026-09-15")
        self.assertGreater(obra_dashboard["kpis"]["huella_total_tco2e"], 0)
        self.assertEqual(portfolio["obras_activas"], 3)
        self.assertEqual(len(build_report_sections(obra_dashboard)), 21)
        energy = ValorIndicador.objects.filter(indicador__organizacion=org, indicador__obra=north,
            indicador__codigo="cz180-energia").order_by("periodo_inicio")
        self.assertGreaterEqual(energy.count(), 6)
        self.assertGreater(len(set(energy.values_list("valor", flat=True))), 2)
        for flow in ("energia", "agua", "combustible_movil", "residuo", "ruido", "emisiones_atmosfericas", "suelo"):
            self.assertTrue(RegistroFlujoAmbiental.objects.filter(organizacion=org, flujo=flow).exists(), flow)
        before = (rows.count(), org.evidencias.count(), org.documentos_ambientales.count(), org.activos_operacionales.count(),
                  LecturaSensorV2.objects.filter(sensor__organizacion=org).count())
        call_command("seed_showcase_180d", end_date="2026-09-15", stdout=StringIO())
        self.assertEqual(before, (rows.count(), org.evidencias.count(), org.documentos_ambientales.count(), org.activos_operacionales.count(),
                                  LecturaSensorV2.objects.filter(sensor__organizacion=org).count()))
        self.assertEqual(Organizacion.objects.filter(organizacion_id=foreign.organizacion_id).count(), 1)
        self.assertFalse(ActividadOperacional.objects.filter(organizacion=foreign, codigo__startswith="CZ180").exists())
        with self.assertRaises(CommandError):
            call_command("seed_showcase_180d", end_date="2026-09-14", stdout=StringIO())
        call_command("seed_showcase_180d", verify_only=True, stdout=StringIO())
