from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import (CapacidadOrganizacion, DiagnosticoAmbientalInicial, Organizacion,
                     ProcesoOperacional, UnidadOperacional, UsuarioOrganizacion)
from .services.foundation import inicializar_capacidades_preset, resumen_preparacion_ambiental


class FoundationApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("foundation", password="test-pass")
        self.organizacion = Organizacion.objects.create(nombre="Nueva Construccion", preset="construccion")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.organizacion)
        self.otra = Organizacion.objects.create(nombre="Otro Tenant")
        self.client.force_login(self.user)
        self.base = f"/api/organizaciones/{self.organizacion.organizacion_id}"

    def test_crea_diagnostico_y_rechaza_acceso_cross_tenant(self):
        response = self.client.post(f"{self.base}/diagnostico-ambiental/", {"estado": "en_progreso", "objetivo_principal": "Medir"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["objetivo_principal"], "Medir")
        self.assertEqual(self.client.get(f"/api/organizaciones/{self.otra.organizacion_id}/diagnostico-ambiental/").status_code, 404)

    def test_preset_es_idempotente_y_preserva_personalizacion(self):
        primera = list(inicializar_capacidades_preset(self.organizacion))
        self.assertEqual(len(primera), 10)
        capacidad = primera[0]; capacidad.estado = CapacidadOrganizacion.Estado.OPERATIVA; capacidad.save()
        segunda = list(inicializar_capacidades_preset(self.organizacion))
        self.assertEqual(len(segunda), 10)
        capacidad.refresh_from_db(); self.assertEqual(capacidad.estado, "operativa")

    def test_estado_invalido_de_capacidad_es_rechazado(self):
        capacidad = inicializar_capacidades_preset(self.organizacion).first()
        response = self.client.patch(f"{self.base}/capacidades-ambientales/{capacidad.id}/", {"estado": "inventado"})
        self.assertEqual(response.status_code, 400)

    def test_crea_unidad_y_proceso_y_bloquea_unidad_de_otro_tenant(self):
        unidad = self.client.post(f"{self.base}/unidades-operacionales/", {"nombre": "Faena Norte", "tipo": "faena"})
        self.assertEqual(unidad.status_code, 201)
        proceso = self.client.post(f"{self.base}/procesos-operacionales/", {"nombre": "Montaje", "unidad": unidad.data["id"]})
        self.assertEqual(proceso.status_code, 201)
        ajena = UnidadOperacional.objects.create(organizacion=self.otra, nombre="Ajena")
        forbidden = self.client.post(f"{self.base}/procesos-operacionales/", {"nombre": "Intruso", "unidad": ajena.id})
        self.assertEqual(forbidden.status_code, 400)

    def test_organizacion_nueva_y_flujo_preparado(self):
        inicializar_capacidades_preset(self.organizacion)
        inicial = resumen_preparacion_ambiental(self.organizacion)
        self.assertTrue(inicial["requiere_diagnostico"]); self.assertFalse(inicial["preparada_para_operacion"])
        DiagnosticoAmbientalInicial.objects.create(organizacion=self.organizacion, estado="completado")
        CapacidadOrganizacion.objects.filter(organizacion=self.organizacion).update(estado="aplica")
        UnidadOperacional.objects.create(organizacion=self.organizacion, nombre="Faena")
        ProcesoOperacional.objects.create(organizacion=self.organizacion, nombre="Montaje")
        self.assertTrue(resumen_preparacion_ambiental(self.organizacion)["preparada_para_operacion"])
