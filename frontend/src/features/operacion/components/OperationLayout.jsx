import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useOutletContext } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { ErrorState, LoadingState, SectionHeader } from "@/shared/ui";
import { getWorkOperation } from "../services/operationApi";

const links = [["", "Resumen"], ["energia", "Energía"], ["agua", "Agua"], ["combustibles", "Combustibles"], ["transporte", "Transporte"], ["materiales", "Materiales"], ["residuos", "Residuos"], ["ruido", "Ruido"], ["hidrica-suelo", "Hídrica/suelo"]];

export default function OperationLayout() {
  const workspace = useOutletContext();
  const { activeOrganizacionId } = useOrganizacionActiva();
  const workId = workspace.obra.id || workspace.obra.obra_id;
  const [state, setState] = useState({ status: "loading", data: null });
  const load = useCallback(() => {
    setState({ status: "loading", data: null });
    getWorkOperation(activeOrganizacionId, workId).then((data) => setState({ status: "ready", data })).catch(() => setState({ status: "error", data: null }));
  }, [activeOrganizacionId, workId]);
  useEffect(() => { load(); }, [load]);

  return <div className="space-y-6">
    <SectionHeader title="Operación ambiental" description="Consumos, movimientos y mediciones dentro del alcance de esta obra." />
    <nav aria-label="Dominios operacionales" className="flex max-w-full gap-1 overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-1">
      {links.map(([path, label]) => <NavLink end={!path} key={label} to={path || "."} className={({ isActive }) => `shrink-0 rounded-[var(--radius-md)] px-3 py-2 text-sm font-bold focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] ${isActive ? "bg-[var(--brand-primary)] text-white" : "text-[var(--text-secondary)] hover:bg-[var(--bg-surface-subtle)]"}`}>{label}</NavLink>)}
    </nav>
    {state.status === "loading" && <LoadingState label="Cargando operación de la obra" />}
    {state.status === "error" && <ErrorState description="No fue posible preparar el contexto operacional básico de esta obra." onRetry={load} />}
    {state.status === "ready" && <Outlet context={{ ...workspace, operation: state.data }} />}
  </div>;
}
