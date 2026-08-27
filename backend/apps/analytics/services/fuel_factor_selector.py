from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from ..models import VersionFactorAmbiental
from .unit_conversion import UnitConversionError, canonicalize_unit


REQUIRED_CONTEXT_FIELDS = ("alcance", "categoria_huella", "combustible")


def _evaluation_date(value):
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.date()
    return value


def _candidate(version, organization, category, fuel, required_unit, on_date):
    factor = version.factor
    context = factor.contexto if isinstance(factor.contexto, dict) else {}
    if factor.organizacion_id == organization.id:
        origin = "tenant"
    elif context.get("proveedor") == "HuellaChile":
        origin = "huellachile"
    else:
        origin = "global"
    reasons = []

    if version.estado != VersionFactorAmbiental.Estado.ACTIVO:
        reasons.append("La versión no está activa.")
    missing = [field for field in REQUIRED_CONTEXT_FIELDS if field not in context]
    if missing:
        reasons.append(f"Falta metadata obligatoria: {', '.join(missing)}.")
    else:
        if context["alcance"] != 1:
            reasons.append("El alcance no corresponde a alcance 1.")
        if context["categoria_huella"] != category:
            reasons.append("La categoría ambiental no coincide.")
        if str(context["combustible"]).strip().casefold() != fuel:
            reasons.append("El combustible no coincide.")
    if origin == "global":
        reasons.append("El factor global no pertenece a HuellaChile.")
    if version.vigencia_desde and version.vigencia_desde > on_date:
        reasons.append("La versión aún no estaba vigente en la fecha de la actividad.")
    if version.vigencia_hasta and version.vigencia_hasta < on_date:
        reasons.append("La versión ya no estaba vigente en la fecha de la actividad.")

    try:
        factor_unit = canonicalize_unit(factor.unidad_entrada)
        canonical_required_unit = canonicalize_unit(required_unit)
    except UnitConversionError as error:
        reasons.append(str(error))
    else:
        if factor_unit != canonical_required_unit:
            reasons.append(
                f"Unidad incompatible: el factor utiliza {factor_unit} y se requiere "
                f"{canonical_required_unit}."
            )

    return {
        "factor_id": factor.id,
        "version_id": version.id,
        "origen": origin,
        "estado": "descartado" if reasons else "aplicable",
        "motivos": reasons,
    }


def _result(state, reason, candidates, factor_version=None, origin=None):
    return {
        "estado": state,
        "factor_version": factor_version,
        "origen": origin,
        "razon": reason,
        "candidatos": candidates,
    }


def select_fuel_factor(
    organization,
    classification,
    fuel,
    required_unit,
    on_date,
):
    classification = classification if isinstance(classification, dict) else {}
    if classification.get("estado") != "clasificado":
        return _result(
            "no_calculable",
            "El combustible debe estar clasificado antes de seleccionar un factor.",
            [],
        )

    category = classification.get("categoria")
    normalized_fuel = str(fuel or "").strip().casefold()
    evaluation_date = _evaluation_date(on_date)
    if not category or not normalized_fuel or not required_unit or not evaluation_date:
        return _result(
            "no_calculable",
            "Falta categoría, combustible, unidad requerida o fecha operacional.",
            [],
        )

    versions = (
        VersionFactorAmbiental.objects.filter(
            Q(factor__organizacion=organization)
            | Q(factor__organizacion__isnull=True)
        )
        .select_related("factor")
        .order_by("factor_id", "version", "id")
    )
    evaluated = [
        (version, _candidate(
            version,
            organization,
            category,
            normalized_fuel,
            required_unit,
            evaluation_date,
        ))
        for version in versions
    ]
    candidates = [candidate for _, candidate in evaluated]
    tenant = [
        version
        for version, candidate in evaluated
        if candidate["estado"] == "aplicable" and candidate["origen"] == "tenant"
    ]
    if len(tenant) > 1:
        return _result(
            "requiere_revision",
            "Existen múltiples factores privados activos y aplicables.",
            candidates,
        )
    if len(tenant) == 1:
        return _result(
            "seleccionado",
            "Se seleccionó un factor privado activo y aplicable del tenant.",
            candidates,
            tenant[0],
            "tenant",
        )

    huellachile = [
        version
        for version, candidate in evaluated
        if candidate["estado"] == "aplicable"
        and candidate["origen"] == "huellachile"
    ]
    if len(huellachile) > 1:
        return _result(
            "requiere_revision",
            "Existen múltiples factores HuellaChile activos y aplicables.",
            candidates,
        )
    if len(huellachile) == 1:
        return _result(
            "seleccionado",
            "No existe un factor tenant aplicable; se utilizó HuellaChile.",
            candidates,
            huellachile[0],
            "huellachile",
        )
    return _result(
        "no_calculable",
        f"No existe un factor activo y aplicable para {normalized_fuel} en {category}.",
        candidates,
    )
