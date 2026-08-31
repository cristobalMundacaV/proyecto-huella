import { captureStateInfo } from "@/shared/utils/canonicalDataState";

const humanize = (value, fallback = "Sin información") => {
  if (value === null || value === undefined || value === "") return fallback;
  const text = String(value).replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
};

const evidenceStates = {
  verificada: { label: "Verificada", tone: "success", needsAttention: false },
  compatible_incompleta: { label: "Compatible incompleta", tone: "warning", needsAttention: true },
  contradiccion: { label: "Contradicción", tone: "danger", needsAttention: true },
  no_pertinente: { label: "No pertinente", tone: "danger", needsAttention: true },
  indeterminada: { label: "Indeterminada", tone: "neutral", needsAttention: true },
};

const importStates = {
  recibido: { label: "Recibida", tone: "neutral" },
  analizando: { label: "Analizando", tone: "info" },
  requiere_mapeo: { label: "Requiere definir columnas", tone: "warning" },
  listo_para_confirmar: { label: "Lista para confirmar", tone: "warning" },
  procesando: { label: "Procesando", tone: "info" },
  completado: { label: "Completada", tone: "success" },
  completado_con_observaciones: { label: "Completada con observaciones", tone: "warning" },
  fallido: { label: "Fallida", tone: "danger" },
};

const destinationLabels = {
  actividad_generica: "Actividad operacional",
  transporte: "Transporte",
  material: "Materiales",
  flujo_ambiental: "Flujo ambiental",
};

export function evidenceStatusInfo(value) {
  const workflow = evidenceStates[value];
  const canonical = captureStateInfo(value);
  return workflow
    ? { ...workflow, canonical: canonical.label, workflowLabel: workflow.label }
    : { label: humanize(value), tone: "neutral", needsAttention: false, canonical: canonical.label };
}

export function evidenceNeedsAttention(item) {
  return Boolean(evidenceStatusInfo(item?.estado_documental).needsAttention);
}

export function importStatusInfo(value) {
  const workflow = importStates[value];
  const canonical = captureStateInfo(value);
  return workflow
    ? { ...workflow, label: canonical.label, canonical: canonical.label, workflowLabel: workflow.label }
    : { label: humanize(value), tone: "neutral", canonical: canonical.label };
}

export function importNeedsAttention(item) {
  if (!item) return false;
  if (["requiere_mapeo", "listo_para_confirmar", "fallido"].includes(item.estado)) return true;
  return item.estado === "completado_con_observaciones";
}

export function importAttentionReason(item) {
  if (!item) return "";
  if (item.estado === "requiere_mapeo") return "Indica qué significa cada columna antes de continuar.";
  if (item.estado === "listo_para_confirmar") return "La carga está preparada y necesita confirmación.";
  if (item.estado === "fallido") return "La carga no pudo completarse. Revisa el detalle.";
  if (item.estado === "completado_con_observaciones") {
    return item.filas_con_error === null || item.filas_con_error === undefined
      ? "La carga terminó con observaciones."
      : `${item.filas_con_error} ${item.filas_con_error === 1 ? "fila requiere" : "filas requieren"} revisión.`;
  }
  return "";
}

export function importResultLabel(item) {
  if (!item) return "Sin datos";
  if (item.estado === "procesando") return "Procesando";
  if (item.estado === "fallido") return "No se completó";
  if (!["completado", "completado_con_observaciones"].includes(item.estado)) return "Aún sin resultado";

  const processed = item.filas_procesadas;
  const errors = item.filas_con_error;
  if (processed === null || processed === undefined) {
    return errors === null || errors === undefined ? "Sin datos" : `${errors} errores`;
  }
  if (errors === null || errors === undefined) return `${processed} procesados`;
  return `${processed} procesados · ${errors} errores`;
}

export function importDisplayName(item) {
  return item?.version_evidencia_detalle?.nombre_original || item?.fuente_nombre || "Importación";
}

export function destinationLabel(value) {
  return destinationLabels[value] || humanize(value);
}

export function evidenceTypeLabel(value) {
  return humanize(value);
}

export function importProgressStep(state) {
  if (state === "fallido") return null;
  if (state === "recibido") return 1;
  if (["analizando", "requiere_mapeo"].includes(state)) return 2;
  if (state === "listo_para_confirmar") return 3;
  if (state === "procesando") return 4;
  if (["completado", "completado_con_observaciones"].includes(state)) return 5;
  return 1;
}
