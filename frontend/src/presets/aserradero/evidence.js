import { formatNumber } from "@/shared/utils/formatters";
import {
  countByMetadata,
  countMatching,
  formatEvidenceDate,
  getEvidenceCoverage,
  getEvidenceStatus,
  getPendingEvidenceTypes,
} from "@/presets/shared/evidenceConfig";

const requiredEvidenceTypes = [
  { key: "guia_recepcion_trozas", label: "Guia de recepcion de trozas", backendType: "guia_despacho" },
  { key: "documento_lote_madera", label: "Documento de lote de madera", backendType: "otro" },
  { key: "guia_despacho_forestal", label: "Guia de despacho forestal", backendType: "documento_transporte" },
  { key: "registro_produccion", label: "Registro de produccion", backendType: "otro" },
  { key: "registro_camara_secado", label: "Registro de camara de secado", backendType: "otro" },
  { key: "factura_electrica", label: "Factura electrica", backendType: "boleta_electrica" },
  { key: "factura_combustible", label: "Factura de combustible", backendType: "factura_combustible" },
  { key: "bitacora_transporte_forestal", label: "Bitacora de transporte forestal", backendType: "documento_transporte" },
  { key: "certificado_valorizacion_residuos", label: "Certificado de valorizacion de residuos", backendType: "registro_retiro_residuos" },
  { key: "registro_subproductos", label: "Registro de subproductos", backendType: "otro" },
];

const optionalEvidenceTypes = [
  { key: "certificado_origen_madera", label: "Certificado de origen de madera", backendType: "certificado_proveedor" },
  { key: "certificacion_fsc_pefc", label: "Certificacion FSC / PEFC", backendType: "certificado_proveedor" },
  { key: "control_humedad", label: "Control de humedad", backendType: "otro" },
  { key: "registro_mantencion_maquinaria", label: "Registro de mantencion de maquinaria", backendType: "registro_maquinaria" },
  { key: "evidencia_fotografica_acopio", label: "Evidencia fotografica de acopio", backendType: "otro" },
  { key: "informe_interno_rendimiento", label: "Informe interno de rendimiento", backendType: "otro" },
];

export const aserraderoEvidence = {
  title: "Evidencias forestales del aserradero",
  subtitle: "Respalda recepcion de trozas, lotes, secado, energia, transporte forestal y valorizacion de residuos.",
  requiredEvidenceTypes,
  optionalEvidenceTypes,
  statusRules: {},
  checklist: [
    "Cada recepcion de trozas debe tener guia o documento de lote.",
    "Cada registro de secado debe tener camara, humedad inicial/final y respaldo energetico si aplica.",
    "Cada transporte forestal debe tener origen, destino, patente y documento asociado.",
    "Cada residuo valorizado debe tener gestor o certificado.",
    "Cada consumo energetico relevante debe tener factura, medidor o registro interno.",
  ],
  emptyMessage: "No hay evidencias forestales cargadas. Sube guias de recepcion de trozas, documentos de lote, facturas de energia o certificados de residuos para respaldar la operacion ambiental.",
  buildKpis(rows) {
    const coverage = getEvidenceCoverage(rows, requiredEvidenceTypes);
    const pending = getPendingEvidenceTypes(rows, requiredEvidenceTypes);
    return [
      { label: "Evidencias cargadas", value: formatNumber(rows.length, 0), detail: "Documentos forestales", tone: "success" },
      { label: "Lotes respaldados", value: formatNumber(countByMetadata(rows, "lote"), 0), detail: "Lotes con documento", tone: "info" },
      { label: "Recepciones con respaldo", value: formatNumber(countMatching(rows, (row) => row.metadata?.module === "recepcion_trozas"), 0), detail: "Trozas documentadas", tone: "success" },
      { label: "Secado respaldado", value: formatNumber(countMatching(rows, (row) => row.metadata?.module === "secado"), 0), detail: "Camara o humedad", tone: "warning" },
      { label: "Energia respaldada", value: formatNumber(countMatching(rows, (row) => row.metadata?.module === "energia"), 0), detail: "Factura o medidor", tone: "warning" },
      { label: "Residuos con certificado", value: formatNumber(countMatching(rows, (row) => row.metadata?.module === "residuos_subproductos"), 0), detail: "Valorizacion o gestor", tone: "success" },
      { label: "Pendientes criticas", value: formatNumber(pending.length, 0), detail: `${formatNumber(coverage, 1)}% cobertura`, tone: pending.length ? "danger" : "success" },
    ];
  },
  buildRecommendations(rows, records = []) {
    const recommendations = [];
    const evidenceModules = new Set(rows.map((row) => row.metadata?.module).filter(Boolean));
    const recordModules = new Set(records.filter((row) => row.metadata?.preset === "aserradero").map((row) => row.metadata?.module).filter(Boolean));
    if (recordModules.has("recepcion_trozas") && !evidenceModules.has("recepcion_trozas")) recommendations.push("Existen recepciones de trozas sin guia o documento de lote.");
    if (recordModules.has("secado") && !evidenceModules.has("secado")) recommendations.push("Existen procesos de secado sin respaldo de camara, humedad o consumo energetico.");
    if (recordModules.has("residuos_subproductos") && !evidenceModules.has("residuos_subproductos")) recommendations.push("Hay residuos o subproductos sin certificado, valorizacion o gestor asociado.");
    if (recordModules.has("transporte_forestal") && !evidenceModules.has("transporte_forestal")) recommendations.push("Hay viajes forestales sin bitacora, patente u origen/destino documentado.");
    return recommendations.length ? recommendations : ["La documentacion forestal cargada permite iniciar validacion por modulo operativo."];
  },
  getTableColumns() {
    return [
      { key: "fecha", label: "Fecha", resolver: (row) => formatEvidenceDate(row.fecha_documento) },
      { key: "tipo", label: "Tipo", resolver: (row) => row.metadata?.evidence_label || row.tipo_evidencia },
      { key: "modulo", label: "Modulo", resolver: (row) => row.metadata?.module || "-" },
      { key: "lote", label: "Lote", resolver: (row) => row.metadata?.lote || "-" },
      { key: "proveedor", label: "Proveedor", resolver: (row) => row.metadata?.proveedor || row.metadata?.proveedor_madera || "-" },
      { key: "guia", label: "Guia / respaldo", resolver: (row) => row.metadata?.guia_despacho || row.metadata?.respaldo || "-" },
      { key: "estado", label: "Estado", resolver: (row) => getEvidenceStatus(row).label },
      { key: "archivo", label: "Archivo", resolver: (row) => row.archivo_url || "" },
    ];
  },
  getUploadMetadataFields() {
    return [
      { key: "lote", label: "Lote" },
      { key: "module", label: "Modulo operativo", type: "select", options: ["recepcion_trozas", "produccion", "secado", "energia", "transporte_forestal", "residuos_subproductos"] },
      { key: "especie", label: "Especie" },
      { key: "proveedor", label: "Proveedor" },
      { key: "guia_despacho", label: "Guia despacho" },
      { key: "camara_secado", label: "Camara secado" },
      { key: "patente", label: "Patente" },
      { key: "gestor_residuo", label: "Gestor residuo" },
    ];
  },
};
