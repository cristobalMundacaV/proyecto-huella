import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";
import { Link } from "react-router-dom";

import {
  Card,
  CardContent,
  StatusBadge,
} from "@/shared/ui";

export default function AttentionList({
  items = [],
  partiallyUnavailable = false,
}) {
  if (!items.length) {
    return (
      <div className="inicio-attention-empty">
        <div className="inicio-attention-empty__icon">✓</div>
        <div>
          <div className="inicio-attention-empty__title">
            No hay pendientes detectados
          </div>
          <div className="inicio-attention-empty__text">
            {partiallyUnavailable
              ? 'Parte del estado no pudo verificarse, pero no se detectaron pendientes confirmados.'
              : 'Todo al día. No hay pendientes disponibles para tus obras.'}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="inicio-attention-list">
      {items.slice(0, 5).map((item, index) => (
        <div className="inicio-attention-item" key={item.id ?? `${item.kind}-${index}`}>
          <div className="inicio-attention-item__top">
            <span className="inicio-attention-item__badge">
              {item.kindLabel ?? 'Pendiente'}
            </span>
            {item.href ? (
              <a href={item.href} className="inicio-inline-link">
                Revisar
              </a>
            ) : null}
          </div>

          <div className="inicio-attention-item__title">
            {item.title}
          </div>

          {item.description ? (
            <div className="inicio-attention-item__description">
              {item.description}
            </div>
          ) : null}
        </div>
      ))}

      {partiallyUnavailable && (
        <div className="inicio-attention-warning">
          Parte del estado no pudo verificarse completamente.
        </div>
      )}
    </div>
  )
}