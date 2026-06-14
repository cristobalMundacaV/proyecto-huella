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
  { key: "factura_combustible", label: "Factura de combustible", backendType: "factura_combustible" },
  { key: "bitacora_viaje", label: "Bitacora de viaje", backendType: "documento_transporte" },
  { key: "registro_gps_ruta", label: "Registro GPS / ruta", backendType: "documento_transporte" },
  { key: "orden_carga", label: "Orden de carga", backendType: "otro" },
  { key: "documento_entrega", label: "Documento de entrega", backendType: "otro" },
  { key: "mantencion_vehiculo", label: "Mantencion del vehiculo", backendType: "registro_maquinaria" },
  { key: "registro_odometro", label: "Registro de odometro", backendType: "otro" },
];

const optionalEvidenceTypes = [
  { key: "certificado_calibracion", label: "Certificado de calibracion", backendType: "certificado_proveedor" },
  { key: "registro_neumaticos", label: "Registro de neumaticos", backendType: "otro" },
  { key: "inspeccion_tecnica", label: "Inspeccion tecnica", backendType: "otro" },
  { key: "evidencia_fotografica", label: "Evidencia fotografica", backendType: "otro" },
  { key: "documento_cliente", label: "Documento cliente", backendType: "otro" },
];

export const transporteEvidence = {
  title: "Evidencias logisticas de transporte",
  subtitle: "Respalda combustible, viajes, rutas, vehiculos, carga y mantenciones.",
  requiredEvidenceTypes,
  optionalEvidenceTypes,
  statusRules: {},
  checklist: [
    "Cada viaje debe tener bitacora y ruta.",
    "Cada carga de combustible debe tener factura o comprobante.",
    "Cada vehiculo critico debe tener mantencion documentada.",
    "Las rutas frecuentes deben tener kilometraje u origen/destino.",
  ],
  emptyMessage: "No hay evidencias logisticas cargadas. Sube facturas de combustible, bitacoras de viaje o registros GPS para respaldar la operacion.",
  buildKpis(rows) {
    const pending = getPendingEvidenceTypes(rows, requiredEvidenceTypes);
    const coverage = getEvidenceCoverage(rows, requiredEvidenceTypes);
    return [
      { label: "Viajes respaldados", value: formatNumber(countByMetadata(rows, "viaje_id"), 0), detail: "Viajes con evidencia", tone: "info" },
      { label: "Litros respaldados", value: formatNumber(countMatching(rows, (row) => row.metadata?.litros), 0), detail: "Con consumo asociado", tone: "warning" },
      { label: "Rutas con evidencia", value: formatNumber(countByMetadata(rows, "ruta"), 0), detail: "Rutas documentadas", tone: "success" },
      { label: "Vehiculos con mantencion", value: formatNumber(countMatching(rows, (row) => row.evidenceType === "mantencion_vehiculo"), 0), detail: "Mantenimiento documentado", tone: "success" },
      { label: "Registros sin respaldo", value: formatNumber(pending.length, 0), detail: `${formatNumber(coverage, 1)}% cobertura`, tone: pending.length ? "danger" : "success" },
    ];
  },
  buildRecommendations(rows) {
    const pending = getPendingEvidenceTypes(rows, requiredEvidenceTypes);
    return pending.length ? pending.map((item) => `Falta evidencia: ${item.label}.`).slice(0, 4) : ["La operacion de transporte cuenta con respaldo documental base."];
  },
  getTableColumns() {
    return [
      { key: "fecha", label: "Fecha", resolver: (row) => formatEvidenceDate(row.fecha_documento) },
      { key: "tipo", label: "Tipo", resolver: (row) => row.metadata?.evidence_label || row.tipo_evidencia },
      { key: "vehiculo", label: "Vehiculo", resolver: (row) => row.metadata?.patente || "-" },
      { key: "ruta", label: "Ruta", resolver: (row) => row.metadata?.ruta || "-" },
      { key: "viaje", label: "Viaje", resolver: (row) => row.metadata?.viaje_id || "-" },
      { key: "estado", label: "Estado", resolver: (row) => getEvidenceStatus(row).label },
      { key: "archivo", label: "Archivo", resolver: (row) => row.archivo_url || "" },
    ];
  },
  getUploadMetadataFields() {
    return [
      { key: "patente", label: "Patente" },
      { key: "conductor", label: "Conductor" },
      { key: "ruta", label: "Ruta" },
      { key: "viaje_id", label: "Viaje ID" },
      { key: "litros", label: "Litros", type: "number" },
      { key: "km", label: "Km", type: "number" },
      { key: "cliente", label: "Cliente" },
    ];
  },
};
