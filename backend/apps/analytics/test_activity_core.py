from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (ActividadOperacional, EtapaObra, FuenteDatos, Obra, Observacion,
                     Organizacion, ProcesoOperacional, RegistroEmision, UnidadOperacional,
                     UsuarioOrganizacion)


class ActivityCoreApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("activity-core", password="test-pass")
        self.organizacion = Organizacion.objects.create(nombre="Operaciones Uno")
        self.otra = Organizacion.objects.create(nombre="Operaciones Dos")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.organizacion)
        self.client.force_login(self.user)
        self.base = f"/api/organizaciones/{self.organizacion.organizacion_id}"
        self.unidad = UnidadOperacional.objects.create(organizacion=self.organizacion, nombre="Centro Norte")
        self.proceso = ProcesoOperacional.objects.create(organizacion=self.organizacion, unidad=self.unidad, nombre="Logistica")
        self.inicio = timezone.now().replace(microsecond=0)

    def crear_fuente(self, nombre="GPS", tipo="gps"):
        response = self.client.post(f"{self.base}/fuentes-datos/", {"nombre": nombre, "tipo": tipo}, format="json")
        self.assertEqual(response.status_code, 201)
        return response.data

    def crear_actividad(self, **overrides):
        payload = {"tipo": "transporte", "codigo": "VIAJE-125", "nombre": "Viaje 125",
                   "timestamp_inicio": self.inicio.isoformat(), "estado": "registrada",
                   "unidad_operacional": self.unidad.id, "proceso_operacional": self.proceso.id, **overrides}
        response = self.client.post(f"{self.base}/actividades-operacionales/", payload, format="json")
        return response

    def test_crea_fuente_y_actividad_sin_registro_emision(self):
        self.crear_fuente()
        response = self.crear_actividad()
        self.assertEqual(response.status_code, 201)
        actividad = ActividadOperacional.objects.get(id=response.data["id"])
        self.assertEqual(actividad.registros_emision_legacy.count(), 0)

    def test_viaje_tres_observaciones_y_detalle_con_fuentes(self):
        actividad = self.crear_actividad().data
        gps = self.crear_fuente("GPS", "gps")
        odometro = self.crear_fuente("Odometro", "manual")
        guia = self.crear_fuente("Guia despacho", "documento")
        observaciones = [
            (gps, "distancia_recorrida_km", "132", "km"),
            (odometro, "distancia_recorrida_km", "134", "km"),
            (guia, "masa_transportada_t", "18", "t"),
        ]
        for fuente, concepto, valor, unidad in observaciones:
            response = self.client.post(
                f"{self.base}/actividades-operacionales/{actividad['id']}/observaciones/",
                {"fuente": fuente["id"], "concepto": concepto, "valor_numerico": valor, "unidad": unidad,
                 "timestamp_observacion": self.inicio.isoformat(), "metodo_captura": "manual"}, format="json",
            )
            self.assertEqual(response.status_code, 201)
        self.assertEqual(Observacion.objects.filter(actividad_id=actividad["id"]).count(), 3)
        self.assertEqual(Observacion.objects.filter(actividad_id=actividad["id"], concepto="distancia_recorrida_km").count(), 2)
        detail = self.client.get(f"{self.base}/actividades-operacionales/{actividad['id']}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["observaciones_count"], 3)
        self.assertEqual({item["fuente_detalle"]["nombre"] for item in detail.data["observaciones"]}, {"GPS", "Odometro", "Guia despacho"})

    def test_actividad_rechaza_unidad_y_proceso_de_otro_tenant(self):
        unidad = UnidadOperacional.objects.create(organizacion=self.otra, nombre="Ajena")
        proceso = ProcesoOperacional.objects.create(organizacion=self.otra, unidad=unidad, nombre="Ajeno")
        self.assertEqual(self.crear_actividad(codigo="A-UNIDAD", unidad_operacional=unidad.id).status_code, 400)
        self.assertEqual(self.crear_actividad(codigo="A-PROCESO", proceso_operacional=proceso.id).status_code, 400)

    def test_observacion_rechaza_fuente_y_actividad_ajenas(self):
        actividad = self.crear_actividad().data
        fuente_ajena = FuenteDatos.objects.create(organizacion=self.otra, nombre="Fuente ajena")
        actividad_ajena = ActividadOperacional.objects.create(
            organizacion=self.otra, codigo="AJENA", nombre="Ajena", timestamp_inicio=self.inicio
        )
        payload = {"fuente": fuente_ajena.id, "concepto": "horas_operacion", "valor_numerico": "2",
                   "timestamp_observacion": self.inicio.isoformat()}
        response = self.client.post(f"{self.base}/actividades-operacionales/{actividad['id']}/observaciones/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        fuente = self.crear_fuente()
        payload.update({"fuente": fuente["id"], "actividad": actividad_ajena.id})
        response = self.client.post(f"{self.base}/actividades-operacionales/{actividad['id']}/observaciones/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_acceso_api_cross_tenant_bloqueado(self):
        actividad = ActividadOperacional.objects.create(
            organizacion=self.otra, codigo="OTRA-1", nombre="Otra", timestamp_inicio=self.inicio
        )
        path = f"/api/organizaciones/{self.otra.organizacion_id}/actividades-operacionales/{actividad.id}/"
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_registro_emision_legacy_sigue_funcionando_y_puede_vincularse(self):
        etapa = EtapaObra.objects.create(organizacion=self.organizacion, nombre="Etapa")
        obra = Obra.objects.create(organizacion=self.organizacion, etapa_principal=etapa, nombre="Obra", fecha_inicio="2026-01-01")
        actividad = ActividadOperacional.objects.create(
            organizacion=self.organizacion, codigo="LEGACY-1", nombre="Compatibilidad", timestamp_inicio=self.inicio
        )
        registro = RegistroEmision.objects.create(
            organizacion=self.organizacion, obra=obra, actividad_operacional=actividad, categoria="Transporte",
            fuente_emision="Diesel", cantidad=Decimal("10"), unidad="L", factor_emision=Decimal("2.5"), fecha="2026-01-01",
        )
        self.assertEqual(registro.emisiones_kg_co2e, Decimal("25.000"))
        self.assertEqual(actividad.registros_emision_legacy.get(), registro)

    def test_filtros_minimos(self):
        self.crear_actividad()
        self.crear_actividad(codigo="ENERGIA-1", tipo="consumo_energia", estado="borrador")
        response = self.client.get(f"{self.base}/actividades-operacionales/?tipo=transporte&estado=registrada")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
