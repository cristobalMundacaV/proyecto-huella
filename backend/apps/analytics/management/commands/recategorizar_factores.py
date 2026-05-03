from django.core.management.base import BaseCommand

from apps.analytics.models import FactorEmision
from apps.analytics.services.factor_classifier import infer_categoria, normalize_key


class Command(BaseCommand):
    help = "Recategoriza factores de emision existentes usando reglas deterministicas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recalcula todos los factores, incluso los que ya tienen categoria.",
        )

    def handle(self, *args, **options):
        force = options["force"]
        updated = 0
        skipped = 0

        for factor in FactorEmision.objects.all().iterator():
            categoria_actual = factor.categoria or ""
            categoria_inferida = infer_categoria(
                factor.actividad,
                factor.unidad,
                factor.fuente,
            )
            actividad_key = normalize_key(factor.actividad_key or factor.actividad)

            should_update = force or categoria_actual in {"", "Otros"} or not factor.actividad_key
            if not should_update:
                skipped += 1
                continue

            factor.categoria = categoria_inferida
            factor.actividad_key = actividad_key
            metadata = factor.metadata_clasificacion or {}
            metadata.update(
                {
                    "metodo": "rules",
                    "categoria_detectada": categoria_inferida,
                    "recategorizado": True,
                }
            )
            factor.metadata_clasificacion = metadata
            factor.save(
                update_fields=[
                    "categoria",
                    "actividad_key",
                    "metadata_clasificacion",
                    "updated_at",
                ]
            )
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Factores recategorizados: {updated}. Omitidos: {skipped}."
            )
        )
