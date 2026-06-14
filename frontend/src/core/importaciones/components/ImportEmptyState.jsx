function ImportEmptyState({ message }) {
  return (
    <section className="rounded-3xl border border-dashed border-[var(--border)] bg-[var(--bg-card)] p-8 text-center shadow-[var(--shadow-card)]">
      <h2 className="text-2xl font-black text-[var(--text-main)]">Sin importacion cargada</h2>
      <p className="mx-auto mt-3 max-w-2xl text-sm font-semibold leading-7 text-[var(--text-muted)]">{message}</p>
    </section>
  );
}

export default ImportEmptyState;
