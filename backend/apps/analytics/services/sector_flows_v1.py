from collections import defaultdict
from decimal import Decimal

from django.db import transaction

from ..models import Observacion, RegistroFlujoAmbiental
from ..selectors.environmental_flows import environmental_records_for_organization
from .capture import capture_observation

ADDITIVE_CONCEPTS = {
    (RegistroFlujoAmbiental.Flujo.ENERGIA, "consumo_energia"),
    (RegistroFlujoAmbiental.Flujo.GENERACION_PROPIA, "energia_generada"),
    (RegistroFlujoAmbiental.Flujo.GENERACION_PROPIA, "energia_autoconsumida"),
    (RegistroFlujoAmbiental.Flujo.GENERACION_PROPIA, "energia_exportada"),
    (RegistroFlujoAmbiental.Flujo.AGUA, "consumo_agua"),
    (RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO, "combustible_consumido"),
    (RegistroFlujoAmbiental.Flujo.RESIDUO, "cantidad_residuo"),
}


def _rows(
    organization,
    *,
    flow=None,
    start=None,
    end=None,
    work=None,
    process=None,
    asset=None,
    point=None
):
    return environmental_records_for_organization(
        organization,
        flow=flow,
        start=start,
        end=end,
        work=work,
        process=process,
        asset=asset,
        point=point,
    )


def save_point(instance, organization, data):
    for field, value in data.items():
        setattr(instance, field, value)
    instance.organizacion = organization
    instance.full_clean()
    instance.save()
    return instance


@transaction.atomic
def save_environmental_record(instance, organization, data, actor=None):
    observation_data = {
        key: data.pop(key, None)
        for key in (
            "concepto",
            "valor_numerico",
            "valor_texto",
            "unidad",
            "fuente",
            "evidencia",
            "version_evidencia",
            "metodo_captura",
            "naturaleza",
        )
    }
    for field, value in data.items():
        setattr(instance, field, value)
    instance.organizacion = organization
    instance.full_clean()
    instance.save()
    if (
        observation_data["valor_numerico"] is not None
        or observation_data["valor_texto"]
    ):
        observation_data["valor_texto"] = observation_data["valor_texto"] or ""
        observation_data["unidad"] = observation_data["unidad"] or ""
        observation_data["metodo_captura"] = (
            observation_data["metodo_captura"] or Observacion.MetodoCaptura.MANUAL
        )
        observation_data["naturaleza"] = (
            observation_data["naturaleza"] or Observacion.Naturaleza.DECLARATIVO
        )
        capture_observation(
            channel="manual",
            organization=organization,
            activity=instance.actividad,
            timestamp=instance.periodo_fin or instance.periodo_inicio,
            actor=actor,
            source=observation_data["fuente"],
            concept=observation_data["concepto"],
            numeric_value=observation_data["valor_numerico"],
            text_value=observation_data["valor_texto"],
            unit=observation_data["unidad"],
            evidence=observation_data["evidencia"],
            evidence_version=observation_data["version_evidencia"],
            method=observation_data["metodo_captura"],
            nature=observation_data["naturaleza"],
        )
    return instance


def _scope(record):
    return {
        "granularidad": record.granularidad,
        "unidad_operacional_id": record.unidad_operacional_id,
        "obra_id": record.obra_id,
        "proceso_id": record.proceso_id,
        "activo_id": record.activo_id,
        "punto_id": record.punto_id,
    }


def record_summary(record):
    observations = list(record.actividad.observaciones.all())
    return {
        "id": record.id,
        "flujo": record.flujo,
        "periodo_inicio": record.periodo_inicio,
        "periodo_fin": record.periodo_fin,
        "alcance": _scope(record),
        "tipo_recurso": record.tipo_recurso,
        "metrica": record.metrica,
        "destino_operacional": record.destino_operacional,
        "mediciones": [
            {
                "id": row.id,
                "concepto": row.concepto,
                "valor": (
                    row.valor_numerico
                    if row.valor_numerico is not None
                    else row.valor_texto
                ),
                "unidad": row.unidad,
                "fuente_id": row.fuente_id,
                "evidencia_id": row.evidencia_id,
                "version_evidencia_id": row.version_evidencia_id,
                "metodo_captura": row.metodo_captura,
                "naturaleza": row.naturaleza,
                "estado": row.estado,
            }
            for row in observations[:20]
        ],
    }


def sector_summary(organization, **filters):
    aggregates = defaultdict(
        lambda: {
            "total": None,
            "mediciones": 0,
            "registros_ambiguos": 0,
            "minimo": None,
            "maximo": None,
        }
    )
    records = []
    signals = []
    for record in _rows(organization, **filters):
        records.append(record_summary(record))
        per_activity = defaultdict(list)
        for observation in record.actividad.observaciones.all():
            if observation.valor_numerico is not None:
                per_activity[(observation.concepto, observation.unidad)].append(
                    observation.valor_numerico
                )
            elif observation.valor_texto:
                normalized = observation.valor_texto.strip().lower()
                if (
                    record.flujo == RegistroFlujoAmbiental.Flujo.GESTION_HIDRICA_SUELO
                    and observation.concepto
                    in {
                        "desborde",
                        "erosion_observada",
                        "acumulacion_agua",
                        "sedimentos",
                    }
                    and normalized not in {"no", "false", "sin", "0"}
                ):
                    signals.append(
                        {
                            "tipo": observation.concepto,
                            "registro_id": record.id,
                            "observacion_id": observation.id,
                        }
                    )
        for (concept, unit), values in per_activity.items():
            key = (
                record.flujo,
                concept,
                unit,
                record.granularidad,
                record.unidad_operacional_id,
                record.obra_id,
                record.proceso_id,
                record.activo_id,
                record.punto_id,
                record.metrica,
            )
            item = aggregates[key]
            item["mediciones"] += len(values)
            item["minimo"] = (
                min(values) if item["minimo"] is None else min(item["minimo"], *values)
            )
            item["maximo"] = (
                max(values) if item["maximo"] is None else max(item["maximo"], *values)
            )
            additive = (record.flujo, concept) in ADDITIVE_CONCEPTS
            if additive and item["total"] is None:
                item["total"] = Decimal("0")
            if additive and len(values) == 1:
                item["total"] += values[0]
            else:
                if len(values) > 1:
                    item["registros_ambiguos"] += 1
    indicators = []
    for key, values in aggregates.items():
        (
            flow,
            concept,
            unit,
            granularity,
            unit_id,
            work_id,
            process_id,
            asset_id,
            point_id,
            metric,
        ) = key
        indicators.append(
            {
                "flujo": flow,
                "concepto": concept,
                "unidad": unit,
                "metrica": metric,
                "estrategia_agregacion": (
                    "suma"
                    if (flow, concept) in ADDITIVE_CONCEPTS
                    else "serie_no_aditiva"
                ),
                "alcance": {
                    "granularidad": granularity,
                    "unidad_operacional_id": unit_id,
                    "obra_id": work_id,
                    "proceso_id": process_id,
                    "activo_id": asset_id,
                    "punto_id": point_id,
                },
                **values,
            }
        )
    return {
        "organizacion_id": organization.organizacion_id,
        "indicadores": indicators,
        "senales": signals,
        "registros": records[:20],
        "cumplimiento_normativo": None,
        "impacto_ambiental": None,
    }
