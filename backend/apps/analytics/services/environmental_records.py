import hashlib
import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.dateparse import parse_date

from apps.analytics.models import Organizacion, RegistroEmision, normalize_key


REQUIRED_FIELDS = ("actividad", "categoria", "cantidad", "unidad", "fecha")

UNIT_ALIASES = {
    "kg": "kg", "kgs": "kg", "kilogramo": "kg", "kilogramos": "kg",
    "t": "t", "ton": "t", "tons": "t", "tonelada": "t", "toneladas": "t",
    "l": "l", "lt": "l", "lts": "l", "litro": "l", "litros": "l",
    "kwh": "kwh", "kw h": "kwh", "m3": "m3", "m 3": "m3",
}


def _text(value):
    return str(value or "").strip()


def normalize_fingerprint_text(value):
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def normalize_fingerprint_unit(value):
    unit = normalize_fingerprint_text(value).replace("³", "3")
    return UNIT_ALIASES.get(unit, unit.replace(" ", ""))


def _canonical_decimal(value):
    value = Decimal(str(value)).normalize()
    return format(value, "f")


def build_environmental_fingerprints(data):
    date_value = data["fecha"]
    date_key = date_value.isoformat() if hasattr(date_value, "isoformat") else _text(date_value)
    core = {
        "organizacion": data["organizacion"].pk,
        "fecha": date_key,
        "actividad": normalize_fingerprint_text(data["fuente_emision"]),
        "categoria": normalize_fingerprint_text(data["categoria"]),
        "cantidad": _canonical_decimal(data["cantidad"]),
        "unidad": normalize_fingerprint_unit(data["unidad"]),
        "proveedor": normalize_fingerprint_text(data.get("proveedor")),
        "area_operacional": normalize_fingerprint_text(data.get("area_operacional")),
        "unidad_operacional": normalize_fingerprint_text(data.get("unidad_operacional")),
    }
    complete = {
        **core,
        "numero_documento": normalize_fingerprint_text(data.get("numero_documento")),
        "identificador_externo": normalize_fingerprint_text(data.get("identificador_externo")),
    }
    digest = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return digest(complete), digest(core)


def _decimal(value, field="cantidad"):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({field: "Debe ser un numero valido."})
    if not number.is_finite() or number <= 0:
        raise ValidationError({field: "Debe ser mayor que cero."})
    return number


def _date(value):
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        return value
    parsed = parse_date(_text(value))
    if not parsed:
        raise ValidationError({"fecha": "Debe ser una fecha valida en formato YYYY-MM-DD."})
    return parsed


def _validate_relation_tenant(organizacion, relation, field):
    if relation is None:
        return
    relation_organizacion_id = getattr(relation, "organizacion_id", None)
    if relation_organizacion_id and relation_organizacion_id != organizacion.id:
        raise ValidationError({field: "No pertenece a la organizacion indicada."})


def normalize_environmental_record(payload, *, organizacion, tipo_ingreso, fuente_ingreso=""):
    """Normaliza cualquier fuente a los campos canónicos de RegistroEmision.

    La función no deduplica: `identificador_externo` se conserva para una fase
    posterior, pero nunca se interpreta aquí como fingerprint ni clave única.
    """
    if not isinstance(organizacion, Organizacion):
        raise ValidationError({"organizacion": "Se requiere una organizacion valida."})
    if not organizacion.activa:
        raise ValidationError({"organizacion": "La organizacion esta inactiva."})
    if tipo_ingreso not in RegistroEmision.TipoIngreso.values:
        raise ValidationError({"tipo_ingreso": "Tipo de ingreso no soportado."})

    actividad = _text(payload.get("actividad") or payload.get("fuente_emision"))
    categoria = _text(payload.get("categoria"))
    unidad = _text(payload.get("unidad"))
    missing = []
    if not actividad:
        missing.append("actividad")
    if not categoria:
        missing.append("categoria")
    if not unidad:
        missing.append("unidad")
    if payload.get("cantidad") in (None, ""):
        missing.append("cantidad")
    if payload.get("fecha") in (None, ""):
        missing.append("fecha")
    if missing:
        raise ValidationError({field: "Este campo es requerido." for field in missing})

    obra = payload.get("obra")
    etapa = payload.get("etapa")
    lote = payload.get("lote_forestal")
    _validate_relation_tenant(organizacion, obra, "obra")
    _validate_relation_tenant(organizacion, etapa, "etapa")
    _validate_relation_tenant(organizacion, lote, "lote_forestal")

    metadata = payload.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise ValidationError({"metadata": "Debe ser un objeto JSON."})
    metadata = dict(metadata)
    metadata.setdefault("ingesta", {})
    if isinstance(metadata["ingesta"], dict):
        metadata["ingesta"].update(
            {"tipo": tipo_ingreso, "fuente": _text(fuente_ingreso) or tipo_ingreso}
        )
    metadata.setdefault(
        "origenes_ingesta",
        [{"tipo": tipo_ingreso, "fuente": _text(fuente_ingreso) or tipo_ingreso}],
    )

    factor = payload.get("factor_emision", Decimal("0"))
    try:
        factor = Decimal(str(factor or 0))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({"factor_emision": "Debe ser un numero valido."})
    if not factor.is_finite() or factor < 0:
        raise ValidationError({"factor_emision": "No puede ser negativo."})

    return {
        "organizacion": organizacion,
        "obra": obra,
        "etapa": etapa,
        "lote_forestal": lote,
        "fecha": _date(payload.get("fecha")),
        "categoria": categoria,
        "fuente_emision": actividad,
        "actividad_key": _text(payload.get("actividad_key")) or normalize_key(actividad).replace(" ", "_"),
        "cantidad": _decimal(payload.get("cantidad")),
        "unidad": unidad,
        "factor_emision": factor,
        "proveedor": _text(payload.get("proveedor")),
        "numero_documento": _text(payload.get("numero_documento")),
        "area_operacional": _text(payload.get("area_operacional")),
        "unidad_operacional": _text(payload.get("unidad_operacional")),
        "identificador_externo": _text(payload.get("identificador_externo") or payload.get("external_id")),
        "tipo_ingreso": tipo_ingreso,
        "fuente_ingreso": _text(fuente_ingreso) or tipo_ingreso,
        "estado_validacion": payload.get("estado_validacion") or RegistroEmision.EstadoValidacion.PENDIENTE,
        "origen_transporte": _text(payload.get("origen_transporte")),
        "destino_transporte": _text(payload.get("destino_transporte")),
        "distancia_km": payload.get("distancia_km"),
        "ruta_geometry": payload.get("ruta_geometry") or [],
        "observaciones": _text(payload.get("observaciones")),
        "metadata": metadata,
    }


@transaction.atomic
def create_environmental_record(payload, *, organizacion, tipo_ingreso, fuente_ingreso=""):
    normalized = normalize_environmental_record(
        payload,
        organizacion=organizacion,
        tipo_ingreso=tipo_ingreso,
        fuente_ingreso=fuente_ingreso,
    )
    fingerprint, fingerprint_nucleo = build_environmental_fingerprints(normalized)
    exact = RegistroEmision.objects.select_for_update().filter(
        organizacion=organizacion,
        fingerprint=fingerprint,
    ).first()
    if exact:
        metadata = dict(exact.metadata or {})
        origins = list(metadata.get("origenes_ingesta") or [])
        origin = {"tipo": tipo_ingreso, "fuente": _text(fuente_ingreso) or tipo_ingreso}
        if origin not in origins:
            origins.append(origin)
            metadata["origenes_ingesta"] = origins
            exact.metadata = metadata
            exact.save(update_fields=["metadata", "updated_at"])
        return exact

    possible = RegistroEmision.objects.select_for_update().filter(
        organizacion=organizacion,
        fingerprint_nucleo=fingerprint_nucleo,
        contabilizable=True,
    ).first()
    normalized["fingerprint"] = fingerprint
    normalized["fingerprint_nucleo"] = fingerprint_nucleo
    if possible:
        normalized["estado_gobernanza"] = RegistroEmision.EstadoGobernanza.POSIBLE_DUPLICADO
        normalized["registro_canonico"] = possible
        normalized["contabilizable"] = False
    else:
        normalized["estado_gobernanza"] = RegistroEmision.EstadoGobernanza.NUEVO
    return RegistroEmision.objects.create(**normalized)


def link_evidence_to_records(evidence, records, *, organizacion):
    if evidence.organizacion_id != organizacion.id:
        raise ValidationError({"evidencia": "No pertenece a la organizacion indicada."})
    records = list(records)
    if any(record.organizacion_id != organizacion.id for record in records):
        raise ValidationError({"registros": "Deben pertenecer a la misma organizacion."})
    evidence.registros_emision.add(*records)
    return evidence


@transaction.atomic
def resolve_record_governance(record, *, estado):
    if estado not in {
        RegistroEmision.EstadoGobernanza.DUPLICADO_CONFIRMADO,
        RegistroEmision.EstadoGobernanza.VALIDADO,
    }:
        raise ValidationError({"estado_gobernanza": "Resolucion no permitida."})
    record.estado_gobernanza = estado
    record.contabilizable = estado == RegistroEmision.EstadoGobernanza.VALIDADO
    if record.contabilizable:
        record.registro_canonico = None
        record.estado_validacion = RegistroEmision.EstadoValidacion.VALIDADO
    record.save()
    return record


def create_document_environmental_record(payload, *, organizacion, documento):
    data = dict(payload)
    data.setdefault("numero_documento", getattr(documento, "numero_documento", ""))
    metadata = dict(data.get("metadata") or {})
    metadata["documento_ambiental_id"] = documento.pk
    data["metadata"] = metadata
    record = create_environmental_record(
        data,
        organizacion=organizacion,
        tipo_ingreso=RegistroEmision.TipoIngreso.DOCUMENTO,
        fuente_ingreso=getattr(documento, "nombre", "documento"),
    )
    if hasattr(documento, "registros_emision"):
        link_evidence_to_records(documento, [record], organizacion=organizacion)
    return record


def create_external_api_environmental_record(payload, *, organizacion, sistema):
    return create_environmental_record(
        payload,
        organizacion=organizacion,
        tipo_ingreso=RegistroEmision.TipoIngreso.API_EXTERNA,
        fuente_ingreso=sistema,
    )
