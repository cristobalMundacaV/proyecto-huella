from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Comando retirado: los factores oficiales ingresan por Knowledge y gobernanza."
    )

    def handle(self, *args, **options):
        raise CommandError(
            "Comando retirado. Use sync_huellachile_factors, "
            "build_huellachile_factor_candidates y reconcile_huellachile_legacy_factors."
        )
