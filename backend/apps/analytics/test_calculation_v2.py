from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.iot.models import DispositivoSensor, LecturaSensorV2
from apps.iot.services_v2 import registrar_lectura

from .models import (
    ActividadOperacional,
    ActivoOperacional,
    CalculoAmbiental,
    FactorAmbiental,
    FormulaAmbiental,
    ImpactoAmbiental,
    InputCalculoAmbiental,
    MetodologiaAmbiental,
    Observacion,
    Organizacion,
    RegistroEmision,
    FuenteDatos,
    UsuarioOrganizacion,
    VariableFormula,
    Vehiculo,
    ViajeOperacional,
    VersionFactorAmbiental,
    VersionMetodologia,
    Obra,
)
from .services.calculation_v2 import calculate_activity

from .services.eligibility_v2 import active_factor_version
from .services.methodology_selector import select_methodology
from .views_calculation_v2 import _serialize_selection


class CalculationV2Tests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("calculation-v2", password="test-pass")
        self.org = Organizacion.objects.create(nombre="Calculo Uno")
        self.other = Organizacion.objects.create(nombre="Calculo Dos")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org)
        self.client.force_login(self.user)
        self.base = f"/api/organizaciones/{self.org.organizacion_id}"
        self.source = FuenteDatos.objects.create(
            organizacion=self.org, nombre="Datos demo"
        )
        self.activity = ActividadOperacional.objects.create(
            organizacion=self.org,
            codigo="V-001",
            nombre="Viaje V-001",
            tipo="transporte",
            timestamp_inicio=timezone.now(),
        )
        self.asset = ActivoOperacional.objects.create(
            organizacion=self.org, codigo="CAM-01", nombre="Camion 01", tipo="vehiculo"
        )
        Vehiculo.objects.create(
            activo=self.asset, tipo_vehiculo="camion", combustible="diesel"
        )
        self.activity.activos.add(self.asset)
        self._create_method(
            "MET-TKM",
            "Transporte t.km",
            "transporte_tkm",
            "transporte_tkm",
            "FACTOR-TKM",
            "kgCO2e/t.km",
            Decimal("0.10"),
            [
                ("distancia", "distancia_recorrida_km", "km"),
                ("masa", "masa_transportada_t", "t"),
            ],
            priority=10,
        )
        self._create_method(
            "MET-KM",
            "Transporte vehiculo.km",
            "transporte_vehiculo_km",
            "transporte_vehiculo_km",
            "FACTOR-KM",
            "kgCO2e/km",
            Decimal("0.50"),
            [("distancia", "distancia_recorrida_km", "km")],
            {"tipo_vehiculo": "camion"},
            priority=20,
        )
        self._create_method(
            "MET-FUEL",
            "Transporte combustible",
            "transporte_combustible",
            "transporte_combustible",
            "FACTOR-FUEL",
            "kgCO2e/L",
            Decimal("2.00"),
            [("combustible", "combustible_consumido_l", "L")],
            {"combustible": "diesel"},
            priority=30,
        )

    def _create_method(
        self,
        code,
        name,
        flow,
        formula_type,
        factor_code,
        factor_unit,
        value,
        variables,
        context=None,
        organization="own",
        priority=100,
    ):
        organization = self.org if organization == "own" else organization
        factor = FactorAmbiental.objects.create(
            organizacion=organization,
            codigo=factor_code.lower(),
            nombre=f"Factor de prueba / demostracion {factor_code}",
            categoria="transporte",
            unidad_entrada=factor_unit.split("/")[-1],
            unidad_resultado="kgCO2e",
            contexto=context or {},
        )
        VersionFactorAmbiental.objects.create(
            factor=factor,
            version=1,
            valor=value,
            fuente="FACTOR DE PRUEBA / DEMOSTRACION",
            estado="activo",
        )
        method = MetodologiaAmbiental.objects.create(
            organizacion=organization,
            codigo=code.lower(),
            nombre=name,
            categoria="transporte",
            flujo=flow,
        )
        version = VersionMetodologia.objects.create(
            metodologia=method,
            version=1,
            estado="borrador",
            fuente_referencia="DEMO",
            prioridad=priority,
        )
        formula = FormulaAmbiental.objects.create(
            version_metodologia=version,
            factor_ambiental=factor,
            codigo=f"formula-{code.lower()}",
            tipo=formula_type,
            expresion_legible={
                "transporte_tkm": "masa x distancia x factor",
                "transporte_vehiculo_km": "distancia x factor",
                "transporte_combustible": "combustible x factor",
            }[formula_type],
        )
        for key, concept, unit in variables:
            VariableFormula.objects.create(
                formula=formula,
                clave=key,
                concepto_observacion=concept,
                unidad_esperada=unit,
            )
        VersionMetodologia.objects.filter(pk=version.pk).update(
            estado=VersionMetodologia.Estado.ACTIVA
        )
        version.refresh_from_db()
        return method, version, factor

    def observe(self, concept, value, unit):
        return Observacion.objects.create(
            organizacion=self.org,
            actividad=self.activity,
            fuente=self.source,
            concepto=concept,
            valor_numerico=value,
            unidad=unit,
            timestamp_observacion=timezone.now(),
            estado="validada",
        )

    def test_metodologia_factor_y_versiones_activas_inmutables(self):
        method = MetodologiaAmbiental.objects.get(flujo="transporte_tkm")
        self.assertEqual(method.versiones.count(), 1)
        version = method.versiones.get()
        version.descripcion_tecnica = "Cambio destructivo"
        with self.assertRaises(ValidationError):
            version.save()
        new_version = VersionMetodologia.objects.create(
            metodologia=method, version=2, estado="borrador"
        )
        self.assertEqual(new_version.version, 2)
        factor_version = VersionFactorAmbiental.objects.get(
            factor__codigo="factor-tkm", version=1
        )
        with self.assertRaises(ValidationError):
            factor_version.valor = Decimal("0.12")
            factor_version.save()
        self.assertEqual(
            VersionFactorAmbiental.objects.create(
                factor=factor_version.factor,
                version=2,
                valor="0.12",
                fuente="DEMO",
                estado="borrador",
            ).version,
            2,
        )

    def test_metodologia_global_es_seleccionable(self):
        method = MetodologiaAmbiental.objects.get(flujo="transporte_tkm")
        MetodologiaAmbiental.objects.filter(pk=method.pk).update(organizacion=None)
        self.observe("distancia_recorrida_km", "132", "km")
        self.observe("masa_transportada_t", "18", "t")
        self.assertEqual(
            select_methodology(self.activity)["seleccion"][
                "version_metodologia"
            ].metodologia_id,
            method.id,
        )

    def test_factor_global_es_seleccionable(self):
        formula = FormulaAmbiental.objects.get(
            tipo=FormulaAmbiental.Tipo.TRANSPORTE_TKM
        )
        FactorAmbiental.objects.filter(pk=formula.factor_ambiental_id).update(
            organizacion=None
        )
        self.assertIsNotNone(active_factor_version(formula, self.org))

    def test_metodologia_privada_propia_es_seleccionable(self):
        self.observe("distancia_recorrida_km", "132", "km")
        self.observe("masa_transportada_t", "18", "t")
        selected = select_methodology(self.activity)["seleccion"]
        self.assertEqual(
            selected["version_metodologia"].metodologia.organizacion, self.org
        )

    def test_factor_privado_propio_es_seleccionable(self):
        formula = FormulaAmbiental.objects.get(
            tipo=FormulaAmbiental.Tipo.TRANSPORTE_TKM
        )
        self.assertEqual(
            active_factor_version(formula, self.org).factor.organizacion, self.org
        )

    def test_recursos_privados_de_otro_tenant_quedan_excluidos(self):
        MetodologiaAmbiental.objects.update(activa=False)
        _, version, factor = self._create_method(
            "OTHER-TKM",
            "Metodo ajeno",
            "transporte_tkm",
            "transporte_tkm",
            "OTHER-FACTOR",
            "kgCO2e/t.km",
            Decimal("9"),
            [
                ("distancia", "distancia_recorrida_km", "km"),
                ("masa", "masa_transportada_t", "t"),
            ],
            organization=self.other,
        )
        self.observe("distancia_recorrida_km", "132", "km")
        self.observe("masa_transportada_t", "18", "t")
        self.assertIsNone(select_methodology(self.activity)["seleccion"])
        self.assertIsNone(active_factor_version(version.formula, self.org))
        self.assertEqual(factor.organizacion, self.other)

    def test_formula_y_variables_de_metodologia_activa_son_inmutables(self):
        formula = FormulaAmbiental.objects.get(
            tipo=FormulaAmbiental.Tipo.TRANSPORTE_TKM
        )
        variable = formula.variables.get(clave="distancia")
        formula.expresion_legible = "cambio"
        with self.assertRaises(ValidationError):
            formula.save()
        with self.assertRaises(ValidationError):
            formula.delete()
        variable.descripcion = "cambio"
        with self.assertRaises(ValidationError):
            variable.save()
        with self.assertRaises(ValidationError):
            variable.delete()
        with self.assertRaises(ValidationError):
            VariableFormula.objects.create(
                formula=formula,
                clave="nueva",
                concepto_observacion="nueva",
                unidad_esperada="u",
            )

    def test_metodologia_borrador_y_sus_hijos_siguen_editables(self):
        method = MetodologiaAmbiental.objects.get(flujo="transporte_tkm")
        version = VersionMetodologia.objects.create(
            metodologia=method, version=2, estado="borrador"
        )
        factor = FactorAmbiental.objects.get(codigo="factor-tkm")
        formula = FormulaAmbiental.objects.create(
            version_metodologia=version,
            factor_ambiental=factor,
            codigo="draft",
            tipo="transporte_tkm",
            expresion_legible="draft",
        )
        variable = VariableFormula.objects.create(
            formula=formula,
            clave="draft",
            concepto_observacion="draft",
            unidad_esperada="u",
        )
        formula.expresion_legible = "edited"
        formula.save()
        variable.descripcion = "edited"
        variable.save()
        variable.delete()
        formula.delete()
        self.assertFalse(FormulaAmbiental.objects.filter(pk=formula.pk).exists())

    def test_caso_obligatorio_prioriza_tkm_y_no_suma_alternativas(self):
        distance = self.observe("distancia_recorrida_km", "132", "km")
        mass = self.observe("masa_transportada_t", "18", "t")
        self.observe("combustible_consumido_l", "42", "L")
        selection = select_methodology(self.activity)
        self.assertEqual(selection["seleccion"]["metodo"], "transporte_tkm")
        self.assertEqual(
            {x["metodo"] for x in selection["alternativos"]},
            {"transporte_vehiculo_km", "transporte_combustible"},
        )
        calculation, _ = calculate_activity(self.activity)
        self.assertEqual(calculation.resultado, Decimal("237.6000000000"))
        self.assertEqual(CalculoAmbiental.objects.count(), 1)
        self.assertEqual(ImpactoAmbiental.objects.count(), 1)
        self.assertEqual(
            set(calculation.inputs.values_list("observacion_id", flat=True)),
            {distance.id, mass.id},
        )
        self.assertEqual(InputCalculoAmbiental.objects.count(), 2)
        self.assertEqual(RegistroEmision.objects.count(), 0)

    def test_viaje_operacional_real_calcula_trabajo_tkm_con_su_actividad(self):
        distance = self.observe("distancia_recorrida_km", "35", "km")
        mass = self.observe("masa_transportada_t", "8", "t")
        distance.refresh_from_db()
        mass.refresh_from_db()
        vehicle = self.asset.vehiculo
        ViajeOperacional.objects.create(
            organizacion=self.org,
            actividad=self.activity,
            codigo="VIAJE-CALC-01",
            vehiculo=vehicle,
            origen_nombre="Bodega proveedor Los Angeles",
            destino_nombre="Edificio Parque Norte",
            fecha_salida=self.activity.timestamp_inicio,
            observacion_distancia=distance,
            observacion_carga=mass,
            estado="completado",
        )

        selection = select_methodology(self.activity)
        self.assertEqual(selection["seleccion"]["metodo"], "transporte_tkm")
        calculation, _ = calculate_activity(self.activity)
        inputs = {
            item["clave"]: Decimal(item["valor"])
            for item in calculation.snapshot_tecnico["inputs"]
        }
        transport_work = inputs["distancia"] * inputs["masa"]
        self.assertEqual(transport_work, Decimal("280"))
        self.assertEqual(
            calculation.resultado,
            transport_work * calculation.version_factor.valor,
        )
        self.assertEqual(calculation.snapshot_tecnico["metodologia_version"], 1)
        self.assertEqual(
            calculation.snapshot_tecnico["version_factor_id"],
            calculation.version_factor_id,
        )

    def test_metodo_b_si_falta_masa(self):
        self.observe("distancia_recorrida_km", "132", "km")
        selection = select_methodology(self.activity)
        self.assertEqual(selection["seleccion"]["metodo"], "transporte_vehiculo_km")
        calculation, _ = calculate_activity(self.activity)
        self.assertEqual(calculation.resultado, Decimal("66.0000000000"))

    def test_metodo_combustible_si_es_unico_disponible(self):
        self.observe("combustible_consumido_l", "42", "L")
        selection = select_methodology(self.activity)
        self.assertEqual(selection["seleccion"]["metodo"], "transporte_combustible")
        calculation, _ = calculate_activity(self.activity)
        self.assertEqual(calculation.resultado, Decimal("84.0000000000"))

    def test_falta_critica_y_ambiguedad_no_calculables(self):
        self.assertIsNone(select_methodology(self.activity)["seleccion"])
        self.observe("distancia_recorrida_km", "132", "km")
        self.observe("distancia_recorrida_km", "134", "km")
        selection = select_methodology(self.activity)
        self.assertIsNone(selection["seleccion"])
        self.assertTrue(
            any(
                "multiples" in reason.lower()
                for item in selection["descartados"]
                for reason in item["motivos"]
            )
        )

    def test_snapshot_factor_historico_y_recalculo_nuevo(self):
        self.observe("distancia_recorrida_km", "132", "km")
        self.observe("masa_transportada_t", "18", "t")
        old, _ = calculate_activity(self.activity)
        factor = FactorAmbiental.objects.get(codigo="factor-tkm")
        old_factor = old.version_factor
        VersionFactorAmbiental.objects.filter(pk=old_factor.pk).update(
            estado="obsoleto"
        )
        VersionFactorAmbiental.objects.create(
            factor=factor, version=2, valor="0.12", fuente="DEMO v2", estado="activo"
        )
        new, _ = calculate_activity(self.activity)
        old.refresh_from_db()
        self.assertEqual(old.version_factor, old_factor)
        self.assertEqual(old.resultado, Decimal("237.6000000000"))
        self.assertEqual(new.version_factor.version, 2)
        self.assertEqual(new.resultado, Decimal("285.1200000000"))
        self.assertEqual(CalculoAmbiental.objects.count(), 2)
        self.assertEqual(ImpactoAmbiental.objects.count(), 2)

    def test_api_detalle_elegibilidad_y_tenant(self):
        self.observe("distancia_recorrida_km", "132", "km")
        self.observe("masa_transportada_t", "18", "t")
        eligibility = self.client.get(
            f"{self.base}/actividades-operacionales/{self.activity.id}/elegibilidad/"
        )
        self.assertEqual(eligibility.status_code, 200)
        self.assertEqual(eligibility.data["estado"], "calculable_completo")
        response = self.client.post(
            f"{self.base}/actividades-operacionales/{self.activity.id}/calcular/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        detail = self.client.get(
            f"{self.base}/calculos/{response.data['calculo']['id']}/"
        )
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.data["inputs"]), 2)
        foreign = ActividadOperacional.objects.create(
            organizacion=self.other,
            codigo="OTHER",
            nombre="Otra",
            tipo="transporte",
            timestamp_inicio=timezone.now(),
        )
        self.assertEqual(
            self.client.get(
                f"{self.base}/actividades-operacionales/{foreign.id}/elegibilidad/"
            ).status_code,
            404,
        )

    def test_iot_v2_no_contiene_calculo_ambiental(self):
        self.assertFalse(hasattr(LecturaSensorV2, "co2e_estimado"))

    def test_observacion_sensor_puede_alimentar_calculo_gobernado_posterior(self):
        sensor = DispositivoSensor.objects.create(
            dispositivo_id="FUEL-GOV-01",
            nombre="Caudalimetro de prueba",
            organizacion=self.org,
            tipo_sensor=DispositivoSensor.TipoSensor.COMBUSTIBLE,
        )
        lectura = registrar_lectura(
            sensor,
            {
                "actividad": self.activity,
                "concepto": "combustible_consumido_l",
                "valor_numerico": Decimal("42"),
                "unidad": "L",
                "timestamp": timezone.now(),
            },
        )
        calculo, _ = calculate_activity(self.activity)
        self.assertEqual(calculo.resultado, Decimal("84.0000000000"))
        self.assertEqual(calculo.inputs.get().observacion, lectura.observacion)
        self.assertEqual(RegistroEmision.objects.count(), 0)

    def test_impactos_filtran_por_obra(
        self,
    ):
        obra_a = Obra.objects.create(
            organizacion=self.org,
            nombre="Obra A",
            fecha_inicio=timezone.localdate(),
        )

        obra_b = Obra.objects.create(
            organizacion=self.org,
            nombre="Obra B",
            fecha_inicio=timezone.localdate(),
        )

        self.activity.obra = obra_a
        self.activity.save()

        self.observe(
            "distancia_recorrida_km",
            "132",
            "km",
        )

        self.observe(
            "masa_transportada_t",
            "18",
            "t",
        )

        calculate_activity(self.activity)

        foreign_activity = ActividadOperacional.objects.create(
            organizacion=self.org,
            obra=obra_b,
            codigo="V-B",
            nombre="Viaje B",
            tipo="transporte",
            timestamp_inicio=timezone.now(),
        )

        foreign_distance = Observacion.objects.create(
            organizacion=self.org,
            actividad=foreign_activity,
            fuente=self.source,
            concepto="distancia_recorrida_km",
            valor_numerico="100",
            unidad="km",
            timestamp_observacion=timezone.now(),
            estado="validada",
        )

        foreign_mass = Observacion.objects.create(
            organizacion=self.org,
            actividad=foreign_activity,
            fuente=self.source,
            concepto="masa_transportada_t",
            valor_numerico="10",
            unidad="t",
            timestamp_observacion=timezone.now(),
            estado="validada",
        )

        self.assertIsNotNone(foreign_distance.id)

        self.assertIsNotNone(foreign_mass.id)

        calculate_activity(foreign_activity)

        response = self.client.get(
            f"{self.base}/impactos-ambientales/" f"?obra={obra_a.id}"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(response.data)

        self.assertEqual(
            {item["obra"] for item in response.data},
            {obra_a.id},
        )

    def test_serializacion_conserva_metodologia_seleccionada_calculable(self):
        self.observe("distancia_recorrida_km", "132", "km")
        self.observe("masa_transportada_t", "18", "t")

        payload = _serialize_selection(select_methodology(self.activity))

        self.assertEqual(payload["estado"], "calculable_completo")
        self.assertEqual(payload["metodologia_seleccionada"]["nombre"], "Transporte t.km")
        self.assertIsNone(payload["metodologia_candidata"])

    def test_calidad_bloqueada_expone_candidata_sin_fingir_seleccion(self):
        blocked = {
            "estado": "no_calculable",
            "motivos": [
                "El procesamiento del respaldo presento un fallo tecnico; requiere revision."
            ],
            "advertencias": [],
            "inputs": {},
            "normalizaciones": {},
            "clasificacion_combustible": None,
            "seleccion_factor_combustible": None,
            "factor_version": None,
        }
        with patch(
            "apps.analytics.services.methodology_selector.evaluate_formula",
            return_value=blocked,
        ):
            payload = _serialize_selection(select_methodology(self.activity))

        self.assertEqual(payload["estado"], "no_calculable")
        self.assertIsNone(payload["metodologia_seleccionada"])
        self.assertEqual(
            payload["metodologia_candidata"],
            {
                "id": MetodologiaAmbiental.objects.get(codigo="met-tkm").id,
                "nombre": "Transporte t.km",
                "version": 1,
                "formula": "masa x distancia x factor",
                "estado": "requiere_revision",
            },
        )
        self.assertIn("fallo tecnico", payload["motivos"][0])

    def test_candidatas_bloqueadas_con_igual_prioridad_requieren_revision(self):
        VersionMetodologia.objects.filter(
            metodologia__codigo="met-km"
        ).update(prioridad=10)
        blocked = {
            "estado": "no_calculable",
            "motivos": ["La calidad requiere revision."],
            "advertencias": [],
            "inputs": {},
            "normalizaciones": {},
            "clasificacion_combustible": None,
            "seleccion_factor_combustible": None,
            "factor_version": None,
        }
        with patch(
            "apps.analytics.services.methodology_selector.evaluate_formula",
            return_value=blocked,
        ):
            payload = _serialize_selection(select_methodology(self.activity))

        self.assertIsNone(payload["metodologia_seleccionada"])
        self.assertIsNone(payload["metodologia_candidata"])
        self.assertTrue(payload["requiere_revision_metodologica"])
        self.assertEqual(payload["estado"], "requiere_revision")

    def test_sin_metodologias_no_expone_candidata(self):
        MetodologiaAmbiental.objects.update(activa=False)

        payload = _serialize_selection(select_methodology(self.activity))

        self.assertIsNone(payload["metodologia_seleccionada"])
        self.assertIsNone(payload["metodologia_candidata"])
        self.assertFalse(payload["requiere_revision_metodologica"])
        self.assertEqual(payload["candidatos"], [])
