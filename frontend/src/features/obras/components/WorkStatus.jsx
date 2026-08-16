import { StatusBadge } from "@/shared/ui";

const labels = {
  activa: "En operación",
  activo: "En operación",
  planificada: "Planificada",
  en_ejecucion: "En ejecución",
  pausada: "Pausada",
  finalizada: "Finalizada",
  estable: "Estable",
  configuracion: "En configuración",
  monitoreo: "En monitoreo",
  requiere_atencion: "Requiere atención",
  mejora_en_curso: "Mejora en curso",
  cierre_pendiente: "Cierre pendiente",
  cerrada: "Cerrada",
  cerrado: "Cerrada",
  no_determinado: "Sin información",
  no_disponible: "Estado no disponible",
};

export function statusLabel(value) {
  return labels[value] || String(value ?? "Sin información").replaceAll("_", " ");
}

export function statusTone(value) {
  if (["cerrada", "cerrado", "estable", "activa", "activo", "en_ejecucion", "finalizada"].includes(value)) return "success";
  if (["requiere_atencion", "cierre_pendiente", "pausada"].includes(value)) return "warning";
  if (["mejora_en_curso", "monitoreo", "configuracion"].includes(value)) return "info";
  return "neutral";
}

export default function WorkStatus({ value }) {
  return <StatusBadge tone={statusTone(value)}>{statusLabel(value)}</StatusBadge>;
}
