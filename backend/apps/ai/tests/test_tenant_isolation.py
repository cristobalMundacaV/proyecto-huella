"""AI-INTELLIGENCE-01 — explicit cross-tenant isolation tests (mission
section 3): a conversation must never surface another organization's data,
even when the (simulated) LLM itself tries to request it via a tool call
naming a foreign material_id."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.analytics.models import MaterialOperacional, Organizacion, UsuarioOrganizacion
from apps.ai.models import Conversation
from apps.ai.orchestrator import run_turn
from apps.ai.providers import AIChatResult, ToolCallRequest

User = get_user_model()


class FakeProviderRequestingForeignMaterial:
    name = "fake"
    model = "fake/model"
    available = True

    def __init__(self, foreign_material_id):
        self._foreign_material_id = foreign_material_id
        self._step = 0

    def chat(self, *, messages, tools=None):
        self._step += 1
        if self._step == 1:
            return AIChatResult(
                content=None,
                tool_calls=[ToolCallRequest(id="call_1", name="get_material_summary",
                                            arguments={"material_id": self._foreign_material_id})],
                model=self.model,
            )
        return AIChatResult(content="No encontré ese material en tu organización.", tool_calls=[], model=self.model)


class CrossTenantIsolationTests(TestCase):
    def setUp(self):
        self.org_a = Organizacion.objects.create(nombre="Tenant A")
        self.org_b = Organizacion.objects.create(nombre="Tenant B")
        self.user_a = User.objects.create_user("tenant-a-user", "tenant-a-user@example.com", "pw")
        UsuarioOrganizacion.objects.create(user=self.user_a, organizacion=self.org_a, rol=UsuarioOrganizacion.Rol.ADMIN)
        self.material_b = MaterialOperacional.objects.create(
            organizacion=self.org_b, codigo="TENANT-B-MAT", nombre="Material secreto de Tenant B",
            categoria="materiales", unidad_base="kg",
        )

    def test_llm_requesting_another_tenants_material_id_never_leaks_it(self):
        conversation = Conversation.objects.create(organizacion=self.org_a, usuario=self.user_a)
        provider = FakeProviderRequestingForeignMaterial(self.material_b.pk)
        reply = run_turn(
            conversation=conversation, organization=self.org_a, user=self.user_a,
            user_message="Dame el resumen del material de la otra empresa",
            provider=provider,
        )
        tool_message = conversation.messages.get(role="tool")
        self.assertFalse(tool_message.tool_result["ok"])
        self.assertEqual(tool_message.tool_result["error"], "not_found")
        self.assertNotIn("Material secreto de Tenant B", reply.content)
        self.assertEqual(reply.provenance, [])

    def test_conversation_from_org_a_is_invisible_when_queried_scoped_to_org_b(self):
        conversation = Conversation.objects.create(organizacion=self.org_a, usuario=self.user_a)
        self.assertFalse(Conversation.objects.filter(pk=conversation.pk, organizacion=self.org_b).exists())

    def test_obra_from_a_different_organization_is_rejected_on_the_conversation(self):
        from apps.analytics.models import Obra
        from datetime import date

        foreign_obra = Obra.objects.create(organizacion=self.org_b, nombre="Obra de Tenant B", fecha_inicio=date.today())
        conversation = Conversation(organizacion=self.org_a, usuario=self.user_a, obra=foreign_obra)
        with self.assertRaises(Exception):
            conversation.full_clean()
