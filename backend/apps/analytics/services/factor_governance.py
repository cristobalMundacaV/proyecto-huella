from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import FactorAmbiental, VersionFactorAmbiental

TRANSITIONS = {
    "borrador": {"pruebas"},
    "pruebas": {"borrador", "validado"},
    "validado": {"activo"},
    "activo": {"obsoleto"},
    "obsoleto": set(),
}
MATERIAL_UNITS = {"kg", "t", "m3", "L", "unidad"}
RESULT_UNITS = {"kgCO2e", "tCO2e"}
SOURCE_TYPES = {"epd", "base_oficial", "organizacion", "otra_fuente_tecnica"}
LIFE_CYCLES = {"A1-A3", "A1-A5", "otro_declarado"}


def _version_data(payload, context):
    required = ("valor", "fuente", "referencia")
    missing = [field for field in required if not str(payload.get(field, "")).strip()]
    if missing:
        raise ValidationError(
            {field: "Este campo es obligatorio." for field in missing}
        )
    if (
        payload.get("vigencia_desde")
        and payload.get("vigencia_hasta")
        and payload["vigencia_desde"] > payload["vigencia_hasta"]
    ):
        raise ValidationError(
            {
                "vigencia_hasta": "La vigencia hasta no puede ser anterior a la vigencia desde."
            }
        )
    return {
        "valor": payload["valor"],
        "fuente": payload["fuente"].strip(),
        "referencia": payload["referencia"].strip(),
        "region": payload.get("region", "").strip(),
        "vigencia_desde": payload.get("vigencia_desde") or None,
        "vigencia_hasta": payload.get("vigencia_hasta") or None,
        "contexto": context,
        "estado": VersionFactorAmbiental.Estado.BORRADOR,
    }


@transaction.atomic
def create_private_material_factor(organization, material, payload):
    unit = payload.get("unidad_entrada")
    result_unit = payload.get("unidad_resultado")
    source_type = payload.get("fuente_tipo")
    life_cycle = payload.get("alcance_ciclo_vida")
    errors = {}
    if unit not in MATERIAL_UNITS:
        errors["unidad_entrada"] = "Unidad no soportada."
    if result_unit not in RESULT_UNITS:
        errors["unidad_resultado"] = "Unidad de resultado no soportada."
    if source_type not in SOURCE_TYPES:
        errors["fuente_tipo"] = "Tipo de fuente no soportado."
    if life_cycle not in LIFE_CYCLES:
        errors["alcance_ciclo_vida"] = "Alcance no soportado."
    if errors:
        raise ValidationError(errors)
    context = {
        "material_codigo": material.codigo,
        "material_categoria": material.categoria,
        "producto": material.nombre,
        "proveedor": material.proveedor_fabricante or "",
        "especificidad": "producto",
        "alcance_ciclo_vida": life_cycle,
        "fuente_tipo": source_type,
    }
    factor = FactorAmbiental.objects.create(
        organizacion=organization,
        codigo=f"FAM-{uuid4().hex.upper()}",
        nombre=(payload.get("nombre") or f"Factor de {material.nombre}").strip(),
        categoria="materiales",
        sustancia_impacto="CO2e",
        unidad_entrada=unit,
        unidad_resultado=result_unit,
        contexto=context,
    )
    VersionFactorAmbiental.objects.create(
        factor=factor, version=1, **_version_data(payload, context)
    )
    return factor


@transaction.atomic
def create_factor_version(factor, payload):
    latest = factor.versiones.order_by("-version").first()
    return VersionFactorAmbiental.objects.create(
        factor=factor,
        version=(latest.version if latest else 0) + 1,
        **_version_data(payload, factor.contexto or {}),
    )


@transaction.atomic
def transition_factor_version(version, target):
    version = (
        VersionFactorAmbiental.objects.select_for_update()
        .select_related("factor")
        .get(pk=version.pk)
    )
    if target not in TRANSITIONS.get(version.estado, set()):
        raise ValidationError(f"Transicion no permitida: {version.estado} -> {target}.")
    if target == VersionFactorAmbiental.Estado.ACTIVO:
        if (
            version.factor.versiones.filter(estado=VersionFactorAmbiental.Estado.ACTIVO)
            .exclude(pk=version.pk)
            .exists()
        ):
            raise ValidationError(
                "El factor ya tiene una version activa; debe volverla obsoleta antes de activar otra."
            )
        factor = version.factor
        context = factor.contexto or {}
        if factor.organizacion_id is None and context.get("proveedor") == "HuellaChile":
            if context.get("categoria_huella"):
                fields = ("proveedor", "alcance", "categoria_huella", "combustible")
            elif context.get("sistema"):
                fields = ("proveedor", "alcance", "sistema", "metodo", "pais")
            else:
                fields = ()
            conflicts = (
                FactorAmbiental.objects.select_for_update()
                .filter(
                    organizacion__isnull=True,
                    unidad_entrada=factor.unidad_entrada,
                    versiones__estado=VersionFactorAmbiental.Estado.ACTIVO,
                )
                .exclude(pk=factor.pk)
            )
            for other in conflicts.distinct():
                other_context = other.contexto or {}
                result_units_match = {
                    factor.unidad_resultado,
                    other.unidad_resultado,
                }.issubset(RESULT_UNITS)
                if (
                    fields
                    and result_units_match
                    and all(
                        context.get(field) == other_context.get(field)
                        for field in fields
                    )
                ):
                    raise ValidationError(
                        "Ya existe otro factor global HuellaChile activo con la misma identidad semantica."
                    )
    VersionFactorAmbiental.objects.filter(pk=version.pk).update(estado=target)
    version.refresh_from_db()
    return version
