from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime

from ...models import Organizacion
from ...services.fuel_classification import FUEL_FLOWS


class Command(BaseCommand):
    help = (
        "Audita candidatos históricos atribuibles al registro manual de "
        "combustibles y solo elimina IDs confirmados explícitamente."
    )

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True, help="organizacion_id del tenant")
        parser.add_argument("--work", type=int, help="ID de obra")
        parser.add_argument("--since", help="Fecha/hora ISO mínima")
        parser.add_argument("--activity-id", action="append", type=int, default=[])
        parser.add_argument("--evidence-id", action="append", type=int, default=[])
        parser.add_argument("--delete-confirmed", action="store_true")

    def handle(self, *args, **options):
        organization = Organizacion.objects.filter(
            organizacion_id=options["organization"]
        ).first()
        if not organization:
            raise CommandError("No existe la organización indicada.")

        activities = organization.actividades_operacionales.filter(
            codigo__startswith="manual-combustibles-",
            registro_flujo_ambiental__isnull=True,
            observaciones__isnull=True,
        ).order_by("created_at")
        evidences = organization.evidencias.filter(
            metadata_extraccion__registro_manual=True,
            metadata_extraccion__origen_operacional=True,
            metadata_extraccion__flujo__in=FUEL_FLOWS,
            observaciones_operacionales__isnull=True,
            eventos_materiales__isnull=True,
            registros_emision__isnull=True,
            versiones__isnull=True,
        ).distinct().order_by("created_at")

        if options.get("work"):
            activities = activities.filter(obra_id=options["work"])
            evidences = evidences.filter(obra_id=options["work"])
        if options.get("since"):
            since = parse_datetime(options["since"])
            if not since:
                raise CommandError("--since debe usar una fecha/hora ISO válida.")
            activities = activities.filter(created_at__gte=since)
            evidences = evidences.filter(created_at__gte=since)

        self.stdout.write("Actividades candidatas sin registro ambiental asociado:")
        for item in activities:
            self.stdout.write(
                f"  id={item.id} obra={item.obra_id} "
                f"fecha={item.created_at.isoformat()} código={item.codigo}"
            )
        self.stdout.write("Evidencias candidatas del flujo manual de combustibles:")
        for item in evidences:
            self.stdout.write(
                f"  id={item.id} obra={item.obra_id} "
                f"fecha={item.created_at.isoformat()} nombre={item.nombre}"
            )

        if not options["delete_confirmed"]:
            self.stdout.write(
                self.style.WARNING("Modo auditoría: no se eliminó ningún registro.")
            )
            return
        if not options["activity_id"] and not options["evidence_id"]:
            raise CommandError(
                "Para eliminar debes indicar --activity-id y/o --evidence-id explícitos."
            )

        selected_activities = activities.filter(id__in=options["activity_id"])
        selected_evidences = evidences.filter(id__in=options["evidence_id"])
        if selected_activities.count() != len(set(options["activity_id"])):
            raise CommandError(
                "Una actividad indicada ya no cumple las condiciones de candidatura."
            )
        if selected_evidences.count() != len(set(options["evidence_id"])):
            raise CommandError(
                "Una evidencia indicada ya no cumple las condiciones de candidatura."
            )

        files = [
            (item.archivo.storage, item.archivo.name)
            for item in selected_evidences
            if item.archivo
        ]
        with transaction.atomic():
            activity_count = selected_activities.count()
            evidence_count = selected_evidences.count()
            selected_activities.delete()
            selected_evidences.delete()
        for storage, name in files:
            storage.delete(name)
        self.stdout.write(
            self.style.SUCCESS(
                "Eliminación confirmada: "
                f"{activity_count} actividades y {evidence_count} evidencias."
            )
        )
