"""AI-INTELLIGENCE-02 — analytical capability layer.

Covers the four real questions the chat MVP (AI-INTELLIGENCE-01) could not
answer (comparison, aggregation by period, ranking by month, ranking by
machinery), plus the edge cases the mission explicitly calls out: período
sin datos, unidad incompatible, entidad inexistente, nombre ambiguo, una
sola obra, cross-tenant, datos incompletos, empate de ranking. Also covers
the evidence/quality/factor axis-separation fix (never conflate "no
evidence" with "no environmental factor").
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.analytics.models import (
    ActividadOperacional, EventoMaterial, FuenteDatos, MaterialOperacional, Obra, Observacion,
    Organizacion, UsuarioOrganizacion,
)
from apps.ai import analytics_tools, periods, resolvers, tools

User = get_user_model()


def _make_reception(org, *, material, obra, source, cantidad, unidad, when, admin=None):
    when = timezone.make_aware(timezone.datetime.combine(when, timezone.datetime.min.time()))
    activity = ActividadOperacional.objects.create(
        organizacion=org, obra=obra, codigo=f"EVT-{material.pk}-{obra.pk}-{when.isoformat()}-{cantidad}",
        nombre="Recepción de prueba", tipo=ActividadOperacional.Tipo.MOVIMIENTO_MATERIAL,
        timestamp_inicio=when,
    )
    observation = Observacion.objects.create(
        organizacion=org, actividad=activity, fuente=source, concepto="cantidad_material",
        valor_numerico=cantidad, unidad=unidad, timestamp_observacion=when,
        estado=Observacion.Estado.VALIDADA,
    )
    return EventoMaterial.objects.create(
        organizacion=org, material=material, actividad=activity, obra=obra,
        tipo=EventoMaterial.Tipo.RECEPCION, fecha_hora=when, observacion_cantidad=observation, fuente=source,
    )


class PeriodsResolutionTests(TestCase):
    def test_no_arguments_means_no_filter(self):
        self.assertEqual(periods.resolve_period(), (None, None))

    def test_explicit_dates_are_used_verbatim(self):
        start, end = periods.resolve_period(date_from="2026-01-01", date_to="2026-01-31")
        self.assertEqual(start, date(2026, 1, 1))
        self.assertEqual(end, date(2026, 1, 31))

    def test_relative_months_computed_from_a_fixed_today(self):
        today = date(2026, 3, 15)
        start, end = periods.resolve_period(relative_months=3, today=today)
        self.assertEqual(end, today)
        self.assertEqual(start, date(2025, 12, 16))

    def test_month_clamping_at_a_short_month_boundary(self):
        # Mar 31 minus 1 calendar month must land on Feb's last valid day.
        self.assertEqual(periods._months_ago(date(2026, 3, 31), 1), date(2026, 2, 28))


class ResolversUnitTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Resolvers org")
        self.other_org = Organizacion.objects.create(nombre="Resolvers org B")
        self.admin = User.objects.create_user("resolvers-admin", "resolvers-admin@example.com", "pw")
        UsuarioOrganizacion.objects.create(user=self.admin, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN)

    def test_resolve_obra_not_found_is_not_an_error(self):
        result = resolvers.resolve_obra(self.org, self.admin, "Obra que no existe XYZ")
        self.assertEqual(result["status"], "not_found")

    def test_resolve_obra_ambiguous_returns_candidates(self):
        Obra.objects.create(organizacion=self.org, nombre="Edificio Norte Uno", fecha_inicio=date.today())
        Obra.objects.create(organizacion=self.org, nombre="Edificio Norte Dos", fecha_inicio=date.today())
        result = resolvers.resolve_obra(self.org, self.admin, "Edificio Norte")
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(len(result["candidates"]), 2)

    def test_resolve_obra_never_crosses_tenants(self):
        Obra.objects.create(organizacion=self.other_org, nombre="Obra ajena", fecha_inicio=date.today())
        result = resolvers.resolve_obra(self.org, self.admin, "Obra ajena")
        self.assertEqual(result["status"], "not_found")

    def test_resolve_obra_respects_obra_scoped_rbac(self):
        allowed = Obra.objects.create(organizacion=self.org, nombre="Obra permitida", fecha_inicio=date.today())
        Obra.objects.create(organizacion=self.org, nombre="Obra restringida", fecha_inicio=date.today())
        scoped_user = User.objects.create_user("resolvers-scoped", "resolvers-scoped@example.com", "pw")
        membership = UsuarioOrganizacion.objects.create(
            user=scoped_user, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ANALISTA,
            alcance=UsuarioOrganizacion.Alcance.OBRAS,
        )
        from apps.analytics.models import UsuarioObraAcceso

        UsuarioObraAcceso.objects.create(usuario_organizacion=membership, obra=allowed)
        result = resolvers.resolve_obra(self.org, scoped_user, "Obra")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["match"]["id"], allowed.pk)

    def test_resolve_material_ambiguous_name(self):
        MaterialOperacional.objects.create(organizacion=self.org, codigo="M1", nombre="Hormigón H20", categoria="materiales", unidad_base="m3")
        MaterialOperacional.objects.create(organizacion=self.org, codigo="M2", nombre="Hormigón H30", categoria="materiales", unidad_base="m3")
        result = resolvers.resolve_material(self.org, "Hormigón")
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(len(result["candidates"]), 2)

    def test_resolve_material_by_categoria(self):
        MaterialOperacional.objects.create(organizacion=self.org, codigo="M3", nombre="Agua de faena", categoria="agua", unidad_base="m3")
        result = resolvers.resolve_material(self.org, "agua")
        self.assertEqual(result["status"], "resolved")


class RankAndCompareEdgeCaseTests(TestCase):
    """Custom, minimal fixtures for cases the demo tenant seed doesn't
    exercise directly: unidad incompatible, empate, una sola obra,
    cross-tenant, período sin datos."""

    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Edge org")
        self.other_org = Organizacion.objects.create(nombre="Edge org B")
        self.admin = User.objects.create_user("edge-admin", "edge-admin@example.com", "pw")
        UsuarioOrganizacion.objects.create(user=self.admin, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN)
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Fuente edge", tipo="manual")

    def test_periodo_sin_datos_returns_ok_with_zero_coverage(self):
        obra = Obra.objects.create(organizacion=self.org, nombre="Obra vacía", fecha_inicio=date.today())
        result = tools.get_operational_aggregate(
            self.org, self.admin, obra_id=obra.id, metric="agua", date_from="2020-01-01", date_to="2020-03-31",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["por_unidad"], {})
        self.assertEqual(result["cobertura"]["periodos_con_datos"], 0)
        self.assertEqual(result["cobertura"]["periodos_totales"], 3)

    def test_unidad_incompatible_never_mixed_in_one_total(self):
        obra = Obra.objects.create(organizacion=self.org, nombre="Obra mixta", fecha_inicio=date.today())
        hormigon = MaterialOperacional.objects.create(organizacion=self.org, codigo="H1", nombre="Hormigón", categoria="materiales", unidad_base="m3")
        acero = MaterialOperacional.objects.create(organizacion=self.org, codigo="A1", nombre="Acero", categoria="materiales", unidad_base="ton")
        today = date.today()
        _make_reception(self.org, material=hormigon, obra=obra, source=self.source, cantidad=Decimal("10"), unidad="m3", when=today)
        _make_reception(self.org, material=acero, obra=obra, source=self.source, cantidad=Decimal("5"), unidad="ton", when=today)
        result = tools.get_operational_aggregate(self.org, self.admin, obra_id=obra.id, categoria="materiales")
        self.assertTrue(result["ok"])
        self.assertIn("m3", result["por_unidad"])
        self.assertIn("ton", result["por_unidad"])
        self.assertEqual(result["por_unidad"]["m3"]["total"], Decimal("10"))
        self.assertEqual(result["por_unidad"]["ton"]["total"], Decimal("5"))

    def test_entidad_inexistente_is_not_found_not_an_error(self):
        result = tools.resolve_entity(self.org, self.admin, entity_type="obra", query="No existe esta obra")
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["status"], "not_found")

    def test_una_sola_obra_compares_cleanly(self):
        material = MaterialOperacional.objects.create(organizacion=self.org, codigo="M1", nombre="Agua", categoria="agua", unidad_base="m3")
        obra = Obra.objects.create(organizacion=self.org, nombre="Única obra", fecha_inicio=date.today())
        _make_reception(self.org, material=material, obra=obra, source=self.source, cantidad=Decimal("50"), unidad="m3", when=date.today())
        result = tools.compare_projects(self.org, self.admin, metric="agua")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["comparacion"]), 1)
        self.assertEqual(result["obra_con_mayor_valor"]["obra_id"], obra.id)

    def test_empate_de_ranking_is_never_silently_broken(self):
        material = MaterialOperacional.objects.create(organizacion=self.org, codigo="M1", nombre="Agua", categoria="agua", unidad_base="m3")
        obra_a = Obra.objects.create(organizacion=self.org, nombre="Obra A", fecha_inicio=date.today())
        obra_b = Obra.objects.create(organizacion=self.org, nombre="Obra B", fecha_inicio=date.today())
        today = date.today()
        _make_reception(self.org, material=material, obra=obra_a, source=self.source, cantidad=Decimal("100"), unidad="m3", when=today)
        _make_reception(self.org, material=material, obra=obra_b, source=self.source, cantidad=Decimal("100"), unidad="m3", when=today)
        result = tools.rank_operational_entities(self.org, self.admin, entity_type="obra", metric="agua")
        self.assertTrue(result["ok"])
        top_value = result["ranking"][0]["valor"]
        tied = [row for row in result["ranking"] if row["valor"] == top_value]
        self.assertEqual(len(tied), 2)

    def test_cross_tenant_ranking_never_leaks_another_orgs_obra(self):
        material_a = MaterialOperacional.objects.create(organizacion=self.org, codigo="M1", nombre="Agua", categoria="agua", unidad_base="m3")
        source_b = FuenteDatos.objects.create(organizacion=self.other_org, nombre="Fuente B", tipo="manual")
        material_b = MaterialOperacional.objects.create(organizacion=self.other_org, codigo="M1B", nombre="Agua B", categoria="agua", unidad_base="m3")
        obra_a = Obra.objects.create(organizacion=self.org, nombre="Obra propia", fecha_inicio=date.today())
        obra_b = Obra.objects.create(organizacion=self.other_org, nombre="Obra ajena", fecha_inicio=date.today())
        today = date.today()
        _make_reception(self.org, material=material_a, obra=obra_a, source=self.source, cantidad=Decimal("999"), unidad="m3", when=today)
        _make_reception(self.other_org, material=material_b, obra=obra_b, source=source_b, cantidad=Decimal("999"), unidad="m3", when=today)
        result = tools.rank_operational_entities(self.org, self.admin, entity_type="obra", metric="agua")
        self.assertTrue(result["ok"])
        names = [row["nombre"] for row in result["ranking"]]
        self.assertIn("Obra propia", names)
        self.assertNotIn("Obra ajena", names)

    def test_obra_scoped_user_never_sees_a_restricted_obra_in_ranking(self):
        material = MaterialOperacional.objects.create(organizacion=self.org, codigo="M1", nombre="Agua", categoria="agua", unidad_base="m3")
        visible = Obra.objects.create(organizacion=self.org, nombre="Obra visible", fecha_inicio=date.today())
        hidden = Obra.objects.create(organizacion=self.org, nombre="Obra oculta", fecha_inicio=date.today())
        today = date.today()
        _make_reception(self.org, material=material, obra=visible, source=self.source, cantidad=Decimal("10"), unidad="m3", when=today)
        _make_reception(self.org, material=material, obra=hidden, source=self.source, cantidad=Decimal("999"), unidad="m3", when=today)
        scoped_user = User.objects.create_user("edge-scoped", "edge-scoped@example.com", "pw")
        membership = UsuarioOrganizacion.objects.create(
            user=scoped_user, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ANALISTA,
            alcance=UsuarioOrganizacion.Alcance.OBRAS,
        )
        from apps.analytics.models import UsuarioObraAcceso

        UsuarioObraAcceso.objects.create(usuario_organizacion=membership, obra=visible)
        result = tools.rank_operational_entities(self.org, scoped_user, entity_type="obra", metric="agua")
        self.assertTrue(result["ok"])
        names = [row["nombre"] for row in result["ranking"]]
        self.assertIn("Obra visible", names)
        self.assertNotIn("Obra oculta", names)


class EvidenceQualityAxesTests(TestCase):
    """Requirement 7's fix, verified directly: evidence-absence, data
    quality, and factor-mapping-absence must never be reported as one
    combined fact."""

    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Evidence org")
        self.admin = User.objects.create_user("evidence-admin", "evidence-admin@example.com", "pw")
        UsuarioOrganizacion.objects.create(user=self.admin, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN)
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Fuente evidencia", tipo="manual")
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="EV1", nombre="Material sin mapear", categoria="materiales", unidad_base="kg",
        )

    def test_no_consumption_record_at_all(self):
        result = tools.get_evidence_quality(self.org, self.admin, material_id=self.material.pk)
        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["registro_consumo"]["existe"])
        self.assertFalse(result["data"]["evidencia_operacional"]["existe"])
        self.assertFalse(result["data"]["factor_ambiental"]["mapeado"])

    def test_consumption_exists_but_no_evidence_and_no_factor_are_reported_separately(self):
        obra = Obra.objects.create(organizacion=self.org, nombre="Obra evidencia", fecha_inicio=date.today())
        _make_reception(self.org, material=self.material, obra=obra, source=self.source, cantidad=Decimal("5"), unidad="kg", when=date.today())
        result = tools.get_evidence_quality(self.org, self.admin, material_id=self.material.pk)
        self.assertTrue(result["ok"])
        data = result["data"]
        # The bug this fixes: consumption exists (a) but neither evidence (b)
        # nor a factor (d) do — these must stay three distinct facts.
        self.assertTrue(data["registro_consumo"]["existe"])
        self.assertFalse(data["evidencia_operacional"]["existe"])
        self.assertFalse(data["factor_ambiental"]["mapeado"])
        self.assertNotEqual(data["evidencia_operacional"], data["factor_ambiental"])


class DemoTenantRealQuestionsTests(TestCase):
    """The four real questions from the mission brief, run against the
    actual synthetic demo tenant (never a bespoke fixture) so this proves
    the fix on the same data the user tested manually."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_ai_demo_tenant")
        cls.org = Organizacion.objects.get(organizacion_id="DEMO_HORIZONTE")
        membership = UsuarioOrganizacion.objects.filter(organizacion=cls.org).select_related("user").first()
        cls.admin = membership.user
        cls.obra_norte = Obra.objects.get(organizacion=cls.org, nombre="Edificio Horizonte Norte")

    def test_q1_cual_obra_tiene_mayor_impacto_y_por_que(self):
        result = tools.compare_projects(self.org, self.admin)
        self.assertTrue(result["ok"])
        self.assertEqual(result["obra_con_mayor_valor"]["nombre"], "Edificio Horizonte Norte")
        self.assertIsNotNone(result["por_que"])
        self.assertIn("principal_contribuyente", result["por_que"])

    def test_q2_consumo_total_de_agua_ultimos_3_meses(self):
        result = tools.get_operational_aggregate(
            self.org, self.admin, obra_id=self.obra_norte.id, metric="agua", relative_months=3,
        )
        self.assertTrue(result["ok"])
        self.assertIn("m3", result["por_unidad"])
        self.assertGreater(result["por_unidad"]["m3"]["total"], 0)

    def test_q3_mes_de_mayor_consumo_de_agua(self):
        result = tools.rank_operational_entities(
            self.org, self.admin, entity_type="periodo", metric="agua", obra_id=self.obra_norte.id, relative_months=4,
        )
        self.assertTrue(result["ok"])
        self.assertGreater(len(result["ranking"]), 0)
        self.assertEqual(result["ranking"][0]["unidad"], "m3")

    def test_q4_que_maquinaria_consumio_mas_combustible(self):
        result = tools.rank_operational_entities(
            self.org, self.admin, entity_type="activo", metric="combustible", obra_id=self.obra_norte.id,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["ranking"]), 2)
        self.assertEqual(result["ranking"][0]["nombre"], "Excavadora Hidráulica EX-14")
        self.assertGreater(result["ranking"][0]["valor"], result["ranking"][1]["valor"])

    def test_datos_incompletos_water_gap_in_most_recent_month_is_visible(self):
        # The seed deliberately skips water in the most recent month so the
        # assistant must say "sin dato" rather than invent a value.
        result = tools.get_operational_timeseries(
            self.org, self.admin, obra_id=self.obra_norte.id, metric="agua", relative_months=4,
        )
        self.assertTrue(result["ok"])
        self.assertFalse(result["serie"][-1]["con_datos"])
        self.assertLess(result["cobertura"]["periodos_con_datos"], result["cobertura"]["periodos_totales"])

    def test_resolve_entity_never_forces_the_model_to_ask_for_an_id(self):
        result = tools.resolve_entity(self.org, self.admin, entity_type="obra", query="Horizonte Norte")
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["status"], "resolved")
        self.assertEqual(result["data"]["match"]["id"], self.obra_norte.id)
