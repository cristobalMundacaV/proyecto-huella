from django.core.management.base import BaseCommand
from django.db import transaction

from apps.analytics.models import EmisionLote


class Command(BaseCommand):
    help = "Elimina actividades duplicadas por lote, actividad, unidad, fecha, cantidad y factor."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra cuantos duplicados se eliminarian sin borrar registros.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        seen = set()
        duplicate_ids = []

        queryset = EmisionLote.objects.order_by("created_at", "id").values(
            "id",
            "lote_id",
            "actividad",
            "unidad",
            "fecha",
            "cantidad",
            "factor_emision",
        )

        for row in queryset:
            key = (
                row["lote_id"],
                (row["actividad"] or "").strip().lower(),
                (row["unidad"] or "").strip().lower(),
                row["fecha"],
                str(row["cantidad"]),
                str(row["factor_emision"]),
            )

            if key in seen:
                duplicate_ids.append(row["id"])
            else:
                seen.add(key)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Se eliminarian {len(duplicate_ids)} actividades duplicadas."
                )
            )
            return

        with transaction.atomic():
            deleted, _ = EmisionLote.objects.filter(id__in=duplicate_ids).delete()

        self.stdout.write(
            self.style.SUCCESS(f"Actividades duplicadas eliminadas: {deleted}")
        )
