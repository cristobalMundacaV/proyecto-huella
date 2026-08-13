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

const categoryOrder = ["Energia", "Combustible", "Procesos", "Residuos", "Agua", "Transporte", "Otros"];
const categoryConfig = {
  Energia: { label: "Energia", color: "#7C3AED" },
  Combustible: { label: "Combustible", color: "#EA580C" },
  Procesos: { label: "Procesos", color: "#2563EB" },
  Residuos: { label: "Residuos", color: "#059669" },
  Agua: { label: "Agua", color: "#0891B2" },
  Transporte: { label: "Transporte", color: "#0F766E" },
  Otros: { label: "Otros", color: "#475569" },
};

const num = (row, field, fallback = 0) => Number(getMetadata(row)[field] ?? row?.[field] ?? fallback) || 0;

function getRows(rows, context = {}) {
  const filtered = rows.filter((row) => getMetadata(row).preset === "industrial");
  return filtered.length ? filtered : context.activePreset?.key === "industrial" ? rows : filtered;
}

function buildReport(rows, filters, context = {}) {
  const registros = filterRowsByDate(getRows(rows, context), filters);
  const serie = buildTemporalSerie(registros, filters.agrupacion || "mes");
  const categorias = groupReportRows(registros, (row) => getMetadata(row).categoria_industrial || row.categoria || "Otros");
  const modules = groupReportRows(registros, (row) => getMetadata(row).proceso || getMetadata(row).area || "Sin proceso");
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
    emptyMessage: "No hay registros industriales en este periodo. Registra energia, procesos, residuos o agua para activar el reporte.",
    primaryModuleView: "emisiones",
  };
}

function buildKpis(context) {
  const rows = context.rows || [];
  const energy = rows.reduce((total, row) => total + num(row, "consumo_kwh"), 0);
  const processes = new Set(rows.map((row) => getMetadata(row).proceso || row.fuente_emision).filter(Boolean)).size;
  const residues = rows.reduce((total, row) => total + num(row, "residuos_kg", row.cantidad), 0);
  const water = rows.reduce((total, row) => total + num(row, "agua_m3"), 0);
  return [
    { label: "Huella total", value: `${formatReportNumber(context.common.total)} kg CO2e`, description: "Emisiones industriales", icon: "factory", tone: "danger" },
    { label: "Consumo energetico", value: `${formatReportNumber(energy, 1)} kWh`, description: "Energia registrada", icon: "zap", tone: "warning" },
    { label: "Procesos registrados", value: formatReportNumber(processes, 0), description: "Procesos con actividad", icon: "database", tone: "info" },
    { label: "Residuos generados", value: `${formatReportNumber(residues, 1)} kg`, description: "Masa declarada", icon: "recycle", tone: "warning" },
    { label: "Agua registrada", value: `${formatReportNumber(water, 1)} m3`, description: "Consumo hidrico", icon: "droplets", tone: "info" },
    { label: "Categoria critica", value: context.categorias[0]?.label || "Sin datos", description: `${formatReportNumber(context.categorias[0]?.emisiones || 0)} kg CO2e`, icon: "target", tone: "violet" },
    { label: "Registros sin factor", value: formatReportNumber(context.missingFactors.length, 0), description: "Pendientes de calculo", icon: "alert", tone: "danger" },
    { label: "Evidencia respaldada", value: context.dashboardData?.evidencia_respaldada ? `${formatReportNumber(context.dashboardData.evidencia_respaldada, 0)}%` : "Pendiente", description: "Respaldo documental", icon: "database", tone: "success" },
  ];
}

function buildInsights(context) {
  if (!context.common.total) return ["Aun no existen registros industriales para el periodo seleccionado."];
  return [
    `La categoria critica es ${context.categorias[0]?.label || "Sin datos"}.`,
    `El proceso o area prioritaria es ${context.modules[0]?.label || "Sin datos"}.`,
    "Separar energia, combustible, agua y residuos mejora la trazabilidad del reporte industrial.",
  ];
}

function buildExecutiveSummary(context) {
  const empresa = context.activeOrganizacion?.nombre || "La operacion industrial";
  if (!context.common.total) return `${empresa} no registra actividad industrial en el periodo analizado.`;
  return `${empresa} registro ${formatReportNumber(context.common.total)} kg CO2e. La categoria critica es ${context.categorias[0]?.label || "Sin datos"} y el proceso prioritario es ${context.modules[0]?.label || "Sin datos"}.`;
}

function buildExportPayload(report, context) {
  return { empresa: context.activeOrganizacion?.nombre || "", preset: "industrial", periodo: context.filters, kpis: report.kpis, insights: report.insights, registros: report.rows };
}

export const industrialReport = {
  title: "Reporte ambiental industrial",
  subtitle: "Analiza energia, procesos, residuos, agua, combustible y transporte.",
  categoryOrder,
  categoryConfig,
  groupingOptions: [
    { value: "mes", label: "Mes" },
    { value: "dia", label: "Dia" },
    { value: "categoria", label: "Categoria" },
    { value: "fuente", label: "Fuente de emision" },
  ],
  buildReport,
  buildInsights,
  buildExecutiveSummary,
  buildKpis,
  buildExportPayload,
  tableColumns: [
    { key: "fecha", label: "Fecha", resolver: (row) => row.fecha || "Sin fecha" },
    { key: "proceso", label: "Area / proceso", resolver: (row) => getMetadata(row).area || getMetadata(row).proceso || "-" },
    { key: "categoria", label: "Categoria", resolver: (row) => getMetadata(row).categoria_industrial || row.categoria || "Otros" },
    { key: "fuente", label: "Fuente", resolver: (row) => row.fuente_emision || "Sin fuente" },
    { key: "cantidad", label: "Cantidad", align: "right", resolver: (row) => formatReportNumber(row.cantidad, 2) },
    { key: "unidad", label: "Unidad", resolver: (row) => row.unidad || "-" },
    { key: "emisiones", label: "Emisiones", align: "right", resolver: (row) => `${formatReportNumber(getEmissionValue(row))} kg CO2e` },
  ],
};
