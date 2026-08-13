from collections import defaultdict
from decimal import Decimal
from math import sqrt

from django.db.models import Sum

from apps.analytics.models import ConfiguracionOrganizacion, DatoACV, RegistroEmision


ZERO = Decimal("0")


def valid_accountable_records(organizacion, *, start=None, end=None):
    queryset = RegistroEmision.objects.filter(
        organizacion=organizacion,
        contabilizable=True,
        estado_validacion=RegistroEmision.EstadoValidacion.VALIDADO,
    )
    if start:
        queryset = queryset.filter(fecha__gte=start)
    if end:
        queryset = queryset.filter(fecha__lte=end)
    return queryset


def _pct(current, reference):
    if not reference:
        return None
    return ((current - reference) / reference * Decimal("100")).quantize(Decimal("0.01"))


def _series(records):
    monthly = defaultdict(Decimal)
    for record in records:
        monthly[record.fecha.strftime("%Y-%m")] += record.emisiones_kg_co2e
    return [{"periodo": key, "co2e_kg": value} for key, value in sorted(monthly.items())]


def _anomalies(series):
    values = [float(item["co2e_kg"]) for item in series]
    if len(values) < 3:
        return []
    mean = sum(values) / len(values)
    deviation = sqrt(sum((value - mean) ** 2 for value in values) / len(values))
    if deviation == 0:
        return []
    return [{**item, "z_score": round((float(item["co2e_kg"]) - mean) / deviation, 3)} for item in series if abs((float(item["co2e_kg"]) - mean) / deviation) >= 2]


def calculate_environmental_metrics(organizacion, *, start=None, end=None, intensity_denominator=None, intensity_unit="unidad"):
    records = list(valid_accountable_records(organizacion, start=start, end=end).order_by("fecha", "id"))
    total = sum((record.emisiones_kg_co2e for record in records), ZERO)
    categories, activities = defaultdict(Decimal), defaultdict(Decimal)
    for record in records:
        categories[record.categoria] += record.emisiones_kg_co2e
        activities[record.fuente_emision] += record.emisiones_kg_co2e
    series = _series(records)
    baseline = series[0]["co2e_kg"] if series else None
    current = series[-1]["co2e_kg"] if series else None
    previous = series[-2]["co2e_kg"] if len(series) > 1 else None
    all_governed = RegistroEmision.objects.filter(organizacion=organizacion)
    complete = all_governed.exclude(fecha=None).exclude(fuente_emision="").exclude(unidad="").count()
    coverage = Decimal(complete * 100) / Decimal(all_governed.count()) if all_governed.count() else ZERO
    config, _ = ConfiguracionOrganizacion.objects.get_or_create(organizacion=organizacion)
    target = config.meta_emisiones_kg_co2e
    denominator = Decimal(str(intensity_denominator)) if intensity_denominator not in (None, "", 0, "0") else None
    return {
        "organizacion_id": organizacion.organizacion_id,
        "periodo": {"desde": start, "hasta": end},
        "co2e_total_kg": total,
        "registros_contabilizados": len(records),
        "por_categoria": dict(sorted(categories.items())),
        "por_actividad": dict(sorted(activities.items())),
        "serie_mensual": series,
        "linea_base": baseline,
        "tendencia": {"actual": current, "anterior": previous, "variacion_pct": _pct(current, previous) if current is not None else None},
        "antes_despues": {"antes": baseline, "despues": current, "variacion_pct": _pct(current, baseline) if current is not None else None},
        "intensidad": {"valor": total / denominator if denominator else None, "unidad": f"kgCO2e/{intensity_unit}", "denominador": denominator},
        "meta": {"valor_kg_co2e": target, "cumple": total <= target if target is not None else None, "variacion_pct": _pct(total, target) if target else None},
        "cobertura_datos_pct": coverage.quantize(Decimal("0.01")),
        "anomalias": _anomalies(series),
    }


def calculate_partial_lca(organizacion, *, material_producto=None):
    queryset = DatoACV.objects.filter(organizacion=organizacion)
    if material_producto:
        queryset = queryset.filter(material_producto__iexact=material_producto)
    by_stage = {row["etapa"]: {"valor": row["total"], "unidad": row["unidad"]} for row in queryset.values("etapa", "unidad").annotate(total=Sum("valor"))}
    available = set(queryset.values_list("etapa", flat=True))
    total_stages = len(DatoACV.Etapa.values)
    return {
        "organizacion_id": organizacion.organizacion_id,
        "material_producto": material_producto,
        "etapas": by_stage,
        "etapas_disponibles": sorted(available),
        "etapas_faltantes": [stage for stage in DatoACV.Etapa.values if stage not in available],
        "cobertura_etapas_pct": (Decimal(len(available) * 100) / Decimal(total_stages)).quantize(Decimal("0.01")),
        "completo": len(available) == total_stages,
    }
