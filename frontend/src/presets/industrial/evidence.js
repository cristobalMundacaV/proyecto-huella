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
  { key: "factura_electrica", label: "Factura electrica", backendType: "boleta_electrica" },
  { key: "factura_combustible", label: "Factura de combustible", backendType: "factura_combustible" },
  { key: "registro_produccion", label: "Registro de produccion", backendType: "otro" },
  { key: "registro_proceso", label: "Registro de proceso", backendType: "otro" },
  { key: "registro_residuos", label: "Registro de residuos", backendType: "registro_retiro_residuos" },
  { key: "certificado_disposicion_residuos", label: "Certificado de disposicion de residuos", backendType: "registro_retiro_residuos" },
  { key: "registro_agua", label: "Registro de agua", backendType: "otro" },
  { key: "informe_interno_operacion", label: "Informe interno de operacion", backendType: "otro" },
];

const optionalEvidenceTypes = [
  { key: "certificado_proveedor", label: "Certificado proveedor", backendType: "certificado_proveedor" },
  { key: "auditoria_interna", label: "Auditoria interna", backendType: "otro" },
  { key: "medicion_proceso", label: "Medicion de proceso", backendType: "otro" },
  { key: "evidencia_fotografica", label: "Evidencia fotografica", backendType: "otro" },
  { key: "certificado_ambiental", label: "Certificado ambiental", backendType: "certificado_proveedor" },
];

export const industrialEvidence = {
  title: "Evidencias ambientales industriales",
  subtitle: "Respalda energia, combustible, procesos, residuos, agua y operacion industrial.",
  requiredEvidenceTypes,
  optionalEvidenceTypes,
  statusRules: {},
  checklist: [
    "Consumos energeticos con factura, medidor o registro interno.",
    "Procesos productivos con parte o informe de operacion.",
    "Residuos con registro y certificado de disposicion.",
    "Agua con medicion o documento de respaldo.",
  ],
  emptyMessage: "No hay evidencias industriales cargadas. Sube facturas, registros de proceso, certificados de residuos o registros de agua para respaldar el periodo.",
  buildKpis(rows) {
    const pending = getPendingEvidenceTypes(rows, requiredEvidenceTypes);
    const coverage = getEvidenceCoverage(rows, requiredEvidenceTypes);
    return [
      { label: "Procesos respaldados", value: formatNumber(countByMetadata(rows, "proceso"), 0), detail: "Procesos documentados", tone: "info" },
      { label: "Energia respaldada", value: formatNumber(countMatching(rows, (row) => ["factura_electrica", "factura_combustible"].includes(row.evidenceType)), 0), detail: "Consumos energéticos", tone: "warning" },
      { label: "Residuos certificados", value: formatNumber(countMatching(rows, (row) => row.evidenceType?.includes("residuos")), 0), detail: "Disposicion documentada", tone: "success" },
      { label: "Agua documentada", value: formatNumber(countMatching(rows, (row) => row.evidenceType === "registro_agua"), 0), detail: "Consumo hidrico", tone: "info" },
      { label: "Criticas faltantes", value: formatNumber(pending.length, 0), detail: `${formatNumber(coverage, 1)}% cobertura`, tone: pending.length ? "danger" : "success" },
    ];
  },
  buildRecommendations(rows) {
    const pending = getPendingEvidenceTypes(rows, requiredEvidenceTypes);
    return pending.length ? pending.map((item) => `Falta respaldo industrial: ${item.label}.`).slice(0, 4) : ["La operacion industrial cuenta con respaldo documental base."];
  },
  getTableColumns() {
    return [
      { key: "fecha", label: "Fecha", resolver: (row) => formatEvidenceDate(row.fecha_documento) },
      { key: "tipo", label: "Tipo", resolver: (row) => row.metadata?.evidence_label || row.tipo_evidencia },
      { key: "proceso", label: "Area / proceso", resolver: (row) => row.metadata?.area || row.metadata?.proceso || "-" },
      { key: "medidor", label: "Medidor / lote", resolver: (row) => row.metadata?.medidor || row.metadata?.lote_produccion || "-" },
      { key: "estado", label: "Estado", resolver: (row) => getEvidenceStatus(row).label },
      { key: "archivo", label: "Archivo", resolver: (row) => row.archivo_url || "" },
    ];
  },
  getUploadMetadataFields() {
    return [
      { key: "area", label: "Area" },
      { key: "proceso", label: "Proceso" },
      { key: "medidor", label: "Medidor" },
      { key: "turno", label: "Turno" },
      { key: "lote_produccion", label: "Lote produccion" },
      { key: "gestor_residuo", label: "Gestor residuo" },
    ];
  },
};
