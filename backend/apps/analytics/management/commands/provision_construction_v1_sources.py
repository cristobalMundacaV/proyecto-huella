from django.core.management.base import BaseCommand, CommandError

from ...models import Organizacion
from ...services.construction_sources import ensure_construction_v1_sources


class Command(BaseCommand):
    help = "Provisiona el catalogo gobernado de fuentes para Construccion V1."

    def add_arguments(self, parser):
        parser.add_argument("--organization")

    def handle(self, *args, **options):
        rows = Organizacion.objects.filter(preset=Organizacion.Preset.CONSTRUCCION)
        if options.get("organization"):
            rows = rows.filter(organizacion_id=options["organization"])
            if not rows.exists():
                raise CommandError("La organizacion de Construccion indicada no existe.")
        created = sum(ensure_construction_v1_sources(org) for org in rows)
        self.stdout.write(self.style.SUCCESS(f"Fuentes disponibles: {created} creadas."))
