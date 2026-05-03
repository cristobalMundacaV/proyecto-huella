function Tabs({ activeTab, onChange, tabs = [] }) {
  return (
    <div className="flex flex-wrap gap-2 rounded-3xl border border-slate-800 bg-slate-900 p-2">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          type="button"
          onClick={() => onChange(tab.value)}
          className={`rounded-2xl px-4 py-2 text-sm font-bold transition ${
            activeTab === tab.value
              ? "bg-emerald-400/10 text-emerald-200"
              : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export default Tabs;
