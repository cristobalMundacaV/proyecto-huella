const normalizeInsightText = (value = "") =>
  String(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();

const categoryOrder = [
  "Materia prima",
  "Produccion",
  "Secado",
  "Energia",
  "Transporte",
  "Residuos",
  "Subproductos",
  "Otros",
];

const categoryDisplayNames = {
  Materiales: "Materia prima",
  "Materia prima": "Materia prima",
  Produccion: "Produccion",
  "Procesos externos": "Produccion",
  Secado: "Secado",
  Energia: "Energia",
  Transporte: "Transporte",
  Residuos: "Residuos",
  Subproductos: "Subproductos",
  Otros: "Otros",
};

const categoryIntelligence = {
  "Materia prima": {
    priority: 1,
    relevanceLabel: "Trazabilidad de abastecimiento",
    diagnosis:
      "El ingreso de trozas define la linea base de volumen, humedad, especie y origen. Sin esta trazabilidad, los indicadores productivos y ambientales quedan incompletos.",
    mainAction: "Estandarizar lotes de recepcion con proveedor, predio, especie, volumen y humedad.",
    actions: [
      "Registrar lote y guia de despacho en cada ingreso.",
      "Comparar volumen recibido contra volumen procesado por especie.",
      "Separar proveedores recurrentes para detectar brechas de trazabilidad.",
    ],
    metrics: ["m3 recibidos", "proveedores", "humedad promedio", "lotes sin factor"],
    evidence: ["Guias de despacho", "Ticket de romana", "Registro de recepcion"],
    nextStep: "Completar recepcion de trozas antes de cargar produccion para mantener rendimiento confiable.",
  },
  Produccion: {
    priority: 2,
    relevanceLabel: "Rendimiento del proceso de aserrio",
    diagnosis:
      "La conversion de troza a producto terminado concentra rendimiento, mermas y eficiencia operacional por linea o turno.",
    mainAction: "Medir entrada, salida y rendimiento por lote productivo.",
    actions: [
      "Vincular cada lote producido con su recepcion de origen.",
      "Separar rendimiento por linea de produccion y turno.",
      "Revisar lotes con baja conversion antes de consolidar reportes.",
    ],
    metrics: ["m3 procesados", "rendimiento promedio", "lotes procesados"],
    evidence: ["Parte de produccion", "Planilla de turno", "Control de inventario"],
    nextStep: "Cruzar rendimiento de produccion con humedad y especie para detectar causas operativas.",
  },
  Secado: {
    priority: 3,
    relevanceLabel: "Eficiencia termica y calidad",
    diagnosis:
      "El secado conecta energia, tiempo de camara y humedad final. Es un punto clave para eficiencia y calidad del producto.",
    mainAction: "Registrar camara, horas, energia, combustible y humedad final por ciclo.",
    actions: [
      "Comparar kWh por m3 secado entre camaras.",
      "Detectar ciclos con exceso de horas o humedad final fuera de rango.",
      "Separar combustible usado para asociar factor de emision correcto.",
    ],
    metrics: ["m3 secados", "kWh registrados", "horas de secado", "humedad final"],
    evidence: ["Bitacora de camara", "Lectura de medidor", "Registro de humedad"],
    nextStep: "Priorizar ciclos con mayor consumo por m3 y revisar setpoints de camara.",
  },
  Energia: {
    priority: 4,
    relevanceLabel: "Consumo energetico operacional",
    diagnosis:
      "La energia debe separarse por area, turno y medidor para evitar promedios que oculten consumos criticos.",
    mainAction: "Separar consumos electricos y termicos por area operacional.",
    actions: [
      "Registrar medidor y turno en cada consumo.",
      "Diferenciar energia electrica, termica y combustibles.",
      "Construir intensidad energetica por m3 procesado.",
    ],
    metrics: ["kWh totales", "areas registradas", "consumo por turno"],
    evidence: ["Factura electrica", "Lectura de medidor", "Parte de consumo"],
    nextStep: "Consolidar consumos por area para estimar intensidad energetica del aserradero.",
  },
  Transporte: {
    priority: 5,
    relevanceLabel: "Logistica forestal",
    diagnosis:
      "El transporte forestal requiere distancia, carga y combustible para evaluar viajes, rutas y emisiones asociadas.",
    mainAction: "Registrar km, litros diesel, carga y patente por viaje.",
    actions: [
      "Separar viajes de abastecimiento y despacho.",
      "Comparar litros por km y m3 transportado.",
      "Detectar rutas repetidas con baja ocupacion de carga.",
    ],
    metrics: ["km recorridos", "litros diesel", "m3 transportados", "kg CO2e"],
    evidence: ["Hoja de ruta", "Carga de combustible", "Guia de transporte"],
    nextStep: "Priorizar viajes con alto diesel por m3 transportado.",
  },
  Residuos: {
    priority: 6,
    relevanceLabel: "Trazabilidad de residuos",
    diagnosis:
      "Los residuos y subproductos deben diferenciar destino, cantidad, gestor y valorizacion para cerrar balance material.",
    mainAction: "Clasificar cada residuo por tipo, destino y condicion de valorizacion.",
    actions: [
      "Separar aserrin, corteza, despuntes y rechazo no valorizado.",
      "Registrar gestor o destino final.",
      "Medir porcentaje valorizado por periodo.",
    ],
    metrics: ["cantidad total", "% valorizado", "tipos de residuo", "gestores"],
    evidence: ["Guia de retiro", "Comprobante de gestor", "Registro de valorizacion"],
    nextStep: "Aumentar valorizacion documentada y cerrar residuos sin destino trazable.",
  },
  Subproductos: {
    priority: 7,
    relevanceLabel: "Valorizacion material",
    diagnosis:
      "Los subproductos permiten transformar salidas del proceso en recuperacion material y menor residuo final.",
    mainAction: "Registrar subproductos valorizados con cantidad, unidad y destino.",
    actions: [
      "Separar subproducto de residuo no valorizado.",
      "Cuantificar destino comercial o energetico.",
      "Mantener respaldo documental por retiro o venta.",
    ],
    metrics: ["cantidad valorizada", "destinos", "gestores", "tipos de subproducto"],
    evidence: ["Factura de venta", "Guia de retiro", "Contrato de valorizacion"],
    nextStep: "Documentar los subproductos de mayor volumen para mejorar reporte ambiental.",
  },
  Otros: {
    priority: 8,
    relevanceLabel: "Clasificacion pendiente",
    diagnosis:
      "Existen registros que requieren clasificacion operacional para aportar al analisis del preset.",
    mainAction: "Revisar categoria, fuente y metadata operacional.",
    actions: [
      "Completar modulo forestal correspondiente.",
      "Asignar factor de emision si existe calculo pendiente.",
      "Adjuntar evidencia minima del registro.",
    ],
    metrics: ["registros", "fuentes", "factores faltantes"],
    evidence: ["Registro operativo", "Documento de respaldo"],
    nextStep: "Reclasificar registros genericos hacia el modulo operativo correcto.",
  },
};

const reductionSteps = [
  "Completar recepcion de trozas con lote, especie, volumen y origen.",
  "Medir rendimiento por lote entre entrada y salida de produccion.",
  "Separar consumos energeticos de secado y produccion por area.",
  "Priorizar viajes forestales con alto consumo por m3 transportado.",
  "Aumentar valorizacion documentada de residuos y subproductos.",
];

function resolveCategoryLabel(category, source = "", metadata = {}) {
  if (metadata?.aserradero_category) return metadata.aserradero_category;
  const normalizedSource = normalizeInsightText(source);
  if (normalizedSource.includes("troza") || normalizedSource.includes("recepcion")) return "Materia prima";
  if (normalizedSource.includes("aserrio") || normalizedSource.includes("produccion")) return "Produccion";
  if (normalizedSource.includes("secado")) return "Secado";
  if (normalizedSource.includes("energia") || normalizedSource.includes("kwh")) return "Energia";
  if (normalizedSource.includes("transporte") || normalizedSource.includes("viaje")) return "Transporte";
  if (normalizedSource.includes("residuo") || normalizedSource.includes("subproducto")) return "Residuos";
  return categoryDisplayNames[category] || category || "Otros";
}

const sawmillIntelligence = {
  categoryOrder,
  categoryDisplayNames,
  categoryIntelligence,
  stageOrder: ["Recepcion", "Aserrio", "Secado", "Clasificacion", "Despacho"],
  stageDisplayNames: {
    recepcion: "Recepcion",
    aserrio: "Aserrio",
    secado: "Secado",
    clasificacion: "Clasificacion",
    despacho: "Despacho",
  },
  stageIntelligence: {},
  reductionSteps,
  resolveCategoryLabel,
};

export { sawmillIntelligence };
