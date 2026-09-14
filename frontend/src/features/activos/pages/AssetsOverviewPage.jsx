import { useCallback, useEffect, useState } from "react";
import { AlertOctagon, Boxes, CalendarClock, CheckCircle2, MapPinOff, Plus, Radio, Wrench } from "lucide-react";
import ContextContentSkeleton from "@/shared/components/ContextContentSkeleton";
import ChartCard from "@/shared/charts/ChartCard";
import EnvironmentalBarChart from "@/shared/charts/EnvironmentalBarChart";
import EnvironmentalDonutChart from "@/shared/charts/EnvironmentalDonutChart";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { ButtonLink, CZMetricCard, CZPageHero, CZSection, CZStatusBadge, EmptyState, ErrorState } from "@/shared/ui";
import { formatDate } from "@/shared/utils/formatters";
import { getAssets } from "../api/assetsApi";
import { buildAssetsSummary } from "../utils/assetSelectors";

export default function AssetsOverviewPage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ status: "loading", rows: [] });

  const load = useCallback(() => {
    if (!activeOrganizacionId) return;
    setState({ status: "loading", rows: [] });
    getAssets(activeOrganizacionId)
      .then((rows) => setState({ status: "ready", rows: Array.isArray(rows) ? rows : [] }))
      .catch(() => setState({ status: "error", rows: [] }));
  }, [activeOrganizacionId]);

  useEffect(() => { load(); }, [load]);

  if (state.status === "loading") return <ContextContentSkeleton charts={4} kpis={8} />;
  if (state.status === "error") return <ErrorState description="Intenta nuevamente para ver el estado de tus activos." onRetry={load} title="No pudimos cargar tus activos" />;

  const summary = buildAssetsSummary(state.rows);

  return <main className="space-y-4 pb-4">
    <CZPageHero>
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-200">Recursos operacionales</p>
          <h1 className="mt-2 text-3xl font-black leading-tight sm:text-4xl">Activos de la organización</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-emerald-50/85">Controla la flota, maquinaria, equipos y dispositivos que participan en tu operación y conoce su estado, uso y trazabilidad ambiental.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-white backdrop-blur">{summary.total} {summary.total === 1 ? "activo registrado" : "activos registrados"}</span>
          </div>
        </div>
        <ButtonLink className="self-start border-white/30 bg-white text-emerald-900 shadow-[0_8px_24px_rgba(0,0,0,0.12)] hover:bg-emerald-50 lg:self-center" leftIcon={Plus} to="/activos/flota" variant="secondary">Registrar activo</ButtonLink>
      </div>
    </CZPageHero>

    {!summary.total ? <EmptyState description="Incorpora maquinaria, vehículos, equipos, medidores o infraestructura cuando formen parte real de tu operación." primaryAction={<ButtonLink leftIcon={Plus} to="/activos/flota">Registrar primer activo</ButtonLink>} title="Aún no hay activos registrados" /> : <>
      <section aria-label="Indicadores de activos" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <CZMetricCard icon={Boxes} label="Activos totales" tone="blue" value={summary.total} />
        <CZMetricCard icon={CheckCircle2} label="En operación" supportingText={`${summary.total ? Math.round((summary.operativos / summary.total) * 100) : 0}% del total`} tone="emerald" value={summary.operativos} />
        <CZMetricCard icon={Wrench} label="Requieren mantención" tone={summary.requierenMantencion ? "amber" : "emerald"} value={summary.requierenMantencion} />
        <CZMetricCard icon={AlertOctagon} label="Fuera de servicio" tone={summary.fueraDeServicio ? "rose" : "emerald"} value={summary.fueraDeServicio} />
        <CZMetricCard icon={MapPinOff} label="Asignados a obras" supportingText="El modelo actual no registra asignación de activos a obra" tone="neutral" value={summary.asignadosAObra} />
        <CZMetricCard icon={MapPinOff} label="Sin asignar" supportingText="Todos los activos, hasta que exista asignación a obra" tone="neutral" value={summary.sinAsignar} />
        <CZMetricCard icon={Radio} label="Con telemetría" supportingText={`${summary.total ? Math.round((summary.conTelemetria / summary.total) * 100) : 0}% del total`} tone="violet" value={summary.conTelemetria} />
        <CZMetricCard icon={CalendarClock} label="Mantenciones próximas" tone={summary.mantencionesProximas ? "amber" : "emerald"} value={summary.mantencionesProximas} />
      </section>

      <section className="grid gap-3 xl:grid-cols-2">
        <ChartCard description="Distribución de tu flota según disponibilidad real." empty={!summary.fleet.some((row) => row.value > 0)} title="Estado de la flota">
          <EnvironmentalBarChart data={summary.fleet} height={260} />
        </ChartCard>
        <ChartCard description="Los activos aún no registran una obra asignada en el modelo de datos." title="Activos por obra">
          <EnvironmentalDonutChart centerLabel="Total" centerUnit="activos" centerValue={summary.total} data={[{ name: "Sin asignar", value: summary.sinAsignar, color: "#94a3b8" }]} height={240} valueFormatter={(value) => `${value} activos`} />
        </ChartCard>
      </section>

      <section className="grid gap-3 xl:grid-cols-[1fr_1.2fr]">
        <ChartCard description="Composición del inventario por tipo de activo." empty={!summary.byType.length} title="Activos por tipo">
          <EnvironmentalDonutChart data={summary.byType} height={240} valueFormatter={(value) => `${value} activos`} />
        </ChartCard>

        <CZSection>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div><p className="text-[10px] font-black uppercase tracking-[0.14em] text-emerald-700">Mantenciones</p><h2 className="mt-1 text-xl font-black">Próximas mantenciones</h2><p className="mt-1 max-w-xl text-xs leading-5 text-[var(--text-muted)]">Próximos vencimientos ordenados por urgencia.</p></div>
            <ButtonLink size="sm" to="/activos/mantenciones" variant="secondary">Ver todas</ButtonLink>
          </div>
          {summary.upcomingMaintenances.length
            ? <ul className="mt-4 space-y-2">{summary.upcomingMaintenances.slice(0, 6).map((row) => <li className="flex items-center justify-between gap-3 rounded-[var(--radius-card)] border border-[var(--border-default)] bg-white px-4 py-3" key={row.id}>
              <div className="min-w-0"><p className="truncate font-bold text-[var(--text-primary)]">{row.assetName}</p><p className="text-xs text-[var(--text-muted)]">{row.tipo || "Mantención"} · {row.fechaProgramada ? formatDate(row.fechaProgramada) : "Sin fecha"}</p></div>
              <CZStatusBadge tone={row.priority === "vencida" ? "danger" : "warning"}>{row.priority === "vencida" ? "Vencida" : "Próxima"}</CZStatusBadge>
            </li>)}</ul>
            : <EmptyState className="mt-4" description="No hay mantenciones programadas o vencidas en este momento." title="Sin mantenciones pendientes" />}
        </CZSection>
      </section>
    </>}
  </main>;
}
