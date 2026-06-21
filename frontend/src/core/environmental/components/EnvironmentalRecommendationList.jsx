import EnvironmentalRecommendationCard from "./EnvironmentalRecommendationCard";

function EnvironmentalRecommendationList({ recommendations = [] }) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-black text-[var(--text-main)]">Recomendaciones tecnicas ambientales</h2>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Diagnosticos generados desde KPIs, alertas, variables, documentos y fuentes de emision. Solo lectura.
        </p>
      </div>

      {!recommendations.length && (
        <div className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
          <p className="text-sm text-[var(--text-muted)]">No hay recomendaciones tecnicas con evidencia suficiente.</p>
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        {recommendations.map((recommendation) => (
          <EnvironmentalRecommendationCard key={recommendation.id} recommendation={recommendation} />
        ))}
      </div>
    </section>
  );
}

export default EnvironmentalRecommendationList;
