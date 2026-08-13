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

const categoryOrder = ["Combustible", "Rutas", "Flota", "Mantencion", "Carga", "Clientes", "Otros"];
const categoryConfig = {
  Combustible: { label: "Combustible", color: "#EA580C" },
  Rutas: { label: "Rutas", color: "#2563EB" },
  Flota: { label: "Flota", color: "#059669" },
  Mantencion: { label: "Mantencion", color: "#7C3AED" },
  Carga: { label: "Carga", color: "#0891B2" },
  Clientes: { label: "Clientes", color: "#DB2777" },
  Otros: { label: "Otros", color: "#475569" },
};

const num = (row, field) => Number(getMetadata(row)[field] ?? row?.[field] ?? 0) || 0;

function getRows(rows, context = {}) {
  const filtered = rows.filter((row) => getMetadata(row).preset === "transporte");
  return filtered.length ? filtered : context.activePreset?.key === "transporte" ? rows : filtered;
}

function buildReport(rows, filters, context = {}) {
  const registros = filterRowsByDate(getRows(rows, context), filters);
  const serie = buildTemporalSerie(registros, filters.agrupacion || "mes");
  const categorias = groupReportRows(registros, (row) => getMetadata(row).categoria_transporte || row.categoria || "Otros");
  const modules = groupReportRows(registros, (row) => getMetadata(row).ruta || getMetadata(row).module || "Sin ruta");
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
    emptyMessage: "No hay registros logisticos en este periodo. Registra viajes, combustible o rutas para activar el reporte.",
    primaryModuleView: "viajes",
  };
}

function buildKpis(context) {
  const rows = context.rows || [];
  const km = rows.reduce((total, row) => total + num(row, "distancia_km"), 0);
  const litros = rows.reduce((total, row) => total + num(row, "litros_combustible"), 0);
  const viajes = new Set(rows.map((row) => getMetadata(row).viaje_id).filter(Boolean)).size || rows.length;
  const vehiculos = new Set(rows.map((row) => getMetadata(row).patente || getMetadata(row).vehiculo).filter(Boolean)).size;
  return [
    { label: "Huella total", value: `${formatReportNumber(context.common.total)} kg CO2e`, description: "Emisiones logisticas", icon: "truck", tone: "danger" },
    { label: "km recorridos", value: formatReportNumber(km, 1), description: "Distancia registrada", icon: "route", tone: "info" },
    { label: "Litros combustible", value: formatReportNumber(litros, 1), description: "Consumo declarado", icon: "fuel", tone: "warning" },
    { label: "Viajes registrados", value: formatReportNumber(viajes, 0), description: "Eventos logisticos", icon: "database", tone: "info" },
    { label: "Vehiculos registrados", value: formatReportNumber(vehiculos, 0), description: "Flota activa", icon: "factory", tone: "success" },
    { label: "Emisiones por km", value: km > 0 ? `${formatReportNumber(context.common.total / km, 2)} kg/km` : "Sin km", description: "Intensidad logistica", icon: "gauge", tone: "success" },
    { label: "Ruta critica", value: context.modules[0]?.label || "Sin datos", description: `${formatReportNumber(context.modules[0]?.emisiones || 0)} kg CO2e`, icon: "target", tone: "warning" },
    { label: "Registros sin factor", value: formatReportNumber(context.missingFactors.length, 0), description: "Pendientes de calculo", icon: "alert", tone: "danger" },
  ];
}

function buildInsights(context) {
  if (!context.common.total) return ["Aun no existen registros de transporte para el periodo seleccionado."];
  return [
    `La ruta o modulo critico es ${context.modules[0]?.label || "Sin datos"}.`,
    "Completar km, litros, vehiculo, carga y ruta permite calcular intensidad por viaje.",
    context.missingFactors.length ? "Existen registros sin factor de emision que deben completarse." : "Los registros del periodo cuentan con factor de emision.",
  ];
}

function buildExecutiveSummary(context) {
  const empresa = context.activeOrganizacion?.nombre || "La operacion logistica";
  if (!context.common.total) return `${empresa} no registra actividad logistica en el periodo analizado.`;
  return `${empresa} registro ${formatReportNumber(context.common.total)} kg CO2e en transporte. El foco principal esta en ${context.modules[0]?.label || "Sin ruta"}, por lo que conviene revisar combustible, km, carga y frecuencia de viajes.`;
}

function buildExportPayload(report, context) {
  return { empresa: context.activeOrganizacion?.nombre || "", preset: "transporte", periodo: context.filters, kpis: report.kpis, insights: report.insights, registros: report.rows };
}

export const transporteReport = {
  title: "Reporte ambiental logistico",
  subtitle: "Analiza huella por combustible, rutas, flota, viajes y carga.",
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
    { key: "vehiculo", label: "Vehiculo", resolver: (row) => getMetadata(row).patente || getMetadata(row).vehiculo || "-" },
    { key: "ruta", label: "Ruta", resolver: (row) => getMetadata(row).ruta || `${getMetadata(row).origen || ""} ${getMetadata(row).destino || ""}`.trim() || "-" },
    { key: "litros", label: "Litros", align: "right", resolver: (row) => formatReportNumber(num(row, "litros_combustible"), 1) },
    { key: "km", label: "Km", align: "right", resolver: (row) => formatReportNumber(num(row, "distancia_km"), 1) },
    { key: "carga", label: "Carga", resolver: (row) => getMetadata(row).carga || getMetadata(row).carga_ton || "-" },
    { key: "emisiones", label: "Emisiones", align: "right", resolver: (row) => `${formatReportNumber(getEmissionValue(row))} kg CO2e` },
  ],
};
