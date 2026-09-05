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
        event = EventoMaterial.objects.create(organizacion=self.org, material=self.material, actividad=activity, tipo=event_type, fecha_hora=kwargs.pop("fecha_hora", timezone.now()), proceso=self.process, **kwargs)
        if amount is not None:
            save_event_quantity(event, amount=Decimal(str(amount)), unit=unit, source=self.source)
        return event

    def test_crear_material_valido(self):
        response = self.client.post(f"{self.base}/materiales-operacionales/", {"codigo": "HOR-30", "nombre": "Hormigon H30", "categoria": "hormigon", "unidad_base": "m3"}, format="json")
        self.assertEqual(response.status_code, 201)

    def test_e2e_recepcion_material_creado_y_codigo_unico_por_tenant(self):
        material_payload = {
            "codigo": "CEM-EPN-01",
            "nombre": "Cemento Portland",
            "categoria": "cemento",
            "unidad_base": "kg",
            "proveedor_fabricante": "Proveedor Demo",
            "activo": True,
        }
        created = self.client.post(
            f"{self.base}/materiales-operacionales/", material_payload, format="json"
        )
        self.assertEqual(created.status_code, 201, created.data)
        duplicate = self.client.post(
            f"{self.base}/materiales-operacionales/", material_payload, format="json"
        )
        self.assertEqual(duplicate.status_code, 400)
        MaterialOperacional.objects.create(
            organizacion=self.other, **material_payload
        )
        activity = ActividadOperacional.objects.create(
            organizacion=self.org,
            obra=self.work,
            tipo=ActividadOperacional.Tipo.MOVIMIENTO_MATERIAL,
            codigo="MATMOV-E2E-01",
            nombre="Recepcion de Cemento Portland",
            timestamp_inicio=timezone.now(),
        )
        response = self.client.post(
            f"{self.base}/eventos-materiales/",
            {
                "material": created.data["id"],
                "actividad": activity.id,
                "obra": self.work.id,
                "tipo": "recepcion",
                "fecha_hora": timezone.now().isoformat(),
                "cantidad": "10000",
                "unidad": "kg",
                "fuente": self.source.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        event = EventoMaterial.objects.get(pk=response.data["id"])
        self.assertEqual(event.actividad, activity)
        self.assertEqual(event.observacion_cantidad.concepto, "cantidad_material")
        self.assertEqual(event.observacion_cantidad.valor_numerico, Decimal("10000"))
        self.assertEqual(event.observacion_cantidad.unidad, "kg")
        self.assertEqual(event.observacion_cantidad.fuente, self.source)
        balance = material_balance(self.org, event.material, work=self.work)["balances"][0]
        self.assertEqual(balance["cantidad_recibida"], Decimal("10000"))
        self.assertEqual(balance["cantidad_utilizada"], Decimal("0"))
        self.assertEqual(balance["cantidad_reutilizada"], Decimal("0"))
        self.assertEqual(balance["stock_restante"], Decimal("10000"))

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

    def test_balance_periodo_incluye_saldo_apertura(self):
        self.event("recepcion", 100, fecha_hora=timezone.datetime(2026, 1, 1, tzinfo=timezone.get_current_timezone()))
        self.event("uso", 20, fecha_hora=timezone.datetime(2026, 2, 10, tzinfo=timezone.get_current_timezone()))
        row = material_balance(self.org, self.material, start="2026-02-01", end="2026-02-28")["balances"][0]
        self.assertEqual(row["saldo_inicial"], Decimal("100"))
        self.assertEqual(row["ingresos_periodo"], Decimal("0"))
        self.assertEqual(row["egresos_periodo"], Decimal("20"))
        self.assertEqual(row["stock_restante"], Decimal("80"))
        self.assertEqual(row["cantidad_recibida"], Decimal("0"))
        self.assertNotEqual(row["calidad_balance"], "inconsistente")

    def test_egreso_periodo_superior_al_saldo_real_es_inconsistente(self):
        self.event("recepcion", 10, fecha_hora=timezone.datetime(2026, 1, 1, tzinfo=timezone.get_current_timezone()))
        self.event("uso", 20, fecha_hora=timezone.datetime(2026, 2, 10, tzinfo=timezone.get_current_timezone()))
        row = material_balance(self.org, self.material, start="2026-02-01")["balances"][0]
        self.assertEqual(row["stock_restante"], Decimal("-10"))
        self.assertEqual(row["calidad_balance"], "inconsistente")

    def test_saldo_inicial_separa_unidades_y_respeta_lote(self):
        lot_a = LoteMaterial.objects.create(organizacion=self.org, material=self.material, codigo="L-A")
        lot_b = LoteMaterial.objects.create(organizacion=self.org, material=self.material, codigo="L-B")
        opening = timezone.datetime(2026, 1, 1, tzinfo=timezone.get_current_timezone())
        self.event("recepcion", 100, "kg", lote=lot_a, fecha_hora=opening)
        self.event("recepcion", 3, "m3", lote=lot_a, fecha_hora=opening)
        self.event("recepcion", 50, "kg", lote=lot_b, fecha_hora=opening)
        rows = material_balance(self.org, self.material, lot=lot_a, start="2026-02-01")["balances"]
        self.assertEqual({row["unidad"] for row in rows}, {"kg", "m3"})
        self.assertEqual(next(row for row in rows if row["unidad"] == "kg")["saldo_inicial"], Decimal("100"))

    def test_filtro_obra_limita_saldo_inicial(self):
        other_work = Obra.objects.create(organizacion=self.org, etapa_principal=self.stage, nombre="Edificio B", fecha_inicio="2026-01-01")
        opening = timezone.datetime(2026, 1, 1, tzinfo=timezone.get_current_timezone())
        self.event("recepcion", 40, obra=self.work, fecha_hora=opening)
        self.event("recepcion", 90, obra=other_work, fecha_hora=opening)
        row = material_balance(self.org, self.material, work=self.work, start="2026-02-01")["balances"][0]
        self.assertEqual(row["saldo_inicial"], Decimal("40"))

    def test_evento_origen_posterior_es_rechazado(self):
        later = self.event("recepcion", fecha_hora=timezone.datetime(2026, 2, 10, tzinfo=timezone.get_current_timezone()))
        with self.assertRaises(ValidationError):
            self.event("uso", evento_origen=later, fecha_hora=timezone.datetime(2026, 2, 1, tzinfo=timezone.get_current_timezone()))

    def test_evento_no_puede_ser_su_propio_origen(self):
        event = self.event("recepcion")
        event.evento_origen = event
        with self.assertRaises(ValidationError): event.save()

    def test_ciclo_lineage_es_rechazado(self):
        instant = timezone.datetime(2026, 2, 1, tzinfo=timezone.get_current_timezone())
        first = self.event("recepcion", fecha_hora=instant)
        second = self.event("uso", evento_origen=first, fecha_hora=instant)
        first.evento_origen = second
        with self.assertRaises(ValidationError): first.save()

    def test_cadena_causal_y_origen_opcional_siguen_validos(self):
        reception = self.event("recepcion")
        use = self.event("uso", evento_origen=reception)
        independent = self.event("sobrante")
        self.assertEqual(use.evento_origen, reception)
        self.assertIsNone(independent.evento_origen)
