from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import (
    FormulaAmbiental,
    MetodologiaAmbiental,
    VariableFormula,
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

        self.stdout.write(
            self.style.SUCCESS(
                "Calculation V2 disponible: catalogo HuellaChile y metodologia "
                f"{METHODOLOGY_CODE} v1 activa ({'creada' if created else 'existente'})."
            )
        )
