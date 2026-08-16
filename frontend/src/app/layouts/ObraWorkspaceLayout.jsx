import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { Link, NavLink, Outlet, useParams } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { getWorkWorkspace } from "@/features/obras/services/workspaceApi";
import WorkStatus from "@/features/obras/components/WorkStatus";
import { getActivePreset } from "@/presets/registry";
import { ErrorState, LoadingState, PageHeader, ScopeBadge } from "@/shared/ui";
import { formatDate } from "@/shared/utils/formatters";

const tabs = [
  ["resumen", "Resumen"],
  ["operacion", "Operación"],
  ["indicadores", "Indicadores"],
  ["problemas", "Problemas"],
  ["evidencias", "Evidencias"],
  ["timeline", "Historial"],
];

export default function ObraWorkspaceLayout() {
  const { obraId } = useParams();
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const preset = getActivePreset(activeOrganizacion?.preset || "construccion");
  const [state, setState] = useState({ status: "loading", workspace: null });
  const requestRef = useRef(0);

  const load = useCallback(() => {
    if (!activeOrganizacionId) return;
    const requestId = ++requestRef.current;
    setState({ status: "loading", workspace: null });
    getWorkWorkspace(activeOrganizacionId, obraId)
      .then((workspace) => {
        if (requestRef.current === requestId) setState({ status: "ready", workspace });
      })
      .catch((error) => {
        if (requestRef.current !== requestId) return;
        setState({ status: error.response?.status === 404 ? "missing" : "error", workspace: null });
      });
  }, [activeOrganizacionId, obraId]);

  useEffect(() => {
    load();
    return () => { requestRef.current += 1; };
  }, [load]);

  if (state.status === "loading") return <LoadingState label={`Cargando ${preset.unitLabel.toLowerCase()}`} />;
  if (state.status === "missing") return <ErrorState title={`${preset.unitLabel} no disponible`} description={`La ${preset.unitLabel.toLowerCase()} no existe o no está disponible en la organización activa.`} />;
  if (state.status === "error") return <ErrorState title="No pudimos cargar esta unidad" description="Intenta nuevamente para recuperar su contexto de gestión." onRetry={load} />;

  const { obra } = state.workspace;
  const secondary = [obra.codigo_obra ? `Código ${obra.codigo_obra}` : null, obra.ubicacion || null].filter(Boolean).join(" · ");

  return <main className="space-y-5">
    <Link className="inline-flex items-center gap-2 text-sm font-bold text-[var(--text-secondary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to="/obras">
      <ArrowLeft aria-hidden="true" size={16} />{preset.unitPluralLabel}
    </Link>

    <PageHeader
      title={obra.nombre || obra.codigo_obra || preset.unitLabel}
      description={secondary || `Detalle de la ${preset.unitLabel.toLowerCase()}`}
      status={<WorkStatus value={obra.estado_ambiental} />}
      metadata={<div className="flex flex-wrap items-center gap-2 text-sm text-[var(--text-secondary)]">
        <WorkStatus value={obra.estado} />
        {obra.fecha_inicio && <span>Inicio {formatDate(obra.fecha_inicio)}</span>}
        {obra.perfil_ambiental && <ScopeBadge label={String(obra.perfil_ambiental).replaceAll("_", " ")} />}
      </div>}
    />

    <nav aria-label={`Secciones de la ${preset.unitLabel.toLowerCase()}`} className="flex max-w-full gap-1 overflow-x-auto border-b border-[var(--border-default)]">
      {tabs.map(([path, label]) => <NavLink
        key={path}
        to={path}
        className={({ isActive }) => `shrink-0 border-b-2 px-3 py-3 text-sm font-bold focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] ${isActive ? "border-[var(--brand-primary)] text-[var(--brand-primary)]" : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"}`}
      >{label}</NavLink>)}
    </nav>

    <Outlet context={state.workspace} />
  </main>;
}
