const environmentalPresetMatrix = {
  construccion: {
    id: "construccion",
    name: "Construcción e inmobiliaria",
    shortName: "Construcción",
    purpose: "Controlar residuos de construcción, ruido, polvo, transporte y evidencias de disposición autorizada.",
    criticalDocuments: [
      {
        id: "rcd_weight_ticket",
        name: "Vale de pesaje RCD",
        description: "Respalda retiro, masa, tipo de escombro, patente y destinatario autorizado.",
        expectedVariables: ["fecha", "patente", "tipo_escombro", "masa_ton", "destinatario_autorizado", "obra"],
        evidenceType: "ticket_pesaje",
      },
      {
        id: "noise_report",
        name: "Informe de ruido",
        description: "Registra niveles de presión sonora en puntos sensibles de la obra.",
        expectedVariables: ["fecha", "punto_medicion", "periodo", "db_a", "limite_db_a"],
        evidenceType: "otro",
      },
      {
        id: "mitigation_plan",
        name: "Plan de mitigación urbana",
        description: "Ordena compromisos de polvo, ruido, tránsito y manejo comunitario.",
        expectedVariables: ["compromiso", "responsable", "frecuencia", "evidencia_requerida"],
        evidenceType: "otro",
      },
    ],
    criticalVariables: [
      variable("rcd_ton", "Toneladas RCD", "ton", "residuos", "Masa total de residuos de construcción y demolición."),
      variable("noise_db", "Ruido", "dB(A)", "ruido", "Nivel de presión sonora corregido."),
      variable("diesel_l", "Diésel maquinaria/transporte", "litros", "co2e", "Consumo de combustible de equipos, camiones y maquinaria."),
      variable("authorized_destination", "Destino autorizado", "boolean", "trazabilidad", "Confirma disposición en gestor autorizado."),
    ],
    calculations: [
      calculation("rcd_total_by_type", "Consolidar toneladas RCD por tipo de material."),
      calculation("rcd_valorization_rate", "Calcular tasa de valorización de RCD."),
      calculation("co2e_diesel", "Calcular CO₂e por consumo de diésel."),
      calculation("noise_limit_compliance", "Comparar ruido medido contra límite aplicable."),
    ],
    regulations: [
      regulation("retc", "RETC / Ventanilla Única", "Consolidación anual de residuos y emisiones."),
      regulation("sinader", "SINADER", "Declaración de residuos no peligrosos."),
      regulation("ds38", "DS 38", "Evaluación de ruido ambiental."),
      regulation("rca", "RCA", "Compromisos específicos de obra y mitigación."),
    ],
    riskSignals: [
      risk("illegal_disposal", "Disposición no autorizada de escombros", "rojo"),
      risk("noise_exceedance", "Sobrepaso de ruido urbano", "rojo"),
      risk("missing_weight_ticket", "Falta vale de pesaje o destino autorizado", "amarillo"),
    ],
    recommendedActions: [
      "Solicitar vale de pesaje por cada retiro de RCD.",
      "Vincular camión, patente, obra y destinatario autorizado.",
      "Crear acción correctiva ante mediciones de ruido cercanas al límite.",
    ],
  },

  forestal_aserradero: {
    id: "forestal_aserradero",
    name: "Forestal y aserraderos",
    shortName: "Forestal / Aserradero",
    purpose: "Controlar biomasa, trazabilidad de madera, calderas, ruido industrial, residuos y transporte forestal.",
    criticalDocuments: [
      {
        id: "wood_dispatch_guide",
        name: "Guía de despacho de madera",
        description: "Respalda origen, destino, especie, volumen y trazabilidad del lote.",
        expectedVariables: ["fecha", "origen", "destino", "especie", "volumen_m3", "lote"],
        evidenceType: "guia_despacho",
      },
      {
        id: "boiler_operation_log",
        name: "Bitácora de caldera",
        description: "Registra consumo de biomasa, temperatura, operación y eventos.",
        expectedVariables: ["fecha", "biomasa_ton", "horas_operacion", "temperatura", "evento"],
        evidenceType: "registro_produccion",
      },
      {
        id: "sawmill_noise_report",
        name: "Informe de ruido industrial",
        description: "Controla exposición y emisión sonora de sierras, chipeadoras y equipos.",
        expectedVariables: ["punto_medicion", "periodo", "db_a", "limite_db_a"],
        evidenceType: "otro",
      },
    ],
    criticalVariables: [
      variable("sawdust_ton", "Aserrín", "ton", "residuos", "Biomasa residual generada por proceso de aserrío."),
      variable("bark_ton", "Corteza", "ton", "residuos", "Residuo sólido combustible asociado a trozas."),
      variable("biomass_boiler_ton", "Biomasa a caldera", "ton", "energia", "Consumo de biomasa para generación térmica."),
      variable("wood_volume_m3", "Volumen de madera", "m3", "trazabilidad", "Volumen por lote, especie y origen."),
      variable("noise_db", "Ruido industrial", "dB(A)", "ruido", "Medición acústica del proceso productivo."),
    ],
    calculations: [
      calculation("biomass_balance", "Balancear biomasa generada, usada y almacenada."),
      calculation("wood_traceability", "Verificar lote, origen, especie, destino y evidencia."),
      calculation("boiler_emissions", "Calcular emisiones asociadas a caldera y combustible."),
      calculation("noise_limit_compliance", "Comparar ruido industrial contra límite aplicable."),
    ],
    regulations: [
      regulation("retc", "RETC / Ventanilla Única", "Declaración de emisiones y residuos."),
      regulation("sinader", "SINADER", "Residuos no peligrosos y subproductos."),
      regulation("ds38", "DS 38", "Ruido ambiental."),
      regulation("rca", "RCA", "Compromisos de operación, biomasa y emisiones."),
      regulation("fsc", "Trazabilidad FSC", "Control de origen y cadena de custodia cuando aplique."),
    ],
    riskSignals: [
      risk("biomass_accumulation", "Acumulación crítica de biomasa combustible", "rojo"),
      risk("boiler_without_log", "Caldera sin bitácora operacional", "amarillo"),
      risk("wood_without_origin", "Madera sin origen o lote trazable", "rojo"),
    ],
    recommendedActions: [
      "Mantener trazabilidad por lote forestal y guía de despacho.",
      "Controlar stock de aserrín y corteza para prevenir incendios.",
      "Vincular operación de caldera con consumo, evidencia y emisiones.",
    ],
  },

  industrial_agroindustria: {
    id: "industrial_agroindustria",
    name: "Manufactura, química, alimentos y agroindustria",
    shortName: "Industrial / Agro",
    purpose: "Controlar RILES, residuos peligrosos, residuos no peligrosos, ruido, energía y cumplimiento operacional.",
    criticalDocuments: [
      {
        id: "riles_lab_report",
        name: "Informe de RILES",
        description: "Informe de laboratorio para descarga líquida industrial.",
        expectedVariables: ["punto_descarga", "fecha_hora", "ph", "temperatura_c", "dbo5_mg_l", "dqo_mg_l", "sst_mg_l", "aceites_grasas_mg_l"],
        evidenceType: "otro",
      },
      {
        id: "sidrep_manifest",
        name: "Manifiesto SIDREP / RESPEL",
        description: "Traza generación, transporte y destino de residuos peligrosos.",
        expectedVariables: ["rut_generador", "rut_transportista", "patente", "codigo_respel", "peso_kg", "fecha_envio", "fecha_recepcion"],
        evidenceType: "documento_transporte",
      },
      {
        id: "sinader_residue_report",
        name: "Registro SINADER",
        description: "Consolida residuos no peligrosos por material, peso y destino.",
        expectedVariables: ["tipo_material", "peso_kg", "metodo_destino", "gestor"],
        evidenceType: "ticket_pesaje",
      },
    ],
    criticalVariables: [
      variable("ph", "pH", "pH", "riles", "Acidez o alcalinidad del RIL."),
      variable("temperature_c", "Temperatura RIL", "°C", "riles", "Temperatura de descarga."),
      variable("dbo5", "DBO5", "mg/L", "riles", "Carga orgánica biodegradable."),
      variable("dqo", "DQO", "mg/L", "riles", "Demanda química de oxígeno."),
      variable("sst", "SST", "mg/L", "riles", "Sólidos suspendidos totales."),
      variable("respel_kg", "RESPEL", "kg", "residuos_peligrosos", "Masa de residuo peligroso generada."),
      variable("non_hazardous_waste_kg", "Residuos no peligrosos", "kg", "residuos", "Masa de residuos industriales no peligrosos."),
    ],
    calculations: [
      calculation("riles_limit_compliance", "Comparar parámetros RILES contra límite DS90 o RCA."),
      calculation("respel_traceability", "Validar trazabilidad generador, transportista y destino."),
      calculation("waste_consolidation", "Consolidar residuos por tipo y destino."),
      calculation("valorization_rate", "Calcular tasa de valorización."),
    ],
    regulations: [
      regulation("ds90", "DS 90", "Control de descargas de residuos líquidos."),
      regulation("ds148", "DS 148", "Manejo y declaración de residuos peligrosos."),
      regulation("sidrep", "SIDREP", "Sistema de declaración y seguimiento RESPEL."),
      regulation("sinader", "SINADER", "Declaración de residuos no peligrosos."),
      regulation("retc", "RETC / Ventanilla Única", "Reporte ambiental consolidado."),
      regulation("rca", "RCA", "Límites específicos de la instalación."),
    ],
    riskSignals: [
      risk("riles_exceedance", "Parámetro RIL sobre límite", "rojo"),
      risk("respel_without_destination", "RESPEL sin destino final acreditado", "rojo"),
      risk("missing_lab_report", "Falta informe de laboratorio del periodo", "amarillo"),
    ],
    recommendedActions: [
      "Cargar informe RILES mensual y comparar contra límites configurados.",
      "Validar manifiestos RESPEL con transportista, patente y destino.",
      "Consolidar residuos no peligrosos para SINADER y tasa de valorización.",
    ],
  },

  mineria: {
    id: "mineria",
    name: "Minería",
    shortName: "Minería",
    purpose: "Controlar agua, relaves, material particulado, combustible, energía, RCA y estabilidad operacional.",
    criticalDocuments: [
      {
        id: "tailings_report",
        name: "Reporte de relaves",
        description: "Controla volumen, estabilidad, monitoreo químico y condición operacional del depósito.",
        expectedVariables: ["fecha", "deposito", "volumen_m3", "nivel_operacional", "ph", "conductividad", "estado_estabilidad"],
        evidenceType: "otro",
      },
      {
        id: "water_extraction_log",
        name: "Registro hidrológico",
        description: "Registra captación, recirculación y consumo de agua en operación minera.",
        expectedVariables: ["fecha", "fuente_agua", "m3_captados", "m3_recirc", "porcentaje_recirculacion"],
        evidenceType: "otro",
      },
      {
        id: "particulate_matter_report",
        name: "Informe material particulado",
        description: "Monitorea MP10/MP2.5 por tronaduras, tránsito y operación.",
        expectedVariables: ["fecha_hora", "punto_medicion", "mp10", "mp25", "condicion_viento"],
        evidenceType: "otro",
      },
    ],
    criticalVariables: [
      variable("tailings_m3", "Relaves", "m3", "relaves", "Volumen operacional del depósito."),
      variable("water_extracted_m3", "Agua captada", "m3", "agua", "Agua extraída desde pozo, río o fuente autorizada."),
      variable("water_recirculation_pct", "Recirculación", "%", "agua", "Porcentaje de agua recirculada."),
      variable("mp10", "MP10", "µg/m3", "aire", "Material particulado grueso."),
      variable("mp25", "MP2.5", "µg/m3", "aire", "Material particulado fino."),
      variable("diesel_l", "Diésel flota mina", "litros", "co2e", "Combustible de camiones y maquinaria."),
    ],
    calculations: [
      calculation("water_balance", "Balancear agua captada, usada y recirculada."),
      calculation("particulate_limit_compliance", "Comparar MP10/MP2.5 contra límite aplicable."),
      calculation("tailings_operational_status", "Evaluar estado operacional del depósito de relaves."),
      calculation("co2e_diesel", "Calcular CO₂e por combustible de flota minera."),
    ],
    regulations: [
      regulation("rca", "RCA", "Compromisos ambientales de la faena."),
      regulation("sma", "SMA", "Fiscalización de cumplimiento ambiental."),
      regulation("sernageomin", "Sernageomin", "Planes de cierre y estabilidad minera."),
      regulation("retc", "RETC / Ventanilla Única", "Emisiones y residuos declarables."),
    ],
    riskSignals: [
      risk("water_overuse", "Consumo hídrico sobre umbral comprometido", "rojo"),
      risk("tailings_instability", "Riesgo operacional en depósito de relaves", "rojo"),
      risk("mp_peak", "Peak de material particulado", "amarillo"),
    ],
    recommendedActions: [
      "Configurar límites RCA de agua, polvo y relaves por unidad fiscalizable.",
      "Vincular reportes hidrológicos y relaves con evidencia mensual.",
      "Crear alertas ante peaks de material particulado o baja recirculación.",
    ],
  },

  energia: {
    id: "energia",
    name: "Energía y termoeléctricas",
    shortName: "Energía",
    purpose: "Controlar CEMS, chimeneas, gases regulados, combustible, cenizas e impuesto verde.",
    criticalDocuments: [
      {
        id: "cems_log",
        name: "Log CEMS",
        description: "Archivo continuo de monitoreo de chimenea.",
        expectedVariables: ["timestamp", "flujo_m3_h", "co2_ppm", "so2_mg_m3", "nox_mg_m3", "opacidad_pct"],
        evidenceType: "otro",
      },
      {
        id: "fuel_report",
        name: "Registro de combustible",
        description: "Respalda consumo por caldera, turbina o unidad generadora.",
        expectedVariables: ["fecha", "combustible", "cantidad", "unidad", "unidad_generadora"],
        evidenceType: "factura_combustible",
      },
    ],
    criticalVariables: [
      variable("co2_ppm", "CO₂", "ppm", "aire", "Concentración de dióxido de carbono."),
      variable("so2_mg_m3", "SO₂", "mg/m3", "aire", "Dióxido de azufre."),
      variable("nox_mg_m3", "NOx", "mg/m3", "aire", "Óxidos de nitrógeno."),
      variable("opacity_pct", "Opacidad", "%", "aire", "Opacidad de humo."),
      variable("fuel_consumption", "Combustible", "unidad", "co2e", "Consumo de combustible por unidad generadora."),
    ],
    calculations: [
      calculation("cems_limit_compliance", "Comparar CEMS contra límites de emisión."),
      calculation("green_tax_basis", "Preparar base de impuesto verde cuando aplique."),
      calculation("co2e_fuel", "Calcular CO₂e por combustible."),
    ],
    regulations: [
      regulation("cems", "CEMS", "Monitoreo continuo de emisiones."),
      regulation("retc", "RETC / Ventanilla Única", "Reporte de emisiones."),
      regulation("impuesto_verde", "Impuesto Verde", "Base de emisiones gravadas."),
      regulation("rca", "RCA", "Compromisos de operación y emisiones."),
    ],
    riskSignals: [
      risk("so2_peak", "Peak SO₂ cercano o sobre límite", "rojo"),
      risk("nox_peak", "Peak NOx cercano o sobre límite", "rojo"),
      risk("cems_gap", "Brecha de continuidad CEMS", "amarillo"),
    ],
    recommendedActions: [
      "Validar continuidad de logs CEMS por unidad generadora.",
      "Configurar límites de RCA o norma por contaminante.",
      "Generar alertas ante peaks o pérdida de datos de chimenea.",
    ],
  },

  acuicultura: {
    id: "acuicultura",
    name: "Acuicultura y salmoneras",
    shortName: "Acuicultura",
    purpose: "Controlar INFFA, fondo marino, oxígeno, redox, antibióticos, mortalidad y escapes.",
    criticalDocuments: [
      {
        id: "inffa_report",
        name: "Informe INFFA",
        description: "Evalúa condición ambiental del fondo marino bajo centros de cultivo.",
        expectedVariables: ["centro", "jaula", "oxigeno_mg_l", "redox_mv", "macrofauna", "condicion_fondo"],
        evidenceType: "otro",
      },
      {
        id: "veterinary_treatment_log",
        name: "Bitácora tratamiento veterinario",
        description: "Registra uso de antimicrobianos y antiparasitarios por biomasa.",
        expectedVariables: ["fecha", "jaula", "farmaco", "gramos", "biomasa_ton", "gr_por_ton"],
        evidenceType: "otro",
      },
    ],
    criticalVariables: [
      variable("oxygen_mg_l", "Oxígeno disuelto", "mg/L", "agua", "Oxígeno disponible en fondo marino."),
      variable("redox_mv", "Potencial redox", "mV", "fondo_marino", "Indicador de degradación orgánica."),
      variable("antibiotics_gr_ton", "Antibióticos", "gr/ton", "tratamiento", "Uso de antimicrobianos por biomasa."),
      variable("fish_escape_count", "Escapes", "individuos", "ecosistema", "Número de peces escapados."),
      variable("mortality_kg", "Mortalidad", "kg", "residuos", "Biomasa muerta retirada."),
    ],
    calculations: [
      calculation("inffa_condition", "Clasificar fondo como aeróbico o anaeróbico."),
      calculation("antibiotic_intensity", "Calcular gramos de fármaco por tonelada de biomasa."),
      calculation("mortality_rate", "Calcular tasa de mortalidad y retiro."),
    ],
    regulations: [
      regulation("sernapesca", "Sernapesca", "Reportabilidad sectorial acuícola."),
      regulation("inffa", "INFFA", "Información ambiental para acuicultura."),
      regulation("rca", "RCA", "Compromisos del centro de cultivo."),
    ],
    riskSignals: [
      risk("anaerobic_bottom", "Fondo marino anaeróbico", "rojo"),
      risk("high_antibiotic_use", "Uso intensivo de antibióticos", "amarillo"),
      risk("fish_escape", "Escape de peces", "rojo"),
    ],
    recommendedActions: [
      "Cargar INFFA y evaluar condición del fondo por centro y jaula.",
      "Controlar tratamientos veterinarios por biomasa.",
      "Crear protocolo de alerta ante escapes o fondo anaeróbico.",
    ],
  },
};

function variable(id, name, unit, category, description) {
  return { id, name, unit, category, description };
}

function calculation(id, description) {
  return { id, description };
}

function regulation(id, name, description) {
  return { id, name, description };
}

function risk(id, description, level) {
  return { id, description, level };
}

function getEnvironmentalPresetMatrix() {
  return environmentalPresetMatrix;
}

function getEnvironmentalPreset(presetId) {
  return environmentalPresetMatrix[presetId] || null;
}

function listEnvironmentalPresets() {
  return Object.values(environmentalPresetMatrix);
}

export { getEnvironmentalPreset, getEnvironmentalPresetMatrix, listEnvironmentalPresets };
export default environmentalPresetMatrix;
