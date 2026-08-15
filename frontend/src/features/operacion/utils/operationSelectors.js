export const DOMAIN_CONFIG = {
  energia: { label: "Energía", flows: ["energia", "generacion_propia"], capability: "energia" },
  agua: { label: "Agua", flows: ["agua"], capability: "agua" },
  combustibles: { label: "Combustibles", flows: ["combustible_estacionario"], capability: "combustibles" },
  residuos: { label: "Residuos", flows: ["residuo"], capability: "residuos" },
  ruido: { label: "Ruido", flows: ["ruido"], capability: "ruido" },
  "hidrica-suelo": { label: "Hídrica y suelo", flows: ["gestion_hidrica_suelo"], capability: "gestion_hidrica_suelo" },
};

export const isResourceReady = (resource) => resource?.status === "ready";
export const resourceData = (resource, fallback) => isResourceReady(resource) ? resource.data : fallback;

export function domainRecords(records, domain) {
  const flows = DOMAIN_CONFIG[domain]?.flows || [];
  return (records || []).filter((record) => flows.includes(record.flujo));
}

export function recordMeasurements(records) {
  return records.flatMap((record) => (record.observaciones || []).map((observation) => ({ record, observation })));
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

export function applicability(context, capability) {
  const item = context?.diagnostico_obra?.aplicabilidad?.find((row) => row.clave === capability);
  return item?.estado_obra || "no_determinado";
}

export function domainState({ applicabilityState, records, ambiguous = false }) {
  if (applicabilityState === "no_aplica") return "no_aplica";
  if (["no_determinado", "pendiente"].includes(applicabilityState)) return "por_definir";
  if (ambiguous) return "requiere_revision";
  return records.length ? "con_datos" : "sin_datos";
}

export const transportMetrics = (transport) => [
  { key: "numero_viajes", label: "Viajes completados", unit: "viajes" },
  { key: "km_totales", label: "Distancia recorrida", unit: "km" },
  { key: "tonelaje_transportado", label: "Carga transportada", unit: "t" },
  { key: "toneladas_km", label: "Trabajo de transporte", unit: "t·km" },
  { key: "combustible_total", label: "Combustible consumido", unit: "L" },
  { key: "porcentaje_km_vacios", label: "Porcentaje de kilómetros vacíos", unit: "%" },
].map((definition) => ({ ...definition, value: transport?.[definition.key] ?? null }));
