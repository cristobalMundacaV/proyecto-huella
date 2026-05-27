import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  Gauge,
  Radio,
  RefreshCw,
  Signal,
  Zap,
} from "lucide-react";

import Pagination from "@/shared/components/Pagination";
import { getIotKpis, getIotUltimasLecturas } from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";

const POLL_INTERVAL_MS = 3000;
const LECTURAS_PAGE_SIZE = 8;
const ROW_HIGHLIGHT_MS = 1400;

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
  const [newLecturaIds, setNewLecturaIds] = useState(() => new Set());
  const [streamTick, setStreamTick] = useState(0);
  const previousLecturaIdsRef = useRef(new Set());
  const clearNewRowsTimeoutRef = useRef(null);

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
          const nextLecturas = Array.isArray(lecturasResult) ? lecturasResult : [];
          const previousIds = previousLecturaIdsRef.current;
          const nextIds = new Set(nextLecturas.map((lectura) => lectura.id));
          const insertedIds = nextLecturas
            .filter((lectura) => !previousIds.has(lectura.id))
            .map((lectura) => lectura.id);

          if (insertedIds.length && previousIds.size > 0) {
            setNewLecturaIds(new Set(insertedIds));
            setStreamTick((currentTick) => currentTick + 1);
            setLecturasPage(1);

            if (clearNewRowsTimeoutRef.current) {
              window.clearTimeout(clearNewRowsTimeoutRef.current);
            }

            clearNewRowsTimeoutRef.current = window.setTimeout(() => {
              setNewLecturaIds(new Set());
            }, ROW_HIGHLIGHT_MS);
          }

          previousLecturaIdsRef.current = nextIds;
          setKpis(kpisResult);
          setLecturas(nextLecturas);
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
      if (clearNewRowsTimeoutRef.current) {
        window.clearTimeout(clearNewRowsTimeoutRef.current);
      }
    };
  }, [activeConstructoraId]);

  return (
    <section className="premium-card premium-card-interactive slide-up overflow-hidden rounded-2xl bg-[var(--bg-surface)] p-4 shadow-[var(--shadow-card)] ring-1 ring-white/45 sm:p-6">
      <style>{`
        @keyframes iotRowIn {
          0% { opacity: 0; transform: translateY(-8px) scale(0.985); box-shadow: inset 4px 0 0 rgba(14, 124, 102, 0); }
          35% { opacity: 1; transform: translateY(0) scale(1); box-shadow: inset 4px 0 0 rgba(14, 124, 102, 0.95); }
          100% { opacity: 1; transform: translateY(0) scale(1); box-shadow: inset 4px 0 0 rgba(14, 124, 102, 0); }
        }

        @keyframes iotKpiPulse {
          0% { transform: scale(0.985); box-shadow: 0 12px 30px rgba(14, 124, 102, 0.08); }
          45% { transform: scale(1.015); box-shadow: 0 18px 44px rgba(14, 124, 102, 0.18); }
          100% { transform: scale(1); box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06); }
        }

        @keyframes liveDotPulse {
          0%, 100% { opacity: 0.45; transform: scale(0.82); }
          50% { opacity: 1; transform: scale(1.18); }
        }
      `}</style>

      <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary-dark)]">
            Monitoreo en tiempo real
          </p>
          <h2 className="mt-1 text-xl font-bold text-[var(--text-main)]">
            Lecturas operativas.
          </h2>
          <p className="mt-1 text-sm font-medium text-[var(--text-muted)]">
            Actualización automática cada {POLL_INTERVAL_MS / 1000}s con inserción fluida de nuevas lecturas.
          </p>
        </div>
        <div className="premium-badge premium-badge--success flex w-fit items-center gap-2 px-4 py-2 uppercase tracking-wide text-[var(--primary-dark)]">
          <span className="relative flex h-3 w-3 items-center justify-center">
            <span className="absolute h-3 w-3 rounded-full bg-emerald-500/30" style={{ animation: "liveDotPulse 1.2s ease-in-out infinite" }} />
            <span className="h-2 w-2 rounded-full bg-emerald-600" />
          </span>
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
            <RealtimeKpiCard
              icon={<Radio />}
              title="Lecturas recibidas"
              value={Number(kpis?.total_lecturas || 0)}
              decimals={0}
              tone="neutral"
              pulseKey={streamTick}
            />
            <RealtimeKpiCard
              icon={<Zap />}
              title="Emisiones de hoy"
              value={Number(kpis?.emisiones_totales_kg_co2e || 0)}
              decimals={2}
              suffix=" kg CO2e"
              tone="success"
              pulseKey={streamTick}
            />
            <RealtimeInfoCard
              icon={<Gauge />}
              title="Etapa con más emisiones hoy"
              value={kpis?.etapa_mayor_emision_hoy || "Sin datos"}
              detail={`${formatNumber(
                kpis?.etapa_mayor_emision_hoy_kg_co2e || 0,
                2
              )} kg CO2e`}
              tone="info"
              pulseKey={streamTick}
            />
            <RealtimeInfoCard
              icon={<Activity />}
              title="Fuente con más emisiones hoy"
              value={formatTipo(kpis?.fuente_emision_mayor_emision_hoy) || "Sin datos"}
              detail={`${formatNumber(
                kpis?.fuente_emision_mayor_emision_hoy_kg_co2e || 0,
                2
              )} kg CO2e`}
              tone="warning"
              pulseKey={streamTick}
            />
          </div>

          <div className="premium-card-interactive mt-5 overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--bg-card)]">
            <div className="flex flex-col gap-2 border-b border-[var(--border)] bg-white/80 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-[var(--text-main)]">
                  Últimas lecturas
                </p>
                <p className="mt-0.5 text-xs font-medium text-[var(--text-muted)]">
                  Las nuevas filas ingresan arriba para simular captura automática de sensores.
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                <RefreshCw size={14} className={newLecturaIds.size ? "animate-spin text-[var(--primary-dark)]" : ""} />
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
                    visibleLecturas.map((lectura) => {
                      const isNew = newLecturaIds.has(lectura.id);

                      return (
                        <tr
                          key={lectura.id}
                          className={`text-[var(--text-muted)] transition-colors duration-300 hover:bg-[var(--success-bg)]/60 ${
                            isNew ? "bg-emerald-50/80" : "bg-white"
                          }`}
                          style={isNew ? { animation: "iotRowIn 1.4s ease-out both" } : undefined}
                        >
                          <td className="whitespace-nowrap px-4 py-3 font-semibold text-[var(--text-main)]">
                            <span className="inline-flex items-center gap-2">
                              {isNew && <span className="h-2 w-2 rounded-full bg-emerald-500" />}
                              {lectura.sensor}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-4 py-3">
                            {lectura.etapa_obra}
                          </td>
                          <td className="whitespace-nowrap px-4 py-3">
                            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-bold text-slate-600">
                              {formatTipo(lectura.tipo)}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-4 py-3 text-right font-semibold text-slate-700">
                            {formatNumber(lectura.valor, 2)} {lectura.unidad}
                          </td>
                          <td className="whitespace-nowrap px-4 py-3 text-right font-bold text-[#075985]">
                            {formatNumber(lectura.co2e_estimado, 2)}
                          </td>
                          <td className="whitespace-nowrap px-4 py-3 text-[var(--text-muted)]">
                            {formatDateTime(lectura.fecha_registro)}
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={6} className="px-4 py-6 text-center text-[var(--text-muted)]">
                        Aún no hay lecturas simuladas registradas.
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

function AnimatedCounter({ decimals = 0, suffix = "", value }) {
  const [displayValue, setDisplayValue] = useState(Number(value || 0));
  const previousValueRef = useRef(Number(value || 0));

  useEffect(() => {
    const target = Number(value || 0);
    const start = previousValueRef.current;
    const duration = 850;
    const startedAt = performance.now();
    let animationFrameId;

    const animate = (timestamp) => {
      const progress = Math.min((timestamp - startedAt) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const nextValue = start + (target - start) * eased;

      setDisplayValue(nextValue);

      if (progress < 1) {
        animationFrameId = window.requestAnimationFrame(animate);
      } else {
        previousValueRef.current = target;
        setDisplayValue(target);
      }
    };

    animationFrameId = window.requestAnimationFrame(animate);

    return () => window.cancelAnimationFrame(animationFrameId);
  }, [value]);

  return (
    <span>
      {formatNumber(displayValue, decimals)}{suffix}
    </span>
  );
}

function RealtimeKpiCard({ decimals = 0, icon, pulseKey, suffix = "", title, tone = "neutral", value }) {
  const toneClasses = getRealtimeToneClasses(tone);

  return (
    <div
      key={`${title}-${pulseKey}`}
      className={`rounded-[18px] border p-6 shadow-[0_12px_30px_rgba(15,23,42,0.06)] ring-1 ring-white/70 ${toneClasses.card}`}
      style={pulseKey ? { animation: "iotKpiPulse 800ms ease-out" } : undefined}
    >
      <div className="mb-4 flex flex-col items-center text-center">
        <div className={`flex h-11 w-11 items-center justify-center rounded-2xl border shadow-[0_8px_24px_rgba(15,23,42,0.04)] ${toneClasses.icon}`}>
          {icon}
        </div>
        <p className={`mt-3 text-sm font-bold ${toneClasses.title}`}>{title}</p>
      </div>
      <h3 className={`mt-1 text-center text-2xl font-black tracking-tight ${toneClasses.value}`}>
        <AnimatedCounter decimals={decimals} suffix={suffix} value={value} />
      </h3>
    </div>
  );
}

function RealtimeInfoCard({ detail, icon, pulseKey, title, tone = "neutral", value }) {
  const toneClasses = getRealtimeToneClasses(tone);

  return (
    <div
      key={`${title}-${pulseKey}`}
      className={`rounded-[18px] border p-6 shadow-[0_12px_30px_rgba(15,23,42,0.06)] ring-1 ring-white/70 ${toneClasses.card}`}
      style={pulseKey ? { animation: "iotKpiPulse 800ms ease-out" } : undefined}
    >
      <div className="mb-4 flex flex-col items-center text-center">
        <div className={`flex h-11 w-11 items-center justify-center rounded-2xl border shadow-[0_8px_24px_rgba(15,23,42,0.04)] ${toneClasses.icon}`}>
          {icon}
        </div>
        <p className={`mt-3 text-sm font-bold ${toneClasses.title}`}>{title}</p>
      </div>
      <h3 className={`mt-1 break-words text-center text-xl font-black leading-tight tracking-tight ${toneClasses.value}`}>
        {value}
      </h3>
      {detail && (
        <p className={`mt-2 text-center text-sm font-semibold ${toneClasses.detail}`}>
          {detail}
        </p>
      )}
    </div>
  );
}

function getRealtimeToneClasses(tone) {
  const tones = {
    neutral: {
      card: "border-[#E2E8F0] bg-[linear-gradient(180deg,#FFFFFF,#F8FAFC)]",
      icon: "border-[#E2E8F0] bg-[#F8FAFC] text-[#334155]",
      title: "text-[#64748B]",
      value: "text-[#334155]",
      detail: "text-[#64748B]",
    },
    success: {
      card: "border-[#A7F3D0] bg-[linear-gradient(180deg,#ECFDF3,#F7FEFA)]",
      icon: "border-[#A7F3D0] bg-white text-[#047857]",
      title: "text-[#64748B]",
      value: "text-[#047857]",
      detail: "text-[#047857]",
    },
    info: {
      card: "border-[#BFDBFE] bg-[linear-gradient(180deg,#EFF6FF,#F8FBFF)]",
      icon: "border-[#BFDBFE] bg-white text-[#1D4ED8]",
      title: "text-[#64748B]",
      value: "text-[#1D4ED8]",
      detail: "text-[#1D4ED8]",
    },
    warning: {
      card: "border-[#FED7AA] bg-[linear-gradient(180deg,#FFF7ED,#FFFBF5)]",
      icon: "border-[#FDBA74] bg-white text-[#B45309]",
      title: "text-[#64748B]",
      value: "text-[#B45309]",
      detail: "text-[#B45309]",
    },
  };

  return tones[tone] || tones.neutral;
}

export default RealtimeIotMonitoring;
