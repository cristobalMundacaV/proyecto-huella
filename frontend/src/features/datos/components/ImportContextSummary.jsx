export default function ImportContextSummary({ context }) {
  const rows = [
    ["Alcance", context.scopeLabel], ["Obra", context.workName], ["Ámbito", context.domainLabel],
    ["Fuente", context.source], ["Contenido", context.destinationLabel], ["Archivo", context.fileName],
  ].filter(([, value]) => value);
  return <dl className="grid gap-3 rounded-[18px] border border-cyan-200 bg-cyan-50/45 p-4 text-sm sm:grid-cols-2 xl:grid-cols-3">
    {rows.map(([label, value]) => <div key={label}><dt className="text-xs font-black uppercase tracking-wide text-cyan-800">{label}</dt><dd className="mt-1 font-bold text-[var(--text-primary)]">{value}</dd></div>)}
  </dl>;
}
