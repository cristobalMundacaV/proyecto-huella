import {
  Activity,
  AlertTriangle,
  Database,
  Droplets,
  Factory,
  Gauge,
  Leaf,
  Package,
  Recycle,
  Route,
  Target,
  Truck,
  Zap,
} from "lucide-react";

const iconMap = {
  activity: Activity,
  alert: AlertTriangle,
  database: Database,
  droplets: Droplets,
  factory: Factory,
  fuel: Zap,
  gauge: Gauge,
  leaf: Leaf,
  package: Package,
  recycle: Recycle,
  route: Route,
  target: Target,
  truck: Truck,
  zap: Zap,
};

const toneMap = {
  danger: "border-rose-200 bg-rose-50 text-rose-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  info: "border-sky-200 bg-sky-50 text-sky-700",
  violet: "border-violet-200 bg-violet-50 text-violet-700",
  neutral: "border-slate-200 bg-white text-slate-700",
};

function PresetKpiGrid({ kpis = [] }) {
  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {kpis.map((kpi) => {
        const Icon = iconMap[kpi.icon] || Activity;
        const tone = toneMap[kpi.tone] || toneMap.neutral;

        return (
          <article
            key={kpi.label}
            className={`min-h-[11rem] rounded-[24px] border p-5 shadow-[0_16px_34px_rgba(15,23,42,0.06)] ${tone}`}
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-xs font-black uppercase tracking-[0.18em] opacity-80">{kpi.label}</p>
              <span className="rounded-2xl border border-current/20 bg-white/70 p-2">
                <Icon size={20} />
              </span>
            </div>
            <p className="mt-5 break-words text-3xl font-black tracking-tight">{kpi.value}</p>
            {kpi.description && <p className="mt-2 text-sm font-semibold leading-5 opacity-80">{kpi.description}</p>}
          </article>
        );
      })}
    </section>
  );
}

export default PresetKpiGrid;
