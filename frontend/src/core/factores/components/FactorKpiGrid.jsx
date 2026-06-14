const toneMap = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  info: "border-sky-200 bg-sky-50 text-sky-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  danger: "border-rose-200 bg-rose-50 text-rose-700",
  neutral: "border-slate-200 bg-white text-slate-700",
};

function FactorKpiGrid({ kpis = [] }) {
  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {kpis.map((kpi) => (
        <article key={kpi.label} className={`rounded-3xl border p-5 shadow-[0_14px_35px_var(--shadow)] ${toneMap[kpi.tone] || toneMap.neutral}`}>
          <p className="text-xs font-black uppercase tracking-wide opacity-80">{kpi.label}</p>
          <p className="mt-3 break-words text-3xl font-black">{kpi.value}</p>
        </article>
      ))}
    </section>
  );
}

export default FactorKpiGrid;
