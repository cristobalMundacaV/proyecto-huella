import { ArrowRight, CalendarDays, MapPin } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent, ScopeBadge } from "@/shared/ui";
import WorkStatus from "./WorkStatus";

export default function WorkCard({ work, context }) {
  const routeId = work.id || work.obra_id || work.codigo_obra;
  const problems = context?.problematicas_abiertas?.length;
  const environmentalStatus = context?.obra?.estado_ambiental || work.estado_ambiental;
  const profile = context?.obra?.perfil || work.perfil_ambiental;
  return <Card className="h-full transition hover:border-[var(--border-strong)] hover:shadow-[var(--shadow-md)]">
    <CardContent className="flex h-full flex-col">
      <div className="flex items-start justify-between gap-3">
        <div><p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">{work.codigo_obra}</p><h2 className="mt-1 text-lg font-bold text-[var(--text-primary)]">{work.nombre || work.tipo_proyecto || "Obra sin nombre"}</h2></div>
        <WorkStatus value={environmentalStatus} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2"><ScopeBadge label={profile || "Perfil por definir"} /><WorkStatus value={work.estado} /></div>
      <div className="mt-4 space-y-2 text-sm text-[var(--text-secondary)]">
        {work.ubicacion && <p className="flex items-center gap-2"><MapPin size={15} />{work.ubicacion}</p>}
        {work.fecha_inicio && <p className="flex items-center gap-2"><CalendarDays size={15} />Inicio {work.fecha_inicio}</p>}
        <p>{problems === undefined ? "Estado de problemas no disponible" : problems ? `${problems} problemas abiertos` : "Sin problemas abiertos"}</p>
      </div>
      <Link className="mt-auto flex items-center justify-between pt-5 font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to={`/obras/${routeId}/resumen`}>
        Abrir obra <ArrowRight size={17} />
      </Link>
    </CardContent>
  </Card>;
}
