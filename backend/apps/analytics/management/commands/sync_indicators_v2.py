from django.core.management.base import BaseCommand, CommandError

from ...models import ImpactoAmbiental, Obra, Organizacion
from ...services.generated_emissions_indicator import (
    calendar_month,
    sync_generated_emissions_month,
)


class Command(BaseCommand):
    help = "Sincroniza indicadores GEI versionados desde impactos efectivos."

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True)
        parser.add_argument("--obra", required=True, type=int)

    def handle(self, *args, **options):
        try:
            organization = Organizacion.objects.get(
                organizacion_id=options["organization"]
            )
        except Organizacion.DoesNotExist as error:
            raise CommandError("La organizacion indicada no existe.") from error
        try:
            work = Obra.objects.get(pk=options["obra"], organizacion=organization)
        except Obra.DoesNotExist as error:
            raise CommandError("La obra no pertenece a la organizacion indicada.") from error

        timestamps = ImpactoAmbiental.objects.filter(
            organizacion=organization,
            actividad__obra=work,
        ).values_list("timestamp", flat=True)
        periods = sorted({calendar_month(timestamp) for timestamp in timestamps})
        created = 0
        for start, end in periods:
            _, value_created = sync_generated_emissions_month(work, start, end)
            created += int(value_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Indicadores sincronizados para {work.nombre}: "
                f"{len(periods)} periodos, {created} nuevas versiones."
            )
        )
