import { AlertTriangle, CheckCircle2, CircleHelp } from "lucide-react";

function EnvironmentalKpiCard({ kpi }) {
  const isMissing = kpi?.status === "missing";
  const isAlert = kpi?.status === "alert";
  const Icon = isMissing ? CircleHelp : isAlert ? AlertTriangle : CheckCircle2;
  const tone = isMissing
    ? "border-slate-200 bg-slate-50 text-slate-700"
    : isAlert
      ? "border-amber-200 bg-amber-50 text-amber-800"
      : "border-emerald-200 bg-emerald-50 text-emerald-800";

  const value = isMissing || kpi?.value === null || kpi?.value === undefined
    ? "Requiere datos"
    : formatKpiValue(kpi.value);

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-[var(--text-muted)]">{kpi?.label}</p>
          <p className="mt-2 text-2xl font-black text-[var(--text-main)]">
            {value}
            {!isMissing && kpi?.unit && <span className="ml-2 text-sm font-black text-[var(--text-muted)]">{kpi.unit}</span>}
          </p>
        </div>
        <span className={`rounded-xl border p-2 ${tone}`}>
          <Icon size={18} />
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-[var(--text-muted)]">{kpi?.reason}</p>
      <p className="mt-3 text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
        Fuente: {formatSource(kpi?.source)}
      </p>
    </div>
  );
}

function formatKpiValue(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return value;
  return new Intl.NumberFormat("es-CL", { maximumFractionDigits: 2 }).format(number);
}

function formatSource(source = "") {
  return String(source).replaceAll("_", " ") || "calculado";
}

export default EnvironmentalKpiCard;
