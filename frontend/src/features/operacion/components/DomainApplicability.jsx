import {
  CheckCircle2,
  CircleHelp,
  CircleOff,
} from "lucide-react";

import {
  StatusBadge,
} from "@/shared/ui";

import {
  applicability,
} from "../utils/operationSelectors";

const presentation = {
  aplica: {
    label: "Aplica",
    tone: "success",
    icon: CheckCircle2,
    description: "Este ámbito forma parte de la operación ambiental de esta obra.",
  },

  no_aplica: {
    label: "No aplica",
    tone: "neutral",
    icon: CircleOff,
    description: "Este ámbito está marcado como no aplicable para esta obra.",
  },

  pendiente: {
    label: "Por definir",
    tone: "warning",
    icon: CircleHelp,
    description: "Aún falta información para determinar si este ámbito aplica a la obra.",
  },

  no_determinado: {
    label: "Por definir",
    tone: "warning",
    icon: CircleHelp,
    description: "Aún falta información para determinar si este ámbito aplica a la obra.",
  },

  sin_datos: {
    label: "Sin información",
    tone: "neutral",
    icon: CircleHelp,
    description: "Todavía no existe información suficiente sobre la aplicabilidad de este ámbito.",
  },
};

export default function DomainApplicability({
  context,
  capability,
}) {
  const state =
    applicability(
      context,
      capability
    );

  const config =
    presentation[state] || {
      label: String(state).replaceAll("_", " "),
      tone: "neutral",
      icon: CircleHelp,
      description: "Estado de aplicabilidad disponible para este ámbito.",
    };

  const Icon =
    config.icon;

  return (
    <div
      className="
        flex
        flex-col
        gap-3
        rounded-[20px]
        border
        border-[var(--border-subtle)]
        bg-white
        p-4
        shadow-[0_8px_24px_rgba(15,23,42,0.04)]
        sm:flex-row
        sm:items-center
        sm:justify-between
      "
    >
      <div className="flex min-w-0 items-start gap-3">
        <div
          className="
            flex
            h-10
            w-10
            shrink-0
            items-center
            justify-center
            rounded-xl
            bg-[var(--bg-surface-subtle)]
            text-[var(--brand-primary)]
          "
        >
          <Icon
            aria-hidden="true"
            size={18}
          />
        </div>

        <div className="min-w-0">
          <p className="text-sm font-black text-[var(--text-primary)]">
            Aplicabilidad
          </p>

          <p className="mt-1 text-sm leading-5 text-[var(--text-muted)]">
            {config.description}
          </p>
        </div>
      </div>

      <div className="shrink-0">
        <StatusBadge tone={config.tone}>
          {config.label}
        </StatusBadge>
      </div>
    </div>
  );
}