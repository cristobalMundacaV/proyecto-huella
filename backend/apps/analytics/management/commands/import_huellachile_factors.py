from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import FactorAmbiental, VersionFactorAmbiental


DOCUMENT_TITLE = "Factores de emisión para el cálculo de la huella de carbono - Nivel básico"
DOCUMENT_REFERENCE = f"{DOCUMENT_TITLE} - Versión 3 - 28/11/2024"
SOURCE = "Programa HuellaChile - Ministerio del Medio Ambiente"

FACTOR_ROWS = (
    ("combustion_estacionaria", "glp", "Gas Licuado de Petróleo (GLP)", "1.59", "tCO2e"),
    ("combustion_estacionaria", "gas_natural", "Gas Natural", "1.98", "kgCO2e"),
    ("combustion_estacionaria", "diesel", "Diésel", "2.71", "tCO2e"),
    ("combustion_movil", "glp", "Gas Licuado de Petróleo (GLP)", "1.72", "tCO2e"),
    ("combustion_movil", "gas_natural", "Gas Natural", "2.09", "tCO2e"),
    ("combustion_movil", "diesel", "Diésel", "2.74", "tCO2e"),
)


class Command(BaseCommand):
    help = "Importa el catálogo global HuellaChile v3 de combustibles de forma idempotente."

    @transaction.atomic
    def handle(self, *args, **options):
        created_factors = 0
        created_versions = 0

        for category, fuel, fuel_label, value, result_unit in FACTOR_ROWS:
            code = f"huellachile-{category.replace('_', '-')}-{fuel.replace('_', '-')}"
            context = {
                "proveedor": "HuellaChile",
                "documento": DOCUMENT_TITLE,
                "documento_version": 3,
                "fecha_actualizacion": "2024-11-28",
                "alcance": 1,
                "categoria_huella": category,
                "combustible": fuel,
            }
            factor, factor_created = FactorAmbiental.objects.update_or_create(
                organizacion=None,
                codigo=code,
                defaults={
                    "nombre": f"HuellaChile · {category.replace('_', ' ').title()} · {fuel_label}",
                    "categoria": category,
                    "sustancia_impacto": "CO2e",
                    "unidad_entrada": "m3",
                    "unidad_resultado": result_unit,
                    "contexto": context,
                },
            )
            created_factors += int(factor_created)

            version_defaults = {
                "valor": Decimal(value),
                "fuente": SOURCE,
                "referencia": DOCUMENT_REFERENCE,
                "region": "Chile",
                "vigencia_desde": None,
                "vigencia_hasta": None,
                "estado": VersionFactorAmbiental.Estado.ACTIVO,
            }
            version, version_created = VersionFactorAmbiental.objects.get_or_create(
                factor=factor,
                version=1,
                defaults=version_defaults,
            )
            if not version_created:
                differences = [
                    field
                    for field, expected in version_defaults.items()
                    if getattr(version, field) != expected
                ]
                if differences:
                    raise CommandError(
                        f"La versión gobernada de {code} difiere en: "
                        f"{', '.join(differences)}. Cree una nueva versión; no se sobrescribió."
                    )
            created_versions += int(version_created)

        self.stdout.write(
            self.style.SUCCESS(
                "Catálogo HuellaChile v3 disponible: 6 factores globales; "
                f"{created_factors} factores y {created_versions} versiones creados."
            )
        )
