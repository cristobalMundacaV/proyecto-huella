const ASERRADERO_PRESET_KEY = "aserradero";

const backendCategoryByAserraderoCategory = {
  "Materia prima": "Materiales",
  Produccion: "Procesos externos",
  Secado: "Energia",
  Energia: "Energia",
  Transporte: "Transporte",
  Residuos: "Residuos",
  Subproductos: "Residuos",
  Otros: "Otros",
};

const aserraderoModules = {
  recepcion_trozas: {
    key: "recepcion_trozas",
    title: "Recepcion de trozas",
    description:
      "Registra el ingreso de materia prima forestal, su trazabilidad, volumen, humedad y proveedor antes de iniciar el proceso productivo.",
    category: "Materia prima",
    defaultSource: "Recepcion de trozas",
    defaultUnit: "m3",
    defaultFactor: 0,
    metadataFields: [
      { key: "lote", label: "Lote" },
      { key: "especie", label: "Especie" },
      { key: "proveedor_madera", label: "Proveedor madera" },
      { key: "volumen_m3", label: "Volumen m3", type: "number" },
      { key: "humedad_pct", label: "Humedad %", type: "number" },
      { key: "origen_predio", label: "Origen predio" },
      { key: "guia_despacho", label: "Guia despacho" },
      { key: "fecha_recepcion", label: "Fecha recepcion", type: "date" },
    ],
  },
  produccion: {
    key: "produccion",
    title: "Produccion",
    description:
      "Controla el proceso de aserrio, rendimiento por lote, volumen de entrada y salida, turno, linea y responsable operativo.",
    category: "Produccion",
    defaultSource: "Proceso de aserrio",
    defaultUnit: "m3 procesados",
    defaultFactor: 0,
    metadataFields: [
      { key: "lote", label: "Lote" },
      { key: "especie", label: "Especie" },
      { key: "volumen_entrada_m3", label: "Volumen entrada m3", type: "number" },
      { key: "volumen_salida_m3", label: "Volumen salida m3", type: "number" },
      { key: "rendimiento_pct", label: "Rendimiento %", type: "number" },
      { key: "turno", label: "Turno" },
      { key: "linea_produccion", label: "Linea produccion" },
      { key: "operador", label: "Operador" },
    ],
  },
  secado: {
    key: "secado",
    title: "Secado",
    description:
      "Registra ciclos de secado, energia, combustible, horas y humedad inicial/final para conectar eficiencia operativa con impacto ambiental.",
    category: "Secado",
    defaultSource: "Secado de madera",
    defaultUnit: "kWh",
    defaultFactor: 0,
    metadataFields: [
      { key: "lote", label: "Lote" },
      { key: "camara_secado", label: "Camara secado" },
      { key: "volumen_secado_m3", label: "Volumen secado m3", type: "number" },
      { key: "humedad_inicial_pct", label: "Humedad inicial %", type: "number" },
      { key: "humedad_final_pct", label: "Humedad final %", type: "number" },
      { key: "horas_secado", label: "Horas secado", type: "number" },
      { key: "energia_kwh", label: "Energia kWh", type: "number" },
      { key: "combustible_usado", label: "Combustible usado" },
    ],
  },
  energia: {
    key: "energia",
    title: "Energia",
    description:
      "Separa consumos energeticos por area, turno, tipo de energia y medidor para construir indicadores de eficiencia del aserradero.",
    category: "Energia",
    defaultSource: "Consumo energetico aserradero",
    defaultUnit: "kWh",
    defaultFactor: 0,
    metadataFields: [
      { key: "area", label: "Area" },
      { key: "tipo_energia", label: "Tipo energia" },
      { key: "consumo_kwh", label: "Consumo kWh", type: "number" },
      { key: "turno", label: "Turno" },
      { key: "medidor", label: "Medidor" },
      { key: "observacion_operativa", label: "Observacion operativa" },
    ],
  },
  transporte_forestal: {
    key: "transporte_forestal",
    title: "Transporte forestal",
    description:
      "Registra viajes forestales, distancia, combustible, carga transportada y trazabilidad logistica entre origen y destino.",
    category: "Transporte",
    defaultSource: "Transporte forestal",
    defaultUnit: "litros diesel",
    defaultFactor: 0,
    metadataFields: [
      { key: "patente", label: "Patente" },
      { key: "conductor", label: "Conductor" },
      { key: "origen", label: "Origen" },
      { key: "destino", label: "Destino" },
      { key: "distancia_km", label: "Distancia km", type: "number" },
      { key: "litros_diesel", label: "Litros diesel", type: "number" },
      { key: "carga_m3", label: "Carga m3", type: "number" },
      { key: "viaje_id", label: "Viaje ID" },
    ],
  },
  residuos_subproductos: {
    key: "residuos_subproductos",
    title: "Residuos / Subproductos",
    description:
      "Ordena residuos, subproductos, destinos, valorizacion y gestores para cerrar trazabilidad material del proceso forestal.",
    category: "Residuos",
    defaultSource: "Residuos y subproductos de madera",
    defaultUnit: "kg",
    defaultFactor: 0,
    metadataFields: [
      { key: "tipo_residuo", label: "Tipo residuo" },
      { key: "destino", label: "Destino" },
      { key: "cantidad", label: "Cantidad", type: "number" },
      { key: "unidad_residuo", label: "Unidad residuo" },
      { key: "valorizado", label: "Valorizado" },
      { key: "gestor", label: "Gestor" },
      { key: "observacion", label: "Observacion" },
    ],
  },
};

function getBackendCategoryForAserradero(category) {
  return backendCategoryByAserraderoCategory[category] || "Otros";
}

function getAserraderoModuleConfig(moduleKey) {
  return aserraderoModules[moduleKey] || null;
}

export {
  ASERRADERO_PRESET_KEY,
  aserraderoModules,
  getAserraderoModuleConfig,
  getBackendCategoryForAserradero,
};
