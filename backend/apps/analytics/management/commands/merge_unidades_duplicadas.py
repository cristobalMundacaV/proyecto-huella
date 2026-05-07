from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.analytics.models import EmisionLote, Evidencia, Lote, UnidadOperativa


def semantic_key(unidad):
    return (
        unidad.empresa_id,
        (unidad.nombre or "").strip().casefold(),
        (unidad.tipo or "").strip().casefold(),
        (unidad.region or "").strip().casefold(),
        (unidad.comuna or "").strip().casefold(),
    )


class Command(BaseCommand):
    help = "Fusiona unidades operativas duplicadas dentro de la misma empresa."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica la fusion. Sin este flag solo muestra una vista previa.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        groups = defaultdict(list)

        for unidad in UnidadOperativa.objects.select_related("empresa").order_by("created_at", "id"):
            groups[semantic_key(unidad)].append(unidad)

        duplicate_groups = [units for units in groups.values() if len(units) > 1]

        if not duplicate_groups:
            self.stdout.write(self.style.SUCCESS("No se encontraron unidades duplicadas."))
            return

        merged = 0
        moved_lotes = 0
        moved_actividades = 0
        moved_evidencias = 0

        with transaction.atomic():
            for units in duplicate_groups:
                keep = units[0]
                duplicates = units[1:]
                self.stdout.write(
                    f"Grupo: {keep.empresa.empresa_id} | {keep.nombre} | mantener {keep.unidad_id}"
                )

                for duplicate in duplicates:
                    lote_count = duplicate.lotes.count()
                    actividad_count = duplicate.actividades_emision.count()
                    evidencia_count = duplicate.evidencias.count()
                    self.stdout.write(
                        f"  fusionar {duplicate.unidad_id}: "
                        f"{lote_count} lotes, {actividad_count} actividades, {evidencia_count} evidencias"
                    )

                    if apply_changes:
                        moved_lotes += Lote.objects.filter(unidad_operativa=duplicate).update(
                            unidad_operativa=keep
                        )
                        moved_actividades += EmisionLote.objects.filter(
                            unidad_operativa=duplicate
                        ).update(unidad_operativa=keep)
                        moved_evidencias += Evidencia.objects.filter(
                            unidad_operativa=duplicate
                        ).update(unidad_operativa=keep)
                        duplicate.delete()
                        merged += 1

            if not apply_changes:
                transaction.set_rollback(True)

        if apply_changes:
            self.stdout.write(
                self.style.SUCCESS(
                    "Fusion completada: "
                    f"{merged} unidades eliminadas, "
                    f"{moved_lotes} lotes movidos, "
                    f"{moved_actividades} actividades movidas, "
                    f"{moved_evidencias} evidencias movidas."
                )
            )
        else:
            self.stdout.write("Vista previa solamente. Ejecuta con --apply para aplicar cambios.")
