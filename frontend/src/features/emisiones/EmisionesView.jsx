import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Factory,
  Flame,
  Gauge,
  Layers3,
  Sparkles,
  Search,
  Target,
  TrendingDown,
  X,
} from "lucide-react";
import { AnimatePresence } from "framer-motion";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import DecisionCenter from "@/features/dashboard/components/DecisionCenter";
import FactorCategoryBadge from "@/features/factores/components/FactorCategoryBadge";
import { useEmpresaActiva } from "@/features/empresas/context/EmpresaActivaContext";
import { optimizeScenario } from "@/features/dashboard/utils/optimizer";
import AnimatedModalShell from "@/shared/components/AnimatedModalShell";
import ChartCard from "@/shared/components/ChartCard";
import EmptyState from "@/shared/components/EmptyState";
import Pagination from "@/shared/components/Pagination";
import {
  getAiAdvisor,
  getEmpresaEmisiones,
  optimizeScenarioApi,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";

const rowsPerPage = 8;
const DIESEL_REDUCTION_SCENARIO = 25;

const tooltipContentStyle = {
  backgroundColor: "#0F172A",
  border: "1px solid #1E293B",
  borderRadius: "12px",
  color: "#F8FAFC",
};

const horizontalActiveBarStyle = {
  fill: "#CBD5E1",
  fillOpacity: 0.55,
  radius: [0, 10, 10, 0],
};

function truncateChartLabel(value) {
  const text = String(value || "");
  return text.length > 28 ? `${text.slice(0, 28)}...` : text;
}

function getBarSizeForRowCount(rowCount) {
  if (rowCount <= 1) {
    return 34;
  }

  if (rowCount <= 2) {
    return 30;
  }

  if (rowCount <= 4) {
    return 24;
  }

  return 18;
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function uniqueOptions(rows, field) {
  return Array.from(new Set(rows.map((row) => row[field]).filter(Boolean))).sort(
    (left, right) => String(left).localeCompare(String(right), "es")
  );
}

function dependencyLevel(value) {
  const pct = Number(value || 0);

  if (pct >= 60) {
    return { label: "Alta", tone: "text-red-200", panel: "border-red-400/20 bg-red-400/10" };
  }

  if (pct >= 30) {
    return {
      label: "Media",
      tone: "text-amber-200",
      panel: "border-amber-400/20 bg-amber-400/10",
    };
  }

  return {
    label: "Baja",
    tone: "text-emerald-200",
    panel: "border-emerald-400/20 bg-emerald-400/10",
  };
}

function buildDecisionModel(data) {
  const kpis = data?.kpis || {};
  const total = Number(kpis.emisiones_totales || 0);
  const dieselPct = Number(kpis.porcentaje_diesel || 0);
  const topActivityPct = Number(kpis.porcentaje_top_actividad || 0);
  const dieselEmissions = total * (dieselPct / 100);
  const estimatedReduction = dieselEmissions * (DIESEL_REDUCTION_SCENARIO / 100);
  const carKmEquivalent = estimatedReduction * 4;
  const homeMonthsEquivalent = estimatedReduction / 120;
  const dieselLevel = dependencyLevel(dieselPct);
  const criticalActivity = kpis.actividad_critica || "Sin datos";
  const criticalUnit = kpis.unidad_critica || "Sin datos";
  const criticalCategory = kpis.categoria_critica || "Sin datos";

  if (!total) {
    return {
      heroTitle: "Aun no hay emisiones para decidir",
      heroSubtitle: "Registra actividades para identificar focos de impacto y acciones de reduccion.",
      recommendation: "Carga actividades con factores de emision para activar el analisis operativo.",
      dieselLevel,
      estimatedReduction,
      carKmEquivalent,
      homeMonthsEquivalent,
      risks: ["Aun no existen emisiones registradas para esta empresa."],
    };
  }

  const heroTitle =
    dieselPct >= 50
      ? "El diésel móvil concentra el principal riesgo operativo y ambiental"
      : `${criticalActivity} concentra el principal riesgo operativo y ambiental`;
  const heroSubtitle =
    estimatedReduction > 0
      ? `Puedes reducir cerca de ${formatNumber(
          estimatedReduction,
          0
        )} kg CO2e con una intervención focalizada en ${criticalUnit}. La recomendación es partir con un piloto medible antes de escalar cambios mayores.`
      : "Prioriza la actividad principal para convertir el análisis en acción operativa.";
  const recommendation =
    dieselPct >= 30
      ? `Iniciar un piloto de reducción de diésel del 20% al 30% en ${criticalUnit}`
      : `Iniciar un piloto de reducción sobre ${criticalActivity} en ${criticalUnit}`;
  const risks = [];

  if (dieselPct > 50) {
    risks.push(
      `Riesgo operativo: Alta dependencia en diesel (${formatNumber(
        dieselPct,
        1
      )}%), puede generar mayor exposicion a costos, riesgo regulatorio y baja eficiencia energetica.`
    );
  }

  if (topActivityPct > 40) {
    risks.push(
      `Riesgo de concentración: ${criticalActivity} explica el ${formatNumber(
        topActivityPct,
        1
      )}% de la huella.`
    );
  }

  if (criticalUnit !== "Sin datos") {
    risks.push(
      `Riesgo operativo localizado: ${criticalUnit} concentra el mayor impacto y debería priorizarse.`
    );
  }

  if (criticalCategory !== "Sin datos") {
    risks.push(
      `Riesgo por categoría: ${criticalCategory} domina el perfil de emisiones de la empresa.`
    );
  }

  return {
    heroTitle,
    heroSubtitle,
    recommendation,
    dieselLevel,
    estimatedReduction,
    carKmEquivalent,
    homeMonthsEquivalent,
    risks: risks.slice(0, 3),
  };
}

function EmisionesView() {
  const { activeEmpresa, activeEmpresaId, loadingEmpresas } = useEmpresaActiva();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [unitFilter, setUnitFilter] = useState("");
  const [loteFilter, setLoteFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState("");
  const [aiSource, setAiSource] = useState("");
  const [loadingAi, setLoadingAi] = useState(false);
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [optimizedScenario, setOptimizedScenario] = useState(null);
  const [, setSimulatedScenario] = useState(null);

  useEffect(() => {
    if (!activeEmpresaId) {
      setData(null);
      return undefined;
    }

    let cancelled = false;
    setLoading(true);
    setError("");

    getEmpresaEmisiones(activeEmpresaId)
      .then((response) => {
        if (!cancelled) {
          setData(response);
          setCurrentPage(1);
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            requestError.response?.data?.error ||
              "No se pudieron cargar las emisiones de la empresa."
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [activeEmpresaId]);

const rows = Array.isArray(data?.rows)
  ? data.rows
  : Array.isArray(data?.results)
    ? data.results
  : Array.isArray(data?.datos)
    ? data.datos
    : Array.isArray(data)
      ? data
      : [];

const kpis = data?.kpis ?? {
  emisiones_totales: data?.total_emisiones ?? 0,
  actividad_critica: data?.actividad_critica ?? "Sin datos",
  unidad_critica: data?.unidad_critica ?? "Sin datos",
  categoria_critica: data?.categoria_critica ?? "Sin datos",
  porcentaje_diesel: data?.porcentaje_diesel ?? 0,
  porcentaje_top_actividad: data?.porcentaje_top_actividad ?? 0,
  promedio_emision_por_lote: data?.promedio_emision_por_lote ?? 0,
  actividades_sin_factor: data?.actividades_sin_factor ?? 0,
};
  const emissionsByUnit = useMemo(() => {
    const totals = rows.reduce((accumulator, row) => {
      const unidad = row.unidad_nombre || "Sin unidad";
      accumulator[unidad] = (accumulator[unidad] || 0) + Number(row.emisiones || 0);
      return accumulator;
    }, {});

    return Object.entries(totals)
      .map(([unidad, emisiones]) => ({ unidad, emisiones }))
      .sort((left, right) => Number(right.emisiones || 0) - Number(left.emisiones || 0));
  }, [rows]);
  const emissionsByActivity = useMemo(() => {
    const totals = rows.reduce((accumulator, row) => {
      const actividad = row.actividad || "Sin actividad";
      accumulator[actividad] =
        (accumulator[actividad] || 0) + Number(row.emisiones || 0);
      return accumulator;
    }, {});

    return Object.entries(totals)
      .map(([actividad, emisiones]) => ({ actividad, emisiones }))
      .sort((left, right) => Number(right.emisiones || 0) - Number(left.emisiones || 0));
  }, [rows]);
  const unitBarSize = getBarSizeForRowCount(emissionsByUnit.length);
  const activityBarSize = getBarSizeForRowCount(emissionsByActivity.length);
  const decision = useMemo(() => buildDecisionModel(data), [data]);
  const decisionData = useMemo(
    () => ({
      total_emisiones: kpis.emisiones_totales || 0,
      datos: rows.map((row) => ({
        empresa: row.empresa || data?.empresa?.nombre || activeEmpresa?.nombre || "",
        actividad: row.actividad,
        actividad_key: row.actividad_key,
        categoria: row.categoria,
        cantidad: row.cantidad,
        unidad: row.unidad,
        factor_emision: row.factor_emision,
        emisiones: row.emisiones,
        unidad_operativa: row.unidad_nombre,
        id_lote: row.id_lote,
      })),
    }),
    [activeEmpresa?.nombre, data?.empresa?.nombre, kpis.emisiones_totales, rows]
  );
  const categoryOptions = useMemo(() => uniqueOptions(rows, "categoria"), [rows]);
  const unitOptions = useMemo(() => uniqueOptions(rows, "unidad_nombre"), [rows]);
  const loteOptions = useMemo(() => uniqueOptions(rows, "id_lote"), [rows]);
  const filteredRows = useMemo(() => {
    const query = normalizeText(search);

    return rows
      .filter((row) => {
        if (categoryFilter && row.categoria !== categoryFilter) {
          return false;
        }
        if (unitFilter && row.unidad_nombre !== unitFilter) {
          return false;
        }
        if (loteFilter && row.id_lote !== loteFilter) {
          return false;
        }
        if (!query) {
          return true;
        }

        return normalizeText(
          [
            row.actividad,
            row.unidad_nombre,
            row.unidad_id,
            row.id_lote,
            row.categoria,
          ].join(" ")
        ).includes(query);
      })
      .sort((left, right) => Number(right.emisiones || 0) - Number(left.emisiones || 0));
  }, [categoryFilter, loteFilter, rows, search, unitFilter]);
  const totalPages = Math.max(1, Math.ceil(filteredRows.length / rowsPerPage));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const visibleRows = filteredRows.slice(
    (safeCurrentPage - 1) * rowsPerPage,
    safeCurrentPage * rowsPerPage
  );
  const maxEmission = filteredRows[0]?.emisiones || 0;
  const formatTooltipValue = (value) => [
    `${formatNumber(value)} kg CO2e`,
    "Emisiones",
  ];

  useEffect(() => {
    setCurrentPage(1);
  }, [categoryFilter, loteFilter, search, unitFilter]);

  const handleOptimize = async () => {
    try {
      const result = await optimizeScenarioApi(decisionData.datos || []);
      setOptimizedScenario(result);
    } catch (requestError) {
      console.error(requestError);
      setOptimizedScenario(optimizeScenario(decisionData.datos || []));
    }
  };

  const handleAiAnalysis = async () => {
    setAiModalOpen(true);

    try {
      setLoadingAi(true);
      const response = await getAiAdvisor({
        total_emisiones: kpis.emisiones_totales || 0,
        unidad_critica: kpis.unidad_critica || "Sin datos",
        actividad_critica: kpis.actividad_critica || "Sin datos",
        simulacion: null,
        optimizacion: optimizedScenario,
      });

      setAiAnalysis(response.analisis);
      setAiSource(response.fuente);
    } catch (requestError) {
      console.error(requestError);
      setAiAnalysis(
        requestError.response?.data?.error || "No se pudo generar el analisis IA."
      );
      setAiSource("");
    } finally {
      setLoadingAi(false);
    }
  };

  const openDecisionCenter = (shouldOptimize = false) => {
    setDecisionModalOpen(true);
    if (shouldOptimize) {
      handleOptimize();
    }
  };

  if (loadingEmpresas) {
    return <EmptyState title="Cargando empresas" description="Preparando empresa activa." />;
  }

  if (!activeEmpresaId) {
    return (
      <EmptyState
        title="Selecciona o crea una empresa para revisar sus emisiones."
        description="La vista Emisiones trabaja siempre sobre la empresa activa."
      />
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <section className="rounded-3xl border border-cyan-400/20 bg-slate-900 p-5 shadow-xl sm:p-7">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <p className="flex items-center gap-2 text-sm font-semibold text-cyan-300">
              <Flame size={18} />
              Centro operativo de emisiones
            </p>
            <h1 className="mt-3 text-3xl font-bold sm:text-5xl">
              {decision.heroTitle}
            </h1>
            <p className="mt-4 text-base leading-7 text-slate-300">
              {decision.heroSubtitle}
            </p>
            <p className="mt-3 text-sm font-semibold text-emerald-300">
              Empresa activa: {activeEmpresa?.nombre || data?.empresa?.nombre || activeEmpresaId}
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row lg:flex-col">
            <button
              type="button"
              onClick={handleAiAnalysis}
              disabled={loadingAi}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-5 py-3 text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:border-slate-700 disabled:bg-slate-800 disabled:text-slate-500"
            >
              <Sparkles size={18} />
              {loadingAi ? "Analizando..." : "Generar analisis IA"}
            </button>
            <button
              type="button"
              onClick={() => openDecisionCenter(false)}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200 transition hover:bg-emerald-400/20"
            >
              <TrendingDown size={18} />
              Simular escenario
            </button>
            <button
              type="button"
              onClick={() => openDecisionCenter(true)}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-5 py-3 text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/20"
            >
              <Target size={18} />
              Ver plan operativo
            </button>
          </div>
        </div>
      </section>

      {error && (
        <p className="rounded-2xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
          {error}
        </p>
      )}

      <section className="rounded-3xl border border-emerald-400/20 bg-emerald-400/10 p-4 sm:p-6">
        <p className="flex items-center gap-2 text-sm font-semibold text-emerald-200">
          <Target size={18} />
          Recomendacion clave
        </p>
        <h2 className="mt-2 text-2xl font-bold text-emerald-100">
          {decision.recommendation}
        </h2>
        <p className="mt-2 text-sm leading-6 text-emerald-200">
          Mide el consumo antes y después del piloto, revisa desviaciones semanalmente y escala la intervención solo si la reducción se mantiene sin afectar la operación.
        </p>
      </section>

      <section className="space-y-4">
        <SectionTitle title="Estado actual de la operación" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <DecisionKpi
            icon={<Activity />}
            label="Emisiones totales"
            value={`${formatNumber(kpis.emisiones_totales || 0, 1)} kg CO2e`}
          />
          <DecisionKpi
            detail={`${formatNumber(kpis.porcentaje_top_actividad || 0, 1)}% del total`}
            icon={<BarChart3 />}
            label="Principal foco de emisiones"
            value={kpis.actividad_critica || "Sin datos"}
          />
          <DecisionKpi
            icon={<Layers3 />}
            label="Categoría principal"
            value={kpis.categoria_critica || "Sin datos"}
          />
          <DecisionKpi
            icon={<Factory />}
            label="Unidad con mayor impacto"
            value={kpis.unidad_critica || "Sin datos"}
          />
          <DecisionKpi
            detail={`${formatNumber(kpis.porcentaje_diesel || 0, 1)}% del total`}
            icon={<Flame />}
            label="Dependencia de diésel"
            tone={decision.dieselLevel.panel}
            value={decision.dieselLevel.label}
            valueClassName={decision.dieselLevel.tone}
          />
          <DecisionKpi
            icon={<Gauge />}
            label="Emisión promedio por lote"
            value={`${formatNumber(kpis.promedio_emision_por_lote || 0, 1)} kg CO2e`}
          />
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-2">
        <ChartCard title="Emisiones por unidad operativa">
          <div className="h-64 sm:h-72 lg:h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={emissionsByUnit}
                layout="vertical"
                margin={{ top: 10, right: 10, left: 24, bottom: 10 }}
              >
                <XAxis
                  type="number"
                  stroke="#94a3b8"
                  tickFormatter={formatNumber}
                />
                <YAxis
                  dataKey="unidad"
                  interval={0}
                  stroke="#94a3b8"
                  tick={{ fill: "#CBD5E1", fontSize: 11 }}
                  tickFormatter={truncateChartLabel}
                  type="category"
                  width={150}
                />
                <Tooltip
                  contentStyle={tooltipContentStyle}
                  cursor={false}
                  formatter={formatTooltipValue}
                  labelStyle={{ color: "#F8FAFC" }}
                  itemStyle={{ color: "#00D4AA" }}
                />
                <Bar
                  activeBar={horizontalActiveBarStyle}
                  dataKey="emisiones"
                  fill="#00D4AA"
                  barSize={unitBarSize}
                  radius={[0, 10, 10, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard title="Emisiones por actividad">
          <div className="h-64 sm:h-72 lg:h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={emissionsByActivity}
                layout="vertical"
                margin={{ top: 10, right: 10, left: 24, bottom: 10 }}
              >
                <XAxis
                  type="number"
                  stroke="#94a3b8"
                  tickFormatter={formatNumber}
                />
                <YAxis
                  dataKey="actividad"
                  interval={0}
                  stroke="#94a3b8"
                  tick={{ fill: "#CBD5E1", fontSize: 11 }}
                  tickFormatter={truncateChartLabel}
                  type="category"
                  width={150}
                />
                <Tooltip
                  contentStyle={tooltipContentStyle}
                  cursor={false}
                  formatter={formatTooltipValue}
                  labelStyle={{ color: "#F8FAFC" }}
                  itemStyle={{ color: "#00D4AA" }}
                />
                <Bar
                  activeBar={horizontalActiveBarStyle}
                  dataKey="emisiones"
                  fill="#38BDF8"
                  barSize={activityBarSize}
                  radius={[0, 10, 10, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-3xl border border-amber-400/20 bg-amber-400/10 p-4 sm:p-6">
          <SectionTitle eyebrow="Riesgos" title="Lo que puede afectar la operacion" />
          <div className="mt-4 space-y-3">
            {decision.risks.map((risk) => (
              <p
                key={risk}
                className="rounded-2xl border border-amber-400/20 bg-slate-950/70 p-4 text-sm leading-6 text-amber-100"
              >
                {risk}
              </p>
            ))}
          </div>
          {Number(kpis.actividades_sin_factor || 0) > 0 && (
            <p className="mt-4 flex items-center gap-2 rounded-2xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-100">
              <AlertTriangle size={18} />
              Existen actividades sin factor de emision asociado.
            </p>
          )}
        </div>

        <div className="rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-4 sm:p-6">
          <SectionTitle
            eyebrow="Impacto real"
            title={`Si reduces diesel en ${DIESEL_REDUCTION_SCENARIO}%`}
          />
          <div className="mt-4 space-y-3">
            <ImpactRow
              label="Tendrias una reduccion estimada:"
              value={`${formatNumber(decision.estimatedReduction, 0)} kg CO2e`}
            />
            <ImpactRow
              label="Que seria equivalente a:"
              value={`${formatNumber(decision.carKmEquivalent, 0)} km en auto`}
            />
            <ImpactRow
              label="Impacto comparable a:"
              value={`${formatNumber(decision.homeMonthsEquivalent, 1)} hogares al mes aprox.`}
            />
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
        <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Detalle de emisiones</h2>
            <p className="mt-1 text-sm text-slate-400">
              {formatNumber(filteredRows.length, 0)} registros encontrados.
            </p>
          </div>
          {loading && <p className="text-sm font-semibold text-emerald-300">Cargando...</p>}
        </div>

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <label className="relative block">
            <Search
              size={18}
              className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-500"
            />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar actividad, unidad, lote o categoría"
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 py-3 pl-11 pr-4 text-sm text-slate-100 outline-none transition focus:border-emerald-400/60"
            />
          </label>
          <FilterSelect
            label="Todas las categorías"
            onChange={setCategoryFilter}
            options={categoryOptions}
            value={categoryFilter}
          />
          <FilterSelect
            label="Todas las unidades"
            onChange={setUnitFilter}
            options={unitOptions}
            value={unitFilter}
          />
          <FilterSelect
            label="Todos los lotes"
            onChange={setLoteFilter}
            options={loteOptions}
            value={loteFilter}
          />
        </div>

        {rows.length === 0 && !loading ? (
          <div className="mt-5">
            <EmptyState
              title="Esta empresa aun no tiene actividades con emisiones calculadas."
              description="Importa o registra actividades para comenzar el analisis."
            />
          </div>
        ) : (
          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[1180px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-left text-xs text-slate-400">
                  <th className="px-4 py-3">Fecha</th>
                  <th className="px-4 py-3">Unidad operativa</th>
                  <th className="px-4 py-3">Lote</th>
                  <th className="px-4 py-3">Actividad</th>
                  <th className="px-4 py-3">Categoria</th>
                  <th className="px-4 py-3 text-right">Cantidad</th>
                  <th className="px-4 py-3">Unidad</th>
                  <th className="px-4 py-3 text-right">Factor</th>
                  <th className="px-4 py-3 text-right">Emisiones kg CO2e</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row) => {
                  const highlighted =
                    maxEmission > 0 && Number(row.emisiones || 0) >= maxEmission * 0.8;

                  return (
                    <tr
                      key={row.id}
                      className={`border-b border-slate-800/80 transition ${
                        highlighted ? "bg-cyan-400/5" : "hover:bg-slate-800/40"
                      }`}
                    >
                      <td className="px-4 py-4 text-slate-300">{row.fecha || "-"}</td>
                      <td className="px-4 py-4 font-semibold text-slate-100">
                        {row.unidad_nombre || "Sin unidad"}
                      </td>
                      <td className="px-4 py-4 text-slate-300">{row.id_lote || "-"}</td>
                      <td className="px-4 py-4 font-semibold text-slate-100">
                        {row.actividad}
                      </td>
                      <td className="px-4 py-4">
                        <FactorCategoryBadge category={row.categoria} />
                      </td>
                      <td className="px-4 py-4 text-right text-slate-300">
                        {formatNumber(row.cantidad || 0, 3)}
                      </td>
                      <td className="px-4 py-4 text-slate-300">{row.unidad || "-"}</td>
                      <td className="px-4 py-4 text-right text-slate-300">
                        {formatNumber(row.factor_emision || 0, 4)}
                      </td>
                      <td className="px-4 py-4 text-right font-bold text-cyan-200">
                        {formatNumber(row.emisiones || 0, 1)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <Pagination
          currentPage={safeCurrentPage}
          itemLabel="emisiones"
          onPageChange={setCurrentPage}
          pageSize={rowsPerPage}
          totalItems={filteredRows.length}
        />
      </section>

      <AnimatePresence>
        {aiModalOpen && (
          <AnimatedModalShell
            ariaLabel="Analisis estrategico IA"
            contentClassName="my-4 flex max-h-[calc(100vh-2rem)] w-full max-w-5xl flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-950 shadow-2xl sm:my-6"
            onBackdropClick={() => setAiModalOpen(false)}
          >
            <div className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-800 bg-slate-950 p-4 sm:p-6">
              <div>
                <p className="text-sm font-semibold text-cyan-300">
                  Carbono Zero AI
                </p>
                <h2 className="mt-1 text-2xl font-bold text-slate-100">
                  Analisis estrategico generado por IA
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setAiModalOpen(false)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-slate-700 bg-slate-900 text-slate-300 transition hover:bg-slate-800"
                aria-label="Cerrar analisis IA"
              >
                <X size={18} />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
              {loadingAi ? (
                <p className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-5 text-sm font-semibold text-cyan-200">
                  Generando analisis...
                </p>
              ) : (
                <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-5 text-slate-200">
                  {aiSource === "carbono_zero_engine" && (
                    <p className="mb-4 text-xs font-semibold text-emerald-300">
                      Generado por motor analitico Carbono Zero
                    </p>
                  )}
                  {aiSource === "openai" && (
                    <p className="mb-4 text-xs font-semibold text-cyan-300">
                      Generado con OpenAI
                    </p>
                  )}
                  <p className="whitespace-pre-line leading-7">
                    {aiAnalysis || "Aun no hay analisis disponible."}
                  </p>
                </div>
              )}
            </div>
          </AnimatedModalShell>
        )}

        {decisionModalOpen && (
          <AnimatedModalShell
            ariaLabel="Centro de decisiones"
            contentClassName="my-4 flex max-h-[calc(100vh-2rem)] w-full max-w-6xl flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-950 shadow-2xl sm:my-6"
            onBackdropClick={() => setDecisionModalOpen(false)}
          >
            <div className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-800 bg-slate-950 p-4 sm:p-6">
              <div>
                <p className="text-sm font-semibold text-emerald-300">
                  Centro de decisiones
                </p>
                <h2 className="mt-1 text-2xl font-bold text-slate-100">
                  Simula y optimiza la operacion activa
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setDecisionModalOpen(false)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-slate-700 bg-slate-900 text-slate-300 transition hover:bg-slate-800"
                aria-label="Cerrar centro de decisiones"
              >
                <X size={18} />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
              <DecisionCenter
                data={decisionData}
                optimizedScenario={optimizedScenario}
                onOptimize={handleOptimize}
                onSimulationChange={setSimulatedScenario}
              />
            </div>
          </AnimatedModalShell>
        )}
      </AnimatePresence>
    </div>
  );
}

function SectionTitle({ eyebrow, title }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {eyebrow}
      </p>
      <h2 className="mt-1 text-xl font-bold text-slate-100">{title}</h2>
    </div>
  );
}

function DecisionKpi({ detail, icon, label, tone = "border-slate-800 bg-slate-900", value, valueClassName = "text-slate-100" }) {
  return (
    <div className={`rounded-3xl border p-5 shadow-xl ${tone}`}>
      <div className="mb-4 text-cyan-300">{icon}</div>
      <p className="text-sm text-slate-400">{label}</p>
      <h3 className={`mt-1 text-2xl font-bold ${valueClassName}`}>{value}</h3>
      {detail && <p className="mt-2 text-sm font-semibold text-slate-300">{detail}</p>}
    </div>
  );
}

function ImpactRow({ label, value }) {
  return (
    <div className="rounded-2xl border border-cyan-400/20 bg-slate-950/70 p-4">
      <p className="text-xs uppercase tracking-wide text-cyan-300">{label}</p>
      <p className="mt-1 text-2xl font-bold text-cyan-100">{value}</p>
    </div>
  );
}

function FilterSelect({ label, onChange, options, value }) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/60"
    >
      <option value="">{label}</option>
      {options.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  );
}

export default EmisionesView;
