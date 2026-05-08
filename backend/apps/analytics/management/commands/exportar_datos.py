from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Exporta los datos de la base de datos a un JSON en la raiz del proyecto."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=str(settings.PROJECT_ROOT / "backup_datos.json"),
            help="Ruta del archivo JSON de salida. Por defecto se guarda en la raiz del proyecto.",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output"]).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as handle:
            call_command(
                "dumpdata",
                "--natural-foreign",
                "--natural-primary",
                "--exclude",
                "admin.logentry",
                "--exclude",
                "auth.permission",
                "--exclude",
                "contenttypes",
                "--exclude",
                "sessions.session",
                stdout=handle,
            )

        self.stdout.write(self.style.SUCCESS(f"Datos exportados en: {output_path}"))
