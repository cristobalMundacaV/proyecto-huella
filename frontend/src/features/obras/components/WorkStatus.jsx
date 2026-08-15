import { StatusBadge } from "@/shared/ui";

const labels = {
  activa: "En operación", activo: "En operación", estable: "Estable",
  monitoreo: "En monitoreo", requiere_atencion: "Requiere atención",
  mejora_en_curso: "Mejora en curso", cierre_pendiente: "Cierre pendiente",
  cerrada: "Cerrada", cerrado: "Cerrada", no_determinado: "No determinado",
};

export function statusLabel(value) {
  return labels[value] || String(value || "No determinado").replaceAll("_", " ");
}

export function statusTone(value) {
  if (["cerrada", "cerrado", "estable", "activa", "activo"].includes(value)) return "success";
  if (["requiere_atencion", "cierre_pendiente"].includes(value)) return "warning";
  if (["mejora_en_curso", "monitoreo"].includes(value)) return "info";
  return "neutral";
}

export default function WorkStatus({ value }) {
  return <StatusBadge tone={statusTone(value)}>{statusLabel(value)}</StatusBadge>;
}
