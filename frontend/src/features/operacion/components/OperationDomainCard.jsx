import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent, StatusBadge } from "@/shared/ui";
import { domainStateInfo } from "../utils/operationSelectors";

export default function OperationDomainCard({ icon: Icon, title, state, signal, detail, to, compact = false }) {
  const status = domainStateInfo(state);

  if (compact) {
    return <Card>
      <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Icon aria-hidden="true" className="text-[var(--brand-primary)]" size={18} />
            <h3 className="font-bold">{title}</h3>
            <StatusBadge tone={status.tone}>{status.label}</StatusBadge>
          </div>
          <p className="mt-2 text-sm font-medium text-[var(--text-secondary)]">{signal || status.description}</p>
          {detail && <p className="mt-1 text-xs text-[var(--text-muted)]">{detail}</p>}
        </div>
        <Link className="inline-flex shrink-0 items-center gap-2 text-sm font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to={to}>
          Ver detalle <ArrowRight aria-hidden="true" size={16} />
        </Link>
      </CardContent>
    </Card>;
  }

  return <Card className="h-full">
    <CardContent className="flex h-full flex-col">
      <div className="flex items-start justify-between gap-3">
        <Icon aria-hidden="true" className="text-[var(--brand-primary)]" />
        <StatusBadge tone={status.tone}>{status.label}</StatusBadge>
      </div>
      <h3 className="mt-4 text-lg font-bold">{title}</h3>
      <p className="mt-3 text-lg font-black text-[var(--text-primary)]">{signal || status.description}</p>
      {detail && <p className="mt-2 text-xs text-[var(--text-muted)]">{detail}</p>}
      <Link className="mt-auto flex items-center justify-between pt-5 text-sm font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to={to}>
        Ver detalle <ArrowRight aria-hidden="true" size={16} />
      </Link>
    </CardContent>
  </Card>;
}
