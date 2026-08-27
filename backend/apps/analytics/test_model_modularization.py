from datetime import date

from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

import apps.analytics.models as public_models
from apps.analytics.models import (
    ActividadOperacional,
    CalculoAmbiental,
    AreaOperacional,
    EspacioTrabajoOperacional,
    EtapaObra,
    EventoAuditoriaSaaS,
    FactorAmbiental,
    Organizacion,
    Obra,
    ProcesoOperacional,
    RegistroFlujoAmbiental,
    SuscripcionSaaS,
    UsuarioObraAcceso,
    UsuarioOrganizacion,
    UnidadOperacional,
)


PLATFORM_MODELS = (
    Organizacion,
    SuscripcionSaaS,
    EventoAuditoriaSaaS,
    UsuarioOrganizacion,
    UsuarioObraAcceso,
)

EXPECTED_TABLES = {
    Organizacion: "analytics_organizacion",
    SuscripcionSaaS: "analytics_suscripcionsaas",
    EventoAuditoriaSaaS: "analytics_eventoauditoriasaas",
    UsuarioOrganizacion: "analytics_usuarioorganizacion",
    UsuarioObraAcceso: "analytics_usuarioobraacceso",
}

OPERATIONAL_CONTEXT_MODELS = (
    EtapaObra,
    Obra,
    AreaOperacional,
    EspacioTrabajoOperacional,
    UnidadOperacional,
    ProcesoOperacional,
)

OPERATIONAL_CONTEXT_TABLES = {
    EtapaObra: "analytics_etapaobra",
    Obra: "analytics_obra",
    AreaOperacional: "analytics_areaoperacional",
    EspacioTrabajoOperacional: "analytics_espaciotrabajooperacional",
    UnidadOperacional: "analytics_unidadoperacional",
    ProcesoOperacional: "analytics_procesooperacional",
}


class ModelModularizationContractTests(SimpleTestCase):
    def test_platform_models_live_in_platform_module(self):
        for model in PLATFORM_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.__module__, "apps.analytics.models.platform")

    def test_platform_models_keep_app_label_and_database_table(self):
        for model in PLATFORM_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, EXPECTED_TABLES[model])

    def test_public_models_api_reexports_platform_models(self):
        for model in PLATFORM_MODELS:
            with self.subTest(model=model.__name__):
                self.assertIs(getattr(public_models, model.__name__), model)

    def test_public_models_api_still_exports_unmoved_models(self):
        for model in (
            ActividadOperacional,
            RegistroFlujoAmbiental,
            FactorAmbiental,
            CalculoAmbiental,
        ):
            with self.subTest(model=model.__name__):
                self.assertIs(getattr(public_models, model.__name__), model)

    def test_operational_context_models_live_in_owner_module(self):
        for model in OPERATIONAL_CONTEXT_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(
                    model.__module__, "apps.analytics.models.operational_context"
                )

    def test_operational_context_models_keep_app_label_and_database_table(self):
        for model in OPERATIONAL_CONTEXT_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, OPERATIONAL_CONTEXT_TABLES[model])

    def test_public_api_and_registry_share_operational_context_model_identity(self):
        for model in OPERATIONAL_CONTEXT_MODELS:
            with self.subTest(model=model.__name__):
                self.assertIs(getattr(public_models, model.__name__), model)
                self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_analytics_registry_contains_no_duplicate_model_labels(self):
        registered = [
            model for model in apps.get_models() if model._meta.app_label == "analytics"
        ]
        labels = [model._meta.label_lower for model in registered]
        self.assertEqual(len(labels), len(set(labels)))

    def test_critical_platform_relations_resolve_to_original_models(self):
        self.assertIs(
            UsuarioOrganizacion._meta.get_field("organizacion").remote_field.model,
            Organizacion,
        )
        self.assertIs(
            UsuarioObraAcceso._meta.get_field(
                "usuario_organizacion"
            ).remote_field.model,
            UsuarioOrganizacion,
        )
        self.assertEqual(
            UsuarioObraAcceso._meta.get_field("obra").remote_field.model._meta.label,
            "analytics.Obra",
        )


class ModelModularizationPersistenceTests(TestCase):
    def test_organization_and_membership_can_still_be_created(self):
        user = User.objects.create_user(username="platform-member")
        organization = Organizacion.objects.create(nombre="Organización Platform")
        membership = UsuarioOrganizacion.objects.create(
            user=user,
            organizacion=organization,
            rol=UsuarioOrganizacion.Rol.ADMIN,
        )

        self.assertEqual(organization.organizacion_id, "ORGANIZACION_PLATFORM")
        self.assertEqual(membership.organizacion, organization)
        self.assertEqual(membership.user, user)

    def test_organization_work_and_area_can_still_be_created(self):
        organization = Organizacion.objects.create(nombre="Contexto Operacional")
        stage = EtapaObra.objects.create(
            organizacion=organization,
            nombre="Obra gruesa",
        )
        work = Obra.objects.create(
            organizacion=organization,
            etapa_principal=stage,
            nombre="Edificio Central",
            fecha_inicio=date(2026, 8, 26),
        )
        area = AreaOperacional.objects.create(
            organizacion=organization,
            nombre="Bodega",
            tipo=AreaOperacional.Tipo.BODEGA,
        )

        self.assertEqual(work.organizacion, organization)
        self.assertEqual(work.etapa_principal, stage)
        self.assertEqual(area.organizacion, organization)

    def test_operational_unit_and_process_can_still_be_created(self):
        organization = Organizacion.objects.create(nombre="Procesos Operacionales")
        unit = UnidadOperacional.objects.create(
            organizacion=organization,
            nombre="Faena principal",
            tipo=UnidadOperacional.Tipo.FAENA,
        )
        process = ProcesoOperacional.objects.create(
            organizacion=organization,
            unidad=unit,
            nombre="Movimiento de tierra",
        )

        self.assertEqual(process.organizacion, organization)
        self.assertEqual(process.unidad, unit)

    def test_membership_area_and_work_create_valid_workspace(self):
        user = User.objects.create_user(username="workspace-member")
        organization = Organizacion.objects.create(nombre="Workspace Válido")
        membership = UsuarioOrganizacion.objects.create(
            user=user,
            organizacion=organization,
        )
        area = AreaOperacional.objects.create(
            organizacion=organization,
            nombre="Operaciones",
        )
        work = Obra.objects.create(
            organizacion=organization,
            nombre="Obra Workspace",
            fecha_inicio=date(2026, 8, 26),
        )
        workspace = EspacioTrabajoOperacional(
            usuario_organizacion=membership,
            area=area,
            obra=work,
        )

        workspace.full_clean()
        workspace.save()

        self.assertEqual(workspace.usuario_organizacion, membership)
        self.assertEqual(workspace.area, area)
        self.assertEqual(workspace.obra, work)

    def test_workspace_still_rejects_cross_tenant_area_and_work(self):
        user = User.objects.create_user(username="cross-tenant-member")
        organization = Organizacion.objects.create(nombre="Tenant Uno")
        other_organization = Organizacion.objects.create(nombre="Tenant Dos")
        membership = UsuarioOrganizacion.objects.create(
            user=user,
            organizacion=organization,
        )
        foreign_area = AreaOperacional.objects.create(
            organizacion=other_organization,
            nombre="Área externa",
        )
        foreign_work = Obra.objects.create(
            organizacion=other_organization,
            nombre="Obra externa",
            fecha_inicio=date(2026, 8, 26),
        )
        workspace = EspacioTrabajoOperacional(
            usuario_organizacion=membership,
            area=foreign_area,
            obra=foreign_work,
        )

        with self.assertRaises(ValidationError) as context:
            workspace.full_clean()

        self.assertIn("area", context.exception.message_dict)
