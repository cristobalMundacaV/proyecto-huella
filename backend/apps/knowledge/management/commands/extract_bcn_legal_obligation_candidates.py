from django.core.management.base import BaseCommand

from apps.knowledge.bcn_obligations import extract_bcn_legal_obligation_candidates


class Command(BaseCommand):
    def handle(self, *args, **options):
        result = extract_bcn_legal_obligation_candidates()
        status = "partial" if result.failed else "success"
        self.stdout.write(
            f"status={status} norms={result.norms} articles={result.articles} "
            f"processed={result.processed} unchanged={result.unchanged} "
            f"articles_with_candidates={result.articles_with_candidates} "
            f"candidates={result.candidates} failed={result.failed}"
        )
