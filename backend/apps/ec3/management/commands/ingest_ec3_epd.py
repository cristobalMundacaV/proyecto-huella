from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from apps.ec3.services import ingest_epd


class Command(BaseCommand):
    help = "Ingesta dirigida de una EPD pública; no confirma ni promueve candidatos."

    def add_arguments(self, parser):
        parser.add_argument("external_id")
        parser.add_argument("--actor-id", required=True, type=int)

    def handle(self, *args, **options):
        try:
            user = get_user_model().objects.get(pk=options["actor_id"])
            version = ingest_epd(options["external_id"], user)
        except Exception:
            raise CommandError("EC3 ingestion failed. Check backend token, rights, actor and SyncRun; no credentials logged.") from None
        self.stdout.write(f"epd_version_id={version.pk} local_version={version.local_version}")
