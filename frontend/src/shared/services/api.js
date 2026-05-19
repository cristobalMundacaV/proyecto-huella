import axios from "axios";

// Helper function to get CSRF token from cookies
function getCsrfToken() {
  if (typeof document === "undefined") return null;
  const name = "csrftoken";
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Helper function to refresh CSRF token from server
export async function refreshCsrfToken() {
  try {
    const response = await axios.get(
      `${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api"}/auth/csrf-token/`,
      { withCredentials: true }
    );
    return response.data.csrfToken;
  } catch (error) {
    console.warn("Failed to refresh CSRF token:", error);
    return getCsrfToken();
  }
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api",
  timeout: 60000,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const method = String(config.method || "get").toLowerCase();
  const isReadMethod = ["get", "head", "options"].includes(method);
  const isDemoMode =
    typeof window !== "undefined" &&
    window.localStorage.getItem("carbono_zero.demo") === "true";

  if (isDemoMode && !isReadMethod) {
    return Promise.reject(
      new axios.CanceledError("El modo demo permite solo lectura.")
    );
  }

  // Add CSRF token to headers for non-GET requests
  if (!isReadMethod) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      config.headers["X-CSRFToken"] = csrfToken;
    }
  }

  return config;
});

function resolveApiBaseUrl(baseUrl) {
  const fallback = "http://127.0.0.1:8000/api";
  const candidate = (baseUrl || fallback).trim();

  // Absolute URL configured (e.g. https://api.domain.com/api)
  if (/^https?:\/\//i.test(candidate)) {
    return candidate;
  }

  // Relative base URL configured (e.g. /api), common in reverse-proxy deploys.
  if (candidate.startsWith("/") && typeof window !== "undefined") {
    return `${window.location.origin}${candidate}`;
  }

  return fallback;
}

function buildApiUrl(path) {
  const baseUrl = resolveApiBaseUrl(api.defaults.baseURL);
  const normalizedBaseUrl = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  const normalizedPath = path.replace(/^\//, "");

  return new URL(normalizedPath, normalizedBaseUrl).toString();
}

function buildEmpresaScopedPath(empresaId, path) {
  return `/empresas/${encodeURIComponent(empresaId)}${path}`;
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

export async function getEmpresaUsuarios(empresaId) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/usuarios/"));
  return response.data;
}

export async function createEmpresaUsuario(empresaId, payload) {
  const response = await api.post(buildEmpresaScopedPath(empresaId, "/usuarios/"), payload);
  return response.data;
}

export async function getReporteEmisionesTiempo(empresaId, params = {}) {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.append(key, value);
    }
  });

  const suffix = query.toString() ? `?${query.toString()}` : "";

  try {
    const response = await api.get(
      `/empresas/${empresaId}/reportes/emisiones-tiempo/${suffix}`
    );

    return response.data;
  } catch (error) {
    console.error("Error al cargar reporte de emisiones:", error);
    throw error;
  }
}

export function getLoteIntegracionUrl(idLote) {
  return buildApiUrl(`/integraciones/lotes/${encodeURIComponent(idLote)}/`);
}

export function getLoteExportJsonUrl(idLote) {
  return buildApiUrl(
    `/integraciones/lotes/${encodeURIComponent(idLote)}/export.json`
  );
}

export function getLoteExportCsvUrl(idLote) {
  return buildApiUrl(
    `/integraciones/lotes/${encodeURIComponent(idLote)}/export.csv`
  );
}

export function getLoteFichaTecnicaUrl(idLote) {
  return buildApiUrl(
    `/integraciones/lotes/${encodeURIComponent(idLote)}/ficha-tecnica/`
  );
}

export async function calculateRouteDistance(payload) {
  const response = await api.post("/rutas/calcular-distancia/", payload);
  return response.data;
}

export async function extractDocumentText(payload) {
  const formData = new FormData();

  if (payload.file) {
    formData.append("file", payload.file);
  }

  if (payload.texto) {
    formData.append("texto", payload.texto);
  }

  const response = await api.post("/documentos/extract-text/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function extractDocumentJson(payload) {
  const formData = new FormData();

  if (payload.file) {
    formData.append("file", payload.file);
  }

  if (payload.texto) {
    formData.append("texto", payload.texto);
  }

  const response = await api.post("/documentos/extract-json/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function extractDocumentTextById(documentoId) {
  const response = await api.post(`/documentos/${documentoId}/extract-text/`);
  return response.data;
}

export async function extractDocumentJsonById(documentoId) {
  const response = await api.post(`/documentos/${documentoId}/extract-json/`);
  return response.data;
}

export async function getHistorialLote(idLote, params = {}) {
  const response = await api.get(
    `/lotes/${encodeURIComponent(idLote)}/historial/`,
    { params }
  );
  return response.data;
}

export async function previewImportFactores(file) {
  await refreshCsrfToken();
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/importaciones/factores/preview/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function confirmarImportFactores(payload) {
  const response = await api.post("/importaciones/factores/confirm/", payload);
  return response.data;
}

export async function previewImportEmpresas(file) {
  await refreshCsrfToken();
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/importaciones/empresas/preview/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function confirmarImportEmpresas(payload) {
  const response = await api.post("/importaciones/empresas/confirm/", payload);
  return response.data;
}

export async function previewEmpresaCompleta(file) {
  await refreshCsrfToken();
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/importaciones/empresa-completa/preview/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function confirmarEmpresaCompleta(payload) {
  const response = await api.post("/importaciones/empresa-completa/confirm/", payload);
  return response.data;
}

export function getEmpresaCompletaTemplateUrl() {
  return buildApiUrl("/importaciones/empresa-completa/template/");
}

export async function previewFactorImport(file) {
  return previewImportFactores(file);
}

export async function confirmFactorImport(rowsOrPayload) {
  if (Array.isArray(rowsOrPayload)) {
    return confirmarImportFactores({ rows: rowsOrPayload });
  }

  return confirmarImportFactores(rowsOrPayload);
}

export async function previewImportLotes(file) {
  await refreshCsrfToken();
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/importaciones/lotes/preview/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function previewImportLotesForEmpresa(empresaId, file) {
  await refreshCsrfToken();
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post(
    buildEmpresaScopedPath(empresaId, "/importaciones/lotes/preview/"),
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );

  return response.data;
}

export async function confirmarImportLotes(payload) {
  const response = await api.post("/importaciones/lotes/confirm/", payload);
  return response.data;
}

export async function confirmarImportLotesForEmpresa(empresaId, payload) {
  const response = await api.post(
    buildEmpresaScopedPath(empresaId, "/importaciones/lotes/confirm/"),
    payload
  );
  return response.data;
}

export async function previewImportUnidades(file) {
  await refreshCsrfToken();
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/importaciones/unidades/preview/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function previewImportUnidadesForEmpresa(empresaId, file) {
  await refreshCsrfToken();
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post(
    buildEmpresaScopedPath(empresaId, "/importaciones/unidades/preview/"),
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );

  return response.data;
}

export async function confirmarImportUnidades(payload) {
  const response = await api.post("/importaciones/unidades/confirm/", payload);
  return response.data;
}

export async function confirmarImportUnidadesForEmpresa(empresaId, payload) {
  const response = await api.post(
    buildEmpresaScopedPath(empresaId, "/importaciones/unidades/confirm/"),
    payload
  );
  return response.data;
}

export async function previewActivityImport(file) {
  await refreshCsrfToken();
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post(
    "/importaciones/actividades/preview/",
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );

  return response.data;
}

export async function previewActivityImportForEmpresa(empresaId, file) {
  await refreshCsrfToken();
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post(
    buildEmpresaScopedPath(empresaId, "/importaciones/actividades/preview/"),
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );

  return response.data;
}

export async function confirmActivityImport(rowsOrPayload) {
  const payload = Array.isArray(rowsOrPayload)
    ? { rows: rowsOrPayload }
    : rowsOrPayload;
  const response = await api.post("/importaciones/actividades/confirm/", payload);
  return response.data;
}

export async function confirmActivityImportForEmpresa(empresaId, rowsOrPayload) {
  const payload = Array.isArray(rowsOrPayload)
    ? { rows: rowsOrPayload }
    : rowsOrPayload;
  const response = await api.post(
    buildEmpresaScopedPath(empresaId, "/importaciones/actividades/confirm/"),
    payload
  );
  return response.data;
}

export async function getAiAdvisor(payload) {
  const response = await api.post("/ai-advisor/", payload);
  return response.data;
}

export async function simulateScenario(payload) {
  const response = await api.post("/simulate/", payload);
  return response.data;
}

export async function optimizeScenarioApi(rows) {
  const response = await api.post("/optimize/", { rows });
  return response.data;
}

export async function getRiskScore(payload) {
  const response = await api.post("/risk-score/", payload);
  return response.data;
}

export async function getLotes() {
  const response = await api.get("/lotes/");
  return response.data;
}

export async function getEmpresas() {
  const response = await api.get("/empresas/");
  return response.data;
}

export async function getEmpresaDashboard(empresaId, params = {}) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/dashboard/"), { params });
  return response.data;
}

export async function getEmpresaEstado(empresaId) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/estado/"));
  return response.data;
}

export async function getEmpresaConfiguracion(empresaId) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/configuracion/"));
  return response.data;
}

export async function updateEmpresaConfiguracion(empresaId, payload) {
  const response = await api.put(buildEmpresaScopedPath(empresaId, "/configuracion/"), payload);
  return response.data;
}

export async function getEmpresaUnidades(empresaId, params = {}) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/unidades/"), { params });
  return response.data;
}

export async function getEmpresaLotes(empresaId) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/lotes/"));
  return response.data;
}

export async function getEmpresaActividades(empresaId) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/actividades/"));
  return response.data;
}

export async function getEmpresaEmisiones(empresaId, params = {}) {
  const response = await api.get(
    buildEmpresaScopedPath(empresaId, "/emisiones/"),
    { params }
  );
  return response.data;
}

export async function getEmpresaEvidencias(empresaId, params = {}) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/evidencias/"), { params });
  return response.data;
}

export async function getEvidenciasEmpresa(empresaId, filters = {}) {
  const params = {};
  ["tipo", "estado", "estado_sistema", "estado_revision", "alcance", "lote_id", "unidad_id", "search"].forEach((key) => {
    if (filters[key] !== undefined && filters[key] !== null && String(filters[key]).trim() !== "") {
      params[key] = filters[key];
    }
  });

  const response = await api.get(buildEmpresaScopedPath(empresaId, "/evidencias/"), { params });
  return response.data;
}

export async function getEvidenciasKpisEmpresa(empresaId) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/evidencias/kpis/"));
  return response.data;
}

export async function crearEvidenciaEmpresa(empresaId, formData) {
  const response = await api.post(buildEmpresaScopedPath(empresaId, "/evidencias/crear/"), formData);
  return response.data;
}

export async function getSistemaEstado() {
  const response = await api.get("/sistema/estado/");
  return response.data;
}

export async function getIotKpis(empresaId) {
  const response = await api.get("/iot/kpis/", {
    params: empresaId ? { empresa_id: empresaId } : {},
  });
  return response.data;
}

export async function getIotUltimasLecturas(empresaId) {
  const response = await api.get("/iot/lecturas/ultimas/", {
    params: empresaId ? { empresa_id: empresaId } : {},
  });
  return response.data;
}

export async function createEmpresa(payload) {
  const response = await api.post("/empresas/", payload);
  return response.data;
}

export async function deleteEmpresa(empresaId) {
  await api.delete(`/empresas/${encodeURIComponent(empresaId)}/`);
}

export async function getUnidadesOperativas(params = {}) {
  const response = await api.get("/unidades-operativas/", { params });
  return response.data;
}

export async function createLote(payload) {
  const response = await api.post("/lotes/", payload);
  return response.data;
}

export async function getLoteDetail(idLote) {
  const response = await api.get(`/lotes/${encodeURIComponent(idLote)}/`);
  return response.data;
}

export async function createLoteActividad(idLote, payload) {
  const response = await api.post(
    `/lotes/${encodeURIComponent(idLote)}/actividades/`,
    payload
  );
  return response.data;
}

export async function getEspeciesMadera() {
  const response = await api.get("/especies-madera/");
  return response.data;
}

function cleanActivityText(value) {
  return String(value || "")
    .replace(/[_\-\u2010-\u2015]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function cleanFactorTextFields(factor) {
  const actividad = cleanActivityText(factor.actividad);

  return {
    ...factor,
    actividad,
    label: [
      actividad,
      factor.unidad,
      factor.factor_emision ? `${factor.factor_emision} kgCO2e/${factor.unidad}` : "",
    ]
      .filter(Boolean)
      .join(" · "),
  };
}

export async function getFactoresEmision() {
  const response = await api.get("/factores-emision/");
  return response.data.map(cleanFactorTextFields);
}

export async function getLoteCarbono(idLote) {
  const response = await api.get(`/lotes/${encodeURIComponent(idLote)}/carbono/`);
  return response.data;
}

export async function downloadLoteCertificado(idLote) {
  const response = await api.get(
    `/lotes/${encodeURIComponent(idLote)}/certificado/`,
    { responseType: "blob" }
  );
  return response.data;
}

export async function runDocumentoOcr(documentoId) {
  const response = await api.post(`/documentos/${documentoId}/ocr/`);
  return response.data;
}

export async function validateExtraccionDocumento(extraccionId, payload) {
  const response = await api.post(
    `/extracciones/${extraccionId}/validar/`,
    payload
  );
  return response.data;
}

export async function rejectExtraccionDocumento(extraccionId) {
  const response = await api.post(`/extracciones/${extraccionId}/rechazar/`);
  return response.data;
}

export async function getVerificacionLote(idLote) {
  const response = await api.get(`/verificar/${encodeURIComponent(idLote)}/`);
  return response.data;
}

export async function uploadLoteDocumento(idLote, payload) {
  const formData = new FormData();
  formData.append("tipo_documento", payload.tipo_documento);
  formData.append("fecha", payload.fecha);
  formData.append("archivo", payload.archivo);

  const response = await api.post(
    `/lotes/${encodeURIComponent(idLote)}/documentos/`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );

  return response.data;

}

export async function createLoteTransporte(idLote, payload) {
  const response = await api.post(
    `/lotes/${encodeURIComponent(idLote)}/transportes/`,
    payload
  );
  return response.data;
}
