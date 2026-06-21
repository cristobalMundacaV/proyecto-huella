from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.db.models import Count, Sum

from apps.analytics.models import (
    AlertaCumplimientoAmbiental,
    DocumentoAmbiental,
    LoteForestal,
    Obra,
    RegistroEmision,
    VariableAmbientalExtraida,
)


AVAILABLE = "available"
MISSING = "missing"
PARTIAL = "partial"
ALERT = "alert"


def decimal_or_none(value):
    if value is None:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None


def as_float(value):
    if value is None:
        return None
    return float(value)


def round_float(value, digits=2):
    if value is None:
        return None
    return round(float(value), digits)


def normalize(value):
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )


def detect_industry_key(constructora):
    rubro = normalize(constructora.rubro)
    preset = normalize(constructora.preset)
    if "mineria" in rubro or "minera" in rubro:
        return "mineria"
    if "energia" in rubro or "generacion" in rubro:
        return "energia"
    if preset == "aserradero" or "forestal" in rubro:
        return "forestal_aserradero"
    if preset == "transporte":
        return "transporte"
    if preset == "construccion":
        return "construccion"
    return "industrial_agroindustria"


def kpi_card(kpi_id, label, value, unit, status, reason, source, priority="medium"):
    return {
        "id": kpi_id,
        "label": label,
        "value": round_float(value) if isinstance(value, (Decimal, float, int)) else value,
        "unit": unit,
        "status": status,
        "reason": reason,
        "source": source,
        "priority": priority,
    }


def available_card(kpi_id, label, value, unit, reason, source, priority="medium"):
    return kpi_card(kpi_id, label, value, unit, AVAILABLE, reason, source, priority)


def missing_card(kpi_id, label, unit, reason, source, priority="medium"):
    return kpi_card(kpi_id, label, None, unit, MISSING, reason, source, priority)


def alert_card(kpi_id, label, value, unit, reason, source, priority="high"):
    return kpi_card(kpi_id, label, value, unit, ALERT, reason, source, priority)


def variable_latest(variables, *ids):
    normalized_ids = {normalize(item) for item in ids}
    for variable in variables:
        if normalize(variable.variable_id) in normalized_ids:
            return variable
    return None


def variable_sum(variables, *ids):
    normalized_ids = {normalize(item) for item in ids}
    values = [
        variable.valor
        for variable in variables
        if normalize(variable.variable_id) in normalized_ids and variable.valor is not None
    ]
    if not values:
        return None
    return sum(values, Decimal("0"))


def variable_status_count(variables, ids):
    normalized_ids = {normalize(item) for item in ids}
    return sum(
        1
        for variable in variables
        if normalize(variable.variable_id) in normalized_ids
        and variable.estado_cumplimiento in {"alerta", "incumple"}
    )


def registro_sum(registros, *, unidad_contains=None, categoria_contains=None, field="cantidad"):
    total = Decimal("0")
    found = False
    for registro in registros:
        if unidad_contains and unidad_contains not in normalize(registro.unidad):
            continue
        if categoria_contains and categoria_contains not in normalize(registro.categoria):
            continue
        value = decimal_or_none(getattr(registro, field, None))
        if value is None:
            continue
        total += value
        found = True
    return total if found else None


def emisiones_sum(registros, *, categoria_contains=None):
    total = Decimal("0")
    found = False
    for registro in registros:
        if categoria_contains and categoria_contains not in normalize(registro.categoria):
            continue
        value = decimal_or_none(registro.emisiones_kg_co2e)
        if value is None:
            continue
        total += value
        found = True
    return total if found else None


def build_common_context(constructora):
    registros = list(
        RegistroEmision.objects.filter(constructora=constructora).select_related("obra", "etapa")
    )
    documentos = DocumentoAmbiental.objects.filter(constructora=constructora)
    variables = list(
        VariableAmbientalExtraida.objects.filter(constructora=constructora, valor__isnull=False).order_by(
            "-fecha_medicion", "-created_at"
        )
    )
    alertas_abiertas = AlertaCumplimientoAmbiental.objects.filter(
        constructora=constructora,
        estado__in=[
            AlertaCumplimientoAmbiental.Estado.ABIERTA,
            AlertaCumplimientoAmbiental.Estado.EN_REVISION,
        ],
    )
    total_kg = sum((registro.emisiones_kg_co2e or Decimal("0")) for registro in registros)
    fechas = [registro.fecha for registro in registros if registro.fecha]

    return {
        "registros": registros,
        "documentos": documentos,
        "variables": variables,
        "alertas_abiertas": alertas_abiertas,
        "total_kg": total_kg,
        "periodo": {
            "desde": min(fechas).isoformat() if fechas else None,
            "hasta": max(fechas).isoformat() if fechas else None,
        },
    }


def build_top_sources(registros, total_kg):
    grouped = defaultdict(Decimal)
    for registro in registros:
        grouped[registro.fuente_emision or "Sin fuente"] += registro.emisiones_kg_co2e or Decimal("0")
    return [
        {
            "label": label,
            "value": round_float(value),
            "unit": "kgCO2e",
            "share_pct": round_float((value / total_kg) * Decimal("100")) if total_kg else None,
        }
        for label, value in sorted(grouped.items(), key=lambda item: item[1], reverse=True)[:5]
        if value > 0
    ]


def build_top_categories(registros, total_kg):
    grouped = defaultdict(Decimal)
    for registro in registros:
        grouped[registro.categoria or "Otros"] += registro.emisiones_kg_co2e or Decimal("0")
    return [
        {
            "label": label,
            "value": round_float(value),
            "unit": "kgCO2e",
            "share_pct": round_float((value / total_kg) * Decimal("100")) if total_kg else None,
        }
        for label, value in sorted(grouped.items(), key=lambda item: item[1], reverse=True)
        if value > 0
    ]


def build_summary(constructora, context):
    documentos = context["documentos"]
    alertas = context["alertas_abiertas"]
    total_kg = context["total_kg"]
    return {
        "huella_total_kg_co2e": round_float(total_kg),
        "huella_total_tco2e": round_float(total_kg / Decimal("1000")),
        "total_registros": len(context["registros"]),
        "total_documentos": documentos.count(),
        "documentos_validados": documentos.filter(estado_validacion="valido").count(),
        "documentos_pendientes": documentos.filter(estado_validacion__in=["pendiente", "observado"]).count(),
        "total_variables": len(context["variables"]),
        "alertas_abiertas": alertas.count(),
        "alertas_rojas": alertas.filter(severidad="rojo").count(),
        "alertas_amarillas": alertas.filter(severidad="amarillo").count(),
    }


def total_footprint_card(kpi_id, label, total_kg, reason):
    if total_kg is None or total_kg == 0:
        return missing_card(kpi_id, label, "tCO2e", "Requiere registros de emision calculados.", "registro_emision", "high")
    return available_card(kpi_id, label, total_kg / Decimal("1000"), "tCO2e", reason, "registro_emision", "high")


def common_data_gaps(cards, summary):
    gaps = [card["reason"] for card in cards if card["status"] == MISSING]
    if summary["documentos_pendientes"] > 0:
        gaps.append("Hay documentos ambientales pendientes u observados.")
    if summary["total_variables"] == 0:
        gaps.append("No hay variables ambientales extraidas para evaluar limites.")
    return gaps[:6]


def common_next_actions(cards, summary):
    actions = []
    missing = [card for card in cards if card["status"] == MISSING]
    if missing:
        actions.append(f"Completar dato requerido para {missing[0]['label']}.")
    if summary["alertas_rojas"] > 0:
        actions.append("Priorizar cierre de alertas rojas abiertas.")
    if summary["documentos_pendientes"] > 0:
        actions.append("Validar documentos ambientales pendientes u observados.")
    if not actions:
        actions.append("Mantener trazabilidad documental y revisar variaciones del periodo.")
    return actions[:5]


def build_construccion_cards(constructora, context):
    registros = context["registros"]
    variables = context["variables"]
    total_kg = context["total_kg"]
    superficie = Obra.objects.filter(constructora=constructora).aggregate(total=Sum("superficie_m2"))["total"]
    diesel = variable_sum(variables, "diesel_l") or registro_sum(registros, unidad_contains="litros diesel")
    rcd = variable_sum(variables, "rcd_ton")
    noise_alerts = variable_status_count(variables, ["noise_db", "ruido_db"])
    cards = [total_footprint_card("huella_total_obra", "Huella total obra", total_kg, "Suma de emisiones de registros de obra.")]
    if superficie:
        cards.append(available_card("huella_m2", "Huella por m2", total_kg / superficie, "kgCO2e/m2", "Calculado con superficie total de obras.", "calculado", "high"))
    else:
        cards.append(missing_card("huella_m2", "Huella por m2", "kgCO2e/m2", "Requiere superficie m2 de obra.", "calculado", "high"))
    cards.append(available_card("combustible_mes", "Combustible consumido", diesel, "L", "Litros desde variables o registros diesel.", "variable_ambiental" if variable_sum(variables, "diesel_l") is not None else "registro_emision") if diesel is not None else missing_card("combustible_mes", "Combustible consumido", "L", "Requiere variable diesel_l o registros en litros diesel.", "variable_ambiental"))
    cards.append(available_card("rcd_generado", "RCD generado", rcd, "ton", "Variable rcd_ton registrada.", "variable_ambiental") if rcd is not None else missing_card("rcd_generado", "RCD generado", "ton", "Requiere variable rcd_ton.", "variable_ambiental"))
    docs_pending = context["documentos"].filter(estado_validacion__in=["pendiente", "observado"]).count()
    cards.append(available_card("docs_faltantes", "Documentos pendientes", docs_pending, "docs", "Documentos pendientes u observados.", "documento_ambiental", "medium") if docs_pending else available_card("docs_faltantes", "Documentos pendientes", None, "docs", "No hay documentos pendientes u observados.", "documento_ambiental", "low"))
    cards.append(alert_card("alertas_ruido", "Alertas ruido", noise_alerts, "alertas", "Variables de ruido en alerta o incumplimiento.", "variable_ambiental") if noise_alerts else available_card("alertas_ruido", "Alertas ruido", None, "alertas", "Sin alertas de ruido registradas.", "variable_ambiental", "low"))
    return cards


def build_transporte_cards(context):
    registros = context["registros"]
    variables = context["variables"]
    total_kg = context["total_kg"]
    transporte_kg = emisiones_sum(registros, categoria_contains="transporte") or total_kg
    viajes = len([registro for registro in registros if "transporte" in normalize(registro.categoria)])
    km = variable_sum(variables, "km_traveled") or registro_sum(registros, categoria_contains="transporte", field="distancia_km")
    litros = variable_sum(variables, "diesel_l") or registro_sum(registros, unidad_contains="litros diesel")
    tire_waste = variable_sum(variables, "tire_waste_kg")
    cards = [total_footprint_card("huella_total_flota", "Huella total flota", total_kg, "Suma de emisiones de flota.")]
    cards.append(available_card("emisiones_por_viaje", "Emisiones por viaje", transporte_kg / viajes, "kgCO2e/viaje", "Calculado con registros de transporte.", "calculado", "high") if viajes and transporte_kg is not None else missing_card("emisiones_por_viaje", "Emisiones por viaje", "kgCO2e/viaje", "Requiere registros tipo transporte.", "registro_emision"))
    cards.append(available_card("emisiones_por_km", "Emisiones por km", transporte_kg / km, "kgCO2e/km", "Calculado con km recorridos.", "calculado", "high") if km and transporte_kg is not None else missing_card("emisiones_por_km", "Emisiones por km", "kgCO2e/km", "Requiere km_traveled o distancia_km.", "variable_ambiental"))
    cards.append(available_card("rendimiento_km_l", "Rendimiento", km / litros, "km/L", "Calculado con km y litros diesel.", "calculado", "high") if km and litros else missing_card("rendimiento_km_l", "Rendimiento", "km/L", "Requiere kilometros y litros diesel.", "calculado"))
    cards.append(available_card("litros_consumidos", "Litros consumidos", litros, "L", "Litros desde variables o registros.", "variable_ambiental") if litros is not None else missing_card("litros_consumidos", "Litros consumidos", "L", "Requiere diesel_l o registros en litros diesel.", "variable_ambiental"))
    cards.append(available_card("residuos_rep", "Residuos REP", tire_waste, "kg", "Variable tire_waste_kg registrada.", "variable_ambiental") if tire_waste is not None else missing_card("residuos_rep", "Residuos REP", "kg", "Requiere variable tire_waste_kg.", "variable_ambiental"))
    return cards


def build_forestal_cards(constructora, context):
    registros = context["registros"]
    variables = context["variables"]
    total_kg = context["total_kg"]
    volume = variable_sum(variables, "wood_volume_m3") or LoteForestal.objects.filter(constructora=constructora).aggregate(total=Sum("volumen_m3"))["total"] or registro_sum(registros, unidad_contains="m3")
    energia = registro_sum(registros, unidad_contains="kwh")
    biomass = variable_sum(variables, "biomass_boiler_ton")
    sawdust = variable_sum(variables, "sawdust_ton", "bark_ton")
    noise = variable_latest(variables, "noise_db", "ruido_db")
    cards = [total_footprint_card("huella_total_planta", "Huella total planta", total_kg, "Suma de emisiones de planta forestal.")]
    cards.append(available_card("huella_m3_madera", "Huella por m3 madera", total_kg / volume, "kgCO2e/m3", "Calculado con volumen de madera.", "calculado", "high") if volume else missing_card("huella_m3_madera", "Huella por m3 madera", "kgCO2e/m3", "Requiere wood_volume_m3, lotes forestales o registros m3.", "calculado", "high"))
    cards.append(available_card("energia_m3", "Energia por m3", energia / volume, "kWh/m3", "Calculado con energia y volumen.", "calculado") if energia and volume else missing_card("energia_m3", "Energia por m3", "kWh/m3", "Requiere energia kWh y volumen m3.", "calculado"))
    cards.append(available_card("biomasa_caldera", "Biomasa caldera", biomass, "ton", "Variable biomass_boiler_ton registrada.", "variable_ambiental") if biomass is not None else missing_card("biomasa_caldera", "Biomasa caldera", "ton", "Requiere variable biomass_boiler_ton.", "variable_ambiental"))
    cards.append(available_card("residuos_valorizables", "Residuos valorizables", sawdust, "ton", "Variables sawdust_ton/bark_ton registradas.", "variable_ambiental") if sawdust is not None else missing_card("residuos_valorizables", "Residuos valorizables", "ton", "Requiere sawdust_ton o bark_ton.", "variable_ambiental"))
    cards.append(available_card("ruido_planta", "Ruido planta", noise.valor, noise.unidad or "dB", "Ultima medicion de ruido registrada.", "variable_ambiental") if noise else missing_card("ruido_planta", "Ruido planta", "dB", "Requiere variable noise_db o ruido_db.", "variable_ambiental"))
    return cards


def build_industrial_cards(context):
    registros = context["registros"]
    variables = context["variables"]
    total_kg = context["total_kg"]
    energia = registro_sum(registros, unidad_contains="kwh")
    combustible = registro_sum(registros, unidad_contains="litros")
    respel = variable_sum(variables, "respel_kg")
    residuos_no_peligrosos = registro_sum(registros, categoria_contains="residuos", unidad_contains="kg")
    agua = variable_sum(variables, "water_m3", "agua_m3") or registro_sum(registros, unidad_contains="m3", categoria_contains="agua")
    riles_alerts = variable_status_count(variables, ["ph", "dbo5", "dqo", "sst"])
    docs_pending = context["documentos"].filter(estado_validacion__in=["pendiente", "observado"]).count()
    cards = [total_footprint_card("huella_total_planta", "Huella total planta", total_kg, "Suma de emisiones industriales.")]
    cards.append(available_card("energia_total", "Energia total", energia, "kWh", "Energia desde registros kWh.", "registro_emision") if energia is not None else missing_card("energia_total", "Energia total", "kWh", "Requiere registros en kWh.", "registro_emision"))
    cards.append(available_card("combustible_total", "Combustible total", combustible, "L", "Combustible desde registros.", "registro_emision") if combustible is not None else missing_card("combustible_total", "Combustible total", "L", "Requiere registros de combustible.", "registro_emision"))
    cards.append(available_card("respel_kg", "RESPEL", respel, "kg", "Variable respel_kg registrada.", "variable_ambiental") if respel is not None else missing_card("respel_kg", "RESPEL", "kg", "Requiere variable respel_kg.", "variable_ambiental"))
    cards.append(available_card("residuos_no_peligrosos", "Residuos no peligrosos", residuos_no_peligrosos, "kg", "Residuos desde registros.", "registro_emision") if residuos_no_peligrosos is not None else missing_card("residuos_no_peligrosos", "Residuos no peligrosos", "kg", "Requiere registros de residuos no peligrosos.", "registro_emision"))
    cards.append(available_card("agua_m3", "Agua", agua, "m3", "Agua desde variable o registros.", "variable_ambiental") if agua is not None else missing_card("agua_m3", "Agua", "m3", "Requiere variable agua_m3 o registros de agua.", "variable_ambiental"))
    cards.append(alert_card("riles_alertas", "Alertas RILES", riles_alerts, "alertas", "Variables pH/DBO5/DQO/SST en alerta o incumplimiento.", "variable_ambiental") if riles_alerts else available_card("riles_alertas", "Alertas RILES", None, "alertas", "Sin alertas RILES registradas.", "variable_ambiental", "low"))
    cards.append(available_card("documentos_pendientes", "Documentos pendientes", docs_pending, "docs", "Documentos pendientes u observados.", "documento_ambiental") if docs_pending else available_card("documentos_pendientes", "Documentos pendientes", None, "docs", "Sin documentos pendientes u observados.", "documento_ambiental", "low"))
    return cards


def build_mineria_cards(context):
    registros = context["registros"]
    variables = context["variables"]
    total_kg = context["total_kg"]
    diesel = variable_sum(variables, "diesel_l") or registro_sum(registros, unidad_contains="litros diesel")
    agua = variable_sum(variables, "water_extracted_m3")
    mp10 = variable_latest(variables, "mp10")
    relaves = variable_sum(variables, "tailings_m3")
    rca_variables = [v for v in variables if normalize((v.metadata or {}).get("normativa")) == "rca"]
    rca_ok = sum(1 for v in rca_variables if v.estado_cumplimiento == "cumple")
    monitoreos = context["documentos"].filter(estado_validacion__in=["pendiente", "observado"], nombre__icontains="monitoreo").count()
    cards = [total_footprint_card("huella_total_faena", "Huella total faena", total_kg, "Suma de emisiones de faena.")]
    cards.append(available_card("diesel_total", "Diesel total", diesel, "L", "Diesel desde variables o registros.", "variable_ambiental") if diesel is not None else missing_card("diesel_total", "Diesel total", "L", "Requiere diesel_l o registros diesel.", "variable_ambiental"))
    cards.append(available_card("agua_captada", "Agua captada", agua, "m3", "Variable water_extracted_m3 registrada.", "variable_ambiental") if agua is not None else missing_card("agua_captada", "Agua captada", "m3", "Requiere variable water_extracted_m3.", "variable_ambiental"))
    cards.append(available_card("mp10", "MP10", mp10.valor, mp10.unidad or "ug/m3", "Ultima variable MP10 registrada.", "variable_ambiental") if mp10 else missing_card("mp10", "MP10", "ug/m3", "Requiere variable mp10.", "variable_ambiental"))
    cards.append(available_card("relaves", "Relaves", relaves, "m3", "Variable tailings_m3 registrada.", "variable_ambiental") if relaves is not None else missing_card("relaves", "Relaves", "m3", "Requiere variable tailings_m3.", "variable_ambiental"))
    cards.append(available_card("cumplimiento_rca", "Cumplimiento RCA", (Decimal(rca_ok) / Decimal(len(rca_variables))) * Decimal("100"), "%", "Variables RCA que cumplen sobre total RCA.", "calculado", "high") if rca_variables else missing_card("cumplimiento_rca", "Cumplimiento RCA", "%", "Requiere variables con normativa RCA.", "variable_ambiental", "high"))
    cards.append(available_card("monitoreos_pendientes", "Monitoreos pendientes", monitoreos, "docs", "Documentos de monitoreo pendientes u observados.", "documento_ambiental") if monitoreos else available_card("monitoreos_pendientes", "Monitoreos pendientes", None, "docs", "Sin monitoreos pendientes registrados.", "documento_ambiental", "low"))
    return cards


def build_energia_cards(context):
    registros = context["registros"]
    variables = context["variables"]
    total_kg = context["total_kg"]
    so2 = variable_latest(variables, "so2")
    nox = variable_latest(variables, "nox")
    opacity = variable_latest(variables, "opacity")
    cems_alerts = context["alertas_abiertas"].filter(normativa="CEMS").count()
    combustible = registro_sum(registros, unidad_contains="m3") or registro_sum(registros, unidad_contains="litros")
    cems_variables = [v for v in variables if normalize((v.metadata or {}).get("normativa")) == "cems"]
    cards = [total_footprint_card("huella_total_generacion", "Huella total generacion", total_kg, "Suma de emisiones de generacion.")]
    cards.append(available_card("so2_mg_m3", "SO2", so2.valor, so2.unidad or "mg/Nm3", "Ultima variable SO2 registrada.", "variable_ambiental") if so2 else missing_card("so2_mg_m3", "SO2", "mg/Nm3", "Requiere variable so2.", "variable_ambiental"))
    cards.append(available_card("nox_mg_m3", "NOx", nox.valor, nox.unidad or "mg/Nm3", "Ultima variable NOx registrada.", "variable_ambiental") if nox else missing_card("nox_mg_m3", "NOx", "mg/Nm3", "Requiere variable nox.", "variable_ambiental"))
    cards.append(available_card("opacity_pct", "Opacidad", opacity.valor, opacity.unidad or "%", "Ultima variable opacity registrada.", "variable_ambiental") if opacity else missing_card("opacity_pct", "Opacidad", "%", "Requiere variable opacity.", "variable_ambiental"))
    cards.append(alert_card("alertas_cems", "Alertas CEMS", cems_alerts, "alertas", "Alertas abiertas asociadas a CEMS.", "variable_ambiental") if cems_alerts else available_card("alertas_cems", "Alertas CEMS", None, "alertas", "Sin alertas CEMS abiertas.", "variable_ambiental", "low"))
    cards.append(available_card("combustible_generacion", "Combustible generacion", combustible, "m3", "Combustible desde registros.", "registro_emision") if combustible is not None else missing_card("combustible_generacion", "Combustible generacion", "m3", "Requiere registros de combustible de generacion.", "registro_emision"))
    if cems_variables:
        cems_bad = sum(1 for v in cems_variables if v.estado_cumplimiento in {"alerta", "incumple"})
        status = ALERT if cems_bad else AVAILABLE
        cards.append(kpi_card("cems_status", "Estado CEMS", len(cems_variables), "variables", status, "Variables CEMS con limites evaluados.", "calculado", "high"))
    else:
        cards.append(missing_card("cems_status", "Estado CEMS", "variables", "Requiere variables con normativa CEMS.", "variable_ambiental", "high"))
    return cards


def build_environmental_kpis(constructora):
    industry_key = detect_industry_key(constructora)
    context = build_common_context(constructora)
    summary = build_summary(constructora, context)
    total_kg = context["total_kg"]

    builders = {
        "construccion": lambda: build_construccion_cards(constructora, context),
        "transporte": lambda: build_transporte_cards(context),
        "forestal_aserradero": lambda: build_forestal_cards(constructora, context),
        "industrial_agroindustria": lambda: build_industrial_cards(context),
        "mineria": lambda: build_mineria_cards(context),
        "energia": lambda: build_energia_cards(context),
    }
    cards = builders.get(industry_key, builders["industrial_agroindustria"])()
    star_kpi = cards[0] if cards else missing_card("star_kpi", "KPI principal", "", "No hay KPIs configurados.", "calculado", "high")

    return {
        "constructora_id": constructora.constructora_id,
        "preset": constructora.preset,
        "rubro": constructora.rubro,
        "periodo": context["periodo"],
        "summary": summary,
        "star_kpi": star_kpi,
        "cards": cards,
        "top_sources": build_top_sources(context["registros"], total_kg),
        "top_categories": build_top_categories(context["registros"], total_kg),
        "data_gaps": common_data_gaps(cards, summary),
        "next_actions": common_next_actions(cards, summary),
    }
