from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import (AplicabilidadCapacidadObra, EventoMaterial, MaterialOperacional, Obra,
                      ProblematicaAmbiental)
from .materials_v2 import material_balance
from .onboarding import onboarding_environmental_capabilities
from .sector_flows_v1 import sector_summary
from .transport_v2 import transport_indicators


OPEN_PROBLEM_STATES = set(ProblematicaAmbiental.Estado.values) - {
    ProblematicaAmbiental.Estado.CERRADA,
    ProblematicaAmbiental.Estado.RESUELTA,
}


def construction_indicators(work):
    return {
        "alcance": {"tipo": "obra", "obra_id": work.id, "codigo": work.codigo_obra},
        "transporte": transport_indicators(work.organizacion, work=work),
        "flujos": sector_summary(work.organizacion, work=work)["indicadores"],
        "corporativo": False,
    }


def construction_materials(work):
    material_ids = EventoMaterial.objects.filter(organizacion=work.organizacion, obra=work).values_list("material_id", flat=True).distinct()
    return [material_balance(work.organizacion, material, work=work)
            for material in MaterialOperacional.objects.filter(id__in=material_ids).order_by("nombre")]


def environmental_timeline(work):
    base = {"actor": "Sistema Carbono Zero", "origen": "Plataforma", "estado": "registrado"}
    events = [{**base, "tipo": "obra_creada", "fecha": work.created_at, "referencia_id": work.id, "titulo": "Obra creada", "entidad": "obra", "entidad_id": work.id}]
    events += [{**base, "tipo": "diagnostico_inicial", "fecha": row.created_at, "referencia_id": row.id, "titulo": "Diagnostico ambiental", "entidad": "diagnostico", "entidad_id": row.id}
               for row in work.diagnosticos_ambientales.all()]
    events += [{**base, "tipo": "evidencia", "fecha": row.created_at, "referencia_id": row.id, "titulo": row.nombre, "entidad": "evidencia", "entidad_id": row.id, "estado": row.estado_documental}
               for row in work.evidencias.all()]
    events += [{**base, "tipo": "actividad", "fecha": row.timestamp_inicio, "referencia_id": row.id, "titulo": row.nombre, "entidad": "actividad_operacional", "entidad_id": row.id, "estado": row.estado}
               for row in work.actividades_operacionales.all()]
    events += [{"tipo": row.tipo, "fecha": row.created_at, "referencia_id": row.id,
                "titulo": row.get_tipo_display(), "descripcion": row.metadata.get("descripcion", "") if isinstance(row.metadata, dict) else "",
                "actor": row.usuario or "Sistema Carbono Zero", "origen": row.fuente or "Importación",
                "entidad": "evidencia" if row.evidencia_id else "dato_operacional",
                "entidad_id": row.evidencia_id, "estado": row.tipo,
                "estado_anterior": row.raw_payload or {}, "estado_nuevo": row.normalized_payload or {},
                "metadata": row.metadata or {}}
               for row in work.historial_cambios.select_related("evidencia").all()]
    for problem in work.problematicas_ambientales.prefetch_related("acciones", "resultados_intervencion"):
        events.append({**base, "tipo": "problematica", "fecha": problem.created_at, "referencia_id": problem.id, "titulo": problem.titulo, "entidad": "problematica", "entidad_id": problem.id, "estado": problem.estado})
        events += [{**base, "tipo": "accion", "fecha": row.created_at, "referencia_id": row.id, "titulo": row.titulo, "entidad": "accion", "entidad_id": row.id, "estado": row.estado}
                   for row in problem.acciones.all()]
        events += [{**base, "tipo": "resultado", "fecha": row.created_at, "referencia_id": row.id, "titulo": row.estado, "entidad": "resultado", "entidad_id": row.id, "estado": row.estado}
                   for row in problem.resultados_intervencion.all()]
    if work.estado_ambiental == Obra.EstadoAmbiental.CERRADA and work.fecha_cierre_ambiental:
        events.append({**base, "tipo": "cierre_ambiental", "fecha": work.fecha_cierre_ambiental,
                       "referencia_id": work.id, "titulo": work.get_estado_ambiental_display(),
                       "entidad": "obra", "entidad_id": work.id, "estado": work.estado_ambiental})
    return sorted(events, key=lambda item: (str(item["fecha"]), item["tipo"]))


def work_context(work):
    capabilities = onboarding_environmental_capabilities(work.organizacion)
    diagnosis = work.diagnosticos_ambientales.prefetch_related("elementos", "aplicabilidades_capacidades__capacidad").first()
    applicability = {row.capacidad_id: row for row in diagnosis.aplicabilidades_capacidades.all()} if diagnosis else {}
    indicators = construction_indicators(work)
    open_problems = work.problematicas_ambientales.filter(estado__in=OPEN_PROBLEM_STATES)
    return {
        "context_type": "work",
        "references": {"organization": work.organizacion.organizacion_id, "work": work.id},
        "obra": {"codigo": work.codigo_obra, "nombre": work.nombre, "tipo_proyecto": work.tipo_proyecto,
                 "perfil": work.perfil_ambiental,
                 "estado": work.estado, "estado_ambiental": work.estado_ambiental},
        "capacidades_organizacion": [{"clave": row.capacidad.clave, "estado_organizacion": row.estado,
                                       "disponible_preset": row.recomendada_por_preset} for row in capabilities],
        "diagnostico_obra": ({
            "id": diagnosis.id, "estado": diagnosis.estado,
            "aplicabilidad": [{"clave": row.capacidad.clave,
                                "estado_obra": applicability[row.capacidad_id].estado if row.capacidad_id in applicability else AplicabilidadCapacidadObra.Estado.NO_DETERMINADO}
                               for row in capabilities],
            "elementos": list(diagnosis.elementos.values("id", "tipo", "nombre", "descripcion")),
        } if diagnosis else {
            "id": None, "estado": "no_determinado",
            "aplicabilidad": [{"clave": row.capacidad.clave, "estado_obra": AplicabilidadCapacidadObra.Estado.NO_DETERMINADO}
                               for row in capabilities], "elementos": [],
        }),
        "indicadores": indicators,
        "problematicas_abiertas": list(open_problems.values("id", "titulo", "categoria", "estado")[:10]),
        "acciones_actuales": list(open_problems.values("acciones__id", "acciones__titulo", "acciones__estado")[:10]),
        "materiales": construction_materials(work)[:10],
        "evidencia": {"total": work.evidencias.count(), "versiones": sum(row.versiones.count() for row in work.evidencias.all())},
        "timeline": environmental_timeline(work)[-20:],
    }


@transaction.atomic
def close_environmental_work(work, observations=""):
    pending = work.problematicas_ambientales.filter(estado__in=OPEN_PROBLEM_STATES).exists()
    work.fecha_cierre_ambiental = None if pending else timezone.localdate()
    work.observaciones_cierre_ambiental = observations
    work.estado_ambiental = Obra.EstadoAmbiental.CIERRE_PENDIENTE if pending else Obra.EstadoAmbiental.CERRADA
    work.save(update_fields=["fecha_cierre_ambiental", "observaciones_cierre_ambiental", "estado_ambiental", "updated_at"])
    return work


def assert_same_work(left, right):
    if left != right:
        raise ValidationError("BASE y RESULT deben conservar la misma obra.")
