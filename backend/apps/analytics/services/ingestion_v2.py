import hashlib
import re
import unicodedata
from decimal import Decimal, InvalidOperation

import pandas as pd
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from ..models import (ActividadOperacional, EvidenciaObra, FuenteDatos, MapeoColumna, Observacion,
                      PlantillaMapeo, ProcesoIngesta, RegistroExtraido, VersionEvidencia)


ALIASES = {
    "viaje_id": ("identificador_actividad", ""), "id_viaje": ("identificador_actividad", ""),
    "viaje": ("identificador_actividad", ""), "fecha": ("fecha_actividad", ""),
    "km": ("distancia_recorrida_km", "km"), "km_dia": ("distancia_recorrida_km", "km"),
    "km_recorridos": ("distancia_recorrida_km", "km"), "kilometraje": ("distancia_recorrida_km", "km"),
    "toneladas": ("masa_transportada_t", "t"), "tonelaje": ("masa_transportada_t", "t"),
    "carga_ton": ("masa_transportada_t", "t"), "combustible": ("combustible_consumido_l", "L"),
    "litros_combustible": ("combustible_consumido_l", "L"), "litros": ("combustible_consumido_l", "L"),
}
ACTIVITY_FIELDS = {"identificador_actividad", "fecha_actividad"}


def normalizar_columna(value):
    value = unicodedata.normalize("NFD", str(value or "").strip().lower())
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value)).strip("_")


def _leer_archivo(version):
    version.archivo.open("rb")
    try:
        if version.nombre_original.lower().endswith(".csv"):
            frame = pd.read_csv(version.archivo)
        else:
            frame = pd.read_excel(version.archivo)
    finally:
        version.archivo.close()
    frame = frame.fillna("").dropna(how="all")
    columns = [str(column).strip() for column in frame.columns]
    rows = []
    for index, row in frame.iterrows():
        raw = {columns[position]: _json_value(value) for position, value in enumerate(row.tolist())}
        if any(str(value).strip() for value in raw.values()):
            rows.append((int(index) + 2, raw))
    return columns, rows


def _json_value(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value if isinstance(value, (str, int, float, bool)) or value is None else str(value)


@transaction.atomic
def crear_ingesta(organizacion, upload, *, fuente_id=None, fuente_nombre="Planilla logistica mensual", evidencia_id=None):
    content = upload.read()
    checksum = hashlib.sha256(content).hexdigest()
    fuente = None
    if fuente_id:
        fuente = FuenteDatos.objects.filter(organizacion=organizacion, id=fuente_id).first()
        if not fuente:
            raise ValueError("La fuente de datos no pertenece a la organizacion.")
    if not fuente:
        fuente, _ = FuenteDatos.objects.get_or_create(
            organizacion=organizacion, nombre=fuente_nombre.strip() or "Planilla logistica mensual",
            defaults={"tipo": FuenteDatos.Tipo.EXCEL_CSV},
        )
    evidencia = EvidenciaObra.objects.filter(organizacion=organizacion, id=evidencia_id).first() if evidencia_id else None
    if evidencia_id and not evidencia:
        raise ValueError("La evidencia no pertenece a la organizacion.")
    if not evidencia:
        evidencia = EvidenciaObra.objects.create(
            organizacion=organizacion, nombre=upload.name, tipo_evidencia=EvidenciaObra.TipoEvidencia.DOCUMENTO_TRANSPORTE,
            archivo=ContentFile(content, name=upload.name), metadata_extraccion={"checksum_sha256": checksum, "ingesta_v2": True},
        )
    version_number = (evidencia.versiones.order_by("-version").values_list("version", flat=True).first() or 0) + 1
    version = VersionEvidencia.objects.create(
        evidencia=evidencia, organizacion=organizacion, version=version_number, archivo=ContentFile(content, name=upload.name),
        nombre_original=upload.name, tipo_documental="transporte_excel_csv", checksum_sha256=checksum,
        metadata_tecnica={"size_bytes": len(content)},
    )
    proceso = ProcesoIngesta(organizacion=organizacion, version_evidencia=version, fuente_datos=fuente)
    proceso.full_clean(); proceso.save()
    return proceso


@transaction.atomic
def analizar_ingesta(proceso):
    proceso.estado = ProcesoIngesta.Estado.ANALIZANDO
    proceso.fecha_inicio = proceso.fecha_inicio or timezone.now()
    proceso.save(update_fields=["estado", "fecha_inicio", "updated_at"])
    columns, rows = _leer_archivo(proceso.version_evidencia)
    proceso.registros_extraidos.all().delete()
    RegistroExtraido.objects.bulk_create([
        RegistroExtraido(proceso_ingesta=proceso, numero_fila=number, origen=f"fila:{number}", datos_originales=data)
        for number, data in rows
    ])
    latest = PlantillaMapeo.objects.filter(organizacion=proceso.organizacion, fuente_datos=proceso.fuente_datos, activa=True).first()
    previous = {item.columna_normalizada: (item.concepto_normalizado, item.unidad_esperada) for item in latest.mapeos.all()} if latest else {}
    mappings = []
    for column in columns:
        normalized = normalizar_columna(column)
        target = previous.get(normalized) or ALIASES.get(normalized)
        mappings.append({"columna_origen": column, "columna_normalizada": normalized,
                         "concepto_normalizado": target[0] if target else "", "unidad_esperada": target[1] if target else "",
                         "reconocida": bool(target), "origen_mapeo": "plantilla" if normalized in previous else ("alias" if target else "pendiente")})
    proceso.filas_detectadas = len(rows)
    proceso.plantilla_mapeo = latest if latest and all(item["reconocida"] for item in mappings) else None
    proceso.estado = ProcesoIngesta.Estado.LISTO_CONFIRMAR if all(item["reconocida"] for item in mappings) else ProcesoIngesta.Estado.REQUIERE_MAPEO
    proceso.version_evidencia.estado_procesamiento = VersionEvidencia.EstadoProcesamiento.LISTA
    proceso.version_evidencia.save(update_fields=["estado_procesamiento", "updated_at"])
    proceso.save()
    return {"columnas": mappings, "filas_detectadas": len(rows), "estado": proceso.estado}


@transaction.atomic
def guardar_mapeo(proceso, mappings, nombre="Transporte"):
    if not mappings:
        raise ValueError("Debe informar al menos un mapeo.")
    version = (PlantillaMapeo.objects.filter(organizacion=proceso.organizacion, fuente_datos=proceso.fuente_datos, nombre=nombre)
               .order_by("-version").values_list("version", flat=True).first() or 0) + 1
    plantilla = PlantillaMapeo.objects.create(organizacion=proceso.organizacion, fuente_datos=proceso.fuente_datos, nombre=nombre, version=version)
    for item in mappings:
        if item.get("concepto_normalizado"):
            MapeoColumna.objects.create(
                plantilla=plantilla, columna_origen=item["columna_origen"],
                columna_normalizada=normalizar_columna(item["columna_origen"]),
                concepto_normalizado=item["concepto_normalizado"], unidad_esperada=item.get("unidad_esperada", ""),
            )
    proceso.plantilla_mapeo = plantilla
    proceso.estado = ProcesoIngesta.Estado.LISTO_CONFIRMAR
    proceso.save(update_fields=["plantilla_mapeo", "estado", "updated_at"])
    return plantilla


def preview_ingesta(proceso):
    mapping = _mapping_for(proceso)
    rows = []
    for record in proceso.registros_extraidos.all():
        normalized = _normalizar_fila(record.datos_originales, mapping)
        errors = [] if normalized.get("identificador_actividad") else ["No se pudo identificar la actividad (viaje_id)."]
        rows.append({"numero_fila": record.numero_fila, "datos_originales": record.datos_originales,
                     "datos_normalizados": normalized, "errores": errors,
                     "actividad": {"tipo": "transporte", "codigo": normalized.get("identificador_actividad", ""),
                                   "observaciones": len([key for key, value in normalized.items() if key not in ACTIVITY_FIELDS and value not in (None, "")])} if not errors else None})
    return {"ingesta_id": proceso.id, "estado": proceso.estado, "filas_detectadas": proceso.filas_detectadas,
            "filas_validas": sum(not row["errores"] for row in rows), "filas_problematicas": sum(bool(row["errores"]) for row in rows), "filas": rows}


def _mapping_for(proceso):
    if proceso.plantilla_mapeo_id:
        return {item.columna_normalizada: (item.concepto_normalizado, item.unidad_esperada) for item in proceso.plantilla_mapeo.mapeos.all()}
    return {normalizar_columna(column): target for column, target in ALIASES.items()}


def _normalizar_fila(raw, mapping):
    result = {}
    for column, value in raw.items():
        target = mapping.get(normalizar_columna(column))
        if target:
            result[target[0]] = value
    return result


def _decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Valor numerico invalido: {value}")


@transaction.atomic
def confirmar_ingesta(proceso):
    if proceso.estado in {ProcesoIngesta.Estado.COMPLETADO, ProcesoIngesta.Estado.COMPLETADO_OBSERVACIONES}:
        return {"actividades_creadas": proceso.filas_procesadas, "filas_con_error": proceso.filas_con_error, "idempotente": True}
    if not proceso.plantilla_mapeo_id:
        raise ValueError("Debe confirmar el mapeo antes de procesar.")
    proceso.estado = ProcesoIngesta.Estado.PROCESANDO; proceso.save(update_fields=["estado", "updated_at"])
    mapping = _mapping_for(proceso)
    processed = errors = observations = 0
    for record in proceso.registros_extraidos.select_for_update():
        if record.estado == RegistroExtraido.Estado.PROCESADO and record.actividad_creada_id:
            processed += 1
            continue
        try:
            with transaction.atomic():
                data = _normalizar_fila(record.datos_originales, mapping)
                reference = str(data.get("identificador_actividad") or "").strip()
                if not reference:
                    raise ValueError("Falta viaje_id; no se invento una actividad.")
                timestamp = pd.to_datetime(data.get("fecha_actividad") or proceso.created_at, errors="coerce")
                if pd.isna(timestamp):
                    raise ValueError("Fecha invalida.")
                timestamp = timestamp.to_pydatetime()
                if timezone.is_naive(timestamp):
                    timestamp = timezone.make_aware(timestamp)
                values = [(concept, value, unit) for concept, unit in mapping.values()
                          if concept not in ACTIVITY_FIELDS and (value := data.get(concept)) not in (None, "")]
                actividad = ActividadOperacional.objects.create(
                    organizacion=proceso.organizacion, tipo=ActividadOperacional.Tipo.TRANSPORTE,
                    codigo=f"ING-{proceso.id}-{reference}"[:100], nombre=f"Viaje {reference}", timestamp_inicio=timestamp,
                    estado=ActividadOperacional.Estado.REGISTRADA if values else ActividadOperacional.Estado.INCOMPLETA,
                    referencia_externa=reference, metadata={"proceso_ingesta_id": proceso.id, "numero_fila": record.numero_fila},
                )
                for concept, value, unit in values:
                    Observacion.objects.create(
                        organizacion=proceso.organizacion, actividad=actividad, fuente=proceso.fuente_datos,
                        concepto=concept, valor_numerico=_decimal(value), unidad=unit,
                        timestamp_observacion=timestamp, metodo_captura=Observacion.MetodoCaptura.IMPORTADO,
                        naturaleza=Observacion.Naturaleza.DOCUMENTAL, evidencia=proceso.version_evidencia.evidencia,
                        version_evidencia=proceso.version_evidencia,
                    )
                    observations += 1
                record.actividad_creada = actividad; record.estado = RegistroExtraido.Estado.PROCESADO; record.errores = []; record.save()
                processed += 1
        except Exception as exc:
            record.estado = RegistroExtraido.Estado.ERROR; record.errores = [str(exc)]; record.save(update_fields=["estado", "errores", "updated_at"])
            errors += 1
    proceso.filas_procesadas = processed; proceso.filas_con_error = errors; proceso.fecha_fin = timezone.now()
    proceso.estado = ProcesoIngesta.Estado.COMPLETADO_OBSERVACIONES if errors else ProcesoIngesta.Estado.COMPLETADO
    proceso.resumen_errores = f"{errors} filas con error" if errors else ""
    proceso.version_evidencia.estado_procesamiento = VersionEvidencia.EstadoProcesamiento.PROCESADA
    proceso.version_evidencia.save(update_fields=["estado_procesamiento", "updated_at"]); proceso.save()
    return {"actividades_creadas": processed, "observaciones_creadas": observations, "filas_con_error": errors, "idempotente": False}
