from django.core.management.base import BaseCommand, CommandError

from ...models import (
    ImpactoAmbiental,
    Obra,
    Observacion,
    Organizacion,
    RegistroFlujoAmbiental,
)
from ...services.generated_emissions_indicator import (
    calendar_month,
    sync_generated_emissions_month,
)
from ...services.operational_indicators import (
    OPERATIONAL_INDICATOR_CONTRACTS,
    calendar_month as operational_calendar_month,
    sync_operational_indicator_month,
)
from ...services.waste_indicators import sync_waste_indicator_month


class Command(BaseCommand):
    help = "Reconcilia indicadores GEI y operacionales versionados para una obra."

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

        operational_periods = set()
        observations = Observacion.objects.filter(
            organizacion=organization,
            actividad__obra=work,
            concepto__in=OPERATIONAL_INDICATOR_CONTRACTS,
        ).values_list("concepto", "timestamp_observacion")
        for concept, timestamp in observations:
            operational_periods.add(
                (concept, *operational_calendar_month(timestamp))
            )
        for concept, start, end in sorted(operational_periods):
            _, value_created = sync_operational_indicator_month(
                work, concept, start, end
            )
            created += int(value_created)

        waste_timestamps = Observacion.objects.filter(
            organizacion=organization,
            actividad__registro_flujo_ambiental__obra=work,
            actividad__registro_flujo_ambiental__flujo=RegistroFlujoAmbiental.Flujo.RESIDUO,
            concepto="cantidad_residuo",
            valor_numerico__isnull=False,
        ).values_list("timestamp_observacion", flat=True)
        waste_periods = sorted(
            {operational_calendar_month(timestamp) for timestamp in waste_timestamps}
        )
        for start, end in waste_periods:
            results = sync_waste_indicator_month(work, start, end)
            created += sum(int(value_created) for _, value_created in results.values())

        self.stdout.write(
            self.style.SUCCESS(
                f"Indicadores sincronizados para {work.nombre}: "
                f"{len(periods) + len(operational_periods) + len(waste_periods)} lotes-periodo, "
                f"{created} nuevas versiones."
            )
        )
