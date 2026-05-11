function KpiCard({ detail, icon, title, tone, value }) {
  const toneClasses = tone
    ? `${tone.background} ${tone.border}`
    : "bg-[var(--bg-card)] border-[var(--border)]";

  return (
    <div className={`rounded-2xl border p-6 shadow-[var(--shadow-card)] ring-1 ring-white/45 ${toneClasses}`}>
      <div className="mb-4 flex items-center gap-3">
        <div className={tone?.color || "text-[var(--primary)]"}>{icon}</div>
        <p className="text-sm text-[var(--text-muted)]">{title}</p>
      </div>
      <h3 className={`mt-1 text-2xl font-bold ${tone?.color || "text-[var(--text-main)]"}`}>
        {value}
      </h3>
      {detail && (
        <p className={`mt-2 text-sm font-semibold ${tone?.color || "text-[var(--text-muted)]"}`}>
          {detail}
        </p>
      )}
    </div>
  );
}

export default KpiCard;
