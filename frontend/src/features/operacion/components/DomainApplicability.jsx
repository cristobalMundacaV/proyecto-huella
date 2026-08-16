import { StatusBadge } from "@/shared/ui";
import { applicability } from "../utils/operationSelectors";

const presentation = {
  aplica: ["Aplica", "info"],
  no_aplica: ["No aplica a esta unidad", "neutral"],
  pendiente: ["Por definir", "warning"],
  no_determinado: ["Por definir", "warning"],
  sin_datos: ["Sin información", "neutral"],
};

export default function DomainApplicability({ context, capability }) {
  const state = applicability(context, capability);
  const [label, tone] = presentation[state] || [String(state).replaceAll("_", " "), "neutral"];

  return <div className="flex flex-wrap items-center gap-2 text-sm">
    <span className="font-bold text-[var(--text-secondary)]">Aplicabilidad</span>
    <StatusBadge tone={tone}>{label}</StatusBadge>
    {state === "no_aplica" && <span className="text-[var(--text-muted)]">Este dominio está marcado como no aplicable para la unidad.</span>}
  </div>;
}
