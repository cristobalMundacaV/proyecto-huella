import {
  Activity,
  ArrowRight,
  FileCheck2,
  MapPin,
  ShieldAlert,
  ShieldCheck,
  CircleDashed,
} from "lucide-react";

import { Link } from "react-router-dom";

function workPresentation(status) {
  switch (status) {
    case "requiere_atencion":
      return {
        label: "Requiere atención",
        accent: "from-amber-500 to-orange-500",
        iconClass: "bg-amber-100 text-amber-700",
        badgeClass: "border-amber-200 bg-amber-50 text-amber-800",
        Icon: ShieldAlert,
      };

    case "cierre_pendiente":
      return {
        label: "Cierre pendiente",
        accent: "from-orange-500 to-amber-500",
        iconClass: "bg-orange-100 text-orange-700",
        badgeClass: "border-orange-200 bg-orange-50 text-orange-800",
        Icon: ShieldAlert,
      };

    case "estable":
      return {
        label: "Estable",
        accent: "from-emerald-500 to-teal-500",
        iconClass: "bg-emerald-100 text-emerald-700",
        badgeClass: "border-emerald-200 bg-emerald-50 text-emerald-800",
        Icon: ShieldCheck,
      };

    case "no_disponible":
      return {
        label: "No disponible",
        accent: "from-slate-400 to-slate-500",
        iconClass: "bg-slate-100 text-slate-600",
        badgeClass: "border-slate-200 bg-slate-50 text-slate-700",
        Icon: Activity,
      };

    case "no_determinado":
    default:
      return {
        label: "Sin información",
        accent: "from-sky-500 to-cyan-500",
        iconClass: "bg-sky-100 text-sky-700",
        badgeClass: "border-sky-200 bg-sky-50 text-sky-800",
        Icon: CircleDashed,
      };
  }
}

export default function WorkCard({
  work,
  context,
  contextError = false,
  unitLabel = "Obra",
}) {
  const routeId =
    work.id ||
    work.obra_id ||
    work.codigo_obra;

  const problems =
    context?.problematicas_abiertas?.length;

  const evidenceCount =
    context?.evidencias?.length;

  const environmentalStatus =
    context?.obra?.estado_ambiental ??
    work.estado_ambiental ??
    (contextError
      ? "no_disponible"
      : "no_determinado");

  const presentation =
    workPresentation(environmentalStatus);

  const StatusIcon = presentation.Icon;

  const problemLabel = contextError
    ? "Seguimiento no disponible"
    : problems === undefined
      ? "Problemas no disponibles"
      : problems > 0
        ? `${problems} ${problems === 1 ? "problema abierto" : "problemas abiertos"}`
        : "Sin problemas abiertos";

  return (
    <Link
      to={`/obras/${routeId}/resumen`}
      aria-label={`Ver ${unitLabel.toLowerCase()} ${work.nombre ||
        work.codigo_obra ||
        "seleccionada"
        }`}
      className="group relative block h-full overflow-hidden rounded-[24px] border border-[var(--border-subtle)] bg-white p-5 shadow-[0_10px_28px_rgba(15,23,42,0.05)] transition duration-200 hover:-translate-y-0.5 hover:border-emerald-200 hover:shadow-[0_18px_40px_rgba(16,185,129,0.10)]"
    >
      <div
        className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${presentation.accent}`}
      />

      <div className="flex items-start gap-4">
        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${presentation.iconClass}`}
        >
          <StatusIcon
            aria-hidden="true"
            size={19}
          />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-black uppercase tracking-[0.16em] text-[var(--text-muted)]">
              {unitLabel}
            </span>

            {work.codigo_obra && (
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-bold text-slate-600">
                {work.codigo_obra}
              </span>
            )}
          </div>

          <h2 className="mt-1 text-lg font-black leading-tight text-[var(--text-primary)] transition group-hover:text-emerald-800">
            {work.nombre ||
              `${unitLabel} sin nombre`}
          </h2>

          {work.ubicacion && (
            <div className="mt-2 flex items-center gap-2 text-sm text-[var(--text-muted)]">
              <MapPin
                aria-hidden="true"
                size={15}
              />
              <span className="truncate">
                {work.ubicacion}
              </span>
            </div>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            <span
              className={`rounded-full border px-3 py-1 text-xs font-bold ${presentation.badgeClass}`}
            >
              {presentation.label}
            </span>

            <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-bold text-slate-700">
              <Activity
                aria-hidden="true"
                size={14}
              />
              {problemLabel}
            </span>

            {evidenceCount !== undefined && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-bold text-slate-700">
                <FileCheck2
                  aria-hidden="true"
                  size={14}
                />
                {evidenceCount} evidencias
              </span>
            )}
          </div>
        </div>

        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700 transition group-hover:bg-emerald-700 group-hover:text-white">
          <ArrowRight
            aria-hidden="true"
            size={17}
          />
        </div>
      </div>
    </Link>
  );
}