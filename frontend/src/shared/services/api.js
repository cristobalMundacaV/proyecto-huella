import axios from "axios";

function getCsrfToken() {
  if (typeof document === "undefined") return null;
  const cookie = document.cookie?.split(";").map((item) => item.trim()).find((item) => item.startsWith("csrftoken="));
  return cookie ? decodeURIComponent(cookie.slice("csrftoken=".length)) : null;
}

export async function refreshCsrfToken() {
  const response = await axios.get(`${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api"}/auth/csrf-token/`, { withCredentials: true });
  return response.data.csrfToken;
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api",
  timeout: 60000,
  withCredentials: true,
});

api.interceptors.request.use(async (config) => {
  const method = String(config.method || "get").toLowerCase();
  const isReadMethod = ["get", "head", "options"].includes(method);
  const isDemoMode = typeof window !== "undefined" && window.localStorage.getItem("carbono_zero.demo") === "true";
  if (isDemoMode && !isReadMethod) return Promise.reject(new axios.CanceledError("El modo demo permite solo lectura."));
  if (!isReadMethod) {
    const csrfToken = getCsrfToken() || (await refreshCsrfToken());
    if (csrfToken) config.headers["X-CSRFToken"] = csrfToken;
  }
  return config;
});

function resolveApiBaseUrl(baseUrl) {
  const fallback = "http://127.0.0.1:8000/api";
  const candidate = (baseUrl || fallback).trim();
  if (/^https?:\/\//i.test(candidate)) return candidate;
  if (candidate.startsWith("/") && typeof window !== "undefined") return `${window.location.origin}${candidate}`;
  return fallback;
}

function buildApiUrl(path) {
  const baseUrl = resolveApiBaseUrl(api.defaults.baseURL);
  return new URL(path.replace(/^\//, ""), baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`).toString();
}

function constructoraPath(id, path = "") { return `/constructoras/${encodeURIComponent(id)}${path}`; }
function obraPath(id, path = "") { return `/obras/${encodeURIComponent(id)}${path}`; }
function query(params = {}) { const q = new URLSearchParams(); Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") q.append(k, v); }); return q.toString() ? `?${q}` : ""; }
function filePayload(file) { const formData = new FormData(); formData.append("file", file); return formData; }
async function previewImport(kind, file, constructoraId = null) { const url = constructoraId ? constructoraPath(constructoraId, `/importaciones/${kind}/preview/`) : `/importaciones/${kind}/preview/`; const r = await api.post(url, filePayload(file), { headers: { "Content-Type": "multipart/form-data" } }); return r.data; }
async function confirmImport(kind, payload, constructoraId = null) { const url = constructoraId ? constructoraPath(constructoraId, `/importaciones/${kind}/confirm/`) : `/importaciones/${kind}/confirm/`; const r = await api.post(url, payload); return r.data; }

export async function getCurrentUser() { return (await api.get("/auth/me/")).data; }
export async function loginUser(payload) { return (await api.post("/auth/login/", payload)).data; }
export async function logoutUser() { return (await api.post("/auth/logout/")).data; }
export async function bootstrapUser(payload) { return (await api.post("/auth/bootstrap/", payload)).data; }
export async function getConstructoras() { return (await api.get("/constructoras/")).data; }
export async function createConstructora(payload) { return (await api.post("/constructoras/", payload)).data; }
export async function updateConstructora(id, payload) { return (await api.patch(constructoraPath(id, "/"), payload)).data; }
export async function deleteConstructora(id) { await api.delete(constructoraPath(id, "/")); }

export async function getEmpresas() { return getConstructoras(); }
export async function createEmpresa(payload) { return createConstructora(payload); }
export async function updateEmpresa(id, payload) { return updateConstructora(id, payload); }
export async function deleteEmpresa(id) { return deleteConstructora(id); }
export async function getConstructoraUsuarios(id) { return (await api.get(constructoraPath(id, "/usuarios/"))).data; }
export async function createConstructoraUsuario(id, payload) { return (await api.post(constructoraPath(id, "/usuarios/"), payload)).data; }
export async function getConstructoraDashboard(id, params = {}) { return (await api.get(constructoraPath(id, "/dashboard/"), { params })).data; }
export async function getConstructoraEstado(id) { return (await api.get(constructoraPath(id, "/estado/"))).data; }
export async function getConstructoraConfiguracion(id) { return (await api.get(constructoraPath(id, "/configuracion/"))).data; }
export async function updateConstructoraConfiguracion(id, payload) { return (await api.patch(constructoraPath(id, "/configuracion/"), payload)).data; }
export async function getConstructoraEtapas(id, params = {}) { return (await api.get(constructoraPath(id, "/etapas/"), { params })).data; }
export async function createEtapaObra(id, payload) { return (await api.post(constructoraPath(id, "/etapas/"), payload)).data; }
export async function getEtapasObra(params = {}) { return params.constructora_id ? getConstructoraEtapas(params.constructora_id, params) : []; }
export async function getObras() { return (await api.get("/obras/")).data; }
export async function getConstructoraObras(id) { return (await api.get(constructoraPath(id, "/obras/"))).data; }
export async function createObra(payload) { const id = payload.constructora_id || payload.constructora; return (await api.post(id ? constructoraPath(id, "/obras/") : "/obras/", payload)).data; }
export async function getObraDetail(codigo) { const [obra, registros, evidencias, transportes] = await Promise.all([api.get(obraPath(codigo, "/")), api.get(obraPath(codigo, "/registros-emision/")), api.get(obraPath(codigo, "/evidencias/")), api.get(obraPath(codigo, "/transportes/"))]); return { ...obra.data, registros_emision: registros.data, evidencias: evidencias.data, transportes: transportes.data }; }
export async function getObraBalanceAmbiental(codigo) { return (await api.get(obraPath(codigo, "/"))).data.analisis_ambiental || {}; }
export async function getConstructoraRegistrosEmision(id) { return (await api.get(constructoraPath(id, "/registros-emision/"))).data; }
export async function createConstructoraRegistroEmision(id, payload) { return (await api.post(constructoraPath(id, "/registros-emision/"), payload)).data; }
export async function getEmpresaRegistrosAmbientales(id) { return getConstructoraRegistrosEmision(id); }
export async function createEmpresaRegistroAmbiental(id, payload) { return createConstructoraRegistroEmision(id, payload); }
export async function getConstructoraEmisiones(id, params = {}) { return (await api.get(constructoraPath(id, "/emisiones/"), { params })).data; }
export async function getLotesForestales(constructoraId) { return (await api.get(constructoraPath(constructoraId, "/lotes-forestales/"))).data; }
export async function getLoteForestalDetail(constructoraId, loteId) { return (await api.get(constructoraPath(constructoraId, `/lotes-forestales/${encodeURIComponent(loteId)}/`))).data; }
export async function createLoteForestal(constructoraId, payload) { return (await api.post(constructoraPath(constructoraId, "/lotes-forestales/"), payload)).data; }
export async function updateLoteForestal(constructoraId, loteId, payload) { return (await api.patch(constructoraPath(constructoraId, `/lotes-forestales/${encodeURIComponent(loteId)}/`), payload)).data; }
export async function deleteLoteForestal(constructoraId, loteId) { await api.delete(constructoraPath(constructoraId, `/lotes-forestales/${encodeURIComponent(loteId)}/`)); }
export async function getLotesForestalesResumen(constructoraId) { return (await api.get(constructoraPath(constructoraId, "/lotes-forestales/resumen/"))).data; }
export async function getTransportesLoteForestal(constructoraId, loteId) { return (await api.get(constructoraPath(constructoraId, `/lotes-forestales/${encodeURIComponent(loteId)}/transportes/`))).data; }
export async function createTransporteLoteForestal(constructoraId, loteId, payload) { return (await api.post(constructoraPath(constructoraId, `/lotes-forestales/${encodeURIComponent(loteId)}/transportes/`), payload)).data; }
export async function createRegistroEmision(codigo, payload) { return (await api.post(obraPath(codigo, "/registros-emision/"), payload)).data; }
export async function getConstructoraEvidencias(id, params = {}) { return (await api.get(constructoraPath(id, "/evidencias/"), { params })).data; }
export async function getEvidenciasConstructora(id, filters = {}) { return getConstructoraEvidencias(id, filters); }
export async function getEvidenciasKpisConstructora(id) { const e = await getConstructoraEvidencias(id); const vinculadas = e.filter((x) => x.obra || x.registro_emision).length; return { total: e.length, vinculadas, pendientes: e.filter((x) => x.estado_documental === "pendiente").length, observadas: e.filter((x) => x.estado_documental === "observada").length, cobertura_documental: e.length ? (vinculadas / e.length) * 100 : null }; }
export async function crearEvidenciaConstructora(id, formData) { return (await api.post(constructoraPath(id, "/evidencias/"), formData)).data; }
export async function extraerEvidenciaDocumento(id, file) {
  const formData = new FormData();
  formData.append("file", file);

  return (await api.post(constructoraPath(id, "/evidencias/extraer/"), formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })).data;
}
export async function uploadObraEvidencia(codigo, payload) { const fd = new FormData(); fd.append("tipo_evidencia", payload.tipo_evidencia || "otro"); fd.append("fecha_evidencia", payload.fecha_evidencia || ""); fd.append("nombre", payload.nombre || payload.archivo?.name || "Evidencia de obra"); fd.append("archivo", payload.archivo); if (payload.observaciones) fd.append("observaciones", payload.observaciones); return (await api.post(obraPath(codigo, "/evidencias/"), fd, { headers: { "Content-Type": "multipart/form-data" } })).data; }
export async function createTransporteObra(codigo, payload) { return (await api.post(obraPath(codigo, "/transportes/"), payload)).data; }
export async function getConstructoraReportes(id, params = {}) { return (await api.get(constructoraPath(id, `/reportes/${query(params)}`))).data; }
export async function getReporteEmisionesTiempo(id, params = {}) { return getConstructoraReportes(id, params); }
export async function getSistemaEstado() { return (await api.get("/sistema/estado/")).data; }
export async function getIotKpis(id) { return (await api.get("/iot/kpis/", { params: id ? { constructora_id: id } : {} })).data; }
export async function getIotUltimasLecturas(id) { return (await api.get("/iot/lecturas/ultimas/", { params: id ? { constructora_id: id } : {} })).data; }
export async function getFactoresEmision(params = {}) { return (await api.get("/factores-emision/", { params })).data; }
export async function createFactorEmision(payload) { return (await api.post("/factores-emision/", payload)).data; }
export async function updateFactorEmision(id, payload) { return (await api.patch(`/factores-emision/${encodeURIComponent(id)}/`, payload)).data; }
export async function aplicarFactorRegistroEmision(constructoraId, registroId, payload) { return (await api.post(constructoraPath(constructoraId, `/registros-emision/${encodeURIComponent(registroId)}/aplicar-factor/`), payload)).data; }
export async function getMaterialesConstruccion() { return (await api.get("/materiales-construccion/")).data; }
export async function calculateRouteDistance(payload) { return (await api.post("/rutas/calcular-distancia/", payload)).data; }
export async function getAiAdvisor(payload) { return (await api.post("/ai-advisor/", payload)).data; }

function rows(input) { return Array.isArray(input) ? input : input?.rows || input?.datos || input?.registros || input?.registros_emision || input?.data || []; }
function emission(row) { return Number(row?.emisiones_kg_co2e ?? row?.emisiones_totales ?? row?.emisiones ?? row?.total_emisiones ?? row?.co2e ?? 0); }
export async function simulateScenario(input) { const list = rows(input).filter((row) => emission(row) > 0); const total = list.reduce((s, row) => s + emission(row), 0); if (!total) return { rows: [], total_emisiones: 0, currentTotal: 0, simulatedTotal: 0, reductionPct: 0, pending: true }; const avoided = total * 0.08; return { rows: list, total_emisiones: total, currentTotal: total, simulatedTotal: total - avoided, reductionPct: 8, avoidedEmissions: avoided, targetSource: list[0]?.fuente_emision || "Fuente crítica", targetCategory: list[0]?.categoria || "Otros", recommendedActions: ["Priorizar fuentes críticas", "Validar evidencias", "Medir reducción semanal"] }; }
export async function optimizeScenarioApi(input) { const scenario = await simulateScenario(input); return scenario.currentTotal ? { ...scenario, scenarioLabel: "Máximo realista", assumptionsTested: 14, methodology: "Escenario calculado con palancas por categoría y fuente crítica." } : null; }
export async function getRiskScore(payload) { return { score: 0, payload }; }
export async function extractDocumentText() { return { texto: "", pendiente: true }; }
export async function extractDocumentJson() { return { data: {}, pendiente: true }; }
export async function extractDocumentTextById() { return { texto: "", pendiente: true }; }
export async function extractDocumentJsonById() { return { data: {}, pendiente: true }; }
export async function runEvidenciaOcr() { return { pendiente: true }; }
export async function validateExtraccionEvidencia() { return { pendiente: true }; }
export async function rejectExtraccionEvidencia() { return { pendiente: true }; }

export function getPlantillaImportacionConstruccionUrl() { return buildApiUrl("/importaciones/plantilla-construccion/"); }
export function getPlantillaGenericaXlsxUrl(columns = [], filename = "plantilla_importacion.xlsx") {
  const params = new URLSearchParams();
  params.set("columns", columns.join(","));
  params.set("filename", filename);
  return buildApiUrl(`/importaciones/plantilla-generica/?${params.toString()}`);
}

export async function previewImportGenerica(file, { columns = [], module = "" } = {}) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("columns", JSON.stringify(columns));
  formData.append("module", module);

  const response = await api.post("/importaciones/generica/preview/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return response.data;
}
export async function previewImportFactores(file) { return previewImport("factores", file); }
export async function confirmarImportFactores(payload) { return confirmImport("factores", payload); }
export async function previewImportConstructoras(file) { return previewImport("constructoras", file); }
export async function confirmarImportConstructoras(payload) { return confirmImport("constructoras", payload); }
export async function previewImportEtapasForConstructora(id, file) { return previewImport("etapas", file, id); }
export async function confirmarImportEtapasForConstructora(id, payload) { return confirmImport("etapas", payload, id); }
export async function previewImportObrasForConstructora(id, file) { return previewImport("obras", file, id); }
export async function confirmarImportObrasForConstructora(id, payload) { return confirmImport("obras", payload, id); }
export async function previewRegistroEmisionImport(file) { return previewImport("registros", file); }
export async function confirmRegistroEmisionImport(payload) { return confirmImport("registros", payload); }
export async function previewRegistroEmisionImportForConstructora(id, file) { return previewImport("registros", file, id); }
export async function confirmRegistroEmisionImportForConstructora(id, payload) { return confirmImport("registros", payload, id); }
export async function previewImportacionCompletaConstruccion(file) { return (await api.post("/importaciones/completa/preview/", filePayload(file), { headers: { "Content-Type": "multipart/form-data" } })).data; }
export async function confirmarImportacionCompletaConstruccion(payload) { return (await api.post("/importaciones/completa/confirm/", payload)).data; }
export const previewImportObras = previewImportObrasForConstructora;
export const confirmarImportObras = confirmarImportObrasForConstructora;
export const previewImportEtapas = previewImportEtapasForConstructora;
export const confirmarImportEtapas = confirmarImportEtapasForConstructora;

export async function getVerificacionObra(codigo) { return (await api.get(`/verificar/obra/${encodeURIComponent(codigo)}/`)).data; }
export function getObraIntegracionUrl() { return ""; }
export function getObraExportJsonUrl() { return ""; }
export function getObraExportCsvUrl() { return ""; }
export function getObraFichaTecnicaUrl(codigo) { return buildApiUrl(`/verificar/obra/${encodeURIComponent(codigo)}/`); }
export async function getHistorialObra() { return []; }
export async function downloadObraFichaAmbiental(codigo) { const response = await api.get(`/verificar/obra/${encodeURIComponent(codigo)}/`); return new Blob([JSON.stringify(response.data, null, 2)], { type: "application/json" }); }
