from django.db.models import Q

from ..models import VersionFactorAmbiental
from .unit_conversion import UnitConversionError, convert_value


def _specificity(version, material):
    factor = version.factor
    context = {**(factor.contexto or {}), **(version.contexto or {})}
    supplier = context.get("proveedor")
    if supplier and supplier.casefold() != (material.proveedor_fabricante or "").casefold():
        return None
    if context.get("material_codigo") == material.codigo or context.get("producto", "").casefold() == material.nombre.casefold():
        return "producto"
    if context.get("especificidad") == "categoria" and context.get("material_categoria") == material.categoria:
        return "categoria"
    return None


def select_material_factor(organization, material, source_unit, effective_date):
    versions = VersionFactorAmbiental.objects.filter(
        estado=VersionFactorAmbiental.Estado.ACTIVO,
    ).filter(
        Q(factor__organizacion=organization) | Q(factor__organizacion__isnull=True),
        Q(vigencia_desde__isnull=True) | Q(vigencia_desde__lte=effective_date),
        Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=effective_date),
    ).select_related("factor")
    candidates = []
    for version in versions:
        specificity = _specificity(version, material)
        if not specificity:
            continue
        try:
            convert_value(1, source_unit, version.factor.unidad_entrada)
        except UnitConversionError:
            continue
        rank = (0 if version.factor.organizacion_id else 2) + (0 if specificity == "producto" else 1)
        candidates.append((rank, -version.version, version, specificity))
    candidates.sort(key=lambda item: (item[0], item[1], item[2].pk))
    if not candidates:
        return {"factor_version": None, "especificidad": None, "razon": f"No existe un factor ambiental gobernado aplicable a {material.nombre}."}
    _, _, version, specificity = candidates[0]
    return {"factor_version": version, "especificidad": specificity, "razon": "Factor de material seleccionado por alcance y especificidad gobernados."}
