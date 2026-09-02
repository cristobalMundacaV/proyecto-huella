from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from rest_framework.test import APITestCase

from .models import FuenteDatos, Organizacion, PuntoAmbientalOperacional, UsuarioOrganizacion
from .services.construction_sources import CATALOG, ensure_construction_v1_sources


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
        expected = sum(len(rows) for rows in CATALOG.values())

        ensure_construction_v1_sources(self.organization)
        ensure_construction_v1_sources(self.organization)

        self.assertEqual(FuenteDatos.objects.filter(organizacion=self.organization).count(), expected)
        self.assertFalse(PuntoAmbientalOperacional.objects.exists())
        self.assertEqual(
            FuenteDatos.objects.get(nombre="Factura eléctrica").metadata,
            {"dominios": ["energia"], "provisionada": True, "catalogo": "construction_v1"},
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
