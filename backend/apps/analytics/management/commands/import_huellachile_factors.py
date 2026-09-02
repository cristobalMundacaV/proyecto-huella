from django.core.management.base import BaseCommand

from ...services.system_environmental_catalog import (
    HUELLACHILE_DOCUMENT as DOCUMENT_TITLE,
    HUELLACHILE_FACTORS as FACTOR_ROWS,
    HUELLACHILE_REFERENCE as DOCUMENT_REFERENCE,
    HUELLACHILE_SOURCE as SOURCE,
    ensure_huellachile_factor_catalog,
)


class Command(BaseCommand):
    help = "Verifica o repara el catalogo HuellaChile administrado por el sistema."

    def handle(self, *args, **options):
        factors = ensure_huellachile_factor_catalog()
        self.stdout.write(
            self.style.SUCCESS(
                "Catalogo ambiental administrado por el sistema disponible: "
                f"{len(factors)} factores HuellaChile globales."
            )
        )
