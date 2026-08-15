from decimal import Decimal, InvalidOperation

import pandas as pd
from django.utils import timezone

from ..models import (ActividadOperacional, EventoMaterial, LoteMaterial, MaterialOperacional,
                      Observacion, RegistroFlujoAmbiental, Vehiculo, ViajeOperacional)


CONTEXT_FIELDS = {"identificador_actividad", "fecha_actividad", "periodo_inicio", "periodo_fin", "material", "tipo_evento_material",
                  "lote_material", "punto_medicion", "obra", "proceso", "activo", "vehiculo", "unidad", "metrica",
                  "destino_operacional", "proveedor_gestor"}
NUMERIC_CONCEPTS = {"distancia_recorrida_km", "masa_transportada_t", "combustible_consumido_l", "consumo_energia",
                    "combustible_consumido",
                    "energia_generada", "energia_autoconsumida", "energia_exportada", "cantidad_material", "cantidad_residuo",
                    "nivel_ruido", "superficie_intervenida", "superficie_impermeabilizada", "precipitacion_observada"}


def _timestamp(value, fallback):
    parsed = pd.to_datetime(value or fallback, errors="coerce")
    if pd.isna(parsed): raise ValueError("fecha_invalida|fecha|La fecha no tiene un formato reconocido.")
    result = parsed.to_pydatetime()
    return timezone.make_aware(result) if timezone.is_naive(result) else result


def _value(value):
    if value in (None, ""): return None, ""
    try: return Decimal(str(value)), ""
    except (InvalidOperation, ValueError): return None, str(value)


def _activity(record, data, activity_type, name, timestamp):
    process = record.proceso_ingesta
    row_context = (record.datos_normalizados or {}).get("contexto_sugerido", {})
    context = {**row_context, **(process.contexto_confirmado or {})}
    reference = str(data.get("identificador_actividad") or f"fila-{record.numero_fila}")
    activity = ActividadOperacional(
        organizacion=process.organizacion, tipo=activity_type, codigo=f"ING-{process.id}-{record.numero_fila}"[:100],
        nombre=name, timestamp_inicio=timestamp, timestamp_fin=_timestamp(data["periodo_fin"], timestamp) if data.get("periodo_fin") else None,
        estado=ActividadOperacional.Estado.REGISTRADA, referencia_externa=reference,
        unidad_operacional_id=context.get("unidad_operacional_id"), proceso_operacional_id=context.get("proceso_operacional_id"),
        metadata={"proceso_ingesta_id": process.id, "registro_extraido_id": record.id},
    )
    activity.full_clean(); activity.save()
    if context.get("activo_id"): activity.activos.add(context["activo_id"])
    return activity


def _observations(record, activity, data, units, timestamp):
    process = record.proceso_ingesta
    created = {}
    for concept, raw_value in data.items():
        if concept in CONTEXT_FIELDS or raw_value in (None, ""): continue
        numeric, textual = _value(raw_value)
        if concept in NUMERIC_CONCEPTS and numeric is None:
            raise ValueError(f"valor_numerico_invalido|{concept}|El valor '{raw_value}' no es numérico.")
        observation = Observacion(
            organizacion=process.organizacion, actividad=activity, fuente=process.fuente_datos, concepto=concept,
            valor_numerico=numeric, valor_texto=textual, unidad=units.get(concept, ""), timestamp_observacion=timestamp,
            metodo_captura=Observacion.MetodoCaptura.IMPORTADO, naturaleza=Observacion.Naturaleza.DOCUMENTAL,
            evidencia=process.version_evidencia.evidencia, version_evidencia=process.version_evidencia,
            registro_extraido=record,
        )
        observation.full_clean(); observation.save(); created[concept] = observation
    return created


def generic_handler(record, data, units):
    timestamp = _timestamp(data.get("fecha_actividad") or data.get("periodo_inicio"), record.proceso_ingesta.created_at)
    activity = _activity(record, data, ActividadOperacional.Tipo.OTRO, "Actividad importada", timestamp)
    observations = _observations(record, activity, data, units, timestamp)
    return activity, None, observations


def transport_handler(record, data, units):
    if not data.get("identificador_actividad"): raise ValueError("campo_critico_faltante|identificador_actividad|Falta el identificador del viaje.")
    timestamp = _timestamp(data.get("fecha_actividad"), record.proceso_ingesta.created_at)
    activity = _activity(record, data, ActividadOperacional.Tipo.TRANSPORTE, f"Viaje {data['identificador_actividad']}", timestamp)
    observations = _observations(record, activity, data, units, timestamp)
    vehicle = None
    if data.get("vehiculo"):
        candidates = Vehiculo.objects.filter(activo__organizacion=record.proceso_ingesta.organizacion).filter(
            patente__iexact=str(data["vehiculo"])).select_related("activo")
        if candidates.count() == 1: vehicle = candidates.first()
        elif candidates.count() > 1: raise ValueError("contexto_ambiguo|vehiculo|Existen múltiples vehículos candidatos.")
    journey = None
    if vehicle:
        journey = ViajeOperacional.objects.create(
            organizacion=record.proceso_ingesta.organizacion, actividad=activity, codigo=activity.codigo, vehiculo=vehicle,
            origen_nombre=str(data.get("origen") or "No informado"), destino_nombre=str(data.get("destino_operacional") or "No informado"),
            fecha_salida=timestamp, observacion_distancia=observations.get("distancia_recorrida_km"),
            observacion_carga=observations.get("masa_transportada_t"), observacion_combustible=observations.get("combustible_consumido_l"),
            metadata_tecnica={"registro_extraido_id": record.id},
        )
    return activity, journey, observations


def material_handler(record, data, units):
    process = record.proceso_ingesta
    material_ref, event_type = str(data.get("material") or "").strip(), str(data.get("tipo_evento_material") or "").strip().lower()
    if not material_ref: raise ValueError("campo_critico_faltante|material|Debe identificar el material.")
    if event_type not in EventoMaterial.Tipo.values: raise ValueError("evento_material_ambiguo|tipo_evento_material|Debe declarar un tipo de evento material válido.")
    candidates = MaterialOperacional.objects.filter(organizacion=process.organizacion).filter(codigo__iexact=material_ref)
    if not candidates.exists(): candidates = MaterialOperacional.objects.filter(organizacion=process.organizacion, nombre__iexact=material_ref)
    if candidates.count() != 1: raise ValueError("contexto_ambiguo|material|El material no se resolvió de forma inequívoca.")
    material = candidates.first(); timestamp = _timestamp(data.get("fecha_actividad") or data.get("periodo_inicio"), process.created_at)
    activity = _activity(record, data, ActividadOperacional.Tipo.MOVIMIENTO_MATERIAL, f"{event_type.title()} {material.nombre}", timestamp)
    observations = _observations(record, activity, data, units, timestamp)
    lot = None
    if data.get("lote_material"):
        lot = LoteMaterial.objects.filter(organizacion=process.organizacion, material=material, codigo=str(data["lote_material"])).first()
        if not lot: raise ValueError("contexto_no_resuelto|lote_material|El lote indicado no existe para el material.")
    event = EventoMaterial.objects.create(
        organizacion=process.organizacion, material=material, lote=lot, actividad=activity, tipo=event_type,
        fecha_hora=timestamp, observacion_cantidad=observations.get("cantidad_material"), fuente=process.fuente_datos,
        evidencia=process.version_evidencia.evidencia, version_evidencia=process.version_evidencia,
        metadata={"registro_extraido_id": record.id},
    )
    return activity, event, observations


def sector_flow_handler(record, data, units):
    process = record.proceso_ingesta
    if process.flujo not in RegistroFlujoAmbiental.Flujo.values: raise ValueError("flujo_desconocido|flujo|Debe seleccionar un flujo ambiental válido.")
    activity_type = RegistroFlujoAmbiental.EXPECTED_ACTIVITY_TYPES[process.flujo]
    timestamp = _timestamp(data.get("periodo_inicio") or data.get("fecha_actividad"), process.created_at)
    activity = _activity(record, data, activity_type, f"Registro {process.flujo}", timestamp)
    observations = _observations(record, activity, data, units, timestamp)
    if not observations: raise ValueError("campo_critico_faltante|observaciones|El registro no contiene hechos ambientales observables.")
    context = {**((record.datos_normalizados or {}).get("contexto_sugerido", {})), **(process.contexto_confirmado or {})}
    granularity = context.get("granularidad")
    if not granularity:
        granularity = (RegistroFlujoAmbiental.Granularidad.PUNTO if context.get("punto_id") else
                       RegistroFlujoAmbiental.Granularidad.ACTIVO if context.get("activo_id") else
                       RegistroFlujoAmbiental.Granularidad.PROCESO if context.get("proceso_operacional_id") else
                       RegistroFlujoAmbiental.Granularidad.OBRA if context.get("obra_id") else
                       RegistroFlujoAmbiental.Granularidad.INSTALACION if context.get("unidad_operacional_id") else
                       RegistroFlujoAmbiental.Granularidad.ORGANIZACION)
    flow = RegistroFlujoAmbiental(
        organizacion=process.organizacion, actividad=activity, flujo=process.flujo, periodo_inicio=timestamp,
        periodo_fin=_timestamp(data["periodo_fin"], timestamp) if data.get("periodo_fin") else None,
        granularidad=granularity, punto_id=context.get("punto_id"), unidad_operacional_id=context.get("unidad_operacional_id"),
        proceso_id=context.get("proceso_operacional_id"), activo_id=context.get("activo_id"), obra_id=context.get("obra_id"),
        metrica=str(data.get("metrica") or ""), destino_operacional=str(data.get("destino_operacional") or "sin_clasificar"),
        proveedor_gestor=str(data.get("proveedor_gestor") or ""), metadata={"registro_extraido_id": record.id},
    )
    flow.full_clean(); flow.save()
    return activity, flow, observations


INGESTION_HANDLERS = {"transporte": transport_handler, "material": material_handler,
                      "flujo_ambiental": sector_flow_handler, "actividad_generica": generic_handler}
