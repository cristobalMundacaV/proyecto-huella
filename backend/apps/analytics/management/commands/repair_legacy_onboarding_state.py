"""Repair the STRUCTURAL side-effects of onboarding for tenants that have
real operational content (at least one obra) but were never (fully) taken
through the onboarding wizard (`apps.analytics.services.onboarding.
apply_onboarding_step`) — e.g. a demo/legacy tenant seeded directly via a
management command, which can have `onboarding_completado=True` hardcoded
without ever having created a single `AreaOperacional` or
`CapacidadOrganizacion` row.

Symptom this fixes: operational flows (Energía, Agua, Combustibles, …)
silently missing from an obra's navigation/cards because the organization
has zero `CapacidadOrganizacion` rows at all, so every capability reads as
"no_determinado" and gets treated the same as "not configured".

Guarantees:
- Idempotent — safe to re-run; a second run finds everything already in
  place and reports "nothing to repair" for every organization.
- Non-destructive — only ever *creates* missing rows via `get_or_create`;
  never updates or deletes an existing `AreaOperacional`/
  `CapacidadOrganizacion`, and never touches `onboarding_completado` or
  `onboarding_step` (those reflect the wizard flag, not this repair).
- Tenant-safe — operates strictly organization-by-organization; a genuinely
  new tenant (0 obras) is left untouched so the real onboarding wizard runs
  for it normally.
- Traceable — stamps `onboarding_data["reparacion_legacy"]` with what was
  created and when, without touching the wizard's own step keys ("1".."4").

New capacidades default to `PENDIENTE_DIAGNOSTICO` (never `APLICA`): this
command does not attempt to infer which flows actually have real data —
that would be a guess. Marking them pending makes every capability visible
(disabled + "requiere configuración"), never silently hidden, and a human
can confirm applicability afterwards exactly as the onboarding wizard's own
step 3 would.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.analytics.models import Organizacion
from apps.analytics.models.legacy import AreaOperacional, CapacidadOrganizacion
from apps.analytics.services.onboarding import AREA_CATALOGS, DEFAULT_AREA_CATALOG, ensure_flow_catalog


class Command(BaseCommand):
    help = (
        "Repara organizaciones con obras reales pero sin estructura de onboarding "
        "(areas operacionales / capacidades ambientales) — idempotente y no destructivo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--organizacion-id", dest="organizacion_id", default=None,
            help="Repara únicamente esta organización (por organizacion_id). Por defecto, todas.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Muestra qué se repararía sin escribir cambios.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        queryset = Organizacion.objects.all().order_by("nombre")
        if options["organizacion_id"]:
            queryset = queryset.filter(organizacion_id=options["organizacion_id"])

        repaired, skipped_new, skipped_complete = 0, 0, 0
        for organizacion in queryset:
            obras_count = organizacion.obras.count()
            if obras_count == 0:
                skipped_new += 1
                continue

            needs_areas = not organizacion.areas_operacionales.filter(activa=True).exists()
            needs_capacidades = not organizacion.capacidades_ambientales.exists()
            if not needs_areas and not needs_capacidades:
                skipped_complete += 1
                continue

            areas_created, capacidades_created = [], []
            if not dry_run:
                if needs_areas:
                    areas_created = self._create_recommended_areas(organizacion)
                if needs_capacidades:
                    capacidades_created = self._create_pending_capacidades(organizacion)
                self._stamp_repair(organizacion, areas_created, capacidades_created)

            repaired += 1
            self.stdout.write(self.style.SUCCESS(
                f"{'[dry-run] ' if dry_run else ''}{organizacion.nombre} ({organizacion.organizacion_id}): "
                f"obras={obras_count}, áreas_creadas={len(areas_created) if not dry_run else ('pendiente' if needs_areas else 0)}, "
                f"capacidades_creadas={len(capacidades_created) if not dry_run else ('pendiente' if needs_capacidades else 0)}"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"Listo. Reparadas: {repaired}. Sin obras (onboarding real corresponde): {skipped_new}. "
            f"Ya completas: {skipped_complete}."
        ))

    def _create_recommended_areas(self, organizacion):
        catalog = AREA_CATALOGS.get(organizacion.preset, DEFAULT_AREA_CATALOG)
        created = []
        for tipo, nombre, recomendada in catalog:
            if not recomendada:
                continue
            area, was_created = AreaOperacional.objects.get_or_create(
                organizacion=organizacion, tipo=tipo, defaults={"nombre": nombre, "activa": True},
            )
            if was_created:
                created.append(area.tipo)
        return created

    def _create_pending_capacidades(self, organizacion):
        catalog = ensure_flow_catalog()
        created = []
        for key, capacidad in catalog.items():
            relation, was_created = CapacidadOrganizacion.objects.get_or_create(
                organizacion=organizacion, capacidad=capacidad,
                defaults={"estado": CapacidadOrganizacion.Estado.PENDIENTE_DIAGNOSTICO},
            )
            if was_created:
                created.append(key)
        return created

    def _stamp_repair(self, organizacion, areas_created, capacidades_created):
        stored = dict(organizacion.onboarding_data or {})
        stored["reparacion_legacy"] = {
            "reparado_automaticamente": True,
            "areas_creadas": areas_created,
            "capacidades_creadas": capacidades_created,
            "fecha": timezone.localdate().isoformat(),
        }
        organizacion.onboarding_data = stored
        organizacion.save(update_fields=["onboarding_data"])
