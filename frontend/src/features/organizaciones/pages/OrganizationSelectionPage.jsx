import { Building2, ChevronRight } from "lucide-react";
import { useEffect } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { useAuth } from "@/features/auth/context/AuthContext";
import { useOrganizacionActiva } from "../context/OrganizacionActivaContext";

export default function OrganizationSelectionPage() {
  const navigate = useNavigate(); const [searchParams] = useSearchParams(); const { user } = useAuth(); const { organizaciones, loadingOrganizaciones, setActiveOrganizacion } = useOrganizacionActiva(); const openedFromSaaS = searchParams.get("desde") === "saas";
  useEffect(() => { if (!loadingOrganizaciones && organizaciones.length === 1) { setActiveOrganizacion(organizaciones[0]); navigate("/inicio", { replace: true }); } }, [loadingOrganizaciones, navigate, organizaciones, setActiveOrganizacion]);
  if (loadingOrganizaciones) return <PlatformLoader fullScreen title="Cargando organizaciones" />;
  if (user?.is_superuser && !openedFromSaaS) return <Navigate to="/saas" replace />;
  if (organizaciones.length === 1) return <PlatformLoader fullScreen title="Abriendo organización" />;
  return <main className="flex min-h-screen items-center justify-center bg-slate-100 p-5"><section className="w-full max-w-2xl rounded-3xl border border-slate-200 bg-white p-7 shadow-xl"><p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-700">Carbono Zero</p><h1 className="mt-2 text-3xl font-black">¿En qué organización quieres trabajar?</h1><p className="mt-2 text-slate-600">Tu rol, permisos y espacios de trabajo se mantienen separados en cada organización.</p><div className="mt-6 grid gap-3">{organizaciones.map((organization) => <button key={organization.organizacion_id} type="button" onClick={() => { setActiveOrganizacion(organization); navigate("/inicio", { replace: true }); }} className="group flex items-center gap-4 rounded-2xl border border-slate-200 p-5 text-left transition hover:border-emerald-500 hover:bg-emerald-50"><span className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-100 text-emerald-800"><Building2 size={22} /></span><span className="min-w-0 flex-1"><b className="block text-lg">{organization.nombre}</b><span className="mt-1 block text-sm capitalize text-slate-600">{organization.preset}</span></span><ChevronRight className="text-emerald-700 transition group-hover:translate-x-1" /></button>)}</div></section></main>;
}
