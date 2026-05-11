function Tabs({ activeTab, onChange, tabs = [] }) {
  return (
    <div className="flex flex-wrap gap-2 rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-2 shadow-[var(--shadow-card)]">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          type="button"
          onClick={() => onChange(tab.value)}
          className={`rounded-2xl px-4 py-2 text-sm font-bold transition ${
            activeTab === tab.value
              ? "border border-[var(--primary)]/25 bg-[var(--success-bg)] text-[var(--primary-dark)]"
              : "border border-transparent text-[var(--text-muted)] hover:bg-[var(--bg-surface)] hover:text-[var(--text-main)]"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export default Tabs;
