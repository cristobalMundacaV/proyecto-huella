"""Importador de empresa completa desde XLSX con múltiples hojas."""

import uuid
from decimal import Decimal
from pathlib import Path

from django.core.cache import cache
from django.db import transaction
from openpyxl import load_workbook

from ..models import Empresa, UnidadOperativa, Lote, EmisionLote, normalize_identifier
from .importadores import (
    _build_company_payload,
    _build_unit_payload,
    _build_lote_payload,
    _build_activity_payload,
    _build_row_payload,
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
    except Exception as e:
        raise ValueError(f"Error leyendo hoja {sheet_name}: {str(e)}")


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
        empresa_rows = _read_xlsx_sheet(uploaded_file, "empresa")
        unidades_rows = _read_xlsx_sheet(uploaded_file, "unidades")
        lotes_rows = _read_xlsx_sheet(uploaded_file, "lotes")
        actividades_rows = _read_xlsx_sheet(uploaded_file, "actividades")
        factores_rows = _read_xlsx_sheet(uploaded_file, "factores")

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

        # Procesar unidades
        unidades_preview = {
            "total": len(unidades_rows),
            "validas": 0,
            "errores": 0,
            "rows": []
        }
        unidades_by_id = {}
        for row in unidades_rows:
            data, errors = _build_unit_payload(row, empresa_activa=empresa_activa)
            unidad_id = data.get("unidad_id")
            status = "valid" if not errors else "error"
            if status == "valid":
                unidades_preview["validas"] += 1
                unidades_by_id[unidad_id] = data
            else:
                unidades_preview["errores"] += 1
            
            unidades_preview["rows"].append({
                "row_number": row.get("row_number"),
                "status": status,
                "errors": errors,
                "data": data
            })

        # Procesar lotes
        lotes_preview = {
            "total": len(lotes_rows),
            "validos": 0,
            "errores": 0,
            "rows": []
        }
        lotes_by_id = {}
        for row in lotes_rows:
            data, errors, warnings = _build_lote_payload(row, empresa_activa=empresa_activa)
            id_lote = data.get("id_lote")
            
            # Validar que unidad existe
            unidad_id = data.get("unidad_id")
            if unidad_id and unidad_id not in unidades_by_id and not UnidadOperativa.objects.filter(unidad_id=unidad_id).exists():
                errors.append(f"unidad_id {unidad_id} no existe en el archivo ni en la base de datos")
            
            status = "valid" if not errors else "error"
            if status == "valid":
                lotes_preview["validos"] += 1
                lotes_by_id[id_lote] = data
            else:
                lotes_preview["errores"] += 1
            
            lotes_preview["rows"].append({
                "row_number": row.get("row_number"),
                "status": status,
                "errors": errors,
                "warnings": warnings,
                "data": data
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
            data, errors = _build_activity_payload(row, empresa_activa=empresa_activa)
            
            # Validar que lote existe si está referenciado
            id_lote = data.get("id_lote")
            if id_lote and id_lote not in lotes_by_id and not Lote.objects.filter(id_lote=id_lote).exists():
                errors.append(f"id_lote {id_lote} no existe")
            
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
                "data": data
            })

        # Procesar factores
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

        created_empresa = None
        created_unidades = 0
        created_lotes = 0
        created_actividades = 0
        created_factores = 0
        errors = []

        with transaction.atomic():
            # Crear/actualizar empresa
            empresa_data = cached["empresa"].get("data", {})
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
                        unidad = created_empresa.unidadoperativa_set.filter(
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
                            "fuente": data.get("fuente", ""),
                            "anio": data.get("anio"),
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
            "empresa": created_empresa,
            "unidades_creadas": created_unidades,
            "lotes_creados": created_lotes,
            "actividades_creadas": created_actividades,
            "factores_creados": created_factores,
            "errores": errors,
        }
