import {
  AlertTriangle,
  BarChart3,
  CalendarDays,
  Database,
  Droplets,
  Factory,
  Flame,
  Gauge,
  Layers3,
  Leaf,
  Package,
  Recycle,
  Route,
  Target,
  TrendingUp,
  Truck,
  Zap,
} from "lucide-react";

const iconMap = {
  alert: AlertTriangle,
  calendar: CalendarDays,
  chart: BarChart3,
  database: Database,
  droplets: Droplets,
  factory: Factory,
  flame: Flame,
  fuel: Zap,
  gauge: Gauge,
  layers: Layers3,
  leaf: Leaf,
  package: Package,
  recycle: Recycle,
  route: Route,
  target: Target,
  trend: TrendingUp,
  truck: Truck,
  zap: Zap,
};

const toneMap = {
  danger: "border-rose-200 bg-rose-50 text-rose-700",
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  info: "border-sky-200 bg-sky-50 text-sky-700",
  violet: "border-violet-200 bg-violet-50 text-violet-700",
  neutral: "border-slate-200 bg-white text-slate-700",
};

function ReportKpiGrid({ kpis = [] }) {
  return (
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {kpis.map((kpi) => {
        const Icon = iconMap[kpi.icon] || BarChart3;
        const tone = toneMap[kpi.tone] || toneMap.neutral;
        return (
          <article key={kpi.label} className={`min-h-[150px] rounded-3xl border p-5 shadow-[0_14px_34px_rgba(15,23,42,0.08)] ${tone}`}>
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-2xl border border-current/20 bg-white/75">
                <Icon size={21} />
              </span>
              <p className="text-xs font-black uppercase tracking-[0.12em] opacity-80">{kpi.label}</p>
            </div>
            <p className="mt-5 break-words text-2xl font-black leading-tight">{kpi.value}</p>
            {kpi.description && <p className="mt-2 text-sm font-semibold leading-5 opacity-80">{kpi.description}</p>}
          </article>
        );
      })}
    </section>
  );
}

export default ReportKpiGrid;
