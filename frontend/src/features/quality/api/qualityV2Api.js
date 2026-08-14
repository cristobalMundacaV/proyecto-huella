import { api } from "@/shared/services/api";
const base = (id) => `/organizaciones/${encodeURIComponent(id)}`;
export const getEnvironmentalSummaryV2 = async (id) => (await api.get(`${base(id)}/resumen-ambiental-v2/`)).data;
export const getObservationQuality = async (id) => (await api.get(`${base(id)}/calidad/observaciones/`)).data;
export const getDiscrepancies = async (id) => (await api.get(`${base(id)}/discrepancias/`)).data;
export const getIndicatorComparison = async (id, indicatorId) => (await api.get(`${base(id)}/indicadores/${indicatorId}/comparacion/`)).data;
