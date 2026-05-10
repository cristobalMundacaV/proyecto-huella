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
              "No se pudieron cargar las unidades operativas."
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
          "No se pudo cargar el detalle de la unidad operativa."
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
        Cargando empresas...
      </div>
    );
  }

  if (!activeEmpresa) {
    return (
      <EmptyState
        title="Selecciona o crea una empresa para comenzar"
        description="Las unidades operativas se muestran dentro del workspace activo."
      />
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-3">
            <Factory className="text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold sm:text-4xl">
              Unidades Operativas
            </h1>
            <p className="max-w-3xl text-slate-400">
              Centros de trabajo, plantas productivas y nodos logísticos vinculados
              a la empresa activa.
            </p>
          </div>
        </div>
        <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200">
          {formatNumber(unidades.length, 0)} unidades
        </div>
      </header>

      {error && (
        <p className="rounded-2xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
          {error}
        </p>
      )}

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <UnitKpi icon={<Factory />} label="Total de unidades" value={metrics.totalUnits} />
        <UnitKpi
          detail={`${formatNumber(metrics.topLotsUnit?.lotes_count || 0, 0)} lotes`}
          icon={<Boxes />}
          label="Unidad con mas lotes"
          value={metrics.topLotsUnit?.nombre || "Sin datos"}
        />
        <UnitKpi
          detail={`${formatNumber(metrics.topActivitiesUnit?.actividades_count || 0, 0)} actividades`}
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

      <section className="rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-4 sm:p-6">
        <p className="text-sm font-semibold text-cyan-200">Resumen operativo</p>
        <h2 className="mt-2 text-2xl font-bold text-slate-100">
          Mapa operativo de {activeEmpresa.nombre}
        </h2>
        <p className="mt-3 max-w-5xl whitespace-pre-line text-sm leading-7 text-cyan-50">
          {buildOperationalSummary(activeEmpresa, metrics)}
        </p>
      </section>

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
        <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Unidades registradas</h2>
            <p className="mt-1 text-sm text-slate-400">
              {formatNumber(filteredUnidades.length, 0)} unidades encontradas.
            </p>
          </div>
          {loading && <Loader2 className="animate-spin text-emerald-300" size={20} />}
        </div>

        <label className="relative mb-5 block">
          <Search
            size={18}
            className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-500"
          />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar por unidad, empresa, tipo, región o comuna"
            className="w-full rounded-2xl border border-slate-700 bg-slate-950 py-3 pl-11 pr-4 text-sm text-slate-100 outline-none transition focus:border-emerald-400/60"
          />
        </label>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1180px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs text-slate-400">
                <th className="px-4 py-3">Empresa</th>
                <th className="px-4 py-3">Unidad</th>
                <th className="px-4 py-3">Tipo</th>
                <th className="px-4 py-3">Region</th>
                <th className="px-4 py-3">Comuna</th>
                <th className="px-4 py-3 text-right">Lotes</th>
                <th className="px-4 py-3 text-right">Actividades</th>
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
                  className={`cursor-pointer border-b border-slate-800/80 transition focus:outline-none focus:ring-2 focus:ring-cyan-400/40 ${
                    String(selectedUnidadId) === String(unidad.id)
                      ? "bg-emerald-400/5"
                      : "hover:bg-slate-800/40"
                  }`}
                >
                  <td className="px-4 py-4 font-semibold text-slate-100">
                    {unidad.empresa_nombre || activeEmpresa.nombre || "-"}
                  </td>
                  <td className="px-4 py-4">
                    <p className="font-semibold text-slate-100">{unidad.nombre || "-"}</p>
                  </td>
                  <td className="px-4 py-4">
                    <UnitTypeBadge type={unidad.tipo} />
                  </td>
                  <td className="px-4 py-4 text-slate-300">{unidad.region || "-"}</td>
                  <td className="px-4 py-4 text-slate-300">{unidad.comuna || "-"}</td>
                  <td className="px-4 py-4 text-right font-semibold text-slate-200">
                    {formatNumber(unidad.lotes_count || 0, 0)}
                  </td>
                  <td className="px-4 py-4 text-right font-semibold text-slate-200">
                    {formatNumber(unidad.actividades_count || 0, 0)}
                  </td>
                  <td className="px-4 py-4 text-right font-bold text-cyan-200">
                    {formatNumber(unidad.emisiones_totales_kg_co2e || 0, 1)}
                  </td>
                  <td className="px-4 py-4 text-center">
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        loadUnidadDetail(unidad);
                      }}
                      className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 text-cyan-200 transition hover:bg-cyan-400/20"
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
                    No hay unidades operativas para mostrar.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination
          currentPage={safeCurrentPage}
          itemLabel="unidades"
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
    return "La empresa aun no tiene unidades operativas registradas. Crea o importa unidades para habilitar lectura operacional, trazabilidad y analisis de emisiones.";
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
    ? `${formatUnitNamesWithEmissions(nextEmitters)} tambien presentan impactos relevantes. En conjunto, estas unidades explican la mayor parte de la huella de la empresa.`
    : "No hay suficientes unidades adicionales con emisiones para construir un segundo nivel de priorizacion.";
  const operationalLoadText = metrics.topActivitiesUnit
    ? `Por otro lado, ${metrics.topActivitiesUnit.nombre} concentra una alta carga operativa, con ${formatNumber(
        metrics.topActivitiesUnit.lotes_count || 0,
        0
      )} lotes y ${formatNumber(
        metrics.topActivitiesUnit.actividades_count || 0,
        0
      )} actividades.`
    : "";
  const priorityList = [topEmitter, ...nextEmitters]
    .filter(Boolean)
    .map((unidad) => unidad.nombre);

  return `${activeEmpresa.nombre} opera con ${formatNumber(
    metrics.totalUnits,
    0
  )} unidades activas, pero la actividad real se concentra en ${formatNumber(
    metrics.unitsWithOperationCount,
    0
  )} unidades con lotes, actividades y emisiones registradas. Estas unidades acumulan ${formatNumber(
    metrics.totalLots,
    0
  )} lotes, ${formatNumber(metrics.totalActivities, 0)} actividades y una huella total de ${formatNumber(
    metrics.totalEmissions,
    1
  )} kg CO2e.

La operacion se concentra principalmente ${territory}${withoutOperationText}. Esto sugiere una operacion territorialmente ${centralization}, con algunas unidades aun sin trazabilidad operativa activa.

La unidad mas critica es ${topEmitter?.nombre || "Sin datos"}, que concentra ${formatNumber(
    topEmitterEmissions,
    1
  )} kg CO2e, equivalente al ${formatNumber(
    topEmitterShare,
    0
  )}% de las emisiones totales. Esto la convierte en el principal foco de riesgo ambiental y operativo.

${nextEmittersText}

${operationalLoadText}

Lectura clave

La empresa no tiene un problema distribuido de forma pareja: tiene una operacion donde pocas unidades concentran la mayor parte del impacto. La prioridad deberia estar en ${formatUnitNames(
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
    cyan: "text-cyan-200",
    emerald: "text-emerald-200",
    slate: "text-slate-100",
  }[tone];

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
      <div className="mb-3 flex items-center gap-3">
        <div className="text-cyan-300">{icon}</div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {label}
        </p>
      </div>
      <p className={`mt-2 line-clamp-2 text-2xl font-bold ${toneClass}`}>
        {typeof value === "number" ? formatNumber(value, 0) : value || "Sin datos"}
      </p>
      {detail && <p className="mt-2 text-sm font-semibold text-slate-400">{detail}</p>}
    </div>
  );
}

function UnitTypeBadge({ type }) {
  const value = type || "Otro";
  const tone = {
    General: "border-slate-500/30 bg-slate-400/10 text-slate-200",
    Planta: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200",
    Aserradero: "border-cyan-400/20 bg-cyan-400/10 text-cyan-200",
    Secado: "border-amber-400/20 bg-amber-400/10 text-amber-200",
    Bodega: "border-violet-400/20 bg-violet-400/10 text-violet-200",
    Despacho: "border-blue-400/20 bg-blue-400/10 text-blue-200",
    Mantencion: "border-orange-400/20 bg-orange-400/10 text-orange-200",
    Administracion: "border-indigo-400/20 bg-indigo-400/10 text-indigo-200",
  }[value] || "border-cyan-400/20 bg-cyan-400/10 text-cyan-200";

  return (
    <span className={`rounded-full border px-3 py-1 text-xs font-bold ${tone}`}>
      {value}
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
        title="Selecciona una unidad operativa"
        description="Selecciona una unidad operativa para revisar su resumen, lotes, actividades y emisiones asociadas."
      />
    );
  }

  const lotes = unidad.lotes_resumen || [];
  const actividades = unidad.actividades_resumen || [];

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-emerald-300">Detalle unidad</p>
          <h2 className="mt-1 text-2xl font-bold text-slate-100">{unidad.nombre}</h2>
          <p className="mt-2 text-sm text-slate-400">
            {unidad.empresa_nombre || "Sin empresa"} · {unidad.region || "Sin region"} ·{" "}
            {unidad.comuna || "Sin comuna"}
          </p>
          {unidad.direccion && (
            <p className="mt-1 text-sm text-slate-500">{unidad.direccion}</p>
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
        <UnitMiniMetric label="Lotes asociados" value={unidad.lotes_count || 0} />
        <UnitMiniMetric label="Actividades" value={unidad.actividades_count || 0} />
        <UnitMiniMetric
          label="Emisiones acumuladas"
          tone="cyan"
          value={`${formatNumber(unidad.emisiones_totales_kg_co2e || 0, 1)} kg CO2e`}
        />
        <UnitMiniMetric
          label="Trazabilidad"
          tone="emerald"
          value={`${formatNumber(unidad.pasaportes_count || 0, 0)} pasaportes`}
          detail={`${formatNumber(unidad.evidencias_count || 0, 0)} evidencias`}
        />
      </div>

      <Tabs
        activeTab={activeTab}
        onChange={onTabChange}
        tabs={[
          { label: "Resumen", value: "resumen" },
          { label: "Actividades", value: "actividades" },
          { label: "Lotes", value: "lotes" },
          { label: "Emisiones", value: "emisiones" },
          { label: "Evidencias / Historial", value: "evidencias" },
        ]}
      />

      <div className="mt-5">
        {activeTab === "resumen" && <UnidadResumen unidad={unidad} />}
        {activeTab === "actividades" && (
          <PaginatedSimpleTable
            columns={["Fecha", "Actividad", "Categoria", "Lote", "Cantidad", "Emisiones"]}
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
            columns={["Lote", "Fecha", "Especie", "Estado", "Emisiones", "Balance"]}
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
            columns={["Actividad", "Categoria", "Factor", "Emisiones"]}
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
            columns={["Lote", "Estado pasaporte", "Evidencias"]}
            onPageChange={(page) =>
              setDetailPages((currentPages) => ({ ...currentPages, evidencias: page }))
            }
            page={detailPages.evidencias || 1}
            rows={lotes.map((lote) => [
              lote.id_lote,
              lote.estado_pasaporte || "Sin pasaporte",
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
    cyan: "text-cyan-200",
    emerald: "text-emerald-200",
    slate: "text-slate-100",
  }[tone];

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className={`mt-2 text-2xl font-bold ${toneClass}`}>{value}</p>
      {detail && <p className="mt-1 text-sm text-slate-400">{detail}</p>}
    </div>
  );
}

function UnidadResumen({ unidad }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <UnitMiniMetric label="Unidad ID" value={unidad.unidad_id || "-"} />
      <UnitMiniMetric label="Tipo" value={unidad.tipo || "Sin tipo"} />
      <UnitMiniMetric label="Region" value={unidad.region || "Sin region"} />
      <UnitMiniMetric label="Comuna" value={unidad.comuna || "Sin comuna"} />
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 sm:col-span-2 xl:col-span-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Descripcion
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          {unidad.descripcion ||
            "No hay descripcion operativa registrada para esta unidad."}
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
        description="Esta unidad aun no tiene registros para esta seccion."
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
            <tr className="border-b border-slate-800 text-left text-xs text-slate-400">
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
                className="border-b border-slate-800/70"
              >
                {row.map((cell, cellIndex) => (
                  <td
                    key={`${row[0]}-${safePage}-${rowIndex}-${cellIndex}`}
                    className={`px-4 py-3 ${
                      cellIndex === 0 ? "font-semibold text-slate-100" : "text-slate-300"
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
