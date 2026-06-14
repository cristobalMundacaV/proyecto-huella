function ImportCloseChecklist({ items }) {
  return (
    <section className="rounded-3xl border border-emerald-200 bg-emerald-50 p-5 shadow-[var(--shadow-card)]">
      <h2 className="text-xl font-black text-emerald-800">Checklist de cierre</h2>
      <div className="mt-4 grid gap-2 md:grid-cols-2">
        {items.map((item) => (
          <div key={item} className="rounded-2xl border border-emerald-200 bg-white/75 p-3 text-sm font-bold text-emerald-800">
            {item}
          </div>
        ))}
      </div>
    </section>
  );
}

export default ImportCloseChecklist;
