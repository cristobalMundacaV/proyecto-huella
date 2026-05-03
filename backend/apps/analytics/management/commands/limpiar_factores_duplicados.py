from collections import defaultdict

from django.core.management.base import BaseCommand

from apps.analytics.models import FactorEmision


def is_readable_name(value: str) -> bool:
    return "_" not in str(value or "")


def factor_group_key(factor: FactorEmision) -> tuple:
    return (
        factor.actividad_key,
        factor.unidad.lower(),
        str(factor.factor_emision),
        factor.anio,
    )


def choose_factor_to_keep(factors: list[FactorEmision]) -> FactorEmision:
    return sorted(
        factors,
        key=lambda factor: (
            0 if is_readable_name(factor.actividad) else 1,
            0 if "Nivel basico" not in factor.fuente and "Nivel básico" not in factor.fuente else 1,
            factor.id,
        ),
    )[0]


class Command(BaseCommand):
    help = "Elimina factores duplicados equivalentes y conserva la fila legible."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra cuantos duplicados se eliminarian sin borrar registros.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        groups = defaultdict(list)

        for factor in FactorEmision.objects.all():
            groups[factor_group_key(factor)].append(factor)

        duplicate_ids = []
        for factors in groups.values():
            if len(factors) < 2:
                continue

            keep = choose_factor_to_keep(factors)
            duplicate_ids.extend(factor.id for factor in factors if factor.id != keep.id)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Se eliminarian {len(duplicate_ids)} factores duplicados."
                )
            )
            return

        deleted, _ = FactorEmision.objects.filter(id__in=duplicate_ids).delete()
        self.stdout.write(
            self.style.SUCCESS(f"Factores duplicados eliminados: {deleted}.")
        )
