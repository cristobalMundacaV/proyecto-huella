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
  Residuos: {
    maxReduction: 0.15,
    label: "Residuos",
  },
  Agua: {
    maxReduction: 0.08,
    label: "Agua",
  },
  Otros: {
    maxReduction: 0.06,
    label: "Otros",
  },
};

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
      row?.co2e ??
      0
  );

const getSource = (row) =>
  row?.fuente_emision ||
  row?.fuente ||
  row?.actividad ||
  row?.nombre ||
  "Fuente sin clasificar";

const getStage = (row) =>
  row?.etapa_nombre ||
  row?.etapa ||
  row?.obra_etapa ||
  row?.frente ||
  "Sin etapa";

const normalizeCategory = (row) => {
  const raw = row?.categoria || "Otros";
  const category = normalizeText(raw);

  if (category.includes("material")) return "Materiales";
  if (category.includes("transporte")) return "Transporte";
  if (category.includes("maquinaria")) return "Maquinaria";
  if (category.includes("energia")) return "Energia";
  if (category.includes("residuo")) return "Residuos";
  if (category.includes("agua")) return "Agua";

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

    const rowReductionRate = rule.maxReduction * ambition * priorityWeight;
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

  const globalCap = 0.28;
  const cappedAvoided = Math.min(avoidedEmissions, currentTotal * globalCap);
  const simulatedTotal = Math.max(currentTotal - cappedAvoided, 0);
  const reductionPct =
    currentTotal > 0 ? ((currentTotal - simulatedTotal) / currentTotal) * 100 : 0;

  const criticalSourceShare =
    currentTotal > 0 ? (criticalSourceItem?.emissions || 0) / currentTotal : 0;

  return {
    currentTotal,
    simulatedTotal,
    avoidedEmissions: cappedAvoided,
    reductionPct,
    rows: simulatedRows,
    targetSource: criticalSource,
    targetCategory: criticalCategory,
    targetStage: criticalStage,
    activityReduction: getCategoryRule(criticalCategory).maxReduction * 100,
    dieselReduction: normalizeText(criticalSource).includes("diesel")
      ? getCategoryRule(criticalCategory).maxReduction * 100
      : 0,
    criticalSourceShare,
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

  return {
    ...bestScenario,
    currentTotal: Number(bestScenario.currentTotal.toFixed(3)),
    simulatedTotal: Number(bestScenario.simulatedTotal.toFixed(3)),
    avoidedEmissions: Number(bestScenario.avoidedEmissions.toFixed(3)),
    reductionPct: Number(bestScenario.reductionPct.toFixed(1)),
    activityReduction: Number(bestScenario.activityReduction.toFixed(1)),
    dieselReduction: Number(bestScenario.dieselReduction.toFixed(1)),
    evaluatedScenarios: scenarios.length,
    scenarioLabel: "Máximo realista",
    message:
      "Escenario calculado probando supuestos progresivos sobre fuente, categoría y etapa crítica.",
  };
}
