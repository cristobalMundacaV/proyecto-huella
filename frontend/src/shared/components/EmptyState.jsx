function EmptyState({ title = "Sin datos", description = "No hay informacion para mostrar." }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-6 text-center">
      <p className="font-semibold text-slate-100">{title}</p>
      <p className="mt-2 text-sm text-slate-400">{description}</p>
    </div>
  );
}

export default EmptyState;
