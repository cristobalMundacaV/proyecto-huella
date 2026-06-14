function ImportHero({ activeConstructora, config, preset }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[linear-gradient(135deg,rgba(236,253,245,0.95),rgba(255,255,255,0.98))] p-6 shadow-[var(--shadow-premium)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full border border-emerald-200 bg-white px-3 py-1 text-xs font-black uppercase tracking-wide text-emerald-700">{activeConstructora?.nombre || "Empresa activa"}</span>
            <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-black uppercase tracking-wide text-sky-700">Preset: {preset.name}</span>
          </div>
          <h1 className="mt-4 text-3xl font-black text-[var(--text-main)] sm:text-4xl">{config.title}</h1>
          <p className="mt-3 max-w-3xl text-sm font-semibold leading-6 text-[var(--text-muted)]">{config.subtitle}</p>
        </div>
      </div>
    </section>
  );
}

export default ImportHero;
