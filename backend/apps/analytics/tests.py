from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Organizacion, EtapaObra, EvidenciaObra, Obra, RegistroEmision, TransporteObra, UsuarioOrganizacion
from .services.local_advisor import generar_analisis_local


class AnalyticsConstructionApiTests(APITestCase):
    def setUp(self):
        self.organizacion = Organizacion.objects.create(
            organizacion_id="ORGANIZACION_ANDINA",
            nombre="Organizacion Andina SpA",
            region="Biobio",
            comuna="Concepcion",
            rubro="Construccion",
        )
        self.user = User.objects.create_user("analista", email="analista@example.com", password="segura-test-123")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.organizacion)
        self.client.force_login(self.user)
        self.etapa = EtapaObra.objects.create(
            organizacion=self.organizacion,
            etapa_id="ETAPA_OBRA_GRUESA",
            nombre="Obra gruesa",
            tipo=EtapaObra.Tipo.OBRA_GRUESA,
        )
        self.obra = Obra.objects.create(
            organizacion=self.organizacion,
            etapa_principal=self.etapa,
            codigo_obra="OBRA_LOS_ROBLES",
            nombre="Edificio Habitacional Los Robles",
            tipo_proyecto=Obra.TipoProyecto.EDIFICIO,
            fecha_inicio="2026-01-10",
            superficie_m2=Decimal("4800"),
            ubicacion="Concepcion, Biobio",
        )

    def test_registro_emision_calcula_kg_co2e(self):
        registro = RegistroEmision.objects.create(
            obra=self.obra,
            categoria=RegistroEmision.Categoria.MATERIALES,
            fuente_emision="Hormigon H30",
            cantidad=Decimal("100"),
            unidad="m3",
            factor_emision=Decimal("320.500000"),
            fecha="2026-02-01",
        )

        self.assertEqual(registro.organizacion, self.organizacion)
        self.assertEqual(registro.etapa, self.etapa)
        self.assertEqual(registro.emisiones_kg_co2e, Decimal("32050.000"))

    def test_dashboard_organizacion_entrega_inteligencia_ambiental(self):
        RegistroEmision.objects.create(
            obra=self.obra,
            categoria=RegistroEmision.Categoria.MATERIALES,
            fuente_emision="Acero estructural",
            cantidad=Decimal("10"),
            unidad="ton",
            factor_emision=Decimal("1850.000000"),
            fecha="2026-02-01",
        )

        response = self.client.get(f"/api/organizaciones/{self.organizacion.organizacion_id}/dashboard/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["categoria_critica"], RegistroEmision.Categoria.MATERIALES)
        self.assertEqual(response.data["fuente_critica"], "Acero estructural")
        self.assertEqual(response.data["intensidad_carbono"], 3.854)

    def test_usuario_no_puede_acceder_a_otro_tenant(self):
        otra = Organizacion.objects.create(organizacion_id="OTRA", nombre="Otra organizacion")
        response = self.client.get(f"/api/organizaciones/{otra.organizacion_id}/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_login_entrega_contexto_de_organizacion(self):
        self.client.logout()
        response = self.client.post(
            "/api/auth/login/",
            {"email": "ANALISTA@example.com", "password": "segura-test-123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["user"]["organizaciones"][0]["organizacion_id"],
            self.organizacion.organizacion_id,
        )

    def test_preset_aserradero_conserva_flujo_de_lotes(self):
        aserradero = Organizacion.objects.create(
            organizacion_id="ASERRADERO_SUR",
            nombre="Aserradero Sur",
            preset=Organizacion.Preset.ASERRADERO,
        )
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=aserradero)
        response = self.client.get(f"/api/organizaciones/{aserradero.organizacion_id}/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(aserradero.preset, "aserradero")
        self.assertIn("lotes_forestales", response.data)

    def test_crea_registro_desde_endpoint_de_obra(self):
        response = self.client.post(
            f"/api/obras/{self.obra.codigo_obra}/registros-emision/",
            {
                "categoria": RegistroEmision.Categoria.MAQUINARIA,
                "fuente_emision": "Excavadora diesel",
                "cantidad": "50",
                "unidad": "litros diesel",
                "factor_emision": "2.680000",
                "fecha": "2026-02-02",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["obra_codigo"], self.obra.codigo_obra)
        self.assertEqual(response.data["emisiones_kg_co2e"], "134.000")

    def test_evidencia_de_obra_se_puede_subir(self):
        archivo = SimpleUploadedFile("factura.pdf", b"%PDF-1.4 demo", content_type="application/pdf")
        response = self.client.post(
            f"/api/obras/{self.obra.codigo_obra}/evidencias/",
            {
                "tipo_evidencia": EvidenciaObra.TipoEvidencia.FACTURA_MATERIAL,
                "estado_documental": EvidenciaObra.EstadoDocumental.PENDIENTE,
                "fecha_documento": "2026-02-03",
                "nombre": "Factura hormigon H30",
                "archivo": archivo,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["obra_codigo"], self.obra.codigo_obra)

    def test_transporte_crea_registro_de_emision_asociado(self):
        transporte = TransporteObra.objects.create(
            obra=self.obra,
            etapa=self.etapa,
            vehiculo="Camion mixer",
            patente="ABCD12",
            origen="Planta hormigon",
            destino="Obra Los Robles",
            distancia_km=Decimal("30"),
            consumo_estimado_litro_km=Decimal("0.4000"),
            fecha_hora="2026-02-04T08:30:00Z",
        )

        self.assertIsNotNone(transporte.registro_emision)
        self.assertEqual(transporte.registro_emision.categoria, RegistroEmision.Categoria.TRANSPORTE)
        self.assertEqual(transporte.registro_emision.emisiones_kg_co2e, Decimal("32.160"))

    def test_advisor_local_usa_lenguaje_de_construccion(self):
        texto = generar_analisis_local(
            {
                "total_emisiones": 1000,
                "categoria_critica": "Materiales",
                "fuente_critica": "Hormigon H30",
                "etapa_critica": "Fundaciones",
            }
        )

        self.assertIn("hormigon", texto.lower())
        self.assertIn("obra", texto.lower())
