from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from .models import (ActividadOperacional, ActivoOperacional, CalculoAmbiental, EventoMaterial,
                     ImpactoAmbiental, MaterialOperacional, Observacion, Organizacion, PlantillaMapeo,
                     ProcesoIngesta, PuntoAmbientalOperacional, RegistroExtraido, RegistroFlujoAmbiental,
                     UsuarioOrganizacion, Vehiculo, ViajeOperacional)


class MultisourceIngestionV1Tests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("multisource", password="test")
        self.org = Organizacion.objects.create(nombre="Ingesta General")
        self.other = Organizacion.objects.create(nombre="Ingesta Ajena")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org)
        self.client.force_login(self.user)
        self.base = f"/api/organizaciones/{self.org.organizacion_id}"

    def prepare(self, content, *, destination="flujo_ambiental", flow="energia", name="datos.csv", context=None):
        file = SimpleUploadedFile(name, content.encode(), content_type="text/csv")
        created = self.client.post(f"{self.base}/ingestas/", {
            "archivo": file, "fuente_nombre": f"Fuente {flow}", "tipo_ingesta": "tabular",
            "destino_operacional": destination, "flujo": flow,
        }, format="multipart")
        self.assertEqual(created.status_code, 201, created.data)
        process_id = created.data["id"]
        analysis = self.client.post(f"{self.base}/ingestas/{process_id}/analizar/", {}, format="json")
        self.assertEqual(analysis.status_code, 200, analysis.data)
        mapping = self.client.post(f"{self.base}/ingestas/{process_id}/mapeo/", {
            "nombre": f"Mapeo {flow}", "mapeos": analysis.data["columnas"],
            "destino_operacional": destination, "flujo": flow, "contexto": context or {},
        }, format="json")
        self.assertEqual(mapping.status_code, 200, mapping.data)
        return process_id

    def confirm(self, process_id):
        return self.client.post(f"{self.base}/ingestas/{process_id}/confirmar/", {}, format="json")

    def test_raw_normalized_multiple_rows_and_provenance(self):
        process_id = self.prepare('fecha_inicio,kwh\n2026-01-01,"1.250,50"\n2026-02-01,800\n')
        preview = self.client.get(f"{self.base}/ingestas/{process_id}/preview/")
        self.assertEqual(preview.data["filas_detectadas"], 2)
        record = RegistroExtraido.objects.filter(proceso_ingesta_id=process_id).first()
        self.assertIn("kwh", {key.lower() for key in record.datos_originales})
        self.assertIn("valores", record.datos_normalizados)
        result = self.confirm(process_id)
        self.assertEqual(result.data["actividades_creadas"], 2)
        observation = Observacion.objects.first()
        self.assertEqual(observation.registro_extraido.proceso_ingesta_id, process_id)
        self.assertEqual(observation.version_evidencia_id, ProcesoIngesta.objects.get(id=process_id).version_evidencia_id)

    def test_energy_creates_flow_and_keeps_installation_granularity(self):
        from .models import UnidadOperacional
        unit = UnidadOperacional.objects.create(organizacion=self.org, nombre="Instalación A")
        process_id = self.prepare("fecha_inicio,kwh\n2026-01-01,1200\n", context={"unidad_operacional_id": unit.id, "granularidad": "instalacion"})
        result = self.confirm(process_id)
        self.assertEqual(result.data["filas_con_error"], 0)
        flow = RegistroFlujoAmbiental.objects.get()
        self.assertEqual(flow.flujo, "energia"); self.assertEqual(flow.granularidad, "instalacion")
        self.assertEqual(flow.unidad_operacional, unit); self.assertIsNone(flow.proceso)
        self.assertEqual(flow.actividad.tipo, ActividadOperacional.Tipo.CONSUMO_ENERGIA)

    def test_water_numeric_and_qualitative_do_not_invent_quantity(self):
        process_id = self.prepare("fecha_inicio,consumo_agua\n2026-01-01,25\n2026-02-01,sin lectura\n", flow="agua")
        result = self.confirm(process_id); self.assertEqual(result.data["filas_con_error"], 0)
        numeric = Observacion.objects.get(valor_numerico=25)
        qualitative = Observacion.objects.get(valor_texto="sin lectura")
        self.assertEqual(numeric.concepto, "consumo_agua"); self.assertIsNone(qualitative.valor_numerico)
        self.assertEqual(qualitative.unidad, "")

    def test_stationary_fuel_is_not_a_journey(self):
        process_id = self.prepare("fecha_inicio,litros\n2026-01-01,50\n", flow="combustible_estacionario")
        self.confirm(process_id)
        self.assertEqual(RegistroFlujoAmbiental.objects.get().flujo, "combustible_estacionario")
        self.assertEqual(Observacion.objects.get().concepto, "combustible_consumido")
        self.assertEqual(ViajeOperacional.objects.count(), 0)

    def test_own_generation_preserves_three_distinct_facts_without_reduction(self):
        process_id = self.prepare("fecha_inicio,energia_generada,energia_autoconsumida,energia_exportada\n2026-01-01,100,60,40\n", flow="generacion_propia")
        self.confirm(process_id)
        self.assertEqual(set(Observacion.objects.values_list("concepto", flat=True)), {"energia_generada", "energia_autoconsumida", "energia_exportada"})
        self.assertEqual(CalculoAmbiental.objects.count(), 0); self.assertEqual(ImpactoAmbiental.objects.count(), 0)

    def test_material_reception_use_and_optional_lot(self):
        material = MaterialOperacional.objects.create(organizacion=self.org, codigo="ACERO", nombre="Acero", categoria="metal", unidad_base="t")
        from .models import FuenteDatos, LoteMaterial
        source = FuenteDatos.objects.create(organizacion=self.org, nombre="Fuente lote")
        lot = LoteMaterial.objects.create(organizacion=self.org, material=material, codigo="L-1", cantidad_inicial=10, unidad="t", fuente=source)
        process_id = self.prepare("fecha,material,cantidad,unidad,tipo_evento,lote\n2026-01-01,ACERO,5,t,recepcion,L-1\n2026-01-02,ACERO,2,t,uso,L-1\n", destination="material", flow="")
        result = self.confirm(process_id); self.assertEqual(result.data["filas_con_error"], 0)
        self.assertEqual(set(EventoMaterial.objects.values_list("tipo", flat=True)), {"recepcion", "uso"})
        self.assertTrue(all(row.lote_id == lot.id for row in EventoMaterial.objects.all()))

    def test_material_acquisition_is_not_changed_to_use(self):
        MaterialOperacional.objects.create(organizacion=self.org, codigo="CEM", nombre="Cemento", categoria="mineral", unidad_base="t")
        process_id = self.prepare("fecha,material,cantidad,unidad,tipo_evento\n2026-01-01,CEM,5,t,adquisicion\n", destination="material", flow="")
        self.confirm(process_id); self.assertEqual(EventoMaterial.objects.get().tipo, "adquisicion")

    def test_residue_noise_and_hydric_flows_do_not_calculate(self):
        residue = self.prepare("fecha_inicio,peso_residuo,destino,gestor\n2026-01-01,50,disposicion,Gestor X\n", flow="residuo")
        noise = self.prepare("fecha_inicio,valor_ruido,unidad,metrica\n2026-01-01,72,dBA,LAeq\n", flow="ruido")
        hydric = self.prepare("fecha_inicio,desborde,erosion_observada,superficie_intervenida,unidad\n2026-01-01,si,no,20,m2\n", flow="gestion_hidrica_suelo")
        for process_id in (residue, noise, hydric): self.confirm(process_id)
        self.assertEqual(RegistroFlujoAmbiental.objects.count(), 3)
        noise_observation = Observacion.objects.get(concepto="nivel_ruido")
        self.assertEqual(noise_observation.unidad, "dBA")
        self.assertNotIn("cumplimiento", RegistroFlujoAmbiental.objects.get(flujo="ruido").metadata)
        self.assertEqual(CalculoAmbiental.objects.count(), 0); self.assertEqual(ImpactoAmbiental.objects.count(), 0)

    def test_transport_handler_creates_journey_when_vehicle_is_unambiguous(self):
        asset = ActivoOperacional.objects.create(organizacion=self.org, codigo="CAM-1", nombre="Camión", tipo="vehiculo")
        Vehiculo.objects.create(activo=asset, patente="AB-CD-12")
        process_id = self.prepare("viaje_id,fecha,patente,km,toneladas,combustible\nV-1,2026-01-01,AB-CD-12,120,15,30\n", destination="transporte", flow="")
        result = self.confirm(process_id); self.assertEqual(result.data["filas_con_error"], 0)
        journey = ViajeOperacional.objects.get(); self.assertEqual(journey.actividad.tipo, "transporte")
        self.assertEqual(journey.actividad.observaciones.count(), 3)
        self.assertEqual(ImpactoAmbiental.objects.count(), 0)

    def test_idempotency_raw_immutability_and_structured_errors(self):
        process_id = self.prepare("viaje_id,km\nV-1,mal\n", destination="transporte", flow="")
        first = self.confirm(process_id); self.assertEqual(first.data["filas_con_error"], 1)
        record = RegistroExtraido.objects.get(); self.assertIsInstance(record.errores[0], dict)
        good_id = self.prepare("viaje_id,km\nV-2,10\n", destination="transporte", flow="")
        self.confirm(good_id); second = self.confirm(good_id)
        self.assertTrue(second.data["idempotente"]); self.assertEqual(ActividadOperacional.objects.count(), 1)
        confirmed = RegistroExtraido.objects.get(proceso_ingesta_id=good_id); confirmed.datos_originales = {"alterado": True}
        with self.assertRaises(ValidationError): confirmed.save()

    def test_schema_alias_template_tenant_and_ambiguous_context(self):
        process_id = self.prepare("viaje_id,distancia_km\nV-1,10\n", destination="transporte", flow="")
        preview = self.client.get(f"{self.base}/ingestas/{process_id}/preview/")
        self.assertEqual(preview.data["filas_validas"], 1)
        template = PlantillaMapeo.objects.get()
        foreign_process = ProcesoIngesta.objects.get(id=process_id)
        foreign_process.organizacion = self.other; foreign_process.plantilla_mapeo = template
        with self.assertRaises(ValidationError): foreign_process.full_clean()

        PuntoAmbientalOperacional.objects.create(organizacion=self.org, codigo="P-1", nombre="Medidor común")
        PuntoAmbientalOperacional.objects.create(organizacion=self.org, codigo="P-2", nombre="Medidor común")
        ambiguous = self.prepare("fecha_inicio,kwh,medidor\n2026-01-01,10,Medidor común\n")
        result = self.client.get(f"{self.base}/ingestas/{ambiguous}/preview/")
        self.assertEqual(result.data["filas"][0]["estado"], "requiere_revision")
        self.assertEqual(result.data["filas"][0]["problemas"][0]["codigo"], "contexto_ambiguo")

    def test_preview_does_not_persist_domain_and_flow_without_method_imports(self):
        process_id = self.prepare("fecha_inicio,kwh\n2026-01-01,10\n")
        self.client.get(f"{self.base}/ingestas/{process_id}/preview/")
        self.assertEqual(ActividadOperacional.objects.count(), 0); self.assertEqual(Observacion.objects.count(), 0)
        result = self.confirm(process_id); self.assertEqual(result.data["filas_con_error"], 0)
        self.assertEqual(CalculoAmbiental.objects.count(), 0)
