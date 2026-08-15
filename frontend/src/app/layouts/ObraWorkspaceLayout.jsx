import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { NavLink, Navigate, Outlet, useParams } from "react-router-dom";
import { getObraDetail } from "@/shared/services/api";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

const tabs = ["resumen", "operacion", "indicadores", "problemas", "evidencias", "timeline", "informes"];

export default function ObraWorkspaceLayout() {
  const { obraId } = useParams();
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const [obra, setObra] = useState(null);
  const [status, setStatus] = useState("loading");
  useEffect(() => {
    let active = true; setStatus("loading");
    getObraDetail(obraId).then((data) => {
      if (!active) return;
      const owner = data.organizacion_id || data.organizacion?.organizacion_id || data.organizacion;
      const allowedOwners = new Set([activeOrganizacionId, activeOrganizacion?.id, activeOrganizacion?.nombre].filter(Boolean).map(String));
      if (owner && !allowedOwners.has(String(owner))) setStatus("foreign");
      else { setObra(data); setStatus("ready"); }
    }).catch(() => active && setStatus("missing"));
    return () => { active = false; };
  }, [activeOrganizacion, activeOrganizacionId, obraId]);
  if (status === "foreign") return <Navigate to="/obras" replace />;
  if (status === "missing") return <section className="rounded-2xl border p-6">No se encontró la obra en la organización activa.</section>;
  if (status !== "ready") return <div className="flex items-center gap-3 py-12"><Loader2 className="animate-spin" /> Cargando obra...</div>;
  return <div className="space-y-6">
    <header><p className="text-xs font-black uppercase tracking-widest text-emerald-700">Workspace de obra</p><h1 className="mt-1 text-3xl font-black">{obra.nombre || obra.codigo_obra}</h1></header>
    <nav className="flex flex-wrap gap-2">{tabs.map((tab) => <NavLink key={tab} to={tab} className={({isActive}) => `rounded-xl border px-3 py-2 text-sm font-bold ${isActive ? "border-emerald-300 bg-emerald-50 text-emerald-800" : "border-slate-200 bg-white text-slate-600"}`}>{tab}</NavLink>)}</nav>
    <Outlet context={{ obra }} />
  </div>;
}

export function ObraWorkspaceSection({ title }) {
  return <section className="rounded-3xl border border-[var(--border)] bg-white p-6 shadow-[var(--shadow-card)]"><h2 className="text-xl font-black">{title}</h2><p className="mt-2 text-sm text-slate-500">Base de routing del workspace preparada. La experiencia definitiva se completa en UX-04/UX-05.</p></section>;
}
