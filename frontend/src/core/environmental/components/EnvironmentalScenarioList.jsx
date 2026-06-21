import EnvironmentalScenarioCard from "./EnvironmentalScenarioCard";

function EnvironmentalScenarioList({ scenarios = [] }) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-black text-[var(--text-main)]">Simulador de impacto ambiental</h2>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Escenarios tecnicos calculados con datos reales. No editan registros ni crean acciones.
        </p>
      </div>

      {!scenarios.length && (
        <div className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
          <p className="text-sm text-[var(--text-muted)]">No hay escenarios disponibles con la informacion actual.</p>
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        {scenarios.map((scenario) => (
          <EnvironmentalScenarioCard key={scenario.id} scenario={scenario} />
        ))}
      </div>
    </section>
  );
}

export default EnvironmentalScenarioList;
