import {
  buildCommonReportKpis,
  buildTemporalSerie,
  filterRowsByDate,
  formatReportNumber,
  getEmissionValue,
  getMetadata,
  getRecordsWithoutFactor,
  groupReportRows,
} from "@/presets/shared/reportConfig";

const moduleLabels = {
  recepcion_trozas: "Recepcion de trozas",
  produccion: "Produccion",
  secado: "Secado",
  energia: "Energia",
  transporte_forestal: "Transporte forestal",
  residuos_subproductos: "Residuos / Subproductos",
};

const categoryOrder = ["Materia prima", "Produccion", "Secado", "Energia", "Transporte", "Residuos", "Subproductos", "Otros"];

const categoryConfig = {
  "Materia prima": { label: "Materia prima", color: "#059669" },
  Produccion: { label: "Produccion", color: "#2563EB" },
  Secado: { label: "Secado", color: "#EA580C" },
  Energia: { label: "Energia", color: "#7C3AED" },
  Transporte: { label: "Transporte", color: "#0F766E" },
  Residuos: { label: "Residuos", color: "#65A30D" },
  Subproductos: { label: "Subproductos", color: "#0891B2" },
  Otros: { label: "Otros", color: "#475569" },
};

const num = (row, field, fallback = 0) => Number(getMetadata(row)?.[field] ?? row?.[field] ?? fallback) || 0;
const sum = (rows, field, fallbackField = null) => rows.reduce((total, row) => total + num(row, field, fallbackField ? row?.[fallbackField] : 0), 0);
const avg = (rows, field) => {
  const values = rows.map((row) => num(row, field)).filter((value) => value > 0);
  return values.length ? values.reduce((total, value) => total + value, 0) / values.length : 0;
};

function getPresetRows(rows, context = {}) {
  const filtered = rows.filter((row) => getMetadata(row).preset === "aserradero");
  return filtered.length ? filtered : context.activePreset?.key === "aserradero" ? rows : filtered;
}

function byModule(rows, moduleKey) {
  return rows.filter((row) => getMetadata(row).module === moduleKey);
}

function buildReport(rows, filters, context = {}) {
  const scoped = getPresetRows(rows, context);
  const registros = filterRowsByDate(scoped, filters);
  const serie = buildTemporalSerie(registros, filters.agrupacion || "mes");
  const categorias = groupReportRows(registros, (row) => getMetadata(row).aserradero_category || row.categoria || "Otros");
  const modules = groupReportRows(registros, (row) => moduleLabels[getMetadata(row).module] || getMetadata(row).module || "Sin modulo");
  const fuentes = groupReportRows(registros, (row) => row.fuente_emision || "Sin fuente");
  const common = buildCommonReportKpis(registros);
  const missingFactors = getRecordsWithoutFactor(registros);
  const reportContext = { ...context, rows: registros, common, categorias, modules, fuentes, missingFactors };
  return {
    rows: registros,
    serie,
    categorias,
    modules,
    fuentes,
    kpis: buildKpis(reportContext),
    insights: buildInsights(reportContext),
    executiveSummary: buildExecutiveSummary(reportContext),
    emptyMessage: "No hay operaciones forestales registradas en este periodo. Registra recepcion de trozas, produccion, secado o transporte forestal para activar el reporte.",
    primaryModuleView: "recepcion_trozas",
  };
}

function buildKpis(context) {
  const rows = context.rows || [];
  const recepcion = byModule(rows, "recepcion_trozas");
  const produccion = byModule(rows, "produccion");
  const secado = byModule(rows, "secado");
  const energia = byModule(rows, "energia");
  const transporte = byModule(rows, "transporte_forestal");
  const residuos = byModule(rows, "residuos_subproductos");
  const valorizados = residuos.filter((row) => String(getMetadata(row).valorizado || "").toLowerCase().includes("si")).length;

  return [
    { label: "Huella total del periodo", value: `${formatReportNumber(context.common.total)} kg CO2e`, description: "Emisiones forestales", icon: "leaf", tone: "danger" },
    { label: "m3 recibidos", value: formatReportNumber(sum(recepcion, "volumen_m3", "cantidad"), 1), description: "Recepcion de trozas", icon: "package", tone: "success" },
    { label: "m3 procesados", value: formatReportNumber(sum(produccion, "volumen_entrada_m3", "cantidad"), 1), description: "Produccion aserradero", icon: "factory", tone: "info" },
    { label: "Rendimiento promedio", value: `${formatReportNumber(avg(produccion, "rendimiento_pct"), 1)}%`, description: "Entrada / salida", icon: "gauge", tone: "success" },
    { label: "Energia registrada", value: `${formatReportNumber(sum([...energia, ...secado], "consumo_kwh", "cantidad"), 1)} kWh`, description: "Energia y secado", icon: "zap", tone: "warning" },
    { label: "km transporte forestal", value: formatReportNumber(sum(transporte, "distancia_km"), 1), description: "Distancia registrada", icon: "route", tone: "info" },
    { label: "Litros diesel", value: formatReportNumber(sum(transporte, "litros_diesel", "cantidad"), 1), description: "Combustible forestal", icon: "fuel", tone: "warning" },
    { label: "Residuos valorizados", value: `${formatReportNumber(residuos.length ? (valorizados / residuos.length) * 100 : 0, 1)}%`, description: "Valorizacion declarada", icon: "recycle", tone: "success" },
    { label: "Registros sin factor", value: formatReportNumber(context.missingFactors.length, 0), description: "Pendientes de calculo", icon: "alert", tone: "danger" },
  ];
}

function buildInsights(context) {
  if (!context.common.total) return ["No existen operaciones forestales con emisiones en el periodo seleccionado."];
  const moduleLabel = context.modules[0]?.label || "Sin modulo";
  const normalized = String(moduleLabel).toLowerCase();
  const insights = [
    `El principal foco operativo es ${moduleLabel}, con ${formatReportNumber(context.modules[0]?.emisiones || 0)} kg CO2e.`,
  ];
  if (normalized.includes("transporte")) insights.push("Controlar litros, km, carga por viaje, viajes vacios y origen/destino.");
  if (normalized.includes("energia")) insights.push("Separar consumo por area, turno y medidor para ubicar consumos criticos.");
  if (normalized.includes("secado")) insights.push("Medir kWh por camara, horas de secado, humedad inicial y humedad final.");
  if (normalized.includes("produccion")) insights.push("Medir rendimiento entrada/salida, merma y lotes procesados.");
  if (normalized.includes("residuos") || normalized.includes("subproductos")) insights.push("Separar aserrin, corteza, despuntes, valorizacion y gestor.");
  if (context.missingFactors.length) insights.push("Completar factores de emision para cerrar calculo ambiental.");
  return insights;
}

function buildExecutiveSummary(context) {
  const empresa = context.activeConstructora?.nombre || "La operacion forestal";
  if (!context.common.total) return `${empresa} no registra operaciones forestales en el periodo analizado.`;
  const foco = context.modules[0]?.label || context.common.criticalCategory;
  return `${empresa} registro ${formatReportNumber(context.common.total)} kg CO2e en el periodo analizado. El principal foco de impacto se concentra en ${foco}, por lo que se recomienda priorizar control de consumo, rendimiento operativo y trazabilidad por lote.`;
}

function buildExportPayload(report, context) {
  return { empresa: context.activeConstructora?.nombre || "", preset: "aserradero", periodo: context.filters, kpis: report.kpis, insights: report.insights, registros: report.rows };
}

export const aserraderoReport = {
  title: "Reporte ambiental forestal",
  subtitle: "Analiza recepcion de trozas, produccion, secado, energia, transporte forestal y valorizacion.",
  categoryOrder,
  categoryConfig,
  groupingOptions: [
    { value: "mes", label: "Mes" },
    { value: "dia", label: "Dia" },
    { value: "categoria", label: "Categoria" },
    { value: "modulo", label: "Modulo operativo" },
    { value: "fuente", label: "Fuente de emision" },
    { value: "proveedor", label: "Proveedor" },
    { value: "lote", label: "Lote" },
  ],
  buildReport,
  buildInsights,
  buildExecutiveSummary,
  buildKpis,
  buildExportPayload,
  tableColumns: [
    { key: "fecha", label: "Fecha", resolver: (row) => row.fecha || "Sin fecha" },
    { key: "modulo", label: "Modulo", resolver: (row) => moduleLabels[getMetadata(row).module] || "Sin modulo" },
    { key: "categoria", label: "Categoria", resolver: (row) => getMetadata(row).aserradero_category || row.categoria || "Otros" },
    { key: "fuente", label: "Fuente", resolver: (row) => row.fuente_emision || "Sin fuente" },
    { key: "lote", label: "Lote", resolver: (row) => getMetadata(row).lote || "-" },
    { key: "proveedor", label: "Proveedor / origen", resolver: (row) => row.proveedor || getMetadata(row).proveedor_madera || getMetadata(row).origen || "-" },
    { key: "cantidad", label: "Cantidad", align: "right", resolver: (row) => formatReportNumber(row.cantidad, 2) },
    { key: "unidad", label: "Unidad", resolver: (row) => row.unidad || "-" },
    { key: "emisiones", label: "Emisiones", align: "right", resolver: (row) => `${formatReportNumber(getEmissionValue(row))} kg CO2e` },
    { key: "factor", label: "Factor", align: "right", resolver: (row) => formatReportNumber(row.factor_emision, 4) },
  ],
};
