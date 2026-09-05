from django.core.management.base import BaseCommand

from apps.analytics.services.factor_candidates import (
    build_huellachile_factor_candidates,
)


class Command(BaseCommand):
    help = "Construye candidatos gobernables desde el artifact HuellaChile vigente."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=2025)

    def handle(self, *args, **options):
        result = build_huellachile_factor_candidates(options["year"])
        self.stdout.write(f"source=HuellaChile\nyear={options['year']}")
        for key, value in result.items():
            self.stdout.write(f"{key}={value}")
