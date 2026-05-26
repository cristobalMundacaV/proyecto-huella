import axios from "axios";

function getCsrfToken() {
  if (typeof document === "undefined") return null;
  const cookie = document.cookie
    ?.split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith("csrftoken="));
  return cookie ? decodeURIComponent(cookie.slice("csrftoken=".length)) : null;
}

export async function refreshCsrfToken() {
  const response = await axios.get(
    `${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api"}/auth/csrf-token/`,
    { withCredentials: true }
  );
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
  const isDemoMode =
    typeof window !== "undefined" &&
    window.localStorage.getItem("carbono_zero.demo") === "true";

  if (isDemoMode && !isReadMethod) {
    return Promise.reject(new axios.CanceledError("El modo demo permite solo lectura."));
  }

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
  if (candidate.startsWith("/") && typeof window !== "undefined") {
    return `${window.location.origin}${candidate}`;
  }
  return fallback;
}

function buildApiUrl(path) {
  const baseUrl = resolveApiBaseUrl(api.defaults.baseURL);
  const normalizedBaseUrl = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  return new URL(path.replace(/^\//, ""), normalizedBaseUrl).toString();
}

function constructoraPath(constructoraId, path = "") {
  return `/constructoras/${encodeURIComponent(constructoraId)}${path}`;
}

function obraPath(codigoObra, path = "") {
  return `/obras/${encodeURIComponent(codigoObra)}${path}`;
}

function buildQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.append(key, value);
  });
  const suffix = query.toString();
  return suffix ? `?${suffix}` : "";
}

export async function getCurrentUser() {
  const response = await api.get("/auth/me/");
  return response.data;
}

export async function loginUser(payload) {
  const response = await api.post("/auth/login/", payload);
  return response.data;
}

export async function logoutUser() {
  const response = await api.post("/auth/logout/");
  return response.data;
}

export async function bootstrapUser(payload) {
  const response = await api.post("/auth/bootstrap/", payload);
  return response.data;
}

export async function getConstructoras() {
  const response = await api.get("/constructoras/");
  return response.data;
}

export async function createConstructora(payload) {
  const response = await api.post("/constructoras/", payload);
  return response.data;
}

export async function deleteConstructora(constructoraId) {
  await api.delete(constructoraPath(constructoraId, "/"));
}

export async function getConstructoraUsuarios(constructoraId) {
  const response = await api.get(constructoraPath(constructoraId, "/usuarios/"));
  return response.data;
}

export async function createConstructoraUsuario(constructoraId, payload) {
  const response = await api.post(constructoraPath(constructoraId, "/usuarios/"), payload);
  return response.data;
}

export async function getConstructoraDashboard(constructoraId, params = {}) {
  const response = await api.get(constructoraPath(constructoraId, "/dashboard/"), { params });
  return response.data;
}

export async function getConstructoraEstado(constructoraId) {
  const response = await api.get(constructoraPath(constructoraId, "/estado/"));
  return response.data;
}

export async function getConstructoraConfiguracion(constructoraId) {
  const response = await api.get(constructoraPath(constructoraId, "/configuracion/"));
  return response.data;
}

export async function updateConstructoraConfiguracion(constructoraId, payload) {
  const response = await api.patch(constructoraPath(constructoraId, "/configuracion/"), payload);
  return response.data;
}

export async function getConstructoraEtapas(constructoraId, params = {}) {
  const response = await api.get(constructoraPath(constructoraId, "/etapas/"), { params });
  return response.data;
}

export async function createEtapaObra(constructoraId, payload) {
  const response = await api.post(constructoraPath(constructoraId, "/etapas/"), payload);
  return response.data;
}

export async function getEtapasObra(params = {}) {
  const constructoraId = params.constructora_id;
  if (!constructoraId) return [];
  return getConstructoraEtapas(constructoraId, params);
}

export async function getObras() {
  const response = await api.get("/obras/");
  return response.data;
}

export async function getConstructoraObras(constructoraId) {
  const response = await api.get(constructoraPath(constructoraId, "/obras/"));
  return response.data;
}

export async function createObra(payload) {
  const constructoraId = payload.constructora_id || payload.constructora;
  const endpoint = constructoraId ? constructoraPath(constructoraId, "/obras/") : "/obras/";
  const response = await api.post(endpoint, payload);
  return response.data;
}

export async function getObraDetail(codigoObra) {
  const [obra, registros, evidencias, transportes] = await Promise.all([
    api.get(obraPath(codigoObra, "/")),
    api.get(obraPath(codigoObra, "/registros-emision/")),
    api.get(obraPath(codigoObra, "/evidencias/")),
    api.get(obraPath(codigoObra, "/transportes/")),
  ]);
  return {
    ...obra.data,
    registros_emision: registros.data,
    evidencias: evidencias.data,
    transportes: transportes.data,
  };
}

export async function getObraBalanceAmbiental(codigoObra) {
  const response = await api.get(obraPath(codigoObra, "/"));
  return response.data.analisis_ambiental || {};
}

export async function getConstructoraRegistrosEmision(constructoraId) {
  const response = await api.get(constructoraPath(constructoraId, "/registros-emision/"));
  return response.data;
}

export async function getConstructoraEmisiones(constructoraId, params = {}) {
  const response = await api.get(constructoraPath(constructoraId, "/emisiones/"), { params });
  return response.data;
}

export async function createRegistroEmision(codigoObra, payload) {
  const response = await api.post(obraPath(codigoObra, "/registros-emision/"), payload);
  return response.data;
}

export async function getConstructoraEvidencias(constructoraId, params = {}) {
  const response = await api.get(constructoraPath(constructoraId, "/evidencias/"), { params });
  return response.data;
}

export async function getEvidenciasConstructora(constructoraId, filters = {}) {
  return getConstructoraEvidencias(constructoraId, filters);
}

export async function getEvidenciasKpisConstructora(constructoraId) {
  const evidencias = await getConstructoraEvidencias(constructoraId);
  const vinculadas = evidencias.filter((item) => item.obra || item.registro_emision).length;
  return {
    total: evidencias.length,
    vinculadas,
    pendientes: evidencias.filter((item) => item.estado_documental === "pendiente").length,
    observadas: evidencias.filter((item) => item.estado_documental === "observada").length,
    cobertura_documental: evidencias.length ? (vinculadas / evidencias.length) * 100 : null,
  };
}

export async function crearEvidenciaConstructora(constructoraId, formData) {
  const response = await api.post(constructoraPath(constructoraId, "/evidencias/"), formData);
  return response.data;
}

export async function uploadObraEvidencia(codigoObra, payload) {
  const formData = new FormData();
  formData.append("tipo_evidencia", payload.tipo_evidencia || "otro");
  formData.append("fecha_evidencia", payload.fecha_evidencia || "");
  formData.append("nombre", payload.nombre || payload.archivo?.name || "Evidencia de obra");
  formData.append("archivo", payload.archivo);
  if (payload.observaciones) formData.append("observaciones", payload.observaciones);
  const response = await api.post(obraPath(codigoObra, "/evidencias/"), formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function createTransporteObra(codigoObra, payload) {
  const response = await api.post(obraPath(codigoObra, "/transportes/"), payload);
  return response.data;
}

export async function getConstructoraReportes(constructoraId, params = {}) {
  const response = await api.get(constructoraPath(constructoraId, `/reportes/${buildQuery(params)}`));
  return response.data;
}

export async function getReporteEmisionesTiempo(constructoraId, params = {}) {
  return getConstructoraReportes(constructoraId, params);
}

export async function getSistemaEstado() {
  const response = await api.get("/sistema/estado/");
  return response.data;
}

export async function getIotKpis(constructoraId) {
  const response = await api.get("/iot/kpis/", {
    params: constructoraId ? { constructora_id: constructoraId } : {},
  });
  return response.data;
}

export async function getIotUltimasLecturas(constructoraId) {
  const response = await api.get("/iot/lecturas/ultimas/", {
    params: constructoraId ? { constructora_id: constructoraId } : {},
  });
  return response.data;
}

export async function getFactoresEmision() {
  const response = await api.get("/factores-emision/");
  return response.data;
}

export async function getMaterialesConstruccion() {
  const response = await api.get("/materiales-construccion/");
  return response.data;
}

export async function calculateRouteDistance(payload) {
  const response = await api.post("/rutas/calcular-distancia/", payload);
  return response.data;
}

export async function getAiAdvisor(payload) {
  const response = await api.post("/ai-advisor/", payload);
  return response.data;
}

export async function simulateScenario(payload) {
  return { rows: payload?.rows || [], total_emisiones: 0 };
}

export async function optimizeScenarioApi(rows) {
  return { rows: rows || [], reductionPct: 0 };
}

export async function getRiskScore(payload) {
  return { score: 0, payload };
}

export async function extractDocumentText() {
  return { texto: "", pendiente: true };
}

export async function extractDocumentJson() {
  return { data: {}, pendiente: true };
}

export async function extractDocumentTextById() {
  return { texto: "", pendiente: true };
}

export async function extractDocumentJsonById() {
  return { data: {}, pendiente: true };
}

export async function runEvidenciaOcr() {
  return { pendiente: true };
}

export async function validateExtraccionEvidencia() {
  return { pendiente: true };
}

export async function rejectExtraccionEvidencia() {
  return { pendiente: true };
}

function unsupportedImport() {
  return Promise.resolve({
    rows: [],
    validos: 0,
    errores: 0,
    total: 0,
    pendiente: true,
    message: "Importacion pendiente de endpoint backend.",
  });
}

export const previewImportFactores = unsupportedImport;
export const confirmarImportFactores = unsupportedImport;
export const previewImportConstructoras = unsupportedImport;
export const confirmarImportConstructoras = unsupportedImport;
export const previewImportEtapasForConstructora = unsupportedImport;
export const confirmarImportEtapasForConstructora = unsupportedImport;
export const previewImportObrasForConstructora = unsupportedImport;
export const confirmarImportObrasForConstructora = unsupportedImport;
export const previewRegistroEmisionImport = unsupportedImport;
export const confirmRegistroEmisionImport = unsupportedImport;
export const previewRegistroEmisionImportForConstructora = unsupportedImport;
export const confirmRegistroEmisionImportForConstructora = unsupportedImport;
export const previewImportacionCompletaConstruccion = unsupportedImport;
export const confirmarImportacionCompletaConstruccion = unsupportedImport;

export function getPlantillaImportacionConstruccionUrl() {
  return "";
}

export async function getVerificacionObra(codigoObra) {
  const response = await api.get(`/verificar/obra/${encodeURIComponent(codigoObra)}/`);
  return response.data;
}

export function getObraIntegracionUrl() {
  return "";
}

export function getObraExportJsonUrl() {
  return "";
}

export function getObraExportCsvUrl() {
  return "";
}

export function getObraFichaTecnicaUrl(codigoObra) {
  return buildApiUrl(`/verificar/obra/${encodeURIComponent(codigoObra)}/`);
}

export async function getHistorialObra() {
  return [];
}

export async function downloadObraFichaAmbiental(codigoObra) {
  const response = await api.get(`/verificar/obra/${encodeURIComponent(codigoObra)}/`);
  return new Blob([JSON.stringify(response.data, null, 2)], { type: "application/json" });
}
