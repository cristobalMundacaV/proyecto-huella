from django.db.models import Q
from django.utils import timezone

from ..models import VersionFactorAmbiental


def _applicable_versions(organization, category, fuel, on_date):
    return (
        VersionFactorAmbiental.objects.filter(
            estado=VersionFactorAmbiental.Estado.ACTIVO,
            factor__contexto__alcance=1,
            factor__contexto__categoria_huella=category,
            factor__contexto__combustible=fuel,
        )
        .filter(
            Q(factor__organizacion=organization)
            | Q(
                factor__organizacion__isnull=True,
                factor__contexto__proveedor="HuellaChile",
            )
        )
        .filter(
            Q(vigencia_desde__isnull=True) | Q(vigencia_desde__lte=on_date),
            Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=on_date),
        )
        .select_related("factor")
    )


def select_fuel_factor(organization, classification, fuel, on_date=None):
    classification = classification if isinstance(classification, dict) else {}
    if classification.get("estado") != "clasificado":
        return {
            "estado": "no_calculable",
            "factor_version": None,
            "origen": None,
            "razon": "El combustible debe estar clasificado antes de seleccionar un factor.",
        }

    category = classification.get("categoria")
    normalized_fuel = str(fuel or "").strip().casefold()
    if not category or not normalized_fuel:
        return {
            "estado": "no_calculable",
            "factor_version": None,
            "origen": None,
            "razon": "Falta la categoría ambiental o el tipo de combustible.",
        }

    versions = _applicable_versions(
        organization,
        category,
        normalized_fuel,
        on_date or timezone.localdate(),
    )
    tenant_version = versions.filter(factor__organizacion=organization).order_by(
        "-version", "-id"
    ).first()
    if tenant_version:
        return {
            "estado": "seleccionado",
            "factor_version": tenant_version,
            "origen": "tenant",
            "razon": "Se seleccionó un factor privado activo y aplicable del tenant.",
        }

    global_version = versions.filter(factor__organizacion__isnull=True).order_by(
        "-version", "-id"
    ).first()
    if global_version:
        return {
            "estado": "seleccionado",
            "factor_version": global_version,
            "origen": "huellachile",
            "razon": "No existe un factor tenant aplicable; se utilizó HuellaChile.",
        }

    return {
        "estado": "no_calculable",
        "factor_version": None,
        "origen": None,
        "razon": (
            f"No existe un factor activo y aplicable para {normalized_fuel} "
            f"en {category}."
        ),
    }
