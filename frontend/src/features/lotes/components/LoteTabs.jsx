const tabs = [
  ["resumen", "Resumen de obra"],
  ["actividades", "Registros de emisión"],
  ["pasaporte", "Ficha"],
  ["evidencias", "Evidencias"],
  ["transporte", "Transporte / logística"],
  ["historial", "Historial"],
];

function LoteTabs({ activeTab, onTabChange }) {
  return (
    <div className="overflow-x-auto rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-2 shadow-[var(--shadow-card)]">
      <div className="flex min-w-max gap-2">
        {tabs.map(([value, label]) => {
          const isActive = activeTab === value;

          return (
            <button
              key={value}
              type="button"
              onClick={() => onTabChange(value)}
              className={`rounded-2xl px-4 py-2 text-sm font-bold transition ${
                isActive
                  ? "border border-[var(--primary)]/25 bg-[var(--success-bg)] text-[var(--primary-dark)]"
                  : "border border-transparent text-[var(--text-muted)] hover:bg-[var(--bg-surface)] hover:text-[var(--text-main)]"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default LoteTabs;
