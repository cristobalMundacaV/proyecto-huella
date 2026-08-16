import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { Link, NavLink, Outlet, useParams } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { getWorkWorkspace } from "@/features/obras/services/workspaceApi";
import WorkStatus from "@/features/obras/components/WorkStatus";
import { ErrorState, LoadingState, PageHeader, ScopeBadge } from "@/shared/ui";

const tabs = [
  ["resumen", "Resumen"], ["operacion", "Operación"], ["indicadores", "Indicadores"],
  ["problemas", "Problemas y acciones"], ["evidencias", "Evidencia"], ["timeline", "Timeline"],
];

export default function ObraWorkspaceLayout() {
  const { obraId } = useParams();
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ status: "loading", workspace: null });
  const requestRef = useRef(0);
  const load = useCallback(() => {
    if (!activeOrganizacionId) return;
    const requestId = ++requestRef.current;
    setState({ status: "loading", workspace: null });
    getWorkWorkspace(activeOrganizacionId, obraId).then((workspace) => { if(requestRef.current===requestId)setState({ status: "ready", workspace }); }).catch(() => { if(requestRef.current===requestId)setState({ status: "missing", workspace: null }); });
  }, [activeOrganizacionId, obraId]);
  useEffect(() => { load(); }, [load]);
  if (state.status === "loading") return <LoadingState label="Cargando contexto de la obra" />;
  if (state.status === "missing") return <ErrorState title="No se encontró la obra" description="La obra no existe o no está disponible en la organización activa." />;
  const { obra, context } = state.workspace;
  return <div className="space-y-6">
    <Link className="inline-flex items-center gap-2 text-sm font-bold text-[var(--text-secondary)]" to="/obras"><ArrowLeft size={16} />Todas las obras</Link>
    <PageHeader eyebrow="Workspace de obra" title={obra.nombre || obra.tipo_proyecto || obra.codigo_obra} description={`Código ${obra.codigo_obra} · ${activeOrganizacion?.nombre}`} status={<WorkStatus value={obra.estado_ambiental} />} metadata={<div className="flex flex-wrap gap-2"><ScopeBadge label={obra.perfil_ambiental || "Perfil por definir"} /><WorkStatus value={obra.estado} />{obra.fecha && <span>Inicio: {obra.fecha}</span>}{obra.fecha_cierre_ambiental && <span>Cierre ambiental: {obra.fecha_cierre_ambiental}</span>}</div>} />
    <nav aria-label="Secciones de la obra" className="flex max-w-full gap-1 overflow-x-auto border-b border-[var(--border-default)]">
      {tabs.map(([path, label]) => <NavLink key={path} to={path} className={({ isActive }) => `shrink-0 border-b-2 px-3 py-3 text-sm font-bold focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] ${isActive ? "border-[var(--brand-primary)] text-[var(--brand-primary)]" : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"}`}>{label}</NavLink>)}
    </nav>
    <Outlet context={state.workspace} />
  </div>;
}
