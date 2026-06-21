import EnvironmentalKpiCard from "./EnvironmentalKpiCard";

function EnvironmentalKpiGrid({ kpis = [] }) {
  if (!kpis.length) {
    return (
      <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
        <h2 className="text-lg font-black text-[var(--text-main)]">KPIs ambientales reales</h2>
        <p className="mt-2 text-sm text-[var(--text-muted)]">Requiere registros, documentos o variables ambientales para calcular indicadores.</p>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-black text-[var(--text-main)]">KPIs ambientales reales</h2>
        <p className="mt-1 text-sm text-[var(--text-muted)]">Indicadores calculados desde registros, documentos, variables y alertas persistidas.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {kpis.map((kpi) => (
          <EnvironmentalKpiCard key={kpi.id} kpi={kpi} />
        ))}
      </div>
    </section>
  );
}

export default EnvironmentalKpiGrid;
