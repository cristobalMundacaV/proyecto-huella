from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.ec3.models import ResponseCache


class Command(BaseCommand):
    help = "Elimina cache EC3 vencido (o todo el cache con --all). No elimina evidencia auditada."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true")

    def handle(self, *args, **options):
        rows = ResponseCache.objects.all()
        if not options["all"]:
            rows = rows.filter(expires_at__lte=timezone.now())
        count, _ = rows.delete()
        self.stdout.write(f"deleted={count}")
