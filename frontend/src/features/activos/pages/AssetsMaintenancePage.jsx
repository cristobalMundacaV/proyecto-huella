import { useCallback, useEffect, useMemo, useState } from "react";
import ContextContentSkeleton from "@/shared/components/ContextContentSkeleton";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { CZStatusBadge, EmptyState, ErrorState, PageHeader, Tabs, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDate } from "@/shared/utils/formatters";
import { getAssets } from "../api/assetsApi";
import { assetTypeLabel } from "../utils/assetSelectors";

const STATE_TONE = { programado: "info", en_proceso: "warning", realizado: "success", vencido: "danger", cancelado: "neutral" };
const STATE_LABEL = { programado: "Programado", en_proceso: "En proceso", realizado: "Realizado", vencido: "Vencido", cancelado: "Cancelado" };

function flattenMaintenances(assets, today) {
  return assets.flatMap((asset) => (Array.isArray(asset.mantenimientos) ? asset.mantenimientos : []).map((item) => {
    const scheduled = item.fecha_programada ? new Date(item.fecha_programada) : null;
    const isOverdue = item.estado === "programado" && scheduled && !Number.isNaN(scheduled.getTime()) && scheduled < today;
    return { ...item, assetId: asset.id, assetName: asset.nombre, assetTipo: asset.tipo, effectiveState: isOverdue ? "vencido" : item.estado };
  }));
}

const TABS = [
  { value: "proximas", label: "Próximas" },
  { value: "vencidas", label: "Vencidas" },
  { value: "en_proceso", label: "En proceso" },
  { value: "historial", label: "Historial" },
];

export default function AssetsMaintenancePage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ status: "loading", rows: [] });
  const [tab, setTab] = useState("proximas");

  const load = useCallback(() => {
    if (!activeOrganizacionId) return;
    setState({ status: "loading", rows: [] });
    getAssets(activeOrganizacionId)
      .then((rows) => setState({ status: "ready", rows: Array.isArray(rows) ? rows : [] }))
      .catch(() => setState({ status: "error", rows: [] }));
  }, [activeOrganizacionId]);

  useEffect(() => { load(); }, [load]);

  const today = useMemo(() => new Date(), []);
  const maintenances = useMemo(() => flattenMaintenances(state.rows, today), [state.rows, today]);

  const filtered = useMemo(() => {
    const byTab = {
      proximas: (item) => item.effectiveState === "programado",
      vencidas: (item) => item.effectiveState === "vencido",
      en_proceso: (item) => item.effectiveState === "en_proceso",
      historial: (item) => ["realizado", "cancelado"].includes(item.effectiveState),
    };
    return [...maintenances]
      .filter(byTab[tab])
      .sort((a, b) => (a.fecha_programada || a.fecha_realizada || "").localeCompare(b.fecha_programada || b.fecha_realizada || ""));
  }, [maintenances, tab]);

  const counts = useMemo(() => ({
    proximas: maintenances.filter((item) => item.effectiveState === "programado").length,
    vencidas: maintenances.filter((item) => item.effectiveState === "vencido").length,
    en_proceso: maintenances.filter((item) => item.effectiveState === "en_proceso").length,
    historial: maintenances.filter((item) => ["realizado", "cancelado"].includes(item.effectiveState)).length,
  }), [maintenances]);

  if (state.status === "loading") return <ContextContentSkeleton charts={0} kpis={0} />;
  if (state.status === "error") return <ErrorState description="Intenta nuevamente para ver las mantenciones de tus activos." onRetry={load} title="No pudimos cargar las mantenciones" />;

  return <main className="space-y-4 pb-4">
    <PageHeader description="Mantenciones preventivas y correctivas de la flota, maquinaria y equipos de tu organización." title="Mantenciones" />
    <Tabs activeTab={tab} onChange={setTab} tabs={TABS.map((item) => ({ ...item, label: `${item.label} (${counts[item.value]})` }))} />
    {!filtered.length
      ? <EmptyState description="No hay registros de mantención en esta categoría por ahora." title="Sin resultados" />
      : <TableShell>
        <TableHead><tr>
          <TableCell as="th">Activo</TableCell>
          <TableCell as="th">Tipo de activo</TableCell>
          <TableCell as="th">Intervención</TableCell>
          <TableCell as="th">Estado</TableCell>
          <TableCell as="th">Fecha programada</TableCell>
          <TableCell as="th">Fecha realizada</TableCell>
        </tr></TableHead>
        <TableBody columns={6}>
          {filtered.map((item) => <tr key={item.id}>
            <TableCell><b>{item.assetName}</b></TableCell>
            <TableCell>{assetTypeLabel(item.assetTipo)}</TableCell>
            <TableCell>{item.tipo || "Sin especificar"}</TableCell>
            <TableCell><CZStatusBadge tone={STATE_TONE[item.effectiveState] || "neutral"}>{STATE_LABEL[item.effectiveState] || item.effectiveState}</CZStatusBadge></TableCell>
            <TableCell>{item.fecha_programada ? formatDate(item.fecha_programada) : "—"}</TableCell>
            <TableCell>{item.fecha_realizada ? formatDate(item.fecha_realizada) : "—"}</TableCell>
          </tr>)}
        </TableBody>
      </TableShell>}
  </main>;
}
