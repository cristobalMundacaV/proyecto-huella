import { api } from "@/shared/services/api";

const root = (organizationId) => `/organizaciones/${encodeURIComponent(organizationId)}/problematicas`;
const options = (workId) => workId ? { params: { obra: workId } } : {};
const detail = (organizationId, problemId, suffix = "") => `${root(organizationId)}/${encodeURIComponent(problemId)}/${suffix}`;

export const listProblems = async (organizationId, workId) => (await api.get(`${root(organizationId)}/`, options(workId))).data;
export const createProblem = async (organizationId, payload) => (await api.post(`${root(organizationId)}/`, payload)).data;
export const getProblem = async (organizationId, problemId, workId) => (await api.get(detail(organizationId, problemId), options(workId))).data;
export const getProblemScope = async (organizationId, problemId, workId) => (await api.get(detail(organizationId, problemId, "alcance/"), options(workId))).data;
export const getProblemIndicators = async (organizationId, problemId, workId) => (await api.get(detail(organizationId, problemId, "indicadores/"), options(workId))).data;
export const getProblemActions = async (organizationId, problemId, workId) => (await api.get(detail(organizationId, problemId, "acciones/"), options(workId))).data;
export const createProblemAction = async (organizationId, problemId, payload, workId) => (await api.post(detail(organizationId, problemId, "acciones/"), payload, options(workId))).data;
export const selectProblemAction = async (organizationId, problemId, actionId, workId) => (await api.post(detail(organizationId, problemId, `acciones/${actionId}/seleccionar/`), {}, options(workId))).data;
export const startProblemAction = async (organizationId, problemId, actionId, workId) => (await api.post(detail(organizationId, problemId, `acciones/${actionId}/iniciar/`), { confirmado: true }, options(workId))).data;
export const implementProblemAction = async (organizationId, problemId, actionId, workId) => (await api.post(detail(organizationId, problemId, `acciones/${actionId}/implementar/`), {}, options(workId))).data;
export const getMeasurements = async (organizationId, problemId, workId) => (await api.get(detail(organizationId, problemId, "seguimientos/"), options(workId))).data;
export const createMeasurement = async (organizationId, problemId, payload, workId) => (await api.post(detail(organizationId, problemId, "seguimientos/"), payload, options(workId))).data;
export const measureFromEngine = async (organizationId, problemId, workId) => (await api.post(detail(organizationId, problemId, "seguimientos/motor/"), {}, options(workId))).data;
export const evaluateProblem = async (organizationId, problemId, workId) => (await api.post(detail(organizationId, problemId, "evaluar/"), {}, options(workId))).data;
export const getBaseSnapshot = async (organizationId, problemId, workId) => (await api.get(detail(organizationId, problemId, "snapshot-base/"), options(workId))).data;
export const getCycles = async (organizationId, problemId, workId) => (await api.get(detail(organizationId, problemId, "ciclos/"), options(workId))).data;
export const reevaluateProblem = async (organizationId, problemId, actionId, workId) => (await api.post(detail(organizationId, problemId, "reevaluar/"), { accion: actionId }, options(workId))).data;
export const escalateProblem = async (organizationId, problemId, reason, workId) => (await api.post(detail(organizationId, problemId, "escalar/"), { motivo: reason }, options(workId))).data;
export const getHistory = async (organizationId, problemId, workId) => (await api.get(detail(organizationId, problemId, "historial/"), options(workId))).data;
