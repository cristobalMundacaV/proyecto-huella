import { formatNumber } from "@/shared/utils/formatters";

const labels = [
  ["total", "Filas"],
  ["validas", "Validas"],
  ["errores", "Errores"],
  ["advertencias", "Advertencias"],
  ["factores_encontrados", "Factores encontrados"],
  ["factores_faltantes", "Factores faltantes"],
  ["listos", "Listos para crear"],
  ["duplicados", "Posibles duplicados"],
];

function ImportValidationSummary({ summary }) {
  return (
    <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {labels.map(([key, label]) => (
        <div key={key} className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-center shadow-[var(--shadow-soft)]">
          <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
          <p className="mt-2 text-2xl font-black text-[var(--text-main)]">{formatNumber(summary?.[key] || 0, 0)}</p>
        </div>
      ))}
    </section>
  );
}

export default ImportValidationSummary;
