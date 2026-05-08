"""Importador de empresa completa desde XLSX con múltiples hojas."""

import uuid
from decimal import Decimal
from pathlib import Path

from django.core.cache import cache
from django.db import transaction
from openpyxl import load_workbook

from ..factores import normalize_activity_key
from ..models import Empresa, UnidadOperativa, Lote, EmisionLote, FactorEmision, normalize_identifier
from .importadores import (
    _build_company_payload,
    _build_unit_payload,
    _build_lote_payload,
    _build_activity_payload,
    _build_row_payload,
    _normalize_header_key,
    FACTOR_IMPORT_CACHE_TTL_SECONDS,
    _normalize_text,
)

COMPLETE_IMPORT_CACHE_PREFIX = "empresa_completa_import_batch:"


def _read_xlsx_sheet(uploaded_file, sheet_name: str) -> list[dict]:
    """Lee una hoja específica de un archivo XLSX."""
    try:
        wb = load_workbook(uploaded_file)
        ws = wb[sheet_name]
        rows = []
        headers = None
        row_number = 0

        for idx, row in enumerate(ws.iter_rows(values_only=True), 1):
            if idx == 1:
                headers = [h for h in row if h]
                continue
            if not headers or not any(row):
                continue

            row_number += 1
            data = {"row_number": row_number}
            for header, cell in zip(headers, row):
                if header:
                    data[_normalize_text(header, lower=True)] = cell

            rows.append(data)

        return rows
    except KeyError:
        return []
    except Exception:
        raise ValueError(f"No se pudo leer la hoja {sheet_name}. Revisa el formato del archivo.")


def _read_normalized_xlsx_sheet(uploaded_file, sheet_name: str) -> list[dict]:
    try:
        uploaded_file.seek(0)
        wb = load_workbook(uploaded_file, data_only=True, read_only=True)
        try:
            ws = wb[sheet_name]
            rows = []
            headers = None
            for idx, row in enumerate(ws.iter_rows(values_only=True), 1):
                if idx == 1:
                    headers = [_normalize_header_key(h) if h is not None else "" for h in row]
                    continue
                if not headers or not any(row):
                    continue

                values = list(row or [])
                data = {"row_number": idx}
                for index, header in enumerate(headers):
                    if header:
                        data[header] = values[index] if index < len(values) else None
                rows.append(data)
            return rows
        finally:
            wb.close()
    except KeyError:
        return []
    except Exception:
        raise ValueError(f"No se pudo leer la hoja {sheet_name}. Revisa el formato del archivo.")


def _strip_runtime_objects(data: dict) -> dict:
    return {key: value for key, value in (data or {}).items() if not key.endswith("_obj")}


def _remove_error(errors: list[str], message: str) -> None:
    while message in errors:
        errors.remove(message)


def _factor_lookup_key(actividad: str, unidad: str) -> tuple[str, str]:
    return (normalize_activity_key(actividad), _normalize_text(unidad, lower=True))


def _build_factor_lookup(rows: list[dict]) -> dict[tuple[str, str], dict]:
    lookup = {}
    for row in rows:
        data = row.get("data") or {}
        if row.get("status") != "valid":
            continue
        key = _factor_lookup_key(data.get("actividad"), data.get("unidad"))
        if all(key):
            lookup[key] = data
    return lookup


def _apply_file_factor(data: dict, errors: list[str], factor_lookup: dict[tuple[str, str], dict]) -> None:
    if data.get("factor_emision"):
        return

    factor = factor_lookup.get(_factor_lookup_key(data.get("actividad"), data.get("unidad")))
    if not factor:
        return

    data["factor_emision"] = Decimal(str(factor.get("factor_emision")))
    data["categoria"] = factor.get("categoria", "")
    data["fuente"] = factor.get("fuente", "")
    data["anio"] = factor.get("anio", "")
    _remove_error(errors, "factor de emision no encontrado")


class ImportadorEmpresaCompleta:
    @staticmethod
    def previsualizar(uploaded_file) -> dict:
        """Preview de importación de empresa completa desde XLSX."""
        name = Path(uploaded_file.name or "").suffix.lower()
        if name != ".xlsx":
            raise ValueError("Solo se permiten archivos XLSX")

        batch_id = uuid.uuid4().hex
        blocking_errors = []
        
        # Leer hojas
        empresa_rows = _read_normalized_xlsx_sheet(uploaded_file, "empresa")
        unidades_rows = _read_normalized_xlsx_sheet(uploaded_file, "unidades")
        lotes_rows = _read_normalized_xlsx_sheet(uploaded_file, "lotes")
        actividades_rows = _read_normalized_xlsx_sheet(uploaded_file, "actividades")
        factores_rows = _read_normalized_xlsx_sheet(uploaded_file, "factores")

        # Procesar empresa
        empresa_data = None
        empresa_errors = []
        empresa_activa = None
        if empresa_rows:
            row = empresa_rows[0]
            empresa_data, empresa_errors = _build_company_payload(row)
            if empresa_errors:
                blocking_errors.extend([f"Empresa: {e}" for e in empresa_errors])
            
            # Crear objeto empresa en memoria para usar como referencia en validaciones
            # Si la empresa no existe aún, generamos el empresa_id a partir del nombre
            if empresa_data and empresa_data.get("nombre"):
                generated_empresa_id = empresa_data.get("empresa_id") or normalize_identifier(empresa_data.get("nombre")) or "EMPRESA_GENERAL"
                # Crear objeto en memoria (sin guardar)
                empresa_activa = Empresa(
                    empresa_id=generated_empresa_id,
                    nombre=empresa_data.get("nombre"),
                    rut=empresa_data.get("rut", ""),
                    region=empresa_data.get("region", ""),
                    comuna=empresa_data.get("comuna", ""),
                    direccion=empresa_data.get("direccion", ""),
                    rubro=empresa_data.get("rubro", ""),
                    email=empresa_data.get("email", ""),
                    telefono=empresa_data.get("telefono", ""),
                    contacto=empresa_data.get("contacto", ""),
                    observaciones=empresa_data.get("observaciones", ""),
                )
                # Actualizar empresa_data con el empresa_id generado
                empresa_data["empresa_id"] = generated_empresa_id
        else:
            blocking_errors.append("La hoja empresa no contiene filas validas para importar")

        if not empresa_data or not empresa_data.get("empresa_id"):
            blocking_errors.append("No se encontro una empresa valida en la hoja empresa")

        # Procesar unidades
        unidades_preview = {
            "total": len(unidades_rows),
            "validas": 0,
            "errores": 0,
            "rows": []
        }
        unidades_by_id = {}
        for row in unidades_rows:
            data, errors, warnings = _build_unit_payload(row, empresa_activa=empresa_activa)
            unidad_id = data.get("unidad_id")
            status = "valid" if not errors else "error"
            if status == "valid":
                unidades_preview["validas"] += 1
                unidades_by_id[unidad_id] = _strip_runtime_objects(data)
            else:
                unidades_preview["errores"] += 1
            
            unidades_preview["rows"].append({
                "row_number": row.get("row_number"),
                "status": status,
                "errors": errors,
                "warnings": warnings,
                "data": _strip_runtime_objects(data)
            })

        # Procesar factores antes de actividades para que las actividades del mismo XLSX
        # puedan usar factores que aun no existen en la base de datos.
        factores_preview = {
            "total": len(factores_rows),
            "validos": 0,
            "errores": 0,
            "rows": []
        }
        for row in factores_rows:
            data, errors = _build_row_payload(row)
            status = "valid" if not errors else "error"
            if status == "valid":
                factores_preview["validos"] += 1
            else:
                factores_preview["errores"] += 1

            factores_preview["rows"].append({
                "row_number": row.get("row_number"),
                "status": status,
                "errors": errors,
                "data": {**data, "factor_emision": str(data.get("factor_emision", ""))}
            })
        factor_lookup = _build_factor_lookup(factores_preview["rows"])

        # Procesar lotes
        lotes_preview = {
            "total": len(lotes_rows),
            "validos": 0,
            "errores": 0,
            "rows": []
        }
        lotes_by_id = {}
        for row in lotes_rows:
            data, errors, warnings = _build_lote_payload(row)
            id_lote = data.get("id_lote")
            empresa_id = data.get("empresa_id")

            if empresa_activa is not None and (not empresa_id or empresa_id == empresa_activa.empresa_id):
                _remove_error(errors, "empresa_id no existe")
                _remove_error(errors, "empresa es obligatoria")
                data["empresa_id"] = empresa_activa.empresa_id
                data["empresa_aserradero"] = data.get("empresa_aserradero") or empresa_activa.nombre
            
            # Validar que unidad existe
            unidad_id = data.get("unidad_id")
            if unidad_id in unidades_by_id:
                _remove_error(errors, "unidad_id no existe")
            elif unidad_id and not UnidadOperativa.objects.filter(unidad_id=unidad_id).exists():
                errors.append(f"unidad_id {unidad_id} no existe en el archivo ni en la base de datos")
            
            status = "valid" if not errors else "error"
            if status == "valid":
                lotes_preview["validos"] += 1
                lotes_by_id[id_lote] = _strip_runtime_objects(data)
            else:
                lotes_preview["errores"] += 1
            
            lotes_preview["rows"].append({
                "row_number": row.get("row_number"),
                "status": status,
                "errors": errors,
                "warnings": warnings,
                "data": _strip_runtime_objects(data)
            })

        # Procesar actividades
        actividades_preview = {
            "total": len(actividades_rows),
            "validas": 0,
            "errores": 0,
            "factores_encontrados": 0,
            "factores_faltantes": 0,
            "rows": []
        }
        for row in actividades_rows:
            data, errors, warnings = _build_activity_payload(row)
            
            # Validar que lote existe si está referenciado
            id_lote = data.get("id_lote")
            unidad_id = data.get("unidad_id")
            empresa_id = data.get("empresa_id")

            if id_lote in lotes_by_id:
                lote_data = lotes_by_id[id_lote]
                _remove_error(errors, "id_lote no existe")
                data["empresa_id"] = lote_data.get("empresa_id") or data.get("empresa_id")
                data["unidad_id"] = lote_data.get("unidad_id") or data.get("unidad_id")
                data["tipo_asignacion"] = EmisionLote.TipoAsignacion.LOTE
            elif id_lote and not Lote.objects.filter(id_lote=id_lote).exists():
                errors.append(f"id_lote {id_lote} no existe")

            if unidad_id in unidades_by_id:
                unidad_data = unidades_by_id[unidad_id]
                _remove_error(errors, "unidad_id no existe")
                data["empresa_id"] = unidad_data.get("empresa_id") or data.get("empresa_id")
                if not data.get("id_lote"):
                    data["tipo_asignacion"] = EmisionLote.TipoAsignacion.UNIDAD

            if empresa_activa is not None and (not empresa_id or empresa_id == empresa_activa.empresa_id):
                _remove_error(errors, "empresa_id no existe")
                data["empresa_id"] = empresa_activa.empresa_id

            _apply_file_factor(data, errors, factor_lookup)
            
            if data.get("factor_emision"):
                actividades_preview["factores_encontrados"] += 1
            else:
                actividades_preview["factores_faltantes"] += 1
            
            status = "valid" if not errors else "error"
            if status == "valid":
                actividades_preview["validas"] += 1
            else:
                actividades_preview["errores"] += 1
            
            actividades_preview["rows"].append({
                "row_number": row.get("row_number"),
                "status": status,
                "errors": errors,
                "warnings": warnings,
                "data": _strip_runtime_objects(data)
            })

        # Cache el resultado
        cache_data = {
            "empresa": {
                "data": empresa_data or {},
                "errors": empresa_errors,
                "status": "valid" if not empresa_errors else "error"
            },
            "unidades": unidades_preview,
            "lotes": lotes_preview,
            "actividades": actividades_preview,
            "factores": factores_preview,
            "blocking_errors": blocking_errors,
        }
        
        cache.set(
            f"{COMPLETE_IMPORT_CACHE_PREFIX}{batch_id}",
            cache_data,
            timeout=FACTOR_IMPORT_CACHE_TTL_SECONDS,
        )

        return {
            "batch_id": batch_id,
            "empresa": cache_data["empresa"],
            "unidades": unidades_preview,
            "lotes": lotes_preview,
            "actividades": actividades_preview,
            "factores": factores_preview,
            "blocking_errors": blocking_errors,
        }

    @staticmethod
    def confirmar(batch_id: str) -> dict:
        """Confirma la importación completa."""
        cached = cache.get(f"{COMPLETE_IMPORT_CACHE_PREFIX}{batch_id}")
        if not cached:
            raise ValueError("El batch_id no existe o expiró")

        empresa_data = cached.get("empresa", {}).get("data", {})
        if not empresa_data or not empresa_data.get("empresa_id"):
            raise ValueError("La importación no contiene una empresa valida para guardar")

        created_empresa = None
        created_unidades = 0
        created_lotes = 0
        created_actividades = 0
        created_factores = 0
        errors = []

        with transaction.atomic():
            # Crear/actualizar empresa
            if empresa_data.get("empresa_id"):
                try:
                    empresa, was_created = Empresa.objects.update_or_create(
                        empresa_id=empresa_data["empresa_id"],
                        defaults={
                            "nombre": empresa_data.get("nombre", ""),
                            "rut": empresa_data.get("rut", ""),
                            "region": empresa_data.get("region", ""),
                            "comuna": empresa_data.get("comuna", ""),
                            "direccion": empresa_data.get("direccion", ""),
                            "rubro": empresa_data.get("rubro", ""),
                            "email": empresa_data.get("email", ""),
                            "telefono": empresa_data.get("telefono", ""),
                            "contacto": empresa_data.get("contacto", ""),
                            "observaciones": empresa_data.get("observaciones", ""),
                        }
                    )
                    if was_created:
                        # Crear unidad general por defecto
                        UnidadOperativa.objects.get_or_create(
                            unidad_id=f"{empresa.empresa_id}_GENERAL",
                            defaults={
                                "empresa": empresa,
                                "nombre": "Unidad General",
                                "tipo": UnidadOperativa.Tipo.GENERAL,
                            }
                        )
                    created_empresa = empresa
                except Exception as e:
                    errors.append({"section": "empresa", "error": str(e)})

            # Crear unidades
            for row in cached["unidades"].get("rows", []):
                if row.get("status") != "valid":
                    continue
                try:
                    data = row.get("data", {})
                    _, was_created = UnidadOperativa.objects.update_or_create(
                        unidad_id=data.get("unidad_id"),
                        defaults={
                            "empresa": created_empresa,
                            "nombre": data.get("nombre", ""),
                            "tipo": data.get("tipo", UnidadOperativa.Tipo.OTRO),
                            "region": data.get("region", ""),
                            "comuna": data.get("comuna", ""),
                            "direccion": data.get("direccion", ""),
                            "descripcion": data.get("descripcion", ""),
                            "activa": data.get("activa", True),
                        }
                    )
                    if was_created:
                        created_unidades += 1
                except Exception as e:
                    errors.append({"section": "unidades", "row": row.get("row_number"), "error": str(e)})

            # Crear/actualizar factores para que las actividades puedan referenciarlos.
            for row in cached["factores"].get("rows", []):
                if row.get("status") != "valid":
                    continue
                try:
                    normalized, validation_errors = _build_row_payload(row.get("data", {}))
                    if validation_errors:
                        errors.append({"section": "factores", "row": row.get("row_number"), "error": "; ".join(validation_errors)})
                        continue

                    factor = FactorEmision.objects.filter(
                        actividad_key=normalized["actividad_key"],
                        unidad__iexact=normalized["unidad"],
                        fuente__iexact=normalized["fuente"],
                        anio=normalized["anio"],
                    ).first()
                    was_created = factor is None
                    if factor is None:
                        factor = FactorEmision(
                            actividad_key=normalized["actividad_key"],
                            unidad=normalized["unidad"],
                            fuente=normalized["fuente"],
                            anio=normalized["anio"],
                        )
                    factor.actividad = normalized["actividad"]
                    factor.categoria = normalized["categoria"]
                    factor.descripcion = normalized["descripcion"]
                    factor.metadata_clasificacion = normalized.get("metadata_clasificacion", {})
                    factor.factor_emision = normalized["factor_emision"]
                    factor.save()
                    if was_created:
                        created_factores += 1
                except Exception as e:
                    errors.append({"section": "factores", "row": row.get("row_number"), "error": str(e)})

            # Crear lotes
            for row in cached["lotes"].get("rows", []):
                if row.get("status") != "valid":
                    continue
                try:
                    data = row.get("data", {})
                    unidad_id = data.get("unidad_id")
                    unidad = UnidadOperativa.objects.filter(unidad_id=unidad_id).first() if unidad_id else None
                    
                    if not unidad and created_empresa:
                        # Usar unidad general de la empresa
                        unidad = created_empresa.unidades_operativas.filter(
                            tipo=UnidadOperativa.Tipo.GENERAL
                        ).first()
                    
                    _, was_created = Lote.objects.update_or_create(
                        id_lote=data.get("id_lote"),
                        defaults={
                            "empresa": created_empresa,
                            "unidad_operativa": unidad,
                            "fecha": data.get("fecha"),
                            "especie": data.get("especie", ""),
                            "volumen_m3": data.get("volumen_m3", Decimal("0")),
                            "origen": data.get("origen", ""),
                            "tipo_producto": data.get("tipo_producto", ""),
                            "densidad_kg_m3": data.get("densidad_kg_m3"),
                            "porcentaje_carbono": data.get("porcentaje_carbono"),
                            "estado": data.get("estado", ""),
                            "observaciones": data.get("observaciones", ""),
                        }
                    )
                    if was_created:
                        created_lotes += 1
                except Exception as e:
                    errors.append({"section": "lotes", "row": row.get("row_number"), "error": str(e)})

            # Crear actividades (EmisionLote)
            for row in cached["actividades"].get("rows", []):
                if row.get("status") != "valid":
                    continue
                try:
                    data = row.get("data", {})
                    id_lote = data.get("id_lote")
                    lote = Lote.objects.filter(id_lote=id_lote).first() if id_lote else None
                    unidad_id = data.get("unidad_id")
                    unidad = UnidadOperativa.objects.filter(unidad_id=unidad_id).first() if unidad_id else None
                    
                    emission, was_created = EmisionLote.objects.update_or_create(
                        lote=lote,
                        unidad_operativa=unidad,
                        empresa=created_empresa if not (lote or unidad) else (lote.empresa if lote else (unidad.empresa if unidad else None)),
                        actividad=data.get("actividad", ""),
                        unidad=data.get("unidad", ""),
                        defaults={
                            "cantidad": data.get("cantidad", Decimal("0")),
                            "fecha": data.get("fecha"),
                            "factor_emision": data.get("factor_emision", Decimal("0")),
                            "categoria": data.get("categoria", ""),
                            "tipo_asignacion": data.get("tipo_asignacion", EmisionLote.TipoAsignacion.EMPRESA),
                        }
                    )
                    if was_created:
                        created_actividades += 1
                except Exception as e:
                    errors.append({"section": "actividades", "row": row.get("row_number"), "error": str(e)})

        return {
            "creados": 1 if created_empresa else 0,
            "empresa_id": created_empresa.empresa_id if created_empresa else None,
            "empresa_nombre": created_empresa.nombre if created_empresa else None,
            "unidades_creadas": created_unidades,
            "lotes_creados": created_lotes,
            "actividades_creadas": created_actividades,
            "factores_creados": created_factores,
            "errores": errors,
        }
