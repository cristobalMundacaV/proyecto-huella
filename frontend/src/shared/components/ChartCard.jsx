function ChartCard({ children, title }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <h2 className="mb-4 text-xl font-bold text-[var(--text-main)]">{title}</h2>
      {children}
    </div>
  );
}

export default ChartCard;
