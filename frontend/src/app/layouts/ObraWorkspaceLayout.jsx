import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  ArrowLeft,
  CalendarDays,
  MapPin,
} from "lucide-react";

import {
  Link,
  Outlet,
  useParams,
} from "react-router-dom";

import PlatformLoader from "@/shared/components/PlatformLoader";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

import { getWorkWorkspace } from "@/features/obras/services/workspaceApi";

import WorkStatus, {
  statusLabel,
} from "@/features/obras/components/WorkStatus";

import { getActivePreset } from "@/presets/registry";

import {
  ErrorState,
  ScopeBadge,
} from "@/shared/ui";

import {
  formatDate,
} from "@/shared/utils/formatters";

function environmentalDescription(
  value
) {
  switch (value) {
    case "configuracion":
      return "La unidad todavía está construyendo su contexto y cobertura ambiental.";

    case "estable":
      return "La información disponible no muestra situaciones ambientales que requieran atención.";

    case "requiere_atencion":
      return "Existen situaciones ambientales que requieren revisión o seguimiento.";

    case "mejora_en_curso":
      return "Hay acciones ambientales actualmente en implementación o seguimiento.";

    case "monitoreo":
      return "La unidad se encuentra bajo seguimiento ambiental activo.";

    case "cierre_pendiente":
      return "La operación finalizó, pero el cierre ambiental todavía requiere completar antecedentes o validaciones.";

    case "cerrada":
      return "La unidad completó su cierre ambiental.";

    case "no_disponible":
      return "No fue posible determinar el estado ambiental de esta unidad.";

    case "no_determinado":
    default:
      return "Todavía no existe información suficiente para determinar un estado ambiental.";
  }
}


export default function ObraWorkspaceLayout() {
  const {
    obraId,
  } = useParams();

  const {
    activeOrganizacion,
    activeOrganizacionId,
  } = useOrganizacionActiva();

  const preset =
    getActivePreset(
      activeOrganizacion?.preset ||
      "construccion"
    );

  const [
    state,
    setState,
  ] = useState({
    status: "loading",
    workspace: null,
  });

  const requestRef =
    useRef(0);


  const load =
    useCallback(() => {
      if (
        !activeOrganizacionId
      ) {
        return;
      }

      const requestId =
        ++requestRef.current;

      setState({
        status: "loading",
        workspace: null,
      });

      getWorkWorkspace(
        activeOrganizacionId,
        obraId
      )
        .then((workspace) => {
          if (
            requestRef.current ===
            requestId
          ) {
            setState({
              status: "ready",
              workspace,
            });
          }
        })
        .catch((error) => {
          if (
            requestRef.current !==
            requestId
          ) {
            return;
          }

          setState({
            status:
              error.response
                ?.status === 404
                ? "missing"
                : "error",

            workspace: null,
          });
        });
    }, [
      activeOrganizacionId,
      obraId,
    ]);


  useEffect(() => {
    load();

    return () => {
      requestRef.current += 1;
    };
  }, [load]);


  if (
    state.status ===
    "loading"
  ) {
    return (
      <PlatformLoader
        compact
        title={`Cargando ${preset.unitLabel.toLowerCase()}`}
        description="Estamos preparando su contexto, indicadores y actividad ambiental."
      />
    );
  }


  if (
    state.status ===
    "missing"
  ) {
    return (
      <ErrorState
        title={`${preset.unitLabel} no disponible`}
        description={`La ${preset.unitLabel.toLowerCase()} no existe o no está disponible en la organización activa.`}
      />
    );
  }


  if (
    state.status ===
    "error"
  ) {
    return (
      <ErrorState
        title="No pudimos cargar esta unidad"
        description="Intenta nuevamente para recuperar su contexto de gestión."
        onRetry={load}
      />
    );
  }


  const {
    obra,
  } = state.workspace;


  const location =
    obra.ubicacion ||
    [
      obra.comuna,
      obra.region,
    ]
      .filter(Boolean)
      .join(", ");


  return (
    <main className="space-y-6">

      {/* VOLVER */}
      <Link
        className="inline-flex items-center gap-2 text-sm font-bold text-[var(--text-secondary)] transition hover:text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
        to="/obras"
      >
        <ArrowLeft
          aria-hidden="true"
          size={16}
        />

        Volver a{" "}
        {preset.unitPluralLabel.toLowerCase()}
      </Link>


      {/* HERO DE OBRA */}
      <section className="overflow-hidden rounded-[28px] border border-emerald-700/20 bg-[linear-gradient(135deg,rgba(6,78,59,0.98)_0%,rgba(6,95,70,0.94)_48%,rgba(15,118,110,0.84)_100%)] p-6 text-white shadow-[0_18px_45px_rgba(6,78,59,0.16)]">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px] lg:items-center">

          <div className="min-w-0">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-100">
              {preset.unitLabel} · Gestión ambiental
            </p>

            <div className="mt-2 flex flex-wrap items-center gap-3">
              <h1 className="text-3xl font-black leading-tight">
                {obra.nombre ||
                  obra.codigo_obra ||
                  preset.unitLabel}
              </h1>
            </div>

            <p className="mt-3 max-w-3xl text-sm leading-6 text-emerald-50/85">
              {environmentalDescription(
                obra.estado_ambiental
              )}
            </p>


            <div className="mt-5 flex flex-wrap gap-2">

              {obra.codigo_obra && (
                <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold">
                  {obra.codigo_obra}
                </span>
              )}


              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold">
                {statusLabel(
                  obra.estado
                )}
              </span>


              {obra.fecha_inicio && (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold">
                  <CalendarDays
                    aria-hidden="true"
                    size={14}
                  />

                  Inicio{" "}
                  {formatDate(
                    obra.fecha_inicio
                  )}
                </span>
              )}


              {location && (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold">
                  <MapPin
                    aria-hidden="true"
                    size={14}
                  />

                  {location}
                </span>
              )}
            </div>
          </div>


          {/* LECTURA RÁPIDA */}
          <div className="rounded-[20px] border border-white/15 bg-white/[0.07] p-5 backdrop-blur-sm">
            <p className="text-xs font-black uppercase tracking-[0.15em] text-emerald-100/80">
              Estado ambiental
            </p>

            <div className="mt-3">
              <WorkStatus
                value={
                  obra.estado_ambiental
                }
              />
            </div>

            <p className="mt-3 text-sm leading-6 text-emerald-50/80">
              {environmentalDescription(
                obra.estado_ambiental
              )}
            </p>

            {obra.perfil_ambiental && (
              <div className="mt-4 border-t border-white/10 pt-4">
                <p className="text-xs text-emerald-50/70">
                  Perfil ambiental
                </p>

                <div className="mt-2">
                  <ScopeBadge
                    label={String(
                      obra.perfil_ambiental
                    ).replaceAll(
                      "_",
                      " "
                    )}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      <Outlet
        context={
          state.workspace
        }
      />
    </main>
  );
}