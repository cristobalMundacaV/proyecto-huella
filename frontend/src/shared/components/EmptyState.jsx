function EmptyState({ title = "Sin datos", description = "No hay informacion para mostrar." }) {
  return (
    <div className="premium-card premium-card-interactive rounded-2xl bg-[var(--bg-surface)] p-6 text-center">
      <p className="font-semibold text-[var(--text-main)]">{title}</p>
      <p className="mt-2 text-sm text-[var(--text-muted)]">{description}</p>
    </div>
  );
}

export default EmptyState;
