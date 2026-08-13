import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  Eye,
  Factory,
  Gauge,
  Loader2,
  MapPinned,
  Search,
} from "lucide-react";

import EmptyState from "@/shared/components/EmptyState";
import Pagination from "@/shared/components/Pagination";
import Tabs from "@/shared/components/Tabs";
import { getOrganizacionEtapas } from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

const rowsPerPage = 8;
const detailRowsPerPage = 8;

function EtapasObraView() {
  const [etapas, setEtapas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedEtapaId, setSelectedEtapaId] = useState("");
  const [selectedEtapaLoading, setSelectedEtapaLoading] = useState(false);
  const [activeDetailTab, setActiveDetailTab] = useState("resumen");
  const { activeOrganizacion, activeOrganizacionId, loadingOrganizaciones } = useOrganizacionActiva();

  useEffect(() => {
    if (!activeOrganizacionId) {
      setEtapas([]);
      setLoading(false);
      return;
    }

    let isCancelled = false;
    setLoading(true);
    setError("");

    async function loadEtapas() {
      try {
        const data = await getOrganizacionEtapas(activeOrganizacionId);

        if (!isCancelled) {
          const nextEtapas = Array.isArray(data) ? data : [];
          setEtapas(nextEtapas);
          setSelectedEtapaId((currentId) => {
            if (currentId && nextEtapas.some((unidad) => String(unidad.id) === String(currentId))) {
              return currentId;
            }
            return "";
          });
        }
      } catch (requestError) {
        if (!isCancelled) {
          setError(
            requestError.response?.data?.error ||
              "No se pudieron cargar las etapas."
          );
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    loadEtapas();

    return () => {
      isCancelled = true;
    };
  }, [activeOrganizacionId]);

  async function loadEtapaDetail(unidad) {
    if (!activeOrganizacionId || !unidad?.etapa_id) {
      return;
    }

    setSelectedEtapaId(String(unidad.id));
    setActiveDetailTab("resumen");
    setSelectedEtapaLoading(true);

    try {
      const data = await getOrganizacionEtapas(activeOrganizacionId, {
        detail: 1,
        etapa_id: unidad.etapa_id,
      });
      const [detail] = Array.isArray(data) ? data : [];

      if (detail) {
        setEtapas((currentEtapas) =>
          currentEtapas.map((currentEtapa) =>
            String(currentEtapa.id) === String(detail.id)
              ? { ...currentEtapa, ...detail }
              : currentEtapa
          )
        );
      }
    } catch (requestError) {
      setError(
        requestError.response?.data?.error ||
          "No se pudo cargar el detalle de la etapa."
      );
    } finally {
      setSelectedEtapaLoading(false);
    }
  }

  const filteredEtapas = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return etapas;
    }

    return etapas.filter((unidad) =>
      [
        unidad.etapa_id,
        unidad.nombre,
        unidad.tipo,
        unidad.organizacion_nombre,
        unidad.region,
        unidad.comuna,
        unidad.direccion,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [search, etapas]);

  const metrics = useMemo(() => buildOperationalMetrics(etapas), [etapas]);
  const selectedEtapa = useMemo(
    () => etapas.find((unidad) => String(unidad.id) === String(selectedEtapaId)),
    [selectedEtapaId, etapas]
  );
  const totalPages = Math.max(1, Math.ceil(filteredEtapas.length / rowsPerPage));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * rowsPerPage;
  const visibleEtapas = filteredEtapas.slice(startIndex, startIndex + rowsPerPage);

  useEffect(() => {
    setCurrentPage(1);
  }, [search]);

  if (loadingOrganizaciones) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-slate-300">
        Cargando organizaciones...
      </div>
    );
  }

  if (!activeOrganizacion) {
    return (
      <EmptyState
        title="Selecciona o crea una organizacion para comenzar"
        description="Las etapas se muestran dentro de la organizacion activa."
      />
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="premium-card-interactive rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-3 shadow-[var(--shadow-soft)]">
            <Factory className="text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold sm:text-4xl">Etapas</h1>
            <p className="max-w-3xl text-slate-400">
              Fases operativas de la obra vinculadas a registros, evidencias y emisiones de la organizacion activa.
            </p>
          </div>
        </div>
        <div className="premium-card-interactive rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-[var(--primary-dark)] shadow-[var(--shadow-soft)]">
          {formatNumber(metrics.totalUnits, 0)} etapas activas
        </div>
      </header>

      {error && (
        <p className="rounded-2xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
          {error}
        </p>
      )}

      <section className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <UnitKpi
          icon={<Factory />}
          label="Etapas activas"
          tone="success"
          value={metrics.totalUnits}
        />
        <UnitKpi
          detail={`${formatNumber(metrics.topEmissionUnit?.emisiones_totales_kg_co2e || 0, 1)} kg CO2e`}
          icon={<BarChart3 />}
          label="Etapa con mayor emisión"
          tone="danger"
          value={metrics.topEmissionUnit?.nombre || "Sin datos"}
        />
        <UnitKpi
          detail={`${formatNumber(metrics.topActivitiesUnit?.registros_count || 0, 0)} registros · ${formatNumber(metrics.topActivitiesUnit?.obras_count || 0, 0)} obras`}
          icon={<Activity />}
          label="Mayor carga operativa"
          tone="info"
          value={metrics.topActivitiesUnit?.nombre || "Sin datos"}
        />
        <UnitKpi
          detail="Alcance operativo registrado"
          icon={<MapPinned />}
          label="Cobertura territorial"
          tone="warning"
          value={`${formatNumber(metrics.territorialCoverage, 0)} ${metrics.coverageLabel}`}
        />
      </section>

      <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--info-bg)] p-4 shadow-[var(--shadow-card)] sm:p-6">
        <p className="text-sm font-bold text-[#075985]">Resumen operativo</p>
        <h2 className="mt-2 text-2xl font-bold text-[var(--text-main)]">
          Mapa operativo de {activeOrganizacion.nombre}
        </h2>
        <p className="mt-3 max-w-6xl text-base font-medium leading-8 text-[#334155]">
          {buildOperationalSummary(activeOrganizacion, metrics)}
        </p>
      </section>

      <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
        <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-[var(--text-main)]">Etapas registradas</h2>
            <p className="mt-1 text-sm font-medium text-[var(--text-muted)]">
              {formatNumber(filteredEtapas.length, 0)} etapas encontradas.
            </p>
          </div>
          {loading && <Loader2 className="animate-spin text-emerald-300" size={20} />}
        </div>

        <label className="relative mb-5 block">
          <Search
            size={18}
            className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-muted)]"
          />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar por etapa, organizacion, tipo, región o comuna"
            className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] py-3 pl-11 pr-4 text-sm text-[var(--text-main)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-[var(--primary)]/60"
          />
        </label>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1180px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-xs text-[var(--text-muted)]">
                <th className="px-4 py-3">Organizacion</th>
                <th className="px-4 py-3">Etapa</th>
                <th className="px-4 py-3">Tipo</th>
                <th className="px-4 py-3">Región</th>
                <th className="px-4 py-3">Comuna</th>
                <th className="px-4 py-3 text-right">Obras</th>
                <th className="px-4 py-3 text-right">Registros</th>
                <th className="px-4 py-3 text-right">Emisiones</th>
                <th className="px-4 py-3 text-center">Ver detalle</th>
              </tr>
            </thead>
            <tbody>
              {visibleEtapas.map((unidad) => (
                <tr
                  key={unidad.id}
                  onClick={() => loadEtapaDetail(unidad)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      loadEtapaDetail(unidad);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  className={`cursor-pointer border-b border-[#CBD5D0] transition focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/40 ${
                    String(selectedEtapaId) === String(unidad.id)
                      ? "bg-[var(--success-bg)]"
                      : "hover:bg-[var(--bg-surface)]"
                  }`}
                >
                  <td className="px-4 py-4 font-semibold text-[var(--text-main)]">
                    {unidad.organizacion_nombre || activeOrganizacion.nombre || "-"}
                  </td>
                  <td className="px-4 py-4">
                    <p className="font-semibold text-[var(--text-main)]">{unidad.nombre || "-"}</p>
                  </td>
                  <td className="px-4 py-4">
                    <UnitTypeBadge type={unidad.tipo} />
                  </td>
                  <td className="px-4 py-4 text-[var(--text-muted)]">{unidad.region || "-"}</td>
                  <td className="px-4 py-4 text-[var(--text-muted)]">{unidad.comuna || "-"}</td>
                  <td className="px-4 py-4 text-right font-semibold text-[var(--text-main)]">
                    {formatNumber(unidad.obras_count || 0, 0)}
                  </td>
                  <td className="px-4 py-4 text-right font-semibold text-[var(--text-main)]">
                    {formatNumber(unidad.registros_count || 0, 0)}
                  </td>
                  <td className="px-4 py-4 text-right font-bold text-[#075985]">
                    {formatNumber(unidad.emisiones_totales_kg_co2e || 0, 1)} kg CO2e
                  </td>
                  <td className="px-4 py-4 text-center">
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        loadEtapaDetail(unidad);
                      }}
                      className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] text-[#075985] transition hover:border-[var(--primary)]/40 hover:bg-[#D9F0E6]"
                      aria-label={`Ver detalle de ${unidad.nombre}`}
                    >
                      <Eye size={18} />
                    </button>
                  </td>
                </tr>
              ))}
              {!loading && visibleEtapas.length === 0 && (
                <tr>
                  <td className="px-1 py-8 text-center text-slate-400" colSpan={9}>
                    No hay etapas para mostrar.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination
          currentPage={safeCurrentPage}
          itemLabel="etapas"
          onPageChange={setCurrentPage}
          pageSize={rowsPerPage}
          totalItems={filteredEtapas.length}
        />
      </section>

      <EtapaDetailPanel
        activeTab={activeDetailTab}
        loading={selectedEtapaLoading}
        onTabChange={setActiveDetailTab}
        unidad={selectedEtapa}
      />
    </div>
  );
}

function buildOperationalMetrics(etapas) {
  const activeUnits = etapas.filter((unidad) => unidad.activa !== false);
  const unitsWithOperation = activeUnits.filter(
    (unidad) =>
      Number(unidad.obras_count || 0) > 0 ||
      Number(unidad.registros_count || 0) > 0 ||
      Number(unidad.emisiones_totales_kg_co2e || 0) > 0
  );
  const comunas = new Set(activeUnits.map((unidad) => unidad.comuna).filter(Boolean));
  const regiones = new Set(activeUnits.map((unidad) => unidad.region).filter(Boolean));
  const totalEmissions = activeUnits.reduce(
    (total, unidad) => total + Number(unidad.emisiones_totales_kg_co2e || 0),
    0
  );
  const totalLots = activeUnits.reduce(
    (total, unidad) => total + Number(unidad.obras_count || 0),
    0
  );
  const totalActivities = activeUnits.reduce(
    (total, unidad) => total + Number(unidad.registros_count || 0),
    0
  );
  const topActivitiesUnit = maxBy(activeUnits, (unidad) =>
    Number(unidad.registros_count || 0) + Number(unidad.obras_count || 0)
  );
  const topEmissionUnits = [...activeUnits]
    .filter((unidad) => Number(unidad.emisiones_totales_kg_co2e || 0) > 0)
    .sort(
      (left, right) =>
        Number(right.emisiones_totales_kg_co2e || 0) -
        Number(left.emisiones_totales_kg_co2e || 0)
    );
  const topEmissionUnit = topEmissionUnits[0] || null;
  const dominantComuna = dominantValue(
    unitsWithOperation.map((unidad) => unidad.comuna).filter(Boolean)
  );
  const territorialCoverage = comunas.size || regiones.size;

  return {
    totalUnits: activeUnits.length,
    unitsWithOperationCount: unitsWithOperation.length,
    topActivitiesUnit,
    topEmissionUnit,
    topEmissionUnits,
    totalLots,
    totalActivities,
    totalEmissions,
    territorialCoverage,
    coverageLabel: comunas.size ? "comunas" : "regiones",
    dominantComuna,
  };
}

function buildOperationalSummary(activeOrganizacion, metrics) {
  if (!metrics.totalUnits) {
    return "La organizacion aún no tiene etapas registradas. Crea o importa etapas para habilitar trazabilidad, registros de emisión y lectura operativa.";
  }

  const topEmitter = metrics.topEmissionUnit;
  const topEmitterEmissions = Number(topEmitter?.emisiones_totales_kg_co2e || 0);
  const topEmitterShare = metrics.totalEmissions
    ? (topEmitterEmissions / metrics.totalEmissions) * 100
    : 0;
  const topOperational = metrics.topActivitiesUnit;
  const territory = metrics.dominantComuna
    ? `La operación se concentra principalmente en ${metrics.dominantComuna}`
    : "La cobertura territorial aún no está completamente definida";

  if (!metrics.totalEmissions) {
    return `${activeOrganizacion.nombre} cuenta con ${formatNumber(metrics.totalUnits, 0)} etapas activas y ${formatNumber(metrics.totalActivities, 0)} registros operativos. El foco inmediato debe ser completar registros de emisión y evidencias para identificar qué etapa concentra el mayor impacto ambiental.`;
  }

  return `${activeOrganizacion.nombre} cuenta con ${formatNumber(metrics.totalUnits, 0)} etapas activas, ${formatNumber(metrics.totalActivities, 0)} registros y ${formatNumber(metrics.totalLots, 0)} obras asociadas. ${topEmitter?.nombre || "La etapa principal"} concentra ${formatNumber(topEmitterEmissions, 1)} kg CO2e, equivalente al ${formatNumber(topEmitterShare, 0)}% de la huella registrada, por lo que debe priorizarse en la gestión ambiental. ${topOperational?.nombre || "La etapa con mayor actividad"} presenta la mayor carga operativa con ${formatNumber(topOperational?.registros_count || 0, 0)} registros. ${territory}.`;
}

function maxBy(items, selector) {
  if (!items.length) {
    return null;
  }

  return items.reduce((best, item) => (selector(item) > selector(best) ? item : best), items[0]);
}

function dominantValue(values) {
  const counts = values.reduce((acc, value) => {
    acc[value] = (acc[value] || 0) + 1;
    return acc;
  }, {});
  return Object.entries(counts).sort((left, right) => right[1] - left[1])[0]?.[0] || "";
}

function UnitKpi({ detail, icon, label, tone = "neutral", value }) {
  const toneClasses = getUnitKpiTone(tone);

  return (
    <div className={`premium-card-interactive relative flex min-h-[190px] overflow-hidden rounded-[24px] border p-5 shadow-[0_18px_45px_rgba(15,23,42,0.10)] ring-1 ring-white/80 transition duration-300 hover:-translate-y-1 hover:shadow-[0_24px_60px_rgba(15,23,42,0.16)] ${toneClasses.card}`}>
      <div className={`absolute inset-x-7 top-0 h-1.5 rounded-b-full ${toneClasses.accent}`} />
      <div className={`pointer-events-none absolute -right-12 -top-12 h-36 w-36 rounded-full blur-3xl ${toneClasses.glow}`} />
      <div className="relative z-10 flex w-full flex-col items-center text-center">
        <div className={`flex h-12 w-12 items-center justify-center rounded-2xl border shadow-[0_12px_28px_rgba(15,23,42,0.08)] ${toneClasses.icon}`}>
          {icon}
        </div>
        <p className={`mt-4 text-[11px] font-black uppercase tracking-[0.14em] ${toneClasses.title}`}>
          {label}
        </p>
        <div className="flex flex-1 items-center justify-center py-3">
          <h3 className={`mx-auto max-w-[260px] break-words text-center text-[clamp(1.5rem,2.4vw,2.15rem)] font-black leading-tight tracking-tight ${toneClasses.value}`}>
            {typeof value === "number" ? formatNumber(value, 0) : value || "Sin datos"}
          </h3>
        </div>
        {detail && <p className={`text-center text-sm font-bold ${toneClasses.detail}`}>{detail}</p>}
      </div>
    </div>
  );
}

function getUnitKpiTone(tone) {
  const tones = {
    success: {
      card: "border-[#86EFAC] bg-[linear-gradient(135deg,#ECFDF3_0%,#FFFFFF_48%,#DCFCE7_100%)]",
      icon: "border-[#86EFAC] bg-white text-[#047857]",
      title: "text-[#64748B]",
      value: "text-[#047857]",
      detail: "text-[#047857]",
      accent: "bg-[#059669]",
      glow: "bg-emerald-200/70",
    },
    danger: {
      card: "border-[#FDA4AF] bg-[linear-gradient(135deg,#FFF1F2_0%,#FFFFFF_46%,#FFE4E6_100%)]",
      icon: "border-[#FDA4AF] bg-white text-[#BE123C]",
      title: "text-[#64748B]",
      value: "text-[#BE123C]",
      detail: "text-[#9F1239]",
      accent: "bg-[#E11D48]",
      glow: "bg-rose-200/70",
    },
    info: {
      card: "border-[#93C5FD] bg-[linear-gradient(135deg,#EFF6FF_0%,#FFFFFF_48%,#DBEAFE_100%)]",
      icon: "border-[#93C5FD] bg-white text-[#1D4ED8]",
      title: "text-[#64748B]",
      value: "text-[#1D4ED8]",
      detail: "text-[#1D4ED8]",
      accent: "bg-[#2563EB]",
      glow: "bg-blue-200/70",
    },
    warning: {
      card: "border-[#FDBA74] bg-[linear-gradient(135deg,#FFF7ED_0%,#FFFFFF_48%,#FFEDD5_100%)]",
      icon: "border-[#FDBA74] bg-white text-[#C2410C]",
      title: "text-[#64748B]",
      value: "text-[#C2410C]",
      detail: "text-[#B45309]",
      accent: "bg-[#EA580C]",
      glow: "bg-orange-200/70",
    },
    neutral: {
      card: "border-[#CBD5E1] bg-[linear-gradient(135deg,#FFFFFF_0%,#F8FAFC_48%,#E2E8F0_100%)]",
      icon: "border-[#CBD5E1] bg-white text-[#334155]",
      title: "text-[#64748B]",
      value: "text-[#334155]",
      detail: "text-[#64748B]",
      accent: "bg-[#475569]",
      glow: "bg-slate-200/70",
    },
  };

  return tones[tone] || tones.neutral;
}

function UnitTypeBadge({ type }) {
  const value = type || "Otro";
  const displayValue = value === "Proveedor" ? "Proveedor / planta" : value;
  const tone = {
    General: "border-[#94A3B8] bg-[#F1F5F9] text-[#334155]",
    Planta: "border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]",
    Proveedor: "border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]",
    control: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]",
    Bodega: "border-[#C4B5FD] bg-[#F1EDFF] text-[#5B21B6]",
    Despacho: "border-[#BFDBFE] bg-[#EFF6FF] text-[#075985]",
    Mantencion: "border-[#FDBA74] bg-[#FFF7ED] text-[#9A3412]",
    Administracion: "border-[#C7D2FE] bg-[#EEF2FF] text-[#3730A3]",
  }[value] || "border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]";

  return (
    <span className={`rounded-full border px-3 py-1 text-xs font-bold ${tone}`}>
      {displayValue}
    </span>
  );
}

function EtapaDetailPanel({ activeTab, loading, onTabChange, unidad }) {
  const [detailPages, setDetailPages] = useState({});

  useEffect(() => {
    setDetailPages({});
  }, [unidad?.id, activeTab]);

  if (!unidad) {
    return (
      <EmptyState
        title="Selecciona una etapa"
        description="Selecciona una etapa para revisar su resumen, obras, registros y emisiones asociadas."
      />
    );
  }

  const obras = unidad.obras_resumen || [];
  const registros_emision = unidad.registros_emision_resumen || [];

  return (
    <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-bold text-[var(--primary-dark)]">Detalle etapa</p>
          <h2 className="mt-1 text-2xl font-bold text-[var(--text-main)]">{unidad.nombre}</h2>
          <p className="mt-2 text-sm font-medium text-[var(--text-muted)]">
            {unidad.organizacion_nombre || "Sin organizacion"} · {unidad.region || "Sin región"} ·{" "}
            {unidad.comuna || "Sin comuna"}
          </p>
          {unidad.direccion && (
            <p className="mt-1 text-sm text-[var(--text-muted)]">{unidad.direccion}</p>
          )}
        </div>
        <UnitTypeBadge type={unidad.tipo} />
      </div>

      {loading && (
        <div className="mb-5 flex items-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm font-semibold text-cyan-100">
          <Loader2 className="animate-spin" size={18} />
          Cargando detalle operativo...
        </div>
      )}

      <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <UnitMiniMetric label="Obras asociadas" value={unidad.obras_count || 0} />
        <UnitMiniMetric label="Registros" value={unidad.registros_count || 0} />
        <UnitMiniMetric
          label="Emisiones acumuladas"
          tone="cyan"
          value={`${formatNumber(unidad.emisiones_totales_kg_co2e || 0, 1)} kg CO2e`}
        />
        <UnitMiniMetric
          label="Trazabilidad"
          tone="emerald"
          value={`${formatNumber(unidad.fichas_ambientales_count || 0, 0)} fichas`}
          detail={`${formatNumber(unidad.evidencias_count || 0, 0)} evidencias`}
        />
      </div>

      <Tabs
        activeTab={activeTab}
        onChange={onTabChange}
        tabs={[
          { label: "Resumen", value: "resumen" },
          { label: "Registros", value: "registros_emision" },
          { label: "Obras", value: "obras" },
          { label: "Emisiones", value: "emisiones" },
          { label: "Evidencias / Historial", value: "evidencias" },
        ]}
      />

      <div className="mt-5">
        {activeTab === "resumen" && <EtapaResumen unidad={unidad} />}
        {activeTab === "registros_emision" && (
          <PaginatedSimpleTable
            columns={["Fecha", "Registro", "Categoría", "Obra", "Cantidad", "Emisiones"]}
            onPageChange={(page) =>
              setDetailPages((currentPages) => ({ ...currentPages, registros_emision: page }))
            }
            page={detailPages.registros_emision || 1}
            rows={registros_emision.map((fuente_emision) => [
              fuente_emision.fecha || "-",
              fuente_emision.fuente_emision,
              fuente_emision.categoria || "-",
              fuente_emision.obra || "-",
              `${formatNumber(fuente_emision.cantidad || 0, 3)} ${fuente_emision.unidad || ""}`,
              `${formatNumber(fuente_emision.emisiones_kg_co2e || 0, 1)} kg CO2e`,
            ])}
          />
        )}
        {activeTab === "obras" && (
          <PaginatedSimpleTable
            columns={["Obra", "Fecha", "Material / tipo de obra", "Estado", "Emisiones", "Balance"]}
            onPageChange={(page) =>
              setDetailPages((currentPages) => ({ ...currentPages, obras: page }))
            }
            page={detailPages.obras || 1}
            rows={obras.map((obra) => [
              obra.codigo_obra,
              obra.fecha || "-",
              obra.tipo_proyecto || "-",
              obra.estado || "-",
              `${formatNumber(obra.emisiones_kg_co2e || 0, 1)} kg CO2e`,
              `${formatNumber(obra.balance_neto_kg_co2e || 0, 1)} kg CO2e`,
            ])}
          />
        )}
        {activeTab === "emisiones" && (
          <PaginatedSimpleTable
            columns={["Registro", "Categoría", "Factor", "Emisiones"]}
            onPageChange={(page) =>
              setDetailPages((currentPages) => ({ ...currentPages, emisiones: page }))
            }
            page={detailPages.emisiones || 1}
            rows={registros_emision.map((fuente_emision) => [
              fuente_emision.fuente_emision,
              fuente_emision.categoria || "-",
              formatNumber(fuente_emision.factor_emision || 0, 4),
              `${formatNumber(fuente_emision.emisiones_kg_co2e || 0, 1)} kg CO2e`,
            ])}
          />
        )}
        {activeTab === "evidencias" && (
          <PaginatedSimpleTable
            columns={["Obra", "Estado ficha", "Evidencias"]}
            onPageChange={(page) =>
              setDetailPages((currentPages) => ({ ...currentPages, evidencias: page }))
            }
            page={detailPages.evidencias || 1}
            rows={obras.map((obra) => [
              obra.codigo_obra,
              obra.estado_ficha_ambiental || "Sin ficha",
              formatNumber(obra.evidencias_count || 0, 0),
            ])}
          />
        )}
      </div>
    </section>
  );
}

function UnitMiniMetric({ detail, label, tone = "slate", value }) {
  const toneClass = {
    cyan: "text-[#075985]",
    emerald: "text-[var(--primary-dark)]",
    slate: "text-[var(--text-main)]",
  }[tone];

  return (
    <div className="premium-card-interactive rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
      <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
        {label}
      </p>
      <p className={`mt-2 text-2xl font-bold ${toneClass}`}>{value}</p>
      {detail && <p className="mt-1 text-sm font-medium text-[var(--text-muted)]">{detail}</p>}
    </div>
  );
}

function EtapaResumen({ unidad }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <UnitMiniMetric label="ID etapa" value={unidad.etapa_id || "-"} />
      <UnitMiniMetric label="Tipo" value={unidad.tipo || "Sin tipo"} />
      <UnitMiniMetric label="Región" value={unidad.region || "Sin región"} />
      <UnitMiniMetric label="Comuna" value={unidad.comuna || "Sin comuna"} />
      <div className="premium-card-interactive rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 sm:col-span-2 xl:col-span-4">
        <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
          Descripción
        </p>
        <p className="mt-2 text-sm font-medium leading-6 text-[var(--text-main)]">
          {unidad.descripcion ||
            "No hay descripción operativa registrada para esta etapa."}
        </p>
      </div>
    </div>
  );
}

function PaginatedSimpleTable({ columns, onPageChange, page, rows }) {
  if (!rows.length) {
    return (
      <EmptyState
        title="Sin datos"
        description="Esta etapa aún no tiene registros para esta sección."
      />
    );
  }

  const totalPages = Math.max(1, Math.ceil(rows.length / detailRowsPerPage));
  const safePage = Math.min(page, totalPages);
  const visibleRows = rows.slice(
    (safePage - 1) * detailRowsPerPage,
    safePage * detailRowsPerPage
  );

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-xs text-[var(--text-muted)]">
              {columns.map((column) => (
                <th key={column} className="px-4 py-3">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, rowIndex) => (
              <tr
                key={`${row[0]}-${safePage}-${rowIndex}`}
                className="border-b border-[#CBD5D0]"
              >
                {row.map((cell, cellIndex) => (
                  <td
                    key={`${row[0]}-${safePage}-${rowIndex}-${cellIndex}`}
                    className={`px-4 py-3 ${
                      cellIndex === 0 ? "font-semibold text-[var(--text-main)]" : "text-[var(--text-muted)]"
                    }`}
                  >
                    {cell || "-"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination
        currentPage={safePage}
        itemLabel="registros"
        onPageChange={onPageChange}
        pageSize={detailRowsPerPage}
        totalItems={rows.length}
      />
    </>
  );
}

export default EtapasObraView;
