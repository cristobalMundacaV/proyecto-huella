import { AlertTriangle, ArrowRight, Lightbulb } from "lucide-react";
import { Link } from "react-router-dom";
import { formatNumber } from "@/shared/utils/formatters";
import { getEnvironmentalDomain } from "@/shared/config/environmentalDomains";
import { StatusBadge } from "./Badge";

const METRIC_TONES = {
  neutral: "border-slate-200 bg-slate-50 text-slate-700",
  info: "border-blue-200 bg-blue-50/65 text-blue-700",
  success: "border-emerald-200 bg-emerald-50/65 text-emerald-700",
  warning: "border-amber-200 bg-amber-50/65 text-amber-700",
  danger: "border-rose-200 bg-rose-50/65 text-rose-700",
  blue: "border-blue-200 bg-blue-50/65 text-blue-700",
  rose: "border-rose-200 bg-rose-50/65 text-rose-700",
  emerald: "border-emerald-200 bg-emerald-50/65 text-emerald-700",
  amber: "border-amber-200 bg-amber-50/65 text-amber-700",
  violet: "border-violet-200 bg-violet-50/65 text-violet-700",
  orange: "border-orange-200 bg-orange-50/65 text-orange-700",
};

export function CZProgress({ value, className = "" }) {
  const normalized = Math.min(100, Math.max(0, Number(value) || 0));
  return <div className={`h-1.5 w-full overflow-hidden rounded-[var(--radius-pill)] bg-slate-200 ${className}`}><div className="h-full rounded-[var(--radius-pill)] bg-current transition-[width] duration-[var(--motion-standard)]" style={{ width: `${normalized}%` }} /></div>;
}

export function CZMetricCard({ icon: Icon, label, value, unit, supportingText, helper, tone = "neutral", progress, delta, className = "" }) {
  const missing = value === null || value === undefined || value === "";
  return <article className={`flex min-h-[112px] items-center rounded-[var(--radius-card)] border p-[var(--space-3)] shadow-[var(--shadow-card-v1)] ${METRIC_TONES[tone] || METRIC_TONES.neutral} ${className}`}>
    <div className="flex w-full items-center gap-[var(--space-3)]"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/80 shadow-sm">{Icon && <Icon aria-hidden="true" size={20} />}</span><div className="min-w-0 flex-1"><p className="text-xs font-black text-slate-600">{label}</p><p className="mt-1 text-[21px] font-black leading-tight text-slate-950">{missing ? "Sin datos" : typeof value === "number" ? formatNumber(value) : value}{!missing && unit && <span className="ml-1 text-xs font-bold text-slate-500">{unit}</span>}</p>{progress != null && <CZProgress className="mt-2" value={progress} />}{delta && <p className="mt-1 text-[11px] font-bold">{delta}</p>}<p className="mt-1.5 text-[11px] leading-4 text-slate-500">{supportingText || helper || "Dato del período actual"}</p></div></div>
  </article>;
}

export function CZPageHero({ children, className = "" }) {
  return <section className={`relative overflow-hidden rounded-[var(--radius-hero)] border border-emerald-700/20 bg-[radial-gradient(circle_at_72%_25%,rgba(110,231,183,0.20),transparent_30%),linear-gradient(118deg,#064e3b_0%,#066657_54%,#0f766e_100%)] p-[var(--space-6)] text-white shadow-[var(--shadow-floating)] lg:p-7 ${className}`}>{children}</section>;
}

export function CZSection({ children, className = "", ...props }) {
  return <section className={`rounded-[var(--radius-panel)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-[var(--space-5)] shadow-[var(--shadow-card-v1)] ${className}`} {...props}>{children}</section>;
}

export function CZFlowCard({ flow, label, icon, value, unit, status, supportingText, href, action = "Ver detalle" }) {
  const identity = getEnvironmentalDomain(flow) || {};
  const Icon = icon || identity.icon;
  const hasValue = value !== null && value !== undefined;
  return <Link className={`group relative rounded-[var(--radius-card)] border ${identity.border || "border-slate-200"} ${identity.softBg || "bg-white"} p-3.5 pb-11 shadow-[var(--shadow-card-v1)] transition duration-[var(--motion-fast)] hover:-translate-y-0.5 hover:shadow-[var(--shadow-md)]`} to={href}><div className="flex items-center justify-between gap-2"><span className={`flex h-9 w-9 items-center justify-center rounded-full bg-white/80 shadow-sm ${identity.text || "text-slate-700"}`}>{Icon && <Icon aria-hidden="true" size={18} />}</span><StatusBadge tone={hasValue ? "success" : "neutral"}>{status || (hasValue ? "Con datos" : "Sin datos")}</StatusBadge></div><p className={`mt-3 text-xs font-black ${identity.text || "text-slate-700"}`}>{label || identity.label}</p><p className="mt-1 text-xl font-black text-slate-950">{hasValue ? formatNumber(value) : "Sin datos"}{hasValue && unit && <span className="ml-1 text-xs font-bold text-slate-500">{unit}</span>}</p><p className="absolute bottom-4 left-3.5 max-w-[55%] truncate text-[11px] text-slate-500">{supportingText || (hasValue ? "Registro físico del período" : "No hay registros en el período")}</p><span className="absolute bottom-4 right-3.5 flex items-center gap-1 text-xs font-black text-slate-700 group-hover:text-emerald-800">{action} <ArrowRight size={13} /></span></Link>;
}

const INSIGHT_TONES = {
  alta: { badge: "danger", card: "border-rose-200 bg-gradient-to-br from-rose-50 via-white to-rose-50/45 shadow-[var(--shadow-card-v1)]", icon: "bg-rose-100 text-rose-700" },
  media: { badge: "warning", card: "border-amber-200 bg-gradient-to-br from-amber-50 via-white to-amber-50/45 shadow-[var(--shadow-card-v1)]", icon: "bg-amber-100 text-amber-700" },
  baja: { badge: "info", card: "border-blue-200 bg-gradient-to-br from-blue-50 via-white to-blue-50/45 shadow-[var(--shadow-card-v1)]", icon: "bg-blue-100 text-blue-700" },
  neutral: { badge: "neutral", card: "border-slate-200 bg-slate-50", icon: "bg-slate-200 text-slate-700" },
};

export function CZInsightCard({ priority = "neutral", title, description, icon: Icon = Lightbulb, cta, className = "" }) {
  const tone = INSIGHT_TONES[priority] || INSIGHT_TONES.neutral;
  return <article className={`relative h-full min-h-[145px] rounded-[var(--radius-card)] border p-[var(--space-4)] pr-20 ${tone.card} ${className}`}>
    <StatusBadge className="absolute right-4 top-4 capitalize" tone={tone.badge}>{priority}</StatusBadge>
    <div className="flex items-start gap-3">
      <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${tone.icon}`}><Icon aria-hidden="true" size={17} /></span>
      <div className="min-w-0 pt-0.5">
        <h3 className="font-black leading-5 text-slate-950">{title}</h3>
        <p className="mt-3 text-sm font-medium leading-5 text-slate-700">{description}</p>
      </div>
    </div>
    {cta && <div className="mt-3">{cta}</div>}
  </article>;
}

const ALERT_BANNER_TONES = {
  warning: "border-amber-300 bg-amber-50 text-amber-900",
  info: "border-blue-200 bg-blue-50 text-blue-900",
  danger: "border-rose-300 bg-rose-50 text-rose-900",
};

export function CZAlertBanner({ tone = "warning", icon: Icon = AlertTriangle, children, action, className = "" }) {
  return <div className={`flex min-h-14 flex-wrap items-center gap-3 rounded-[var(--radius-card)] border px-4 py-2.5 text-sm ${ALERT_BANNER_TONES[tone] || ALERT_BANNER_TONES.warning} ${className}`}>
    <Icon aria-hidden="true" className="shrink-0" size={18} />
    <div className="min-w-0 flex-1 leading-5">{children}</div>
    {action && <div className="shrink-0">{action}</div>}
  </div>;
}

export { StatusBadge as CZStatusBadge };
