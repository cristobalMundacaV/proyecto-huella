import { ArrowRight, MapPin } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "@/shared/ui";
import WorkStatus from "./WorkStatus";

export default function WorkCard({ work, context, contextError = false, unitLabel = "Obra" }) {
  const routeId = work.id || work.obra_id || work.codigo_obra;
  const problems = context?.problematicas_abiertas?.length;
  const environmentalStatus = contextError ? "no_disponible" : (context?.obra?.estado_ambiental ?? work.estado_ambiental ?? "no_determinado");
  const signal = contextError
    ? "Información de seguimiento no disponible"
    : problems === undefined
      ? "Estado de problemas no disponible"
      : problems > 0
        ? `${problems} ${problems === 1 ? "problema abierto" : "problemas abiertos"}`
        : "Sin problemas abiertos";

  return <Card className="h-full transition hover:border-[var(--border-strong)] hover:shadow-[var(--shadow-md)]">
    <CardContent className="flex h-full flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">{work.codigo_obra || "Código automático"}</p>
          <h2 className="mt-1 text-lg font-bold text-[var(--text-primary)]">{work.nombre || `${unitLabel} sin nombre`}</h2>
        </div>
        <WorkStatus value={environmentalStatus} />
      </div>

      <div className="space-y-2 text-sm text-[var(--text-secondary)]">
        <p className="font-semibold text-[var(--text-primary)]">{signal}</p>
        {work.ubicacion && <p className="flex items-center gap-2"><MapPin aria-hidden="true" size={15} />{work.ubicacion}</p>}
      </div>

      <Link
        aria-label={`Ver ${unitLabel.toLowerCase()} ${work.nombre || work.codigo_obra || "seleccionada"}`}
        className="mt-auto flex items-center justify-between pt-2 font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
        to={`/obras/${routeId}/resumen`}
      >
        Ver {unitLabel.toLowerCase()} <ArrowRight aria-hidden="true" size={17} />
      </Link>
    </CardContent>
  </Card>;
}
