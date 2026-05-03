function AiAdvisor({
  aiAnalysis,
  aiSource,
  loadingAi,
  onGenerateAnalysis,
}) {
  return (
    <section className="rounded-3xl bg-slate-900 border border-slate-800 p-6 space-y-4 shadow-xl">
      <div>
        <p className="text-emerald-400 text-sm font-semibold">Huella AI</p>
        <h2 className="text-2xl font-bold">
          Analisis estrategico generado por IA
        </h2>
      </div>

      <button
        type="button"
        onClick={onGenerateAnalysis}
        disabled={loadingAi}
        className="px-6 py-3 rounded-2xl bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400 transition disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
      >
        {loadingAi ? "Analizando..." : "Generar analisis IA"}
      </button>

      {aiAnalysis && (
        <div className="rounded-2xl bg-cyan-400/10 border border-cyan-400/20 p-5 whitespace-pre-line text-slate-200 leading-7">
          {aiSource === "huella_engine" && (
            <p className="mb-4 text-xs font-semibold text-emerald-300">
              Generado por motor analitico Huella
            </p>
          )}
          {aiSource === "openai" && (
            <p className="mb-4 text-xs font-semibold text-cyan-300">
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
