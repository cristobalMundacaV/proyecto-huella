const defaultItems = [
  { label: "Presets disponibles", status: "manual", detail: "Validar en entorno local" },
  { label: "Empresa con preset activo", status: "manual", detail: "Validar en entorno local" },
  { label: "Dashboard adaptativo", status: "manual", detail: "Validar en entorno local" },
  { label: "Modulos operativos", status: "manual", detail: "Validar en entorno local" },
  { label: "Reportes adaptativos", status: "manual", detail: "Validar en entorno local" },
  { label: "Evidencias adaptativas", status: "manual", detail: "Validar en entorno local" },
  { label: "Factores adaptativos", status: "manual", detail: "Validar en entorno local" },
  { label: "Importaciones adaptativas", status: "manual", detail: "Validar en entorno local" },
  { label: "Build frontend", status: "pending", detail: "Pendiente de validacion local" },
  { label: "Lint frontend", status: "pending", detail: "Pendiente de validacion local" },
  { label: "Migraciones backend", status: "pending", detail: "Pendiente de validacion local" },
  { label: "Check backend", status: "pending", detail: "Pendiente de validacion local" },
  { label: "Pendientes conocidos documentados", status: "manual", detail: "Validar contra documento de cierre" },
];

function SystemClosureChecklist({ items = defaultItems }) {
  const normalizedItems = items.map(normalizeItem);

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)]">
      <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">Cierre tecnico</p>
      <h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">Refactor incremental nucleo + presets</h2>
      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {normalizedItems.map((item) => (
          <div key={item.label} className={`rounded-2xl border p-4 text-sm font-black ${getStatusClass(item.status)}`}>
            {getStatusLabel(item.status)} - {item.label}
            {item.detail && <p className="mt-2 text-xs font-semibold opacity-80">{item.detail}</p>}
          </div>
        ))}
      </div>
    </section>
  );
}

function normalizeItem(item) {
  if (Array.isArray(item)) {
    return {
      label: item[0],
      status: item[1] ? "ok" : "pending",
      detail: item[2] || "",
    };
  }

  return {
    label: item.label,
    status: item.status || "pending",
    detail: item.detail || "",
  };
}

function getStatusLabel(status) {
  if (status === "ok") return "OK";
  if (status === "blocked") return "Bloqueado";
  if (status === "manual") return "Manual";
  return "Pendiente";
}

function getStatusClass(status) {
  if (status === "ok") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "blocked") return "border-red-200 bg-red-50 text-red-700";
  return "border-amber-200 bg-amber-50 text-amber-700";
}

export default SystemClosureChecklist;
