from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import (
    EnvironmentalFactorCandidate,
    FactorAmbiental,
    VersionFactorAmbiental,
)
from .unit_conversion import UnitConversionError, canonicalize_unit, convert_value

RESULT_UNITS = {"kgco2e": "kgCO2e", "tco2e": "tCO2e"}
PUBLISHED_UNIT_LABELS = {
    "metros cúbicos": "m3",
    "metros cubicos": "m3",
    "litros": "L",
    "kilogramos": "kg",
    "toneladas": "t",
    "kwh": "kWh",
    "mwh": "MWh",
}
MAPPING_TYPES = {"combustible", "energia_red"}


def _ensure_current_source(candidate):
    current = candidate.source_fact.__class__.objects.filter(
        pk=candidate.source_fact_id, artifact__is_current=True
    ).exists()
    if not current:
        raise ValidationError({"source_fact": "fuente_historica_no_promocionable"})


def _result_units_equivalent(left, right):
    return left in RESULT_UNITS.values() and right in RESULT_UNITS.values()


def _factor_value_for_unit(value, source_unit, target_unit):
    if source_unit == target_unit:
        return value
    if source_unit == "kgCO2e" and target_unit == "tCO2e":
        return value / Decimal("1000")
    if source_unit == "tCO2e" and target_unit == "kgCO2e":
        return value * Decimal("1000")
    raise ValidationError("Las unidades de resultado no son convertibles.")


def parse_emission_factor_unit(value):
    parts = str(value or "").strip().split("/", 1)
    if len(parts) != 2 or parts[0].strip().casefold() not in RESULT_UNITS:
        return {"compatible": False, "reason": "unidad_resultado_no_soportada"}
    result = RESULT_UNITS[parts[0].strip().casefold()]
    denominator = parts[1].strip()
    candidate = PUBLISHED_UNIT_LABELS.get(denominator.casefold(), denominator)
    try:
        input_unit = canonicalize_unit(candidate)
    except UnitConversionError:
        return {
            "compatible": False,
            "reason": "unidad_no_soportada",
            "result_unit": result,
            "raw_input_unit": denominator,
        }
    return {
        "compatible": True,
        "result_unit": result,
        "input_unit": input_unit,
        "raw_input_unit": denominator,
    }


def candidate_provenance(fact):
    artifact = fact.artifact
    return {
        "source": "HuellaChile",
        "publisher": fact.publisher,
        "source_fact_id": fact.id,
        "artifact_id": artifact.id,
        "artifact_version": artifact.version,
        "artifact_sha256": artifact.content_sha256,
        "dataset_year": fact.dataset_year,
        "sheet": fact.sheet_name,
        "source_row_number": fact.source_row_number,
        "row": fact.source_row_number,
        "external_record_id": artifact.parent_record_id,
        "external_activity": fact.actividad,
        "external_category": fact.categoria,
        "external_scope": fact.alcance,
        "published_value": fact.published_value_raw,
        "activity_unit": fact.unidad_actividad,
        "factor_unit": fact.unidad_factor,
        "technical_source_1": fact.technical_source_1,
        "technical_source_2": fact.technical_source_2,
        "technical_source_3": fact.technical_source_3,
    }


def evaluate_factor_candidate_compatibility(candidate):
    fact = candidate.source_fact
    parsed = parse_emission_factor_unit(fact.unidad_factor)
    reasons = []
    conversion = None
    if fact.factor_value is None or not fact.cached_value_available:
        reasons.append("factor_no_numerico")
    if fact.published_value_raw.strip().casefold() == "pendiente":
        reasons.append("factor_pendiente")
    activity_label = PUBLISHED_UNIT_LABELS.get(
        fact.unidad_actividad.strip().casefold(), fact.unidad_actividad
    )
    try:
        activity_unit = canonicalize_unit(activity_label)
    except UnitConversionError:
        activity_unit = None
        reasons.append("unidad_actividad_no_soportada")
    if not parsed.get("compatible"):
        reasons.append(parsed["reason"])
    elif activity_unit:
        try:
            conversion = convert_value(
                Decimal("1"), activity_unit, parsed["input_unit"]
            )
        except UnitConversionError:
            reasons.append("denominador_incompatible")
        else:
            conversion = {
                key: str(value) if isinstance(value, Decimal) else value
                for key, value in conversion.items()
            }
    compatibility = {
        **candidate_provenance(fact),
        "compatible": not reasons,
        "reasons": list(dict.fromkeys(reasons)),
        "normalized_input_unit": parsed.get("input_unit"),
        "normalized_result_unit": parsed.get("result_unit"),
        "activity_to_denominator_conversion": conversion,
        "source_current": fact.artifact.is_current,
    }
    return compatibility


@transaction.atomic
def build_huellachile_factor_candidates(year=2025):
    from apps.knowledge.models import HuellaChileEmissionFactorFact

    facts = HuellaChileEmissionFactorFact.objects.filter(
        dataset_year=year, artifact__is_current=True
    ).select_related("artifact", "artifact__parent_record")
    created = 0
    existing = 0
    numeric = 0
    pending = 0
    compatible = 0
    unsupported = 0
    for fact in facts.iterator():
        candidate, was_created = EnvironmentalFactorCandidate.objects.get_or_create(
            source_fact=fact
        )
        created += was_created
        existing += not was_created
        result = evaluate_factor_candidate_compatibility(candidate)
        candidate.compatibility = result
        if candidate.status not in {
            candidate.Status.READY,
            candidate.Status.REJECTED,
            candidate.Status.PROMOTED,
        }:
            candidate.status = (
                candidate.Status.REQUIRES_MAPPING
                if result["compatible"]
                else candidate.Status.DETECTED
            )
        candidate.save(update_fields=["compatibility", "status", "updated_at"])
        numeric += fact.factor_value is not None
        pending += fact.published_value_raw.strip().casefold() == "pendiente"
        compatible += result["compatible"]
        unsupported += int(
            "unidad_no_soportada" in result["reasons"]
            or "unidad_actividad_no_soportada" in result["reasons"]
        )
    return {
        "facts": facts.count(),
        "candidates_created": created,
        "candidates_existing": existing,
        "numeric": numeric,
        "pending": pending,
        "mechanically_compatible": compatible,
        "unsupported_unit": unsupported,
        "requires_mapping": EnvironmentalFactorCandidate.objects.filter(
            source_fact__in=facts,
            status=EnvironmentalFactorCandidate.Status.REQUIRES_MAPPING,
        ).count(),
    }


def validate_candidate_mapping(candidate, mapping_type, context):
    _ensure_current_source(candidate)
    if mapping_type not in MAPPING_TYPES:
        raise ValidationError({"mapping_type": "Mapping no soportado."})
    compatibility = evaluate_factor_candidate_compatibility(candidate)
    if not compatibility["compatible"]:
        raise ValidationError({"compatibility": compatibility["reasons"]})
    errors = {}
    if mapping_type == "combustible":
        unknown = set(context) - {
            "proveedor",
            "alcance",
            "categoria_huella",
            "combustible",
        }
        if unknown:
            errors["mapping_context"] = (
                f"Campos no soportados: {', '.join(sorted(unknown))}."
            )
        if context.get("alcance") != 1:
            errors["alcance"] = "Debe ser alcance 1."
        if context.get("categoria_huella") not in {
            "combustion_estacionaria",
            "combustion_movil",
        }:
            errors["categoria_huella"] = "Categoría no soportada."
        if not str(context.get("combustible") or "").strip():
            errors["combustible"] = "Campo obligatorio."
        normalized = {
            "proveedor": "HuellaChile",
            "alcance": 1,
            "categoria_huella": context.get("categoria_huella"),
            "combustible": str(context.get("combustible") or "").strip().casefold(),
        }
    else:
        unknown = set(context) - {"proveedor", "alcance", "sistema", "metodo", "pais"}
        if unknown:
            errors["mapping_context"] = (
                f"Campos no soportados: {', '.join(sorted(unknown))}."
            )
        if context.get("alcance") != 2:
            errors["alcance"] = "Debe ser alcance 2."
        for field in ("sistema", "metodo", "pais"):
            if not str(context.get(field) or "").strip():
                errors[field] = "Campo obligatorio."
        normalized = {
            "proveedor": "HuellaChile",
            "alcance": 2,
            "sistema": str(context.get("sistema") or "").strip(),
            "metodo": str(context.get("metodo") or "").strip(),
            "pais": str(context.get("pais") or "").strip(),
        }
    if errors:
        raise ValidationError(errors)
    if context.get("proveedor") not in (None, "HuellaChile"):
        raise ValidationError(
            {"proveedor": "El proveedor del fact debe ser HuellaChile."}
        )
    return normalized, compatibility


@transaction.atomic
def apply_candidate_mapping(candidate, user, mapping_type, context, note=""):
    normalized, compatibility = validate_candidate_mapping(
        candidate, mapping_type, context
    )
    candidate.mapping_type = mapping_type
    candidate.mapping_context = normalized
    candidate.compatibility = compatibility
    candidate.reviewed_by = user
    candidate.reviewed_at = timezone.now()
    candidate.review_note = note
    candidate.status = candidate.Status.READY
    candidate.save()
    return candidate


def equivalent_global_factors(candidate):
    context = candidate.mapping_context or {}
    compatibility = candidate.compatibility or {}
    matches = []
    for factor in FactorAmbiental.objects.filter(organizacion__isnull=True):
        current = factor.contexto or {}
        if candidate.mapping_type == "combustible":
            same = all(
                current.get(field) == context.get(field)
                for field in ("proveedor", "alcance", "categoria_huella", "combustible")
            )
        elif candidate.mapping_type == "energia_red":
            same = all(
                current.get(field) == context.get(field)
                for field in ("alcance", "sistema", "metodo", "pais")
            )
        else:
            same = False
        if (
            same
            and factor.unidad_entrada == compatibility.get("normalized_input_unit")
            and _result_units_equivalent(
                factor.unidad_resultado, compatibility.get("normalized_result_unit")
            )
        ):
            matches.append(factor)
    return {
        "status": (
            "sin_equivalente"
            if not matches
            else "equivalente_unico" if len(matches) == 1 else "conflicto_multiple"
        ),
        "factors": matches,
    }


@transaction.atomic
def promote_candidate_to_draft(candidate, user, mode, target_factor=None):
    candidate = (
        EnvironmentalFactorCandidate.objects.select_for_update()
        .select_related("source_fact__artifact__parent_record")
        .get(pk=candidate.pk)
    )
    if not user.is_superuser:
        raise ValidationError("Sólo un superusuario puede promover factores globales.")
    _ensure_current_source(candidate)
    if candidate.status != candidate.Status.READY or candidate.promoted_version_id:
        raise ValidationError("El candidato no está listo o ya fue promovido.")
    normalized, compatibility = validate_candidate_mapping(
        candidate, candidate.mapping_type, candidate.mapping_context
    )
    equivalence = equivalent_global_factors(candidate)
    if equivalence["status"] == "conflicto_multiple":
        raise ValidationError("Existen múltiples factores globales equivalentes.")
    fact = candidate.source_fact
    if mode == "create_global":
        if equivalence["factors"]:
            raise ValidationError(
                "Ya existe un factor global equivalente; seleccione new_version explícitamente."
            )
        factor = FactorAmbiental.objects.create(
            organizacion=None,
            codigo=f"fhg-{uuid4().hex}",
            nombre=f"HuellaChile · {fact.actividad}",
            categoria=(
                normalized["categoria_huella"]
                if candidate.mapping_type == "combustible"
                else "electricidad_red"
            ),
            sustancia_impacto="CO2e",
            unidad_entrada=compatibility["normalized_input_unit"],
            unidad_resultado=compatibility["normalized_result_unit"],
            contexto=normalized,
        )
        version_number = 1
    elif mode == "new_version":
        if (
            not target_factor
            or target_factor.organizacion_id is not None
            or target_factor not in equivalence["factors"]
        ):
            raise ValidationError(
                "El factor objetivo no es el equivalente global validado."
            )
        factor = FactorAmbiental.objects.select_for_update().get(pk=target_factor.pk)
        version_number = (
            factor.versiones.order_by("-version")
            .values_list("version", flat=True)
            .first()
            or 0
        ) + 1
    else:
        raise ValidationError({"mode": "Modo explícito inválido."})
    provenance = {
        "provider": "HuellaChile",
        **candidate_provenance(fact),
        "technical_sources": [
            fact.technical_source_1,
            fact.technical_source_2,
            fact.technical_source_3,
        ],
    }
    value = _factor_value_for_unit(
        fact.factor_value,
        compatibility["normalized_result_unit"],
        factor.unidad_resultado,
    )
    provenance.update(
        {
            "published_unit": (
                f"{compatibility['normalized_result_unit']}/"
                f"{compatibility['normalized_input_unit']}"
            ),
            "normalized_value": str(value),
            "normalized_unit": (f"{factor.unidad_resultado}/{factor.unidad_entrada}"),
        }
    )
    version = VersionFactorAmbiental.objects.create(
        factor=factor,
        version=version_number,
        valor=value,
        fuente="Programa HuellaChile / Ministerio del Medio Ambiente",
        referencia=f"Base de datos factores de emisión {fact.dataset_year}; {fact.sheet_name}, fila {fact.source_row_number}.",
        region=normalized.get("pais", "Chile"),
        contexto={**normalized, "knowledge_source": provenance},
        estado=VersionFactorAmbiental.Estado.BORRADOR,
    )
    candidate.mapping_context = normalized
    candidate.compatibility = compatibility
    candidate.promoted_factor = factor
    candidate.promoted_version = version
    candidate.reviewed_by = user
    candidate.reviewed_at = timezone.now()
    candidate.status = candidate.Status.PROMOTED
    candidate.save()
    return factor, version
