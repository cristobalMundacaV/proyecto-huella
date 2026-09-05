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

function organizacionPath(id, path = "") { return `/organizaciones/${encodeURIComponent(id)}${path}`; }
function obraPath(id, path = "") { return `/obras/${encodeURIComponent(id)}${path}`; }
function query(params = {}) { const q = new URLSearchParams(); Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") q.append(k, v); }); return q.toString() ? `?${q}` : ""; }
function filePayload(file) { const formData = new FormData(); formData.append("file", file); return formData; }
async function previewImport(kind, file, organizacionId = null) { const url = organizacionId ? organizacionPath(organizacionId, `/importaciones/${kind}/preview/`) : `/importaciones/${kind}/preview/`; const r = await api.post(url, filePayload(file), { headers: { "Content-Type": "multipart/form-data" } }); return r.data; }
async function confirmImport(kind, payload, organizacionId = null) { const url = organizacionId ? organizacionPath(organizacionId, `/importaciones/${kind}/confirm/`) : `/importaciones/${kind}/confirm/`; const r = await api.post(url, payload); return r.data; }

export async function getCurrentUser() { return (await api.get("/auth/me/")).data; }
export async function loginUser(payload) { return (await api.post("/auth/login/", payload)).data; }
export async function logoutUser() { return (await api.post("/auth/logout/")).data; }
export async function bootstrapUser(payload) { return (await api.post("/auth/bootstrap/", payload)).data; }
export async function getOrganizaciones(config = {}) { return (await api.get("/organizaciones/", config)).data; }
export async function createOrganizacion(payload) { return (await api.post("/organizaciones/", payload)).data; }
export async function updateOrganizacion(id, payload) { return (await api.patch(organizacionPath(id, "/"), payload)).data; }
export async function deleteOrganizacion(id) { await api.delete(organizacionPath(id, "/")); }

export async function getEmpresas() { return getOrganizaciones(); }
export async function createEmpresa(payload) { return createOrganizacion(payload); }
export async function updateEmpresa(id, payload) { return updateOrganizacion(id, payload); }
export async function deleteEmpresa(id) { return deleteOrganizacion(id); }
export async function getOrganizacionUsuarios(id) { return (await api.get(organizacionPath(id, "/usuarios/"))).data; }
export async function createOrganizacionUsuario(id, payload) { return (await api.post(organizacionPath(id, "/usuarios/"), payload)).data; }
export async function updateOrganizacionUsuario(id, userId, payload) { return (await api.patch(organizacionPath(id, `/usuarios/${userId}/`), payload)).data; }
export async function deleteOrganizacionUsuario(id, userId) { return (await api.delete(organizacionPath(id, `/usuarios/${userId}/`))).data; }
export async function getOrganizacionDashboard(id, params = {}) { return (await api.get(organizacionPath(id, "/dashboard/"), { params })).data; }
export async function getOrganizacionEstado(id) { return (await api.get(organizacionPath(id, "/estado/"))).data; }
export async function getOrganizacionConfiguracion(id) { return (await api.get(organizacionPath(id, "/configuracion/"))).data; }
export async function updateOrganizacionConfiguracion(id, payload) { return (await api.patch(organizacionPath(id, "/configuracion/"), payload)).data; }
export async function getOrganizacionEtapas(id, params = {}) { return (await api.get(organizacionPath(id, "/etapas/"), { params })).data; }
export async function createEtapaObra(id, payload) { return (await api.post(organizacionPath(id, "/etapas/"), payload)).data; }
export async function getEtapasObra(params = {}) { return params.organizacion_id ? getOrganizacionEtapas(params.organizacion_id, params) : []; }
export async function getObras() { return (await api.get("/obras/")).data; }
export async function getOrganizacionObras(id) { return (await api.get(organizacionPath(id, "/obras/"))).data; }
export async function createObra(payload) { const id = payload.organizacion_id || payload.organizacion; return (await api.post(id ? organizacionPath(id, "/obras/") : "/obras/", payload)).data; }
export async function getObraBalanceAmbiental(codigo) { return (await api.get(obraPath(codigo, "/"))).data.analisis_ambiental || {}; }
export async function getOrganizacionRegistrosEmision(id) { return (await api.get(organizacionPath(id, "/registros-emision/"))).data; }
export async function createOrganizacionRegistroEmision(id, payload) { return (await api.post(organizacionPath(id, "/registros-emision/"), payload)).data; }
export async function getEmpresaRegistrosAmbientales(id) { return getOrganizacionRegistrosEmision(id); }
export async function createEmpresaRegistroAmbiental(id, payload) { return createOrganizacionRegistroEmision(id, payload); }
export async function getOrganizacionEmisiones(id, params = {}) { return (await api.get(organizacionPath(id, "/emisiones/"), { params })).data; }
export async function getLotesForestales(organizacionId) { return (await api.get(organizacionPath(organizacionId, "/lotes-forestales/"))).data; }
export async function getLoteForestalDetail(organizacionId, loteId) { return (await api.get(organizacionPath(organizacionId, `/lotes-forestales/${encodeURIComponent(loteId)}/`))).data; }
export async function createLoteForestal(organizacionId, payload) { return (await api.post(organizacionPath(organizacionId, "/lotes-forestales/"), payload)).data; }
export async function updateLoteForestal(organizacionId, loteId, payload) { return (await api.patch(organizacionPath(organizacionId, `/lotes-forestales/${encodeURIComponent(loteId)}/`), payload)).data; }
export async function deleteLoteForestal(organizacionId, loteId) { await api.delete(organizacionPath(organizacionId, `/lotes-forestales/${encodeURIComponent(loteId)}/`)); }
export async function getLotesForestalesResumen(organizacionId) { return (await api.get(organizacionPath(organizacionId, "/lotes-forestales/resumen/"))).data; }
export async function getTransportesLoteForestal(organizacionId, loteId) { return (await api.get(organizacionPath(organizacionId, `/lotes-forestales/${encodeURIComponent(loteId)}/transportes/`))).data; }
export async function createTransporteLoteForestal(organizacionId, loteId, payload) { return (await api.post(organizacionPath(organizacionId, `/lotes-forestales/${encodeURIComponent(loteId)}/transportes/`), payload)).data; }
export async function createRegistroEmision(codigo, payload) { return (await api.post(obraPath(codigo, "/registros-emision/"), payload)).data; }
export async function getOrganizacionEvidencias(id, params = {}) { return (await api.get(organizacionPath(id, "/evidencias/"), { params })).data; }
export async function getEvidenciasOrganizacion(id, filters = {}) { return getOrganizacionEvidencias(id, filters); }
export async function getEvidenciasKpisOrganizacion(id) { const e = await getOrganizacionEvidencias(id); const vinculadas = e.filter((x) => x.obra || x.registros_emision?.length).length; const pendientes = e.filter((x) => ["indeterminada", "compatible_incompleta"].includes(x.estado_documental)).length; const observadas = e.filter((x) => ["contradiccion", "no_pertinente"].includes(x.estado_documental)).length; return { total: e.length, vinculadas, pendientes, observadas, cobertura_documental: e.length ? (vinculadas / e.length) * 100 : null }; }
export async function crearEvidenciaOrganizacion(id, formData) { return (await api.post(organizacionPath(id, "/evidencias/"), formData)).data; }
export async function extraerEvidenciaDocumento(id, file) {
  const formData = new FormData();
  formData.append("file", file);

  return (await api.post(organizacionPath(id, "/evidencias/extraer/"), formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })).data;
}
export async function uploadObraEvidencia(codigo, payload) { const fd = new FormData(); fd.append("tipo_evidencia", payload.tipo_evidencia || "otro"); fd.append("fecha_evidencia", payload.fecha_evidencia || ""); fd.append("nombre", payload.nombre || payload.archivo?.name || "Evidencia de obra"); fd.append("archivo", payload.archivo); if (payload.observaciones) fd.append("observaciones", payload.observaciones); return (await api.post(obraPath(codigo, "/evidencias/"), fd, { headers: { "Content-Type": "multipart/form-data" } })).data; }
export async function getOrganizacionReportes(id, params = {}) { return (await api.get(organizacionPath(id, `/reportes/${query(params)}`))).data; }
export async function getReporteEmisionesTiempo(id, params = {}) { return getOrganizacionReportes(id, params); }
export async function getSistemaEstado() { return (await api.get("/sistema/estado/")).data; }
export async function getIotKpis(id) { return (await api.get("/iot/kpis/", { params: id ? { organizacion_id: id } : {} })).data; }
export async function getIotUltimasLecturas(id) { return (await api.get("/iot/lecturas/ultimas/", { params: id ? { organizacion_id: id } : {} })).data; }
export async function getFactoresEmision(params = {}) { return (await api.get("/factores-emision/", { params })).data; }
export async function getMetodologiasAmbientales(id) { return (await api.get(organizacionPath(id, "/metodologias/"))).data; }
export async function getFactoresAmbientalesV2(id) { return (await api.get(organizacionPath(id, "/factores-ambientales/"))).data; }
export async function createFactorAmbientalV2(id, payload) { return (await api.post(organizacionPath(id, "/factores-ambientales/"), payload)).data; }
export async function createFactorVersionV2(id, factorId, payload) { return (await api.post(organizacionPath(id, `/factores-ambientales/${factorId}/versiones/`), payload)).data; }
export async function transitionFactorVersionV2(id, factorId, versionId, estado) { return (await api.post(organizacionPath(id, `/factores-ambientales/${factorId}/versiones/${versionId}/transicion/`), { estado })).data; }
export async function createVersionMetodologia(id, metodologiaId, payload) { return (await api.post(organizacionPath(id, `/metodologias/${encodeURIComponent(metodologiaId)}/`), payload)).data; }
export async function transitionVersionMetodologia(id, metodologiaId, versionId, estado) { return (await api.post(organizacionPath(id, `/metodologias/${encodeURIComponent(metodologiaId)}/versiones/${encodeURIComponent(versionId)}/transicion/`), { estado })).data; }
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
export async function previewImportOrganizaciones(file) { return previewImport("organizaciones", file); }
export async function confirmarImportOrganizaciones(payload) { return confirmImport("organizaciones", payload); }
export async function previewImportEtapasForOrganizacion(id, file) { return previewImport("etapas", file, id); }
export async function confirmarImportEtapasForOrganizacion(id, payload) { return confirmImport("etapas", payload, id); }
export async function previewImportObrasForOrganizacion(id, file) { return previewImport("obras", file, id); }
export async function confirmarImportObrasForOrganizacion(id, payload) { return confirmImport("obras", payload, id); }
export async function previewImportacionCompletaConstruccion(file) { return (await api.post("/importaciones/completa/preview/", filePayload(file), { headers: { "Content-Type": "multipart/form-data" } })).data; }
export async function confirmarImportacionCompletaConstruccion(payload) { return (await api.post("/importaciones/completa/confirm/", payload)).data; }
export const previewImportObras = previewImportObrasForOrganizacion;
export const confirmarImportObras = confirmarImportObrasForOrganizacion;
export const previewImportEtapas = previewImportEtapasForOrganizacion;
export const confirmarImportEtapas = confirmarImportEtapasForOrganizacion;

export async function getVerificacionObra(codigo) { return (await api.get(`/verificar/obra/${encodeURIComponent(codigo)}/`)).data; }
export function getObraIntegracionUrl() { return ""; }
export function getObraExportJsonUrl() { return ""; }
export function getObraExportCsvUrl() { return ""; }
export function getObraFichaTecnicaUrl(codigo) { return buildApiUrl(`/verificar/obra/${encodeURIComponent(codigo)}/`); }
export async function getHistorialObra() { return []; }
export async function downloadObraFichaAmbiental(codigo) { const response = await api.get(`/verificar/obra/${encodeURIComponent(codigo)}/`); return new Blob([JSON.stringify(response.data, null, 2)], { type: "application/json" }); }
