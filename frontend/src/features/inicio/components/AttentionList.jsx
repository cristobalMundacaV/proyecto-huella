import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ScanSearch,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import { getEnvironmentalDomain } from "@/shared/config/environmentalDomains";
import { ButtonLink, EmptyState, StatusBadge } from "@/shared/ui";

const categoryKey = (value) => {
  const key = String(value || "").toLowerCase().normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "").replaceAll(" ", "_").replaceAll("-", "_");
  return key === "hidrica_y_suelo" ? "hidrica_suelo" : key;
};

const signalIcon = (item, fallback) => {
  const text = `${item.title || ""} ${item.description || ""}`.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  if (/aumento|alza|crecimiento|incremento/.test(text)) return TrendingUp;
  if (/disminucion|caida|perdida/.test(text)) return TrendingDown;
  if (/trazabilidad|revision|seguimiento/.test(text)) return ScanSearch;
  if (/desvio|riesgo|incumplimiento|alerta/.test(text)) return ShieldAlert;
  return fallback;
};

const severityInfo = (value) => {
  if (["critico", "alto"].includes(value)) return {
    card: "border-rose-200 border-l-rose-500 bg-rose-50/45",
    icon: "bg-rose-100 text-rose-700",
    risk: "border-rose-200 bg-rose-50 text-rose-700",
  };
  if (value === "medio") return {
    card: "border-amber-200 border-l-amber-500 bg-amber-50/45",
    icon: "bg-amber-100 text-amber-700",
    risk: "border-amber-200 bg-amber-50 text-amber-700",
  };
  if (["bajo", "seguimiento", "en_seguimiento", "en_implementacion"].includes(value)) return {
    card: "border-cyan-200 border-l-cyan-500 bg-cyan-50/40",
    icon: "bg-cyan-100 text-cyan-800",
    risk: "border-cyan-200 bg-cyan-50 text-cyan-800",
  };
  return {
    card: "border-slate-200 border-l-slate-400 bg-white",
    icon: "bg-slate-100 text-slate-600",
    risk: "border-slate-200 bg-slate-50 text-slate-600",
  };
};

const riskLabel = (value) => ({ critico: "Crítico", alto: "Alto", medio: "Medio", bajo: "Bajo" })[value] || value;
const capitalized = (value) => {
  const label = String(value || "Pendiente").replaceAll("_", " ").trim();
  return label ? `${label.charAt(0).toUpperCase()}${label.slice(1).toLowerCase()}` : "Pendiente";
};

export default function AttentionList({ items = [], contextIncomplete = false }) {
  if (!items.length) return <EmptyState
    icon={CheckCircle2}
    title="Sin prioridades abiertas"
    description="No hay problemas o seguimientos prioritarios que requieran tu atención en este momento."
  />;

  return <div className="mt-4 space-y-3">
    {items.slice(0, 4).map((item) => {
      const category = getEnvironmentalDomain(categoryKey(item.category));
      const DomainIcon = category?.icon || AlertCircle;
      const SignalIcon = signalIcon(item, DomainIcon);
      const severity = severityInfo(item.severity);

      return <article className={`rounded-[18px] border border-l-4 p-4 shadow-[0_8px_24px_rgba(15,23,42,0.04)] ${severity.card}`} key={item.key}>
        <div className="flex items-center gap-3">
          <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${severity.icon}`}>
            <SignalIcon aria-hidden="true" size={19} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-black text-[var(--text-primary)]">{item.title}</h3>
              <span className="shrink-0"><StatusBadge tone={item.tone}>{capitalized(item.status)}</StatusBadge></span>
            </div>
            {item.description && <p className="mt-1 line-clamp-2 text-sm text-[var(--text-secondary)]">{item.description}</p>}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
          <div className="flex flex-wrap gap-2 text-xs font-bold">
              {category && <span className={`inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1 ${category.text}`}><DomainIcon aria-hidden="true" size={14} />{category.label}</span>}
              {item.risk && <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${severity.risk}`}><ShieldAlert aria-hidden="true" size={14} />Riesgo: {riskLabel(item.risk)}</span>}
              {!item.risk && item.reason && <span className="inline-flex items-center rounded-full border border-slate-200 bg-white px-2.5 py-1 text-slate-600">{item.reason}</span>}
          </div>
          {item.path && <ButtonLink className="ml-auto" size="sm" variant="secondary" rightIcon={ArrowRight} to={item.path}>{item.action || "Ver gestión"}</ButtonLink>}
        </div>
      </article>;
    })}

    {contextIncomplete && <p className="text-xs text-amber-700">Parte del estado no pudo verificarse completamente.</p>}
  </div>;
}
