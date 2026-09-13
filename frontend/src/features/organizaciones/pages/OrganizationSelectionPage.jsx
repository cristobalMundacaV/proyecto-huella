import { Building2, ChevronRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { ErrorState, Pagination } from "@/shared/ui";
import { useAuth } from "@/features/auth/context/AuthContext";
import { useOrganizacionActiva } from "../context/OrganizacionActivaContext";
import { organizationDestination, resolveOrganizationAccess } from "../context/organizationResolution";

const PAGE_SIZE = 6;

export default function OrganizationSelectionPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const organizationState = useOrganizacionActiva();
  const { organizaciones, setActiveOrganizacion } = organizationState;
  const [page, setPage] = useState(1);
  const openedFromSaaS = searchParams.get("desde") === "saas";
  const access = resolveOrganizationAccess({
    status: organizationState.organizationResolutionStatus,
    organizations: organizaciones,
    activeOrganization: organizationState.activeOrganizacion,
  });
  const totalPages = Math.max(1, Math.ceil(organizaciones.length / PAGE_SIZE));
  const visibleOrganizations = useMemo(
    () => organizaciones.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [organizaciones, page],
  );

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);
  useEffect(() => {
    if (access === "ready" && organizaciones.length === 1) {
      navigate(organizationDestination(organizaciones[0]), { replace: true });
    }
  }, [access, navigate, organizaciones]);

  if (access === "resolving") return <PlatformLoader fullScreen title="Cargando organizaciones" />;
  if (user?.is_superuser && !openedFromSaaS) return <Navigate to="/saas" replace />;
  if (access === "error") return <main className="flex min-h-screen items-center justify-center bg-slate-100 p-5"><ErrorState title="No pudimos cargar tus organizaciones" description={organizationState.errorOrganizaciones} onRetry={() => organizationState.refreshOrganizaciones().catch(() => undefined)} /></main>;
  if (access === "no-organization") return <main className="flex min-h-screen items-center justify-center bg-slate-100 p-5"><ErrorState title="Tu cuenta no tiene una organización" description="Solicita a un administrador que vincule tu cuenta a una organización para poder continuar." /></main>;
  if (organizaciones.length === 1) return <PlatformLoader fullScreen title="Abriendo organización" />;
  if (access === "ready" && !openedFromSaaS) return <Navigate to={organizationDestination(organizationState.activeOrganizacion)} replace />;

  const selectOrganization = (organization) => {
    setActiveOrganizacion(organization);
    navigate(organizationDestination(organization), { replace: true });
  };

  return <main className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,.07),transparent_30%),#f1f5f9] p-5">
    <section className="w-full max-w-2xl rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_22px_60px_rgba(15,23,42,.12)] sm:p-7">
      <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-700">Carbono Zero</p>
      <h1 className="mt-2 text-3xl font-black text-slate-950">¿En qué organización quieres trabajar?</h1>
      <p className="mt-2 text-slate-600">Tu rol, permisos y espacios de trabajo se mantienen separados en cada organización.</p>
      <div className="mt-6 grid gap-3">
        {visibleOrganizations.map((organization) => <button key={organization.organizacion_id} type="button" onClick={() => selectOrganization(organization)} className="group flex min-h-[82px] items-center gap-4 rounded-2xl border border-slate-200 p-4 text-left shadow-[0_4px_14px_rgba(15,23,42,.025)] transition hover:-translate-y-0.5 hover:border-emerald-400 hover:bg-emerald-50/60 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-800"><Building2 size={22} /></span>
          <span className="min-w-0 flex-1"><b className="block truncate text-lg text-slate-950">{organization.nombre}</b><span className="mt-1 block text-sm capitalize text-slate-600">{organization.preset}</span></span>
          <ChevronRight className="shrink-0 text-emerald-700 transition group-hover:translate-x-1" />
        </button>)}
      </div>
      <Pagination page={page} totalPages={totalPages} totalItems={organizaciones.length} pageSize={PAGE_SIZE} itemLabel="organizaciones" onChange={setPage} />
    </section>
  </main>;
}
