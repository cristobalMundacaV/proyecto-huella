import { Alert, StatusBadge } from "@/shared/ui";
import { applicability } from "../utils/operationSelectors";

const presentation = {
  aplica: ["Aplica", "success"], no_aplica: ["No aplica", "neutral"],
  pendiente: ["Por definir", "warning"], no_determinado: ["Por definir", "warning"],
  sin_datos: ["Sin datos", "warning"],
};

export default function DomainApplicability({ context, capability }) {
  const state = applicability(context, capability);
  const [label, tone] = presentation[state] || [state.replaceAll("_", " "), "neutral"];
  return <div className="flex flex-wrap items-center gap-3"><span className="text-sm font-bold text-[var(--text-secondary)]">Aplicabilidad de obra</span><StatusBadge tone={tone}>{label}</StatusBadge>{state === "no_aplica" && <Alert tone="info">Este dominio está marcado como no aplicable para la obra.</Alert>}</div>;
}
