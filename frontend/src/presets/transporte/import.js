const modules = [
  { key: "flota", label: "Flota", supported: false, columns: ["patente", "tipo", "capacidad", "combustible", "anio", "observaciones"] },
  { key: "viajes", label: "Viajes", supported: false, columns: ["fecha", "patente", "conductor", "origen", "destino", "distancia_km", "litros_combustible", "carga", "cliente", "ruta", "factor_emision", "observaciones"] },
  { key: "combustible", label: "Combustible", supported: false, columns: ["fecha", "patente", "litros_combustible", "proveedor", "factura", "factor_emision", "observaciones"] },
  { key: "rutas", label: "Rutas", supported: false, columns: ["ruta", "origen", "destino", "distancia_km", "cliente", "observaciones"] },
  { key: "mantenciones", label: "Mantenciones", supported: false, columns: ["fecha", "patente", "tipo_mantencion", "km", "proveedor", "observaciones"] },
  { key: "factores", label: "Factores", supported: false, columns: ["categoria", "module", "actividad", "unidad", "factor_emision", "fuente", "anio"] },
  { key: "evidencias", label: "Evidencias", supported: false, columns: ["fecha_documento", "tipo_evidencia", "patente", "ruta", "archivo", "observaciones"] },
];

export const transporteImport = {
  title: "Importaciones logisticas",
  subtitle: "Plantillas preparadas para flota, viajes, combustible, rutas y mantenciones.",
  modules,
  templates: modules,
  validationRules: {},
  previewColumns: {},
  buildPayload: null,
  buildSummary: null,
  buildRecommendations() {
    return ["La importacion de transporte esta preparada. La conexion backend masiva queda para una fase posterior."];
  },
  emptyMessage: "No hay importaciones de flota o viajes cargadas. Descarga una plantilla de combustible, rutas o viajes para comenzar.",
};
