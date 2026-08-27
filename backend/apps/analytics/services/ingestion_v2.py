import hashlib

import pandas as pd
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from ..models import (
    ActivoOperacional,
    EvidenciaObra,
    FuenteDatos,
    MapeoColumna,
    Obra,
    PlantillaMapeo,
    ProcesoIngesta,
    ProcesoOperacional,
    PuntoAmbientalOperacional,
    RegistroExtraido,
    VersionEvidencia,
)
from .ingestion_concepts import (
    CONCEPT_ALIASES,
    classify_document,
    normalize_column,
    normalize_unit,
    normalize_value,
)
from .ingestion_handlers import INGESTION_HANDLERS, resolve_transport_vehicle
from ..policies.ingestion import (
    ensure_ingestion_mutable,
    validate_ingestion_contract,
    validate_process_context,
    validate_structured_contract,
)
from ..selectors.ingestion import (
    active_template_for_process,
    column_mappings_for_template,
    extracted_records_for_process,
    extracted_records_for_update,
    next_template_version,
    process_has_processed_records,
    source_by_name,
    source_for_organization,
)
from ..selectors.provenance import evidence_for_organization, next_evidence_version

ALIASES = CONCEPT_ALIASES
normalizar_columna = normalize_column


def mark_ingestion_failed(process, error):
    process.estado = ProcesoIngesta.Estado.FALLIDO
    process.resumen_errores = str(error)
    process.save()


def _aliases_for(process):
    aliases = dict(CONCEPT_ALIASES)
    if process.destino_operacional == "transporte":
        aliases.update(
            {
                "combustible": ("combustible_consumido_l", "L"),
                "litros": ("combustible_consumido_l", "L"),
            }
        )
    elif (
        process.destino_operacional == "flujo_ambiental"
        and process.flujo == "combustible_estacionario"
    ):
        aliases.update(
            {
                "combustible": ("combustible_consumido", ""),
                "litros": ("combustible_consumido", "L"),
            }
        )
    return aliases


def _json_value(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return (
        value
        if isinstance(value, (str, int, float, bool)) or value is None
        else str(value)
    )


def _leer_archivo(version):
    version.archivo.open("rb")
    try:
        frame = (
            pd.read_csv(version.archivo)
            if version.nombre_original.lower().endswith(".csv")
            else pd.read_excel(version.archivo)
        )
    finally:
        version.archivo.close()
    frame = frame.fillna("").dropna(how="all")
    columns = [str(column).strip() for column in frame.columns]
    rows = []
    for index, row in frame.iterrows():
        raw = {
            columns[position]: _json_value(value)
            for position, value in enumerate(row.tolist())
        }
        if any(str(value).strip() for value in raw.values()):
            rows.append((int(index) + 2, raw))
    return columns, rows


def _document_evidence_type(destination):
    return (
        EvidenciaObra.TipoEvidencia.DOCUMENTO_TRANSPORTE
        if destination == ProcesoIngesta.DestinoOperacional.TRANSPORTE
        else EvidenciaObra.TipoEvidencia.OTRO
    )


SOURCE_TYPE_BY_INGESTION = {
    "tabular": FuenteDatos.Tipo.EXCEL_CSV,
    "documental": FuenteDatos.Tipo.DOCUMENTO,
    "manual_estructurado": FuenteDatos.Tipo.MANUAL,
    "api": FuenteDatos.Tipo.API,
    "telemetria": FuenteDatos.Tipo.TELEMETRIA,
    "sensor": FuenteDatos.Tipo.SENSOR,
}


def _source_for(
    organization, ingestion_type, source_id=None, source_name="Fuente de ingesta"
):
    source = source_for_organization(organization, source_id)
    if source_id and not source:
        raise ValueError("La fuente de datos no pertenece a la organizacion.")
    if source:
        return source
    resolved_name = source_name.strip() or "Fuente de ingesta"
    expected_type = SOURCE_TYPE_BY_INGESTION[ingestion_type]
    existing = source_by_name(organization, resolved_name)
    if existing and existing.tipo != expected_type:
        resolved_name = f"{resolved_name} ({ingestion_type})"
    source, _ = FuenteDatos.objects.get_or_create(
        organizacion=organization,
        nombre=resolved_name,
        defaults={"tipo": expected_type},
    )
    return source


@transaction.atomic
def crear_ingesta(
    organizacion,
    upload,
    *,
    fuente_id=None,
    fuente_nombre="Fuente de ingesta",
    evidencia_id=None,
    tipo_ingesta="tabular",
    destino_operacional="actividad_generica",
    flujo="",
    clasificacion_confirmada="",
    contexto_confirmado=None,
):
    validate_ingestion_contract(tipo_ingesta, destino_operacional)
    content = upload.read()
    checksum = hashlib.sha256(content).hexdigest()
    fuente = _source_for(organizacion, tipo_ingesta, fuente_id, fuente_nombre)
    evidencia = (
        evidence_for_organization(organizacion, evidencia_id) if evidencia_id else None
    )
    if evidencia_id and not evidencia:
        raise ValueError("La evidencia no pertenece a la organizacion.")
    suggested = classify_document(upload.name)
    if not evidencia:
        evidencia = EvidenciaObra.objects.create(
            organizacion=organizacion,
            nombre=upload.name,
            tipo_evidencia=_document_evidence_type(destino_operacional),
            archivo=ContentFile(content, name=upload.name),
            metadata_extraccion={"checksum_sha256": checksum, "ingesta_v2": True},
        )
    number = next_evidence_version(evidencia)
    version = VersionEvidencia(
        evidencia=evidencia,
        organizacion=organizacion,
        version=number,
        archivo=ContentFile(content, name=upload.name),
        nombre_original=upload.name,
        tipo_documental=clasificacion_confirmada or suggested,
        checksum_sha256=checksum,
        metadata_tecnica={
            "size_bytes": len(content),
            "clasificacion_sugerida": suggested,
        },
    )
    version.full_clean()
    version.save()
    process = ProcesoIngesta(
        organizacion=organizacion,
        version_evidencia=version,
        fuente_datos=fuente,
        tipo_ingesta=tipo_ingesta,
        destino_operacional=destino_operacional,
        flujo=flujo,
        clasificacion_sugerida=suggested,
        clasificacion_confirmada=clasificacion_confirmada,
        contexto_confirmado=contexto_confirmado or {},
    )
    validate_process_context(process, process.contexto_confirmado)
    process.full_clean()
    process.save()
    return process


@transaction.atomic
def crear_ingesta_estructurada(
    organizacion,
    payload,
    *,
    fuente_id=None,
    fuente_nombre="Fuente estructurada",
    tipo_ingesta="api",
    destino_operacional="actividad_generica",
    flujo="",
    contexto_confirmado=None,
):
    rows = validate_structured_contract(tipo_ingesta, destino_operacional, payload)
    source = _source_for(organizacion, tipo_ingesta, fuente_id, fuente_nombre)
    process = ProcesoIngesta(
        organizacion=organizacion,
        version_evidencia=None,
        fuente_datos=source,
        tipo_ingesta=tipo_ingesta,
        destino_operacional=destino_operacional,
        flujo=flujo,
        contexto_confirmado=contexto_confirmado or {},
        estado=ProcesoIngesta.Estado.RECIBIDO,
        filas_detectadas=len(rows),
    )
    validate_process_context(process, process.contexto_confirmado)
    process.full_clean()
    process.save()
    RegistroExtraido.objects.bulk_create(
        [
            RegistroExtraido(
                proceso_ingesta=process,
                numero_fila=index,
                origen=f"payload:{index}",
                datos_originales=row,
            )
            for index, row in enumerate(rows, start=1)
        ]
    )
    return process


def _context_conflicts(confirmed, suggested):
    labels = {
        "obra_id": "obra",
        "activo_id": "activo",
        "proceso_operacional_id": "proceso",
        "punto_id": "punto_medicion",
    }
    return [
        {
            "codigo": "contexto_contradictorio",
            "campo": labels.get(field, field),
            "detalle": f"El valor del archivo contradice el {labels.get(field, field)} seleccionado.",
        }
        for field, selected in (confirmed or {}).items()
        if field in labels
        and suggested.get(field)
        and str(suggested[field]) != str(selected)
    ]


@transaction.atomic
def analizar_ingesta(proceso):
    if process_has_processed_records(proceso):
        raise ValueError(
            "Una ingesta confirmada no puede analizarse nuevamente; cree un nuevo proceso."
        )
    proceso.estado = ProcesoIngesta.Estado.ANALIZANDO
    proceso.fecha_inicio = proceso.fecha_inicio or timezone.now()
    proceso.save(update_fields=["estado", "fecha_inicio", "updated_at"])
    if proceso.tipo_ingesta == ProcesoIngesta.TipoIngesta.DOCUMENTAL:
        proceso.estado = ProcesoIngesta.Estado.REQUIERE_MAPEO
        proceso.save(update_fields=["estado", "updated_at"])
        return {
            "columnas": [],
            "filas_detectadas": 0,
            "estado": proceso.estado,
            "problemas": [
                {
                    "codigo": "extraccion_no_disponible",
                    "campo": "archivo",
                    "detalle": "No existe extracción estructurada para este documento.",
                }
            ],
        }
    if proceso.tipo_ingesta == ProcesoIngesta.TipoIngesta.TABULAR:
        columns, rows = _leer_archivo(proceso.version_evidencia)
        proceso.registros_extraidos.all().delete()
        RegistroExtraido.objects.bulk_create(
            [
                RegistroExtraido(
                    proceso_ingesta=proceso,
                    numero_fila=number,
                    origen=f"fila:{number}",
                    datos_originales=data,
                )
                for number, data in rows
            ]
        )
    else:
        existing = list(extracted_records_for_process(proceso))
        rows = [(record.numero_fila, record.datos_originales) for record in existing]
        columns = list(dict.fromkeys(column for _, row in rows for column in row))
    latest = active_template_for_process(proceso)
    previous = (
        {
            item.columna_normalizada: (item.concepto_normalizado, item.unidad_esperada)
            for item in column_mappings_for_template(latest)
        }
        if latest
        else {}
    )
    mappings = []
    for column in columns:
        normalized = normalize_column(column)
        target = previous.get(normalized) or _aliases_for(proceso).get(normalized)
        mappings.append(
            {
                "columna_origen": column,
                "columna_normalizada": normalized,
                "concepto_normalizado": target[0] if target else "",
                "unidad_esperada": target[1] if target else "",
                "reconocida": bool(target),
                "origen_mapeo": (
                    "plantilla"
                    if normalized in previous
                    else ("alias" if target else "pendiente")
                ),
            }
        )
    proceso.filas_detectadas = len(rows)
    all_known = all(item["reconocida"] for item in mappings)
    proceso.plantilla_mapeo = latest if latest and all_known else None
    proceso.estado = (
        ProcesoIngesta.Estado.LISTO_CONFIRMAR
        if all_known
        else ProcesoIngesta.Estado.REQUIERE_MAPEO
    )
    if proceso.version_evidencia_id:
        proceso.version_evidencia.estado_procesamiento = (
            VersionEvidencia.EstadoProcesamiento.LISTA
        )
        proceso.version_evidencia.save(
            update_fields=["estado_procesamiento", "updated_at"]
        )
    proceso.save()
    return {
        "columnas": mappings,
        "filas_detectadas": len(rows),
        "estado": proceso.estado,
        "clasificacion_sugerida": proceso.clasificacion_sugerida,
        "destino_operacional": proceso.destino_operacional,
        "flujo": proceso.flujo,
    }


@transaction.atomic
def guardar_mapeo(
    proceso,
    mappings,
    nombre="Mapeo ambiental",
    *,
    destino_operacional=None,
    flujo=None,
    contexto=None,
):
    ensure_ingestion_mutable(proceso)
    if not mappings:
        raise ValueError("Debe informar al menos un mapeo.")
    destination = destino_operacional or proceso.destino_operacional
    selected_flow = flujo if flujo is not None else proceso.flujo
    if destination not in ProcesoIngesta.DestinoOperacional.values:
        raise ValueError("Destino operacional no soportado.")
    version = next_template_version(proceso, nombre)
    template = PlantillaMapeo(
        organizacion=proceso.organizacion,
        fuente_datos=proceso.fuente_datos,
        nombre=nombre,
        version=version,
        formato="excel_csv",
        tipo_ingesta=proceso.tipo_ingesta,
        destino_operacional=destination,
        flujo=selected_flow,
    )
    template.full_clean()
    template.save()
    for item in mappings:
        if item.get("concepto_normalizado"):
            MapeoColumna.objects.create(
                plantilla=template,
                columna_origen=item["columna_origen"],
                columna_normalizada=normalize_column(item["columna_origen"]),
                concepto_normalizado=normalize_column(item["concepto_normalizado"]),
                unidad_esperada=normalize_unit(item.get("unidad_esperada", "")),
            )
    proceso.plantilla_mapeo = template
    proceso.destino_operacional = destination
    proceso.flujo = selected_flow
    if contexto is not None:
        validate_process_context(proceso, contexto)
        proceso.contexto_confirmado = contexto
    proceso.full_clean()
    proceso.estado = ProcesoIngesta.Estado.LISTO_CONFIRMAR
    proceso.save()
    return template


def _mapping_for(process):
    if process.plantilla_mapeo_id:
        return {
            item.columna_normalizada: (item.concepto_normalizado, item.unidad_esperada)
            for item in column_mappings_for_template(process.plantilla_mapeo)
        }
    return _aliases_for(process)


def _normalize_row(raw, mapping):
    data, units = {}, {}
    for column, value in raw.items():
        target = mapping.get(normalize_column(column))
        if target:
            concept, unit = target
            data[concept] = normalize_value(value, concept)
            units[concept] = normalize_unit(unit)
    row_unit = normalize_unit(data.get("unidad"))
    if row_unit:
        for concept in data:
            if concept not in {"unidad"} and not units.get(concept):
                units[concept] = row_unit
    return data, units


def _context_suggestions(process, data):
    specs = {
        "obra": (Obra, "obra_id", ("codigo_obra", "nombre")),
        "proceso": (ProcesoOperacional, "proceso_operacional_id", ("nombre",)),
        "activo": (ActivoOperacional, "activo_id", ("codigo", "nombre")),
        "punto_medicion": (PuntoAmbientalOperacional, "punto_id", ("codigo", "nombre")),
    }
    result, errors = {}, []
    for concept, (model, output, fields) in specs.items():
        value = str(data.get(concept) or "").strip()
        if not value:
            continue
        query = model.objects.filter(organizacion=process.organizacion)
        matches = None
        for field in fields:
            current = query.filter(**{f"{field}__iexact": value})
            matches = current if matches is None else matches | current
        matches = matches.distinct()
        if matches.count() == 1:
            result[output] = matches.first().id
        elif matches.count() > 1:
            errors.append(
                {
                    "codigo": "contexto_ambiguo",
                    "campo": concept,
                    "detalle": f"Existen múltiples coincidencias para '{value}'.",
                }
            )
        else:
            errors.append(
                {
                    "codigo": "contexto_no_resuelto",
                    "campo": concept,
                    "detalle": f"No existe una coincidencia para '{value}'.",
                }
            )
    return result, errors


def _capture_errors(process, data):
    errors = []
    if process.destino_operacional == "transporte" and not data.get(
        "identificador_actividad"
    ):
        errors.append(
            {
                "codigo": "campo_critico_faltante",
                "campo": "identificador_actividad",
                "detalle": "Falta el identificador del viaje.",
            }
        )
    if process.destino_operacional == "transporte":
        vehicle, code, detail = resolve_transport_vehicle(process, data)
        if not vehicle:
            errors.append({"codigo": code, "campo": "vehiculo", "detalle": detail})
    if process.destino_operacional == "material":
        if not data.get("material"):
            errors.append(
                {
                    "codigo": "campo_critico_faltante",
                    "campo": "material",
                    "detalle": "Falta el material.",
                }
            )
        if not data.get("tipo_evento_material"):
            errors.append(
                {
                    "codigo": "evento_material_ambiguo",
                    "campo": "tipo_evento_material",
                    "detalle": "El tipo de evento debe declararse explícitamente.",
                }
            )
    if process.destino_operacional == "flujo_ambiental" and not process.flujo:
        errors.append(
            {
                "codigo": "flujo_desconocido",
                "campo": "flujo",
                "detalle": "Debe seleccionar el flujo ambiental.",
            }
        )
    return errors


def preview_ingesta(proceso):
    mapping = _mapping_for(proceso)
    rows = []
    for record in extracted_records_for_process(proceso):
        normalized, units = _normalize_row(record.datos_originales, mapping)
        suggestions, context_errors = _context_suggestions(proceso, normalized)
        errors = (
            _capture_errors(proceso, normalized)
            + context_errors
            + _context_conflicts(proceso.contexto_confirmado, suggestions)
        )
        record.datos_normalizados = {
            "valores": normalized,
            "unidades": units,
            "contexto_sugerido": suggestions,
        }
        record.errores = errors
        record.auto_confirmable = not errors
        record.estado = (
            RegistroExtraido.Estado.LISTO
            if not errors
            else RegistroExtraido.Estado.REQUIERE_REVISION
        )
        record.save(
            update_fields=[
                "datos_normalizados",
                "errores",
                "auto_confirmable",
                "estado",
                "updated_at",
            ]
        )
        rows.append(
            {
                "id": record.id,
                "numero_fila": record.numero_fila,
                "datos_originales": record.datos_originales,
                "datos_normalizados": record.datos_normalizados,
                "destino": proceso.destino_operacional,
                "flujo": proceso.flujo,
                "actividad": {
                    "tipo": proceso.flujo or proceso.destino_operacional,
                    "observaciones": [
                        key
                        for key, value in normalized.items()
                        if value not in (None, "")
                    ],
                },
                "contexto": {**suggestions, **proceso.contexto_confirmado},
                "estado": "lista" if not errors else "requiere_revision",
                "auto_confirmable": not errors,
                "problemas": errors,
                "errores": errors,
            }
        )
    proceso.contexto_sugerido = (
        rows[0]["datos_normalizados"].get("contexto_sugerido", {})
        if len(rows) == 1
        else {}
    )
    proceso.save(update_fields=["contexto_sugerido", "updated_at"])
    return {
        "ingesta_id": proceso.id,
        "archivo": (
            proceso.version_evidencia.nombre_original
            if proceso.version_evidencia_id
            else None
        ),
        "estado": proceso.estado,
        "destino": proceso.destino_operacional,
        "flujo": proceso.flujo,
        "filas_detectadas": proceso.filas_detectadas,
        "filas_validas": sum(not row["problemas"] for row in rows),
        "filas_problematicas": sum(bool(row["problemas"]) for row in rows),
        "filas_error": 0,
        "filas": rows,
    }


def _structured_error(exc):
    parts = str(exc).split("|", 2)
    return {
        "codigo": parts[0] if parts else "error_procesamiento",
        "campo": parts[1] if len(parts) > 1 else "registro",
        "detalle": parts[2] if len(parts) > 2 else str(exc),
    }


@transaction.atomic
def confirmar_ingesta(proceso):
    if proceso.estado in {
        ProcesoIngesta.Estado.COMPLETADO,
        ProcesoIngesta.Estado.COMPLETADO_OBSERVACIONES,
    }:
        return {
            "actividades_creadas": proceso.filas_procesadas,
            "filas_con_error": proceso.filas_con_error,
            "idempotente": True,
        }
    if not proceso.plantilla_mapeo_id:
        raise ValueError("Debe confirmar el mapeo antes de procesar.")
    handler = INGESTION_HANDLERS.get(proceso.destino_operacional)
    if not handler:
        raise ValueError("No existe un handler registrado para el destino.")
    proceso.estado = ProcesoIngesta.Estado.PROCESANDO
    proceso.save(update_fields=["estado", "updated_at"])
    mapping = _mapping_for(proceso)
    processed = errors = observations = 0
    for record in extracted_records_for_update(proceso):
        if (
            record.estado == RegistroExtraido.Estado.PROCESADO
            and record.actividad_creada_id
        ):
            processed += 1
            continue
        try:
            with transaction.atomic():
                data, units = _normalize_row(record.datos_originales, mapping)
                capture_errors = _capture_errors(proceso, data)
                if capture_errors:
                    raise ValueError(
                        f"{capture_errors[0]['codigo']}|{capture_errors[0]['campo']}|{capture_errors[0]['detalle']}"
                    )
                suggestions, context_errors = _context_suggestions(proceso, data)
                confirmed = proceso.contexto_confirmado or {}
                context_key = {
                    "obra": "obra_id",
                    "proceso": "proceso_operacional_id",
                    "activo": "activo_id",
                    "punto_medicion": "punto_id",
                }
                unresolved = _context_conflicts(confirmed, suggestions) + [
                    error
                    for error in context_errors
                    if not confirmed.get(context_key.get(error["campo"], ""))
                ]
                if unresolved:
                    raise ValueError(
                        f"{unresolved[0]['codigo']}|{unresolved[0]['campo']}|{unresolved[0]['detalle']}"
                    )
                record.datos_normalizados = {
                    "valores": data,
                    "unidades": units,
                    "contexto_sugerido": suggestions,
                }
                activity, specialization, created_observations = handler(
                    record, data, units
                )
                record.actividad_creada = activity
                record.estado = RegistroExtraido.Estado.PROCESADO
                record.errores = []
                record.resultado_procesamiento = {
                    "actividad_id": activity.id,
                    "especializacion": (
                        specialization.__class__.__name__ if specialization else ""
                    ),
                    "especializacion_id": getattr(specialization, "id", None),
                    "observacion_ids": [
                        row.id for row in created_observations.values()
                    ],
                }
                record.procesado_at = timezone.now()
                record.save()
                processed += 1
                observations += len(created_observations)
        except Exception as exc:
            record.estado = RegistroExtraido.Estado.ERROR
            record.errores = [_structured_error(exc)]
            record.save(update_fields=["estado", "errores", "updated_at"])
            errors += 1
    proceso.filas_procesadas = processed
    proceso.filas_con_error = errors
    proceso.fecha_fin = timezone.now()
    proceso.estado = (
        ProcesoIngesta.Estado.COMPLETADO_OBSERVACIONES
        if errors
        else ProcesoIngesta.Estado.COMPLETADO
    )
    proceso.resumen_errores = f"{errors} filas con error" if errors else ""
    if proceso.version_evidencia_id:
        proceso.version_evidencia.estado_procesamiento = (
            VersionEvidencia.EstadoProcesamiento.PROCESADA
        )
        proceso.version_evidencia.save(
            update_fields=["estado_procesamiento", "updated_at"]
        )
    proceso.save()
    return {
        "actividades_creadas": processed,
        "observaciones_creadas": observations,
        "filas_con_error": errors,
        "idempotente": False,
    }
