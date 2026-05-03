const tabs = [
  ["resumen", "Resumen"],
  ["actividades", "Actividades"],
  ["pasaporte", "Pasaporte"],
  ["evidencias", "Evidencias"],
  ["transporte", "Transporte"],
  ["historial", "Historial"],
];

function LoteTabs({ activeTab, onTabChange }) {
  return (
    <div className="overflow-x-auto rounded-3xl border border-slate-800 bg-slate-900 p-2">
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
                  ? "border border-emerald-400/20 bg-emerald-400/10 text-emerald-200"
                  : "border border-transparent text-slate-400 hover:bg-slate-800 hover:text-slate-200"
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
