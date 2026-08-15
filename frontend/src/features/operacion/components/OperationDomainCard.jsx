import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent, StatusBadge } from "@/shared/ui";
import { formatNumber } from "@/shared/utils/formatters";

const statePresentation = {
  no_aplica: ["No aplica", "neutral"], por_definir: ["Por definir", "neutral"],
  sin_datos: ["Sin datos registrados", "warning"], con_datos: ["Con datos", "success"],
  requiere_revision: ["Requiere revisión", "danger"],
  error: ["No disponible", "danger"],
};

export default function OperationDomainCard({ icon: Icon, title, state, metric, detail, to }) {
  const [status, tone] = statePresentation[state] || statePresentation.por_definir;
  return <Card className="h-full"><CardContent className="flex h-full flex-col">
    <div className="flex items-start justify-between gap-3"><Icon className="text-[var(--brand-primary)]" /><StatusBadge tone={tone}>{status}</StatusBadge></div>
    <h3 className="mt-4 text-lg font-bold">{title}</h3>
    {metric ? <p className="mt-3 text-2xl font-black">{formatNumber(metric.value)} <span className="text-sm text-[var(--text-secondary)]">{metric.unit}</span></p> : <p className="mt-3 text-sm text-[var(--text-muted)]">No hay una métrica agregable disponible.</p>}
    {detail && <p className="mt-2 text-xs text-[var(--text-muted)]">{detail}</p>}
    <Link className="mt-auto flex items-center justify-between pt-5 text-sm font-bold text-[var(--brand-primary)]" to={to}>Ver detalle <ArrowRight size={16} /></Link>
  </CardContent></Card>;
}
