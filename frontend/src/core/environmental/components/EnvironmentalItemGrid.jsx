function EnvironmentalItemGrid({ title, description, items = [], icon: Icon, tone = "emerald" }) {
  const toneClass = {
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-800",
    amber: "border-amber-200 bg-amber-50 text-amber-800",
    red: "border-red-200 bg-red-50 text-red-800",
    blue: "border-blue-200 bg-blue-50 text-blue-800",
    slate: "border-slate-200 bg-slate-50 text-slate-700",
  }[tone];

  return (
    <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-start gap-3">
        {Icon && (
          <span className={`rounded-xl border p-2 ${toneClass}`}>
            <Icon size={18} />
          </span>
        )}
        <div>
          <h2 className="text-lg font-black text-[var(--text-main)]">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">{description}</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {items.map((item) => (
          <div key={item} className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
            <p className="text-sm font-bold text-[var(--text-main)]">{item}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default EnvironmentalItemGrid;
