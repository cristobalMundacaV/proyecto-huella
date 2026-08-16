import { AlertCircle, ArrowRight, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent, StatusBadge } from "@/shared/ui";

export default function AttentionList({ contextIncomplete, items, unitPluralLabel }) {
  if (!items.length) {
    const Icon = contextIncomplete ? AlertCircle : CheckCircle2;
    return <Card><CardContent className="flex items-center gap-3">
      <span className={`rounded-full p-2 ${contextIncomplete ? "bg-[var(--info-bg)] text-[var(--status-info)]" : "bg-[var(--success-bg)] text-[var(--status-success)]"}`}><Icon aria-hidden="true" size={20} /></span>
      <div><h3 className="font-black">{contextIncomplete ? "No hay pendientes detectados" : "Todo al día"}</h3><p className="text-sm text-[var(--text-muted)]">{contextIncomplete ? "Parte del estado no pudo verificarse." : `No hay pendientes disponibles para tus ${unitPluralLabel.toLowerCase()}.`}</p></div>
    </CardContent></Card>;
  }
  return <ul className="divide-y divide-[var(--border-subtle)] rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)]">{items.map((item) => <li key={item.key} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h3 className="font-black text-[var(--text-primary)]">{item.title}</h3><StatusBadge tone={item.tone}>{item.status}</StatusBadge></div><p className="mt-1 text-sm text-[var(--text-secondary)]">{item.location}</p><p className="text-xs text-[var(--text-muted)]">{item.reason}</p></div><Link className="inline-flex shrink-0 items-center gap-2 text-sm font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to={item.path}>{item.action}<ArrowRight aria-hidden="true" size={16} /></Link></li>)}</ul>;
}
