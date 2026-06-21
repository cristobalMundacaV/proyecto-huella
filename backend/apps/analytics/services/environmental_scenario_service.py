from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.analytics.models import LoteForestal, Obra, RegistroEmision, VariableAmbientalExtraida
from apps.analytics.services.environmental_kpi_service import build_environmental_kpis, detect_industry_key, normalize
from apps.analytics.services.environmental_recommendation_engine import build_environmental_recommendations


def build_environmental_scenarios(constructora):
    kpis = build_environmental_kpis(constructora)
    recommendations = build_environmental_recommendations(constructora)
    industry = detect_industry_key(constructora)
    registros = list(RegistroEmision.objects.filter(constructora=constructora))
    variables = list(VariableAmbientalExtraida.objects.filter(constructora=constructora, valor__isnull=False))
    baseline = {
        "huella_total_kg_co2e": kpis["summary"].get("huella_total_kg_co2e"),
        "huella_total_tco2e": kpis["summary"].get("huella_total_tco2e"),
        "total_registros": kpis["summary"].get("total_registros"),
    }
    builders = {
        "construccion": build_construction_scenarios,
        "transporte": build_transport_scenarios,
        "forestal_aserradero": build_sawmill_scenarios,
        "industrial_agroindustria": build_industrial_scenarios,
        "mineria": build_mining_scenarios,
        "energia": build_energy_scenarios,
    }
    scenarios = builders.get(industry, build_industrial_scenarios)(constructora, registros, variables, recommendations)
    best = sorted(
        [item for item in scenarios if item["status"] == "available" and item["estimated_reduction_kg_co2e"] is not None],
        key=lambda item: item["estimated_reduction_kg_co2e"],
        reverse=True,
    )[:3]
    return {
        "constructora_id": constructora.constructora_id,
        "preset": constructora.preset,
        "rubro": constructora.rubro,
        "generated_at": timezone.now().isoformat(),
        "baseline": baseline,
        "scenarios": scenarios,
        "best_scenarios": best,
        "data_gaps": [item["reason"] for item in scenarios if item["status"] == "missing"][:6],
    }


def build_construction_scenarios(constructora, registros, variables, recommendations):
    scenarios = []
    material = top_emission(registros, lambda item: any(term in normalize(item.fuente_emision) for term in ["hormigon", "acero", "cemento", "arido", "asfalto"]))
    if material:
        for pct in [10, 15, 20]:
            scenarios.append(reduction_scenario(
                scenario_id=f"material-factor-{pct}",
                title=f"Reducir factor de {material['label']} en {pct}%",
                scenario_type="factor_reduction",
                area="materiales",
                baseline_value=material["emissions"],
                scenario_value=material["emissions"] * (Decimal("1") - Decimal(pct) / Decimal("100")),
                unit="kgCO2e",
                reduction=material["emissions"] * Decimal(pct) / Decimal("100"),
                reason=f"Basado en emisiones reales de {material['label']}.",
                evidence=[f"Fuente critica: {material['label']}", f"Emisiones base: {round_float(material['emissions'])} kgCO2e"],
                decision_hint="Evaluar alternativa tecnica con menor factor, EPD o ajuste de diseno.",
                related_recommendation_id=find_related_recommendation(recommendations, "materiales"),
            ))
        if material.get("provider"):
            scenarios.append(reduction_scenario(
                scenario_id="supplier-change-material",
                title=f"Evaluar proveedor alternativo para {material['label']}",
                scenario_type="supplier_change",
                area="materiales",
                baseline_value=material["emissions"],
                scenario_value=material["emissions"] * Decimal("0.90"),
                unit="kgCO2e",
                reduction=material["emissions"] * Decimal("0.10"),
                reason="Escenario conservador de 10% por alternativa tecnica/proveedor.",
                evidence=[f"Proveedor frecuente: {material['provider']}", f"Fuente: {material['label']}"],
                decision_hint="Comparar proveedor solo con respaldo tecnico, factor y distancia logistica.",
                related_recommendation_id=find_related_recommendation(recommendations, "materiales"),
            ))
    else:
        scenarios.append(missing_scenario("material-factor", "Reducir factor de material critico", "factor_reduction", "materiales", "Requiere registros de hormigon, acero, cemento, aridos o asfalto."))

    transport_emissions = emissions_sum(registros, lambda item: "transporte" in normalize(item.categoria))
    distance = sum_field(registros, "distancia_km", lambda item: "transporte" in normalize(item.categoria))
    if transport_emissions and distance:
        scenarios.append(percent_scenario("distance-10", "Reducir distancia logistica en 10%", "distance_reduction", "transporte", transport_emissions, Decimal("10"), "Reducir km recorridos reduce emisiones de transporte proporcionalmente.", ["Registros de transporte con distancia_km."], "Revisar origen/destino, consolidacion de viajes y proveedor cercano.", find_related_recommendation(recommendations, "transporte")))
    else:
        scenarios.append(missing_scenario("distance-10", "Reducir distancia logistica", "distance_reduction", "transporte", "Requiere emisiones de transporte y distancia_km."))

    rcd = variable_sum(variables, "rcd_ton")
    scenarios.append(variable_proxy_scenario("rcd-valorization", "Aumentar valorizacion RCD", "waste_valorization", "residuos", rcd, "ton", Decimal("15"), "Escenario sobre RCD registrado.") if rcd is not None else missing_scenario("rcd-valorization", "Aumentar valorizacion RCD", "waste_valorization", "residuos", "Requiere variable rcd_ton."))
    if not Obra.objects.filter(constructora=constructora, superficie_m2__isnull=False).exists():
        scenarios.append(missing_scenario("surface-gap", "Calcular intensidad por m2", "factor_reduction", "materiales", "Requiere superficie m2 de obra."))
    return scenarios


def build_transport_scenarios(constructora, registros, variables, recommendations):
    scenarios = []
    transport_emissions = emissions_sum(registros, lambda item: "transporte" in normalize(item.categoria))
    km = variable_sum(variables, "km_traveled") or sum_field(registros, "distancia_km", lambda item: "transporte" in normalize(item.categoria))
    liters = variable_sum(variables, "diesel_l") or sum_quantity(registros, lambda item: "litros diesel" in normalize(item.unidad))
    if km and liters and transport_emissions:
        for pct in [10, 15, 20]:
            scenarios.append(percent_scenario(f"fuel-efficiency-{pct}", f"Mejorar rendimiento km/L en {pct}%", "fuel_efficiency", "combustible", transport_emissions, Decimal(pct), "Mejor rendimiento reduce consumo diesel estimado.", [f"Km base: {round_float(km)}", f"Litros base: {round_float(liters)}"], "Revisar mantencion, presion de neumaticos, ralentí y conduccion.", find_related_recommendation(recommendations, "combustible")))
        scenarios.append(percent_scenario("km-reduction-10", "Reducir kilometros recorridos en 10%", "distance_reduction", "transporte", transport_emissions, Decimal("10"), "Menos km reduce emisiones de transporte.", [f"Km base: {round_float(km)}"], "Optimizar rutas y consolidar viajes.", find_related_recommendation(recommendations, "transporte")))
        scenarios.append(percent_scenario("diesel-reduction-10", "Reducir diesel en 10%", "fuel_efficiency", "combustible", transport_emissions, Decimal("10"), "Menor diesel reduce emisiones directas.", [f"Litros base: {round_float(liters)}"], "Priorizar vehiculos de mayor consumo.", find_related_recommendation(recommendations, "combustible")))
    else:
        scenarios.append(missing_scenario("transport-intensity", "Simular rendimiento y rutas", "fuel_efficiency", "combustible", "Requiere km, litros diesel y emisiones de transporte."))
    return scenarios


def build_sawmill_scenarios(constructora, registros, variables, recommendations):
    scenarios = []
    volume = variable_sum(variables, "wood_volume_m3") or LoteForestal.objects.filter(constructora=constructora).aggregate(total=Sum("volumen_m3"))["total"] or sum_quantity(registros, lambda item: "m3" in normalize(item.unidad))
    energy_emissions = emissions_sum(registros, lambda item: "energia" in normalize(item.categoria))
    if volume and energy_emissions:
        for pct in [10, 15]:
            scenarios.append(percent_scenario(f"energy-m3-{pct}", f"Reducir energia por m3 en {pct}%", "energy_reduction", "energia", energy_emissions, Decimal(pct), "Escenario sobre emisiones energeticas de produccion/secado.", [f"Volumen base: {round_float(volume)} m3"], "Revisar secado, humedad inicial/final y programacion de camaras.", find_related_recommendation(recommendations, "energia")))
    else:
        scenarios.append(missing_scenario("energy-m3", "Reducir energia por m3", "energy_reduction", "energia", "Requiere volumen m3 y registros de energia."))
    biomass = variable_sum(variables, "biomass_boiler_ton")
    scenarios.append(variable_proxy_scenario("biomass-10", "Reducir biomasa a caldera en 10%", "energy_reduction", "energia", biomass, "ton", Decimal("10"), "Escenario sobre biomasa registrada.") if biomass is not None else missing_scenario("biomass-10", "Reducir biomasa a caldera", "energy_reduction", "energia", "Requiere variable biomass_boiler_ton."))
    sawdust = variable_sum(variables, "sawdust_ton", "bark_ton")
    scenarios.append(variable_proxy_scenario("sawdust-valorization", "Aumentar valorizacion de subproductos", "waste_valorization", "residuos", sawdust, "ton", Decimal("15"), "Escenario sobre aserrin/corteza registrados.") if sawdust is not None else missing_scenario("sawdust-valorization", "Aumentar valorizacion de subproductos", "waste_valorization", "residuos", "Requiere sawdust_ton o bark_ton."))
    return scenarios


def build_industrial_scenarios(constructora, registros, variables, recommendations):
    scenarios = []
    energy = emissions_sum(registros, lambda item: "energia" in normalize(item.categoria))
    fuel = emissions_sum(registros, lambda item: "litros" in normalize(item.unidad) or "combustible" in normalize(item.fuente_emision))
    scenarios.append(percent_scenario("energy-10", "Reducir consumo energetico en 10%", "energy_reduction", "energia", energy, Decimal("10"), "Escenario sobre emisiones energeticas.", ["Registros de energia."], "Identificar proceso critico antes de intervenir.", find_related_recommendation(recommendations, "energia")) if energy else missing_scenario("energy-10", "Reducir consumo energetico", "energy_reduction", "energia", "Requiere registros de energia."))
    scenarios.append(percent_scenario("fuel-10", "Reducir combustible en 10%", "fuel_efficiency", "combustible", fuel, Decimal("10"), "Escenario sobre emisiones de combustible.", ["Registros de combustible."], "Revisar caldera, equipos y consumo especifico.", find_related_recommendation(recommendations, "combustible")) if fuel else missing_scenario("fuel-10", "Reducir combustible", "fuel_efficiency", "combustible", "Requiere registros de combustible."))
    riles = [var for var in variables if normalize(var.variable_id) in {"dbo5", "dqo", "sst", "ph"} and var.estado_cumplimiento in {"alerta", "incumple"}]
    scenarios.append(variable_quality_scenario("riles-improvement", "Mejorar tratamiento RILES", "riles_improvement", "riles", riles, "Reducir carga contaminante asociada a variables RILES en alerta.") if riles else missing_scenario("riles-improvement", "Mejorar tratamiento RILES", "riles_improvement", "riles", "Requiere variables RILES en alerta o incumplimiento."))
    respel = variable_sum(variables, "respel_kg")
    scenarios.append(variable_proxy_scenario("respel-10", "Reducir RESPEL en 10%", "waste_valorization", "residuos", respel, "kg", Decimal("10"), "Escenario sobre RESPEL registrado.") if respel is not None else missing_scenario("respel-10", "Reducir RESPEL", "waste_valorization", "residuos", "Requiere variable respel_kg."))
    return scenarios


def build_mining_scenarios(constructora, registros, variables, recommendations):
    scenarios = []
    diesel = emissions_sum(registros, lambda item: "diesel" in normalize(item.fuente_emision) or "litros diesel" in normalize(item.unidad))
    scenarios.append(percent_scenario("mining-diesel-10", "Reducir diesel en maquinaria en 10%", "fuel_efficiency", "combustible", diesel, Decimal("10"), "Escenario sobre emisiones diesel de maquinaria.", ["Registros diesel de faena."], "Revisar mantencion, ralentí y planificacion de equipos.", find_related_recommendation(recommendations, "combustible")) if diesel else missing_scenario("mining-diesel-10", "Reducir diesel en maquinaria", "fuel_efficiency", "combustible", "Requiere registros diesel."))
    water = variable_sum(variables, "water_extracted_m3")
    scenarios.append(variable_proxy_scenario("water-10", "Reducir agua captada en 10%", "water_reduction", "agua", water, "m3", Decimal("10"), "Escenario sobre agua captada registrada.") if water is not None else missing_scenario("water-10", "Reducir agua captada", "water_reduction", "agua", "Requiere variable water_extracted_m3."))
    mp10 = variable_sum(variables, "mp10")
    scenarios.append(variable_proxy_scenario("mp10-10", "Reducir MP10 en 10%", "riles_improvement", "aire", mp10, "ug/m3", Decimal("10"), "Escenario sobre MP10 registrado.") if mp10 is not None else missing_scenario("mp10-10", "Reducir MP10", "riles_improvement", "aire", "Requiere variable mp10."))
    recirculation = variable_sum(variables, "recirculation_pct")
    scenarios.append(variable_proxy_scenario("recirculation-5", "Mejorar recirculacion en 5%", "water_reduction", "agua", recirculation, "%", Decimal("5"), "Escenario sobre recirculacion registrada.") if recirculation is not None else missing_scenario("recirculation-5", "Mejorar recirculacion", "water_reduction", "agua", "Requiere variable recirculation_pct."))
    return scenarios


def build_energy_scenarios(constructora, registros, variables, recommendations):
    scenarios = []
    fuel = emissions_sum(registros, lambda item: "combustible" in normalize(item.fuente_emision) or "m3" in normalize(item.unidad))
    generation = sum_quantity(registros, lambda item: "mwh" in normalize(item.unidad))
    scenarios.append(percent_scenario("generation-fuel-10", "Reducir combustible de generacion en 10%", "fuel_efficiency", "combustible", fuel, Decimal("10"), "Escenario sobre combustible de generacion.", ["Registros de combustible/generacion."], "Revisar eficiencia de unidad generadora.", find_related_recommendation(recommendations, "combustible")) if fuel else missing_scenario("generation-fuel-10", "Reducir combustible de generacion", "fuel_efficiency", "combustible", "Requiere registros de combustible."))
    total = emissions_sum(registros)
    if total and generation:
        scenarios.append(percent_scenario("intensity-mwh-10", "Mejorar intensidad kgCO2e/MWh en 10%", "energy_reduction", "energia", total, Decimal("10"), "Escenario sobre intensidad de generacion.", [f"Generacion base: {round_float(generation)} MWh"], "Optimizar eficiencia operacional y factor de combustible.", find_related_recommendation(recommendations, "energia")))
    else:
        scenarios.append(missing_scenario("intensity-mwh-10", "Mejorar intensidad kgCO2e/MWh", "energy_reduction", "energia", "Requiere emisiones y generacion MWh."))
    cems_vars = [var for var in variables if normalize(var.variable_id) in {"so2", "nox", "opacity"} and var.estado_cumplimiento in {"alerta", "incumple"}]
    scenarios.append(variable_quality_scenario("cems-improvement", "Reducir SO2/NOx/opacidad", "riles_improvement", "aire", cems_vars, "Reducir variables CEMS en alerta.") if cems_vars else missing_scenario("cems-improvement", "Reducir SO2/NOx/opacidad", "riles_improvement", "aire", "Requiere variables CEMS en alerta o incumplimiento."))
    return scenarios


def reduction_scenario(scenario_id, title, scenario_type, area, baseline_value, scenario_value, unit, reduction, reason, evidence, decision_hint, related_recommendation_id=""):
    return {
        "id": scenario_id,
        "title": title,
        "type": scenario_type,
        "area": area,
        "description": reason,
        "baseline_value": round_float(baseline_value),
        "scenario_value": round_float(scenario_value),
        "unit": unit,
        "estimated_reduction_kg_co2e": round_float(reduction),
        "estimated_reduction_tco2e": round_float(reduction / Decimal("1000")),
        "estimated_reduction_pct": round_float((reduction / baseline_value) * Decimal("100")) if baseline_value else None,
        "status": "available",
        "reason": reason,
        "evidence": evidence,
        "decision_hint": decision_hint,
        "related_recommendation_id": related_recommendation_id,
    }


def percent_scenario(scenario_id, title, scenario_type, area, emissions, pct, reason, evidence, decision_hint, related_recommendation_id=""):
    if not emissions:
        return missing_scenario(scenario_id, title, scenario_type, area, "Requiere emisiones base para simular reduccion.")
    reduction = emissions * pct / Decimal("100")
    return reduction_scenario(scenario_id, title, scenario_type, area, emissions, emissions - reduction, "kgCO2e", reduction, reason, evidence, decision_hint, related_recommendation_id)


def variable_proxy_scenario(scenario_id, title, scenario_type, area, value, unit, pct, reason):
    if value is None:
        return missing_scenario(scenario_id, title, scenario_type, area, "Requiere variable ambiental base.")
    scenario_value = value * (Decimal("1") - pct / Decimal("100"))
    return {
        "id": scenario_id,
        "title": title,
        "type": scenario_type,
        "area": area,
        "description": reason,
        "baseline_value": round_float(value),
        "scenario_value": round_float(scenario_value),
        "unit": unit,
        "estimated_reduction_kg_co2e": None,
        "estimated_reduction_tco2e": None,
        "estimated_reduction_pct": round_float(pct),
        "status": "partial",
        "reason": "Impacto ambiental parcial: reduce variable operacional, pero no hay factor CO2e directo vinculado.",
        "evidence": [f"Variable base: {round_float(value)} {unit}."],
        "decision_hint": "Validar factor o relacion operacional antes de cuantificar CO2e.",
        "related_recommendation_id": "",
    }


def variable_quality_scenario(scenario_id, title, scenario_type, area, variables, reason):
    if not variables:
        return missing_scenario(scenario_id, title, scenario_type, area, "Requiere variables en alerta o incumplimiento.")
    labels = [f"{var.nombre}: {var.valor} {var.unidad}" for var in variables[:4]]
    return {
        "id": scenario_id,
        "title": title,
        "type": scenario_type,
        "area": area,
        "description": reason,
        "baseline_value": None,
        "scenario_value": None,
        "unit": "",
        "estimated_reduction_kg_co2e": None,
        "estimated_reduction_tco2e": None,
        "estimated_reduction_pct": None,
        "status": "partial",
        "reason": "Escenario de cumplimiento: requiere relacion tecnica para traducir mejora a CO2e.",
        "evidence": labels,
        "decision_hint": "Priorizar mejora operacional y remuestreo validado.",
        "related_recommendation_id": "",
    }


def missing_scenario(scenario_id, title, scenario_type, area, reason):
    return {
        "id": scenario_id,
        "title": title,
        "type": scenario_type,
        "area": area,
        "description": reason,
        "baseline_value": None,
        "scenario_value": None,
        "unit": "",
        "estimated_reduction_kg_co2e": None,
        "estimated_reduction_tco2e": None,
        "estimated_reduction_pct": None,
        "status": "missing",
        "reason": reason,
        "evidence": [],
        "decision_hint": "Cargar el dato base antes de simular.",
        "related_recommendation_id": "",
    }


def emissions_sum(registros, predicate=None):
    total = Decimal("0")
    found = False
    for registro in registros:
        if predicate and not predicate(registro):
            continue
        total += registro.emisiones_kg_co2e or Decimal("0")
        found = True
    return total if found and total > 0 else None


def sum_quantity(registros, predicate):
    total = Decimal("0")
    found = False
    for registro in registros:
        if predicate(registro):
            total += registro.cantidad or Decimal("0")
            found = True
    return total if found else None


def sum_field(registros, field, predicate):
    total = Decimal("0")
    found = False
    for registro in registros:
        if not predicate(registro):
            continue
        value = getattr(registro, field, None)
        if value is None:
            continue
        total += value
        found = True
    return total if found else None


def variable_sum(variables, *ids):
    normalized = {normalize(item) for item in ids}
    values = [var.valor for var in variables if normalize(var.variable_id) in normalized and var.valor is not None]
    return sum(values, Decimal("0")) if values else None


def top_emission(registros, predicate):
    grouped = {}
    for registro in registros:
        if not predicate(registro):
            continue
        key = registro.fuente_emision or "Sin fuente"
        current = grouped.setdefault(key, {"label": key, "emissions": Decimal("0"), "provider": registro.proveedor})
        current["emissions"] += registro.emisiones_kg_co2e or Decimal("0")
        if not current.get("provider") and registro.proveedor:
            current["provider"] = registro.proveedor
    if not grouped:
        return None
    return max(grouped.values(), key=lambda item: item["emissions"])


def find_related_recommendation(recommendations, area):
    for item in recommendations.get("recommendations", []):
        if item.get("area") == area:
            return item.get("id", "")
    return ""


def round_float(value):
    if value is None:
        return None
    return round(float(value), 2)
