from django.core.management.base import BaseCommand,CommandError

from apps.knowledge.huellachile_sync import sync_huellachile_factors

class Command(BaseCommand):
    help="Descubre e importa una publicación oficial de factores de emisión HuellaChile como conocimiento externo."
    def add_arguments(self,parser): parser.add_argument("--year",type=int,default=2025);parser.add_argument("--edition",choices=("completa","resumen"),default="completa")
    def handle(self,*args,**options):
        try: result=sync_huellachile_factors(options["year"],options["edition"])
        except Exception as exc: raise CommandError(str(exc)) from exc
        self.stdout.write(f"source=HuellaChile\ndataset={result.dataset}\nyear={result.year}\nedition={result.edition}\ndiscovered_url={result.discovered_url}\nfilename={result.filename}\nbytes={result.byte_size}\nsha256={result.sha256}\nsheets={len(result.artifact.metadata.get('sheets',[]))}\nrows_read={result.rows_read}\nfactors_imported={result.factors_imported}\nrows_rejected={len(result.rejected)}\nreferences={len(result.references)}\nartifact_version={result.artifact.version}\nstatus={result.estado}")
