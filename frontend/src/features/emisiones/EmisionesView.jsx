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
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { optimizeScenario } from "@/features/dashboard/utils/optimizer";
import {
  constructionCategories,
  getConstructionCategoryLabel,
} from "@/features/obras/utils/constructionEmissionCategories";
import AnimatedModalShell from "@/shared/components/AnimatedModalShell";
import ChartCard from "@/shared/components/ChartCard";
import EmptyState from "@/shared/components/EmptyState";
import Pagination from "@/shared/components/Pagination";
import {
  getAiAdvisor,
  getConstructoraEmisiones,
  optimizeScenarioApi,
} from "@/shared/services/api";
import {
  getConstructionEvidenceLinkLabel,
  getConstructionEvidenceReviewLabel,
  getConstructionEvidenceTypeLabel,
} from "@/shared/utils/constructionEvidenceLabels";
import { formatNumber } from "@/shared/utils/formatters";

const rowsPerPage = 8;
const DIESEL_REDUCTION_SCENARIO = 25;

const fuelUseLabels = {
  preparacion: "Preparación / movimiento",
  despacho: "Despacho",
  transporte: "Transporte",
  maquinaria: "Maquinaria",
  vehiculos: "Vehiculos",
};

const categoryInsightRules = {
  Materiales:
    "La categorí­a critica actualmente es Materiales. Revisa hormigón, acero, áridos y proveedores, ya que suelen concentrar una parte importante del carbono incorporado de una obra.",
  Transporte:
    "La categorí­a critica actualmente es Transporte. Reduce distancia, consolida viajes y evalúa proveedores cercanos para bajar emisiones logí­sticas.",
  Maquinaria:
    "La categorí­a critica actualmente es Maquinaria. Controla ralentí­, consumo por equipo y mantención para reducir emisiones durante la ejecución.",
  Energia:
    "La categorí­a critica actualmente es Energia. Revisa uso de generadores, consumo electrico de faena y horarios de operación.",
  Residuos:
    "La categorí­a critica actualmente es Residuos. Prioriza segregación, reciclaje y valorización para reducir disposición final.",
  Agua:
    "La categorí­a critica actualmente es Agua. Mejora el monitoreo y control de consumo para detectar desviaciones tempranas.",
  Otros:
    "La categorí­a critica actualmente es Otros. Clasifica mejor los registros para priorizar acciones de reducción más precisas.",
};

const tooltipContentStyle = {
  backgroundColor: "#FCFDFC",
  border: "1px solid #B7C6BD",
  borderRadius: "12px",
  color: "#1F2937",
  boxShadow: "0 12px 28px rgba(15, 23, 42, 0.12)",
};

const horizontalActiveBarStyle = {
  fill: "#6B7F75",
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
    return { label: "Alta", tone: "text-[#B42318]", panel: "border-[#F1B8B8] bg-[var(--danger-bg)]" };
  }

  if (pct >= 30) {
    return {
      label: "Media",
      tone: "text-[#7A4F00]",
      panel: "border-[#E1C56F] bg-[var(--warning-bg)]",
    };
  }

  return {
    label: "Baja",
    tone: "text-[var(--primary-dark)]",
    panel: "border-[var(--border)] bg-[var(--success-bg)]",
  };
}

function buildDecisionModel(data) {
  const kpis = data?.kpis || {};
  const total = Number(kpis.emisiones_totales || 0);
  const dieselPct = Number(kpis.porcentaje_diesel || 0);
  const topSourcePct = Number(kpis.porcentaje_top_fuente_emision || 0);
  const dieselEmissions = total * (dieselPct / 100);
  const estimatedReduction = dieselEmissions * (DIESEL_REDUCTION_SCENARIO / 100);
  const carKmEquivalent = estimatedReduction * 4;
  const homeMonthsEquivalent = estimatedReduction / 120;
  const dieselLevel = dependencyLevel(dieselPct);
  const criticalSource = kpis.fuente_critica || "Sin datos";
  const criticalUnit = kpis.unidad_critica || "Sin datos";
  const criticalCategory = kpis.categoria_critica || "Sin datos";

  if (!total) {
    return {
      heroTitle: "Aun no hay emisiones para decidir",
      heroSubtitle: "Registra datos de materiales, transporte, maquinaria, Energia y residuos para identificar focos de impacto.",
      recommendation: "Carga registros de obra con factores de emision para activar el análisis operativo.",
      dieselLevel,
      estimatedReduction,
      carKmEquivalent,
      homeMonthsEquivalent,
      risks: ["Aun no existen emisiones registradas para esta constructora."],
    };
  }

  const heroTitle =
    dieselPct >= 50
      ? "El diésel móvil concentra el principal riesgo operativo y ambiental"
      : `${criticalSource} concentra el principal riesgo operativo y ambiental`;
  const heroSubtitle =
    estimatedReduction > 0
      ? `Puedes reducir cerca de ${formatNumber(
          estimatedReduction,
          0
        )} kg CO²e con una intervención focalizada en ${criticalUnit}. La recomendación es comenzar con un piloto medible antes de avanzar hacia cambios mayores.`
      : "Prioriza la fuente principal para convertir el análisis en acción operativa.";
  const recommendation =
    dieselPct >= 30
      ? `Iniciar un piloto de reducción de diésel del 20% al 30% en ${criticalUnit}`
      : `Iniciar un piloto de reducción sobre ${criticalSource} en ${criticalUnit}`;
  const risks = [];

  if (dieselPct > 50) {
    risks.push(
      `Riesgo operativo:\nLa alta dependencia del diésel, equivalente al ${formatNumber(
        dieselPct,
        1
      )}% del consumo, puede aumentar la exposición a costos, riesgos regulatorios y baja eficiencia energética.`
    );
  }

  if (topSourcePct > 40) {
    risks.push(
      `Riesgo de concentración:\nLa combustión móvil de diésel representa el ${formatNumber(
        topSourcePct,
        1
      )}% de la huella total, por lo que cualquier mejora en este frente puede generar un impacto relevante.`
    );
  }

  if (criticalUnit !== "Sin datos") {
    risks.push(
      `Riesgo operativo localizado:\nLa etapa ${criticalUnit} concentra el mayor impacto, por lo que deberí­a ser priorizada en la estrategia de reducción.`
    );
  }

  if (criticalCategory !== "Sin datos") {
    risks.push(
      `Riesgo por categorí­a: ${getConstructionCategoryLabel(criticalCategory)} domina el perfil de emisiones de la constructora.`
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
  const { activeConstructora, activeConstructoraId, loadingConstructoras } = useConstructoraActiva();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [unitFilter, setUnitFilter] = useState("");
  const [obraFilter, setObraFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState("");
  const [aiSource, setAiSource] = useState("");
  const [loadingAi, setLoadingAi] = useState(false);
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [optimizedScenario, setOptimizedScenario] = useState(null);
  const [, setSimulatedScenario] = useState(null);

  useEffect(() => {
    if (!activeConstructoraId) {
      setData(null);
      return undefined;
    }

    let cancelled = false;
    setError("");

    const loadEmisiones = (showLoading = false) => {
      if (showLoading) {
        setLoading(true);
      }

      return getConstructoraEmisiones(activeConstructoraId)
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
              "No se pudieron cargar las emisiones de la constructora."
          );
        }
      })
      .finally(() => {
        if (!cancelled && showLoading) {
          setLoading(false);
        }
      });
    };

    loadEmisiones(true);
    const intervalId = window.setInterval(() => loadEmisiones(false), 5000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [activeConstructoraId]);

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
  fuente_critica: data?.fuente_critica ?? "Sin datos",
  unidad_critica: data?.unidad_critica ?? "Sin datos",
  categoria_critica: data?.categoria_critica ?? "Sin datos",
  porcentaje_diesel: data?.porcentaje_diesel ?? 0,
  porcentaje_top_fuente_emision: data?.porcentaje_top_fuente_emision ?? 0,
  promedio_emision_por_obra: data?.promedio_emision_por_obra ?? 0,
  registros_emision_sin_factor: data?.registros_emision_sin_factor ?? 0,
};
  const emissionsByUnit = useMemo(() => {
    if (Array.isArray(data?.emisiones_por_unidad)) {
      return data.emisiones_por_unidad
        .map((item) => ({
          unidad: item.unidad || "Sin unidad",
          emisiones: Number(item.emisiones || 0),
        }))
        .sort((left, right) => Number(right.emisiones || 0) - Number(left.emisiones || 0));
    }

    const totals = rows.reduce((accumulator, row) => {
      const unidad = row.etapa_nombre || "Sin unidad";
      accumulator[unidad] = (accumulator[unidad] || 0) + Number(row.emisiones || 0);
      return accumulator;
    }, {});

    return Object.entries(totals)
      .map(([unidad, emisiones]) => ({ unidad, emisiones }))
      .sort((left, right) => Number(right.emisiones || 0) - Number(left.emisiones || 0));
  }, [data?.emisiones_por_unidad, rows]);
  const emissionsByActivity = useMemo(() => {
    if (Array.isArray(data?.emisiones_por_fuente_emision)) {
      return data.emisiones_por_fuente_emision
        .map((item) => ({
          fuente_emision: item.fuente_emision || "Sin fuente",
          emisiones: Number(item.emisiones || 0),
        }))
        .sort((left, right) => Number(right.emisiones || 0) - Number(left.emisiones || 0));
    }

    const totals = rows.reduce((accumulator, row) => {
      const fuente_emision = row.fuente_emision || "Sin fuente";
      accumulator[fuente_emision] =
        (accumulator[fuente_emision] || 0) + Number(row.emisiones || 0);
      return accumulator;
    }, {});

    return Object.entries(totals)
      .map(([fuente_emision, emisiones]) => ({ fuente_emision, emisiones }))
      .sort((left, right) => Number(right.emisiones || 0) - Number(left.emisiones || 0));
  }, [data?.emisiones_por_fuente_emision, rows]);
  const unitBarSize = getBarSizeForRowCount(emissionsByUnit.length);
  const activityBarSize = getBarSizeForRowCount(emissionsByActivity.length);
  const decision = useMemo(() => buildDecisionModel(data), [data]);
  const rowsWithCategories = useMemo(
    () =>
      rows.map((row) => ({
        ...row,
        categoria_visible: getConstructionCategoryLabel(row.categoria, row.fuente_emision),
      })),
    [rows]
  );
  const emissionsByCategory = useMemo(() => {
    const totals = rowsWithCategories.reduce((accumulator, row) => {
      const category = row.categoria_visible || "Otros";
      accumulator[category] = (accumulator[category] || 0) + Number(row.emisiones || 0);
      return accumulator;
    }, {});

    return Object.entries(totals)
      .map(([categoria, emisiones]) => ({ categoria, emisiones }))
      .sort((left, right) => Number(right.emisiones || 0) - Number(left.emisiones || 0));
  }, [rowsWithCategories]);
  const criticalCategory = emissionsByCategory[0]?.categoria || getConstructionCategoryLabel(kpis.categoria_critica);
  const criticalSource = emissionsByActivity[0]?.fuente_emision || kpis.fuente_critica || "Sin datos";
  const rowsWithEvidence = rowsWithCategories.filter(
    (row) => row.evidencia || row.evidencia_id || row.evidencia_id || row.evidencia
  ).length;
  const categoryInsight = categoryInsightRules[criticalCategory] || categoryInsightRules.Otros;
  const decisionData = useMemo(
    () => ({
      total_emisiones: kpis.emisiones_totales || 0,
      datos: rows.map((row) => ({
        constructora: row.constructora || data?.constructora?.nombre || activeConstructora?.nombre || "",
        fuente_emision: row.fuente_emision,
        fuente_emision_key: row.fuente_emision_key,
        categoria: row.categoria,
        cantidad: row.cantidad,
        unidad: row.unidad,
        factor_emision: row.factor_emision,
        emisiones: row.emisiones,
        etapa: row.etapa_nombre,
        codigo_obra: row.codigo_obra,
      })),
    }),
    [activeConstructora?.nombre, data?.constructora?.nombre, kpis.emisiones_totales, rows]
  );
  const categoryOptions = constructionCategories;
  const unitOptions = useMemo(() => uniqueOptions(rows, "etapa_nombre"), [rows]);
  const obraOptions = useMemo(() => uniqueOptions(rows, "codigo_obra"), [rows]);
  const filteredRows = useMemo(() => {
    const query = normalizeText(search);

    return rowsWithCategories
      .filter((row) => {
        if (categoryFilter && row.categoria_visible !== categoryFilter) {
          return false;
        }
        if (unitFilter && row.etapa_nombre !== unitFilter) {
          return false;
        }
        if (obraFilter && row.codigo_obra !== obraFilter) {
          return false;
        }
        if (!query) {
          return true;
        }

        return normalizeText(
          [
            row.fuente_emision,
            row.etapa_nombre,
            row.etapa_id,
            row.codigo_obra,
            row.categoria,
            fuelUseLabels[row.tipo_consumo_combustible],
          ].join(" ")
        ).includes(query);
      })
      .sort((left, right) => Number(right.emisiones || 0) - Number(left.emisiones || 0));
  }, [categoryFilter, obraFilter, rowsWithCategories, search, unitFilter]);
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
  }, [categoryFilter, obraFilter, search, unitFilter]);

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
    const advisorScenario =
      optimizedScenario || optimizeScenario(decisionData.datos || []);

    try {
      setLoadingAi(true);
      const response = await getAiAdvisor({
        total_emisiones: kpis.emisiones_totales || 0,
        unidad_critica: kpis.unidad_critica || "Sin datos",
        fuente_critica: kpis.fuente_critica || "Sin datos",
        simulacion: null,
        optimizacion: advisorScenario,
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

  if (loadingConstructoras) {
    return <EmptyState title="Cargando constructoras" description="Preparando constructora activa." />;
  }

  if (!activeConstructoraId) {
    return (
      <EmptyState
        title="Selecciona o crea una constructora para revisar sus emisiones."
        description="La vista Emisiones trabaja siempre sobre la constructora activa."
      />
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)] sm:p-7">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <p className="flex items-center gap-2 text-sm font-semibold text-[var(--secondary)]">
              <Flame size={18} />
              Emisiones
            </p>
            <h1 className="mt-3 text-3xl font-bold sm:text-5xl">
              {decision.heroTitle}
            </h1>
            <p className="mt-4 text-base leading-7 text-[var(--text-muted)]">
              {decision.heroSubtitle}
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
          Insight automático
        </p>
        <h2 className="mt-2 text-2xl font-bold text-emerald-100">
          {categoryInsight}
        </h2>
        <p className="mt-2 text-sm leading-6 text-emerald-200">
          Mide el consumo antes y después de cada intervención, revisa resultados semanalmente y escala solo cuando la reducción se mantenga sin afectar la ejecución de obra.
        </p>
      </section>

      <section className="space-y-4">
        <SectionTitle title="Estado actual de registros de emision" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <DecisionKpi
            icon={<Activity />}
            label="Emisiones totales"
            value={`${formatNumber(kpis.emisiones_totales || 0, 1)} kg CO2e`}
          />
          <DecisionKpi
            icon={<Layers3 />}
            label="Categorí­a critica"
            value={criticalCategory || "Sin datos"}
          />
          <DecisionKpi
            detail={`${formatNumber(kpis.porcentaje_top_fuente_emision || 0, 1)}% del total`}
            icon={<BarChart3 />}
            label="Fuente critica"
            value={criticalSource}
          />
          <DecisionKpi
            icon={<Factory />}
            label="Registros de emision"
            value={formatNumber(rows.length, 0)}
          />
          <DecisionKpi
            icon={<Gauge />}
            label="Emisiones con evidencia"
            value={
              rowsWithEvidence > 0
                ? formatNumber(rowsWithEvidence, 0)
                : "Sin dato disponible"
            }
          />
          <DecisionKpi
            icon={<Target />}
            label="Etapa critica"
            value={kpis.unidad_critica || "Sin datos"}
          />
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-2">
        <ChartCard title="Emisiones por etapa / frente">
          <div className="h-64 sm:h-72 lg:h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={emissionsByUnit}
                layout="vertical"
                margin={{ top: 10, right: 10, left: 24, bottom: 10 }}
              >
                <XAxis
                  type="number"
                  stroke="#64748B"
                  tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }}
                  tickFormatter={formatNumber}
                />
                <YAxis
                  dataKey="unidad"
                  interval={0}
                  stroke="#64748B"
                  tick={{ fill: "#475569", fontSize: 11, fontWeight: 600 }}
                  tickFormatter={truncateChartLabel}
                  type="category"
                  width={150}
                />
                <Tooltip
                  contentStyle={tooltipContentStyle}
                  cursor={false}
                  formatter={formatTooltipValue}
                  labelStyle={{ color: "#1F2937", fontWeight: 700 }}
                  itemStyle={{ color: "#0B7D5D", fontWeight: 700 }}
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

        <ChartCard title="Emisiones por fuente">
          <div className="h-64 sm:h-72 lg:h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={emissionsByActivity}
                layout="vertical"
                margin={{ top: 10, right: 10, left: 24, bottom: 10 }}
              >
                <XAxis
                  type="number"
                  stroke="#64748B"
                  tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }}
                  tickFormatter={formatNumber}
                />
                <YAxis
                  dataKey="fuente_emision"
                  interval={0}
                  stroke="#64748B"
                  tick={{ fill: "#475569", fontSize: 11, fontWeight: 600 }}
                  tickFormatter={truncateChartLabel}
                  type="category"
                  width={150}
                />
                <Tooltip
                  contentStyle={tooltipContentStyle}
                  cursor={false}
                  formatter={formatTooltipValue}
                  labelStyle={{ color: "#1F2937", fontWeight: 700 }}
                  itemStyle={{ color: "#0B7D5D", fontWeight: 700 }}
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
        <div className="rounded-2xl border border-[#E1C56F] bg-[var(--warning-bg)] p-4 shadow-[var(--shadow-card)] sm:p-6">
          <SectionTitle eyebrow="Riesgos" title="Lo que puede afectar la operacion" />
          <div className="mt-4 space-y-3">
            {decision.risks.map((risk) => (
              <p
                key={risk}
                className="whitespace-pre-line rounded-2xl border border-[#E1C56F] bg-[#FFF9E8] p-4 text-sm font-medium leading-6 text-[#5F3B00]"
              >
                {risk}
              </p>
            ))}
          </div>
          {Number(kpis.registros_emision_sin_factor || 0) > 0 && (
            <p className="mt-4 flex items-center gap-2 rounded-2xl border border-[#F1B8B8] bg-[var(--danger-bg)] p-3 text-sm font-semibold text-[#B42318]">
              <AlertTriangle size={18} />
              Existen registros sin factor de emision asociado.
            </p>
          )}
        </div>

        <div className="rounded-2xl border border-[var(--border)] bg-[var(--info-bg)] p-4 shadow-[var(--shadow-card)] sm:p-6">
          <SectionTitle
            eyebrow="Impacto real"
            title={`Si reduces el consumo de diésel en un ${DIESEL_REDUCTION_SCENARIO}%`}
          />
          <div className="mt-4 space-y-3">
            <ImpactRow
              label="Reducción estimada:"
              value={`${formatNumber(decision.estimatedReduction, 0)} kg CO2e`}
            />
            <ImpactRow
              label="Equivalente aproximado a:"
              value={`${formatNumber(decision.carKmEquivalent, 0)} km recorridos en auto`}
            />
            <ImpactRow
              label="Impacto comparable con:"
              value={`Las emisiones mensuales aproximadas de ${formatNumber(
                decision.homeMonthsEquivalent,
                0
              )} hogares`}
            />
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
        <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Registros de emision</h2>
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
              placeholder="Buscar fuente, etapa, obra o categorí­a"
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 py-3 pl-11 pr-4 text-sm text-slate-100 outline-none transition focus:border-emerald-400/60"
            />
          </label>
          <FilterSelect
            label="Todas las categorí­as"
            onChange={setCategoryFilter}
            options={categoryOptions}
            value={categoryFilter}
          />
          <FilterSelect
            label="Todas las etapas"
            onChange={setUnitFilter}
            options={unitOptions}
            value={unitFilter}
          />
          <FilterSelect
            label="Todas las obras"
            onChange={setObraFilter}
            options={obraOptions}
            value={obraFilter}
          />
        </div>

        {rows.length === 0 && !loading ? (
          <div className="mt-5">
            <EmptyState
              title="Aún no hay registros de emision para esta obra."
              description="Agrega emisiones por materiales, transporte, maquinaria, Energia, agua o residuos para comenzar a medir la huella del proyecto."
            />
          </div>
        ) : (
          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[1380px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-left text-xs text-slate-400">
                  <th className="px-4 py-3">Fecha</th>
                  <th className="px-4 py-3">Obra</th>
                  <th className="px-4 py-3">Etapa / frente</th>
                  <th className="px-4 py-3">Categorí­a</th>
                  <th className="px-4 py-3">Fuente de emision</th>
                  <th className="px-4 py-3 text-right">Cantidad</th>
                  <th className="px-4 py-3">Etapa</th>
                  <th className="px-4 py-3 text-right">Factor</th>
                  <th className="px-4 py-3 text-right">Emisiones kg CO2e</th>
                  <th className="px-4 py-3">Evidencia</th>
                  <th className="px-4 py-3 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row) => {
                  const isCritical =
                    maxEmission > 0 && Number(row.emisiones || 0) >= maxEmission * 0.8;

                  return (
                    <tr
                      key={row.id}
                      className={`border-b border-slate-800/80 transition ${
                        isCritical
                          ? "bg-[var(--danger-bg)]/50"
                          : "hover:bg-[var(--success-bg)]/50"
                      }`}
                    >
                      <td className="px-4 py-4 text-slate-300">{row.fecha || "-"}</td>
                      <td className="px-4 py-4 text-slate-300">{row.codigo_obra || "-"}</td>
                      <td className="px-4 py-4 font-semibold text-slate-100">
                        {row.etapa_nombre || "Sin etapa"}
                      </td>
                      <td className="px-4 py-4">
                        <FactorCategoryBadge category={row.categoria_visible} />
                      </td>
                      <td className="px-4 py-4 font-semibold text-slate-100">
                        {row.fuente_emision}
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
                      <td className="px-4 py-4 text-slate-300">
                        <div className="space-y-1">
                          <p className="font-semibold text-slate-100">
                            {row.evidencia || row.evidencia || row.evidencia_id || row.evidencia_id ? "Sí­" : "No"}
                          </p>
                          <p className="text-xs text-slate-400">
                            {row.evidencia || row.evidencia_id || row.evidencia || row.evidencia_id
                              ? getConstructionEvidenceTypeLabel(row.tipo_evidencia || row.tipo_evidencia || row.evidencia_tipo)
                              : "Evidencia asociada: pendiente de vinculación"}
                          </p>
                          <p className="text-xs text-slate-500">
                            {row.estado_documental || row.estado_revision || row.estado_validacion
                              ? getConstructionEvidenceReviewLabel(row.estado_documental || row.estado_revision || row.estado_validacion)
                              : "Estado documental: pendiente de vinculación"}
                          </p>
                          <p className="text-xs text-slate-500">
                            {row.evidencia || row.evidencia || row.evidencia_id || row.evidencia_id
                              ? getConstructionEvidenceLinkLabel(row.estado_vinculo || row.estado_sistema)
                              : "Sin ví­nculo"}
                          </p>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-right">
                        <span className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs font-bold text-slate-300">
                          Ver
                        </span>
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
      <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
        {eyebrow}
      </p>
      <h2 className="mt-1 text-xl font-bold text-[var(--text-main)]">{title}</h2>
    </div>
  );
}

function DecisionKpi({ detail, icon, label, tone = "border-[var(--border)] bg-[var(--bg-card)]", value, valueClassName = "text-[var(--text-main)]" }) {
  return (
    <div className={`relative rounded-2xl border p-5 shadow-[var(--shadow-card)] ${tone}`}>
      {detail && (
        <p className="absolute right-4 top-4 rounded-full border border-[var(--border)] bg-[var(--info-bg)] px-3 py-1 text-xs font-bold text-[#075985]">
          {detail}
        </p>
      )}
      <div className="mb-4 flex items-center gap-3 pr-24">
        <div className="text-[var(--primary-dark)]">{icon}</div>
        <p className="text-sm font-medium text-[var(--text-muted)]">{label}</p>
      </div>
      <h3 className={`mt-1 pr-20 text-2xl font-bold ${valueClassName}`}>{value}</h3>
    </div>
  );
}

function ImpactRow({ label, value }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4">
      <p className="text-xs font-bold uppercase tracking-wide text-[var(--secondary)]">{label}</p>
      <p className="mt-1 text-2xl font-bold text-[#075985]">{value}</p>
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
