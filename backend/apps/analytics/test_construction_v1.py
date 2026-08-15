from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (AccionMejoraAmbiental, ActividadOperacional,
                     DiagnosticoAmbientalInicial, EventoMaterial, FuenteDatos,
                     IndicadorAmbiental, MaterialOperacional, Obra, Observacion,
                     Organizacion, ProblematicaAmbiental,
                     RegistroFlujoAmbiental, UsuarioOrganizacion)
from .services.construction_v1 import (close_environmental_work,
                                       construction_materials,
                                       environmental_timeline, work_context)
from .services.foundation import inicializar_capacidades_preset
from .services.indicators_v2 import generate_indicator_value


class ConstructionV1IntegrationTests(APITestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Constructora Demo", preset="construccion")
        self.other = Organizacion.objects.create(nombre="Otra Constructora", preset="construccion")
        self.work_a = Obra.objects.create(organizacion=self.org, nombre="Obra A", fecha_inicio=date(2026, 1, 1), perfil_ambiental="edificacion")
        self.work_b = Obra.objects.create(organizacion=self.org, nombre="Obra B", fecha_inicio=date(2026, 1, 1), perfil_ambiental="vial")
        self.foreign_work = Obra.objects.create(organizacion=self.other, nombre="Ajena", fecha_inicio=date(2026, 1, 1))
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Medicion obra")
        self.user = User.objects.create_user("construction-v1", password="test")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org)
        self.client.force_login(self.user)
        self.base = f"/api/organizaciones/{self.org.organizacion_id}"

    def activity(self, work, code, kind=ActividadOperacional.Tipo.OTRO):
        return ActividadOperacional.objects.create(organizacion=self.org, obra=work, codigo=code, nombre=code,
                                                   tipo=kind, timestamp_inicio=timezone.now())

    def observation(self, activity, concept, value, unit):
        return Observacion.objects.create(organizacion=self.org, actividad=activity, fuente=self.source, concepto=concept,
                                          valor_numerico=value, unidad=unit, timestamp_observacion=timezone.now())

    def test_activity_work_is_optional_tenant_safe_and_profile_is_context_only(self):
        activity = self.activity(self.work_a, "A-1")
        activity.full_clean(); self.assertEqual(activity.obra, self.work_a)
        without_work = ActividadOperacional(organizacion=self.org, codigo="GENERAL", nombre="General", timestamp_inicio=timezone.now())
        without_work.full_clean()
        foreign = ActividadOperacional(organizacion=self.org, obra=self.foreign_work, codigo="BAD", nombre="Bad", timestamp_inicio=timezone.now())
        with self.assertRaises(ValidationError): foreign.full_clean()
        self.assertEqual(self.work_a.perfil_ambiental, "edificacion")

    def test_diagnosis_and_capabilities_are_scoped(self):
        first = DiagnosticoAmbientalInicial(organizacion=self.org, obra=self.work_a, objetivo_principal="A")
        first.full_clean(); first.save()
        second = DiagnosticoAmbientalInicial.objects.create(organizacion=self.org, obra=self.work_b, objetivo_principal="B")
        self.assertNotEqual(first.id, second.id)
        keys = {row.capacidad.clave for row in inicializar_capacidades_preset(self.org)}
        self.assertTrue({"ruido", "gestion_hidrica_suelo"}.issubset(keys))

    def test_work_indicator_never_mixes_concurrent_works(self):
        self.observation(self.activity(self.work_a, "ENERGY-A"), "consumo_energia", Decimal("1000"), "kWh")
        self.observation(self.activity(self.work_b, "ENERGY-B"), "consumo_energia", Decimal("800"), "kWh")
        indicator = IndicadorAmbiental.objects.create(organizacion=self.org, alcance="obra", obra=self.work_a,
            codigo="energia-obra-a", nombre="Energia Obra A", tipo="operacional", unidad="kWh", origen_numerador="consumo_energia")
        value = generate_indicator_value(indicator, date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(value.valor, Decimal("1000")); self.assertEqual(value.metadata["obra_id"], self.work_a.id)
        corporate = IndicadorAmbiental(organizacion=self.org, alcance="organizacion", codigo="corporativo", nombre="Corporativo",
            tipo="operacional", unidad="kWh", origen_numerador="consumo_energia")
        corporate.full_clean()

    def test_specialized_records_cannot_contradict_activity_work(self):
        activity = self.activity(self.work_a, "FLOW-A", ActividadOperacional.Tipo.CONSUMO_ENERGIA)
        flow = RegistroFlujoAmbiental(organizacion=self.org, actividad=activity, flujo="energia", periodo_inicio=timezone.now(),
                                      granularidad="obra", obra=self.work_b)
        with self.assertRaises(ValidationError): flow.full_clean()
        material = MaterialOperacional.objects.create(organizacion=self.org, codigo="MAT", nombre="Material", categoria="otro", unidad_base="t")
        event_activity = self.activity(self.work_a, "MAT-A", ActividadOperacional.Tipo.MOVIMIENTO_MATERIAL)
        event = EventoMaterial(organizacion=self.org, actividad=event_activity, material=material, tipo="recepcion",
                               fecha_hora=timezone.now(), obra=self.work_b)
        with self.assertRaises(ValidationError): event.full_clean()

    def test_material_and_sector_flows_stay_in_work(self):
        material = MaterialOperacional.objects.create(organizacion=self.org, codigo="STEEL", nombre="Acero", categoria="metal", unidad_base="t")
        for work, code, amount in ((self.work_a, "MA", 5), (self.work_b, "MB", 9)):
            activity = self.activity(work, code, ActividadOperacional.Tipo.MOVIMIENTO_MATERIAL)
            obs = self.observation(activity, "cantidad_material", Decimal(amount), "t")
            EventoMaterial.objects.create(organizacion=self.org, actividad=activity, material=material, tipo="recepcion",
                                          fecha_hora=timezone.now(), obra=work, observacion_cantidad=obs)
        result = construction_materials(self.work_a)[0]
        self.assertEqual(result["balances"][0]["cantidad_recibida"], Decimal("5"))

    def test_ingestion_resolves_work_into_activity(self):
        created = self.client.post(f"{self.base}/ingestas/", {"payload": {"fecha": "2026-01-01", "obra": self.work_a.codigo_obra, "kwh": 10},
            "tipo_ingesta": "api", "destino_operacional": "actividad_generica", "fuente_nombre": "API obra"}, format="json")
        process_id = created.data["id"]
        analysis = self.client.post(f"{self.base}/ingestas/{process_id}/analizar/", {}, format="json")
        mappings = analysis.data["columnas"]
        for item in mappings:
            if not item["concepto_normalizado"]: item["concepto_normalizado"] = item["columna_normalizada"]
        self.client.post(f"{self.base}/ingestas/{process_id}/mapeo/", {"mapeos": mappings}, format="json")
        preview = self.client.get(f"{self.base}/ingestas/{process_id}/preview/")
        self.assertEqual(preview.data["filas_validas"], 1)
        self.client.post(f"{self.base}/ingestas/{process_id}/confirmar/", {}, format="json")
        self.assertEqual(ActividadOperacional.objects.get(codigo=f"ING-{process_id}-1").obra, self.work_a)

    def test_timeline_context_and_close_preserve_history(self):
        self.activity(self.work_a, "OP-A")
        problem = ProblematicaAmbiental.objects.create(organizacion=self.org, obra=self.work_a, titulo="Ruido recurrente",
            descripcion="Eventos reportados", categoria="ruido", valor_inicial=3, objetivo_meta=1, fecha_deteccion=date(2026, 2, 1))
        AccionMejoraAmbiental.objects.create(problematica=problem, titulo="Revisar horarios", descripcion="Seguimiento")
        timeline = environmental_timeline(self.work_a)
        self.assertTrue({"obra_creada", "actividad", "problematica", "accion"}.issubset({row["tipo"] for row in timeline}))
        close_environmental_work(self.work_a, "Cierre con pendientes")
        self.assertEqual(self.work_a.estado_ambiental, "cierre_pendiente")
        self.assertTrue(self.work_a.actividades_operacionales.exists())
        package = work_context(self.work_a)
        self.assertEqual(package["references"]["work"], self.work_a.id)
        self.assertNotIn(self.work_b.id, [row.get("obra_id") for row in package["materiales"]])

    def test_work_endpoints_are_tenant_isolated(self):
        response = self.client.get(f"{self.base}/obras/{self.work_a.id}/contexto/")
        self.assertEqual(response.status_code, 200); self.assertEqual(response.data["references"]["work"], self.work_a.id)
        foreign = self.client.get(f"{self.base}/obras/{self.foreign_work.id}/contexto/")
        self.assertEqual(foreign.status_code, 404)
