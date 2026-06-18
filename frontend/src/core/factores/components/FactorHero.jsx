import { Database, ShieldCheck, Sparkles } from "lucide-react";

function FactorHero({ activeConstructora, config, preset, status }) {
  return (
    <section className="relative overflow-hidden rounded-[34px] border border-emerald-200/70 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.20),transparent_34%),linear-gradient(135deg,rgba(15,45,39,0.98),rgba(18,61,52,0.96))] p-6 text-white shadow-[0_28px_90px_rgba(15,45,39,0.24)] sm:p-8">
      <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-emerald-300/20 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 left-10 h-72 w-72 rounded-full bg-teal-300/20 blur-3xl" />

      <div className="relative flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-4xl">
          <p className="inline-flex items-center gap-2 rounded-full border border-emerald-300/25 bg-white/10 px-3 py-1 text-xs font-black uppercase tracking-[0.2em] text-emerald-100">
            <Database size={16} />
            Catálogo ambiental
          </p>

          <h1 className="mt-5 text-3xl font-black leading-tight tracking-tight sm:text-5xl">
            {config.title}
          </h1>

          <p className="mt-4 max-w-3xl text-sm font-semibold leading-7 text-emerald-50/85 sm:text-base">
            {config.subtitle}
          </p>

          <div className="mt-5 flex flex-wrap gap-2">
            <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-black uppercase tracking-wide text-emerald-50">
              {activeConstructora?.nombre || "Empresa activa"}
            </span>
            <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-black uppercase tracking-wide text-emerald-50">
              Preset: {preset.name}
            </span>
          </div>
        </div>

        <div className="min-w-[260px] rounded-[28px] border border-emerald-300/20 bg-white/10 p-5 text-center shadow-[0_18px_42px_rgba(0,0,0,0.14)] backdrop-blur">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-300/25 bg-white/10 text-emerald-100">
            <ShieldCheck size={26} />
          </div>
          <p className="mt-4 text-xs font-black uppercase tracking-[0.18em] text-emerald-100/80">
            Estado del cálculo
          </p>
          <p className="mt-2 text-2xl font-black text-white">
            {status}
          </p>
          <p className="mt-3 flex items-center justify-center gap-2 text-xs font-semibold text-emerald-100/75">
            <Sparkles size={14} />
            Factores listos para trazabilidad ambiental
          </p>
        </div>
      </div>
    </section>
  );
}

export default FactorHero;