from collections import defaultdict
from decimal import Decimal

from django.db.models import Prefetch

from ..models import Observacion, RegistroFlujoAmbiental


def _rows(organization, *, flow=None, start=None, end=None, work=None, process=None, asset=None, point=None):
    rows = RegistroFlujoAmbiental.objects.filter(organizacion=organization).select_related(
        "actividad", "punto", "unidad_operacional", "proceso", "activo", "obra", "evento_material"
    ).prefetch_related(Prefetch("actividad__observaciones", queryset=Observacion.objects.select_related("fuente", "evidencia", "version_evidencia").order_by("timestamp_observacion", "id")))
    if flow: rows = rows.filter(flujo=flow)
    if start: rows = rows.filter(periodo_inicio__date__gte=start)
    if end: rows = rows.filter(periodo_inicio__date__lte=end)
    if work is not None: rows = rows.filter(obra=work)
    if process is not None: rows = rows.filter(proceso=process)
    if asset is not None: rows = rows.filter(activo=asset)
    if point is not None: rows = rows.filter(punto=point)
    return rows


def _scope(record):
    return {"granularidad": record.granularidad, "unidad_operacional_id": record.unidad_operacional_id,
            "obra_id": record.obra_id, "proceso_id": record.proceso_id, "activo_id": record.activo_id,
            "punto_id": record.punto_id}


def record_summary(record):
    observations = list(record.actividad.observaciones.all())
    return {
        "id": record.id, "flujo": record.flujo, "periodo_inicio": record.periodo_inicio,
        "periodo_fin": record.periodo_fin, "alcance": _scope(record), "tipo_recurso": record.tipo_recurso,
        "metrica": record.metrica, "destino_operacional": record.destino_operacional,
        "mediciones": [{"id": row.id, "concepto": row.concepto, "valor": row.valor_numerico if row.valor_numerico is not None else row.valor_texto,
                         "unidad": row.unidad, "fuente_id": row.fuente_id, "evidencia_id": row.evidencia_id,
                         "version_evidencia_id": row.version_evidencia_id, "metodo_captura": row.metodo_captura,
                         "naturaleza": row.naturaleza, "estado": row.estado} for row in observations[:20]],
    }


def sector_summary(organization, **filters):
    aggregates = defaultdict(lambda: {"total": Decimal("0"), "mediciones": 0, "registros_ambiguos": 0, "minimo": None, "maximo": None})
    records = []
    signals = []
    for record in _rows(organization, **filters):
        records.append(record_summary(record))
        per_activity = defaultdict(list)
        for observation in record.actividad.observaciones.all():
            if observation.valor_numerico is not None:
                per_activity[(observation.concepto, observation.unidad)].append(observation.valor_numerico)
            elif observation.valor_texto:
                normalized = observation.valor_texto.strip().lower()
                if record.flujo == RegistroFlujoAmbiental.Flujo.GESTION_HIDRICA_SUELO and observation.concepto in {"desborde", "erosion_observada", "acumulacion_agua", "sedimentos"} and normalized not in {"no", "false", "sin", "0"}:
                    signals.append({"tipo": observation.concepto, "registro_id": record.id, "observacion_id": observation.id})
        for (concept, unit), values in per_activity.items():
            key = (record.flujo, concept, unit, record.granularidad, record.unidad_operacional_id, record.obra_id, record.proceso_id, record.activo_id, record.punto_id, record.metrica)
            item = aggregates[key]
            item["mediciones"] += len(values)
            item["minimo"] = min(values) if item["minimo"] is None else min(item["minimo"], *values)
            item["maximo"] = max(values) if item["maximo"] is None else max(item["maximo"], *values)
            if len(values) == 1:
                item["total"] += values[0]
            else:
                item["registros_ambiguos"] += 1
    indicators = []
    for key, values in aggregates.items():
        flow, concept, unit, granularity, unit_id, work_id, process_id, asset_id, point_id, metric = key
        indicators.append({"flujo": flow, "concepto": concept, "unidad": unit, "metrica": metric,
                           "alcance": {"granularidad": granularity, "unidad_operacional_id": unit_id, "obra_id": work_id, "proceso_id": process_id, "activo_id": asset_id, "punto_id": point_id}, **values})
    return {"organizacion_id": organization.organizacion_id, "indicadores": indicators, "senales": signals, "registros": records[:20], "cumplimiento_normativo": None, "impacto_ambiental": None}
