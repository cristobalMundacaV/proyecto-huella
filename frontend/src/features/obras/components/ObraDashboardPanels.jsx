import { ArrowRight, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "@/shared/ui/Card";
import { SectionHeader } from "@/shared/ui/Headers";
import { StatusBadge } from "@/shared/ui/Badge";
import { formatNumber } from "@/shared/utils/formatters";

export function FlowStatusGrid({ flows = [] }) {
  return <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
    {flows.map((flow) => {
      const Icon = flow.icon;
      const hasValue = flow.value !== null && flow.value !== undefined;
      return <Link className={`group relative rounded-[18px] border ${flow.border || "border-slate-200"} ${flow.softBg || "bg-white"} p-3.5 pb-11 shadow-[0_7px_20px_rgba(15,23,42,.045)] transition hover:-translate-y-0.5 hover:shadow-md`} key={flow.key} to={flow.href}>
        <div className="flex items-center justify-between gap-2"><span className={`flex h-9 w-9 items-center justify-center rounded-full bg-white/80 shadow-sm ${flow.text || "text-slate-700"}`}>{Icon && <Icon size={18} />}</span><StatusBadge tone={hasValue ? "success" : "neutral"}>{hasValue ? "Con datos" : "Sin datos"}</StatusBadge></div>
        <p className={`mt-3 text-xs font-black ${flow.text || "text-slate-700"}`}>{flow.label}</p>
        <p className="mt-1 text-xl font-black text-slate-950">{hasValue ? formatNumber(flow.value) : "Sin datos"}{hasValue && flow.unit && <span className="ml-1 text-xs font-bold text-slate-500">{flow.unit}</span>}</p>
        <p className="absolute bottom-4 left-3.5 max-w-[55%] truncate text-[11px] font-normal text-slate-500">{hasValue ? "Registro físico del período" : "No hay registros en el período"}</p>
        <span className="absolute bottom-4 right-3.5 flex items-center gap-1 text-xs font-black text-slate-700 group-hover:text-emerald-800">Ver detalle <ArrowRight size={13} /></span>
      </Link>;
    })}
  </div>;
}

export function AiRecommendationsPanel({ recommendations = [] }) {
  const visible = recommendations.slice(0, 3);
  return <Card className="border-slate-200 bg-white/90"><CardContent>
    <SectionHeader title="Insights y recomendaciones IA" titleClassName="text-lg font-black" description="Priorizadas según impacto potencial en la huella, evidencia y riesgo ambiental." />
    {!visible.length ? <p className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">El motor de diagnóstico no identificó recomendaciones prioritarias con la información disponible.</p> : <div className="grid gap-3 lg:grid-cols-3">{visible.map((item) => <article className="relative flex min-h-[210px] flex-col rounded-[18px] border border-slate-200 bg-[linear-gradient(145deg,#fff,#f8fafc)] p-4 shadow-[0_7px_20px_rgba(15,23,42,.04)]" key={item.key}>
      <StatusBadge className="absolute right-4 top-4" tone={item.tone}>{item.priorityLabel}</StatusBadge>
      <div className="flex items-start gap-3 pr-16"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-violet-50 text-violet-700"><Sparkles size={17} /></span><div className="min-w-0"><h3 className="font-black text-slate-950">{item.title}</h3><p className="mt-2 text-xs leading-5 text-slate-600">{item.description}</p></div></div>
      {item.comparison && <ComparisonValues comparison={item.comparison} />}
      <Link className="ml-auto mt-auto inline-flex items-center gap-1 pt-3 text-xs font-black text-emerald-800" to={item.href}>Revisar <ArrowRight size={13} /></Link>
    </article>)}</div>}
  </CardContent></Card>;
}

function ComparisonValues({ comparison }) {
  return <div className="mt-3 grid grid-cols-[1fr_auto_1fr] items-end gap-2 text-center" aria-label="Comparación con el período anterior">
    <ComparisonValue label="Antes" value={comparison.before} unit={comparison.unit} muted />
    <ArrowRight className="mb-3 text-slate-400" size={16} />
    <ComparisonValue label="Después" value={comparison.after} unit={comparison.unit} />
  </div>;
}

function ComparisonValue({ label, value, unit, muted = false }) {
  return <div><p className="mb-1 text-center text-[10px] font-black uppercase tracking-wider text-slate-500">{label}</p><div className={`flex items-end justify-center gap-1.5 rounded-xl border px-3 py-2 text-center ${muted ? "border-slate-200 bg-slate-50" : "border-emerald-200 bg-emerald-50"}`}><span className="text-lg font-black leading-none text-slate-950">{formatNumber(value)}</span>{unit && <span className="text-[10px] font-bold leading-none text-slate-500">{unit}</span>}</div></div>;
}
