const backendCategoryMap = {
  "Materia prima": "Materiales",
  Produccion: "Procesos externos",
  Secado: "Energia",
  Energia: "Energia",
  Transporte: "Transporte",
  Residuos: "Residuos",
};

const modules = [
  {
    key: "recepcion_trozas",
    label: "Recepcion de trozas",
    supported: true,
    columns: ["fecha_recepcion", "lote", "especie", "proveedor_madera", "origen_predio", "guia_despacho", "volumen_m3", "humedad_pct", "cantidad", "unidad", "factor_emision", "observaciones"],
    category: "Materia prima",
    source: "Recepcion de trozas",
    dateField: "fecha_recepcion",
  },
  {
    key: "produccion",
    label: "Produccion",
    supported: true,
    columns: ["fecha", "lote", "especie", "volumen_entrada_m3", "volumen_salida_m3", "rendimiento_pct", "turno", "linea_produccion", "operador", "cantidad", "unidad", "factor_emision", "observaciones"],
    category: "Produccion",
    source: "Proceso de aserrio",
  },
  {
    key: "secado",
    label: "Secado",
    supported: true,
    columns: ["fecha", "lote", "camara_secado", "volumen_secado_m3", "humedad_inicial_pct", "humedad_final_pct", "horas_secado", "energia_kwh", "combustible_usado", "cantidad", "unidad", "factor_emision", "observaciones"],
    category: "Secado",
    source: "Secado de madera",
  },
  {
    key: "energia",
    label: "Energia",
    supported: true,
    columns: ["fecha", "area", "tipo_energia", "consumo_kwh", "turno", "medidor", "cantidad", "unidad", "factor_emision", "observacion_operativa"],
    category: "Energia",
    source: "Consumo energetico aserradero",
  },
  {
    key: "transporte_forestal",
    label: "Transporte forestal",
    supported: true,
    columns: ["fecha", "patente", "conductor", "origen", "destino", "distancia_km", "litros_diesel", "carga_m3", "viaje_id", "cantidad", "unidad", "factor_emision", "observaciones"],
    category: "Transporte",
    source: "Transporte forestal",
  },
  {
    key: "lotes_forestales",
    label: "Lotes forestales",
    supported: false,
    columns: ["fecha", "lote_id", "especie", "volumen_m3", "origen", "destino", "tipo_producto", "densidad_kg_m3", "porcentaje_carbono", "estado", "observaciones"],
    category: "Materia prima",
    source: "Lote forestal",
  },
  {
    key: "residuos_subproductos",
    label: "Residuos / Subproductos",
    supported: true,
    columns: ["fecha", "tipo_residuo", "destino", "cantidad", "unidad_residuo", "valorizado", "gestor", "factor_emision", "observacion"],
    category: "Residuos",
    source: "Residuos y subproductos de madera",
  },
  { key: "factores", label: "Factores de emision", supported: false, columns: ["categoria", "module", "actividad", "unidad", "factor_emision", "fuente", "anio"] },
  { key: "evidencias", label: "Evidencias", supported: false, columns: ["fecha_documento", "tipo_evidencia", "module", "lote", "archivo", "observaciones"] },
];

function buildPayload(data, { module, rowNumber }) {
  const config = modules.find((item) => item.key === module);
  const date = data.fecha || data[config.dateField] || "";
  const unidad = data.unidad || data.unidad_residuo || "unidad";
  const operationalAmount =
    data.cantidad ||
    data.consumo_kwh ||
    data.energia_kwh ||
    data.volumen_m3 ||
    data.volumen_entrada_m3 ||
    data.volumen_secado_m3 ||
    data.distancia_km ||
    data.litros_diesel ||
    data.carga_m3 ||
    0;
  return {
    categoria: backendCategoryMap[config.category] || "Otros",
    fuente_emision: config.source,
    cantidad: Number(operationalAmount),
    unidad,
    factor_emision: Number(data.factor_emision || 0),
    fecha: date || null,
    proveedor: data.proveedor_madera || data.proveedor || "",
    origen_transporte: data.origen || "",
    destino_transporte: data.destino || "",
    distancia_km: data.distancia_km || null,
    observaciones: data.observaciones || data.observacion || data.observacion_operativa || "",
    metadata: {
      preset: "forestal",
      module,
      imported_from: "preset_import",
      original_row: rowNumber,
      aserradero_category: config.category,
      ...data,
    },
  };
}

export const aserraderoImport = {
  title: "Importaciones forestales",
  subtitle: "Carga datos masivos de recepcion, produccion, secado, energia, transporte forestal y residuos.",
  modules,
  templates: modules,
  validationRules: {},
  previewColumns: {},
  buildPayload,
  buildSummary: null,
  buildRecommendations(summary) {
    if (!summary.total) return ["Descarga una plantilla forestal para comenzar."];
    if (summary.factores_faltantes) return ["Hay filas sin factor de emision. Se importaran como operacion pendiente de cierre ambiental."];
    return ["Las filas validas estan listas para crear registros operativos del aserradero."];
  },
  emptyMessage: "No hay importaciones forestales cargadas. Descarga una plantilla de recepcion de trozas, produccion, secado, energia, transporte forestal o residuos para cargar datos masivos de operacion.",
};
