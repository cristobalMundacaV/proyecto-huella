import { formatNumber } from "@/shared/utils/formatters";

const modules = [
  "recepcion_trozas",
  "produccion",
  "secado",
  "energia",
  "transporte_forestal",
  "residuos_subproductos",
];

function unitIncludes(record, text) {
  return String(record?.unidad || "").toLowerCase().includes(text);
}

function findFactor(factors, predicate) {
  return factors.find(predicate) || null;
}

function suggestFactor(record, factors) {
  const module = record?.metadata?.module || "";
  const category = record?.metadata?.aserradero_category || record?.categoria || "";
  let reason = "Se sugiere revisar factores por categoria, unidad y modulo operativo.";
  let factor = null;

  if (module === "secado" && unitIncludes(record, "kwh")) {
    reason = "Este registro pertenece al modulo Secado y usa unidad kWh. Se sugiere revisar factores de Energia asociados a consumo electrico.";
    factor = findFactor(factors, (item) => item.categoria === "Energia" && String(item.unidad || "").toLowerCase().includes("kwh"));
  } else if (module === "transporte_forestal" && record?.metadata?.litros_diesel) {
    reason = "Este registro de transporte forestal contiene litros diesel. Se sugiere un factor de combustible diesel.";
    factor = findFactor(factors, (item) => item.module === "transporte_forestal" || String(item.unidad || "").toLowerCase().includes("diesel"));
  } else if (module === "transporte_forestal" && unitIncludes(record, "km")) {
    reason = "Este registro usa kilometros. Se sugiere revisar factores de transporte por distancia.";
    factor = findFactor(factors, (item) => item.categoria === "Transporte" && String(item.unidad || "").toLowerCase().includes("km"));
  } else if (module === "residuos_subproductos") {
    reason = "Este registro pertenece a residuos o subproductos. Si esta valorizado, valida factor o respaldo de valorizacion.";
    factor = findFactor(factors, (item) => item.categoria === "Residuos");
  } else if (module === "produccion") {
    reason = "Este registro de produccion puede requerir factor de proceso productivo o energia si declara kWh.";
    factor = findFactor(factors, (item) => item.module === "produccion" || item.categoria === "Procesos externos");
  } else if (module === "recepcion_trozas") {
    reason = "La recepcion de trozas no debe asumir emisiones por volumen de madera; aplica factor solo si hay transporte, combustible o proceso asociado.";
    factor = findFactor(factors, (item) => item.module === "recepcion_trozas");
  }

  if (!factor) {
    factor = findFactor(factors, (item) => item.module === module) ||
      findFactor(factors, (item) => item.categoria === record?.categoria || item.categoria === category);
  }

  return { factor, reason };
}

function buildCommonKpis(factors, records) {
  const pending = records.filter((record) => !Number(record.factor_emision || 0));
  const calculatedPct = records.length ? ((records.length - pending.length) / records.length) * 100 : 0;
  const validation = factors.filter((factor) => factor.metadata?.requires_validation).length;
  return { pending, calculatedPct, validation };
}

export const aserraderoFactors = {
  title: "Factores de emision para operacion forestal",
  subtitle: "Gestiona factores para energia, secado, transporte forestal, residuos y procesos del aserradero.",
  categories: ["Materia prima", "Produccion", "Secado", "Energia", "Transporte", "Residuos", "Subproductos", "Otros"],
  modules,
  suggestionRules: { suggestFactor },
  buildKpis(factors, records) {
    const { pending, calculatedPct, validation } = buildCommonKpis(factors, records);
    const byCategory = topPending(pending, (record) => record.metadata?.aserradero_category || record.categoria || "Otros");
    const byModule = topPending(pending, (record) => record.metadata?.module || "Sin modulo");
    return [
      { label: "Factores disponibles", value: formatNumber(factors.length, 0), tone: "info" },
      { label: "Registros sin factor", value: formatNumber(pending.length, 0), tone: pending.length ? "danger" : "success" },
      { label: "% registros calculados", value: `${formatNumber(calculatedPct, 1)}%`, tone: calculatedPct >= 80 ? "success" : "warning" },
      { label: "Factores por validar", value: formatNumber(validation, 0), tone: validation ? "warning" : "success" },
      { label: "Categoria con mas pendientes", value: byCategory, tone: "neutral" },
      { label: "Modulo con mas pendientes", value: byModule, tone: "neutral" },
    ];
  },
  buildRecommendations(factors, pending) {
    if (!factors.length) return ["No hay factores configurados para operacion forestal. Agrega factores para energia, secado, transporte forestal y residuos para cerrar el calculo ambiental."];
    if (!pending.length) return ["Todos los registros forestales tienen factor asignado."];
    return ["Prioriza registros de secado, energia y transporte forestal sin factor.", "Valida factores referenciales antes de usarlos en reportes oficiales."];
  },
  getFactorQualityStatus(factors, records) {
    const { pending, calculatedPct, validation } = buildCommonKpis(factors, records);
    if (!factors.length) return "Sin factores";
    if (validation) return "Requiere validacion";
    if (calculatedPct >= 90) return "Calculo bien respaldado";
    if (pending.length) return "Calculo parcialmente cerrado";
    return "Factores incompletos";
  },
};

function topPending(rows, resolver) {
  const counts = rows.reduce((acc, row) => {
    const key = resolver(row);
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || "Sin pendientes";
}

export { suggestFactor };
