import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.ec3.client import Ec3Client
from apps.ec3.rate_limit import RateLimited
from apps.ec3.services import ingest_epd
from apps.knowledge.models import EnvironmentalSource, ExternalRecord


class Command(BaseCommand):
    help = ("Refresca (re-valida) las EPD EC3 ya conocidas localmente — nunca descubre ni "
            "importa EPD nuevas, nunca vuelca el catálogo EC3 (capability 10). Cada EPD ya "
            "conocida se re-consulta individualmente vía la misma ingesta dirigida y "
            "auditada de siempre; una EPD sin cambios sólo confirma frescura (idempotente, "
            "nunca crea una versión local duplicada). Respeta el presupuesto compartido de "
            "100 tokens/min: ante RateLimited espera el retry_after indicado y reintenta una "
            "vez antes de continuar con la siguiente EPD (continue-on-error, nunca aborta "
            "el lote por una sola EPD).")

    def add_arguments(self, parser):
        parser.add_argument("--actor-id", required=True, type=int)
        parser.add_argument("--limit", type=int, default=None)

    def handle(self, *args, **options):
        try:
            user = get_user_model().objects.get(pk=options["actor_id"])
        except get_user_model().DoesNotExist:
            raise CommandError("actor-id desconocido.") from None

        source = EnvironmentalSource.objects.filter(codigo="ec3-openepd").first()
        if source is None:
            self.stdout.write("known_epds=0 refreshed=0 changed=0 errors=0")
            return

        external_ids = list(
            ExternalRecord.objects.filter(source=source).order_by("pk").values_list("external_id", flat=True)
        )
        if options["limit"]:
            external_ids = external_ids[: options["limit"]]

        client = Ec3Client()
        refreshed = changed = errors = 0
        try:
            for external_id in external_ids:
                latest_before = (
                    ExternalRecord.objects.get(source=source, external_id=external_id)
                    .ec3_versions.order_by("-local_version").values_list("pk", flat=True).first()
                )
                for attempt in range(2):
                    try:
                        version = ingest_epd(external_id, user, client=client)
                        refreshed += 1
                        if version.pk != latest_before:
                            changed += 1
                        break
                    except RateLimited as exc:
                        if attempt == 1:
                            errors += 1
                            self.stderr.write(f"external_id={external_id} rate_limited retry_after={exc.retry_after}")
                            break
                        time.sleep(exc.retry_after)
                    except Exception as exc:
                        errors += 1
                        self.stderr.write(f"external_id={external_id} error={exc.__class__.__name__}")
                        break
        finally:
            client.close()

        self.stdout.write(f"known_epds={len(external_ids)} refreshed={refreshed} changed={changed} errors={errors}")
