function EnvironmentalShell({ eyebrow, title, description, children }) {
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <section className="rounded-[var(--radius-xl)] border border-[var(--border)] bg-white/88 p-6 shadow-[var(--shadow-card)] sm:p-7">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">{eyebrow}</p>
        <div className="mt-3 max-w-4xl">
          <h1 className="text-3xl font-black text-[var(--text-main)] sm:text-4xl">{title}</h1>
          <p className="mt-3 text-sm leading-6 text-[var(--text-muted)] sm:text-base">{description}</p>
        </div>
      </section>

      {children}
    </div>
  );
}

export default EnvironmentalShell;
