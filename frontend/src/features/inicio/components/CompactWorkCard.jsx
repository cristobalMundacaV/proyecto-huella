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

function getWorkTitle(work, unitLabel) {
  return (
    work?.nombre ||
    work?.nombre_obra ||
    work?.nombre_unidad ||
    work?.titulo ||
    work?.codigo_obra ||
    `${unitLabel} sin nombre`
  );
}

function getWorkLocation(work) {
  return [
    work?.ubicacion,
    work?.direccion,
    work?.comuna,
    work?.region,
  ]
    .filter(Boolean)
    .join(" · ");
}

function getWorkCode(work) {
  return work?.codigo_obra || work?.codigo || work?.identificador || null;
}

function getWorkHref(work) {
  const id = work?.id || work?.obra_id || work?.pk;
  return id ? `/obras/${id}` : "/obras";
}

function resolveEnvironmentalState({ context, contextError, work }) {
  const rawState =
    context?.estado_ambiental ??
    work?.estado_ambiental ??
    (contextError ? "no_disponible" : "no_determinado");

  if (contextError) {
    return {
      label: "Seguimiento no disponible",
      helper:
        "No fue posible consultar el seguimiento reciente de esta unidad.",
      badgeClass:
        "border-sky-200 bg-sky-50 text-sky-800",
      accentClass: "from-sky-500 to-cyan-500",
      icon: Activity,
      iconClass: "bg-sky-100 text-sky-700",
    };
  }

  switch (rawState) {
    case "requiere_atencion":
      return {
        label: "Requiere atención",
        helper:
          "Esta unidad presenta señales que necesitan revisión.",
        badgeClass:
          "border-amber-200 bg-amber-50 text-amber-800",
        accentClass: "from-amber-500 to-orange-500",
        icon: ShieldAlert,
        iconClass: "bg-amber-100 text-amber-700",
      };

    case "estable":
      return {
        label: "Estable",
        helper:
          "La unidad no muestra alertas relevantes con la información disponible.",
        badgeClass:
          "border-emerald-200 bg-emerald-50 text-emerald-800",
        accentClass: "from-emerald-500 to-teal-500",
        icon: ShieldCheck,
        iconClass: "bg-emerald-100 text-emerald-700",
      };

    case "cierre_pendiente":
      return {
        label: "Cierre pendiente",
        helper:
          "Hay seguimiento pendiente para cerrar correctamente el ciclo.",
        badgeClass:
          "border-orange-200 bg-orange-50 text-orange-800",
        accentClass: "from-orange-500 to-amber-500",
        icon: ShieldAlert,
        iconClass: "bg-orange-100 text-orange-700",
      };

    case "no_disponible":
      return {
        label: "Estado no disponible",
        helper:
          "El estado ambiental no se encuentra disponible actualmente.",
        badgeClass:
          "border-slate-200 bg-slate-100 text-slate-700",
        accentClass: "from-slate-400 to-slate-500",
        icon: CircleDashed,
        iconClass: "bg-slate-200 text-slate-700",
      };

    case "no_determinado":
    default:
      return {
        label: "Sin información",
        helper:
          "Todavía no hay suficiente información para determinar el estado ambiental.",
        badgeClass:
          "border-blue-200 bg-blue-50 text-blue-800",
        accentClass: "from-blue-500 to-cyan-500",
        icon: CircleDashed,
        iconClass: "bg-blue-100 text-blue-700",
      };
  }
}

export default function CompactWorkCard({
  work,
  context,
  contextError,
  evidenceCount = 0,
  unitLabel = "Unidad",
}) {
  const title = getWorkTitle(work, unitLabel);
  const location = getWorkLocation(work);
  const code = getWorkCode(work);
  const href = getWorkHref(work);
  const state = resolveEnvironmentalState({
    context,
    contextError,
    work,
  });
  const StateIcon = state.icon;

  return (
    <Link
      to={href}
      className="group relative block overflow-hidden rounded-[24px] border border-[var(--border-subtle)] bg-white p-5 shadow-[0_10px_28px_rgba(15,23,42,0.05)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_18px_40px_rgba(16,185,129,0.10)]"
    >
      <div
        className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${state.accentClass}`}
      />

      <div className="flex items-start gap-4">
        <div
          className={`mt-0.5 flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl ${state.iconClass}`}
        >
          <StateIcon
            aria-hidden="true"
            size={20}
          />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">
              {unitLabel}
            </span>

            {code && (
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-bold text-slate-600">
                {code}
              </span>
            )}
          </div>

          <h3 className="mt-1 text-lg font-black leading-tight text-slate-950 transition group-hover:text-emerald-800">
            {title}
          </h3>

          {location && (
            <div className="mt-2 flex items-center gap-2 text-sm text-slate-500">
              <MapPin
                aria-hidden="true"
                size={15}
              />
              <span className="truncate">{location}</span>
            </div>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            <span
              className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-bold ${state.badgeClass}`}
            >
              {state.label}
            </span>

            <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-bold text-slate-700">
              <FileCheck2
                aria-hidden="true"
                size={14}
              />
              {evidenceCount} evidencias
            </span>

            <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-bold text-slate-700">
              <Activity
                aria-hidden="true"
                size={14}
              />
              {contextError
                ? "Seguimiento no disponible"
                : "Seguimiento operativo"}
            </span>
          </div>

          <p className="mt-3 text-sm leading-6 text-slate-600">
            {state.helper}
          </p>
        </div>

        <div className="hidden self-center sm:block">
          <div className="flex h-11 w-11 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700 transition group-hover:bg-emerald-600 group-hover:text-white">
            <ArrowRight
              aria-hidden="true"
              size={18}
            />
          </div>
        </div>
      </div>
    </Link>
  );
}