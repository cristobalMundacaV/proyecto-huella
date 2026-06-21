import { AlertTriangle, CheckCircle2, Database, FileSearch, UploadCloud } from "lucide-react";

function EnvironmentalIngestionReadinessPanel({ readiness }) {
  if (!readiness) return null;

  const summary = readiness.summary || {};
  const documentCoverage = readiness.document_coverage || [];
  const variableCoverage = readiness.variable_coverage || [];
  const fieldCoverage = readiness.field_coverage || [];
  const nextUploads = readiness.next_uploads || [];
  const blockers = readiness.blockers || [];

  return (
    <section className="rounded-2xl border border-emerald-200 bg-white p-5 shadow-[var(--shadow-card)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Preparacion de ingesta</p>
          <h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">{summary.status || "Ingesta en evaluacion"}</h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-[var(--text-muted)]">
            Esta lectura revisa documentos, variables, campos base y registros para saber si la empresa puede alimentar KPIs, recomendaciones y reportes sin datos falsos.
          </p>
        </div>
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-center">
          <p className="text-xs font-black uppercase tracking-wide text-emerald-700">Score ingesta</p>
          <p className="mt-1 text-3xl font-black text-emerald-900">{summary.score ?? 0}%</p>
          <p className="mt-1 text-xs font-bold text-emerald-800">{summary.documents_total ?? 0} documentos · {summary.variables_total ?? 0} variables</p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-4">
        <MetricCard label="Documentos" value={summary.documents_total ?? 0} icon={FileSearch} />
        <MetricCard label="Variables" value={summary.variables_total ?? 0} icon={Database} />
        <MetricCard label="Evidencias" value={summary.evidences_total ?? 0} icon={CheckCircle2} />
        <MetricCard label="Registros" value={summary.records_total ?? 0} icon={UploadCloud} />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <CoverageBlock title="Cobertura documental" items={documentCoverage} />
        <CoverageBlock title="Variables cubiertas" items={variableCoverage} />
        <CoverageBlock title="Campos base" items={fieldCoverage} />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_0.8fr]">
        <div className="rounded-2xl border border-cyan-100 bg-cyan-50/70 p-4">
          <div className="flex items-center gap-2">
            <UploadCloud className="text-cyan-700" size={18} />
            <h3 className="text-lg font-black text-[var(--text-main)]">Siguiente carga recomendada</h3>
          </div>
          <div className="mt-4 space-y-3">
            {nextUploads.length ? nextUploads.map((item, index) => (
              <article key={`${item.title}-${index}`} className="rounded-2xl border border-cyan-100 bg-white p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-xs font-black uppercase text-cyan-800">{item.type}</span>
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-black uppercase text-slate-700">{item.priority}</span>
                </div>
                <h4 className="mt-3 text-sm font-black text-[var(--text-main)]">{item.title}</h4>
                <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">{item.reason}</p>
              </article>
            )) : <EmptyLine text="Sin cargas recomendadas por ahora." />}
          </div>
        </div>

        <div className="rounded-2xl border border-amber-100 bg-amber-50/70 p-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="text-amber-700" size={18} />
            <h3 className="text-lg font-black text-[var(--text-main)]">Bloqueos de ingesta</h3>
          </div>
          <p className="mt-2 text-sm leading-6 text-amber-950">Brechas que impiden alimentar bien el motor ambiental.</p>
          <div className="mt-4 space-y-2">
            {blockers.length ? blockers.map((item) => <EmptyLine key={item} text={item} />) : <EmptyLine text="Sin bloqueos criticos de ingesta." />}
          </div>
        </div>
      </div>
    </section>
  );
}

function MetricCard({ label, value, icon: Icon }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-main)] p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
        <Icon className="text-emerald-700" size={18} />
      </div>
      <p className="mt-2 text-2xl font-black text-[var(--text-main)]">{value}</p>
    </div>
  );
}

function CoverageBlock({ title, items }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-main)] p-4">
      <h3 className="text-lg font-black text-[var(--text-main)]">{title}</h3>
      <div className="mt-4 space-y-2">
        {items?.length ? items.slice(0, 8).map((item) => (
          <div key={item.key} className="flex items-center justify-between gap-3 rounded-xl border border-white bg-white px-3 py-2">
            <span className="text-xs font-bold text-[var(--text-main)]">{item.label}</span>
            <span className={`rounded-full px-3 py-1 text-xs font-black uppercase ${item.status === "covered" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
              {item.status === "covered" ? "cubierto" : "falta"}
            </span>
          </div>
        )) : <EmptyLine text="Sin criterios definidos." />}
      </div>
    </div>
  );
}

function EmptyLine({ text }) {
  return <p className="rounded-xl border border-dashed border-slate-200 bg-white/80 px-3 py-2 text-xs font-bold text-slate-600">{text}</p>;
}

export default EnvironmentalIngestionReadinessPanel;
