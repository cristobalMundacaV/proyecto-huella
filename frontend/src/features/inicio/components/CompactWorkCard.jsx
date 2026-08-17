import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

import { Card, CardContent } from "@/shared/ui";
import WorkStatus from "@/features/obras/components/WorkStatus";

export default function CompactWorkCard({ work, contextError = false }) {
  const statusLabel = work?.environmentalStatusLabel ?? 'Sin información'
  const trackingLabel = contextError
    ? 'Seguimiento no disponible'
    : work?.trackingLabel ?? 'Sin problemas abiertos'

  return (
    <a
      href={`/obras/${work.id}/resumen`}
      className="inicio-work-card"
    >
      <div className="inicio-work-card__top">
        <div className="inicio-work-card__code">
          {work.code ?? 'UNIDAD'}
        </div>
        <div className="inicio-work-card__arrow">→</div>
      </div>

      <h3 className="inicio-work-card__title">
        {work.name}
      </h3>

      <div className="inicio-work-card__meta-row">
        <span className="inicio-work-card__pill">
          {statusLabel}
        </span>
        <span className="inicio-work-card__plain-meta">
          {trackingLabel}
        </span>
      </div>
    </a>
  )
}