/** Single, reusable loading pattern for content that lives under the
 * persistent shell (sidebar/header/context selector never remount for
 * this): a soft skeleton that keeps the page's rough shape (hero, KPI row,
 * chart row) instead of a branded logo/progress-bar card or a spinner.
 * Used by Inicio (portfolio + obra), Reportes, Control and Configuración
 * so switching context never looks like a different loading application. */
export default function ContextContentSkeleton({
  heroHeight = 168,
  kpis = 4,
  charts = 2,
}) {
  return (
    <div aria-busy="true" aria-live="polite" className="animate-pulse space-y-4" role="status">
      <span className="sr-only">Cargando…</span>

      <div className="rounded-[28px] bg-slate-200/70" style={{ height: heroHeight }} />

      {kpis > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: kpis }).map((_, index) => (
            <div className="h-24 rounded-2xl bg-slate-200/70" key={index} />
          ))}
        </div>
      )}

      {charts > 0 && (
        <div className="grid gap-3 lg:grid-cols-2">
          {Array.from({ length: charts }).map((_, index) => (
            <div className="h-64 rounded-2xl bg-slate-200/60" key={index} />
          ))}
        </div>
      )}
    </div>
  );
}
