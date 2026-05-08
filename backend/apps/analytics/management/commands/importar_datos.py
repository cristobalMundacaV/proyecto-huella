from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Importa un JSON de backup generado por exportar_datos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            default=str(settings.PROJECT_ROOT / "backup_datos.json"),
            help="Ruta del archivo JSON a importar. Por defecto busca en la raiz del proyecto.",
        )

    def handle(self, *args, **options):
        input_path = Path(options["input"]).resolve()

        if not input_path.exists():
            raise FileNotFoundError(f"No existe el archivo de backup: {input_path}")

        call_command("loaddata", str(input_path))
        self.stdout.write(self.style.SUCCESS(f"Datos importados desde: {input_path}"))
