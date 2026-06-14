function ImportPresetSelector({ modules = [], selectedModule, onChange }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)]">
      <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">Modulo de importacion</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {modules.map((module) => (
          <button
            key={module.key}
            type="button"
            onClick={() => onChange(module.key)}
            className={`rounded-2xl border p-4 text-left text-sm font-black transition ${
              selectedModule === module.key
                ? "border-[var(--primary)] bg-[var(--success-bg)] text-[var(--primary-dark)]"
                : "border-[var(--border)] bg-[var(--bg-surface)] text-[var(--text-main)]"
            }`}
          >
            {module.label}
            {!module.supported && <p className="mt-1 text-xs font-semibold text-[var(--text-muted)]">Preparado</p>}
          </button>
        ))}
      </div>
    </section>
  );
}

export default ImportPresetSelector;
