function ChartCard({ children, title }) {
  return (
    <div className="rounded-3xl bg-slate-900 border border-slate-800 p-4 sm:p-6 shadow-xl">
      <h2 className="text-xl font-semibold mb-4">{title}</h2>
      {children}
    </div>
  );
}

export default ChartCard;
