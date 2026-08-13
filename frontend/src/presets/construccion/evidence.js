import { formatNumber } from "@/shared/utils/formatters";
import {
  countByMetadata,
  formatEvidenceDate,
  getEvidenceCoverage,
  getEvidenceStatus,
  getPendingEvidenceTypes,
} from "@/presets/shared/evidenceConfig";

const requiredEvidenceTypes = [
  { key: "guia_despacho_materiales", label: "Guia de despacho de materiales", backendType: "guia_despacho" },
  { key: "factura_materiales", label: "Factura de materiales", backendType: "factura_material" },
  { key: "ficha_tecnica_material", label: "Ficha tecnica de material", backendType: "ficha_tecnica_material" },
  { key: "registro_combustible_maquinaria", label: "Registro de combustible maquinaria", backendType: "registro_maquinaria" },
  { key: "guia_retiro_residuos", label: "Guia de retiro de residuos", backendType: "registro_retiro_residuos" },
  { key: "certificado_disposicion_final", label: "Certificado de disposicion final", backendType: "registro_retiro_residuos" },
  { key: "registro_transporte", label: "Registro de transporte", backendType: "documento_transporte" },
  { key: "evidencia_fotografica_obra", label: "Evidencia fotografica de obra", backendType: "otro" },
];

const optionalEvidenceTypes = [
  { key: "certificacion_proveedor", label: "Certificacion proveedor", backendType: "certificado_proveedor" },
  { key: "declaracion_ambiental_producto", label: "Declaracion ambiental de producto", backendType: "certificado_proveedor" },
  { key: "plano_documento_tecnico", label: "Plano o documento tecnico", backendType: "otro" },
  { key: "acta_inspeccion", label: "Acta de inspeccion", backendType: "otro" },
];

export const construccionEvidence = {
  title: "Evidencias documentales de construccion",
  subtitle: "Respalda obras, etapas, materiales, transporte, maquinaria y residuos con documentos verificables.",
  requiredEvidenceTypes,
  optionalEvidenceTypes,
  statusRules: {},
  checklist: [
    "Materiales con guia, factura o ficha tecnica.",
    "Combustible y maquinaria con registro documentado.",
    "Residuos con guia de retiro o certificado de disposicion.",
    "Transporte con documento asociado.",
    "Obras criticas con evidencia fotografica o tecnica.",
  ],
  emptyMessage: "No hay evidencias de construccion cargadas. Sube guias, facturas, fichas tecnicas o certificados de residuos para respaldar la operacion.",
  buildKpis(rows) {
    const coverage = getEvidenceCoverage(rows, requiredEvidenceTypes);
    const pending = getPendingEvidenceTypes(rows, requiredEvidenceTypes);
    return [
      { label: "Evidencias cargadas", value: formatNumber(rows.length, 0), detail: "Respaldos documentales", tone: "success" },
      { label: "Cobertura documental", value: `${formatNumber(coverage, 1)}%`, detail: "Tipos requeridos cubiertos", tone: coverage >= 70 ? "success" : "warning" },
      { label: "Evidencias pendientes", value: formatNumber(pending.length, 0), detail: "Tipos requeridos faltantes", tone: pending.length ? "danger" : "success" },
      { label: "Evidencias vinculadas", value: formatNumber(rows.filter((row) => row.registros_emision?.length || row.obra || row.etapa).length, 0), detail: "Con relacion operativa", tone: "info" },
      { label: "Criticas faltantes", value: formatNumber(pending.slice(0, 3).length, 0), detail: "Prioridad documental", tone: pending.length ? "danger" : "success" },
    ];
  },
  buildRecommendations(rows) {
    const pending = getPendingEvidenceTypes(rows, requiredEvidenceTypes);
    return pending.length
      ? pending.slice(0, 4).map((item) => `Falta cargar: ${item.label}.`)
      : ["La cobertura documental requerida para construccion esta completa para este set de tipos."];
  },
  getTableColumns() {
    return [
      { key: "fecha", label: "Fecha", resolver: (row) => formatEvidenceDate(row.fecha_documento) },
      { key: "tipo", label: "Tipo", resolver: (row) => row.metadata?.evidence_label || row.tipo_evidencia },
      { key: "obra", label: "Obra", resolver: (row) => row.obra_nombre || row.metadata?.obra || "-" },
      { key: "etapa", label: "Etapa", resolver: (row) => row.etapa_nombre || row.metadata?.etapa || "-" },
      { key: "registro", label: "Registros vinculados", resolver: (row) => row.registros_fuente?.join(", ") || "-" },
      { key: "estado", label: "Estado", resolver: (row) => getEvidenceStatus(row).label },
      { key: "archivo", label: "Archivo", resolver: (row) => row.archivo_url || "" },
    ];
  },
  getUploadMetadataFields() {
    return [
      { key: "obra", label: "Obra" },
      { key: "etapa", label: "Etapa" },
      { key: "proveedor", label: "Proveedor" },
      { key: "guia_despacho", label: "Guia despacho" },
      { key: "material", label: "Material" },
      { key: "maquinaria", label: "Maquinaria" },
      { key: "gestor_residuo", label: "Gestor residuo" },
    ];
  },
};
