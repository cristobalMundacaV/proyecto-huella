import { AlertTriangle, Factory, Leaf } from "lucide-react";

function AserraderoModuleShell({
  children,
  config,
  error,
  loading,
  message,
  presetName = "Aserradero / Forestal",
}) {
  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[28px] border border-[var(--border)] bg-[linear-gradient(135deg,rgba(236,253,245,0.94),rgba(255,255,255,0.98)_45%,rgba(240,249,255,0.92))] p-5 shadow-[var(--shadow-premium)] sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/80 px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
                <Leaf size={14} />
                {presetName}
              </span>
              <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-sky-700">
                Modulo operativo
              </span>
            </div>

            <h1 className="mt-4 text-3xl font-black tracking-tight text-[var(--text-main)] sm:text-4xl">
              {config.title}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--text-muted)] sm:text-[15px]">
              {config.description}
            </p>
          </div>

          <div className="rounded-2xl border border-white/70 bg-white/85 p-4 shadow-[0_14px_32px_rgba(15,23,42,0.07)]">
            <div className="flex items-center gap-3">
              <span className="rounded-2xl bg-emerald-100 p-3 text-emerald-700">
                <Factory size={22} />
              </span>
              <div>
                <p className="text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)]">
                  Categoria operativa
                </p>
                <p className="mt-1 text-lg font-black text-[var(--text-main)]">{config.category}</p>
              </div>
            </div>
            <p className="mt-3 text-xs font-semibold leading-5 text-[var(--text-muted)]">
              Modulo preparado para el preset, pendiente de conectar flujo operativo.
            </p>
          </div>
        </div>
      </section>

      {message && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800">
          {message}
        </div>
      )}

      {error && (
        <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-800">
          <AlertTriangle className="mt-0.5 shrink-0" size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 text-sm font-semibold text-[var(--text-muted)] shadow-[var(--shadow-card)]">
          Cargando registros operativos...
        </div>
      ) : (
        children
      )}
    </div>
  );
}

export default AserraderoModuleShell;
