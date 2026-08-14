import hashlib
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (AccionMejoraAmbiental, ActividadOperacional,
                     AlcanceProblematica, CalculoAmbiental,
                     CorreccionHistoricaAmbiental, EventoAuditoriaAmbiental,
                     EvidenciaObra, FactorAmbiental, FormulaAmbiental, HitoDecisionIA,
                     IndicadorAmbiental, IndicadorProblematica, InformeAmbiental,
                     Observacion, Organizacion, ProblematicaAmbiental,
                     RecomendacionAgenteAmbiental, RevisionProfesionalAmbiental,
                     SnapshotInformeAmbiental, SnapshotIntervencion, UsuarioOrganizacion,
                     ValorIndicador, VariableFormula, VersionFactorAmbiental,
                     VersionMetodologia, MetodologiaAmbiental, FuenteDatos)
from .services.calculation_v2 import calculate_activity
from .services.intervention_v2 import evaluate_intervention, select_action, start_action
from .services.professional_v2 import (create_correction, create_dossier,
                                       decide_review, generate_report,
                                       recalculate_for_correction,
                                       validate_report)


class ProfessionalV2Tests(APITestCase):
    def setUp(self):
        self.professional = User.objects.create_user("professional", password="test-pass", first_name="Ana", last_name="Revisora")
        self.operator = User.objects.create_user("operator-v9", password="test-pass")
        self.org = Organizacion.objects.create(nombre="Profesional Uno")
        self.other = Organizacion.objects.create(nombre="Profesional Dos")
        UsuarioOrganizacion.objects.create(user=self.professional, organizacion=self.org, rol="analista", cargo="Revisor ambiental")
        UsuarioOrganizacion.objects.create(user=self.operator, organizacion=self.org, rol="operador")
        self.client.force_login(self.professional); self.base = f"/api/organizaciones/{self.org.organizacion_id}"
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="GPS-CAM-01", tipo="gps")
        self.activity = ActividadOperacional.objects.create(organizacion=self.org, codigo="V-001", nombre="Viaje V-001", tipo="transporte", timestamp_inicio=timezone.now())
        self.distance = Observacion.objects.create(organizacion=self.org, actividad=self.activity, fuente=self.source, concepto="distancia_recorrida_km", valor_numerico=132, unidad="km", timestamp_observacion=timezone.now(), estado="validada", metodo_captura="instrumental")
        self.mass = Observacion.objects.create(organizacion=self.org, actividad=self.activity, fuente=self.source, concepto="masa_transportada_t", valor_numerico=18, unidad="t", timestamp_observacion=timezone.now(), estado="validada")
        factor = FactorAmbiental.objects.create(organizacion=self.org, codigo="factor-tkm-v9", nombre="Factor transporte X", categoria="transporte", unidad_entrada="t.km", unidad_resultado="kgCO2e")
        VersionFactorAmbiental.objects.create(factor=factor, version=1, valor=Decimal("0.1"), fuente="Fuente tecnica de prueba", estado="activo")
        method = MetodologiaAmbiental.objects.create(organizacion=self.org, codigo="met-tkm-v9", nombre="Transporte t.km", categoria="transporte", flujo="transporte_tkm")
        version = VersionMetodologia.objects.create(metodologia=method, version=1, estado="borrador")
        formula = FormulaAmbiental.objects.create(version_metodologia=version, factor_ambiental=factor, codigo="formula-tkm-v9", tipo="transporte_tkm", expresion_legible="masa x distancia x factor")
        VariableFormula.objects.create(formula=formula, clave="distancia", concepto_observacion="distancia_recorrida_km", unidad_esperada="km")
        VariableFormula.objects.create(formula=formula, clave="masa", concepto_observacion="masa_transportada_t", unidad_esperada="t")
        VersionMetodologia.objects.filter(pk=version.pk).update(estado="activa")
        self.calculation, _ = calculate_activity(self.activity)
        self.problem = ProblematicaAmbiental.objects.create(organizacion=self.org, titulo="Alta intensidad transporte", descripcion="Intensidad elevada", categoria="transporte", indicador="intensidad", unidad_indicador="kgCO2e/t", valor_inicial=10, objetivo_meta=9, fecha_deteccion=date(2026,1,1))
        self.indicator = IndicadorAmbiental.objects.create(organizacion=self.org, codigo="intensidad-v9", nombre="Intensidad kgCO2e/t", tipo="intensidad", unidad="kgCO2e/t", origen_numerador="impactos_ambientales", origen_denominador="masa_transportada_t", direccion_deseable="menor_es_mejor")
        IndicadorProblematica.objects.create(problematica=self.problem, indicador=self.indicator, rol="principal", direccion_deseada="menor_es_mejor")
        AlcanceProblematica.objects.create(problematica=self.problem, actividad_operacional=self.activity, indicador=self.indicator)
        ValorIndicador.objects.create(indicador=self.indicator, periodo_inicio=date(2026,1,1), periodo_fin=date(2026,1,31), valor=10, unidad=self.indicator.unidad, fuente_calculo="test")
        self.action = AccionMejoraAmbiental.objects.create(problematica=self.problem, titulo="Consolidar cargas", descripcion="Consolidacion")
        select_action(self.action); start_action(self.action, confirmed=True)
        ValorIndicador.objects.create(indicador=self.indicator, periodo_inicio=date(2026,2,1), periodo_fin=date(2026,2,28), valor=Decimal("8.4"), unidad=self.indicator.unidad, fuente_calculo="test")
        self.result = evaluate_intervention(self.problem)

    def review(self, state=None):
        row = RevisionProfesionalAmbiental.objects.create(organizacion=self.org, tipo="problematica", problematica=self.problem)
        if state:
            decide_review(row, state, "Antecedentes revisados", "Observaciones tecnicas", ["respaldo adicional"] if state == "solicita_antecedentes" else [], self.professional)
        return row

    def other_case(self):
        problem = ProblematicaAmbiental.objects.create(organizacion=self.org, titulo="Consumo energetico anomalo", descripcion="Caso B", categoria="energia", valor_inicial=5, objetivo_meta=4, fecha_deteccion=date.today())
        action = AccionMejoraAmbiental.objects.create(problematica=problem, titulo="Ajustar consumo", descripcion="Caso B")
        base = SnapshotIntervencion.objects.create(problematica=problem, accion=action, ciclo=1, tipo="base", fecha=date.today(), congelado=True)
        result = SnapshotIntervencion.objects.create(problematica=problem, accion=action, ciclo=1, tipo="resultado", fecha=date.today(), congelado=True)
        intervention = self.result.__class__.objects.create(problematica=problem, accion=action, ciclo=1, snapshot_base=base, snapshot_resultado=result, estado="inconclusa", fecha_evaluacion=date.today())
        return problem, intervention

    def test_revision_tipo_debe_corresponder_a_referencia(self):
        valid = RevisionProfesionalAmbiental.objects.create(organizacion=self.org, tipo="calculo", calculo=self.calculation)
        self.assertEqual(valid.calculo_id, self.calculation.id)
        evidence = EvidenciaObra.objects.create(organizacion=self.org, nombre="Respaldo", archivo=SimpleUploadedFile("respaldo.txt", b"dato"))
        self.assertEqual(RevisionProfesionalAmbiental.objects.create(organizacion=self.org, tipo="evidencia", evidencia=evidence).evidencia_id, evidence.id)
        with self.assertRaises(ValidationError):
            RevisionProfesionalAmbiental.objects.create(organizacion=self.org, tipo="calculo", evidencia=evidence)
        with self.assertRaises(ValidationError):
            RevisionProfesionalAmbiental.objects.create(organizacion=self.org, tipo="calculo")
        with self.assertRaises(ValidationError):
            RevisionProfesionalAmbiental.objects.create(organizacion=self.other, tipo="calculo", calculo=self.calculation)

    def test_informe_rechaza_referencias_de_casos_distintos(self):
        problem_b, intervention_b = self.other_case()
        valid = generate_report(self.org, "problematica", self.professional, problem=problem_b, intervention=intervention_b)
        self.assertEqual(valid.estado, "generado")
        before = InformeAmbiental.objects.count()
        with self.assertRaises(ValidationError):
            generate_report(self.org, "problematica", self.professional, problem=self.problem, intervention=intervention_b)
        dossier = create_dossier(self.problem, self.professional)
        with self.assertRaises(ValidationError):
            generate_report(self.org, "expediente", self.professional, problem=problem_b, dossier=dossier)
        self.assertEqual(InformeAmbiental.objects.count(), before)

    def test_servicio_informe_exige_tipo_y_objeto_principal(self):
        with self.assertRaises(ValidationError):
            generate_report(self.org, "actividad", self.professional)
        with self.assertRaises(ValidationError):
            generate_report(self.org, "desconocido", self.professional, problem=self.problem)

    def test_validacion_exige_version_generada_completa(self):
        draft = InformeAmbiental.objects.create(organizacion=self.org, tipo="problematica", problematica=self.problem, version=99, estado="borrador", generado_por=self.professional)
        with self.assertRaises(ValidationError):
            validate_report(draft, self.professional)
        report = generate_report(self.org, "problematica", self.professional, problem=self.problem)
        validate_report(report, self.professional)
        self.assertEqual(report.estado, "validado")
        with self.assertRaises(ValidationError):
            validate_report(report, self.professional)
        report.metadata = {"mutacion": True}
        with self.assertRaises(ValidationError):
            report.save()

    def test_crear_revision_y_rechazar_cross_tenant(self):
        response = self.client.post(f"{self.base}/revisiones-profesionales/", {"tipo":"problematica", "problematica":self.problem.id}, format="json")
        self.assertEqual(response.status_code, 201)
        foreign = ProblematicaAmbiental.objects.create(organizacion=self.other, titulo="Ajena", descripcion="x", categoria="x", valor_inicial=1, objetivo_meta=0, fecha_deteccion=date.today())
        self.assertEqual(self.client.post(f"{self.base}/revisiones-profesionales/", {"tipo":"problematica", "problematica":foreign.id}, format="json").status_code, 400)

    def test_hallazgo_validacion_y_revision_decidida_inmutable(self):
        review = self.review()
        finding = self.client.post(f"{self.base}/revisiones-profesionales/{review.id}/hallazgos/", {"tipo":"observacion", "severidad":"media", "observacion":"Trazabilidad completa", "recomendacion":"Conservar anexos"}, format="json")
        self.assertEqual(finding.status_code, 201)
        decision = self.client.post(f"{self.base}/revisiones-profesionales/{review.id}/decision/", {"estado":"validada_con_observaciones", "conclusion":"Validada", "observaciones":"Mantener referencias"}, format="json")
        self.assertEqual(decision.status_code, 200); review.refresh_from_db(); self.assertEqual(review.profesional, self.professional)
        review.observaciones = "Cambio destructivo"
        with self.assertRaises(ValidationError): review.save()

    def test_solicitar_antecedentes_y_usuario_sin_permiso_no_valida(self):
        requested = self.review("solicita_antecedentes"); self.assertEqual(requested.antecedentes_solicitados, ["respaldo adicional"])
        pending = self.review(); self.client.force_login(self.operator)
        response = self.client.post(f"{self.base}/revisiones-profesionales/{pending.id}/decision/", {"estado":"validada", "conclusion":"No autorizado"}, format="json")
        self.assertEqual(response.status_code, 400); pending.refresh_from_db(); self.assertEqual(pending.estado, "pendiente")

    def test_correccion_no_cambia_observacion_original(self):
        review = self.review("validada_con_observaciones")
        correction = create_correction(review, self.professional, "Valor requiere aclaracion", {"valor":"132"}, {"valor":"133"}, observacion_afectada=self.distance)
        self.distance.refresh_from_db(); self.assertEqual(self.distance.valor_numerico, Decimal("132")); self.assertEqual(correction.propuesta_corregida["valor"], "133")

    def test_recalculo_por_correccion_crea_nuevo_calculo(self):
        review = self.review("validada_con_observaciones")
        correction = create_correction(review, self.professional, "Recalcular sin sobrescribir", {"calculo":self.calculation.id}, {"recalcular":True}, calculo_afectado=self.calculation)
        new = recalculate_for_correction(correction); self.calculation.refresh_from_db()
        self.assertNotEqual(new.id, self.calculation.id); self.assertEqual(CalculoAmbiental.objects.filter(actividad=self.activity).count(), 2)
        self.assertEqual(self.calculation.resultado, Decimal("237.6000000000"))

    def test_eventos_auditoria_y_expediente_referencias(self):
        dossier = create_dossier(self.problem, self.professional)
        self.assertEqual(dossier.referencias["problematica"], self.problem.id)
        self.assertIn(self.action.id, dossier.referencias["acciones"]); self.assertIn(self.result.id, dossier.referencias["resultados"])
        self.assertTrue(EventoAuditoriaAmbiental.objects.filter(tipo="creacion_expediente", referencia=str(dossier.id)).exists())

    def test_cerrar_y_reabrir_conserva_cierre(self):
        dossier = create_dossier(self.problem, self.professional)
        closed = self.client.post(f"{self.base}/expedientes/{dossier.id}/cerrar/", {}, format="json")
        self.assertEqual(closed.status_code, 200); closed_at = closed.data["cerrado_at"]
        reopened = self.client.post(f"{self.base}/expedientes/{dossier.id}/reabrir/", {"motivo":"Nueva evidencia"}, format="json")
        self.assertEqual(reopened.status_code, 200); self.assertEqual(reopened.data["cerrado_at"], closed_at); self.assertEqual(reopened.data["estado"], "reabierto")

    def test_caso_obligatorio_informe_pdf_snapshot_checksum_y_trazabilidad(self):
        review = self.review("validada_con_observaciones")
        report = generate_report(self.org, "problematica", self.professional, problem=self.problem)
        self.assertEqual(report.estado, "generado"); self.assertEqual(len(report.checksum_sha256), 64)
        with report.archivo.open("rb") as stream:
            content = stream.read(); self.assertEqual(hashlib.sha256(content).hexdigest(), report.checksum_sha256)
            text = content.decode("latin-1")
        for expected in ("Viaje V-001", "132", "18", "Transporte t.km", "Factor transporte X", "8.4", "validada_con_observaciones"):
            self.assertIn(expected, text)
        self.assertEqual(report.snapshot.contenido["problematica"]["titulo"], "Alta intensidad transporte")
        self.assertEqual(review.estado, "validada_con_observaciones")

    def test_snapshot_estable_regenerar_crea_version_y_checksum_nuevo(self):
        first = generate_report(self.org, "problematica", self.professional, problem=self.problem)
        frozen = first.snapshot.contenido.copy(); self.problem.titulo = "Titulo posterior"; self.problem.save()
        first.snapshot.refresh_from_db(); self.assertEqual(first.snapshot.contenido, frozen)
        second = generate_report(self.org, "problematica", self.professional, problem=self.problem)
        self.assertEqual(second.version, 2); self.assertNotEqual(first.id, second.id); self.assertNotEqual(first.checksum_sha256, second.checksum_sha256)

    def test_informe_validado_inmutable_y_permisos(self):
        report = generate_report(self.org, "problematica", self.professional, problem=self.problem)
        self.client.force_login(self.operator)
        self.assertEqual(self.client.post(f"{self.base}/informes/{report.id}/validar/", {}, format="json").status_code, 400)
        validate_report(report, self.professional); report.metadata = {"cambio":True}
        with self.assertRaises(ValidationError): report.save()

    def test_ia_no_equivale_revision_y_negativos_aparecen(self):
        proposal = RecomendacionAgenteAmbiental.objects.create(problematica=self.problem, accion="Propuesta", justificacion="IA", indicador_afectado="intensidad-v9", resultado_esperado="Pendiente", prioridad="media", periodo_seguimiento="30", nivel_confianza="media")
        HitoDecisionIA.objects.create(organizacion=self.org, problematica=self.problem, propuesta=proposal, tipo="propuesta", resumen="Propuesta IA")
        self.assertEqual(self.problem.revisiones_profesionales.count(), 0)
        self.result.estado = "negativa"; self.result.save(update_fields=["estado"])
        report = generate_report(self.org, "problematica", self.professional, problem=self.problem)
        self.assertEqual(report.snapshot.contenido["problematica"]["resultados_negativos"][0]["id"], self.result.id)

    def test_api_informe_pdf_y_tenant(self):
        created = self.client.post(f"{self.base}/informes/", {"tipo":"problematica", "problematica":self.problem.id}, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.client.get(f"{self.base}/informes/{created.data['id']}/pdf/").status_code, 200)
        foreign = ProblematicaAmbiental.objects.create(organizacion=self.other, titulo="Foreign", descripcion="x", categoria="x", valor_inicial=1, objetivo_meta=0, fecha_deteccion=date.today())
        self.assertEqual(self.client.post(f"{self.base}/informes/", {"tipo":"problematica", "problematica":foreign.id}, format="json").status_code, 404)
