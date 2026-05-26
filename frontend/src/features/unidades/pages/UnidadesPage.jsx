import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Boxes,
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
import { getEmpresaUnidades } from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import { useEmpresaActiva } from "@/features/empresas/context/EmpresaActivaContext";

const rowsPerPage = 8;
const detailRowsPerPage = 8;

function UnidadesOperativasView() {
  const [unidades, setUnidades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedUnidadId, setSelectedUnidadId] = useState("");
  const [selectedUnidadLoading, setSelectedUnidadLoading] = useState(false);
  const [activeDetailTab, setActiveDetailTab] = useState("resumen");
  const { activeEmpresa, activeEmpresaId, loadingEmpresas } = useEmpresaActiva();

  useEffect(() => {
    if (!activeEmpresaId) {
      setUnidades([]);
      setLoading(false);
      return;
    }

    let isCancelled = false;
    setLoading(true);
    setError("");

    async function loadUnidades() {
      try {
        const data = await getEmpresaUnidades(activeEmpresaId);

        if (!isCancelled) {
          setUnidades(Array.isArray(data) ? data : []);
          setSelectedUnidadId((currentId) => {
            if (currentId && data.some((unidad) => String(unidad.id) === String(currentId))) {
              return currentId;
            }
            return "";
          });
        }
      } catch (requestError) {
        if (!isCancelled) {
          setError(
            requestError.response?.data?.error ||
              "No se pudieron cargar las etapas o frentes."
          );
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    loadUnidades();

    return () => {
      isCancelled = true;
    };
  }, [activeEmpresaId]);

  async function loadUnidadDetail(unidad) {
    if (!activeEmpresaId || !unidad?.unidad_id) {
      return;
    }

    setSelectedUnidadId(String(unidad.id));
    setActiveDetailTab("resumen");
    setSelectedUnidadLoading(true);

    try {
      const data = await getEmpresaUnidades(activeEmpresaId, {
        detail: 1,
        unidad_id: unidad.unidad_id,
      });
      const [detail] = Array.isArray(data) ? data : [];

      if (detail) {
        setUnidades((currentUnidades) =>
          currentUnidades.map((currentUnidad) =>
            String(currentUnidad.id) === String(detail.id)
              ? { ...currentUnidad, ...detail }
              : currentUnidad
          )
        );
      }
    } catch (requestError) {
      setError(
        requestError.response?.data?.error ||
          "No se pudo cargar el detalle de la etapa o frente."
      );
    } finally {
      setSelectedUnidadLoading(false);
    }
  }

  const filteredUnidades = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return unidades;
    }

    return unidades.filter((unidad) =>
      [
        unidad.unidad_id,
        unidad.nombre,
        unidad.tipo,
        unidad.empresa_nombre,
        unidad.region,
        unidad.comuna,
        unidad.direccion,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [search, unidades]);

  const metrics = useMemo(() => buildOperationalMetrics(unidades), [unidades]);
  const selectedUnidad = useMemo(
    () => unidades.find((unidad) => String(unidad.id) === String(selectedUnidadId)),
    [selectedUnidadId, unidades]
  );
  const totalPages = Math.max(1, Math.ceil(filteredUnidades.length / rowsPerPage));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * rowsPerPage;
  const visibleUnidades = filteredUnidades.slice(startIndex, startIndex + rowsPerPage);

  useEffect(() => {
    setCurrentPage(1);
  }, [search]);

  if (loadingEmpresas) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-slate-300">
        Cargando constructoras...
      </div>
    );
  }

  if (!activeEmpresa) {
    return (
      <EmptyState
        title="Selecciona o crea una constructora para comenzar"
        description="Las etapas y frentes se muestran dentro del workspace activo."
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
            <h1 className="text-3xl font-bold sm:text-4xl">
              Etapas / frentes
            </h1>
            <p className="max-w-3xl text-slate-400">
              Centros de trabajo, plantas productivas y nodos logísticos vinculados
              a la constructora activa.
            </p>
          </div>
        </div>
        <div className="premium-card-interactive rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200 shadow-[var(--shadow-soft)]">
          {formatNumber(unidades.length, 0)} etapas
        </div>
      </header>

      {error && (
        <p className="rounded-2xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
          {error}
        </p>
      )}

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <UnitKpi icon={<Factory />} label="Total de etapas" value={metrics.totalUnits} />
        <UnitKpi
          detail={`${formatNumber(metrics.topLotsUnit?.lotes_count || 0, 0)} obras`}
          icon={<Boxes />}
          label="Etapa con más obras"
          value={metrics.topLotsUnit?.nombre || "Sin datos"}
        />
        <UnitKpi
          detail={`${formatNumber(metrics.topActivitiesUnit?.actividades_count || 0, 0)} registros`}
          icon={<Activity />}
          label="Mayor carga operativa"
          value={metrics.topActivitiesUnit?.nombre || "Sin datos"}
        />
        <UnitKpi
          icon={<Gauge />}
          label="Emisiones asociadas"
          tone="cyan"
          value={`${formatNumber(metrics.totalEmissions, 1)} kg CO2e`}
        />
        <UnitKpi
          icon={<MapPinned />}
          label="Cobertura territorial"
          value={`${formatNumber(metrics.territorialCoverage, 0)} ${metrics.coverageLabel}`}
        />
      </section>

      <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--info-bg)] p-4 shadow-[var(--shadow-card)] sm:p-6">
        <p className="text-sm font-bold text-[#075985]">Resumen operativo</p>
        <h2 className="mt-2 text-2xl font-bold text-[var(--text-main)]">
          Mapa operativo de {activeEmpresa.nombre}
        </h2>
        <p className="mt-3 max-w-5xl whitespace-pre-line text-sm font-medium leading-7 text-[#334155]">
          {buildOperationalSummary(activeEmpresa, metrics)}
        </p>
      </section>

      <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
        <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-[var(--text-main)]">Etapas registradas</h2>
            <p className="mt-1 text-sm font-medium text-[var(--text-muted)]">
              {formatNumber(filteredUnidades.length, 0)} etapas encontradas.
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
            placeholder="Buscar por etapa, constructora, tipo, región o comuna"
            className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] py-3 pl-11 pr-4 text-sm text-[var(--text-main)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-[var(--primary)]/60"
          />
        </label>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1180px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-xs text-[var(--text-muted)]">
                <th className="px-4 py-3">Constructora</th>
                <th className="px-4 py-3">Etapa / frente</th>
                <th className="px-4 py-3">Tipo</th>
                <th className="px-4 py-3">Region</th>
                <th className="px-4 py-3">Comuna</th>
                <th className="px-4 py-3 text-right">Obras</th>
                <th className="px-4 py-3 text-right">Registros</th>
                <th className="px-4 py-3 text-right">Emisiones</th>
                <th className="px-4 py-3 text-center">Ver detalle</th>
              </tr>
            </thead>
            <tbody>
              {visibleUnidades.map((unidad) => (
                <tr
                  key={unidad.id}
                  onClick={() => loadUnidadDetail(unidad)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      loadUnidadDetail(unidad);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  className={`cursor-pointer border-b border-[#CBD5D0] transition focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/40 ${
                    String(selectedUnidadId) === String(unidad.id)
                      ? "bg-[var(--success-bg)]"
                      : "hover:bg-[var(--bg-surface)]"
                  }`}
                >
                  <td className="px-4 py-4 font-semibold text-[var(--text-main)]">
                    {unidad.empresa_nombre || activeEmpresa.nombre || "-"}
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
                    {formatNumber(unidad.lotes_count || 0, 0)}
                  </td>
                  <td className="px-4 py-4 text-right font-semibold text-[var(--text-main)]">
                    {formatNumber(unidad.actividades_count || 0, 0)}
                  </td>
                  <td className="px-4 py-4 text-right font-bold text-[#075985]">
                    {formatNumber(unidad.emisiones_totales_kg_co2e || 0, 1)}
                  </td>
                  <td className="px-4 py-4 text-center">
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        loadUnidadDetail(unidad);
                      }}
                      className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] text-[#075985] transition hover:border-[var(--primary)]/40 hover:bg-[#D9F0E6]"
                      aria-label={`Ver detalle de ${unidad.nombre}`}
                    >
                      <Eye size={18} />
                    </button>
                  </td>
                </tr>
              ))}
              {!loading && visibleUnidades.length === 0 && (
                <tr>
                  <td className="px-1 py-8 text-center text-slate-400" colSpan={9}>
                    No hay etapas o frentes para mostrar.
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
          totalItems={filteredUnidades.length}
        />
      </section>

      <UnidadDetailPanel
        activeTab={activeDetailTab}
        loading={selectedUnidadLoading}
        onTabChange={setActiveDetailTab}
        unidad={selectedUnidad}
      />
    </div>
  );
}

function buildOperationalMetrics(unidades) {
  const activeUnits = unidades.filter((unidad) => unidad.activa !== false);
  const unitsWithOperation = activeUnits.filter(
    (unidad) =>
      Number(unidad.lotes_count || 0) > 0 ||
      Number(unidad.actividades_count || 0) > 0 ||
      Number(unidad.emisiones_totales_kg_co2e || 0) > 0
  );
  const unitsWithoutOperation = activeUnits.filter(
    (unidad) =>
      Number(unidad.lotes_count || 0) === 0 &&
      Number(unidad.actividades_count || 0) === 0 &&
      Number(unidad.emisiones_totales_kg_co2e || 0) === 0
  );
  const types = new Set(activeUnits.map((unidad) => unidad.tipo).filter(Boolean));
  const comunas = new Set(activeUnits.map((unidad) => unidad.comuna).filter(Boolean));
  const regiones = new Set(activeUnits.map((unidad) => unidad.region).filter(Boolean));
  const totalEmissions = activeUnits.reduce(
    (total, unidad) => total + Number(unidad.emisiones_totales_kg_co2e || 0),
    0
  );
  const totalLots = activeUnits.reduce(
    (total, unidad) => total + Number(unidad.lotes_count || 0),
    0
  );
  const totalActivities = activeUnits.reduce(
    (total, unidad) => total + Number(unidad.actividades_count || 0),
    0
  );
  const topLotsUnit = maxBy(activeUnits, (unidad) => Number(unidad.lotes_count || 0));
  const topActivitiesUnit = maxBy(activeUnits, (unidad) =>
    Number(unidad.actividades_count || 0)
  );
  const topEmissionUnits = [...activeUnits]
    .filter((unidad) => Number(unidad.emisiones_totales_kg_co2e || 0) > 0)
    .sort(
      (left, right) =>
        Number(right.emisiones_totales_kg_co2e || 0) -
        Number(left.emisiones_totales_kg_co2e || 0)
    );
  const dominantType = dominantValue(activeUnits.map((unidad) => unidad.tipo).filter(Boolean));
  const dominantComuna = dominantValue(
    unitsWithOperation.map((unidad) => unidad.comuna).filter(Boolean)
  );
  const territorialCoverage = comunas.size || regiones.size;

  return {
    totalUnits: activeUnits.length,
    unitsWithOperationCount: unitsWithOperation.length,
    unitsWithoutOperation,
    uniqueTypes: types.size,
    topLotsUnit,
    topActivitiesUnit,
    topEmissionUnits,
    totalLots,
    totalActivities,
    totalEmissions,
    territorialCoverage,
    coverageLabel: comunas.size ? "comunas" : "regiones",
    dominantType,
    dominantComuna,
  };
}

function buildOperationalSummary(activeEmpresa, metrics) {
  if (!metrics.totalUnits) {
    return "La constructora aun no tiene etapas o frentes registrados. Crea o importa etapas para habilitar lectura operacional, trazabilidad y analisis de emisiones.";
  }

  const centralization =
    metrics.territorialCoverage <= 1
      ? "centralizada"
      : metrics.territorialCoverage <= 3
        ? "semi-centralizada"
        : "distribuida";
  const territory = metrics.dominantComuna
    ? `en la comuna de ${metrics.dominantComuna}`
    : "sin cobertura territorial definida";
  const topEmitter = metrics.topEmissionUnits[0];
  const nextEmitters = metrics.topEmissionUnits.slice(1, 3);
  const topEmitterEmissions = Number(topEmitter?.emisiones_totales_kg_co2e || 0);
  const topEmitterShare = metrics.totalEmissions
    ? (topEmitterEmissions / metrics.totalEmissions) * 100
    : 0;
  const withoutOperationText = metrics.unitsWithoutOperation.length
    ? `, mientras que ${formatUnitNames(metrics.unitsWithoutOperation)} ${metrics.unitsWithoutOperation.length === 1 ? "aparece" : "aparecen"} sin actividad ni emisiones registradas`
    : "";
  const nextEmittersText = nextEmitters.length
    ? `${formatUnitNamesWithEmissions(nextEmitters)} tambien presentan impactos relevantes. En conjunto, estas etapas explican la mayor parte de la huella de la constructora.`
    : "No hay suficientes etapas adicionales con emisiones para construir un segundo nivel de priorizacion.";
  const operationalLoadText = metrics.topActivitiesUnit
    ? `Por otro lado, ${metrics.topActivitiesUnit.nombre} concentra una alta carga operativa, con ${formatNumber(
        metrics.topActivitiesUnit.lotes_count || 0,
        0
      )} obras y ${formatNumber(
        metrics.topActivitiesUnit.actividades_count || 0,
        0
      )} registros.`
    : "";
  const priorityList = [topEmitter, ...nextEmitters]
    .filter(Boolean)
    .map((unidad) => unidad.nombre);

  return `${activeEmpresa.nombre} opera con ${formatNumber(
    metrics.totalUnits,
    0
  )} etapas activas, pero la actividad real se concentra en ${formatNumber(
    metrics.unitsWithOperationCount,
    0
  )} etapas con obras, registros y emisiones registradas. Estas etapas acumulan ${formatNumber(
    metrics.totalLots,
    0
  )} obras, ${formatNumber(metrics.totalActivities, 0)} registros y una huella total de ${formatNumber(
    metrics.totalEmissions,
    1
  )} kg CO2e.

La operacion se concentra principalmente ${territory}${withoutOperationText}. Esto sugiere una operacion territorialmente ${centralization}, con algunas etapas aun sin trazabilidad operativa activa.

La etapa más crítica es ${topEmitter?.nombre || "Sin datos"}, que concentra ${formatNumber(
    topEmitterEmissions,
    1
  )} kg CO2e, equivalente al ${formatNumber(
    topEmitterShare,
    0
  )}% de las emisiones totales. Esto la convierte en el principal foco de riesgo ambiental y operativo.

${nextEmittersText}

${operationalLoadText}

Lectura clave

La constructora no tiene un problema distribuido de forma pareja: tiene una operación donde pocas etapas concentran la mayor parte del impacto. La prioridad debería estar en ${formatUnitNames(
    priorityList
  )}.`;
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

function formatUnitNames(unitsOrNames) {
  const names = unitsOrNames
    .map((item) => (typeof item === "string" ? item : item?.nombre))
    .filter(Boolean);

  if (!names.length) {
    return "Sin datos";
  }

  if (names.length === 1) {
    return names[0];
  }

  return `${names.slice(0, -1).join(", ")} y ${names[names.length - 1]}`;
}

function formatUnitNamesWithEmissions(units) {
  const parts = units.map(
    (unidad) =>
      `${unidad.nombre} (${formatNumber(
        unidad.emisiones_totales_kg_co2e || 0,
        1
      )} kg CO2e)`
  );

  return formatUnitNames(parts);
}

function UnitKpi({ detail, icon, label, tone = "slate", value }) {
  const toneClass = {
    cyan: "text-[#075985]",
    emerald: "text-[var(--primary-dark)]",
    slate: "text-[var(--text-main)]",
  }[tone];

  return (
    <div className="premium-card-interactive rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)]">
      <div className="mb-3 flex items-center gap-3">
        <div className="text-[var(--primary-dark)]">{icon}</div>
        <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
          {label}
        </p>
      </div>
      <p className={`mt-2 line-clamp-2 text-2xl font-bold ${toneClass}`}>
        {typeof value === "number" ? formatNumber(value, 0) : value || "Sin datos"}
      </p>
      {detail && <p className="mt-2 text-sm font-semibold text-[var(--text-muted)]">{detail}</p>}
    </div>
  );
}

function UnitTypeBadge({ type }) {
  const value = type || "Otro";
  const displayValue = value === "Aserradero" ? "Proveedor / planta" : value;
  const tone = {
    General: "border-[#94A3B8] bg-[#F1F5F9] text-[#334155]",
    Planta: "border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]",
    Aserradero: "border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]",
    Secado: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]",
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

function UnidadDetailPanel({ activeTab, loading, onTabChange, unidad }) {
  const [detailPages, setDetailPages] = useState({});

  useEffect(() => {
    setDetailPages({});
  }, [unidad?.id, activeTab]);

  if (!unidad) {
    return (
      <EmptyState
        title="Selecciona una etapa / frente"
        description="Selecciona una etapa o frente para revisar su resumen, obras, registros y emisiones asociadas."
      />
    );
  }

  const lotes = unidad.lotes_resumen || [];
  const actividades = unidad.actividades_resumen || [];

  return (
    <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-bold text-[var(--primary-dark)]">Detalle etapa</p>
          <h2 className="mt-1 text-2xl font-bold text-[var(--text-main)]">{unidad.nombre}</h2>
          <p className="mt-2 text-sm font-medium text-[var(--text-muted)]">
            {unidad.empresa_nombre || "Sin constructora"} · {unidad.region || "Sin region"} ·{" "}
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
        <UnitMiniMetric label="Obras asociadas" value={unidad.lotes_count || 0} />
        <UnitMiniMetric label="Registros" value={unidad.actividades_count || 0} />
        <UnitMiniMetric
          label="Emisiones acumuladas"
          tone="cyan"
          value={`${formatNumber(unidad.emisiones_totales_kg_co2e || 0, 1)} kg CO2e`}
        />
        <UnitMiniMetric
          label="Trazabilidad"
          tone="emerald"
          value={`${formatNumber(unidad.pasaportes_count || 0, 0)} fichas`}
          detail={`${formatNumber(unidad.evidencias_count || 0, 0)} evidencias`}
        />
      </div>

      <Tabs
        activeTab={activeTab}
        onChange={onTabChange}
        tabs={[
          { label: "Resumen", value: "resumen" },
          { label: "Registros", value: "actividades" },
          { label: "Obras", value: "lotes" },
          { label: "Emisiones", value: "emisiones" },
          { label: "Evidencias / Historial", value: "evidencias" },
        ]}
      />

      <div className="mt-5">
        {activeTab === "resumen" && <UnidadResumen unidad={unidad} />}
        {activeTab === "actividades" && (
          <PaginatedSimpleTable
            columns={["Fecha", "Registro", "Categoria", "Obra", "Cantidad", "Emisiones"]}
            onPageChange={(page) =>
              setDetailPages((currentPages) => ({ ...currentPages, actividades: page }))
            }
            page={detailPages.actividades || 1}
            rows={actividades.map((actividad) => [
              actividad.fecha || "-",
              actividad.actividad,
              actividad.categoria || "-",
              actividad.lote || "-",
              `${formatNumber(actividad.cantidad || 0, 3)} ${actividad.unidad || ""}`,
              `${formatNumber(actividad.emisiones_kg_co2e || 0, 1)} kg CO2e`,
            ])}
          />
        )}
        {activeTab === "lotes" && (
          <PaginatedSimpleTable
            columns={["Obra", "Fecha", "Material / tipo de obra", "Estado", "Emisiones", "Balance"]}
            onPageChange={(page) =>
              setDetailPages((currentPages) => ({ ...currentPages, lotes: page }))
            }
            page={detailPages.lotes || 1}
            rows={lotes.map((lote) => [
              lote.id_lote,
              lote.fecha || "-",
              lote.especie || "-",
              lote.estado || "-",
              `${formatNumber(lote.emisiones_kg_co2e || 0, 1)} kg CO2e`,
              `${formatNumber(lote.balance_neto_kg_co2e || 0, 1)} kg CO2e`,
            ])}
          />
        )}
        {activeTab === "emisiones" && (
          <PaginatedSimpleTable
            columns={["Registro", "Categoria", "Factor", "Emisiones"]}
            onPageChange={(page) =>
              setDetailPages((currentPages) => ({ ...currentPages, emisiones: page }))
            }
            page={detailPages.emisiones || 1}
            rows={actividades.map((actividad) => [
              actividad.actividad,
              actividad.categoria || "-",
              formatNumber(actividad.factor_emision || 0, 4),
              `${formatNumber(actividad.emisiones_kg_co2e || 0, 1)} kg CO2e`,
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
            rows={lotes.map((lote) => [
              lote.id_lote,
              lote.estado_pasaporte || "Sin ficha",
              formatNumber(lote.evidencias_count || 0, 0),
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

function UnidadResumen({ unidad }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <UnitMiniMetric label="ID etapa" value={unidad.unidad_id || "-"} />
      <UnitMiniMetric label="Tipo" value={unidad.tipo || "Sin tipo"} />
      <UnitMiniMetric label="Region" value={unidad.region || "Sin region"} />
      <UnitMiniMetric label="Comuna" value={unidad.comuna || "Sin comuna"} />
      <div className="premium-card-interactive rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 sm:col-span-2 xl:col-span-4">
        <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
          Descripcion
        </p>
        <p className="mt-2 text-sm font-medium leading-6 text-[var(--text-main)]">
          {unidad.descripcion ||
            "No hay descripcion operativa registrada para esta etapa."}
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
        description="Esta etapa aun no tiene registros para esta seccion."
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

export default UnidadesOperativasView;
