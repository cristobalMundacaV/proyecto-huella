import re
import unicodedata
import uuid
from decimal import Decimal, InvalidOperation
from io import BytesIO

import pandas as pd
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import (
    ConfiguracionConstructora,
    Constructora,
    EtapaObra,
    EvidenciaObra,
    FactorEmision,
    Obra,
    RegistroEmision,
    UsuarioConstructora,
)

BATCH_PREFIX = "importaciones"
BATCH_TTL = 60 * 60

SHEET_ALIASES = {
    "constructoras": ["constructora", "constructoras", "empresa", "empresas"],
    "factores": ["factores", "factores_emision", "factores de emision", "factores de emisión"],
    "etapas": ["etapas", "frentes", "etapas frentes", "etapas y frentes"],
    "obras": ["obras", "proyectos"],
    "registros": ["registros", "registros_emision", "registros de emision", "registros de emisión", "emisiones"],
    "evidencias": ["evidencias", "evidencia"],
}

CATEGORIES = [choice[0] for choice in RegistroEmision.Categoria.choices]
CATEGORY_KEYWORDS = [
    ("Materiales", ["acero", "hormigon", "cemento", "arido", "yeso", "carton", "madera", "material"]),
    ("Transporte", ["transporte", "camion", "flete", "viaje", "ruta"]),
    ("Maquinaria", ["excavadora", "retroexcavadora", "maquinaria", "equipo", "grua", "horas maquinaria"]),
    ("Energia", ["electricidad", "generador", "diesel", "energia", "kwh", "combustible"]),
    ("Agua", ["agua", "hidrico"]),
    ("Residuos", ["residuo", "escombro", "retiro", "disposicion"]),
]


def norm(value):
    value = str(value or "").strip().lower()
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_")


def clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def dec(value, default=None):
    raw = clean(value).replace(" ", "")
    if raw == "":
        return default
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    elif "." in raw:
        parts = raw.split(".")
        if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) >= 1:
            raw = "".join(parts)
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return default


def as_int(value, default=None):
    parsed = dec(value, None)
    return int(parsed) if parsed is not None else default


def as_date(value):
    if not clean(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    return None if pd.isna(parsed) else parsed.date()


def as_bool(value, default=True):
    value = norm(value)
    if value in {"", "si", "true", "1", "activa", "activo", "en_ejecucion"}:
        return True
    if value in {"no", "false", "0", "inactiva", "inactivo", "suspendida", "finalizada"}:
        return False
    return default


def normalize_category(category, source=""):
    category_norm = norm(category)
    for valid in CATEGORIES:
        if norm(valid) == category_norm:
            return valid
    text = norm(f"{category} {source}")
    for candidate, keywords in CATEGORY_KEYWORDS:
        if any(norm(keyword) in text for keyword in keywords):
            return candidate
    return "Otros"


def get(row, *aliases):
    for alias in aliases:
        key = norm(alias)
        if key in row and clean(row[key]):
            return clean(row[key])
    return ""


def get_upload(request):
    upload = request.FILES.get("file") or request.FILES.get("archivo")
    if not upload:
        raise ValueError("Debes adjuntar un archivo CSV o XLSX.")
    return upload


def read_rows(upload, sheet_name=None):
    if hasattr(upload, "seek"):
        upload.seek(0)
    filename = (getattr(upload, "name", "") or "").lower()
    if filename.endswith(".csv"):
        frame = pd.read_csv(upload)
    else:
        frame = pd.read_excel(upload, sheet_name=sheet_name or 0)
    frame = frame.fillna("").dropna(how="all")
    frame = frame.rename(columns={column: norm(column) for column in frame.columns})
    rows = []
    for index, row in frame.iterrows():
        data = {column: clean(value) for column, value in row.to_dict().items()}
        if any(data.values()):
            rows.append((int(index) + 2, data))
    return rows


def find_sheet(excel_file, kind):
    aliases = {norm(alias) for alias in SHEET_ALIASES.get(kind, [kind])}
    for sheet_name in excel_file.sheet_names:
        if norm(sheet_name) in aliases:
            return sheet_name
    return None


def row_result(row_number, data, errors=None, warnings=None, action="crear"):
    errors = errors or []
    return {
        "row_number": row_number,
        "status": "error" if errors else "valid",
        "data": data,
        "errors": errors,
        "warnings": warnings or [],
        "db_action": action,
    }


def valid_rows(rows):
    return [row for row in rows if row.get("status") == "valid"]


def cache_batch(payload):
    batch_id = str(uuid.uuid4())
    cache.set(f"{BATCH_PREFIX}:{batch_id}", payload, BATCH_TTL)
    return batch_id


def load_batch(batch_id):
    return cache.get(f"{BATCH_PREFIX}:{batch_id}") if batch_id else None


def resolve_constructora(constructora_id):
    if not constructora_id:
        return None
    return Constructora.objects.get(constructora_id=constructora_id)


def parse_constructoras(raw_rows):
    rows = []
    seen = set()
    for row_number, raw in raw_rows:
        data = {
            "constructora_id": get(raw, "ID constructora", "constructora_id", "id"),
            "nombre": get(raw, "Nombre", "Constructora", "Nombre constructora"),
            "rut": get(raw, "RUT"),
            "region": get(raw, "Región", "Region"),
            "comuna": get(raw, "Comuna"),
            "direccion": get(raw, "Dirección", "Direccion"),
            "rubro": get(raw, "Rubro"),
            "email": get(raw, "Email", "Correo"),
            "telefono": get(raw, "Teléfono", "Telefono"),
            "contacto": get(raw, "Contacto"),
            "observaciones": get(raw, "Observaciones"),
        }
        if not data["constructora_id"] and data["nombre"]:
            data["constructora_id"] = norm(data["nombre"]).upper()
        errors = []
        warnings = []
        if not data["nombre"]:
            errors.append("El nombre de la constructora es obligatorio.")
        if not data["constructora_id"]:
            errors.append("El ID constructora es obligatorio.")
        key = norm(data["constructora_id"] or data["nombre"])
        if key in seen:
            warnings.append("Posible duplicado dentro del archivo.")
        seen.add(key)
        exists = bool(data["constructora_id"] and Constructora.objects.filter(constructora_id=data["constructora_id"]).exists())
        rows.append(row_result(row_number, data, errors, warnings, "actualizar" if exists else "crear"))
    return rows


def parse_factores(raw_rows):
    rows = []
    for row_number, raw in raw_rows:
        activity = get(raw, "Fuente de emisión", "Fuente de emision", "Actividad", "Material", "Nombre")
        data = {
            "fuente_emision": activity,
            "actividad": activity,
            "categoria": normalize_category(get(raw, "Categoría", "Categoria"), activity),
            "unidad": get(raw, "Unidad", "Etapa", "Unidad de medida", "Tipo de consumo"),
            "factor_emision": get(raw, "Factor de Emisión", "Factor de emision", "Factor"),
            "fuente": get(raw, "Fuente", "Fuente dato", "Referencia") or "Carga importada",
            "anio": get(raw, "Año", "Anio", "Year") or "2026",
            "observaciones": get(raw, "Observaciones", "Descripción", "Descripcion"),
        }
        errors = []
        if not data["fuente_emision"]:
            errors.append("La fuente de emisión es obligatoria.")
        if not data["unidad"]:
            errors.append("La unidad es obligatoria.")
        if dec(data["factor_emision"], None) is None:
            errors.append("El factor de emisión debe ser numérico.")
        if as_int(data["anio"], None) is None:
            errors.append("El año debe ser numérico.")
        exists = FactorEmision.objects.filter(
            actividad=data["fuente_emision"],
            unidad=data["unidad"],
            fuente=data["fuente"],
            anio=as_int(data["anio"], 2026),
        ).exists()
        rows.append(row_result(row_number, data, errors, [], "actualizar" if exists else "crear"))
    return rows


def parse_etapas(raw_rows, constructora=None):
    rows = []
    for row_number, raw in raw_rows:
        constructora_id = get(raw, "ID constructora", "constructora_id") or getattr(constructora, "constructora_id", "")
        nombre = get(raw, "Nombre", "Etapa", "Frente")
        data = {
            "etapa_id": get(raw, "ID Etapa", "Etapa ID", "id_etapa") or norm(f"{constructora_id}_{nombre}").upper(),
            "constructora_id": constructora_id,
            "nombre": nombre,
            "tipo": get(raw, "Tipo") or nombre or "Otro",
            "region": get(raw, "Región", "Region"),
            "comuna": get(raw, "Comuna"),
            "direccion": get(raw, "Dirección", "Direccion"),
            "estado": norm(get(raw, "Estado") or "activa"),
            "activa": as_bool(get(raw, "Activa", "Estado"), True),
            "descripcion": get(raw, "Descripción", "Descripcion", "Observaciones"),
        }
        errors = []
        if not data["constructora_id"]:
            errors.append("El ID constructora es obligatorio.")
        if not data["nombre"]:
            errors.append("El nombre de la etapa es obligatorio.")
        exists = EtapaObra.objects.filter(etapa_id=data["etapa_id"]).exists()
        rows.append(row_result(row_number, data, errors, [], "actualizar" if exists else "crear"))
    return rows


def parse_obras(raw_rows, constructora=None, known_stage_ids=None):
    rows = []
    known_stage_ids = known_stage_ids or set()
    for row_number, raw in raw_rows:
        constructora_id = get(raw, "ID constructora", "constructora_id") or getattr(constructora, "constructora_id", "")
        tipo = get(raw, "Material / tipo de obra", "Tipo de obra", "Tipo proyecto", "Tipo") or "Otro"
        code = get(raw, "Código de obra", "Codigo de obra", "codigo_obra")
        name = get(raw, "Obra / proyecto", "Nombre", "Proyecto") or tipo or code
        data = {
            "codigo_obra": code or norm(name).upper(),
            "constructora_id": constructora_id,
            "etapa_id": get(raw, "ID Etapa", "Etapa ID", "id_etapa"),
            "fecha": get(raw, "Fecha", "Fecha inicio", "fecha_inicio"),
            "fecha_inicio": get(raw, "Fecha", "Fecha inicio", "fecha_inicio"),
            "nombre": name,
            "tipo_proyecto": tipo,
            "superficie_m2": get(raw, "Cantidad base", "Superficie", "Superficie m2", "m2"),
            "origen": get(raw, "Ubicación / origen", "Ubicacion", "Ubicación", "Origen"),
            "ubicacion": get(raw, "Ubicación / origen", "Ubicacion", "Ubicación", "Origen"),
            "region": get(raw, "Región", "Region"),
            "comuna": get(raw, "Comuna"),
            "estado": norm(get(raw, "Estado") or "en_ejecucion"),
            "descripcion": get(raw, "Observaciones", "Descripción", "Descripcion"),
        }
        errors = []
        if not data["codigo_obra"]:
            errors.append("El código de obra es obligatorio.")
        if not data["constructora_id"]:
            errors.append("El ID constructora es obligatorio.")
        if not as_date(data["fecha_inicio"]):
            errors.append("La fecha de inicio es obligatoria y debe ser válida.")
        if data["etapa_id"] and data["etapa_id"] not in known_stage_ids and not EtapaObra.objects.filter(etapa_id=data["etapa_id"]).exists():
            errors.append(f"No existe la etapa {data['etapa_id']}.")
        exists = Obra.objects.filter(codigo_obra=data["codigo_obra"]).exists()
        rows.append(row_result(row_number, data, errors, [], "actualizar" if exists else "crear"))
    return rows


def find_factor(activity, unit):
    if not activity:
        return None
    queryset = FactorEmision.objects.filter(actividad__iexact=activity)
    if unit:
        factor = queryset.filter(unidad__iexact=unit).order_by("-anio").first()
        if factor:
            return factor
    return queryset.order_by("-anio").first()


def parse_registros(raw_rows, constructora=None, known_stage_ids=None, known_work_codes=None, known_factors=None):
    rows = []
    known_stage_ids = known_stage_ids or set()
    known_work_codes = known_work_codes or set()
    known_factors = known_factors or {}
    for row_number, raw in raw_rows:
        source = get(raw, "Fuente", "Fuente de emisión", "Fuente de emision", "Actividad")
        unit = get(raw, "Unidad", "Etapa", "Tipo de consumo")
        factor_obj = find_factor(source, unit)
        factor_from_file = known_factors.get((norm(source), norm(unit)))
        factor_value = get(raw, "Factor", "Factor de emisión", "Factor de emision") or factor_from_file or (str(factor_obj.factor_emision) if factor_obj else "")
        data = {
            "registro_id": get(raw, "ID Registro", "Registro ID", "id_registro"),
            "codigo_obra": get(raw, "Código de obra", "Codigo de obra", "codigo_obra"),
            "constructora_id": get(raw, "ID constructora", "constructora_id") or getattr(constructora, "constructora_id", ""),
            "etapa_id": get(raw, "ID Etapa", "Etapa ID", "id_etapa"),
            "fuente_emision": source,
            "categoria": normalize_category(get(raw, "Categoría", "Categoria") or (factor_obj.categoria if factor_obj else ""), source),
            "cantidad": get(raw, "Cantidad"),
            "unidad": unit or (factor_obj.unidad if factor_obj else ""),
            "factor_emision": factor_value,
            "fecha": get(raw, "Fecha"),
            "observaciones": get(raw, "Observación", "Observacion", "Observaciones"),
            "fuente_dato": get(raw, "Fuente de dato", "Fuente dato"),
        }
        errors = []
        if not data["fuente_emision"]:
            errors.append("La fuente de emisión es obligatoria.")
        if dec(data["cantidad"], None) is None:
            errors.append("La cantidad debe ser numérica.")
        if not data["unidad"]:
            errors.append("La unidad es obligatoria.")
        if dec(data["factor_emision"], None) is None:
            errors.append("No se encontró factor de emisión válido para la fuente/unidad.")
        if not as_date(data["fecha"]):
            errors.append("La fecha debe ser válida.")
        if data["codigo_obra"] and data["codigo_obra"] not in known_work_codes and not Obra.objects.filter(codigo_obra=data["codigo_obra"]).exists():
            errors.append(f"No existe la obra {data['codigo_obra']}.")
        if data["etapa_id"] and data["etapa_id"] not in known_stage_ids and not EtapaObra.objects.filter(etapa_id=data["etapa_id"]).exists():
            errors.append(f"No existe la etapa {data['etapa_id']}.")
        rows.append(row_result(row_number, data, errors))
    return rows


def parse_evidencias(raw_rows, constructora=None, known_work_codes=None):
    rows = []
    known_work_codes = known_work_codes or set()
    for row_number, raw in raw_rows:
        data = {
            "codigo_obra": get(raw, "Código de obra", "Codigo de obra", "codigo_obra"),
            "etapa_id": get(raw, "ID Etapa", "Etapa ID", "id_etapa"),
            "tipo_evidencia": norm(get(raw, "Tipo evidencia", "Tipo de evidencia")) or "otro",
            "nombre": get(raw, "Nombre", "Documento", "Archivo") or "Evidencia importada",
            "fecha_documento": get(raw, "Fecha", "Fecha documento"),
            "estado_documental": norm(get(raw, "Estado", "Estado documental")) or "pendiente",
            "archivo": get(raw, "Archivo", "Archivo referencia") or "documento_importado.txt",
            "observaciones": get(raw, "Observaciones"),
        }
        errors = []
        if data["codigo_obra"] and data["codigo_obra"] not in known_work_codes and not Obra.objects.filter(codigo_obra=data["codigo_obra"]).exists():
            errors.append(f"No existe la obra {data['codigo_obra']}.")
        if not data["codigo_obra"] and not constructora:
            errors.append("Debes indicar código de obra o importar dentro de una constructora.")
        rows.append(row_result(row_number, data, errors))
    return rows


def summary(rows, kind):
    total = len(rows)
    valid = len(valid_rows(rows))
    errors = total - valid
    updates = len([row for row in valid_rows(rows) if row.get("db_action") == "actualizar"])
    creates = valid - updates
    duplicates = len([row for row in rows if "duplic" in " ".join(row.get("warnings", [])).lower()])
    if kind in {"constructoras", "factores"}:
        return {"total_filas": total, "validas": valid, "con_error": errors, "duplicadas": duplicates, "posibles_creaciones": creates, "posibles_actualizaciones": updates}
    if kind == "etapas":
        return {"validas": valid, "con_error": errors, "nuevas": creates, "existentes": updates, "duplicadas": duplicates}
    if kind == "obras":
        return {"validas": valid, "con_error": errors, "obras_nuevos": creates, "obras_existentes": updates, "duplicadas": duplicates}
    return {"total_filas": total, "validas": valid, "con_error": errors}


def registros_summary(rows):
    valid = valid_rows(rows)
    return {
        "filas_validas": len(valid),
        "filas_con_error": len(rows) - len(valid),
        "factores_encontrados": len([row for row in valid if row["data"].get("factor_emision")]),
        "factores_faltantes": len([row for row in rows if any("factor" in error.lower() for error in row.get("errors", []))]),
        "obras_encontrados": len([row for row in valid if row["data"].get("codigo_obra")]),
        "obras_nuevos_detectados": 0,
    }


def preview_payload(kind, rows):
    payload = {"rows": rows, "summary": registros_summary(rows) if kind == "registros" else summary(rows, kind)}
    payload["batch_id"] = cache_batch({"kind": kind, "rows": rows})
    return payload


def save_constructoras(rows, user=None):
    created = updated = 0
    last = None
    for row in valid_rows(rows):
        data = row["data"]
        constructora_id = data.get("constructora_id") or norm(data.get("nombre")).upper()
        constructora, was_created = Constructora.objects.update_or_create(
            constructora_id=constructora_id,
            defaults={
                "nombre": data.get("nombre") or constructora_id,
                "rut": data.get("rut", ""),
                "region": data.get("region", ""),
                "comuna": data.get("comuna", ""),
                "direccion": data.get("direccion", ""),
                "rubro": data.get("rubro", ""),
                "email": data.get("email", ""),
                "telefono": data.get("telefono", ""),
                "contacto": data.get("contacto", ""),
                "observaciones": data.get("observaciones", ""),
                "activa": True,
            },
        )
        ConfiguracionConstructora.objects.get_or_create(constructora=constructora)
        if user and getattr(user, "is_authenticated", False):
            UsuarioConstructora.objects.get_or_create(user=user, constructora=constructora, defaults={"rol": UsuarioConstructora.Rol.ADMIN, "cargo": "Administrador"})
        last = constructora
        created += int(was_created)
        updated += int(not was_created)
    return {"creados": created, "actualizados": updated, "rechazados": len(rows) - len(valid_rows(rows)), "constructora": last}


def save_factores(rows):
    created = updated = 0
    for row in valid_rows(rows):
        data = row["data"]
        _, was_created = FactorEmision.objects.update_or_create(
            actividad=data["fuente_emision"],
            unidad=data["unidad"],
            fuente=data.get("fuente") or "Carga importada",
            anio=as_int(data.get("anio"), 2026),
            defaults={"categoria": normalize_category(data.get("categoria"), data.get("fuente_emision")), "factor_emision": dec(data.get("factor_emision"), Decimal("0")), "descripcion": data.get("observaciones", "")},
        )
        created += int(was_created)
        updated += int(not was_created)
    return {"creados": created, "actualizados": updated, "rechazados": len(rows) - len(valid_rows(rows))}


def save_etapas(rows, constructora=None):
    created = updated = 0
    for row in valid_rows(rows):
        data = row["data"]
        owner = constructora or Constructora.objects.get(constructora_id=data["constructora_id"])
        _, was_created = EtapaObra.objects.update_or_create(
            etapa_id=data["etapa_id"],
            defaults={"constructora": owner, "nombre": data.get("nombre") or data["etapa_id"], "tipo": data.get("tipo") or "Otro", "region": data.get("region", ""), "comuna": data.get("comuna", ""), "direccion": data.get("direccion", ""), "descripcion": data.get("descripcion", ""), "estado": data.get("estado") or "activa", "activa": bool(data.get("activa", True))},
        )
        created += int(was_created)
        updated += int(not was_created)
    return {"creados": created, "actualizados": updated, "rechazados": len(rows) - len(valid_rows(rows))}


def save_obras(rows, constructora=None):
    created = updated = 0
    for row in valid_rows(rows):
        data = row["data"]
        owner = constructora or Constructora.objects.get(constructora_id=data["constructora_id"])
        etapa = EtapaObra.objects.filter(etapa_id=data.get("etapa_id")).first()
        _, was_created = Obra.objects.update_or_create(
            codigo_obra=data["codigo_obra"],
            defaults={"constructora": owner, "etapa_principal": etapa, "nombre": data.get("nombre") or data["codigo_obra"], "tipo_proyecto": data.get("tipo_proyecto") or "Otro", "fecha_inicio": as_date(data.get("fecha_inicio")) or as_date(data.get("fecha")), "superficie_m2": dec(data.get("superficie_m2"), None), "ubicacion": data.get("ubicacion") or data.get("origen", ""), "region": data.get("region", ""), "comuna": data.get("comuna", ""), "estado": data.get("estado") or "en_ejecucion", "descripcion": data.get("descripcion", "")},
        )
        created += int(was_created)
        updated += int(not was_created)
    return {"creados": created, "actualizados": updated, "rechazados": len(rows) - len(valid_rows(rows))}


def save_registros(rows, constructora=None):
    created = 0
    for row in valid_rows(rows):
        data = row["data"]
        obra = Obra.objects.filter(codigo_obra=data.get("codigo_obra")).first()
        etapa = EtapaObra.objects.filter(etapa_id=data.get("etapa_id")).first()
        owner = constructora or (obra.constructora if obra else None) or (etapa.constructora if etapa else None)
        RegistroEmision.objects.create(
            constructora=owner,
            obra=obra,
            etapa=etapa,
            categoria=normalize_category(data.get("categoria"), data.get("fuente_emision")),
            fuente_emision=data.get("fuente_emision") or "Fuente importada",
            cantidad=dec(data.get("cantidad"), Decimal("0")),
            unidad=data.get("unidad") or "unidad",
            factor_emision=dec(data.get("factor_emision"), Decimal("0")),
            fecha=as_date(data.get("fecha")),
            observaciones=data.get("observaciones", ""),
            metadata={"registro_import_id": data.get("registro_id", ""), "fuente_dato": data.get("fuente_dato", "")},
        )
        created += 1
    return {"creados": created, "actualizados": 0, "rechazados": len(rows) - len(valid_rows(rows))}


def save_evidencias(rows, constructora=None):
    created = 0
    for row in valid_rows(rows):
        data = row["data"]
        obra = Obra.objects.filter(codigo_obra=data.get("codigo_obra")).first()
        etapa = EtapaObra.objects.filter(etapa_id=data.get("etapa_id")).first()
        owner = constructora or (obra.constructora if obra else None) or (etapa.constructora if etapa else None)
        if not owner:
            continue
        evidencia = EvidenciaObra(constructora=owner, obra=obra, etapa=etapa, tipo_evidencia=data.get("tipo_evidencia") or "otro", estado_documental=data.get("estado_documental") or "pendiente", fecha_documento=as_date(data.get("fecha_documento")), nombre=data.get("nombre") or "Evidencia importada", observaciones=data.get("observaciones", ""))
        filename = data.get("archivo") or f"evidencia_importada_{uuid.uuid4().hex}.txt"
        evidencia.archivo.save(filename, ContentFile("Archivo referencial creado por importación de datos."), save=True)
        created += 1
    return {"creados": created, "actualizados": 0, "rechazados": len(rows) - len(valid_rows(rows))}


def parse_for_kind(kind, upload, constructora=None):
    rows = read_rows(upload)
    if kind == "constructoras":
        return parse_constructoras(rows)
    if kind == "factores":
        return parse_factores(rows)
    if kind == "etapas":
        return parse_etapas(rows, constructora)
    if kind == "obras":
        return parse_obras(rows, constructora)
    if kind == "registros":
        return parse_registros(rows, constructora)
    raise ValueError("Tipo de importación no soportado.")


def save_for_kind(kind, rows, user=None, constructora=None):
    if kind == "constructoras":
        return save_constructoras(rows, user)
    if kind == "factores":
        return save_factores(rows)
    if kind == "etapas":
        return save_etapas(rows, constructora)
    if kind == "obras":
        return save_obras(rows, constructora)
    if kind == "registros":
        return save_registros(rows, constructora)
    raise ValueError("Tipo de importación no soportado.")


def normalize_kind(kind):
    kind = norm(kind).replace("registros_emision", "registros")
    if kind in {"constructoras", "factores", "etapas", "obras", "registros"}:
        return kind
    raise ValueError("Tipo de importación no soportado.")


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def importacion_preview(request, kind, constructora_id=None):
    try:
        normalized_kind = normalize_kind(kind)
        constructora = resolve_constructora(constructora_id)
        rows = parse_for_kind(normalized_kind, get_upload(request), constructora)
        return Response(preview_payload(normalized_kind, rows))
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def importacion_confirm(request, kind, constructora_id=None):
    try:
        normalized_kind = normalize_kind(kind)
        constructora = resolve_constructora(constructora_id)
        batch = load_batch(request.data.get("batch_id"))
        rows = (batch or {}).get("rows") or request.data.get("rows") or []
        with transaction.atomic():
            result = save_for_kind(normalized_kind, rows, request.user, constructora)
        result.pop("constructora", None)
        return Response(result)
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def plantilla_importacion_construccion(request):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(columns=["ID constructora", "Nombre", "RUT", "Región", "Comuna", "Dirección", "Rubro", "Email", "Teléfono", "Contacto", "Observaciones"]).to_excel(writer, sheet_name="constructora", index=False)
        pd.DataFrame(columns=["Fuente de emisión", "Categoría", "Unidad", "Factor de Emisión", "Fuente", "Año", "Observaciones"]).to_excel(writer, sheet_name="factores", index=False)
        pd.DataFrame(columns=["ID Etapa", "ID constructora", "Nombre", "Tipo", "Región", "Comuna", "Dirección", "Estado", "Observaciones"]).to_excel(writer, sheet_name="etapas", index=False)
        pd.DataFrame(columns=["Código de obra", "ID constructora", "ID Etapa", "Obra / proyecto", "Fecha", "Material / tipo de obra", "Cantidad base", "Ubicación / origen", "Región", "Comuna", "Estado", "Observaciones"]).to_excel(writer, sheet_name="obras", index=False)
        pd.DataFrame(columns=["ID Registro", "Código de obra", "ID Etapa", "Fuente", "Categoría", "Cantidad", "Unidad", "Factor", "Fecha", "Observación", "Fuente de dato"]).to_excel(writer, sheet_name="registros", index=False)
        pd.DataFrame(columns=["Código de obra", "ID Etapa", "Tipo evidencia", "Nombre", "Fecha", "Estado", "Archivo", "Observaciones"]).to_excel(writer, sheet_name="evidencias", index=False)
    response = HttpResponse(output.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="plantilla_importacion_construccion.xlsx"'
    return response


def preview_complete_payload(upload):
    if hasattr(upload, "seek"):
        upload.seek(0)
    excel = pd.ExcelFile(upload)
    missing = []
    raw = {}
    for key in ["constructoras", "factores", "etapas", "obras", "registros", "evidencias"]:
        sheet = find_sheet(excel, key)
        if not sheet and key != "evidencias":
            missing.append(key)
        elif sheet:
            raw[key] = read_rows(upload, sheet)
    blocking_errors = [f"Falta la hoja {sheet}." for sheet in missing]
    constructoras = parse_constructoras(raw.get("constructoras", []))
    constructora_data = constructoras[0]["data"] if constructoras else {}
    temp_constructora = type("TempConstructora", (), {"constructora_id": constructora_data.get("constructora_id", "")})()
    factores = parse_factores(raw.get("factores", []))
    factor_map = {(norm(row["data"].get("fuente_emision")), norm(row["data"].get("unidad"))): row["data"].get("factor_emision") for row in valid_rows(factores)}
    etapas = parse_etapas(raw.get("etapas", []), temp_constructora)
    stage_ids = {row["data"].get("etapa_id") for row in valid_rows(etapas)}
    obras = parse_obras(raw.get("obras", []), temp_constructora, stage_ids)
    work_codes = {row["data"].get("codigo_obra") for row in valid_rows(obras)}
    registros = parse_registros(raw.get("registros", []), temp_constructora, stage_ids, work_codes, factor_map)
    evidencias = parse_evidencias(raw.get("evidencias", []), temp_constructora, work_codes)
    if constructoras and constructoras[0]["status"] == "error":
        blocking_errors.extend(constructoras[0].get("errors", []))
    dates = [as_date(row["data"].get("fecha")) for row in valid_rows(registros) if as_date(row["data"].get("fecha"))]
    emissions = sum(float(dec(row["data"].get("cantidad"), Decimal("0")) * dec(row["data"].get("factor_emision"), Decimal("0"))) for row in valid_rows(registros))
    payload = {
        "constructora": constructoras[0] if constructoras else {"status": "error", "data": {}, "errors": ["No se encontró la constructora."]},
        "factores": {"rows": factores, "total": len(factores), "validas": len(valid_rows(factores)), "errores": len(factores) - len(valid_rows(factores))},
        "etapas": {"rows": etapas, "total": len(etapas), "validas": len(valid_rows(etapas)), "errores": len(etapas) - len(valid_rows(etapas))},
        "obras": {"rows": obras, "total": len(obras), "validos": len(valid_rows(obras)), "errores": len(obras) - len(valid_rows(obras))},
        "registros_emision": {"rows": registros, "total": len(registros), "validas": len(valid_rows(registros)), "errores": len(registros) - len(valid_rows(registros)), "factores_faltantes": registros_summary(registros)["factores_faltantes"]},
        "evidencias": {"rows": evidencias, "total": len(evidencias), "validas": len(valid_rows(evidencias)), "errores": len(evidencias) - len(valid_rows(evidencias))},
        "blocking_errors": blocking_errors,
        "resumen": {"Constructora_detectada": constructora_data.get("nombre", ""), "periodo_detectado": f"{min(dates)} a {max(dates)}" if dates else "Sin fechas", "emisiones_estimadas_kg_co2e": emissions, "alertas": []},
    }
    payload["batch_id"] = cache_batch({"kind": "completa", "payload": payload})
    return payload


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def importacion_completa_preview(request):
    try:
        return Response(preview_complete_payload(get_upload(request)))
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def importacion_completa_confirm(request):
    batch = load_batch(request.data.get("batch_id"))
    if not batch:
        return Response({"error": "La previsualización expiró. Carga nuevamente el archivo antes de confirmar."}, status=status.HTTP_400_BAD_REQUEST)
    payload = batch.get("payload") or {}
    with transaction.atomic():
        constructora_result = save_constructoras([payload["constructora"]], request.user)
        constructora = constructora_result.get("constructora")
        factores_result = save_factores(payload.get("factores", {}).get("rows", []))
        etapas_result = save_etapas(payload.get("etapas", {}).get("rows", []), constructora)
        obras_result = save_obras(payload.get("obras", {}).get("rows", []), constructora)
        registros_result = save_registros(payload.get("registros_emision", {}).get("rows", []), constructora)
        evidencias_result = save_evidencias(payload.get("evidencias", {}).get("rows", []), constructora)
    return Response({
        "creados": constructora_result["creados"],
        "actualizados": constructora_result["actualizados"],
        "rechazados": constructora_result["rechazados"],
        "factores_creados": factores_result["creados"],
        "etapas_creadas": etapas_result["creados"],
        "obras_creados": obras_result["creados"],
        "registros_emision_creadas": registros_result["creados"],
        "evidencias_creadas": evidencias_result["creados"],
        "errores": [],
    })
