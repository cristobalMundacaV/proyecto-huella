import { useCallback, useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useOutletContext } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { ErrorState, LoadingState, SectionHeader } from "@/shared/ui";
import { getWorkOperation } from "../services/operationApi";

const links = [
  ["", "Resumen"],
  ["energia", "Energía"],
  ["agua", "Agua"],
  ["combustibles", "Combustibles"],
  ["transporte", "Transporte"],
  ["materiales", "Materiales"],
  ["residuos", "Residuos"],
  ["ruido", "Ruido"],
  ["hidrica-suelo", "Hídrica y suelo"],
];

export default function OperationLayout() {
  const workspace = useOutletContext();
  const { activeOrganizacionId } = useOrganizacionActiva();
  const workId = workspace.obra.id || workspace.obra.obra_id;
  const [state, setState] = useState({ status: "loading", data: null });
  const requestRef = useRef(0);

  const load = useCallback(() => {
    if (!activeOrganizacionId || !workId) return;
    const requestId = ++requestRef.current;
    setState({ status: "loading", data: null });
    getWorkOperation(activeOrganizacionId, workId)
      .then((data) => {
        if (requestRef.current === requestId) setState({ status: "ready", data });
      })
      .catch(() => {
        if (requestRef.current === requestId) setState({ status: "error", data: null });
      });
  }, [activeOrganizacionId, workId]);

  useEffect(() => {
    load();
    return () => { requestRef.current += 1; };
  }, [load]);

  return <div className="space-y-6">
    <SectionHeader title="Operación" description="Revisa lo que está ocurriendo en esta unidad." />
    <nav
      aria-label="Dominios operacionales"
      className="
    overflow-hidden
    rounded-[18px]
    border
    border-slate-200
    bg-white
    p-1.5
    shadow-[0_8px_24px_rgba(15,23,42,0.04)]
  "
    >
      <div className="flex max-w-full gap-1 overflow-x-auto">
        {links.map(([path, label]) => (
          <NavLink
            end={!path}
            key={label}
            to={path || "."}
            className={({ isActive }) =>
              `
            shrink-0
            rounded-[12px]
            px-4
            py-2.5
            text-sm
            font-black
            transition
            duration-150
            focus-visible:outline-none
            focus-visible:shadow-[var(--focus-ring)]
            ${isActive
                ? "bg-emerald-700 text-white shadow-sm"
                : "text-[var(--text-secondary)] hover:bg-emerald-50 hover:text-emerald-800"
              }
          `
            }
          >
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
    {state.status === "loading" && <LoadingState label="Cargando información operacional" />}
    {state.status === "error" && <ErrorState description="No fue posible preparar la información operacional de esta unidad." onRetry={load} />}
    {state.status === "ready" && <Outlet context={{ ...workspace, operation: state.data }} />}
  </div>;
}
