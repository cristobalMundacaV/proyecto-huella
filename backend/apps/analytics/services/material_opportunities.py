"""Environmental opportunity detection (MI-01H): connects hotspots (01F),
comparable sets (01D) and the deterministic comparison (01E) to surface
"potential lower-A1-A3 opportunities." This is explicitly NOT a technical
recommendation — language stays opportunity/candidate/requires_review,
never "approved substitution," "best material" or "recommended for use."
Ranking is allowed only among alternatives already established as directly
comparable, on the single explicit metric of A1-A3 impact per functional
unit — never a black-box score, never mixing cost/schedule/logistics
(those authorities do not exist in this system)."""

from ..models import MaterialOperacional
from ..models.material_application_profile import MaterialApplicationProfile
from ..models.material_functional_use import MaterialFunctionalUse
from .material_comparable_sets import comparable_alternatives
from .material_environmental_comparison import compare_materials
from .material_hotspots import material_hotspots


def _approved_profiles_for_material(organization, material):
    return (
        MaterialFunctionalUse.objects.filter(
            organizacion=organization, material=material, estado=MaterialFunctionalUse.Estado.APROBADO,
        )
        .select_related("profile")
        .values_list("profile", flat=True)
        .distinct()
    )


def detect_opportunities(organization, *, work=None, start=None, end=None, categoria=None, standard=None):
    hotspots = material_hotspots(organization, work=work, start=start, end=end, categoria=categoria, standard=standard)
    all_materials = list(MaterialOperacional.objects.filter(organizacion=organization))
    opportunities = []

    for hotspot_rows in hotspots.values():
        for row in hotspot_rows["materiales"]:
            if row["positive_gwp"] <= 0 or row["material_id"] is None:
                continue
            material = next((m for m in all_materials if m.pk == row["material_id"]), None)
            if material is None:
                continue

            for profile_id in _approved_profiles_for_material(organization, material):
                profile = MaterialApplicationProfile.objects.filter(
                    pk=profile_id, organizacion=organization, estado=MaterialApplicationProfile.Estado.APROBADO,
                ).first()
                if profile is None:
                    continue

                candidates = [m for m in all_materials if m.pk != material.pk]
                comparable = comparable_alternatives(organization, material, profile, candidates)
                if not comparable["source_eligible"]:
                    continue

                alternatives = []
                for entry in comparable["comparable_candidates"]:
                    alt_material = next((m for m in all_materials if m.pk == entry["material_id"]), None)
                    if alt_material is None:
                        continue
                    comparison = compare_materials(organization, material, alt_material, profile)
                    if not comparison["comparable"]:
                        continue
                    alternatives.append({
                        "alternative_material_id": alt_material.pk,
                        "baseline_impact_per_functional_unit": comparison["baseline"]["impact_a1a3_per_functional_unit"],
                        "alternative_impact_per_functional_unit": comparison["alternative"]["impact_a1a3_per_functional_unit"],
                        "absolute_delta": comparison["absolute_delta"],
                        "relative_delta": comparison["relative_delta"],
                        "quality_estado": entry["chain"]["quality_estado"],
                        "warnings": comparison["warnings"],
                    })

                # Deterministic ordering by the single explicit metric only.
                alternatives.sort(key=lambda item: item["alternative_impact_per_functional_unit"])

                # A hotspot with no comparable alternative is still reported
                # — silently dropping it would hide the (equally useful)
                # finding "this hotspot currently has no approved comparable
                # alternative."
                opportunities.append({
                    "hotspot_material_id": material.pk,
                    "profile_id": profile.pk,
                    "functional_unit": profile.unidad_funcional,
                    "hotspot_positive_gwp": row["positive_gwp"],
                    "hotspot_share": row["hotspot_share"],
                    "alternatives": alternatives,
                    "excluded_alternatives": comparable["excluded_candidates"],
                })

    return opportunities
