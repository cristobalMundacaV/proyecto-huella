import { ArrowRight, Minus, TrendingDown, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import { formatNumber, formatPercent } from "@/shared/utils/formatters";

const FLOW_ROUTE = {
  energia: "energia", agua: "agua", combustibles: "combustibles", residuos: "residuos",
  ruido: "ruido", "emisiones-atmosfericas": "emisiones-atmosfericas", suelo: "suelo",
  transporte: "transporte", materiales: "materiales",
};

function trendOf(flow) {
  if (!flow.hasComparison) return { Icon: Minus, tone: "text-slate-500", label: "Línea de referencia" };
  if (flow.variation > 0) return { Icon: TrendingUp, tone: "text-rose-700", label: `+${formatPercent(flow.variation)} vs. ${flow.previousLabel}` };
  if (flow.variation < 0) return { Icon: TrendingDown, tone: "text-emerald-700", label: `${formatPercent(flow.variation)} vs. ${flow.previousLabel}` };
  return { Icon: Minus, tone: "text-slate-500", label: `Sin variación vs. ${flow.previousLabel}` };
}

/** Each flow keeps its own unit — this grid never sums kWh + m3 + kg + dB
 * into anything. Flows with no real data this period are shown as a
 * compact, de-emphasized chip instead of a large empty card (progressive
 * disclosure: this is a summary surface, the per-flow page has the detail). */
export default function EnvironmentalBalanceSection({ flows, obraId }) {
  const withData = flows.filter((flow) => flow.state === "con_datos");
  const withoutData = flows.filter((flow) => flow.state !== "con_datos");

  return <section className="rounded-[22px] border border-slate-200 bg-white/90 p-4 shadow-[0_10px_30px_rgba(15,23,42,.05)]">
    <div className="mb-4"><h2 className="text-xl font-bold text-slate-950">Balance de flujos ambientales</h2><p className="mt-1 text-sm font-normal text-slate-500">Desempeño físico real del período, cada flujo en su propia unidad — sin convertir ni sumar entre ellos.</p></div>
    {withData.length > 0
      ? <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{withData.map((flow) => {
        const trend = trendOf(flow);
        const route = FLOW_ROUTE[flow.domain];
        return <Link className={`group relative rounded-[18px] border ${flow.border || "border-slate-200"} ${flow.softBg || "bg-white"} p-3.5 pb-11 shadow-[0_7px_20px_rgba(15,23,42,.045)] transition hover:-translate-y-0.5 hover:shadow-md`} key={flow.domain} to={route ? `/obras/${obraId}/operacion/${route}` : `/obras/${obraId}/operacion`}>
          <div className="flex items-center justify-between gap-2">
            <span className={`flex h-9 w-9 items-center justify-center rounded-full bg-white/80 shadow-sm ${flow.text || "text-slate-700"}`}>{flow.icon && <flow.icon aria-hidden="true" size={18} />}</span>
            <span className={`inline-flex items-center gap-1 text-[11px] font-black ${trend.tone}`}><trend.Icon aria-hidden="true" size={13} />{flow.hasComparison ? formatPercent(Math.abs(flow.variation)) : "Referencia"}</span>
          </div>
          <p className={`mt-3 text-xs font-black ${flow.text || "text-slate-700"}`}>{flow.label}</p>
          <p className="mt-1 text-xl font-black text-slate-950">{formatNumber(flow.currentValue)}<span className="ml-1 text-xs font-bold text-slate-500">{flow.unit}</span></p>
          {flow.domain === "materiales" && flow.dominantMaterial && <p className="mt-1 text-[11px] font-bold text-slate-500">{flow.dominantMaterial}{flow.otherMaterialsCount > 0 ? ` +${flow.otherMaterialsCount} más` : ""}</p>}
          {flow.domain === "transporte" && flow.tripsInPeriod ? <p className="mt-1 text-[11px] font-bold text-slate-500">{flow.tripsInPeriod} viaje{flow.tripsInPeriod === 1 ? "" : "s"} en el período</p> : null}
          <p className="absolute bottom-4 left-3.5 max-w-[60%] truncate text-[11px] font-normal text-slate-500">{trend.label}</p>
          <span className="absolute bottom-4 right-3.5 flex items-center gap-1 text-xs font-black text-slate-700 group-hover:text-emerald-800">Ver detalle <ArrowRight size={13} /></span>
        </Link>;
      })}</div>
      : <p className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">Ningún flujo registra información física en el período seleccionado.</p>}
    {withoutData.length > 0 && <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3"><span className="text-[10px] font-black uppercase tracking-[0.13em] text-slate-400">Sin registros en el período:</span>{withoutData.map((flow) => <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-bold text-slate-500" key={flow.domain}>{flow.label}</span>)}</div>}
  </section>;
}
