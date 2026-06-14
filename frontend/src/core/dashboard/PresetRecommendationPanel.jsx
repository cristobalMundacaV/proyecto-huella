import { Lightbulb } from "lucide-react";

function PresetRecommendationPanel({ recommendation }) {
  return (
    <section className="rounded-[28px] border border-emerald-200 bg-[linear-gradient(180deg,rgba(236,253,245,0.94),rgba(255,255,255,0.99))] p-5 shadow-[var(--shadow-premium)] sm:p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <p className="inline-flex items-center gap-2 text-xs font-black uppercase tracking-[0.22em] text-emerald-700">
            <Lightbulb size={16} />
            Recomendacion
          </p>
          <h2 className="mt-2 text-2xl font-black text-[var(--text-main)]">{recommendation.title}</h2>
          <p className="mt-2 text-sm font-semibold leading-6 text-[var(--text-muted)]">
            {recommendation.description}
          </p>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
        {(recommendation.actions || []).map((action, index) => (
          <div key={action} className="rounded-2xl border border-emerald-200 bg-white/80 p-4">
            <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
              Paso {index + 1}
            </p>
            <p className="mt-2 text-sm font-bold leading-6 text-[var(--text-main)]">{action}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default PresetRecommendationPanel;
