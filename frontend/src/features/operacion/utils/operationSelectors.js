export const DOMAIN_CONFIG = {
  energia: {
    label: "Energía",
    flows: ["energia", "generacion_propia"],
    capability: "energia",
    question: "¿Cuánta energía se está utilizando y cuándo?",
  },
  agua: {
    label: "Agua",
    flows: ["agua"],
    capability: "agua",
    question: "¿Qué consumo o registro hídrico existe?",
  },
  combustibles: {
    label: "Combustibles",
    flows: ["combustible", "combustible_movil", "combustible_estacionario"],
    capability: "combustibles",
    question: "¿Qué combustible se está utilizando?",
  },
  residuos: {
    label: "Residuos",
    flows: ["residuo"],
    capabilities: ["residuos_no_peligrosos", "residuos_peligrosos"],
    question: "¿Qué residuos se están registrando?",
  },
  ruido: {
    label: "Ruido",
    flows: ["ruido"],
    capability: "ruido",
    question: "¿Qué mediciones acústicas se están registrando?",
  },
  "emisiones-atmosfericas": {
    label: "Emisiones atmosféricas",
    flows: ["emisiones_atmosfericas"],
    capability: "emisiones_atmosfericas",
    question: "¿Qué emisiones atmosféricas se están registrando?",
  },
  suelo: {
    label: "Suelo",
    flows: ["suelo"],
    capability: "suelo",
    question: "¿Qué condiciones o afectaciones del suelo se están registrando?",
  },
};

export const DOMAIN_ACTIVITY_TYPES = {
  energia: ["consumo_energia", "generacion_energia"],
  agua: ["consumo_agua"],
  combustibles: ["consumo_combustible", "consumo_combustible_estacionario"],
  transporte: ["transporte"],
  materiales: ["movimiento_material"],
  residuos: ["gestion_residuo"],
  ruido: ["monitoreo_ruido"],
  "emisiones-atmosfericas": ["monitoreo_emisiones_atmosfericas"],
  suelo: ["gestion_suelo"],
  "hidrica-suelo": ["gestion_hidrica_suelo"],
};

export function activityBelongsToDomain(activity, domain) {
  return (DOMAIN_ACTIVITY_TYPES[domain] || []).includes(activity?.tipo);
}

export function explicitDomainActivities(activities, domain) {
  const seen = new Set();
  return (activities || [])
    .filter((activity) => activity?.id && activityBelongsToDomain(activity, domain))
    .filter((activity) => {
      if (seen.has(activity.id)) return false;
      seen.add(activity.id);
      return true;
    });
}

export function domainActivities(records, domain) {
  return explicitDomainActivities(
    (records || []).map((record) => record.actividad_detalle),
    domain,
  );
}

const statePresentation = {
  con_datos: {
    label: "Capturado",
    tone: "info",
    description: "Hay actividad registrada con trazabilidad disponible.",
  },
  sin_datos: {
    label: "Incompleto",
    tone: "warning",
    description: "Este ámbito todavía no tiene información registrada.",
  },
  no_aplica: {
    label: "No aplica",
    tone: "neutral",
    description: "No aplica a esta unidad.",
  },
  por_definir: {
    label: "Requiere revisión",
    tone: "warning",
    description: "La aplicabilidad aún debe ser confirmada por una persona.",
  },
  requiere_revision: {
    label: "Requiere revisión",
    tone: "warning",
    description: "Hay información que requiere revisión.",
  },
  error: {
    label: "No disponible",
    tone: "danger",
    description: "La información no está disponible.",
  },
};

export const isResourceReady = (resource) => resource?.status === "ready";
export const resourceData = (resource, fallback) => isResourceReady(resource) ? resource.data : fallback;

export function domainRecords(records, domain) {
  const flows = DOMAIN_CONFIG[domain]?.flows || [];
  return (records || []).filter((record) => flows.includes(record.flujo));
}

export function recordMeasurements(records) {
  return (records || []).flatMap((record) => (record.observaciones || []).map((observation) => ({ record, observation })));
}

export function domainMetrics(indicators, domain) {
  const flows = DOMAIN_CONFIG[domain]?.flows || [];
  return (indicators?.flujos || []).filter((metric) => flows.includes(metric.flujo));
}

export function additiveMetrics(indicators, domain) {
  return domainMetrics(indicators, domain).filter((metric) => metric.estrategia_agregacion === "suma");
}

export function nonAdditiveMetrics(indicators, domain) {
  return domainMetrics(indicators, domain).filter((metric) => metric.estrategia_agregacion === "serie_no_aditiva");
}

export function primaryAdditiveMetric(indicators, domain) {
  return additiveMetrics(indicators, domain)
    .filter((metric) => metric.total !== null && metric.total !== undefined && metric.unidad)
    .toSorted((left, right) => `${left.concepto}:${left.unidad}`.localeCompare(`${right.concepto}:${right.unidad}`))[0] || null;
}

export function applicability(context, capability) {
  const capabilities = Array.isArray(capability) ? capability : [capability];
  const states = capabilities.map((key) =>
    context?.diagnostico_obra?.aplicabilidad?.find((row) => row.clave === key)?.estado_obra || "no_determinado"
  );
  if (states.includes("aplica")) return "aplica";
  if (states.every((state) => state === "no_aplica")) return "no_aplica";
  return "pendiente";
}

export function wasteClassification(record) {
  const classification = record?.clasificacion_residuo;
  if (["no_peligroso", "peligroso"].includes(classification)) {
    return classification;
  }
  const legacyClassification = record?.tipo_recurso;
  return ["no_peligroso", "peligroso"].includes(legacyClassification)
    ? legacyClassification
    : null;
}

export function compatibleDomainTotals(indicators, domain) {
  const concepts = new Set(domainMetrics(indicators, domain).map((metric) => metric.concepto));
  return (indicators?.totales_compatibles || []).filter((metric) => concepts.has(metric.concepto));
}

export function calculationMethodologyPresentation(eligibility) {
  if (eligibility?.metodologia_seleccionada) {
    return { methodology: eligibility.metodologia_seleccionada, label: null };
  }
  if (eligibility?.requiere_revision_metodologica) {
    return { methodology: null, label: "Revisión metodológica requerida" };
  }
  if (eligibility?.metodologia_candidata) {
    return { methodology: eligibility.metodologia_candidata, label: null };
  }
  return { methodology: null, label: "Sin metodología" };
}

export const isCalculationSelectable = (eligibility) =>
  Boolean(eligibility?.metodologia_seleccionada);

export function domainState({ applicabilityState, records = [], ambiguous = false, available = true }) {
  if (!available) return "error";
  if (applicabilityState === "no_aplica") return "no_aplica";
  if (ambiguous) return "requiere_revision";
  if (records.length) return "con_datos";
  if (["no_determinado", "pendiente"].includes(applicabilityState)) return "por_definir";
  return "sin_datos";
}

export function domainStateInfo(state) {
  return statePresentation[state] || statePresentation.por_definir;
}

export function latestRecord(records, field) {
  return (records || [])
    .filter((row) => row?.[field])
    .toSorted((left, right) => String(right[field]).localeCompare(String(left[field])))[0] || null;
}

export function latestMeasurement(records) {
  return recordMeasurements(records)
    .filter(({ observation }) => observation?.timestamp_observacion)
    .toSorted((left, right) => String(right.observation.timestamp_observacion).localeCompare(String(left.observation.timestamp_observacion)))[0] || null;
}

export const transportMetrics = (transport) => [
  { key: "numero_viajes", label: "Viajes completados", unit: "viajes" },
  { key: "km_totales", label: "Distancia recorrida", unit: "km" },
  { key: "tonelaje_transportado", label: "Carga transportada", unit: "t" },
  { key: "toneladas_km", label: "Trabajo de transporte", unit: "t·km" },
  { key: "combustible_total", label: "Combustible consumido", unit: "L" },
  { key: "porcentaje_km_vacios", label: "Porcentaje de kilómetros vacíos", unit: "%" },
].map((definition) => ({ ...definition, value: transport?.[definition.key] ?? null }));
