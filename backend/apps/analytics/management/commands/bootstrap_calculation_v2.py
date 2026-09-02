from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import (
    FormulaAmbiental,
    FactorAmbiental,
    MetodologiaAmbiental,
    VariableFormula,
    VersionFactorAmbiental,
    VersionMetodologia,
)
from ...services.methodology_governance import transition_version


METHODOLOGY_CODE = "construccion-v1-combustible-consumido"
SOURCE_REFERENCE = (
    "Construccion V1; factores seleccionados desde el catalogo gobernado "
    "HuellaChile segun clasificacion, combustible, unidad y fecha."
)
APPLICABILITY = {
    "tipos_actividad": [
        "consumo_combustible",
        "consumo_combustible_estacionario",
    ],
    "flujos": [
        "combustible",
        "combustible_estacionario",
        "combustible_movil",
    ],
}

ENERGY_METHODOLOGY_CODE = "construccion-v1-electricidad-red-sen"
ENERGY_FACTOR_CODE = "sen-electricidad-red-location-based-2025"
ENERGY_SOURCE = "Programa HuellaChile / Ministerio del Medio Ambiente"
ENERGY_REFERENCE = (
    "Recomendacion HuellaChile publicada en 2026: factor oficial 2025 del "
    "Ministerio de Energia, usado como ultima referencia oficial disponible "
    "para registros 2026 hasta disponer de una version posterior gobernada."
)
ENERGY_APPLICABILITY = {
    "tipos_actividad": ["consumo_energia"],
    "flujos": ["energia"],
    "tipos_recurso": ["red_electrica"],
}


class Command(BaseCommand):
    help = "Provisiona factores y metodologia global base de Calculation V2."

    @transaction.atomic
    def handle(self, *args, **options):
        # El catalogo tiene un unico dueno: su importador gobernado e idempotente.
        call_command("import_huellachile_factors", stdout=self.stdout)

        methodology, created = MetodologiaAmbiental.objects.get_or_create(
            organizacion=None,
            codigo=METHODOLOGY_CODE,
            defaults={
                "nombre": "Construccion V1 - combustible consumido",
                "categoria": "combustibles",
                "flujo": "combustible",
                "descripcion": (
                    "Calculo generico de combustible consumido por factor dinamico."
                ),
                "activa": True,
            },
        )
        expected_methodology = {
            "categoria": "combustibles",
            "flujo": "combustible",
            "activa": True,
        }
        differences = [
            field
            for field, expected in expected_methodology.items()
            if getattr(methodology, field) != expected
        ]
        if differences:
            raise CommandError(
                "La metodologia global existente difiere en: "
                + ", ".join(differences)
            )

        version, version_created = VersionMetodologia.objects.get_or_create(
            metodologia=methodology,
            version=1,
            defaults={
                "descripcion_tecnica": (
                    "Emision = combustible consumido normalizado x factor aplicable."
                ),
                "fuente_referencia": SOURCE_REFERENCE,
                "aplicabilidad": APPLICABILITY,
                "prioridad": 10,
                "tipo_resultado": "emision",
            },
        )
        if not version_created:
            expected_version = {
                "fuente_referencia": SOURCE_REFERENCE,
                "aplicabilidad": APPLICABILITY,
                "prioridad": 10,
                "tipo_resultado": "emision",
            }
            differences = [
                field
                for field, expected in expected_version.items()
                if getattr(version, field) != expected
            ]
            if differences:
                raise CommandError(
                    "La version gobernada existente difiere en: "
                    + ", ".join(differences)
                )

        formula, formula_created = FormulaAmbiental.objects.get_or_create(
            version_metodologia=version,
            defaults={
                "factor_ambiental": None,
                "codigo": "construccion-v1-combustible-consumido-v1",
                "tipo": FormulaAmbiental.Tipo.COMBUSTIBLE_CONSUMIDO,
                "expresion_legible": "combustible_consumido x factor_seleccionado",
                "version": 1,
            },
        )
        if not formula_created and (
            formula.factor_ambiental_id is not None
            or formula.tipo != FormulaAmbiental.Tipo.COMBUSTIBLE_CONSUMIDO
        ):
            raise CommandError("La formula gobernada existente no usa seleccion dinamica.")

        variable, variable_created = VariableFormula.objects.get_or_create(
            formula=formula,
            clave="combustible_consumido",
            defaults={
                "concepto_observacion": "combustible_consumido",
                "unidad_esperada": "m3",
                "obligatoria": True,
                "criticidad": VariableFormula.Criticidad.CRITICA,
                "rol": VariableFormula.Rol.ACTIVIDAD,
                "descripcion": "Volumen de combustible consumido.",
            },
        )
        if not variable_created and (
            variable.concepto_observacion != "combustible_consumido"
            or variable.unidad_esperada != "m3"
        ):
            raise CommandError("La variable gobernada existente difiere de Construccion V1.")

        for target in (
            VersionMetodologia.Estado.PRUEBAS,
            VersionMetodologia.Estado.VALIDADA,
            VersionMetodologia.Estado.ACTIVA,
        ):
            if version.estado == target or version.estado == VersionMetodologia.Estado.ACTIVA:
                continue
            version = transition_version(version, target)

        energy_factor_defaults = {
            "nombre": "SEN Chile - electricidad de red location-based - factor 2025",
            "categoria": "electricidad_red",
            "sustancia_impacto": "CO2e",
            "unidad_entrada": "MWh",
            "unidad_resultado": "tCO2e",
            "contexto": {
                "factor_year": 2025,
                "sistema": "SEN",
                "metodo": "location_based",
                "alcance": 2,
                "pais": "Chile",
                "fuente_original": "Ministerio de Energia",
            },
        }
        energy_factor, energy_factor_created = FactorAmbiental.objects.get_or_create(
            organizacion=None,
            codigo=ENERGY_FACTOR_CODE,
            defaults=energy_factor_defaults,
        )
        if not energy_factor_created:
            differences = [
                field
                for field, expected in energy_factor_defaults.items()
                if getattr(energy_factor, field) != expected
            ]
            if differences:
                raise CommandError(
                    "El factor electrico global existente difiere en: "
                    + ", ".join(differences)
                )

        energy_factor_version_defaults = {
            "valor": Decimal("0.2466"),
            "fuente": ENERGY_SOURCE,
            "referencia": ENERGY_REFERENCE,
            "region": "Chile",
            "vigencia_desde": date(2026, 1, 1),
            "vigencia_hasta": None,
            "estado": VersionFactorAmbiental.Estado.ACTIVO,
        }
        energy_factor_version, energy_factor_version_created = (
            VersionFactorAmbiental.objects.get_or_create(
                factor=energy_factor,
                version=1,
                defaults=energy_factor_version_defaults,
            )
        )
        if not energy_factor_version_created:
            differences = [
                field
                for field, expected in energy_factor_version_defaults.items()
                if getattr(energy_factor_version, field) != expected
            ]
            if differences:
                raise CommandError(
                    "La version gobernada del factor electrico difiere en: "
                    + ", ".join(differences)
                )

        energy_methodology_defaults = {
            "nombre": "Construccion V1 - electricidad de red SEN",
            "categoria": "energia",
            "flujo": "energia",
            "descripcion": "Emisiones GEI indirectas por electricidad consumida de la red.",
            "activa": True,
        }
        energy_methodology, energy_methodology_created = (
            MetodologiaAmbiental.objects.get_or_create(
                organizacion=None,
                codigo=ENERGY_METHODOLOGY_CODE,
                defaults=energy_methodology_defaults,
            )
        )
        if not energy_methodology_created:
            differences = [
                field
                for field, expected in energy_methodology_defaults.items()
                if getattr(energy_methodology, field) != expected
            ]
            if differences:
                raise CommandError(
                    "La metodologia electrica global existente difiere en: "
                    + ", ".join(differences)
                )

        energy_version_defaults = {
            "descripcion_tecnica": (
                "Emision Scope 2 location-based = energia consumida normalizada x factor SEN."
            ),
            "fuente_referencia": ENERGY_REFERENCE,
            "vigencia_desde": date(2026, 1, 1),
            "aplicabilidad": ENERGY_APPLICABILITY,
            "prioridad": 10,
            "tipo_resultado": "emision",
        }
        energy_version, energy_version_created = VersionMetodologia.objects.get_or_create(
            metodologia=energy_methodology,
            version=1,
            defaults=energy_version_defaults,
        )
        if not energy_version_created:
            differences = [
                field
                for field, expected in energy_version_defaults.items()
                if getattr(energy_version, field) != expected
            ]
            if differences:
                raise CommandError(
                    "La version electrica gobernada existente difiere en: "
                    + ", ".join(differences)
                )

        energy_formula, energy_formula_created = FormulaAmbiental.objects.get_or_create(
            version_metodologia=energy_version,
            defaults={
                "factor_ambiental": energy_factor,
                "codigo": "construccion-v1-electricidad-red-sen-v1",
                "tipo": FormulaAmbiental.Tipo.ENERGIA_CONSUMIDA,
                "expresion_legible": "energia_consumida x factor_electrico_sen",
                "version": 1,
            },
        )
        if not energy_formula_created and (
            energy_formula.factor_ambiental_id != energy_factor.id
            or energy_formula.tipo != FormulaAmbiental.Tipo.ENERGIA_CONSUMIDA
        ):
            raise CommandError("La formula electrica gobernada existente difiere.")

        energy_variable, energy_variable_created = VariableFormula.objects.get_or_create(
            formula=energy_formula,
            clave="energia_consumida",
            defaults={
                "concepto_observacion": "consumo_energia",
                "unidad_esperada": "MWh",
                "obligatoria": True,
                "criticidad": VariableFormula.Criticidad.CRITICA,
                "rol": VariableFormula.Rol.ACTIVIDAD,
                "descripcion": "Electricidad consumida desde la red.",
            },
        )
        if not energy_variable_created and (
            energy_variable.concepto_observacion != "consumo_energia"
            or energy_variable.unidad_esperada != "MWh"
        ):
            raise CommandError("La variable electrica gobernada existente difiere.")

        for target in (
            VersionMetodologia.Estado.PRUEBAS,
            VersionMetodologia.Estado.VALIDADA,
            VersionMetodologia.Estado.ACTIVA,
        ):
            if (
                energy_version.estado == target
                or energy_version.estado == VersionMetodologia.Estado.ACTIVA
            ):
                continue
            energy_version = transition_version(energy_version, target)

        self.stdout.write(
            self.style.SUCCESS(
                "Calculation V2 disponible: catalogo HuellaChile y metodologia "
                f"{METHODOLOGY_CODE} v1 y {ENERGY_METHODOLOGY_CODE} v1 activas "
                f"({'creada' if created else 'existente'})."
            )
        )
