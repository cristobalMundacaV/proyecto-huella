from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import (
    EnvironmentalFactorCandidate,
    EnvironmentalFactorReconciliation,
    FactorAmbiental,
    VersionFactorAmbiental,
)
from .factor_candidates import (
    _factor_value_for_unit,
    apply_candidate_mapping,
    equivalent_global_factors,
    promote_candidate_to_draft,
)
from .factor_governance import transition_factor_version

EXPECTED_SHA = "8caaeed89d08202f47894842e4a4e5274b4bca54b25186501efe9fd0d05b1ca0"
MATERIAL_CHANGE_RATIO_UPPER = Decimal("10")
MATERIAL_CHANGE_RATIO_LOWER = Decimal("0.1")

RECONCILIATION_MANIFEST = (
    {
        "row": 28,
        "factor_code": "huellachile-combustion-estacionaria-glp",
        "activity": "Gas licuado de petróleo",
        "scope": "Emisiones directas",
        "activity_unit": "metros cúbicos",
        "factor_unit": "kgCO2e/metros cúbicos",
        "mapping_type": "combustible",
        "mapping_context": {
            "alcance": 1,
            "categoria_huella": "combustion_estacionaria",
            "combustible": "glp",
        },
    },
    {
        "row": 30,
        "factor_code": "huellachile-combustion-estacionaria-gas-natural",
        "activity": "Gas natural",
        "scope": "Emisiones directas",
        "activity_unit": "metros cúbicos",
        "factor_unit": "kgCO2e/metros cúbicos",
        "mapping_type": "combustible",
        "mapping_context": {
            "alcance": 1,
            "categoria_huella": "combustion_estacionaria",
            "combustible": "gas_natural",
        },
    },
    {
        "row": 36,
        "factor_code": "huellachile-combustion-estacionaria-diesel",
        "activity": "Petróleo 2 (Diésel)",
        "scope": "Emisiones directas",
        "activity_unit": "metros cúbicos",
        "factor_unit": "kgCO2e/metros cúbicos",
        "mapping_type": "combustible",
        "mapping_context": {
            "alcance": 1,
            "categoria_huella": "combustion_estacionaria",
            "combustible": "diesel",
        },
    },
    {
        "row": 42,
        "factor_code": "huellachile-combustion-movil-diesel",
        "activity": "Petróleo 2 (Diesel)",
        "scope": "Emisiones directas",
        "activity_unit": "metros cúbicos",
        "factor_unit": "kgCO2e/metros cúbicos",
        "mapping_type": "combustible",
        "mapping_context": {
            "alcance": 1,
            "categoria_huella": "combustion_movil",
            "combustible": "diesel",
        },
    },
    {
        "row": 44,
        "factor_code": "huellachile-combustion-movil-glp",
        "activity": "Gas licuado",
        "scope": "Emisiones directas",
        "activity_unit": "metros cúbicos",
        "factor_unit": "kgCO2e/metros cúbicos",
        "mapping_type": "combustible",
        "mapping_context": {
            "alcance": 1,
            "categoria_huella": "combustion_movil",
            "combustible": "glp",
        },
    },
    {
        "row": 46,
        "factor_code": "huellachile-combustion-movil-gas-natural",
        "activity": "Gas natural",
        "scope": "Emisiones directas",
        "activity_unit": "metros cúbicos",
        "factor_unit": "kgCO2e/metros cúbicos",
        "mapping_type": "combustible",
        "mapping_context": {
            "alcance": 1,
            "categoria_huella": "combustion_movil",
            "combustible": "gas_natural",
        },
    },
    {
        "row": 187,
        "factor_code": "sen-electricidad-red-location-based-2025",
        "activity": "Sistema Eléctrico Nacional",
        "scope": "Emisiones indirectas por energía importada",
        "activity_unit": "MWh",
        "factor_unit": "kgCO2e/MWh",
        "mapping_type": "energia_red",
        "mapping_context": {
            "alcance": 2,
            "sistema": "SEN",
            "metodo": "location_based",
            "pais": "Chile",
        },
    },
)


def _manifest_rows(year=2025, confirm_sha=None):
    from apps.knowledge.models import HuellaChileEmissionFactorFact

    if year != 2025:
        raise ValidationError("Esta reconciliación sólo admite dataset_year=2025.")
    if confirm_sha is not None and confirm_sha != EXPECTED_SHA:
        raise ValidationError("SHA de confirmación incorrecto.")
    result = []
    for entry in RECONCILIATION_MANIFEST:
        facts = HuellaChileEmissionFactorFact.objects.select_related("artifact").filter(
            dataset_year=year,
            source_row_number=entry["row"],
            artifact__is_current=True,
            artifact__content_sha256=EXPECTED_SHA,
        )
        if facts.count() != 1:
            raise ValidationError(
                f"Manifest fila {entry['row']}: fact current único no encontrado."
            )
        fact = facts.get()
        expected = {
            "actividad": entry["activity"],
            "alcance": entry["scope"],
            "categoria": (
                "2.1 Electricidad"
                if entry["row"] == 187
                else (
                    "1.1 Combustión estacionaria"
                    if entry["row"] < 40
                    else "1.2 Combustión móvil"
                )
            ),
            "unidad_actividad": entry["activity_unit"],
            "unidad_factor": entry["factor_unit"],
        }
        differences = [
            field for field, value in expected.items() if getattr(fact, field) != value
        ]
        if differences:
            raise ValidationError(
                f"Manifest fila {entry['row']} incompatible: {', '.join(differences)}."
            )
        if fact.factor_value is None:
            raise ValidationError(
                f"Manifest fila {entry['row']} no contiene factor numérico."
            )
        factor = FactorAmbiental.objects.get(
            organizacion=None, codigo=entry["factor_code"]
        )
        candidate = (
            EnvironmentalFactorCandidate.objects.select_related("source_fact__artifact")
            .filter(source_fact=fact)
            .first()
        )
        active_versions = factor.versiones.filter(
            estado=VersionFactorAmbiental.Estado.ACTIVO
        ).order_by("-version")
        active = active_versions.first() if active_versions.count() == 1 else None
        reconciliation = (
            EnvironmentalFactorReconciliation.objects.filter(
                candidate=candidate
            ).first()
            if candidate
            else None
        )
        result.append(
            {
                "entry": entry,
                "fact": fact,
                "factor": factor,
                "candidate": candidate,
                "legacy": reconciliation.legacy_version if reconciliation else active,
                "reconciliation": reconciliation,
            }
        )
    return result


def reconciliation_report(year=2025):
    rows = _manifest_rows(year)
    report = []
    for row in rows:
        factor, fact, candidate, legacy = (
            row["factor"],
            row["fact"],
            row["candidate"],
            row["legacy"],
        )
        normalized = _factor_value_for_unit(
            fact.factor_value, "kgCO2e", factor.unidad_resultado
        )
        delta = normalized - legacy.valor if legacy else None
        delta_percentage = (
            delta / legacy.valor * Decimal("100") if legacy and legacy.valor else None
        )
        change_ratio = (
            abs(normalized / legacy.valor) if legacy and legacy.valor else None
        )
        requires_explicit_ack = change_ratio is not None and (
            change_ratio >= MATERIAL_CHANGE_RATIO_UPPER
            or change_ratio <= MATERIAL_CHANGE_RATIO_LOWER
        )
        equivalence = "sin_mapping"
        if candidate:
            candidate.mapping_type = row["entry"]["mapping_type"]
            candidate.mapping_context = {
                "proveedor": "HuellaChile",
                **row["entry"]["mapping_context"],
            }
            equivalence = equivalent_global_factors(candidate)["status"]
        readiness = (
            "ready"
            if candidate
            and legacy
            and equivalence == "equivalente_unico"
            and equivalent_global_factors(candidate)["factors"][0].id == factor.id
            else "blocked"
        )
        report.append(
            {
                "factor_code": factor.codigo,
                "active_version": legacy.version if legacy else None,
                "legacy_value": str(legacy.valor) if legacy else None,
                "fact_row": fact.source_row_number,
                "official_value": str(fact.factor_value),
                "normalized_official_value": str(normalized),
                "legacy_result_unit": factor.unidad_resultado,
                "official_result_unit": "kgCO2e",
                "normalized_result_unit": factor.unidad_resultado,
                "delta": str(delta) if delta is not None else None,
                "delta_percentage": (
                    str(delta_percentage) if delta_percentage is not None else None
                ),
                "change_ratio": str(change_ratio) if change_ratio is not None else None,
                "requires_explicit_ack": requires_explicit_ack,
                "anomaly_reason": (
                    "material_legacy_factor_change" if requires_explicit_ack else None
                ),
                "candidate_status": candidate.status if candidate else "missing",
                "equivalence": (equivalence),
                "readiness": readiness,
            }
        )
    return report


@transaction.atomic
def prepare_reconciliation(
    user, year, confirm_sha, note="", acknowledged_material_changes=None
):
    if not user.is_superuser:
        raise ValidationError("El reviewer debe ser superusuario.")
    rows = _manifest_rows(year, confirm_sha)
    acknowledged = set(acknowledged_material_changes or [])
    report_by_code = {item["factor_code"]: item for item in reconciliation_report(year)}
    required_acknowledgements = {
        code for code, item in report_by_code.items() if item["requires_explicit_ack"]
    }
    missing = required_acknowledgements - acknowledged
    if missing:
        raise ValidationError(
            "Cambios materiales requieren reconocimiento explícito para: "
            + ", ".join(sorted(missing))
        )
    created = 0
    for row in rows:
        entry, candidate, factor, legacy = (
            row["entry"],
            row["candidate"],
            row["factor"],
            row["legacy"],
        )
        if not candidate or not legacy:
            raise ValidationError(
                f"{factor.codigo}: faltan candidate o versión legacy activa."
            )
        existing = row["reconciliation"]
        if existing:
            if (
                existing.factor_id != factor.id
                or existing.replacement_version_id != candidate.promoted_version_id
            ):
                raise ValidationError(
                    f"{factor.codigo}: reconciliación existente incompatible."
                )
            continue
        if candidate.promoted_version_id:
            raise ValidationError(
                f"{factor.codigo}: candidate promovido fuera de esta reconciliación."
            )
        candidate = apply_candidate_mapping(
            candidate, user, entry["mapping_type"], entry["mapping_context"], note
        )
        equivalence = equivalent_global_factors(candidate)
        if (
            equivalence["status"] != "equivalente_unico"
            or equivalence["factors"][0].id != factor.id
        ):
            raise ValidationError(
                f"{factor.codigo}: equivalencia gobernada inesperada."
            )
        _, replacement = promote_candidate_to_draft(
            candidate, user, "new_version", factor
        )
        replacement.refresh_from_db()
        official = replacement.valor
        delta = official - legacy.valor
        percentage = (delta / legacy.valor * Decimal("100")) if legacy.valor else None
        report_item = report_by_code[factor.codigo]
        acknowledged_at = timezone.now()
        EnvironmentalFactorReconciliation.objects.create(
            candidate=candidate,
            factor=factor,
            legacy_version=legacy,
            replacement_version=replacement,
            source_artifact_sha=EXPECTED_SHA,
            comparison={
                "legacy_value": str(legacy.valor),
                "replacement_value": str(official),
                "input_unit": factor.unidad_entrada,
                "result_unit": factor.unidad_resultado,
                "absolute_difference": str(delta),
                "percentage_difference": (
                    str(percentage) if percentage is not None else None
                ),
                "legacy_result_unit": report_item["legacy_result_unit"],
                "official_result_unit": report_item["official_result_unit"],
                "normalized_result_unit": report_item["normalized_result_unit"],
                "change_ratio": report_item["change_ratio"],
                "requires_explicit_ack": report_item["requires_explicit_ack"],
                "anomaly_reason": report_item["anomaly_reason"],
                "material_change_acknowledged": (
                    factor.codigo in required_acknowledgements
                ),
                "acknowledged_factor_code": (
                    factor.codigo
                    if factor.codigo in required_acknowledgements
                    else None
                ),
                "acknowledged_by": (
                    user.username
                    if factor.codigo in required_acknowledgements
                    else None
                ),
                "acknowledged_at": (
                    acknowledged_at.isoformat()
                    if factor.codigo in required_acknowledgements
                    else None
                ),
                "legacy_source": legacy.fuente,
                "legacy_reference": legacy.referencia,
                "replacement_provenance": replacement.contexto.get("knowledge_source"),
                "candidate_id": candidate.id,
                "fact_id": candidate.source_fact_id,
                "artifact_id": candidate.source_fact.artifact_id,
            },
            prepared_by=user,
            note=note,
        )
        created += 1
    return {"created": created, "existing": len(rows) - created}


@transaction.atomic
def advance_reconciliation(user, target, year=2025):
    if not user.is_superuser:
        raise ValidationError("El reviewer debe ser superusuario.")
    rows = _manifest_rows(year)
    changed = []
    for row in rows:
        reconciliation = row["reconciliation"]
        if not reconciliation:
            raise ValidationError("La reconciliación no está preparada completamente.")
        version = transition_factor_version(reconciliation.replacement_version, target)
        changed.append((reconciliation.factor.codigo, version.estado))
    return changed


@transaction.atomic
def switch_reconciliation(user, year, confirm_sha):
    if not user.is_superuser:
        raise ValidationError("El reviewer debe ser superusuario.")
    rows = _manifest_rows(year, confirm_sha)
    reconciliations = list(
        EnvironmentalFactorReconciliation.objects.select_for_update()
        .select_related("legacy_version", "replacement_version", "factor")
        .filter(candidate__source_fact__in=[row["fact"] for row in rows])
    )
    if len(reconciliations) != len(RECONCILIATION_MANIFEST):
        raise ValidationError("Se requieren siete reconciliaciones preparadas.")
    list(
        FactorAmbiental.objects.select_for_update().filter(
            pk__in=[item.factor_id for item in reconciliations]
        )
    )
    for item in reconciliations:
        if item.status == item.Status.SWITCHED:
            continue
        legacy = VersionFactorAmbiental.objects.select_for_update().get(
            pk=item.legacy_version_id
        )
        replacement = VersionFactorAmbiental.objects.select_for_update().get(
            pk=item.replacement_version_id
        )
        if (
            legacy.factor_id != item.factor_id
            or replacement.factor_id != item.factor_id
            or legacy.estado != legacy.Estado.ACTIVO
            or replacement.estado != replacement.Estado.VALIDADO
        ):
            raise ValidationError(
                f"{item.factor.codigo}: estados o identidad incompatibles para switch."
            )
        active_ids = list(
            item.factor.versiones.filter(estado=VersionFactorAmbiental.Estado.ACTIVO)
            .order_by("id")
            .values_list("id", flat=True)
        )
        if active_ids != [legacy.id]:
            raise ValidationError(
                f"{item.factor.codigo}: existe una versión activa inesperada."
            )
    for item in reconciliations:
        if item.status == item.Status.SWITCHED:
            continue
        transition_factor_version(
            item.legacy_version, VersionFactorAmbiental.Estado.OBSOLETO
        )
        transition_factor_version(
            item.replacement_version, VersionFactorAmbiental.Estado.ACTIVO
        )
        item.status = item.Status.SWITCHED
        item.switched_by = user
        item.switched_at = timezone.now()
        item.save(update_fields=["status", "switched_by", "switched_at"])
    return reconciliations
