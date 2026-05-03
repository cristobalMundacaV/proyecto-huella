function Field({ label, children, error }) {
  return (
    <label className="space-y-2 text-sm">
      <span className="text-slate-300">{label}</span>
      {children}
      {error && <span className="block text-xs text-red-300">{error}</span>}
    </label>
  );
}

function DetailItem({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold text-slate-100">
        {value || "Sin dato"}
      </p>
    </div>
  );
}

export { DetailItem, Field };
