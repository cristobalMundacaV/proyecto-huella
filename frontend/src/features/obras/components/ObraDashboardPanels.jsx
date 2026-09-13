import { ArrowRight, Lightbulb } from "lucide-react";
import { Link } from "react-router-dom";

import { Card, CardContent } from "@/shared/ui/Card";
import { SectionHeader } from "@/shared/ui/Headers";
import { StatusBadge } from "@/shared/ui/Badge";
import { formatNumber } from "@/shared/utils/formatters";

/** Grid of per-flow cards, each colored/iconed from the same
 * `ENVIRONMENTAL_DOMAINS` registry used across the whole product (sidebar,
 * operación pages, reports) — never a page-local color choice. */
export function FlowStatusGrid({ flows = [] }) {
  const withData = flows.filter((flow) => flow.value !== null && flow.value !== undefined);

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {flows.map((flow) => {
        const Icon = flow.icon;
        const hasValue = flow.value !== null && flow.value !== undefined;

        return (
          <Link
            className={`group rounded-[20px] border ${flow.border || "border-slate-200"} ${flow.softBg || "bg-white"} p-4 shadow-[0_8px_22px_rgba(15,23,42,0.05)] transition hover:shadow-md`}
            key={flow.key}
            to={flow.href}
          >
            <div className="flex items-center justify-between gap-2">
              <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white/70 ${flow.text || "text-slate-700"}`}>
                {Icon && <Icon aria-hidden="true" size={18} />}
              </span>

              <StatusBadge tone={hasValue ? "success" : "neutral"}>
                {hasValue ? "Con datos" : "Sin datos"}
              </StatusBadge>
            </div>

            <p className={`mt-3 text-xs font-black uppercase tracking-[0.1em] ${flow.text || "text-slate-700"}`}>
              {flow.label}
            </p>

            <p className="mt-1 text-xl font-black text-[var(--text-primary)]">
              {hasValue ? formatNumber(flow.value) : "Sin datos"}
              {hasValue && flow.unit && <span className="ml-1 text-sm font-bold text-[var(--text-secondary)]">{flow.unit}</span>}
            </p>

            <span className="mt-3 inline-flex items-center gap-1 text-xs font-black text-[var(--text-secondary)] group-hover:text-[var(--brand-primary)]">
              Ver detalle <ArrowRight aria-hidden="true" size={13} />
            </span>
          </Link>
        );
      })}

      {!withData.length && (
        <p className="col-span-full rounded-[18px] border border-dashed border-slate-200 bg-slate-50/60 p-4 text-sm text-[var(--text-muted)]">
          Todavía no hay consumo físico registrado en ningún flujo para este período.
        </p>
      )}
    </div>
  );
}

const REASON_LABEL = { rule: "Regla aplicada", observed: "Valor observado", threshold: "Umbral" };

function ReasonChips({ reason }) {
  const entries = Object.entries(reason || {}).filter(([, value]) => value !== null && value !== undefined && value !== "");
  if (!entries.length) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {entries.map(([key, value]) => (
        <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-[var(--text-muted)]" key={key}>
          {REASON_LABEL[key] || key}: <span className="text-[var(--text-secondary)]">{String(value)}</span>
        </span>
      ))}
    </div>
  );
}

/** "Recomendaciones para esta obra" — every card is a verbatim rendering of
 * a backend `DiagnosticFinding` (AI-INTELLIGENCE-03): the LLM/frontend adds
 * no claim, no severity, no recommendation text of its own. */
export function AiRecommendationsPanel({ recommendations = [], pendientes = [] }) {
  if (!recommendations.length && !pendientes.length) {
    return (
      <Card className="border-emerald-200 bg-[linear-gradient(135deg,rgba(236,253,245,0.9),rgba(255,255,255,0.98))]">
        <CardContent>
          <SectionHeader
            description="El motor de diagnóstico no encontró hallazgos relevantes para este período con la información disponible."
            title="Sin recomendaciones pendientes"
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <SectionHeader
          description="Priorizadas por el motor de diagnóstico determinista (AI-INTELLIGENCE-03) a partir de variación, concentración, evidencia y calidad del dato."
          title="Recomendaciones para esta obra"
        />

        <div className="space-y-3">
          {recommendations.map((item) => (
            <article className="rounded-[18px] border border-slate-200 bg-slate-50/60 p-4" key={item.key}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white text-amber-600 shadow-sm">
                    <Lightbulb aria-hidden="true" size={16} />
                  </span>

                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge tone={item.tone}>{item.priorityLabel}</StatusBadge>
                      <h3 className="font-black text-[var(--text-primary)]">{item.title}</h3>
                    </div>

                    <p className="mt-1.5 max-w-3xl text-sm leading-6 text-[var(--text-secondary)]">
                      {item.description}
                    </p>

                    {item.recommendations.length > 0 && (
                      <ul className="mt-2 space-y-1">
                        {item.recommendations.map((rec) => (
                          <li className="flex gap-2 text-sm text-[var(--text-secondary)]" key={rec}>
                            <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-emerald-600" />
                            {rec}
                          </li>
                        ))}
                      </ul>
                    )}

                    <ReasonChips reason={item.reason} />
                  </div>
                </div>

                <Link
                  className="inline-flex shrink-0 items-center gap-1 text-xs font-black text-[var(--brand-primary)]"
                  to={item.href}
                >
                  Ver detalle <ArrowRight aria-hidden="true" size={13} />
                </Link>
              </div>
            </article>
          ))}
        </div>

        {pendientes.length > 0 && (
          <div className="mt-4 rounded-[18px] border border-amber-200 bg-amber-50/60 p-4">
            <p className="text-xs font-black uppercase tracking-[0.12em] text-amber-800">
              Pendientes para el cierre del período
            </p>
            <ul className="mt-2 space-y-1">
              {pendientes.map((item) => (
                <li className="flex gap-2 text-sm text-amber-900" key={item}>
                  <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-amber-600" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
