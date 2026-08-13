const modules = [
  { key: "organizaciones", label: "Empresas / organizaciones", supported: true, backendKind: "organizaciones", columns: ["organizacion_id", "nombre", "rut", "region", "comuna", "direccion", "rubro", "email", "telefono", "contacto", "observaciones"] },
  { key: "factores", label: "Factores", supported: true, backendKind: "factores", columns: ["fuente_emision", "categoria", "unidad", "factor_emision", "fuente", "anio", "observaciones"] },
  { key: "etapas", label: "Etapas", supported: true, backendKind: "etapas", columns: ["etapa_id", "organizacion_id", "nombre", "tipo", "region", "comuna", "estado", "observaciones"] },
  { key: "obras", label: "Obras", supported: true, backendKind: "obras", columns: ["codigo_obra", "organizacion_id", "etapa_id", "nombre", "tipo_proyecto", "fecha", "superficie_m2", "ubicacion", "observaciones"] },
  { key: "registros", label: "Registros de emision", supported: true, backendKind: "registros", columns: ["registro_id", "codigo_obra", "etapa_id", "fuente_emision", "categoria", "cantidad", "unidad", "factor_emision", "fecha", "observaciones"] },
  { key: "evidencias", label: "Evidencias", supported: false, columns: ["fecha_documento", "tipo_evidencia", "obra", "etapa", "archivo", "observaciones"] },
];

export const construccionImport = {
  title: "Importaciones de construccion",
  subtitle: "Carga empresas, factores, etapas, obras y registros usando los endpoints actuales.",
  modules,
  templates: modules,
  validationRules: {},
  previewColumns: {},
  buildPayload: null,
  buildSummary: null,
  buildRecommendations(summary) {
    if (!summary.total) return ["Carga un archivo CSV o XLSX compatible para previsualizar."];
    return ["Usa confirmar importacion cuando existan filas validas."];
  },
  emptyMessage: "No hay importaciones de construccion cargadas. Descarga una plantilla y carga datos de empresas, obras, etapas, registros o factores.",
};
