from django.apps import apps
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

import apps.analytics.models as public_models
from apps.analytics.models import (
    ActividadOperacional,
    CalculoAmbiental,
    EventoAuditoriaSaaS,
    FactorAmbiental,
    Organizacion,
    RegistroFlujoAmbiental,
    SuscripcionSaaS,
    UsuarioObraAcceso,
    UsuarioOrganizacion,
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
