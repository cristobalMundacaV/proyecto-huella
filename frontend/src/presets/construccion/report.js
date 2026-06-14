import {
  buildCommonReportKpis,
  buildTemporalSerie,
  filterRowsByDate,
  formatReportNumber,
  getEmissionValue,
  getRecordsWithoutFactor,
  groupReportRows,
} from "@/presets/shared/reportConfig";

const categoryOrder = ["Materiales", "Energia", "Maquinaria", "Residuos", "Transporte", "Agua", "Procesos externos", "Otros"];

const categoryConfig = {
  Materiales: { label: "Materiales", color: "#EA580C" },
  Energia: { label: "Energia", color: "#7C3AED" },
  Maquinaria: { label: "Maquinaria", color: "#65A30D" },
  Residuos: { label: "Residuos", color: "#059669" },
  Transporte: { label: "Transporte", color: "#2563EB" },
  Agua: { label: "Agua", color: "#0891B2" },
  "Procesos externos": { label: "Procesos externos", color: "#DB2777" },
  Otros: { label: "Otros", color: "#475569" },
};

function buildReport(rows, filters, context = {}) {
  const registros = filterRowsByDate(rows, filters);
  const serie = buildTemporalSerie(registros, filters.agrupacion || "mes");
  const categorias = groupReportRows(registros, (row) => row.categoria || "Otros");
  const modules = groupReportRows(registros, (row) => row.etapa_nombre || row.obra_nombre || "Sin etapa");
  const fuentes = groupReportRows(registros, (row) => row.fuente_emision || "Sin fuente");
  const common = buildCommonReportKpis(registros);
  const maxPeriod = serie.reduce((best, item) => (!best || item.emisiones > best.emisiones ? item : best), null);
  const last = serie[serie.length - 1];
  const previous = serie[serie.length - 2];
  const variation = previous?.emisiones > 0 ? ((Number(last?.emisiones || 0) - previous.emisiones) / previous.emisiones) * 100 : 0;
  const tendencia = serie.length < 2 ? "Sin datos" : Math.abs(variation) <= 3 ? "Estable" : variation > 0 ? "Al alza" : "A la baja";

  return {
    rows: registros,
    serie,
    categorias,
    modules,
    fuentes,
    kpis: buildKpis({ common, modules, categorias, serie, tendencia, variation, context }),
    insights: buildInsights({ common, modules, categorias, fuentes, tendencia, maxPeriod }),
    executiveSummary: buildExecutiveSummary({ common, modules, categorias, fuentes, tendencia, maxPeriod, context }),
    emptyMessage: "No hay registros de construccion en este periodo. Importa datos o registra emisiones para activar el reporte.",
    primaryModuleView: "obras",
  };
}

function buildKpis({ common, modules, categorias, serie, tendencia, variation, context }) {
  const maxPeriod = serie.reduce((best, item) => (!best || item.emisiones > best.emisiones ? item : best), null);
  return [
    { label: "Emisiones totales", value: `${formatReportNumber(common.total)} kg CO2e`, description: "Huella del periodo", icon: "flame", tone: "danger" },
    { label: "Tendencia", value: tendencia, description: `${formatReportNumber(variation)}% vs periodo anterior`, icon: "trend", tone: tendencia === "A la baja" ? "success" : tendencia === "Al alza" ? "danger" : "warning" },
    { label: "Fuente critica", value: common.criticalSource, description: `${formatReportNumber(common.criticalSourceEmissions)} kg CO2e`, icon: "target", tone: "warning" },
    { label: "Etapa critica", value: modules[0]?.label || "Sin datos", description: `${formatReportNumber(modules[0]?.emisiones || 0)} kg CO2e`, icon: "layers", tone: "info" },
    { label: "Categoria dominante", value: categorias[0]?.label || "Sin datos", description: `${formatReportNumber(categorias[0]?.emisiones || 0)} kg CO2e`, icon: "chart", tone: "violet" },
    { label: "Periodo mayor emision", value: maxPeriod?.label || "Sin datos", description: `${formatReportNumber(maxPeriod?.emisiones || 0)} kg CO2e`, icon: "calendar", tone: "warning" },
    { label: "Intensidad", value: context.dashboardData?.intensidad_carbono ? `${formatReportNumber(context.dashboardData.intensidad_carbono, 2)} kg CO2e/m2` : "Pendiente", description: "Si existe superficie declarada", icon: "gauge", tone: "info" },
    { label: "Evidencia respaldada", value: context.dashboardData?.evidencia_respaldada ? `${formatReportNumber(context.dashboardData.evidencia_respaldada, 0)}%` : "Pendiente", description: "Respaldo documental", icon: "database", tone: "success" },
  ];
}

function buildInsights({ common, modules, categorias, tendencia, maxPeriod }) {
  if (!common.total) return ["Aun no existen emisiones registradas para el periodo seleccionado."];
  return [
    `La tendencia del periodo es ${tendencia}.`,
    `La fuente critica es ${common.criticalSource}, con ${formatReportNumber(common.criticalSourceEmissions)} kg CO2e.`,
    `La etapa critica es ${modules[0]?.label || "Sin datos"} y la categoria dominante es ${categorias[0]?.label || "Sin datos"}.`,
    `El periodo con mayor emision es ${maxPeriod?.label || "Sin datos"}.`,
  ];
}

function buildExecutiveSummary({ common, modules, categorias, tendencia, maxPeriod, context }) {
  const empresa = context.activeConstructora?.nombre || "La empresa";
  if (!common.total) return `${empresa} no registra emisiones de construccion en el periodo analizado.`;
  return `${empresa} registro ${formatReportNumber(common.total)} kg CO2e en el periodo. La tendencia es ${tendencia}, con foco principal en ${common.criticalSource}, etapa ${modules[0]?.label || "Sin datos"} y categoria ${categorias[0]?.label || "Sin datos"}. El periodo mas alto fue ${maxPeriod?.label || "Sin datos"}.`;
}

function buildExportPayload(report, context) {
  return {
    empresa: context.activeConstructora?.nombre || "",
    preset: "construccion",
    periodo: context.filters,
    kpis: report.kpis,
    insights: report.insights,
    registros: report.rows,
  };
}

export const construccionReport = {
  title: "Reporte ambiental de construccion",
  subtitle: "Analiza emisiones por obra, etapa, categoria, fuente y periodo.",
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
    { key: "categoria", label: "Categoria", resolver: (row) => row.categoria || "Otros" },
    { key: "fuente", label: "Fuente", resolver: (row) => row.fuente_emision || "Sin fuente" },
    { key: "etapa", label: "Etapa", resolver: (row) => row.etapa_nombre || "Sin etapa" },
    { key: "obra", label: "Obra", resolver: (row) => row.obra_nombre || row.obra_codigo || "-" },
    { key: "cantidad", label: "Cantidad", align: "right", resolver: (row) => formatReportNumber(row.cantidad, 2) },
    { key: "emisiones", label: "Emisiones", align: "right", resolver: (row) => `${formatReportNumber(getEmissionValue(row))} kg CO2e` },
  ],
};
