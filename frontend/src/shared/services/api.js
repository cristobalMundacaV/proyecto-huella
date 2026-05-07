import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api",
  timeout: 10000,
});

function buildApiUrl(path) {
  const baseUrl = api.defaults.baseURL || "http://127.0.0.1:8000/api";
  const normalizedBaseUrl = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  const normalizedPath = path.replace(/^\//, "");

  return new URL(normalizedPath, normalizedBaseUrl).toString();
}

function buildEmpresaScopedPath(empresaId, path) {
  return `/empresas/${encodeURIComponent(empresaId)}${path}`;
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
