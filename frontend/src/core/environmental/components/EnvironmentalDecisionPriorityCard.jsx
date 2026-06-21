import { CheckCircle2, Loader2, PlusCircle } from "lucide-react";

function EnvironmentalDecisionPriorityCard({ created, onConvertToAction, priority, working }) {
  const priorityTone =
    {
      critica: "border-red-200 bg-red-50 text-red-800",
      alta: "border-orange-200 bg-orange-50 text-orange-800",
      media: "border-amber-200 bg-amber-50 text-amber-800",
      baja: "border-slate-200 bg-slate-50 text-slate-700",
    }[priority.priority] || "border-slate-200 bg-slate-50 text-slate-700";
  const statusTone =
    {
      ready: "border-emerald-200 bg-emerald-50 text-emerald-800",
      requires_data: "border-blue-200 bg-blue-50 text-blue-800",
      monitor: "border-slate-200 bg-slate-50 text-slate-700",
    }[priority.status] || "border-slate-200 bg-slate-50 text-slate-700";

  return (
    <article className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
            #{priority.rank} · {priority.area} · {priority.decision_type}
          </p>
          <h3 className="mt-1 text-lg font-black text-[var(--text-main)]">{priority.title}</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`rounded-full border px-3 py-1 text-xs font-black uppercase ${priorityTone}`}>{priority.priority}</span>
          <span className={`rounded-full border px-3 py-1 text-xs font-black uppercase ${statusTone}`}>{formatStatus(priority.status)}</span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        <Metric label="Score" value={formatPlain(priority.score)} />
        <Metric label="kgCO2e" value={formatImpact(priority.expected_impact?.kg_co2e, "kg")} />
        <Metric label="tCO2e" value={formatImpact(priority.expected_impact?.tco2e, "t")} />
        <Metric label="Reduccion" value={formatImpact(priority.expected_impact?.pct, "%")} />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <TextBlock label="Por que ahora" value={priority.why_now} />
        <TextBlock label="Base tecnica" value={priority.technical_basis} />
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <SmallFact label="Confianza" value={priority.confidence} />
        <SmallFact label="Esfuerzo" value={priority.effort} />
        <SmallFact label="Riesgo" value={priority.expected_impact?.risk_reduction || "sin dato"} />
      </div>

      {!!priority.evidence?.length && (
        <div className="mt-4">
          <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">Evidencia</p>
          <ul className="mt-2 space-y-2">
            {priority.evidence.slice(0, 3).map((item) => (
              <li key={item} className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-muted)]">
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <TextBlock label="Decision recomendada" value={priority.recommended_decision} />
        <TextBlock label="Siguiente paso" value={priority.next_step} />
      </div>

      <div className="mt-5 border-t border-slate-100 pt-4">
        <DecisionActionControl
          created={created || priority.action_created}
          onConvertToAction={onConvertToAction}
          status={priority.status}
          working={working}
        />
      </div>
    </article>
  );
}

function DecisionActionControl({ created, onConvertToAction, status, working }) {
  if (created) {
    return (
      <p className="inline-flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-black text-emerald-800">
        <CheckCircle2 size={17} />
        Accion creada y en seguimiento
      </p>
    );
  }
  if (status === "requires_data") {
    return <p className="text-sm font-bold text-blue-800">Requiere datos antes de crear accion</p>;
  }
  if (status === "monitor") {
    return <p className="text-sm font-bold text-slate-700">Monitorear antes de accionar</p>;
  }
  return (
    <button
      type="button"
      onClick={onConvertToAction}
      disabled={working}
      className="inline-flex items-center gap-2 rounded-2xl bg-[var(--primary)] px-4 py-3 text-sm font-black text-white shadow-[0_14px_30px_rgba(15,124,109,0.18)] hover:bg-[var(--primary-dark)] disabled:opacity-60"
    >
      {working ? <Loader2 className="animate-spin" size={17} /> : <PlusCircle size={17} />}
      {working ? "Preparando..." : "Convertir en accion"}
    </button>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-3">
      <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 text-lg font-black text-[var(--text-main)]">{value}</p>
    </div>
  );
}

function TextBlock({ label, value }) {
  return (
    <div>
      <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 text-sm leading-6 text-[var(--text-main)]">{value || "Requiere datos"}</p>
    </div>
  );
}

function SmallFact({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
      <p className="text-xs font-black uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-black text-slate-800">{value}</p>
    </div>
  );
}

function formatImpact(value, unit) {
  if (value === null || value === undefined) return "Requiere datos";
  const number = Number(value);
  if (!Number.isFinite(number)) return value;
  return `${new Intl.NumberFormat("es-CL", { maximumFractionDigits: 2 }).format(number)} ${unit}`;
}

function formatPlain(value) {
  if (value === null || value === undefined) return "Requiere datos";
  const number = Number(value);
  if (!Number.isFinite(number)) return value;
  return new Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 }).format(number);
}

function formatStatus(status) {
  return (
    {
      ready: "lista",
      requires_data: "requiere datos",
      monitor: "monitorear",
    }[status] || status
  );
}

export default EnvironmentalDecisionPriorityCard;
