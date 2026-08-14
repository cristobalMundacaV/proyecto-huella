import { api } from "@/shared/services/api";
const base=(id)=>`/organizaciones/${encodeURIComponent(id)}`;
export const getEligibility=async(id,activityId)=>(await api.get(`${base(id)}/actividades-operacionales/${activityId}/elegibilidad/`)).data;
export const calculateImpact=async(id,activityId)=>(await api.post(`${base(id)}/actividades-operacionales/${activityId}/calcular/`)).data;
export const getCalculations=async(id,activityId)=>(await api.get(`${base(id)}/actividades-operacionales/${activityId}/calculos/`)).data;
export const getMethodologies=async(id)=>(await api.get(`${base(id)}/metodologias/`)).data;
