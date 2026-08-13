from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.dateparse import parse_date

from apps.analytics.models import Organizacion, RegistroEmision, normalize_key


REQUIRED_FIELDS = ("actividad", "categoria", "cantidad", "unidad", "fecha")


def _text(value):
    return str(value or "").strip()


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
    return RegistroEmision.objects.create(**normalized)


def create_document_environmental_record(payload, *, organizacion, documento):
    data = dict(payload)
    data.setdefault("numero_documento", getattr(documento, "numero_documento", ""))
    metadata = dict(data.get("metadata") or {})
    metadata["documento_ambiental_id"] = documento.pk
    data["metadata"] = metadata
    return create_environmental_record(
        data,
        organizacion=organizacion,
        tipo_ingreso=RegistroEmision.TipoIngreso.DOCUMENTO,
        fuente_ingreso=getattr(documento, "nombre", "documento"),
    )


def create_external_api_environmental_record(payload, *, organizacion, sistema):
    return create_environmental_record(
        payload,
        organizacion=organizacion,
        tipo_ingreso=RegistroEmision.TipoIngreso.API_EXTERNA,
        fuente_ingreso=sistema,
    )
