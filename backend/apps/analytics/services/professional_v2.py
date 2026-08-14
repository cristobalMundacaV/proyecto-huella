import hashlib
import io
import json
from datetime import date

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from ..models import (CalculoAmbiental, CorreccionHistoricaAmbiental,
                      EventoAuditoriaAmbiental, ExpedienteAmbiental,
                      InformeAmbiental, RevisionProfesionalAmbiental,
                      SnapshotInformeAmbiental, UsuarioOrganizacion)
from .calculation_v2 import calculate_activity


REVIEW_ROLES = {UsuarioOrganizacion.Rol.ADMIN, UsuarioOrganizacion.Rol.ANALISTA}


def can_review(user, organization):
    return bool(user and user.is_authenticated and (user.is_superuser or UsuarioOrganizacion.objects.filter(user=user, organizacion=organization, activo=True, rol__in=REVIEW_ROLES).exists()))


def audit(organization, event_type, actor, entity, reference, summary, metadata=None):
    safe_metadata = json.loads(json.dumps(metadata or {}, default=str, ensure_ascii=False))
    return EventoAuditoriaAmbiental.objects.create(organizacion=organization, tipo=event_type, actor=actor if getattr(actor, "is_authenticated", False) else None, entidad=entity, referencia=str(reference), resumen=summary, metadata_auditable=safe_metadata)


def decide_review(review, state, conclusion, observations, requested, user):
    if not can_review(user, review.organizacion):
        raise ValidationError("El usuario no tiene capacidad de revision profesional.")
    if review.estado != RevisionProfesionalAmbiental.Estado.PENDIENTE:
        raise ValidationError("La revision ya tiene una decision.")
    if state not in RevisionProfesionalAmbiental.Estado.values or state == RevisionProfesionalAmbiental.Estado.PENDIENTE:
        raise ValidationError("Decision profesional invalida.")
    membership = UsuarioOrganizacion.objects.filter(user=user, organizacion=review.organizacion, activo=True).first()
    review.estado = state; review.profesional = user
    review.profesional_nombre = user.get_full_name() or user.get_username()
    review.profesional_cargo = membership.cargo if membership else ""
    review.fecha = timezone.now(); review.conclusion = conclusion; review.observaciones = observations
    review.antecedentes_solicitados = requested or []
    review.save(update_fields=["estado", "profesional", "profesional_nombre", "profesional_cargo", "fecha", "conclusion", "observaciones", "antecedentes_solicitados"])
    audit(review.organizacion, "revision_profesional", user, "RevisionProfesionalAmbiental", review.id, f"Revision profesional: {state}.", {"version": review.version})
    return review


@transaction.atomic
def create_correction(review, user, reason, previous, proposed, **references):
    if review.estado not in {RevisionProfesionalAmbiental.Estado.VALIDADA_OBSERVACIONES, RevisionProfesionalAmbiental.Estado.RECHAZADA}:
        raise ValidationError("La correccion requiere una revision profesional decidida con observaciones o rechazo.")
    correction = CorreccionHistoricaAmbiental.objects.create(
        organizacion=review.organizacion, motivo=reason, valor_estado_anterior=previous,
        propuesta_corregida=proposed, autor=user, revision_origen=review,
        version=review.correcciones_historicas.count() + 1, **references,
    )
    audit(review.organizacion, "correccion_historica", user, "CorreccionHistoricaAmbiental", correction.id, reason, {"revision": review.id})
    return correction


@transaction.atomic
def recalculate_for_correction(correction):
    if not correction.calculo_afectado_id:
        raise ValidationError("La correccion no referencia un calculo.")
    calculation, _ = calculate_activity(correction.calculo_afectado.actividad)
    correction.recalculo_generado = calculation; correction.save(update_fields=["recalculo_generado"])
    audit(correction.organizacion, "recalculo", correction.autor, "CalculoAmbiental", calculation.id, "Nuevo calculo generado desde correccion historica.", {"calculo_anterior": correction.calculo_afectado_id, "correccion": correction.id})
    return calculation


def build_dossier_references(problem):
    activity_ids = list(problem.alcances_v2.exclude(actividad_operacional=None).values_list("actividad_operacional_id", flat=True))
    calculation_ids = list(CalculoAmbiental.objects.filter(organizacion=problem.organizacion, actividad_id__in=activity_ids).values_list("id", flat=True))
    observation_rows = problem.organizacion.observaciones_operacionales.filter(actividad_id__in=activity_ids)
    return {
        "problematica": problem.id,
        "alcance": list(problem.alcances_v2.values_list("id", flat=True)),
        "indicadores": list(problem.indicadores_v2.values_list("indicador_id", flat=True)),
        "actividades": activity_ids,
        "observaciones": list(observation_rows.values_list("id", flat=True)),
        "evidencias": list(observation_rows.exclude(evidencia=None).values_list("evidencia_id", flat=True).distinct()),
        "calculos": calculation_ids,
        "impactos": list(problem.organizacion.impactos_ambientales_v2.filter(calculo_id__in=calculation_ids).values_list("id", flat=True)),
        "discrepancias": list(problem.organizacion.discrepancias_dato.filter(actividad_id__in=activity_ids).values_list("id", flat=True)),
        "acciones": list(problem.acciones.values_list("id", flat=True)),
        "ciclos": list(problem.ciclos_reevaluacion.values_list("id", flat=True)),
        "snapshots": list(problem.snapshots_intervencion.values_list("id", flat=True)),
        "resultados": list(problem.resultados_intervencion.values_list("id", flat=True)),
        "propuestas_ia": list(problem.recomendaciones_agente.exclude(estado="descartada").values_list("id", flat=True)),
        "decisiones_humanas": list(problem.hitos_decision_ia.filter(tipo="decision_humana").values_list("id", flat=True)),
        "revisiones": list(problem.revisiones_profesionales.values_list("id", flat=True)),
        "correcciones": list(CorreccionHistoricaAmbiental.objects.filter(revision_origen__problematica=problem).values_list("id", flat=True)),
    }


def create_dossier(problem, user):
    version = (problem.expedientes.order_by("-version").values_list("version", flat=True).first() or 0) + 1
    dossier = ExpedienteAmbiental.objects.create(
        problematica=problem, version=version, contenido_procesado={}, resumen_ejecutivo=f"Expediente tecnico de {problem.titulo}",
        generado_por=user.get_username(), responsable=user, referencias=build_dossier_references(problem), estado="abierto",
    )
    audit(problem.organizacion, "creacion_expediente", user, "ExpedienteAmbiental", dossier.id, "Expediente ambiental creado.", {"version": version})
    return dossier


def close_dossier(dossier, user):
    if not can_review(user, dossier.problematica.organizacion): raise ValidationError("No autorizado para cerrar expediente.")
    dossier.estado = "cerrado"; dossier.cerrado_por = user; dossier.cerrado_at = timezone.now(); dossier.save(update_fields=["estado", "cerrado_por", "cerrado_at"])
    audit(dossier.problematica.organizacion, "cierre_expediente", user, "ExpedienteAmbiental", dossier.id, "Expediente cerrado.", {"version": dossier.version})
    return dossier


def reopen_dossier(dossier, user, reason):
    if not can_review(user, dossier.problematica.organizacion): raise ValidationError("No autorizado para reabrir expediente.")
    if dossier.estado != "cerrado" or not reason: raise ValidationError("La reapertura requiere expediente cerrado y motivo.")
    dossier.estado = "reabierto"; dossier.reabierto_por = user; dossier.reabierto_at = timezone.now(); dossier.motivo_reapertura = reason
    dossier.save(update_fields=["estado", "reabierto_por", "reabierto_at", "motivo_reapertura"])
    audit(dossier.problematica.organizacion, "reapertura_expediente", user, "ExpedienteAmbiental", dossier.id, reason, {"cierre_anterior": dossier.cerrado_at})
    return dossier


def _activity_snapshot(activity):
    observations = activity.observaciones.select_related("fuente", "evidencia", "version_evidencia")
    calculations = activity.calculos_ambientales.select_related("version_metodologia__metodologia", "formula", "version_factor__factor").prefetch_related("inputs__observacion", "inputs__fuente")
    return {
        "actividad": {"id": activity.id, "codigo": activity.codigo, "nombre": activity.nombre, "tipo": activity.tipo, "inicio": activity.timestamp_inicio},
        "observaciones": [{"id": row.id, "concepto": row.concepto, "valor": row.valor_numerico if row.valor_numerico is not None else row.valor_texto, "unidad": row.unidad, "fuente": row.fuente.nombre, "fuente_tipo": row.fuente.tipo, "evidencia": row.evidencia.nombre if row.evidencia_id else None, "version_evidencia": row.version_evidencia.version if row.version_evidencia_id else None, "archivo": row.version_evidencia.nombre_original if row.version_evidencia_id else None, "checksum": row.version_evidencia.checksum_sha256 if row.version_evidencia_id else None} for row in observations],
        "calculos": [{"id": row.id, "metodologia": row.version_metodologia.metodologia.nombre, "metodologia_version": row.version_metodologia.version, "formula": row.formula.expresion_legible, "factor": row.version_factor.factor.nombre, "factor_version": row.version_factor.version, "inputs": [{"concepto": value.concepto, "valor": value.valor_utilizado, "unidad": value.unidad, "observacion": value.observacion_id, "fuente": value.fuente.nombre} for value in row.inputs.all()], "resultado": row.resultado, "unidad": row.unidad_resultado} for row in calculations],
    }


def build_report_snapshot(organization, report_type, activity=None, problem=None, intervention=None, dossier=None):
    data = {"organizacion": {"id": organization.organizacion_id, "nombre": organization.nombre}, "tipo": report_type, "generado_en": timezone.now()}
    activities = []
    if activity: activities = [activity]
    elif problem:
        activities = list({row.actividad_operacional for row in problem.alcances_v2.select_related("actividad_operacional") if row.actividad_operacional_id})
    data["trazabilidad"] = [_activity_snapshot(item) for item in activities]
    if problem:
        data["problematica"] = {"id": problem.id, "titulo": problem.titulo, "estado": problem.estado, "alcance": build_dossier_references(problem)["alcance"], "indicadores": [{"codigo": row.indicador.codigo, "rol": row.rol, "meta": row.valor_objetivo} for row in problem.indicadores_v2.select_related("indicador")], "acciones": list(problem.acciones.values("id", "titulo", "estado")), "ciclos": [{"numero": row.numero, "resultado": row.resultado.estado if row.resultado_id else None, "metricas": row.resultado.metricas_comparadas if row.resultado_id else []} for row in problem.ciclos_reevaluacion.select_related("resultado")], "resultados_negativos": list(problem.resultados_intervencion.filter(estado="negativa").values("id", "ciclo", "metricas_comparadas"))}
        data["revisiones_profesionales"] = [{"id": row.id, "estado": row.estado, "version": row.version, "profesional": row.profesional_nombre, "conclusion": row.conclusion, "hallazgos": list(row.hallazgos.values("tipo", "severidad", "observacion", "referencia_tecnica"))} for row in problem.revisiones_profesionales.prefetch_related("hallazgos")]
    if intervention: data["intervencion"] = {"id": intervention.id, "estado": intervention.estado, "base": intervention.snapshot_base_id, "resultado": intervention.snapshot_resultado_id, "metricas": intervention.metricas_comparadas, "conclusion": intervention.conclusion_estructurada}
    if dossier: data["expediente"] = {"id": dossier.id, "version": dossier.version, "estado": dossier.estado, "referencias": dossier.referencias}
    data["auditoria"] = list(organization.eventos_auditoria_ambiental.values("tipo", "entidad", "referencia", "resumen", "timestamp")[:30])
    return json.loads(json.dumps(data, default=str, ensure_ascii=False))


def _pdf_bytes(snapshot, version):
    output = io.BytesIO(); pdf = canvas.Canvas(output, pagesize=A4, pageCompression=0); width, height = A4; y = height - 55
    lines = ["CARBONO ZERO - INFORME AMBIENTAL PROFESIONAL", f"Organizacion: {snapshot['organizacion']['nombre']}", f"Tipo informe: {snapshot['tipo']}", f"Version: {version}", "", "RESUMEN EJECUTIVO"]
    for trace in snapshot.get("trazabilidad", []):
        lines.extend(["", "DATOS Y TRAZABILIDAD", f"Actividad: {trace['actividad']['nombre']} ({trace['actividad']['codigo']})"])
        for observation in trace.get("observaciones", []):
            lines.append(f"Dato: {observation['concepto']} = {observation['valor']} {observation['unidad']} | Origen: {observation['fuente']}")
            if observation.get("archivo"):
                lines.append(f"Archivo: {observation['archivo']} | Version: {observation['version_evidencia']} | Checksum: {observation['checksum']}")
        for calculation in trace.get("calculos", []):
            lines.extend([f"Metodologia: {calculation['metodologia']} | Version: {calculation['metodologia_version']}", f"Formula: {calculation['formula']}", f"Factor: {calculation['factor']} | Version: {calculation['factor_version']}", f"Resultado: {calculation['resultado']} {calculation['unidad']}"])
    for cycle in snapshot.get("problematica", {}).get("ciclos", []):
        for metric in cycle.get("metricas", []):
            lines.append(f"Intervencion ciclo {cycle['numero']}: BASE {metric['base']} | RESULTADO {metric['resultado']} | Variacion {metric['porcentaje']}% | Estado {cycle['resultado']}")
    for review in snapshot.get("revisiones_profesionales", []):
        lines.append(f"Revision profesional: {review['estado']} | Profesional: {review['profesional']} | Version: {review['version']}")
    for section in ("trazabilidad", "problematica", "intervencion", "revisiones_profesionales", "auditoria"):
        lines.extend(["", section.upper(), json.dumps(snapshot.get(section, []), ensure_ascii=False, default=str)])
    for raw in lines:
        chunks = [raw[index:index+105] for index in range(0, len(raw), 105)] or [""]
        for line in chunks:
            if y < 50: pdf.showPage(); y = height - 55
            pdf.drawString(45, y, line); y -= 13
    pdf.save(); return output.getvalue()


@transaction.atomic
def generate_report(organization, report_type, user, activity=None, problem=None, intervention=None, dossier=None):
    for item in (activity, problem, intervention, dossier):
        if item:
            owner_id = item.organizacion_id if hasattr(item, "organizacion_id") else item.problematica.organizacion_id
            if owner_id != organization.id: raise ValidationError("El objeto principal pertenece a otra organizacion.")
    query = InformeAmbiental.objects.filter(organizacion=organization, tipo=report_type, actividad=activity, problematica=problem, intervencion=intervention, expediente=dossier)
    version = (query.order_by("-version").values_list("version", flat=True).first() or 0) + 1
    report = InformeAmbiental.objects.create(organizacion=organization, tipo=report_type, actividad=activity, problematica=problem, intervencion=intervention, expediente=dossier, version=version, estado="borrador", generado_por=user)
    snapshot_data = build_report_snapshot(organization, report_type, activity, problem, intervention, dossier)
    SnapshotInformeAmbiental.objects.create(informe=report, contenido=snapshot_data, referencias={"actividad": activity.id if activity else None, "problematica": problem.id if problem else None, "intervencion": intervention.id if intervention else None, "expediente": dossier.id if dossier else None})
    content = _pdf_bytes(snapshot_data, version); checksum = hashlib.sha256(content).hexdigest()
    report.archivo.save(f"informe-{report_type}-{report.id}-v{version}.pdf", ContentFile(content), save=False)
    report.checksum_sha256 = checksum; report.estado = "generado"; report.metadata = {"snapshot": report.snapshot.id, "sha256": checksum}; report.save(update_fields=["archivo", "checksum_sha256", "estado", "metadata"])
    audit(organization, "generacion_informe", user, "InformeAmbiental", report.id, "Informe ambiental generado.", {"version": version, "checksum": checksum})
    return report


def validate_report(report, user):
    if not can_review(user, report.organizacion): raise ValidationError("El usuario no tiene capacidad de revision profesional.")
    if report.estado == "validado": raise ValidationError("El informe ya fue validado.")
    report.estado = "validado"; report.validado_por = user; report.validado_at = timezone.now(); report.save(update_fields=["estado", "validado_por", "validado_at"])
    audit(report.organizacion, "validacion_informe", user, "InformeAmbiental", report.id, "Version de informe validada.", {"version": report.version, "checksum": report.checksum_sha256})
    return report
