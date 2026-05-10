function KpiCard({ detail, icon, title, tone, value }) {
  const toneClasses = tone
    ? `${tone.background} ${tone.border}`
    : "bg-slate-900 border-slate-800";

  return (
    <div className={`rounded-3xl border p-6 shadow-xl ${toneClasses}`}>
      <div className="mb-4 flex items-center gap-3">
        <div className="text-emerald-400">{icon}</div>
        <p className="text-sm text-slate-400">{title}</p>
      </div>
      <h3 className={`text-2xl font-bold mt-1 ${tone?.color || ""}`}>
        {value}
      </h3>
      {detail && (
        <p className={`mt-2 text-sm font-semibold ${tone?.color}`}>
          {detail}
        </p>
      )}
    </div>
  );
}

export default KpiCard;
