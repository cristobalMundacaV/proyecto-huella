import { FileSearch } from "lucide-react";

function EmptyState({
  title = "Sin datos disponibles",
  description = "Aún no hay información suficiente para construir esta vista.",
  icon: Icon = FileSearch,
  action = null,
}) {
  return (
    <section className="rounded-[32px] border border-emerald-200/70 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_34%),linear-gradient(135deg,rgba(236,253,245,0.96),rgba(255,255,255,0.98))] p-8 text-center shadow-[0_24px_70px_rgba(15,118,110,0.10)] ring-1 ring-white/80">
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl border border-emerald-200 bg-white text-emerald-700 shadow-[0_18px_42px_rgba(15,118,110,0.12)]">
        <Icon size={34} />
      </div>

      <p className="mt-6 text-xs font-black uppercase tracking-[0.22em] text-emerald-700">
        Estado de información
      </p>
      <h2 className="mx-auto mt-2 max-w-2xl text-2xl font-black tracking-tight text-slate-950">
        {title}
      </h2>
      <p className="mx-auto mt-3 max-w-2xl text-sm font-semibold leading-7 text-slate-600">
        {description}
      </p>

      {action ? <div className="mt-6">{action}</div> : null}
    </section>
  );
}

export default EmptyState;