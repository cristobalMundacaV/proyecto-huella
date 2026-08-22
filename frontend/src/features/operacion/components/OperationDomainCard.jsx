import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

import {
  StatusBadge,
} from "@/shared/ui";

import {
  domainStateInfo,
} from "../utils/operationSelectors";
import { getEnvironmentalDomain } from "@/shared/config/environmentalDomains";

const stateStyles = {
  con_datos: {
    container:
      "border-emerald-200 bg-[linear-gradient(135deg,rgba(236,253,245,0.96),rgba(255,255,255,0.98))]",
    icon:
      "bg-emerald-100 text-emerald-700",
  },

  requiere_revision: {
    container:
      "border-amber-200 bg-[linear-gradient(135deg,rgba(255,251,235,0.96),rgba(255,255,255,0.98))]",
    icon:
      "bg-amber-100 text-amber-700",
  },

  sin_datos: {
    container:
      "border-slate-200 bg-white",
    icon:
      "bg-slate-100 text-slate-600",
  },

  no_aplica: {
    container:
      "border-slate-200 bg-slate-50/70",
    icon:
      "bg-slate-100 text-slate-500",
  },

  sin_configurar: {
    container:
      "border-amber-100 bg-[linear-gradient(135deg,rgba(255,251,235,0.72),rgba(255,255,255,0.98))]",
    icon:
      "bg-amber-50 text-amber-700",
  },

  error: {
    container:
      "border-rose-200 bg-[linear-gradient(135deg,rgba(255,241,242,0.82),rgba(255,255,255,0.98))]",
    icon:
      "bg-rose-100 text-rose-700",
  },
};

export default function OperationDomainCard({
  icon: Icon,
  title,
  state,
  signal,
  detail,
  to,
  domainKey,
  compact = false,
}) {
  const status = domainStateInfo(state);

  const identity = getEnvironmentalDomain(domainKey);
  const domainVisual = identity ? {
    container: `${identity.border} bg-gradient-to-br ${identity.accent}`,
    icon: `${identity.softBg} ${identity.text}`,
  } : null;
  const visual = state === "con_datos" && domainVisual ? domainVisual : stateStyles[state] || domainVisual || stateStyles.sin_datos;
  const actionColor = identity?.text || "text-emerald-700";

  if (compact) {
    return (
      <article
        className={`
          group
          rounded-[20px]
          border
          p-4
          shadow-[0_8px_22px_rgba(15,23,42,0.04)]
          transition
          duration-200
          hover:-translate-y-0.5
          hover:shadow-[0_14px_30px_rgba(15,23,42,0.07)]
          ${visual.container}
        `}
      >
        <div className="flex items-center gap-4">
          <div
            className={`
              flex
              h-11
              w-11
              shrink-0
              items-center
              justify-center
              rounded-xl
              ${visual.icon}
            `}
          >
            <Icon
              aria-hidden="true"
              size={20}
            />
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-black text-[var(--text-primary)]">
                {title}
              </h3>

              <StatusBadge tone={status.tone}>
                {status.label}
              </StatusBadge>
            </div>

            <p className="mt-1 text-sm leading-5 text-[var(--text-secondary)]">
              {signal || status.description}
            </p>

            {detail && (
              <p className="mt-1 text-xs text-[var(--text-muted)]">
                {detail}
              </p>
            )}
          </div>

          <Link
            to={to}
            aria-label={`Ver ${title}`}
            className={`
              flex
              h-10
              w-10
              shrink-0
              items-center
              justify-center
              rounded-full
              border
              ${identity?.border || "border-emerald-200"}
              ${identity?.softBg || "bg-emerald-50"}
              ${identity?.text || "text-emerald-700"}
              transition
              duration-200
              group-hover:border-emerald-700
              group-hover:bg-emerald-700
              group-hover:text-white
              focus-visible:outline-none
              focus-visible:shadow-[var(--focus-ring)]
            `}
          >
            <ArrowRight
              aria-hidden="true"
              size={17}
            />
          </Link>
        </div>
      </article>
    );
  }

  return (
    <article
      className={`
        flex
        h-full
        flex-col
        rounded-[22px]
        border
        p-5
        shadow-[0_10px_28px_rgba(15,23,42,0.05)]
        transition
        duration-200
        hover:-translate-y-0.5
        hover:shadow-[0_16px_34px_rgba(15,23,42,0.08)]
        ${visual.container}
      `}
    >
      <div className="flex items-start justify-between gap-3">
        <div
          className={`
            flex
            h-11
            w-11
            items-center
            justify-center
            rounded-xl
            ${visual.icon}
          `}
        >
          <Icon
            aria-hidden="true"
            size={20}
          />
        </div>

        <StatusBadge tone={status.tone}>
          {status.label}
        </StatusBadge>
      </div>

      <h3 className="mt-4 text-lg font-black text-[var(--text-primary)]">
        {title}
      </h3>

      <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
        {signal || status.description}
      </p>

      {detail && (
        <p className="mt-2 text-xs text-[var(--text-muted)]">
          {detail}
        </p>
      )}

      <Link
        to={to}
        className={`
          mt-auto
          flex
          items-center
          justify-between
          pt-5
          text-sm
          font-black
          ${actionColor}
          focus-visible:outline-none
          focus-visible:shadow-[var(--focus-ring)]
        `}
      >
        Explorar dominio

        <ArrowRight
          aria-hidden="true"
          size={16}
        />
      </Link>
    </article>
  );
}
