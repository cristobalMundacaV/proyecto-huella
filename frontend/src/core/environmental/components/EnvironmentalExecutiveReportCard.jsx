import { AlertTriangle, CheckCircle2, ClipboardList, FileCheck2, TrendingDown } from "lucide-react";

function EnvironmentalExecutiveReportCard({ report }) {
  if (!report) return null;

  const summary = report.executive_summary || {};
  const readiness = report.readiness || {};
  const baseline = report.baseline || {};
  const decisions = report.decision_agenda || [];
  const scenarios = report.impact_scenarios || [];
  const actions = report.action_summary || {};
  const traceability = report.document_traceability || {};
  const plan = report.management_plan || [];
  const gaps = report.data_gaps || [];

  return (
    <section className="rounded-3xl border border-emerald-200 bg-white p-5 shadow-[var(--shadow-card)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Informe ejecutivo automatico</p>
          <h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">{summary.headline || report.title}</h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-[var(--text-muted)]">{summary.main_message}</p>
        </div>
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-center">
          <p className="text-xs font-black uppercase tracking-wide text-emerald-700">Preparacion</p>
          <p className="mt-1 text-3xl font-black text-emerald-900">{readiness.score ?? 0}%</p>
          <p className="mt-1 text-xs font-bold text-emerald-800">{readiness.status || "En evaluacion"}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-4">
        <MetricCard label="Huella total" value={formatNumber(baseline.huella_total_tco2e)} suffix="tCO2e" />
        <MetricCard label="Registros" value={baseline.total_registros ?? 0} />
        <MetricCard label="Acciones cerradas" value={actions.completed ?? 0} suffix={`/ ${actions.total ?? 0}`} />
        <MetricCard label="Evidencia" value={`${actions.traceability_pct ?? 0}%`} suffix="trazabilidad" />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_0.9fr]">
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-main)] p-4">
          <div className="flex items-center gap-2">
            <ClipboardList className="text-emerald-700" size={18} />
            <h3 className="text-lg font-black text-[var(--text-main)]">Agenda ejecutiva priorizada</h3>
          </div>
          <p className="mt-1 text-sm text-[var(--text-muted)]">{summary.main_decision}</p>
          <div className="mt-4 space-y-3">
            {decisions.length ? decisions.map((item) => <DecisionItem key={item.id} item={item} />) : <EmptyLine text="Sin decisiones priorizadas para listar." />}
          </div>
        </div>

        <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-main)] p-4">
          <div className="flex items-center gap-2">
            <TrendingDown className="text-emerald-700" size={18} />
            <h3 className="text-lg font-black text-[var(--text-main)]">Impacto esperado</h3>
          </div>
          <p className="mt-1 text-sm text-[var(--text-muted)]">Escenarios calculados para explicar cuanto podria mejorar la gestion.</p>
          <div className="mt-4 space-y-3">
            {scenarios.length ? scenarios.map((item) => <ScenarioItem key={item.id} item={item} />) : <EmptyLine text="Sin escenarios disponibles para este periodo." />}
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-cyan-100 bg-cyan-50/70 p-4">
          <div className="flex items-center gap-2">
            <FileCheck2 className="text-cyan-700" size={18} />
            <h3 className="text-lg font-black text-[var(--text-main)]">Acciones y evidencia</h3>
          </div>
          <p className="mt-2 text-sm leading-6 text-cyan-950">{summary.management_message}</p>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <MiniMetric label="Activas" value={actions.active ?? 0} />
            <MiniMetric label="Vencidas" value={actions.overdue ?? 0} />
            <MiniMetric label="Con evidencia" value={actions.with_evidence ?? 0} />
            <MiniMetric label="Docs validados" value={traceability.documents_validated ?? 0} />
          </div>
        </div>

        <div className="rounded-2xl border border-amber-100 bg-amber-50/70 p-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="text-amber-700" size={18} />
            <h3 className="text-lg font-black text-[var(--text-main)]">Brechas antes de presentar</h3>
          </div>
          <p className="mt-2 text-sm leading-6 text-amber-950">{summary.risk_message}</p>
          <div className="mt-4 space-y-2">
            {gaps.length ? gaps.slice(0, 5).map((item, index) => <EmptyLine key={`${item.label || item}-${index}`} text={item.label || item.reason || String(item)} />) : <EmptyLine text="Sin brechas criticas adicionales detectadas." />}
          </div>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-emerald-100 bg-emerald-50/70 p-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="text-emerald-700" size={18} />
          <h3 className="text-lg font-black text-[var(--text-main)]">Plan de gestion sugerido</h3>
        </div>
        <p className="mt-1 text-sm text-emerald-900">Siguiente paso recomendado: {summary.next_step}</p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {plan.length ? plan.map((item, index) => (
            <div key={`${item.title}-${index}`} className="rounded-2xl border border-emerald-100 bg-white p-3">
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-black uppercase text-emerald-800">{item.priority || "media"}</span>
              <h4 className="mt-3 text-sm font-black text-[var(--text-main)]">{item.title}</h4>
              <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">{item.step}</p>
            </div>
          )) : <EmptyLine text="Sin plan sugerido para este periodo." />}
        </div>
      </div>
    </section>
  );
}

function MetricCard({ label, value, suffix = "" }) {
  return <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-main)] p-4"><p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">{label}</p><p className="mt-2 text-2xl font-black text-[var(--text-main)]">{value} <span className="text-sm text-[var(--text-muted)]">{suffix}</span></p></div>;
}

function MiniMetric({ label, value }) {
  return <div className="rounded-xl border border-white/80 bg-white px-3 py-2"><p className="text-xs font-black uppercase text-slate-500">{label}</p><p className="mt-1 text-xl font-black text-[var(--text-main)]">{value}</p></div>;
}

function DecisionItem({ item }) {
  return <article className="rounded-2xl border border-white bg-white p-3"><div className="flex flex-wrap items-center gap-2"><span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-black uppercase text-emerald-800">#{item.rank || "-"}</span><span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-black uppercase text-amber-800">{item.priority || "media"}</span><span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-black uppercase text-slate-700">score {item.score ?? "-"}</span></div><h4 className="mt-3 text-sm font-black text-[var(--text-main)]">{item.title}</h4><p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">{item.next_step || item.recommended_decision}</p></article>;
}

function ScenarioItem({ item }) {
  const reduction = item.estimated_reduction_tco2e ?? null;
  return <article className="rounded-2xl border border-white bg-white p-3"><div className="flex flex-wrap items-center gap-2"><span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-black uppercase text-emerald-800">{item.status}</span><span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-black uppercase text-slate-700">{item.area || "ambiental"}</span></div><h4 className="mt-3 text-sm font-black text-[var(--text-main)]">{item.title}</h4><p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">Reduccion estimada: {reduction !== null ? `${formatNumber(reduction)} tCO2e` : "requiere datos"}{item.estimated_reduction_pct !== null && item.estimated_reduction_pct !== undefined ? ` · ${item.estimated_reduction_pct}%` : ""}</p></article>;
}

function EmptyLine({ text }) {
  return <p className="rounded-xl border border-dashed border-slate-200 bg-white/80 px-3 py-2 text-xs font-bold text-slate-600">{text}</p>;
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "sin dato";
  const number = Number(value);
  if (Number.isNaN(number)) return String(value);
  return number.toLocaleString("es-CL", { maximumFractionDigits: 2 });
}

export default EnvironmentalExecutiveReportCard;
