const toneMap = {
  success: {
    card: "border-emerald-200 bg-[linear-gradient(180deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_18px_45px_rgba(15,118,110,0.10)]",
    value: "text-emerald-700",
  },
  info: {
    card: "border-sky-200 bg-[linear-gradient(180deg,rgba(240,249,255,0.98),rgba(255,255,255,0.98))] shadow-[0_18px_45px_rgba(2,132,199,0.08)]",
    value: "text-sky-700",
  },
  warning: {
    card: "border-amber-200 bg-[linear-gradient(180deg,rgba(255,251,235,0.98),rgba(255,255,255,0.98))] shadow-[0_18px_45px_rgba(180,83,9,0.08)]",
    value: "text-amber-700",
  },
  danger: {
    card: "border-rose-200 bg-[linear-gradient(180deg,rgba(255,241,242,0.98),rgba(255,255,255,0.98))] shadow-[0_18px_45px_rgba(190,18,60,0.08)]",
    value: "text-rose-700",
  },
  neutral: {
    card: "border-slate-200 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.98))] shadow-[0_18px_45px_rgba(15,23,42,0.06)]",
    value: "text-slate-900",
  },
};

function FactorKpiGrid({ kpis = [] }) {
  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {kpis.slice(0, 4).map((kpi) => {
        const selectedTone = toneMap[kpi.tone] || toneMap.neutral;

        return (
          <article
            key={kpi.label}
            className={`min-h-[150px] rounded-[28px] border p-5 text-center ring-1 ring-white/70 ${selectedTone.card}`}
          >
            <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-500">
              {kpi.label}
            </p>
            <p className={`mt-4 flex min-h-[56px] items-center justify-center break-words text-3xl font-black leading-tight ${selectedTone.value}`}>
              {kpi.value}
            </p>
          </article>
        );
      })}
    </section>
  );
}

export default FactorKpiGrid;