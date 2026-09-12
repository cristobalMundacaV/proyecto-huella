"""AI-INTELLIGENCE-01 — tools: tenant isolation, RBAC, structured results."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.analytics.models import MaterialOperacional, Organizacion, ProblematicaAmbiental, UsuarioOrganizacion
from apps.ai import tools

User = get_user_model()


class ToolsTenantAndRbacTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="AI tools org A")
        self.other_org = Organizacion.objects.create(nombre="AI tools org B")
        self.admin = User.objects.create_user("ai-tools-admin", "ai-tools-admin@example.com", "pw")
        UsuarioOrganizacion.objects.create(user=self.admin, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN)
        self.lector = User.objects.create_user("ai-tools-lector", "ai-tools-lector@example.com", "pw")
        UsuarioOrganizacion.objects.create(user=self.lector, organizacion=self.org, rol=UsuarioOrganizacion.Rol.LECTOR)
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="AI-MAT-1", nombre="Material de prueba",
            categoria="materiales", unidad_base="kg",
        )
        self.other_material = MaterialOperacional.objects.create(
            organizacion=self.other_org, codigo="AI-MAT-OTHER", nombre="Material de otra organización",
            categoria="materiales", unidad_base="kg",
        )

    def test_get_current_organization_returns_own_tenant_only(self):
        result = tools.get_current_organization(self.org, self.admin)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["organizacion_id"], self.org.organizacion_id)

    def test_list_projects_returns_own_tenant_obras_only(self):
        from datetime import date
        from apps.analytics.models import Obra

        Obra.objects.create(organizacion=self.org, nombre="Obra propia", fecha_inicio=date.today())
        Obra.objects.create(organizacion=self.other_org, nombre="Obra ajena", fecha_inicio=date.today())
        result = tools.list_projects(self.org, self.admin)
        self.assertTrue(result["ok"])
        names = [row["nombre"] for row in result["data"]["obras"]]
        self.assertIn("Obra propia", names)
        self.assertNotIn("Obra ajena", names)

    def test_material_from_another_tenant_is_not_found_not_leaked(self):
        result = tools.get_material_summary(self.org, self.admin, material_id=self.other_material.pk)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "not_found")

    def test_ec3_mapping_status_from_another_tenant_is_not_found(self):
        result = tools.get_ec3_mapping_status(self.org, self.admin, material_id=self.other_material.pk)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "not_found")

    def test_evidence_quality_rbac_denied_without_permission(self):
        # LECTOR has EVIDENCE_VIEW via VIEW_PERMISSIONS, so simulate a role
        # lacking it is not directly expressible with existing roles — this
        # instead proves the guard actually fires for an unrelated permission
        # by revoking membership entirely (no membership => no permission).
        stranger = User.objects.create_user("ai-tools-stranger", "ai-tools-stranger@example.com", "pw")
        result = tools.get_evidence_quality(self.org, stranger, material_id=self.material.pk)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "permission_denied")

    def test_missing_argument_is_reported_not_guessed(self):
        result = tools.get_material_summary(self.org, self.admin, material_id=None)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "missing_argument")

    def test_get_open_alerts_only_returns_own_tenant_problems(self):
        ProblematicaAmbiental.objects.create(
            organizacion=self.org, titulo="Problema propio", descripcion="d", categoria="materiales",
            valor_inicial=10, objetivo_meta=5, fecha_deteccion=timezone.now().date(), estado=ProblematicaAmbiental.Estado.DETECTADA,
            nivel_riesgo=ProblematicaAmbiental.Riesgo.ALTO,
        )
        ProblematicaAmbiental.objects.create(
            organizacion=self.other_org, titulo="Problema ajeno", descripcion="d", categoria="materiales",
            valor_inicial=10, objetivo_meta=5, fecha_deteccion=timezone.now().date(), estado=ProblematicaAmbiental.Estado.DETECTADA,
            nivel_riesgo=ProblematicaAmbiental.Riesgo.CRITICO,
        )
        result = tools.get_open_alerts(self.org, self.admin)
        self.assertTrue(result["ok"])
        titles = [row["titulo"] for row in result["data"]["alertas"]]
        self.assertIn("Problema propio", titles)
        self.assertNotIn("Problema ajeno", titles)

    def test_open_alerts_excludes_closed_problems(self):
        ProblematicaAmbiental.objects.create(
            organizacion=self.org, titulo="Cerrada", descripcion="d", categoria="materiales",
            valor_inicial=10, objetivo_meta=5, fecha_deteccion=timezone.now().date(), estado=ProblematicaAmbiental.Estado.CERRADA,
            nivel_riesgo=ProblematicaAmbiental.Riesgo.BAJO,
        )
        result = tools.get_open_alerts(self.org, self.admin)
        titles = [row["titulo"] for row in result["data"]["alertas"]]
        self.assertNotIn("Cerrada", titles)

    def test_search_environmental_knowledge_requires_query(self):
        result = tools.search_environmental_knowledge(self.org, self.admin, query="")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "missing_argument")

    def test_search_environmental_knowledge_finds_real_sources_and_records(self):
        from apps.knowledge.models import EnvironmentalSource, ExternalRecord, ExternalSnapshot, SyncRun

        source = EnvironmentalSource.objects.create(
            codigo="ai-tools-source", nombre="RETC Ambiental de prueba", organismo="Prueba",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test", stale_after_hours=10,
        )
        run = SyncRun.objects.create(source=source, trigger="manual", started_at=timezone.now())
        snapshot = ExternalSnapshot.objects.create(
            source=source, sync_run=run, external_id="rec-1", content_hash="h1", record_kind="test",
            source_url="https://example.org/rec-1", retrieved_at=timezone.now(),
            content_type="application/json",
        )
        ExternalRecord.objects.create(
            source=source, external_id="rec-1", kind="test", title="Registro RETC de prueba",
            current_snapshot=snapshot, first_seen_at=timezone.now(), last_seen_at=timezone.now(),
        )
        result = tools.search_environmental_knowledge(self.org, self.admin, query="RETC Ambiental de prueba")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["data"]["fuentes"]), 1)
        self.assertEqual(result["data"]["fuentes"][0]["codigo"], "ai-tools-source")
        result_records = tools.search_environmental_knowledge(self.org, self.admin, query="Registro RETC de prueba")
        self.assertEqual(len(result_records["data"]["registros"]), 1)

    def test_unknown_tool_is_reported_cleanly(self):
        result = tools.execute_tool("not_a_real_tool", organization=self.org, user=self.admin, arguments={})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "unknown_tool")

    def test_execute_tool_never_raises_for_permission_denied(self):
        stranger = User.objects.create_user("ai-tools-stranger2", "ai-tools-stranger2@example.com", "pw")
        result = tools.execute_tool(
            "get_evidence_quality", organization=self.org, user=stranger,
            arguments={"material_id": self.material.pk},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "permission_denied")

    def test_all_tool_schemas_are_valid_openai_function_shape(self):
        schemas = tools.openai_tool_schemas()
        self.assertEqual(len(schemas), len(tools.TOOLS))
        for schema in schemas:
            self.assertEqual(schema["type"], "function")
            self.assertIn("name", schema["function"])
            self.assertIn("description", schema["function"])
            self.assertIn("parameters", schema["function"])
            self.assertEqual(schema["function"]["parameters"]["type"], "object")
