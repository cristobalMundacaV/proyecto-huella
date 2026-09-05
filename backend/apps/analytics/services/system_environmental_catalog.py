from datetime import date
from decimal import Decimal

from django.core.exceptions import ImproperlyConfigured
from django.db import connection, transaction

from ..models import (
    FactorAmbiental,
    FormulaAmbiental,
    MetodologiaAmbiental,
    VariableFormula,
    VersionFactorAmbiental,
    VersionMetodologia,
)
from .methodology_governance import transition_version


SYSTEM_ENVIRONMENTAL_CATALOG_VERSION = 3
SYSTEM_CATALOG_LOCK_ID = 739_204_101

HUELLACHILE_SOURCE = "Programa HuellaChile - Ministerio del Medio Ambiente"
HUELLACHILE_DOCUMENT = "Factores de emisión para el cálculo de la huella de carbono - Nivel básico"
HUELLACHILE_REFERENCE = f"{HUELLACHILE_DOCUMENT} - Versión 3 - 28/11/2024"
HUELLACHILE_FACTORS = (
    ("combustion_estacionaria", "glp", "Gas Licuado de Petróleo (GLP)", "1.59", "tCO2e"),
    ("combustion_estacionaria", "gas_natural", "Gas Natural", "1.98", "kgCO2e"),
    ("combustion_estacionaria", "diesel", "Diésel", "2.71", "tCO2e"),
    ("combustion_movil", "glp", "Gas Licuado de Petróleo (GLP)", "1.72", "tCO2e"),
    ("combustion_movil", "gas_natural", "Gas Natural", "2.09", "tCO2e"),
    ("combustion_movil", "diesel", "Diésel", "2.74", "tCO2e"),
)

FUEL_METHODOLOGY_CODE = "construccion-v1-combustible-consumido"
ENERGY_METHODOLOGY_CODE = "construccion-v1-electricidad-red-sen"
TRANSPORT_FUEL_METHODOLOGY_CODE = "construccion-v1-transporte-combustible"
MATERIAL_METHODOLOGY_CODE = "construccion-v1-material-recibido"
ENERGY_FACTOR_CODE = "sen-electricidad-red-location-based-2025"
ENERGY_SOURCE = "Programa HuellaChile / Ministerio del Medio Ambiente"
ENERGY_REFERENCE = (
    "Recomendacion HuellaChile publicada en 2026: factor oficial 2025 del "
    "Ministerio de Energia, usado como ultima referencia oficial disponible "
    "para registros 2026 hasta disponer de una version posterior gobernada."
)


def _assert_contract(instance, expected, label):
    differences = [
        field for field, value in expected.items() if getattr(instance, field) != value
    ]
    if differences:
        raise ImproperlyConfigured(
            f"Contrato global incompatible para {label}: {', '.join(differences)}. "
            "No se modificaron datos gobernados."
        )


def _ensure_factor(*, code, factor_fields, version, version_fields):
    factor, created = FactorAmbiental.objects.get_or_create(
        organizacion=None, codigo=code, defaults=factor_fields
    )
    if not created:
        _assert_contract(factor, factor_fields, code)
    factor_version, created = VersionFactorAmbiental.objects.get_or_create(
        factor=factor, version=version, defaults=version_fields
    )
    if not created:
        _assert_contract(factor_version, version_fields, f"{code} v{version}")
    return factor, factor_version


@transaction.atomic
def ensure_huellachile_factor_catalog():
    _lock_system_catalog()
    factors = []
    for category, fuel, label, value, result_unit in HUELLACHILE_FACTORS:
        code = f"huellachile-{category.replace('_', '-')}-{fuel.replace('_', '-')}"
        context = {
            "proveedor": "HuellaChile",
            "documento": HUELLACHILE_DOCUMENT,
            "documento_version": 3,
            "fecha_actualizacion": "2024-11-28",
            "alcance": 1,
            "categoria_huella": category,
            "combustible": fuel,
        }
        factors.append(
            _ensure_factor(
                code=code,
                factor_fields={
                    "nombre": f"HuellaChile · {category.replace('_', ' ').title()} · {label}",
                    "categoria": category,
                    "sustancia_impacto": "CO2e",
                    "unidad_entrada": "m3",
                    "unidad_resultado": result_unit,
                    "contexto": context,
                },
                version=1,
                version_fields={
                    "valor": Decimal(value),
                    "fuente": HUELLACHILE_SOURCE,
                    "referencia": HUELLACHILE_REFERENCE,
                    "region": "Chile",
                    "vigencia_desde": None,
                    "vigencia_hasta": None,
                    "contexto": context,
                    "estado": VersionFactorAmbiental.Estado.ACTIVO,
                },
            )
        )
    return factors


def _ensure_methodology(*, code, methodology_fields, version_fields, formula_fields, variable_fields):
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
                "tipos_actividad": ["consumo_combustible", "consumo_combustible_estacionario"],
                "flujos": ["combustible", "combustible_estacionario", "combustible_movil"],
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

    energy_context = {
        "factor_year": 2025,
        "sistema": "SEN",
        "metodo": "location_based",
        "alcance": 2,
        "pais": "Chile",
        "fuente_original": "Ministerio de Energia",
    }
    energy_factor, _ = _ensure_factor(
        code=ENERGY_FACTOR_CODE,
        factor_fields={
            "nombre": "SEN Chile - electricidad de red location-based - factor 2025",
            "categoria": "electricidad_red",
            "sustancia_impacto": "CO2e",
            "unidad_entrada": "MWh",
            "unidad_resultado": "tCO2e",
            "contexto": energy_context,
        },
        version=1,
        version_fields={
            "valor": Decimal("0.2466"),
            "fuente": ENERGY_SOURCE,
            "referencia": ENERGY_REFERENCE,
            "region": "Chile",
            "vigencia_desde": date(2026, 1, 1),
            "vigencia_hasta": None,
            "contexto": energy_context,
            "estado": VersionFactorAmbiental.Estado.ACTIVO,
        },
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
            "vigencia_desde": None, "vigencia_hasta": None,
            "aplicabilidad": {"tipos_actividad": ["movimiento_material"]},
            "prioridad": 10, "requiere_revision_profesional": False, "tipo_resultado": "emision",
        },
        formula_fields={
            "factor_ambiental": None,
            "codigo": "construccion-v1-material-recibido-v1",
            "tipo": FormulaAmbiental.Tipo.MATERIAL_CANTIDAD,
            "expresion_legible": "cantidad_material_normalizada x factor_material",
            "version": 1,
        },
        variable_fields={
            "clave": "cantidad_material_normalizada", "concepto_observacion": "cantidad_material",
            "unidad_esperada": "kg", "obligatoria": True,
            "criticidad": VariableFormula.Criticidad.CRITICA, "rol": VariableFormula.Rol.ACTIVIDAD,
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
