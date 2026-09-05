from datetime import date

from django.core.exceptions import ImproperlyConfigured
from django.db import connection, transaction

from ..models import (
    FactorAmbiental,
    FormulaAmbiental,
    MetodologiaAmbiental,
    VariableFormula,
    VersionMetodologia,
)
from .methodology_governance import transition_version

SYSTEM_ENVIRONMENTAL_CATALOG_VERSION = 4
SYSTEM_CATALOG_LOCK_ID = 739_204_101

SYSTEM_FACTOR_IDENTITIES = (
    (
        "huellachile-combustion-estacionaria-glp",
        "HuellaChile · Combustión estacionaria · GLP",
        "combustion_estacionaria",
        "m3",
        "tCO2e",
        {
            "proveedor": "HuellaChile",
            "alcance": 1,
            "categoria_huella": "combustion_estacionaria",
            "combustible": "glp",
        },
    ),
    (
        "huellachile-combustion-estacionaria-gas-natural",
        "HuellaChile · Combustión estacionaria · Gas natural",
        "combustion_estacionaria",
        "m3",
        "kgCO2e",
        {
            "proveedor": "HuellaChile",
            "alcance": 1,
            "categoria_huella": "combustion_estacionaria",
            "combustible": "gas_natural",
        },
    ),
    (
        "huellachile-combustion-estacionaria-diesel",
        "HuellaChile · Combustión estacionaria · Diésel",
        "combustion_estacionaria",
        "m3",
        "tCO2e",
        {
            "proveedor": "HuellaChile",
            "alcance": 1,
            "categoria_huella": "combustion_estacionaria",
            "combustible": "diesel",
        },
    ),
    (
        "huellachile-combustion-movil-glp",
        "HuellaChile · Combustión móvil · GLP",
        "combustion_movil",
        "m3",
        "tCO2e",
        {
            "proveedor": "HuellaChile",
            "alcance": 1,
            "categoria_huella": "combustion_movil",
            "combustible": "glp",
        },
    ),
    (
        "huellachile-combustion-movil-gas-natural",
        "HuellaChile · Combustión móvil · Gas natural",
        "combustion_movil",
        "m3",
        "tCO2e",
        {
            "proveedor": "HuellaChile",
            "alcance": 1,
            "categoria_huella": "combustion_movil",
            "combustible": "gas_natural",
        },
    ),
    (
        "huellachile-combustion-movil-diesel",
        "HuellaChile · Combustión móvil · Diésel",
        "combustion_movil",
        "m3",
        "tCO2e",
        {
            "proveedor": "HuellaChile",
            "alcance": 1,
            "categoria_huella": "combustion_movil",
            "combustible": "diesel",
        },
    ),
    (
        "sen-electricidad-red-location-based-2025",
        "SEN Chile · electricidad de red location-based",
        "electricidad_red",
        "MWh",
        "tCO2e",
        {"alcance": 2, "sistema": "SEN", "metodo": "location_based", "pais": "Chile"},
    ),
)

FUEL_METHODOLOGY_CODE = "construccion-v1-combustible-consumido"
ENERGY_METHODOLOGY_CODE = "construccion-v1-electricidad-red-sen"
TRANSPORT_FUEL_METHODOLOGY_CODE = "construccion-v1-transporte-combustible"
MATERIAL_METHODOLOGY_CODE = "construccion-v1-material-recibido"
ENERGY_FACTOR_CODE = "sen-electricidad-red-location-based-2025"
ENERGY_REFERENCE = "Construcción V1; factor SEN seleccionado desde gobernanza."


def _assert_contract(instance, expected, label):
    differences = [
        field for field, value in expected.items() if getattr(instance, field) != value
    ]
    if differences:
        raise ImproperlyConfigured(
            f"Contrato global incompatible para {label}: {', '.join(differences)}. "
            "No se modificaron datos gobernados."
        )


def _ensure_factor_identity(*, code, factor_fields):
    factor, created = FactorAmbiental.objects.get_or_create(
        organizacion=None, codigo=code, defaults=factor_fields
    )
    if not created:
        _assert_contract(
            factor,
            {
                key: value
                for key, value in factor_fields.items()
                if key not in {"nombre", "contexto"}
            },
            code,
        )
        current = factor.contexto or {}
        contradictions = [
            key
            for key, value in factor_fields["contexto"].items()
            if key in current and current[key] != value
        ]
        if contradictions:
            raise ImproperlyConfigured(
                f"Contrato semántico incompatible para {code}: {', '.join(contradictions)}."
            )
    return factor


@transaction.atomic
def ensure_huellachile_factor_catalog():
    _lock_system_catalog()
    factors = []
    for (
        code,
        name,
        category,
        input_unit,
        result_unit,
        context,
    ) in SYSTEM_FACTOR_IDENTITIES:
        factors.append(
            _ensure_factor_identity(
                code=code,
                factor_fields={
                    "nombre": name,
                    "categoria": category,
                    "sustancia_impacto": "CO2e",
                    "unidad_entrada": input_unit,
                    "unidad_resultado": result_unit,
                    "contexto": context,
                },
            )
        )
    return factors


def _ensure_methodology(
    *, code, methodology_fields, version_fields, formula_fields, variable_fields
):
    methodology, created = MetodologiaAmbiental.objects.get_or_create(
        organizacion=None, codigo=code, defaults=methodology_fields
    )
    if not created:
        _assert_contract(methodology, methodology_fields, code)
    version, created = VersionMetodologia.objects.get_or_create(
        metodologia=methodology, version=1, defaults=version_fields
    )
    if not created:
        _assert_contract(version, version_fields, f"{code} v1")
    formula, created = FormulaAmbiental.objects.get_or_create(
        version_metodologia=version, defaults=formula_fields
    )
    if not created:
        _assert_contract(formula, formula_fields, f"formula {code} v1")
    variable, created = VariableFormula.objects.get_or_create(
        formula=formula, clave=variable_fields["clave"], defaults=variable_fields
    )
    if not created:
        _assert_contract(variable, variable_fields, f"variable {code} v1")
    for target in (
        VersionMetodologia.Estado.PRUEBAS,
        VersionMetodologia.Estado.VALIDADA,
        VersionMetodologia.Estado.ACTIVA,
    ):
        if version.estado in {target, VersionMetodologia.Estado.ACTIVA}:
            continue
        version = transition_version(version, target)
    return methodology, version


@transaction.atomic
def ensure_construction_v1_methodologies():
    _lock_system_catalog()
    fuel_reference = (
        "Construccion V1; factores seleccionados desde el catalogo gobernado "
        "HuellaChile segun clasificacion, combustible, unidad y fecha."
    )
    fuel = _ensure_methodology(
        code=FUEL_METHODOLOGY_CODE,
        methodology_fields={
            "nombre": "Construccion V1 - combustible consumido",
            "categoria": "combustibles",
            "flujo": "combustible",
            "descripcion": "Calculo generico de combustible consumido por factor dinamico.",
            "activa": True,
        },
        version_fields={
            "descripcion_tecnica": "Emision = combustible consumido normalizado x factor aplicable.",
            "fuente_referencia": fuel_reference,
            "vigencia_desde": None,
            "vigencia_hasta": None,
            "aplicabilidad": {
                "tipos_actividad": [
                    "consumo_combustible",
                    "consumo_combustible_estacionario",
                ],
                "flujos": [
                    "combustible",
                    "combustible_estacionario",
                    "combustible_movil",
                ],
            },
            "prioridad": 10,
            "requiere_revision_profesional": False,
            "tipo_resultado": "emision",
        },
        formula_fields={
            "factor_ambiental": None,
            "codigo": "construccion-v1-combustible-consumido-v1",
            "tipo": FormulaAmbiental.Tipo.COMBUSTIBLE_CONSUMIDO,
            "expresion_legible": "combustible_consumido x factor_seleccionado",
            "version": 1,
        },
        variable_fields={
            "clave": "combustible_consumido",
            "concepto_observacion": "combustible_consumido",
            "unidad_esperada": "m3",
            "obligatoria": True,
            "criticidad": VariableFormula.Criticidad.CRITICA,
            "rol": VariableFormula.Rol.ACTIVIDAD,
            "descripcion": "Volumen de combustible consumido.",
        },
    )

    transport_fuel = _ensure_methodology(
        code=TRANSPORT_FUEL_METHODOLOGY_CODE,
        methodology_fields={
            "nombre": "Construccion V1 - transporte por combustible consumido",
            "categoria": "transporte",
            "flujo": "transporte_combustible",
            "descripcion": "Emisiones de transporte por combustible realmente consumido.",
            "activa": True,
        },
        version_fields={
            "descripcion_tecnica": "Emision = combustible del viaje normalizado x factor movil aplicable.",
            "fuente_referencia": fuel_reference,
            "vigencia_desde": None,
            "vigencia_hasta": None,
            "aplicabilidad": {"tipos_actividad": ["transporte"]},
            "prioridad": 100,
            "requiere_revision_profesional": False,
            "tipo_resultado": "emision",
        },
        formula_fields={
            "factor_ambiental": None,
            "codigo": "construccion-v1-transporte-combustible-v1",
            "tipo": FormulaAmbiental.Tipo.TRANSPORTE_COMBUSTIBLE,
            "expresion_legible": "combustible x factor_movil_seleccionado",
            "version": 1,
        },
        variable_fields={
            "clave": "combustible",
            "concepto_observacion": "combustible_consumido_l",
            "unidad_esperada": "m3",
            "obligatoria": True,
            "criticidad": VariableFormula.Criticidad.CRITICA,
            "rol": VariableFormula.Rol.ACTIVIDAD,
            "descripcion": "Volumen de combustible consumido por el viaje.",
        },
    )

    energy_factor = FactorAmbiental.objects.get(
        organizacion=None, codigo=ENERGY_FACTOR_CODE
    )
    energy = _ensure_methodology(
        code=ENERGY_METHODOLOGY_CODE,
        methodology_fields={
            "nombre": "Construccion V1 - electricidad de red SEN",
            "categoria": "energia",
            "flujo": "energia",
            "descripcion": "Emisiones GEI indirectas por electricidad consumida de la red.",
            "activa": True,
        },
        version_fields={
            "descripcion_tecnica": "Emision Scope 2 location-based = energia consumida normalizada x factor SEN.",
            "fuente_referencia": ENERGY_REFERENCE,
            "vigencia_desde": date(2026, 1, 1),
            "vigencia_hasta": None,
            "aplicabilidad": {
                "tipos_actividad": ["consumo_energia"],
                "flujos": ["energia"],
                "tipos_recurso": ["red_electrica"],
            },
            "prioridad": 10,
            "requiere_revision_profesional": False,
            "tipo_resultado": "emision",
        },
        formula_fields={
            "factor_ambiental": energy_factor,
            "codigo": "construccion-v1-electricidad-red-sen-v1",
            "tipo": FormulaAmbiental.Tipo.ENERGIA_CONSUMIDA,
            "expresion_legible": "energia_consumida x factor_electrico_sen",
            "version": 1,
        },
        variable_fields={
            "clave": "energia_consumida",
            "concepto_observacion": "consumo_energia",
            "unidad_esperada": "MWh",
            "obligatoria": True,
            "criticidad": VariableFormula.Criticidad.CRITICA,
            "rol": VariableFormula.Rol.ACTIVIDAD,
            "descripcion": "Electricidad consumida desde la red.",
        },
    )
    material = _ensure_methodology(
        code=MATERIAL_METHODOLOGY_CODE,
        methodology_fields={
            "nombre": "Construccion V1 - material recibido",
            "categoria": "materiales",
            "flujo": "materiales",
            "descripcion": "Impacto del material en su recepcion fisica en obra, sin volver a contabilizar su uso.",
            "activa": True,
        },
        version_fields={
            "descripcion_tecnica": "Emision = cantidad recibida normalizada x factor de material aplicable.",
            "fuente_referencia": "Construccion V1; factor de material seleccionado dinamicamente desde gobernanza.",
            "vigencia_desde": None,
            "vigencia_hasta": None,
            "aplicabilidad": {
                "tipos_actividad": ["movimiento_material"],
                "tipos_evento_material": ["recepcion"],
            },
            "prioridad": 10,
            "requiere_revision_profesional": False,
            "tipo_resultado": "emision",
        },
        formula_fields={
            "factor_ambiental": None,
            "codigo": "construccion-v1-material-recibido-v1",
            "tipo": FormulaAmbiental.Tipo.MATERIAL_CANTIDAD,
            "expresion_legible": "cantidad_material_normalizada x factor_material",
            "version": 1,
        },
        variable_fields={
            "clave": "cantidad_material_normalizada",
            "concepto_observacion": "cantidad_material",
            "unidad_esperada": "kg",
            "obligatoria": True,
            "criticidad": VariableFormula.Criticidad.CRITICA,
            "rol": VariableFormula.Rol.ACTIVIDAD,
            "descripcion": "Cantidad fisica recibida, normalizada a la unidad del factor seleccionado.",
        },
    )
    return fuel, energy, transport_fuel, material


def _lock_system_catalog():
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [SYSTEM_CATALOG_LOCK_ID])


@transaction.atomic
def ensure_system_environmental_catalog():
    _lock_system_catalog()
    factors = ensure_huellachile_factor_catalog()
    methodologies = ensure_construction_v1_methodologies()
    return {
        "catalog_version": SYSTEM_ENVIRONMENTAL_CATALOG_VERSION,
        "huellachile_factors": len(factors),
        "methodologies": len(methodologies),
    }
