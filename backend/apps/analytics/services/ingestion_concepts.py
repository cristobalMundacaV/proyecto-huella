import re
import unicodedata
from decimal import Decimal, InvalidOperation


CONCEPT_ALIASES = {
    "viaje_id": ("identificador_actividad", ""), "id_viaje": ("identificador_actividad", ""), "viaje": ("identificador_actividad", ""),
    "fecha": ("fecha_actividad", ""), "fecha_inicio": ("periodo_inicio", ""), "fecha_fin": ("periodo_fin", ""),
    "km": ("distancia_recorrida_km", "km"), "km_dia": ("distancia_recorrida_km", "km"),
    "km_recorridos": ("distancia_recorrida_km", "km"), "distancia_km": ("distancia_recorrida_km", "km"),
    "kilometros": ("distancia_recorrida_km", "km"), "distancia": ("distancia_recorrida_km", "km"),
    "toneladas": ("masa_transportada_t", "t"), "tonelaje": ("masa_transportada_t", "t"), "carga_ton": ("masa_transportada_t", "t"),
    "combustible": ("combustible_consumido_l", "L"), "litros_combustible": ("combustible_consumido_l", "L"),
    "litros": ("combustible_consumido_l", "L"), "kwh": ("consumo_energia", "kWh"),
    "consumo_electrico": ("consumo_energia", "kWh"), "energia_consumida": ("consumo_energia", "kWh"),
    "energia_generada": ("energia_generada", "kWh"), "energia_autoconsumida": ("energia_autoconsumida", "kWh"),
    "energia_exportada": ("energia_exportada", "kWh"), "m3_agua": ("consumo_agua", "m3"),
    "consumo_agua": ("consumo_agua", ""), "peso_residuo": ("cantidad_residuo", "kg"),
    "kg_residuo": ("cantidad_residuo", "kg"), "cantidad_residuo": ("cantidad_residuo", ""),
    "material": ("material", ""), "codigo_material": ("material", ""), "cantidad": ("cantidad_material", ""),
    "unidad": ("unidad", ""), "tipo_evento": ("tipo_evento_material", ""), "evento": ("tipo_evento_material", ""),
    "lote": ("lote_material", ""), "medidor": ("punto_medicion", ""), "punto": ("punto_medicion", ""),
    "obra": ("obra", ""), "proceso": ("proceso", ""), "activo": ("activo", ""), "patente": ("vehiculo", ""),
    "valor_ruido": ("nivel_ruido", ""), "ruido": ("nivel_ruido", ""), "metrica": ("metrica", ""),
    "destino": ("destino_operacional", ""), "gestor": ("proveedor_gestor", ""),
    "superficie_intervenida": ("superficie_intervenida", ""), "superficie_impermeabilizada": ("superficie_impermeabilizada", ""),
    "estado_drenaje": ("estado_drenaje", ""), "desborde": ("desborde", ""), "erosion_observada": ("erosion_observada", ""),
    "sedimentos": ("sedimentos", ""), "precipitacion_observada": ("precipitacion_observada", ""), "acumulacion_agua": ("acumulacion_agua", ""),
}

UNIT_ALIASES = {"kwh": "kWh", "l": "L", "lt": "L", "litro": "L", "litros": "L", "km": "km", "kg": "kg", "t": "t", "m3": "m3", "m³": "m3"}
DATE_CONCEPTS = {"fecha_actividad", "periodo_inicio", "periodo_fin"}
TEXT_CONCEPTS = {"identificador_actividad", "material", "tipo_evento_material", "lote_material", "punto_medicion", "obra", "proceso", "activo", "vehiculo", "unidad", "metrica", "destino_operacional", "proveedor_gestor"}


def normalize_column(value):
    value = unicodedata.normalize("NFD", str(value or "").strip().lower())
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value)).strip("_")


def normalize_unit(value):
    raw = str(value or "").strip()
    return UNIT_ALIASES.get(raw.lower(), raw)


def normalize_value(value, concept):
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if concept in TEXT_CONCEPTS or concept in DATE_CONCEPTS:
        return str(value).strip()
    if isinstance(value, bool):
        return value
    text = str(value).strip()
    normalized = text.replace(".", "").replace(",", ".") if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", text) else text.replace(",", ".")
    try:
        return str(Decimal(normalized))
    except (InvalidOperation, ValueError):
        if text.lower() in {"si", "sí", "true", "verdadero"}: return True
        if text.lower() in {"no", "false", "falso"}: return False
        return text


def classify_document(filename):
    name = normalize_column(filename)
    rules = {
        "factura_electrica": ("electric", "energia", "kwh"), "factura_combustible": ("combustible", "diesel"),
        "factura_material": ("material", "cemento", "acero"), "guia_despacho": ("guia", "despacho"),
        "ticket_pesaje": ("pesaje", "bascula"), "certificado_disposicion": ("disposicion", "residuo"),
        "hoja_ruta": ("ruta", "viaje"), "lectura_medidor": ("medidor",), "medicion_ruido": ("ruido",),
        "inspeccion_drenaje": ("drenaje", "erosion"),
    }
    matches = [kind for kind, tokens in rules.items() if any(token in name for token in tokens)]
    return matches[0] if len(matches) == 1 else "otro"
