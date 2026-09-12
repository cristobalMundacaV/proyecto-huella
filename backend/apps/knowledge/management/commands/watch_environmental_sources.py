import json

from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.models import EnvironmentalSource
from apps.knowledge.watch_orchestration import watch_source, watch_sources


class Command(BaseCommand):
    """SOURCE-WATCH-01I — the one entry point ordinary cron/systemd/scheduler
    infrastructure needs to run a complete watch cycle. Embeds no
    source-specific business logic itself: it only calls
    `watch_orchestration.watch_source()`/`watch_sources()`, which in turn
    reuse each source's existing sync command/service."""

    help = "Ejecuta un ciclo de SOURCE-WATCH sobre una o varias fuentes registradas."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--source", dest="source", help="Código de una única fuente a observar.")
        group.add_argument(
            "--all-active", dest="all_active", action="store_true",
            help="Observa todas las fuentes activas y habilitadas para poll automático (comportamiento por defecto).",
        )
        parser.add_argument(
            "--health-only", dest="health_only", action="store_true",
            help="No sincroniza; solo reporta salud/frescura actual.",
        )
        parser.add_argument(
            "--dry-run", dest="dry_run", action="store_true",
            help="Equivalente a --health-only: no ejecuta ninguna sincronización real.",
        )
        parser.add_argument(
            "--continue-on-error", dest="continue_on_error", action="store_true", default=True,
            help="No detiene el ciclo si una fuente falla inesperadamente (comportamiento por defecto).",
        )
        parser.add_argument(
            "--stop-on-error", dest="continue_on_error", action="store_false",
            help="Detiene el ciclo completo ante la primera falla inesperada de una fuente.",
        )
        parser.add_argument(
            "--json", dest="as_json", action="store_true",
            help="Imprime el resumen como JSON (para consumo por otras herramientas operativas).",
        )

    def handle(self, *args, **options):
        health_only = options["health_only"] or options["dry_run"]

        if options.get("source"):
            try:
                source = EnvironmentalSource.objects.get(codigo=options["source"])
            except EnvironmentalSource.DoesNotExist as exc:
                raise CommandError(f"Fuente no registrada: {options['source']}") from exc
            results = [watch_source(source, health_only=health_only, dry_run=options["dry_run"])]
        else:
            results = watch_sources(
                health_only=health_only, dry_run=options["dry_run"],
                continue_on_error=options["continue_on_error"],
            )

        if options["as_json"]:
            self.stdout.write(json.dumps(results, default=str))
        else:
            for result in results:
                if not result.get("attempted"):
                    self.stdout.write(f"source={result['codigo']} attempted=no reason={result.get('reason', result.get('health', {}).get('health_bucket', ''))}")
                    continue
                self.stdout.write(
                    f"source={result['codigo']} attempted=yes success={result['success']} "
                    f"changes={result.get('change_count', 0)} reviews={result.get('review_count', 0)} "
                    f"health_after={result.get('health_after', '')} error={result.get('error', '')}"
                )

        # Individual upstream source failures are reported in the structured
        # per-source output above and never fail the command by themselves —
        # that is exactly what health tracking/the review queue is for. The
        # command itself only exits non-zero if the orchestration cycle was
        # explicitly told to stop on the first unexpected failure
        # (--stop-on-error) and an exception actually propagated out of
        # watch_sources() (handled naturally by BaseCommand, no extra check
        # needed here).
