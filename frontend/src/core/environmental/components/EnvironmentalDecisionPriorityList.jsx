import EnvironmentalDecisionPriorityCard from "./EnvironmentalDecisionPriorityCard";

function EnvironmentalDecisionPriorityList({ createdActionIds = [], onConvertToAction, priorities = [], workingPriorityId = "" }) {
  const createdSet = new Set(createdActionIds);

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-black text-[var(--text-main)]">Decisiones ambientales priorizadas</h2>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Ranking tecnico desde KPIs, recomendaciones, escenarios, alertas y documentos. Solo lectura.
        </p>
      </div>

      {!priorities.length && (
        <div className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
          <p className="text-sm text-[var(--text-muted)]">No hay decisiones priorizadas con la informacion actual.</p>
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        {priorities.map((priority) => (
          <EnvironmentalDecisionPriorityCard
            key={priority.id}
            created={createdSet.has(priority.id)}
            onConvertToAction={() => onConvertToAction?.(priority)}
            priority={priority}
            working={workingPriorityId === priority.id}
          />
        ))}
      </div>
    </section>
  );
}

export default EnvironmentalDecisionPriorityList;
