const modules = [
  { key: "energia", label: "Energia", supported: false, columns: ["fecha", "area", "proceso", "medidor", "consumo_kwh", "turno", "factor_emision", "observaciones"] },
  { key: "combustible", label: "Combustible", supported: false, columns: ["fecha", "area", "tipo_combustible", "cantidad", "unidad", "factor_emision", "observaciones"] },
  { key: "procesos", label: "Procesos", supported: false, columns: ["fecha", "area", "proceso", "lote_produccion", "cantidad", "unidad", "factor_emision", "observaciones"] },
  { key: "residuos", label: "Residuos", supported: false, columns: ["fecha", "area", "tipo_residuo", "cantidad", "unidad", "gestor", "factor_emision", "observaciones"] },
  { key: "agua", label: "Agua", supported: false, columns: ["fecha", "area", "medidor", "agua_m3", "turno", "factor_emision", "observaciones"] },
  { key: "factores", label: "Factores", supported: false, columns: ["categoria", "module", "actividad", "unidad", "factor_emision", "fuente", "anio"] },
  { key: "evidencias", label: "Evidencias", supported: false, columns: ["fecha_documento", "tipo_evidencia", "area", "proceso", "archivo", "observaciones"] },
];

export const industrialImport = {
  title: "Importaciones industriales",
  subtitle: "Plantillas preparadas para energia, combustible, procesos, residuos y agua.",
  modules,
  templates: modules,
  validationRules: {},
  previewColumns: {},
  buildPayload: null,
  buildSummary: null,
  buildRecommendations() {
    return ["La importacion industrial esta preparada. La conexion backend masiva queda para una fase posterior."];
  },
  emptyMessage: "No hay importaciones industriales cargadas. Descarga una plantilla de energia, procesos, residuos o agua para comenzar.",
};
