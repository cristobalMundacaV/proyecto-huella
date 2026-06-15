const CATEGORY_REDUCTION_RULES = {
  Materiales: {
    maxReduction: 0.18,
    label: "Materiales",
  },
  Transporte: {
    maxReduction: 0.24,
    label: "Transporte",
  },
  Maquinaria: {
    maxReduction: 0.18,
    label: "Maquinaria",
  },
  Energia: {
    maxReduction: 0.22,
    label: "Energía",
  },
  Energía: {
    maxReduction: 0.22,
    label: "Energía",
  },
  Agua: {
    maxReduction: 0.08,
    label: "Agua",
  },
  Residuos: {
    maxReduction: 0.15,
    label: "Residuos",
  },
  "Procesos externos": {
    maxReduction: 0.16,
    label: "Procesos externos",
  },
  Otros: {
    maxReduction: 0.06,
    label: "Otros",
  },
};

const SOURCE_INTELLIGENCE_RULES = [
  {
    key: "hormigon",
    label: "Hormigón",
    category: "Materiales",
    maxReductionBoost: 1.12,
    recommendations: [
      "Comparar m³ de hormigón comprados contra avance real ejecutado para detectar sobreconsumo o merma.",
      "Solicitar ficha técnica, EPD o respaldo de proveedor para validar factor de emisión usado.",
      "Evaluar proveedor con menor contenido de clínker o mezclas con adiciones cuando el proyecto lo permita.",
      "Separar hormigón estructural, rellenos y morteros para no mezclar fuentes con impactos distintos.",
      "Cruzar guías de despacho contra cubicación estimada de obra antes de cerrar reportes.",
    ],
    evidence: [
      "factura de hormigón",
      "guía de despacho",
      "cubicación o avance real",
      "ficha técnica / EPD del proveedor",
    ],
    nextStep: "Validar volumen real ejecutado y respaldo del proveedor antes de definir sustituciones o cambios de mezcla.",
  },
  {
    key: "cemento",
    label: "Cemento",
    category: "Materiales",
    maxReductionBoost: 1.1,
    recommendations: [
      "Separar consumo de cemento por uso: mortero, hormigón en obra, estabilizado u otros procesos.",
      "Revisar rendimiento esperado versus consumo real para detectar pérdidas o reprocesos.",
      "Solicitar ficha técnica del proveedor y factor actualizado del material.",
      "Evaluar alternativas con menor contenido de clínker cuando técnicamente sea viable.",
    ],
    evidence: [
      "factura de cemento",
      "guía de despacho",
      "ficha técnica",
      "registro de consumo por frente",
    ],
    nextStep: "Separar el cemento por uso operativo y validar cantidad real consumida por etapa.",
  },
  {
    key: "acero",
    label: "Acero",
    category: "Materiales",
    maxReductionBoost: 1.08,
    recommendations: [
      "Comparar toneladas compradas contra toneladas instaladas para detectar despuntes o sobrecompra.",
      "Separar acero estructural, mallas, perfiles y fierro de refuerzo para mejorar precisión del cálculo.",
      "Evaluar proveedor con contenido reciclado certificado o menor factor de emisión.",
      "Solicitar certificado de origen, ficha técnica o EPD.",
      "Registrar y valorizar despuntes o retornos para evitar inflar la huella neta.",
    ],
    evidence: [
      "factura de acero",
      "guía de despacho",
      "certificado de proveedor",
      "registro de instalación o cubicación",
    ],
    nextStep: "Cruzar compra de acero con instalación real y certificados del proveedor.",
  },
  {
    key: "diesel",
    label: "Diésel",
    category: "Transporte",
    maxReductionBoost: 1.18,
    recommendations: [
      "Separar consumo de diésel por vehículo, maquinaria, generador o ruta.",
      "Consolidar viajes y reducir retornos vacíos si el consumo está asociado a transporte.",
      "Revisar ralentí, horas máquina y mantenciones si el consumo está asociado a maquinaria.",
      "Cruzar facturas de combustible contra kilometraje, horómetro o bitácora operacional.",
      "Definir un piloto de reducción sobre la unidad con mayor consumo antes de cambiar toda la operación.",
    ],
    evidence: [
      "factura de combustible",
      "litros cargados",
      "patente o equipo",
      "kilometraje / horómetro",
      "bitácora de uso",
    ],
    nextStep: "Separar el diésel por origen de consumo y validar litros reales contra operación.",
  },
  {
    key: "combustible",
    label: "Combustible",
    category: "Transporte",
    maxReductionBoost: 1.14,
    recommendations: [
      "Clasificar combustible por uso: transporte, maquinaria, generador o proceso productivo.",
      "Asociar facturas a vehículos, equipos o centros de costo para evitar registros genéricos.",
      "Detectar unidades con consumo fuera de rango frente a kilómetros u horas trabajadas.",
      "Revisar consolidación de viajes, mantención y hábitos operativos.",
    ],
    evidence: [
      "factura de combustible",
      "detalle de litros",
      "unidad asociada",
      "bitácora operacional",
    ],
    nextStep: "Clasificar cada factura de combustible por unidad o proceso antes de reportar.",
  },
  {
    key: "kwh",
    label: "Electricidad",
    category: "Energia",
    maxReductionBoost: 1.08,
    recommendations: [
      "Separar consumo eléctrico por medidor, área o proceso para identificar el foco real.",
      "Revisar horarios de mayor consumo y detectar uso fuera de jornada.",
      "Separar consumo de red, generador y equipos críticos.",
      "Contrastar boletas eléctricas contra producción, avance o actividad operacional.",
      "Evaluar eficiencia energética solo después de identificar el proceso dominante.",
    ],
    evidence: [
      "boleta eléctrica",
      "medidor",
      "consumo kWh",
      "periodo facturado",
      "área o proceso asociado",
    ],
    nextStep: "Vincular consumo eléctrico a medidor, área o proceso para explicar la variación.",
  },
  {
    key: "electricidad",
    label: "Electricidad",
    category: "Energia",
    maxReductionBoost: 1.08,
    recommendations: [
      "Separar consumo eléctrico por medidor, área o proceso para identificar el foco real.",
      "Revisar horarios de mayor consumo y detectar uso fuera de jornada.",
      "Separar consumo de red, generador y equipos críticos.",
      "Contrastar boletas eléctricas contra producción, avance o actividad operacional.",
    ],
    evidence: [
      "boleta eléctrica",
      "medidor",
      "consumo kWh",
      "periodo facturado",
    ],
    nextStep: "Vincular consumo eléctrico a medidor, área o proceso.",
  },
  {
    key: "residuo",
    label: "Residuos",
    category: "Residuos",
    maxReductionBoost: 1.05,
    recommendations: [
      "Separar residuos por tipo: madera, fierro, escombro, orgánico, peligroso o mixto.",
      "Solicitar certificado del gestor autorizado y ticket de pesaje.",
      "Aumentar valorización antes de enviar a disposición final.",
      "Identificar procesos que generan residuo mixto y corregir separación en origen.",
      "Cruzar retiros contra avance real para detectar desviaciones.",
    ],
    evidence: [
      "certificado de residuos",
      "ticket de pesaje",
      "tipo de residuo",
      "gestor autorizado",
      "destino final",
    ],
    nextStep: "Clasificar residuos por tipo y validar peso con certificado de gestor.",
  },
  {
    key: "agua",
    label: "Agua",
    category: "Agua",
    maxReductionBoost: 1,
    recommendations: [
      "Separar consumo de agua por medidor, área o proceso.",
      "Revisar consumos fuera de tendencia y posibles fugas.",
      "Vincular consumo hídrico con producción, avance o actividad operacional.",
      "Solicitar respaldo de boleta o medición interna para trazabilidad.",
    ],
    evidence: [
      "factura de agua",
      "medidor",
      "periodo facturado",
      "consumo m3",
    ],
    nextStep: "Validar consumo por periodo y asociarlo a operación real.",
  },
];

const normalizeText = (value) =>
  String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();

const getEmissionValue = (row) =>
  Number(
    row?.emisiones_kg_co2e ??
    row?.emisiones ??
    row?.emisiones_totales ??
    row?.total_emisiones ??
    row?.co2e ??
    0
  );

const getSource = (row) =>
  row?.fuente_emision ||
  row?.fuente ||
  row?.actividad ||
  row?.nombre ||
  row?.metadata?.fuente_emision_sugerida ||
  "Fuente sin clasificar";

const getStage = (row) =>
  row?.etapa_nombre ||
  row?.metadata?.module ||
  row?.etapa ||
  row?.obra_etapa ||
  row?.frente ||
  "Sin etapa";

const normalizeCategory = (row) => {
  const raw = row?.categoria_visible || row?.categoria || row?.metadata?.categoria_sugerida || "Otros";
  const category = normalizeText(raw);
  const source = normalizeText(getSource(row));

  if (category.includes("material") || source.includes("hormigon") || source.includes("cemento") || source.includes("acero")) return "Materiales";
  if (category.includes("transporte") || source.includes("diesel") || source.includes("combustible") || source.includes("ruta")) return "Transporte";
  if (category.includes("maquinaria") || source.includes("maquinaria") || source.includes("horometro")) return "Maquinaria";
  if (category.includes("energia") || source.includes("electricidad") || source.includes("kwh")) return "Energia";
  if (category.includes("residuo") || source.includes("residuo") || source.includes("pesaje")) return "Residuos";
  if (category.includes("agua") || source.includes("agua")) return "Agua";
  if (category.includes("proceso")) return "Procesos externos";

  return raw || "Otros";
};

const getCategoryRule = (category) =>
  CATEGORY_REDUCTION_RULES[category] || CATEGORY_REDUCTION_RULES.Otros;

const groupBy = (rows, keyGetter) =>
  rows.reduce((acc, row) => {
    const key = keyGetter(row);
    const emissions = getEmissionValue(row);

    if (!acc[key]) {
      acc[key] = {
        name: key,
        emissions: 0,
        rows: [],
      };
    }

    acc[key].emissions += emissions;
    acc[key].rows.push(row);

    return acc;
  }, {});

const sumEmissions = (rows) =>
  rows.reduce((total, row) => total + getEmissionValue(row), 0);

const getCriticalItem = (grouped) =>
  Object.values(grouped).sort((a, b) => b.emissions - a.emissions)[0] || null;

const getSourceIntelligenceProfile = (source, category) => {
  const text = normalizeText(`${source} ${category}`);

  const profile = SOURCE_INTELLIGENCE_RULES.find((rule) =>
    text.includes(normalizeText(rule.key))
  );

  if (profile) return profile;

  const fallbackCategory = normalizeText(category);

  if (fallbackCategory.includes("material")) {
    return {
      key: "materiales",
      label: "Materiales",
      category: "Materiales",
      maxReductionBoost: 1,
      recommendations: [
        "Separar materiales por tipo para evitar una huella agrupada sin explicación.",
        "Comparar compras contra avance real ejecutado.",
        "Solicitar respaldo técnico o factor actualizado del proveedor.",
        "Priorizar los materiales que concentran mayor volumen y mayor factor de emisión.",
      ],
      evidence: ["factura de materiales", "guía de despacho", "ficha técnica", "avance real"],
      nextStep: "Identificar el material específico que explica la mayor parte de la huella.",
    };
  }

  if (fallbackCategory.includes("transporte")) {
    return {
      key: "transporte",
      label: "Transporte",
      category: "Transporte",
      maxReductionBoost: 1,
      recommendations: [
        "Separar viajes por origen, destino, distancia y carga transportada.",
        "Consolidar viajes y reducir retornos vacíos.",
        "Comparar proveedor cercano versus proveedor actual.",
        "Vincular facturas de combustible a rutas o unidades específicas.",
      ],
      evidence: ["factura de combustible", "ruta", "origen/destino", "kilómetros", "carga transportada"],
      nextStep: "Crear trazabilidad por viaje para calcular reducción real.",
    };
  }

  if (fallbackCategory.includes("energia")) {
    return {
      key: "energia",
      label: "Energía",
      category: "Energia",
      maxReductionBoost: 1,
      recommendations: [
        "Separar consumo por medidor, área o proceso.",
        "Detectar consumo fuera de jornada.",
        "Validar si el consumo proviene de red, generador u otro sistema.",
        "Comparar consumo contra actividad operacional.",
      ],
      evidence: ["boleta eléctrica", "medidor", "periodo", "consumo kWh"],
      nextStep: "Asociar energía a procesos para identificar foco real.",
    };
  }

  if (fallbackCategory.includes("residuo")) {
    return {
      key: "residuos",
      label: "Residuos",
      category: "Residuos",
      maxReductionBoost: 1,
      recommendations: [
        "Clasificar residuos por tipo y destino.",
        "Solicitar ticket de pesaje y certificado de gestor.",
        "Separar residuos valorizables de residuos mixtos.",
        "Revisar procesos que generan mayor descarte.",
      ],
      evidence: ["certificado de residuos", "ticket de pesaje", "gestor", "destino"],
      nextStep: "Separar residuos por tipo y validar pesaje.",
    };
  }

  return {
    key: "general",
    label: "Fuente ambiental",
    category: category || "Otros",
    maxReductionBoost: 1,
    recommendations: [
      "Completar clasificación de la fuente crítica.",
      "Validar factor de emisión utilizado.",
      "Asociar evidencia documental al registro ambiental.",
      "Separar esta fuente por proceso, proveedor o unidad operativa.",
    ],
    evidence: ["registro ambiental", "factor de emisión", "evidencia documental"],
    nextStep: "Completar datos faltantes antes de definir una intervención.",
  };
};

const getPriorityWeight = (row, criticalSource, criticalCategory, criticalStage) => {
  const source = getSource(row);
  const category = normalizeCategory(row);
  const stage = getStage(row);

  let weight = 0.25;

  if (category === criticalCategory) weight += 0.3;
  if (stage === criticalStage) weight += 0.15;
  if (source === criticalSource) weight += 0.35;

  return Math.min(weight, 1);
};

function simulateWithAmbition(rows, ambition) {
  const currentTotal = sumEmissions(rows);

  const sourceGroups = groupBy(rows, getSource);
  const categoryGroups = groupBy(rows, normalizeCategory);
  const stageGroups = groupBy(rows, getStage);

  const criticalSourceItem = getCriticalItem(sourceGroups);
  const criticalCategoryItem = getCriticalItem(categoryGroups);
  const criticalStageItem = getCriticalItem(stageGroups);

  const criticalSource = criticalSourceItem?.name || "Sin fuente crítica";
  const criticalCategory = criticalCategoryItem?.name || "Otros";
  const criticalStage = criticalStageItem?.name || "Sin etapa";
  const sourceProfile = getSourceIntelligenceProfile(criticalSource, criticalCategory);

  let avoidedEmissions = 0;

  const simulatedRows = rows.map((row) => {
    const currentEmissions = getEmissionValue(row);
    const category = normalizeCategory(row);
    const rule = getCategoryRule(category);
    const priorityWeight = getPriorityWeight(
      row,
      criticalSource,
      criticalCategory,
      criticalStage
    );
    const isSourceProfileMatch = normalizeText(getSource(row)).includes(normalizeText(sourceProfile.key));
    const sourceBoost = isSourceProfileMatch ? sourceProfile.maxReductionBoost : 1;

    const rowReductionRate = Math.min(rule.maxReduction * sourceBoost * ambition * priorityWeight, 0.34);
    const rowAvoided = currentEmissions * rowReductionRate;
    const simulatedEmissions = Math.max(currentEmissions - rowAvoided, 0);

    avoidedEmissions += rowAvoided;

    return {
      ...row,
      emisiones: simulatedEmissions,
      emisiones_kg_co2e: simulatedEmissions,
      reduccion_simulada_pct: rowReductionRate * 100,
    };
  });

  const globalCap = 0.32;
  const cappedAvoided = Math.min(avoidedEmissions, currentTotal * globalCap);
  const simulatedTotal = Math.max(currentTotal - cappedAvoided, 0);
  const reductionPct =
    currentTotal > 0 ? ((currentTotal - simulatedTotal) / currentTotal) * 100 : 0;

  const criticalSourceShare =
    currentTotal > 0 ? (criticalSourceItem?.emissions || 0) / currentTotal : 0;

  const criticalCategoryShare =
    currentTotal > 0 ? (criticalCategoryItem?.emissions || 0) / currentTotal : 0;

  return {
    currentTotal,
    simulatedTotal,
    avoidedEmissions: cappedAvoided,
    rows: simulatedRows,
    reductionPct,
    targetSource: criticalSource,
    targetCategory: criticalCategory,
    targetStage: criticalStage,
    sourceProfile,
    recommendedActions: sourceProfile.recommendations,
    evidenceNeeded: sourceProfile.evidence,
    operationalNextStep: sourceProfile.nextStep,
    activityReduction: getCategoryRule(criticalCategory).maxReduction * sourceProfile.maxReductionBoost * 100,
    dieselReduction: normalizeText(criticalSource).includes("diesel")
      ? getCategoryRule(criticalCategory).maxReduction * sourceProfile.maxReductionBoost * 100
      : 0,
    criticalSourceShare,
    criticalCategoryShare,
    ambition,
  };
}

export function optimizeScenario(rows = []) {
  const cleanRows = Array.isArray(rows)
    ? rows.filter((row) => getEmissionValue(row) > 0)
    : [];

  const currentTotal = sumEmissions(cleanRows);

  if (!cleanRows.length || currentTotal <= 0) {
    return {
      currentTotal: 0,
      simulatedTotal: 0,
      reductionPct: 0,
      avoidedEmissions: 0,
      evaluatedScenarios: 0,
      rows: [],
      targetSource: "Sin fuente crítica",
      targetCategory: "Otros",
      targetStage: "Sin etapa",
      recommendedActions: [
        "Completar registros ambientales antes de calcular escenarios.",
        "Validar factores de emisión y evidencia documental.",
      ],
      evidenceNeeded: ["registros ambientales", "factores de emisión", "evidencias"],
      operationalNextStep: "Cargar registros suficientes para detectar puntos críticos.",
      message: "No hay registros suficientes para simular escenarios.",
    };
  }

  const scenarios = [];

  for (let ambition = 0.35; ambition <= 1.001; ambition += 0.05) {
    scenarios.push(simulateWithAmbition(cleanRows, Number(ambition.toFixed(2))));
  }

  const bestScenario = scenarios.reduce((best, scenario) =>
    scenario.reductionPct > best.reductionPct ? scenario : best
  );

  const sourceSharePct = Number((bestScenario.criticalSourceShare * 100).toFixed(1));
  const categorySharePct = Number((bestScenario.criticalCategoryShare * 100).toFixed(1));

  return {
    ...bestScenario,
    currentTotal: Number(bestScenario.currentTotal.toFixed(3)),
    simulatedTotal: Number(bestScenario.simulatedTotal.toFixed(3)),
    avoidedEmissions: Number(bestScenario.avoidedEmissions.toFixed(3)),
    reductionPct: Number(bestScenario.reductionPct.toFixed(1)),
    activityReduction: Number(bestScenario.activityReduction.toFixed(1)),
    dieselReduction: Number(bestScenario.dieselReduction.toFixed(1)),
    criticalSourceSharePct: sourceSharePct,
    criticalCategorySharePct: categorySharePct,
    evaluatedScenarios: scenarios.length,
    scenarioLabel: "Máximo realista",
    potentialExplanation: `La categoría ${bestScenario.targetCategory} concentra aproximadamente ${categorySharePct}% de la huella y la fuente crítica detectada es ${bestScenario.targetSource}, con cerca de ${sourceSharePct}% del total.`,
    message:
      "Escenario calculado probando supuestos progresivos sobre fuente, categoría y etapa crítica.",
  };
}