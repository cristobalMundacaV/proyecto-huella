function FactorSuggestionPanel({ suggestion }) {
  if (!suggestion) return null;
  return (
    <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm font-semibold leading-6 text-sky-800">
      {suggestion.reason}
      {suggestion.factor?.metadata?.requires_validation && (
        <p className="mt-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-amber-800">
          Este factor es referencial. Validalo antes de usarlo en reportes oficiales.
        </p>
      )}
    </div>
  );
}

export default FactorSuggestionPanel;
