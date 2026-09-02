from django.core.management.base import BaseCommand

from ...services.system_environmental_catalog import (
    ENERGY_FACTOR_CODE,
    ENERGY_METHODOLOGY_CODE,
    ENERGY_REFERENCE,
    ENERGY_SOURCE,
    FUEL_METHODOLOGY_CODE as METHODOLOGY_CODE,
    SYSTEM_ENVIRONMENTAL_CATALOG_VERSION,
    ensure_system_environmental_catalog,
)


class Command(BaseCommand):
    help = "Verifica o repara el catalogo ambiental administrado por el sistema."

    def handle(self, *args, **options):
        result = ensure_system_environmental_catalog()
        self.stdout.write(
            self.style.SUCCESS(
                "Catalogo ambiental administrado por el sistema disponible: "
                f"version {SYSTEM_ENVIRONMENTAL_CATALOG_VERSION}, "
                f"{result['huellachile_factors']} factores HuellaChile y "
                f"{result['methodologies']} metodologias Construction V1."
            )
        )
