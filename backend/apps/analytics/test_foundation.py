from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import (CapacidadOrganizacion, DiagnosticoAmbientalInicial, Organizacion,
                     ElementoDiagnosticoAmbiental, ProcesoOperacional, UnidadOperacional,
                     UsuarioOrganizacion)
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
        self.assertEqual(len(primera), 12)
        capacidad = primera[0]; capacidad.estado = CapacidadOrganizacion.Estado.OPERATIVA; capacidad.save()
        segunda = list(inicializar_capacidades_preset(self.organizacion))
        self.assertEqual(len(segunda), 12)
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

    def _diagnostico_con_elemento(self):
        diagnostico = DiagnosticoAmbientalInicial.objects.create(organizacion=self.organizacion)
        elemento = ElementoDiagnosticoAmbiental.objects.create(
            diagnostico=diagnostico, tipo="proceso", nombre="Montaje", descripcion="Inicial"
        )
        return diagnostico, elemento

    def test_actualizar_elemento_conserva_id(self):
        _, elemento = self._diagnostico_con_elemento()
        response = self.client.patch(
            f"{self.base}/diagnostico-ambiental/",
            {"elementos": [{"id": elemento.id, "nombre": "Montaje actualizado"}]}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        elemento.refresh_from_db()
        self.assertEqual(elemento.nombre, "Montaje actualizado")
        self.assertEqual(response.data["elementos"][0]["id"], elemento.id)

    def test_agregar_elemento_no_recrea_existentes(self):
        diagnostico, elemento = self._diagnostico_con_elemento()
        created_at = elemento.created_at
        response = self.client.patch(
            f"{self.base}/diagnostico-ambiental/",
            {"elementos": [{"tipo": "fuente", "nombre": "Factura electrica"}]}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        elemento.refresh_from_db()
        self.assertEqual(elemento.created_at, created_at)
        self.assertEqual(diagnostico.elementos.count(), 2)

    def test_eliminar_elemento_requiere_marca_explicita(self):
        diagnostico, elemento = self._diagnostico_con_elemento()
        response = self.client.patch(
            f"{self.base}/diagnostico-ambiental/",
            {"elementos": [{"id": elemento.id, "eliminar": True}]}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(diagnostico.elementos.filter(id=elemento.id).exists())

    def test_no_modifica_elemento_de_otro_diagnostico_tenant(self):
        self._diagnostico_con_elemento()
        diagnostico_ajeno = DiagnosticoAmbientalInicial.objects.create(organizacion=self.otra)
        ajeno = ElementoDiagnosticoAmbiental.objects.create(
            diagnostico=diagnostico_ajeno, tipo="brecha", nombre="Ajena"
        )
        response = self.client.patch(
            f"{self.base}/diagnostico-ambiental/",
            {"elementos": [{"id": ajeno.id, "nombre": "Intrusion"}]}, format="json",
        )
        self.assertEqual(response.status_code, 400)
        ajeno.refresh_from_db()
        self.assertEqual(ajeno.nombre, "Ajena")

    def test_patch_sin_elementos_no_altera_existentes(self):
        diagnostico, elemento = self._diagnostico_con_elemento()
        updated_at = elemento.updated_at
        response = self.client.patch(
            f"{self.base}/diagnostico-ambiental/", {"observaciones": "Nueva nota"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        elemento.refresh_from_db()
        self.assertEqual(elemento.updated_at, updated_at)
        self.assertEqual(diagnostico.elementos.count(), 1)
