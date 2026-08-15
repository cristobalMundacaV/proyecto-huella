from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (ActividadOperacional, CalculoAmbiental, EtapaObra,
                     EventoMaterial, FactorAmbiental, FuenteDatos,
                     LoteMaterial, MaterialConstruccion, MaterialOperacional,
                     Obra, Observacion, Organizacion, ProcesoOperacional,
                     UnidadOperacional, UsuarioOrganizacion)
from .services.context_gateway import ContextGateway
from .services.materials_v2 import (material_balance, material_lineage,
                                    save_event_quantity)


class MaterialsV2Tests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("materials-v2", password="test-pass")
        self.org = Organizacion.objects.create(nombre="Constructora Uno", preset="construccion")
        self.other = Organizacion.objects.create(nombre="Constructora Dos", preset="construccion")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org)
        self.client.force_login(self.user)
        self.base = f"/api/organizaciones/{self.org.organizacion_id}"
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Guia", tipo="documento")
        self.unit = UnidadOperacional.objects.create(organizacion=self.org, nombre="Obra Central", tipo="faena")
        self.process = ProcesoOperacional.objects.create(organizacion=self.org, unidad=self.unit, nombre="Fundaciones")
        self.stage = EtapaObra.objects.create(organizacion=self.org, nombre="Fundaciones")
        self.work = Obra.objects.create(organizacion=self.org, etapa_principal=self.stage, nombre="Edificio A", fecha_inicio="2026-01-01")
        self.material = MaterialOperacional.objects.create(organizacion=self.org, codigo="MAT-AC", nombre="Acero", categoria="metal", unidad_base="t")
        self.sequence = 0

    def activity(self):
        self.sequence += 1
        return ActividadOperacional.objects.create(organizacion=self.org, tipo="movimiento_material", codigo=f"MOV-{self.sequence}", nombre=f"Movimiento {self.sequence}", timestamp_inicio=timezone.now(), proceso_operacional=self.process)

    def event(self, event_type, amount=None, unit="t", **kwargs):
        activity = kwargs.pop("actividad", None) or self.activity()
        event = EventoMaterial.objects.create(organizacion=self.org, material=self.material, actividad=activity, tipo=event_type, fecha_hora=timezone.now(), proceso=self.process, **kwargs)
        if amount is not None:
            save_event_quantity(event, amount=Decimal(str(amount)), unit=unit, source=self.source)
        return event

    def test_crear_material_valido(self):
        response = self.client.post(f"{self.base}/materiales-operacionales/", {"codigo": "HOR-30", "nombre": "Hormigon H30", "categoria": "hormigon", "unidad_base": "m3"}, format="json")
        self.assertEqual(response.status_code, 201)

    def test_aislamiento_tenant(self):
        foreign = MaterialOperacional.objects.create(organizacion=self.other, codigo="OTRO", nombre="Otro", categoria="otro", unidad_base="kg")
        ids = {row["id"] for row in self.client.get(f"{self.base}/materiales-operacionales/").json()}
        self.assertNotIn(foreign.id, ids)
        response = self.client.post(f"{self.base}/lotes-materiales/", {"material": foreign.id, "codigo": "BAD"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_crear_lote_opcional(self):
        response = self.client.post(f"{self.base}/lotes-materiales/", {"material": self.material.id, "codigo": "L-A", "cantidad_inicial": "20", "unidad": "t"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(LoteMaterial.objects.get().material, self.material)

    def test_registrar_adquisicion(self): self.assertEqual(self.event("adquisicion", 100).tipo, "adquisicion")
    def test_registrar_recepcion(self):
        activity = self.activity()
        response = self.client.post(f"{self.base}/eventos-materiales/", {"material": self.material.id, "actividad": activity.id, "tipo": "recepcion", "fecha_hora": timezone.now().isoformat(), "cantidad": "100", "unidad": "t", "fuente": self.source.id, "proceso": self.process.id}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(EventoMaterial.objects.get().observacion_cantidad.valor_numerico, Decimal("100"))
    def test_registrar_uso(self): self.assertEqual(self.event("uso", 72).tipo, "uso")
    def test_registrar_sobrante(self): self.assertEqual(self.event("sobrante", 18).tipo, "sobrante")
    def test_registrar_reutilizacion(self): self.assertEqual(self.event("reutilizacion", 8).tipo, "reutilizacion")
    def test_registrar_residuo(self): self.assertEqual(self.event("residuo", 10).tipo, "residuo")

    def test_eventos_misma_cantidad_no_se_deduplican(self):
        for event_type in ("adquisicion", "despacho", "recepcion"):
            self.event(event_type, 20)
        self.assertEqual(EventoMaterial.objects.count(), 3)
        self.assertEqual(Observacion.objects.filter(concepto="cantidad_material").count(), 3)

    def test_observaciones_discrepantes_coexisten(self):
        event = self.event("recepcion", Decimal("19.8"))
        other_source = FuenteDatos.objects.create(organizacion=self.org, nombre="Balanza", tipo="sensor")
        Observacion.objects.create(organizacion=self.org, actividad=event.actividad, fuente=other_source, concepto="cantidad_material", valor_numerico=Decimal("20.2"), unidad="t", timestamp_observacion=timezone.now())
        self.assertEqual(event.actividad.observaciones.filter(concepto="cantidad_material").count(), 2)
        self.assertEqual(event.observacion_cantidad.valor_numerico, Decimal("19.8"))

    def test_balance_completo(self):
        for event_type, amount in (("recepcion", 100), ("uso", 72), ("reutilizacion", 8), ("devolucion", 5), ("residuo", 10)):
            self.event(event_type, amount)
        row = material_balance(self.org, self.material)["balances"][0]
        self.assertEqual(row["stock_restante"], Decimal("5")); self.assertEqual(row["calidad_balance"], "completo")

    def test_balance_incompleto_sin_recepcion(self):
        self.event("adquisicion", 100)
        self.assertEqual(material_balance(self.org, self.material)["balances"][0]["calidad_balance"], "incompleto")

    def test_balance_inconsistente_si_egreso_supera_ingreso(self):
        self.event("recepcion", 100); self.event("uso", 120)
        result = material_balance(self.org, self.material)
        self.assertEqual(result["balances"][0]["calidad_balance"], "inconsistente")
        self.assertIn("stock_negativo", {row["tipo"] for row in result["senales"]})

    def test_unidades_incompatibles_no_se_suman(self):
        self.event("recepcion", 100, "kg"); self.event("recepcion", 3, "m3")
        balances = material_balance(self.org, self.material)["balances"]
        self.assertEqual({row["unidad"] for row in balances}, {"kg", "m3"})

    def test_obra_se_relaciona_sin_mezclar_tenant(self):
        self.assertEqual(self.event("uso", 5, obra=self.work).obra, self.work)
        foreign_stage = EtapaObra.objects.create(organizacion=self.other, nombre="Otra")
        foreign_work = Obra.objects.create(organizacion=self.other, etapa_principal=foreign_stage, nombre="Obra B", fecha_inicio="2026-01-01")
        with self.assertRaises(ValidationError): self.event("uso", obra=foreign_work)

    def test_lineage_reconstruye_cadena(self):
        lot = LoteMaterial.objects.create(organizacion=self.org, material=self.material, codigo="L-1")
        reception = self.event("recepcion", 20, lote=lot)
        self.event("uso", 12, lote=lot, obra=self.work, evento_origen=reception)
        lineage = material_lineage(self.org, self.material, lot=lot)
        self.assertEqual([row["tipo"] for row in lineage["eventos"]], ["recepcion", "uso"])
        self.assertEqual(lineage["eventos"][1]["evento_origen_id"], reception.id)

    def test_indicadores_respetan_tenant(self):
        self.event("recepcion", 25)
        self.assertEqual(material_balance(self.org, self.material)["balances"][0]["cantidad_recibida"], Decimal("25"))
        self.assertIsNone(material_balance(self.other, MaterialOperacional.objects.create(organizacion=self.other, codigo="X", nombre="X", categoria="x", unidad_base="t"))["balances"][0]["stock_restante"])

    def test_no_crea_calculos_ni_factores(self):
        calculations = CalculoAmbiental.objects.count(); factors = FactorAmbiental.objects.count()
        self.event("recepcion", 10); material_balance(self.org, self.material)
        self.assertEqual(CalculoAmbiental.objects.count(), calculations); self.assertEqual(FactorAmbiental.objects.count(), factors)

    def test_legacy_material_construccion_permanece(self):
        legacy = MaterialConstruccion.objects.create(nombre="Legacy F12", unidad_default="kg", factor_emision_default=Decimal("1.5"))
        self.assertEqual(legacy.factor_emision_default, Decimal("1.5")); self.assertEqual(MaterialOperacional.objects.count(), 1)

    def test_context_gateway_entrega_balance_procesado(self):
        event = self.event("recepcion", 15)
        package = ContextGateway().activity(event.actividad, self.org)
        self.assertEqual(package["material"]["nombre"], "Acero")
        self.assertEqual(package["material"]["balance"]["balances"][0]["cantidad_recibida"], Decimal("15"))
