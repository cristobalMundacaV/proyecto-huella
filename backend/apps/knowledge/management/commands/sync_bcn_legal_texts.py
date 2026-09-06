from django.core.management.base import BaseCommand
from apps.knowledge.bcn_text import sync_bcn_legal_texts


class Command(BaseCommand):
    def handle(self, *args, **options):
        r = sync_bcn_legal_texts()
        self.stdout.write(
            f"status={'partial' if r.failed else 'success'} normas={r.normas} downloaded={r.downloaded} imported={r.imported} unchanged={r.unchanged} failed={r.failed} articles={r.articles}"
        )
