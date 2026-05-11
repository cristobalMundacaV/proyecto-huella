function AiAdvisor({
  aiAnalysis,
  aiSource,
  loadingAi,
  onGenerateAnalysis,
}) {
  return (
    <section className="space-y-4 rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-[var(--shadow-card)]">
      <div>
        <p className="text-sm font-bold text-[var(--primary-dark)]">Carbono Zero AI</p>
        <h2 className="text-2xl font-bold text-[var(--text-main)]">
          Analisis estrategico generado por IA
        </h2>
      </div>

      <button
        type="button"
        onClick={onGenerateAnalysis}
        disabled={loadingAi}
        className="rounded-2xl bg-[var(--primary-dark)] px-6 py-3 font-bold text-white transition hover:bg-[var(--primary)] disabled:cursor-not-allowed disabled:bg-[#CBD5D0] disabled:text-[var(--text-muted)]"
      >
        {loadingAi ? "Analizando..." : "Generar analisis IA"}
      </button>

      {aiAnalysis && (
        <div className="whitespace-pre-line rounded-2xl border border-[var(--border)] bg-[var(--info-bg)] p-5 leading-7 text-[var(--text-main)]">
          {aiSource === "carbono_zero_engine" && (
            <p className="mb-4 text-xs font-bold text-[var(--primary-dark)]">
              Generado por motor analitico Carbono Zero
            </p>
          )}
          {aiSource === "openai" && (
            <p className="mb-4 text-xs font-bold text-[#075985]">
              Generado con OpenAI
            </p>
          )}
          {aiAnalysis}
        </div>
      )}
    </section>
  );
}

export default AiAdvisor;
