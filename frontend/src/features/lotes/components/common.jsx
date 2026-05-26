function Field({ label, children, error }) {
  return (
    <label className="space-y-2 text-sm">
      <span className="font-medium text-[var(--text-muted)]">{label}</span>
      {children}
      {error && <span className="block text-xs font-semibold text-[#B42318]">{error}</span>}
    </label>
  );
}

function DetailItem({ label, value }) {
  return (
    <div className="premium-card p-4">
      <p className="text-xs font-medium text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold text-[var(--text-main)]">
        {value || "Sin dato"}
      </p>
    </div>
  );
}

export { DetailItem, Field };
