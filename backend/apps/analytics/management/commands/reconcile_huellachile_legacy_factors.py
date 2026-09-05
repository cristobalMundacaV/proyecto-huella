from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from ...services.factor_reconciliation import (
    advance_reconciliation,
    prepare_reconciliation,
    reconciliation_report,
    switch_reconciliation,
)


class Command(BaseCommand):
    help = "Reconcilia los siete factores legacy con facts HuellaChile 2025 gobernados."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=2025)
        parser.add_argument("--prepare", action="store_true")
        parser.add_argument("--advance", choices=("pruebas", "validado"))
        parser.add_argument("--switch", action="store_true")
        parser.add_argument("--reviewer")
        parser.add_argument("--confirm-sha")
        parser.add_argument("--note", default="")

    def handle(self, *args, **options):
        actions = sum(bool(options[key]) for key in ("prepare", "advance", "switch"))
        if actions > 1:
            raise CommandError("Seleccione una sola acción.")
        if not actions:
            try:
                rows = reconciliation_report(options["year"])
            except (ValidationError, Exception) as exc:
                raise CommandError(str(exc)) from exc
            for row in rows:
                self.stdout.write(
                    " ".join(f"{key}={value}" for key, value in row.items())
                )
            ready = sum(row["readiness"] == "ready" for row in rows)
            self.stdout.write(f"ready={ready}\nblocked={len(rows)-ready}\nmutations=0")
            return
        if not options["reviewer"]:
            raise CommandError("--reviewer es obligatorio.")
        try:
            reviewer = get_user_model().objects.get(
                username=options["reviewer"], is_superuser=True
            )
        except get_user_model().DoesNotExist as exc:
            raise CommandError("Reviewer superuser no encontrado.") from exc
        try:
            if options["prepare"]:
                if not options["confirm_sha"]:
                    raise CommandError("--confirm-sha es obligatorio para prepare.")
                result = prepare_reconciliation(
                    reviewer, options["year"], options["confirm_sha"], options["note"]
                )
                self.stdout.write(
                    f"prepared_created={result['created']} prepared_existing={result['existing']}"
                )
            elif options["advance"]:
                for code, state in advance_reconciliation(
                    reviewer, options["advance"], options["year"]
                ):
                    self.stdout.write(f"factor={code} estado={state}")
            else:
                if not options["confirm_sha"]:
                    raise CommandError("--confirm-sha es obligatorio para switch.")
                rows = switch_reconciliation(
                    reviewer, options["year"], options["confirm_sha"]
                )
                for item in rows:
                    self.stdout.write(
                        f"factor={item.factor.codigo} estado={item.status}"
                    )
        except ValidationError as exc:
            raise CommandError(str(exc)) from exc
