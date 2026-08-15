import { api } from "@/shared/services/api";
const base=(id)=>`/organizaciones/${encodeURIComponent(id)}`;
export const getJourneys=async(id)=>(await api.get(`${base(id)}/viajes-operacionales/`)).data;
export const createJourney=async(id,data)=>(await api.post(`${base(id)}/viajes-operacionales/`,data)).data;
export const updateJourney=async(id,journeyId,data)=>(await api.patch(`${base(id)}/viajes-operacionales/${journeyId}/`,data)).data;
export const getTransportIndicators=async(id)=>(await api.get(`${base(id)}/viajes-operacionales/indicadores/`)).data;
