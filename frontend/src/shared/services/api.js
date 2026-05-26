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

const REDUCTION_LIBRARY = {
  Materiales: {
    maxReduction: 0.18,
    quickWin: 0.06,
    label: "Materiales",
    levers: [
      "Revisar hormigón, cemento, acero y áridos",
      "Comparar proveedores con menor factor de emisión",
      "Reducir desperdicio y sobreconsumo de materiales",
      "Priorizar fichas técnicas o EPD cuando existan",
    ],
  },
  Transporte: {
    maxReduction: 0.24,
    quickWin: 0.08,
    label: "Transporte",
    levers: [
      "Consolidar viajes",
      "Priorizar proveedores cercanos",
      "Reducir kilómetros sin carga útil",
      "Optimizar rutas y frecuencia de despacho",
    ],
  },
  Maquinaria: {
    maxReduction: 0.18,
    quickWin: 0.07,
    label: "Maquinaria",
    levers: [
      "Controlar ralentí",
      "Medir litros u horas máquina por equipo",
      "Planificar turnos de maquinaria",
      "Reforzar mantención preventiva",
    ],
  },
  Energia: {
    maxReduction: 0.22,
    quickWin: 0.08,
    label: "Energía",
    levers: [
      "Reducir uso de generadores",
      "Optimizar consumo eléctrico de faena",
      "Evaluar conexión temporal a red",
      "Controlar horarios de mayor consumo",
    ],
  },
  Energía: {
    maxReduction: 0.22,
    quickWin: 0.08,
    label: "Energía",
    levers: [
      "Reducir uso de generadores",
      "Optimizar consumo eléctrico de faena",
      "Evaluar conexión temporal a red",
      "Controlar horarios de mayor consumo",
    ],
  },
  Residuos: {
    maxReduction: 0.15,
    quickWin: 0.05,
    label: "Residuos",
    levers: [
      "Segregar residuos valorizables",
      "Mejorar trazabilidad de retiro",
      "Reducir residuos mixtos",
      "Priorizar reciclaje o valorización",
    ],
  },
  Agua: {
    maxReduction: 0.08,
    quickWin: 0.03,
    label: "Agua",
    levers: [
      "Monitorear consumo por etapa",
      "Detectar desviaciones operativas",
      "Controlar uso en faena",
    ],
  },
  "Procesos externos": {
    maxReduction: 0.12,
    quickWin: 0.04,
    label: "Procesos externos",
    levers: [
      "Revisar subcontratos críticos",
      "Solicitar información ambiental de proveedores",
      "Priorizar procesos con respaldo documental",
    ],
  },
  Otros: {
    maxReduction: 0.06,
    quickWin: 0.02,
    label: "Otros",
    levers: [
      "Clasificar mejor los registros",
      "Separar fuentes de emisión por categoría",
      "Completar factores y evidencias",
    ],
  },
};

function normalizeScenarioText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
}

function getScenarioRows(input) {
  if (Array.isArray(input)) return input;
  if (Array.isArray(input?.rows)) return input.rows;
  if (Array.isArray(input?.datos)) return input.datos;
  if (Array.isArray(input?.registros)) return input.registros;
  if (Array.isArray(input?.registros_emision)) return input.registros_emision;
  if (Array.isArray(input?.data)) return input.data;
  return [];
}

function getRegistroEmisionesValue(row) {
  return Number(
    row?.emisiones_kg_co2e ??
      row?.emisiones_totales ??
      row?.emisiones ??
      row?.total_emisiones ??
      row?.co2e ??
      0
  );
}

function getRegistroFuente(row) {
  return (
    row?.fuente_emision ||
    row?.fuente ||
    row?.actividad ||
    row?.material ||
    row?.nombre ||
    "Fuente sin clasificar"
  );
}

function getRegistroCategoria(row) {
  const rawCategory = row?.categoria || row?.category || "Otros";
  const normalized = normalizeScenarioText(rawCategory);

  if (normalized.includes("material")) return "Materiales";
  if (normalized.includes("transporte")) return "Transporte";
  if (normalized.includes("maquinaria")) return "Maquinaria";
  if (normalized.includes("energia") || normalized.includes("energía")) return "Energia";
  if (normalized.includes("agua")) return "Agua";
  if (normalized.includes("residuo")) return "Residuos";
  if (normalized.includes("proceso")) return "Procesos externos";

  return rawCategory || "Otros";
}

function getRegistroEtapa(row) {
  return (
    row?.etapa_nombre ||
    row?.etapa ||
    row?.obra_etapa ||
    row?.frente ||
    "Sin etapa"
  );
}

function hasLinkedEvidence(row) {
  return Boolean(
    row?.evidencia ||
      row?.evidencia_id ||
      row?.evidencia_asociada ||
      row?.registro_emision_evidencia ||
      (Array.isArray(row?.evidencias) && row.evidencias.length > 0)
  );
}

function getCategoryConfig(category) {
  return REDUCTION_LIBRARY[category] || REDUCTION_LIBRARY.Otros;
}

function groupScenarioData(rows) {
  const categoryTotals = new Map();
  const sourceTotals = new Map();
  const stageTotals = new Map();
  let total = 0;
  let evidenceCount = 0;

  rows.forEach((row) => {
    const emissions = getRegistroEmisionesValue(row);
    if (emissions <= 0) return;

    const category = getRegistroCategoria(row);
    const source = getRegistroFuente(row);
    const stage = getRegistroEtapa(row);

    total += emissions;

    categoryTotals.set(category, (categoryTotals.get(category) || 0) + emissions);

    if (!sourceTotals.has(source)) {
      sourceTotals.set(source, {
        fuente: source,
        categoria: category,
        emisiones: 0,
      });
    }
    sourceTotals.get(source).emisiones += emissions;

    stageTotals.set(stage, (stageTotals.get(stage) || 0) + emissions);

    if (hasLinkedEvidence(row)) evidenceCount += 1;
  });

  const sortedCategories = [...categoryTotals.entries()]
    .map(([categoria, emisiones]) => ({ categoria, emisiones }))
    .sort((a, b) => b.emisiones - a.emisiones);

  const sortedSources = [...sourceTotals.values()].sort(
    (a, b) => b.emisiones - a.emisiones
  );

  const sortedStages = [...stageTotals.entries()]
    .map(([etapa, emisiones]) => ({ etapa, emisiones }))
    .sort((a, b) => b.emisiones - a.emisiones);

  const rowsWithEmissions = rows.filter((row) => getRegistroEmisionesValue(row) > 0);
  const evidenceCoverage = rowsWithEmissions.length
    ? evidenceCount / rowsWithEmissions.length
    : null;

  return {
    total,
    rows: rowsWithEmissions,
    sortedCategories,
    sortedSources,
    sortedStages,
    evidenceCoverage,
  };
}

function getDataConfidence(summary) {
  let confidence = 0.72;

  if (summary.rows.length >= 5) confidence += 0.08;
  if (summary.rows.length >= 10) confidence += 0.05;
  if (summary.sortedCategories.length >= 3) confidence += 0.05;

  if (summary.evidenceCoverage !== null) {
    confidence *= 0.82 + summary.evidenceCoverage * 0.18;
  } else {
    confidence *= 0.88;
  }

  return Math.min(1, Math.max(0.45, confidence));
}

function getGlobalCap(summary) {
  let cap = 0.18;

  if (summary.sortedCategories.length >= 2) cap += 0.03;
  if (summary.sortedCategories.length >= 4) cap += 0.03;
  if (summary.rows.length >= 10) cap += 0.02;
  if (summary.evidenceCoverage !== null && summary.evidenceCoverage >= 0.7) cap += 0.03;

  return Math.min(0.32, cap);
}

function buildScenario(summary, ambition) {
  const confidence = getDataConfidence(summary);
  const globalCap = getGlobalCap(summary);
  const topCategories = summary.sortedCategories.slice(0, 4).map((item) => item.categoria);
  const topSource = summary.sortedSources[0];
  const topCategory = summary.sortedCategories[0];

  let avoided = 0;
  const reductionsByCategory = {};
  const assumptions = [];

  summary.rows.forEach((row) => {
    const emissions = getRegistroEmisionesValue(row);
    const category = getRegistroCategoria(row);
    const source = getRegistroFuente(row);
    const config = getCategoryConfig(category);

    const categoryRank = topCategories.indexOf(category);
    const isTopCategory = categoryRank !== -1;
    const isCriticalSource = topSource && source === topSource.fuente;

    let priorityFactor = 0.35;

    if (isTopCategory) {
      priorityFactor = 0.65 - categoryRank * 0.1;
    }

    if (isCriticalSource) {
      priorityFactor = Math.max(priorityFactor, 1);
    }

    const rowReductionRate = Math.min(
      config.maxReduction,
      config.maxReduction * ambition * priorityFactor * confidence
    );

    const rowAvoided = emissions * rowReductionRate;
    avoided += rowAvoided;

    if (!reductionsByCategory[category]) {
      reductionsByCategory[category] = {
        categoria: category,
        emisiones_base: 0,
        emisiones_evitadas: 0,
        reduccion_pct_categoria: 0,
        palancas: config.levers,
      };
    }

    reductionsByCategory[category].emisiones_base += emissions;
    reductionsByCategory[category].emisiones_evitadas += rowAvoided;
  });

  const cappedAvoided = Math.min(avoided, summary.total * globalCap);
  const reductionPct = summary.total > 0 ? (cappedAvoided / summary.total) * 100 : 0;
  const simulatedTotal = Math.max(summary.total - cappedAvoided, 0);

  Object.values(reductionsByCategory).forEach((item) => {
    item.reduccion_pct_categoria = item.emisiones_base
      ? (item.emisiones_evitadas / item.emisiones_base) * 100
      : 0;
  });

  assumptions.push({
    nombre: "ambicion_operativa",
    valor: ambition,
    descripcion: "Nivel de aplicación de medidas operativas y de gestión sobre fuentes críticas.",
  });
  assumptions.push({
    nombre: "confianza_datos",
    valor: confidence,
    descripcion: "Ajuste según cantidad de registros, categorías disponibles y trazabilidad documental.",
  });
  assumptions.push({
    nombre: "tope_global_realista",
    valor: globalCap,
    descripcion: "Límite máximo de reducción global para evitar escenarios poco realistas.",
  });

  return {
    rows: summary.rows,
    currentTotal: summary.total,
    simulatedTotal,
    reductionPct,
    avoidedEmissions: cappedAvoided,
    activityReduction: topSource
      ? Math.min(
          getCategoryConfig(topSource.categoria).maxReduction * 100,
          reductionPct / Math.max(topSource.emisiones / summary.total, 0.01)
        )
      : 0,
    dieselReduction: reductionPct,
    targetSource: topSource?.fuente || "Sin fuente crítica",
    targetCategory: topSource?.categoria || topCategory?.categoria || "Otros",
    targetStage: summary.sortedStages[0]?.etapa || "Sin etapa",
    confidence,
    globalCap,
    ambition,
    reductionsByCategory: Object.values(reductionsByCategory),
    assumptions,
    assumptionsTested: 0,
    recommendedActions: topSource
      ? getCategoryConfig(topSource.categoria).levers
      : REDUCTION_LIBRARY.Otros.levers,
  };
}

export async function simulateScenario(payload) {
  const rows = getScenarioRows(payload);
  const summary = groupScenarioData(rows);

  if (!summary.rows.length || summary.total <= 0) {
    return {
      rows: [],
      total_emisiones: 0,
      currentTotal: 0,
      simulatedTotal: 0,
      reductionPct: 0,
      pending: true,
    };
  }

  const scenario = buildScenario(summary, 0.55);

  return {
    ...scenario,
    total_emisiones: scenario.currentTotal,
  };
}

export async function optimizeScenarioApi(input) {
  const rows = getScenarioRows(input);
  const summary = groupScenarioData(rows);

  if (!summary.rows.length || summary.total <= 0) {
    return null;
  }

  const ambitions = [];
  for (let value = 0.35; value <= 1.001; value += 0.05) {
    ambitions.push(Number(value.toFixed(2)));
  }

  const scenarios = ambitions
    .map((ambition) => buildScenario(summary, ambition))
    .filter((scenario) => scenario.reductionPct > 0);

  if (!scenarios.length) {
    return null;
  }

  const bestScenario = scenarios.reduce((best, scenario) =>
    scenario.reductionPct > best.reductionPct ? scenario : best
  );

  const recommendedScenario = scenarios.reduce((best, scenario) => {
    const target = bestScenario.reductionPct * 0.65;
    const currentDistance = Math.abs(scenario.reductionPct - target);
    const bestDistance = Math.abs(best.reductionPct - target);
    return currentDistance < bestDistance ? scenario : best;
  }, scenarios[0]);

  return {
    ...bestScenario,
    recommendedScenario,
    assumptionsTested: scenarios.length,
    reductionPct: Number(bestScenario.reductionPct.toFixed(1)),
    currentTotal: Number(bestScenario.currentTotal.toFixed(3)),
    simulatedTotal: Number(bestScenario.simulatedTotal.toFixed(3)),
    avoidedEmissions: Number(bestScenario.avoidedEmissions.toFixed(3)),
    activityReduction: Number(bestScenario.activityReduction.toFixed(1)),
    dieselReduction: Number(bestScenario.dieselReduction.toFixed(1)),
    scenarioLabel: "Máximo realista",
    methodology:
      "Escenario calculado probando supuestos progresivos por categoría, fuente crítica, confianza de datos y tope global realista.",
  };
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
