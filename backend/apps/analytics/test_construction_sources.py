from io import StringIO
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (
    ActividadOperacional,
    FuenteDatos,
    Observacion,
    Organizacion,
    PuntoAmbientalOperacional,
    UsuarioOrganizacion,
)
from .services.construction_sources import (
    CATALOG,
    CONSTRUCTION_SOURCE_CATALOG_VERSION,
    SOURCE_CATALOG,
    ensure_existing_construction_v1_sources,
    ensure_construction_v1_sources,
)


class ConstructionSourcesTests(APITestCase):
    def setUp(self):
        self.organization = Organizacion.objects.create(
            nombre="Fuentes Construccion", preset=Organizacion.Preset.CONSTRUCCION
        )
        self.user = User.objects.create_user("sources-user", password="test-pass")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.organization)
        self.client.force_login(self.user)
        self.url = f"/api/organizaciones/{self.organization.organizacion_id}/fuentes-datos/"

    def test_catalog_is_complete_idempotent_and_does_not_create_points(self):
        expected = len(SOURCE_CATALOG)

        ensure_construction_v1_sources(self.organization)
        ensure_construction_v1_sources(self.organization)

        self.assertEqual(FuenteDatos.objects.filter(organizacion=self.organization).count(), expected)
        self.assertFalse(PuntoAmbientalOperacional.objects.exists())
        self.assertEqual(
            FuenteDatos.objects.get(nombre="Factura eléctrica").metadata,
            {
                "dominios": ["energia"],
                "provisionada": True,
                "catalogo": "construction_v1",
                "catalogo_version": 1,
            },
        )

    def test_domain_filter_custom_scope_and_explicit_multi_domain(self):
        fuel = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Solo combustible",
            metadata={"dominios": ["combustibles"]},
        )
        energy = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Solo energia",
            metadata={"dominios": ["energia"]},
        )
        shared = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Compartida",
            metadata={"dominios": ["energia", "agua"]},
        )
        FuenteDatos.objects.create(organizacion=self.organization, nombre="Legacy sin metadata")

        energy_response = self.client.get(self.url, {"dominio": "energia"})
        fuel_response = self.client.get(self.url, {"dominio": "combustibles"})

        self.assertEqual({row["id"] for row in energy_response.data}, {energy.id, shared.id})
        self.assertEqual({row["id"] for row in fuel_response.data}, {fuel.id})

        created = self.client.post(
            f"{self.url}?dominio=energia",
            {"nombre": "Fuente custom energia", "tipo": "sistema_externo"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["metadata"]["dominios"], ["energia"])
        self.assertFalse(
            FuenteDatos.objects.filter(
                pk=created.data["id"], metadata__dominios__contains=["combustibles"]
            ).exists()
        )

    def test_water_is_never_empty_and_domains_remain_isolated(self):
        ensure_construction_v1_sources(self.organization)

        water = self.client.get(self.url, {"dominio": "agua"})
        fuels = self.client.get(self.url, {"dominio": "combustibles"})
        energy = self.client.get(self.url, {"dominio": "energia"})
        water_names = {row["nombre"] for row in water.data}
        fuel_names = {row["nombre"] for row in fuels.data}
        energy_names = {row["nombre"] for row in energy.data}

        self.assertTrue(
            {
                "Factura sanitaria",
                "Lectura manual de medidor de agua",
                "Medidor de agua",
                "Registro de abastecimiento externo",
            }.issubset(water_names)
        )
        self.assertNotIn("Factura sanitaria", fuel_names)
        self.assertNotIn("Factura de combustible", energy_names)
        self.assertNotIn("Factura eléctrica", fuel_names)

    def test_provisioned_sources_sort_before_compatible_custom_sources(self):
        FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="AAA custom agua",
            metadata={"dominios": ["agua"]},
        )
        ensure_construction_v1_sources(self.organization)

        response = self.client.get(self.url, {"dominio": "agua"})

        self.assertTrue(response.data[0]["metadata"]["provisionada"])
        self.assertEqual(response.data[-1]["nombre"], "AAA custom agua")

    def test_explicit_catalog_source_can_serve_multiple_domains(self):
        ensure_construction_v1_sources(self.organization)
        source = FuenteDatos.objects.get(
            organizacion=self.organization, nombre="Registro de combustible"
        )

        fuel = self.client.get(self.url, {"dominio": "combustibles"})
        machinery = self.client.get(self.url, {"dominio": "maquinaria"})

        self.assertEqual(source.metadata["dominios"], ["combustibles", "maquinaria"])
        self.assertIn(source.id, {row["id"] for row in fuel.data})
        self.assertIn(source.id, {row["id"] for row in machinery.data})

    def test_custom_source_is_not_adopted_or_reclassified(self):
        custom = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Factura sanitaria",
            tipo=FuenteDatos.Tipo.OTRO,
            activa=False,
            metadata={"dominios": ["custom"]},
        )

        ensure_construction_v1_sources(self.organization)

        custom.refresh_from_db()
        self.assertEqual(custom.tipo, FuenteDatos.Tipo.OTRO)
        self.assertFalse(custom.activa)
        self.assertEqual(custom.metadata, {"dominios": ["custom"]})

    def test_catalog_upgrade_only_adds_missing_and_preserves_disabled_and_custom(self):
        ensure_construction_v1_sources(self.organization)
        disabled = FuenteDatos.objects.get(nombre="Factura eléctrica")
        disabled.activa = False
        disabled.save(update_fields=["activa", "updated_at"])
        custom = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Laboratorio local",
            tipo=FuenteDatos.Tipo.OTRO,
            metadata={"dominios": ["agua"]},
        )
        future_row = ("Fuente estándar release futuro", "manual", ("agua",))

        with patch(
            "apps.analytics.services.construction_sources.SOURCE_CATALOG",
            SOURCE_CATALOG + (future_row,),
        ), patch(
            "apps.analytics.services.construction_sources.CONSTRUCTION_SOURCE_CATALOG_VERSION",
            CONSTRUCTION_SOURCE_CATALOG_VERSION + 1,
        ):
            ensure_construction_v1_sources(self.organization)

        disabled.refresh_from_db()
        custom.refresh_from_db()
        self.assertFalse(disabled.activa)
        self.assertEqual(custom.metadata, {"dominios": ["agua"]})
        self.assertTrue(
            FuenteDatos.objects.filter(
                organizacion=self.organization,
                nombre="Fuente estándar release futuro",
            ).exists()
        )

    def test_historical_observation_keeps_source_fk_after_reprovision(self):
        ensure_construction_v1_sources(self.organization)
        source = FuenteDatos.objects.get(nombre="Factura sanitaria")
        activity = ActividadOperacional.objects.create(
            organizacion=self.organization,
            codigo="water-history",
            nombre="Consumo histórico",
            tipo=ActividadOperacional.Tipo.CONSUMO_AGUA,
            timestamp_inicio=timezone.make_aware(datetime(2026, 9, 1, 10, 0)),
        )
        observation = Observacion.objects.create(
            organizacion=self.organization,
            actividad=activity,
            fuente=source,
            concepto="consumo_agua",
            valor_numerico=Decimal("10"),
            unidad="m3",
            timestamp_observacion=activity.timestamp_inicio,
        )

        ensure_construction_v1_sources(self.organization)

        observation.refresh_from_db()
        self.assertEqual(observation.fuente_id, source.id)

    def test_upgrade_service_only_targets_existing_construction_tenants(self):
        other = Organizacion.objects.create(
            nombre="Tenant forestal", preset=Organizacion.Preset.FORESTAL
        )

        ensure_existing_construction_v1_sources()

        self.assertTrue(self.organization.fuentes_datos.exists())
        self.assertFalse(other.fuentes_datos.exists())

    def test_migrate_backfills_existing_construction_tenant_automatically(self):
        self.assertFalse(self.organization.fuentes_datos.exists())

        call_command("migrate", interactive=False, verbosity=0)

        self.assertTrue(
            self.organization.fuentes_datos.filter(
                nombre="Factura sanitaria",
                metadata__dominios__contains=["agua"],
            ).exists()
        )

    def test_command_backfills_existing_construction_tenant_without_duplicates(self):
        call_command(
            "provision_construction_v1_sources",
            organization=self.organization.organizacion_id,
            stdout=StringIO(),
        )
        count = FuenteDatos.objects.count()
        call_command(
            "provision_construction_v1_sources",
            organization=self.organization.organizacion_id,
            stdout=StringIO(),
        )
        self.assertEqual(FuenteDatos.objects.count(), count)

    def test_command_reuses_the_single_provisioning_service(self):
        with patch(
            "apps.analytics.management.commands.provision_construction_v1_sources.ensure_construction_v1_sources",
            return_value=0,
        ) as ensure:
            call_command(
                "provision_construction_v1_sources",
                organization=self.organization.organizacion_id,
                stdout=StringIO(),
            )
        ensure.assert_called_once()
