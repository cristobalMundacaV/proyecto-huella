function ReportFiltersModal({
  draftFilters,
  groupingOptions = [],
  onApply,
  onChange,
  onClear,
  onClose,
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 backdrop-blur-sm">
      <div className="w-full max-w-xl rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-2xl">
        <div className="mb-5 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--secondary)]">Filtros</p>
            <h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">Configurar reporte</h2>
          </div>
          <button onClick={onClose} className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-xs font-bold text-[var(--text-muted)]">
            Cerrar
          </button>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <label className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
            Fecha inicio
            <input
              type="date"
              value={draftFilters.fecha_inicio}
              onChange={(event) => onChange({ ...draftFilters, fecha_inicio: event.target.value })}
              className="mt-2 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)]"
            />
          </label>

          <label className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
            Fecha fin
            <input
              type="date"
              value={draftFilters.fecha_fin}
              onChange={(event) => onChange({ ...draftFilters, fecha_fin: event.target.value })}
              className="mt-2 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)]"
            />
          </label>

          <label className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
            Agrupacion
            <select
              value={draftFilters.agrupacion}
              onChange={(event) => onChange({ ...draftFilters, agrupacion: event.target.value })}
              className="mt-2 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)]"
            >
              {groupingOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <button onClick={onClear} className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-5 py-3 text-sm font-bold text-[#475467]">
            Limpiar
          </button>
          <button onClick={onApply} className="rounded-xl bg-[var(--primary-dark)] px-5 py-3 text-sm font-black text-white">
            Aplicar filtros
          </button>
        </div>
      </div>
    </div>
  );
}

export default ReportFiltersModal;
