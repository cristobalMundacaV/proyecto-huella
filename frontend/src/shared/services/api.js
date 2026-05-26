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

api.interceptors.request.use(async (config) => {
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

  // Add CSRF token to headers for non-read requests
  if (!isReadMethod) {
    let csrfToken = getCsrfToken();

    if (!csrfToken) {
      csrfToken = await refreshCsrfToken();
    }

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
  return `/constructoras/${encodeURIComponent(empresaId)}${path}`;
}

function mapConstructoraToEmpresa(item = {}) {
  return {
    ...item,
    empresa_id: item.empresa_id || item.constructora_id,
    unidades_count: item.unidades_count ?? item.etapas_count ?? 0,
    lotes_count: item.lotes_count ?? item.obras_count ?? 0,
    actividades_count: item.actividades_count ?? item.registros_count ?? 0,
  };
}

function mapEtapaToUnidad(item = {}) {
  return {
    ...item,
    unidad_id: item.unidad_id || item.etapa_id,
    empresa_id: item.empresa_id || item.constructora_id,
    empresa_nombre: item.empresa_nombre || item.constructora_nombre,
    lotes_count: item.lotes_count ?? item.obras_count ?? 0,
    actividades_count: item.actividades_count ?? item.registros_count ?? 0,
  };
}

function mapRegistroToActividad(item = {}) {
  return {
    ...item,
    actividad: item.actividad || item.fuente_emision,
    id_lote: item.id_lote || item.obra_codigo,
    lote: item.lote || item.obra,
    lote_nombre: item.lote_nombre || item.obra_nombre,
    unidad_operativa: item.unidad_operativa || item.etapa,
    unidad_nombre: item.unidad_nombre || item.etapa_nombre,
    emisiones: item.emisiones ?? item.emisiones_kg_co2e,
  };
}

function mapEvidenciaToDocumento(item = {}) {
  return {
    ...item,
    tipo_documento: item.tipo_documento || item.tipo_evidencia,
    tipo_documento_label: item.tipo_documento_label || item.tipo_evidencia,
    estado_validacion: item.estado_validacion || item.estado_documental,
    estado_validacion_label: item.estado_validacion_label || item.estado_documental,
    fecha: item.fecha || item.fecha_documento,
    id_lote: item.id_lote || item.obra_codigo,
    lote_codigo: item.lote_codigo || item.obra_codigo,
  };
}

function mapObraToLote(item = {}) {
  const registros = item.registros_emision || item.actividades || item.registros || [];
  const evidencias = item.evidencias || item.documentos || [];
  return {
    ...item,
    id_lote: item.id_lote || item.codigo_obra,
    empresa_id: item.empresa_id || item.constructora_id,
    empresa_nombre: item.empresa_nombre || item.constructora_nombre,
    empresa_aserradero: item.empresa_aserradero || item.constructora_nombre,
    unidad_operativa: item.unidad_operativa || item.etapa_principal,
    unidad_nombre: item.unidad_nombre || item.etapa_principal_nombre,
    especie: item.especie || item.tipo_proyecto,
    tipo_producto: item.tipo_producto || item.tipo_proyecto,
    volumen_m3: item.volumen_m3 ?? item.superficie_m2,
    origen: item.origen || item.ubicacion,
    fecha: item.fecha || item.fecha_inicio,
    actividades: registros.map(mapRegistroToActividad),
    documentos: evidencias.map(mapEvidenciaToDocumento),
  };
}

function mapDashboardResponse(data = {}) {
  return {
    ...data,
    empresa_id: data.empresa_id || data.constructora_id,
    empresa_nombre: data.empresa_nombre || data.constructora_nombre,
    lotes_count: data.lotes_count ?? data.obras_count ?? 0,
    actividades_count: data.actividades_count ?? data.registros_count ?? 0,
    actividad_critica: data.actividad_critica || data.fuente_critica,
    unidad_critica: data.unidad_critica || data.etapa_critica,
    emisiones_por_actividad: data.emisiones_por_actividad || Object.fromEntries((data.top_fuentes_criticas || []).map((row) => [row.fuente_emision, row.emisiones_kg_co2e])),
    emisiones_por_unidad_operativa: data.emisiones_por_unidad_operativa || Object.fromEntries((data.emisiones_por_etapa || []).map((row) => [row.etapa, row.emisiones_kg_co2e])),
    datos: (data.datos || []).map(mapRegistroToActividad),
  };
}

function mapObraPayload(payload = {}) {
  return {
    codigo_obra: payload.codigo_obra || payload.id_lote,
    constructora: payload.constructora,
    nombre: payload.nombre || payload.tipo_proyecto || payload.especie || payload.id_lote,
    tipo_proyecto: payload.tipo_proyecto || payload.especie || payload.tipo_producto || "Otro",
    fecha_inicio: payload.fecha_inicio || payload.fecha,
    superficie_m2: payload.superficie_m2 ?? payload.volumen_m3,
    ubicacion: payload.ubicacion || payload.origen,
    region: payload.region || "",
    comuna: payload.comuna || "",
    mandante: payload.mandante || payload.empresa_aserradero || "",
    etapa_principal: payload.etapa_principal || payload.unidad_operativa || payload.unidad_id || null,
    estado: payload.estado || "en_ejecucion",
    descripcion: payload.descripcion || "",
  };
}

function mapRegistroPayload(payload = {}) {
  return {
    ...payload,
    fuente_emision: payload.fuente_emision || payload.actividad,
    etapa: payload.etapa || payload.unidad_operativa || payload.unidad_id || null,
  };
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
      buildEmpresaScopedPath(empresaId, `/reportes/${suffix}`)
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
  const response = await api.get("/obras/");
  return response.data.map(mapObraToLote);
}

export async function getEmpresas() {
  const response = await api.get("/constructoras/");
  return response.data.map(mapConstructoraToEmpresa);
}

export async function getEmpresaDashboard(empresaId, params = {}) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/dashboard/"), { params });
  return mapDashboardResponse(response.data);
}

export async function getEmpresaEstado(empresaId) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/estado/"));
  return {
    ...response.data,
    unidades: response.data.etapas ?? response.data.unidades,
    lotes: response.data.obras ?? response.data.lotes,
    actividades: response.data.registros ?? response.data.actividades,
  };
}

export async function getEmpresaConfiguracion(empresaId) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/configuracion/"));
  return response.data;
}

export async function updateEmpresaConfiguracion(empresaId, payload) {
  const response = await api.patch(buildEmpresaScopedPath(empresaId, "/configuracion/"), payload);
  return response.data;
}

export async function getEmpresaUnidades(empresaId, params = {}) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/etapas/"), { params });
  return response.data.map(mapEtapaToUnidad);
}

export async function getEmpresaLotes(empresaId) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/obras/"));
  return response.data.map(mapObraToLote);
}

export async function getEmpresaActividades(empresaId) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/registros-emision/"));
  return response.data.map(mapRegistroToActividad);
}

export async function getEmpresaEmisiones(empresaId, params = {}) {
  const response = await api.get(
    buildEmpresaScopedPath(empresaId, "/emisiones/"),
    { params }
  );
  return response.data.map(mapRegistroToActividad);
}

export async function getEmpresaEvidencias(empresaId, params = {}) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/evidencias/"), { params });
  return response.data.map(mapEvidenciaToDocumento);
}

export async function getEvidenciasEmpresa(empresaId, filters = {}) {
  const params = {};
  ["tipo", "estado", "estado_sistema", "estado_revision", "alcance", "lote_id", "unidad_id", "search"].forEach((key) => {
    if (filters[key] !== undefined && filters[key] !== null && String(filters[key]).trim() !== "") {
      params[key] = filters[key];
    }
  });

  const response = await api.get(buildEmpresaScopedPath(empresaId, "/evidencias/"), { params });
  return response.data.map(mapEvidenciaToDocumento);
}

export async function getEvidenciasKpisEmpresa(empresaId) {
  const response = await api.get(buildEmpresaScopedPath(empresaId, "/evidencias/"));
  const evidencias = response.data || [];
  const vinculadas = evidencias.filter((item) => item.obra || item.registro_emision).length;
  const pendientes = evidencias.filter((item) => item.estado_documental === "pendiente").length;
  return {
    total: evidencias.length,
    vinculadas,
    pendientes,
    observadas: evidencias.filter((item) => item.estado_documental === "observada").length,
    total_lotes: 0,
    lotes_con_evidencia: vinculadas,
  };
}

export async function crearEvidenciaEmpresa(empresaId, formData) {
  const response = await api.post(buildEmpresaScopedPath(empresaId, "/evidencias/"), formData);
  return mapEvidenciaToDocumento(response.data);
}

export async function getSistemaEstado() {
  const response = await api.get("/sistema/estado/");
  return {
    ...response.data,
    empresas: response.data.constructoras ?? response.data.empresas,
    unidades: response.data.etapas ?? response.data.unidades,
    lotes: response.data.obras ?? response.data.lotes,
    actividades: response.data.registros_emision ?? response.data.actividades,
  };
}

export async function getIotKpis(empresaId) {
  const response = await api.get("/iot/kpis/", {
    params: empresaId ? { constructora_id: empresaId } : {},
  });
  return response.data;
}

export async function getIotUltimasLecturas(empresaId) {
  const response = await api.get("/iot/lecturas/ultimas/", {
    params: empresaId ? { constructora_id: empresaId } : {},
  });
  return response.data;
}

export async function createEmpresa(payload) {
  const response = await api.post("/constructoras/", {
    ...payload,
    constructora_id: payload.constructora_id || payload.empresa_id,
  });
  return mapConstructoraToEmpresa(response.data);
}

export async function deleteEmpresa(empresaId) {
  await api.delete(`/constructoras/${encodeURIComponent(empresaId)}/`);
}

export async function getUnidadesOperativas(params = {}) {
  if (params.empresa_id || params.constructora_id) {
    return getEmpresaUnidades(params.empresa_id || params.constructora_id, params);
  }
  const constructoras = await getEmpresas();
  const groups = await Promise.all(constructoras.map((item) => getEmpresaUnidades(item.empresa_id)));
  return groups.flat();
}

export async function createLote(payload) {
  const empresaId = payload.empresa_id || payload.constructora_id;
  const path = empresaId ? buildEmpresaScopedPath(empresaId, "/obras/") : "/obras/";
  const response = await api.post(path, mapObraPayload(payload));
  return mapObraToLote(response.data);
}

export async function getLoteDetail(idLote) {
  const [obra, registros, evidencias] = await Promise.all([
    api.get(`/obras/${encodeURIComponent(idLote)}/`),
    api.get(`/obras/${encodeURIComponent(idLote)}/registros-emision/`),
    api.get(`/obras/${encodeURIComponent(idLote)}/evidencias/`),
  ]);
  return mapObraToLote({
    ...obra.data,
    actividades: registros.data,
    documentos: evidencias.data,
  });
}

export async function createLoteActividad(idLote, payload) {
  const response = await api.post(
    `/obras/${encodeURIComponent(idLote)}/registros-emision/`,
    mapRegistroPayload(payload)
  );
  return mapRegistroToActividad(response.data);
}

export async function getEspeciesMadera() {
  const response = await api.get("/materiales-construccion/");
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
  const response = await api.get(`/obras/${encodeURIComponent(idLote)}/`);
  return response.data.analisis_ambiental || {};
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
  const response = await api.get(`/verificar/obra/${encodeURIComponent(idLote)}/`);
  return response.data;
}

export async function uploadLoteDocumento(idLote, payload) {
  const formData = new FormData();
  formData.append("tipo_evidencia", payload.tipo_evidencia || payload.tipo_documento || "otro");
  formData.append("fecha_documento", payload.fecha_documento || payload.fecha || "");
  formData.append("nombre", payload.nombre || payload.archivo?.name || "Evidencia de obra");
  formData.append("archivo", payload.archivo);

  const response = await api.post(
    `/obras/${encodeURIComponent(idLote)}/evidencias/`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );

  return mapEvidenciaToDocumento(response.data);

}

export async function createLoteTransporte(idLote, payload) {
  const response = await api.post(
    `/obras/${encodeURIComponent(idLote)}/transportes/`,
    payload
  );
  return response.data;
}
