from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from .models import EvidenciaObra, Organizacion
from .serializers import EvidenciaObraSerializer
from .services.evidence_taxonomy import evidence_types_for_domain


class EvidenceTaxonomyTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("taxonomy-user", password="test-pass")
        self.client.force_login(self.user)

    def values(self, domain):
        response = self.client.get("/api/tipos-evidencia/", {"dominio": domain})
        self.assertEqual(response.status_code, 200, response.data)
        return {item["value"] for item in response.data}

    def test_water_returns_only_water_types_and_other(self):
        values = self.values("agua")
        self.assertEqual(
            values,
            {
                "factura_agua",
                "lectura_medidor_agua",
                "abastecimiento_camion_aljibe",
                "extraccion_agua_propia",
                "informe_hidrico",
                "otro",
            },
        )
        self.assertNotIn("boleta_electrica", values)
        self.assertNotIn("factura_combustible", values)
        self.assertNotIn("ticket_pesaje", values)

    def test_energy_fuel_and_waste_are_isolated(self):
        energy = self.values("energia")
        fuel = self.values("combustible_estacionario")
        waste = self.values("residuos")
        self.assertNotIn("factura_combustible", energy)
        self.assertNotIn("ticket_pesaje", energy)
        self.assertNotIn("factura_agua", fuel)
        self.assertTrue(
            {
                "ticket_pesaje",
                "manifiesto_retiro",
                "certificado_disposicion_final",
                "registro_retiro_residuos",
            }.issubset(waste)
        )
        self.assertTrue(all("otro" in values for values in (energy, fuel, waste)))

    def test_energy_mode_has_a_distinct_generation_taxonomy(self):
        consumption = self.values("energia")
        generation = self.values("generacion_propia")
        self.assertNotIn("reporte_inversor_energia", consumption)
        self.assertIn("reporte_inversor_energia", generation)
        self.assertIn("reporte_generacion", generation)

    def test_historical_type_remains_readable_even_if_not_newly_eligible(self):
        organization = Organizacion.objects.create(nombre="Historico taxonomia")
        evidence = EvidenciaObra.objects.create(
            organizacion=organization,
            tipo_evidencia=EvidenciaObra.TipoEvidencia.DOCUMENTO_ORIGEN,
            archivo=SimpleUploadedFile("historico.txt", b"historico"),
            nombre="Documento historico",
        )

        serialized = EvidenciaObraSerializer(evidence).data

        self.assertEqual(serialized["tipo_evidencia"], "documento_origen")
        self.assertNotIn(
            "documento_origen",
            {item["value"] for item in evidence_types_for_domain("agua")},
        )
