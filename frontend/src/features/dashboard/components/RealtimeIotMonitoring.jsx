import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Gauge,
  Radio,
  RefreshCw,
  Signal,
  Zap,
} from "lucide-react";

import KpiCard from "@/shared/components/KpiCard";
import Pagination from "@/shared/components/Pagination";
import { getIotKpis, getIotUltimasLecturas } from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";

const POLL_INTERVAL_MS = 10000;
const LECTURAS_PAGE_SIZE = 8;

const formatDateTime = (value) => {
  if (!value) {
    return "Sin datos";
  }

  return new Intl.DateTimeFormat("es-CL", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value));
};

const formatTipo = (value) =>
  String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());

function RealtimeIotMonitoring({ activeConstructoraId }) {
  const [kpis, setKpis] = useState(null);
  const [lecturas, setLecturas] = useState([]);
  const [lecturasPage, setLecturasPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const totalLecturasPages = Math.max(
    1,
    Math.ceil(lecturas.length / LECTURAS_PAGE_SIZE)
  );
  const safeLecturasPage = Math.min(lecturasPage, totalLecturasPages);
  const visibleLecturas = useMemo(() => {
    const startIndex = (safeLecturasPage - 1) * LECTURAS_PAGE_SIZE;
    return lecturas.slice(startIndex, startIndex + LECTURAS_PAGE_SIZE);
  }, [lecturas, safeLecturasPage]);

  useEffect(() => {
    let isCancelled = false;

    if (!activeConstructoraId) {
      return undefined;
    }

    let timeoutId;

    const loadIotData = async ({ showLoading = false } = {}) => {
      if (document.visibilityState === "hidden") {
        timeoutId = window.setTimeout(loadIotData, POLL_INTERVAL_MS);
        return;
      }

      try {
        if (showLoading) {
          setLoading(true);
        }

        const [kpisResult, lecturasResult] = await Promise.all([
          getIotKpis(activeConstructoraId),
          getIotUltimasLecturas(activeConstructoraId),
        ]);

        if (!isCancelled) {
          setKpis(kpisResult);
          setLecturas(Array.isArray(lecturasResult) ? lecturasResult : []);
          setError("");
          setLoading(false);
        }
      } catch (loadError) {
        if (!isCancelled) {
          setError(
            loadError.response?.data?.error ||
              "No se pudo cargar el monitoreo IoT."
          );
          setLoading(false);
        }
      } finally {
        if (!isCancelled) {
          timeoutId = window.setTimeout(loadIotData, POLL_INTERVAL_MS);
        }
      }
    };

    loadIotData({ showLoading: true });

    return () => {
      isCancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [activeConstructoraId]);

  return (
    <section className="premium-card premium-card-interactive slide-up rounded-2xl bg-[var(--bg-surface)] p-4 shadow-[var(--shadow-card)] ring-1 ring-white/45 sm:p-6">
      <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary-dark)]">
            Monitoreo en tiempo real
          </p>
          <h2 className="mt-1 text-xl font-bold text-[var(--text-main)]">
            Lecturas operativas.
          </h2>
        </div>
        <div className="premium-badge premium-badge--success flex w-fit items-center gap-2 px-4 py-2 uppercase tracking-wide text-[var(--primary-dark)]">
          <Signal size={16} />
          Modo IoT activo
        </div>
      </div>

      {error && (
        <div className="mb-5 rounded-2xl border border-[#F1C7C7] bg-[var(--danger-bg)] px-4 py-3 text-sm text-[#B42318]">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-6 text-sm text-[var(--text-muted)]">
          Cargando lecturas de sensores...
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              icon={<Radio />}
              title="Lecturas recibidas"
              value={formatNumber(kpis?.total_lecturas || 0, 0)}
              tone="neutral"
            />
            <KpiCard
              icon={<Zap />}
              title="Emisiones de hoy"
              value={`${formatNumber(
                kpis?.emisiones_totales_kg_co2e || 0,
                2
              )} kg CO2e`}
            />
            <KpiCard
              icon={<Gauge />}
              title="Etapa con más emisiones hoy"
              value={
                <span className="block text-xl leading-tight">
                  {kpis?.etapa_mayor_emision_hoy || "Sin datos"}
                </span>
              }
              detail={`${formatNumber(
                kpis?.etapa_mayor_emision_hoy_kg_co2e || 0,
                2
              )} kg CO2e`}
              tone="info"
            />
            <KpiCard
              icon={<Activity />}
              title="Fuente con más emisiones hoy"
              value={
                <span className="block text-xl leading-tight">
                  {formatTipo(kpis?.fuente_emision_mayor_emision_hoy) || "Sin datos"}
                </span>
              }
              detail={`${formatNumber(
                kpis?.fuente_emision_mayor_emision_hoy_kg_co2e || 0,
                2
              )} kg CO2e`}
              tone="warning"
            />
          </div>

          <div className="premium-card-interactive mt-5 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)]">
            <div className="flex flex-col gap-2 border-b border-[var(--border)] px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm font-semibold text-[var(--text-main)]">
                Ultimas lecturas
              </p>
              <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                <RefreshCw size={14} />
                Actualizado: {formatDateTime(kpis?.ultima_actualizacion)}
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="premium-table min-w-full divide-y divide-[var(--border)] text-sm">
                <thead className="bg-[var(--bg-surface)] text-xs uppercase tracking-wide text-[var(--text-muted)]">
                  <tr>
                    <th className="px-4 py-3 text-left">Sensor</th>
                    <th className="px-4 py-3 text-left">Etapa / frente</th>
                    <th className="px-4 py-3 text-left">Tipo</th>
                    <th className="px-4 py-3 text-right">Valor</th>
                    <th className="px-4 py-3 text-right">CO2e</th>
                    <th className="px-4 py-3 text-left">Hora</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {visibleLecturas.length > 0 ? (
                    visibleLecturas.map((lectura) => (
                      <tr key={lectura.id} className="text-[var(--text-muted)] hover:bg-[var(--success-bg)]/60">
                        <td className="whitespace-nowrap px-4 py-3 font-semibold text-[var(--text-main)]">
                          {lectura.sensor}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3">
                          {lectura.etapa_obra}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3">
                          {formatTipo(lectura.tipo)}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-right">
                          {formatNumber(lectura.valor, 2)} {lectura.unidad}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-right">
                          {formatNumber(lectura.co2e_estimado, 2)}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-[var(--text-muted)]">
                          {formatDateTime(lectura.fecha_registro)}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="px-4 py-6 text-center text-[var(--text-muted)]">
                        Aun no hay lecturas simuladas registradas.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="px-4 pb-4">
              <Pagination
                currentPage={safeLecturasPage}
                itemLabel="lecturas"
                onPageChange={setLecturasPage}
                pageSize={LECTURAS_PAGE_SIZE}
                totalItems={lecturas.length}
              />
            </div>
          </div>
        </>
      )}
    </section>
  );
}

export default RealtimeIotMonitoring;
