const defaultItems = [
  ["Presets disponibles", true],
  ["Empresa con preset activo", true],
  ["Dashboard adaptativo", true],
  ["Modulos operativos", true],
  ["Reportes adaptativos", true],
  ["Evidencias adaptativas", true],
  ["Factores adaptativos", true],
  ["Importaciones adaptativas", true],
  ["Build frontend", true],
  ["Check backend", true],
  ["Pendientes conocidos documentados", true],
];

function SystemClosureChecklist({ items = defaultItems }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)]">
      <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">Cierre tecnico</p>
      <h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">Refactor incremental núcleo + presets</h2>
      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {items.map(([label, done]) => (
          <div key={label} className={`rounded-2xl border p-4 text-sm font-black ${done ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-700"}`}>
            {done ? "OK" : "Pendiente"} · {label}
          </div>
        ))}
      </div>
    </section>
  );
}

export default SystemClosureChecklist;
