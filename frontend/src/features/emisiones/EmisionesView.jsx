import { useEffect, useMemo, useState } from "react";
import PlatformLoader from "@/shared/components/PlatformLoader";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Factory,
  Flame,
  Gauge,
  Layers3,
  Search,
  Sparkles,
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
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { optimizeScenario } from "@/features/dashboard/utils/optimizer";
import {
  constructionCategories,
  getConstructionCategoryLabel,
} from "@/features/obras/utils/constructionEmissionCategories";
import AnimatedModalShell from "@/shared/components/AnimatedModalShell";
import ChartCard from "@/shared/components/ChartCard";
import EmptyState from "@/shared/components/EmptyState";
import EmissionValue from "@/shared/components/EmissionValue";
import Pagination from "@/shared/components/Pagination";
import {
  getAiAdvisor,
  getOrganizacionEmisiones,
  optimizeScenarioApi,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";

const rowsPerPage = 8;
const DIESEL_REDUCTION_SCENARIO = 25;

const fuelUseLabels = {
  preparacion: "Preparación / movimiento",
  despacho: "Despacho",
  transporte: "Transporte",
  maquinaria: "Maquinaria",
  vehiculos: "Vehículos",
};

const categoryInsightRules = {
  Materiales:
    "La categoría crítica actualmente es Materiales. Revisa hormigón, acero, áridos y proveedores, ya que suelen concentrar una parte importante del carbono incorporado de una obra.",
  Transporte:
    "La categoría crítica actualmente es Transporte. Reduce distancia, consolida viajes y evalúa proveedores cercanos para bajar emisiones logísticas.",
  Maquinaria:
    "La categoría crítica actualmente es Maquinaria. Controla ralentí, consumo por equipo y mantención para reducir emisiones durante la ejecución.",
  Energia:
    "La categoría crítica actualmente es Energía. Revisa uso de generadores, consumo eléctrico de faena y horarios de operación.",
  Energía:
    "La categoría crítica actualmente es Energía. Revisa uso de generadores, consumo eléctrico de faena y horarios de operación.",
  Residuos:
    "La categoría crítica actualmente es Residuos. Prioriza segregación, reciclaje y valorización para reducir disposición final.",
  Agua:
    "La categoría crítica actualmente es Agua. Mejora el monitoreo y control de consumo para detectar desviaciones tempranas.",
  Otros:
    "La categoría crítica actualmente es Otros. Clasifica mejor los registros para priorizar acciones de reducción más precisas.",
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
  return text.length > 34 ? `${text.slice(0, 34)}...` : text;
}

function getBarSizeForRowCount(rowCount) {
  if (rowCount <= 1) return 34;
  if (rowCount <= 2) return 30;
  if (rowCount <= 4) return 24;
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

function getRowEmission(row) {
  return Number(row?.emisiones ?? row?.emisiones_kg_co2e ?? 0);
}

function formatRegistroUnit(value) {
  const rawUnit = String(value || "").trim();
  const normalizedUnit = normalizeText(rawUnit);

  if (!rawUnit) return "";
  if (normalizedUnit.includes("litros") || normalizedUnit === "l") return "L";
  if (normalizedUnit === "kwh") return "kWh";
  if (normalizedUnit === "m2" || normalizedUnit.includes("metro cuadrado")) return "m2";
  if (normalizedUnit === "m3" || normalizedUnit.includes("metro cubico")) return "m3";
  if (normalizedUnit.includes("ton")) return "ton";

  return rawUnit;
}

function formatQuantityWithUnit(row) {
  const unit = formatRegistroUnit(row?.unidad);
  const quantity = formatNumber(row?.cantidad || 0, 3);

  return unit ? `${quantity} ${unit}` : quantity;
}

function formatTableDate(value) {
  if (!value) return "-";

  const text = String(value);
  const match = text.match(/^(\d{4})-(\d{2})-(\d{2})/);

  if (match) {
    return `${match[3]}-${match[2]}-${match[1]}`;
  }

  const parsedDate = new Date(text);

  if (!Number.isNaN(parsedDate.getTime())) {
    const day = String(parsedDate.getDate()).padStart(2, "0");
    const month = String(parsedDate.getMonth() + 1).padStart(2, "0");
    const year = parsedDate.getFullYear();

    return `${day}-${month}-${year}`;
  }

  return text;
}

function getEvidenceStatus(row) {
  const evidence = row?.evidencia_asociada || null;
  const hasEvidence = Boolean(evidence || row?.evidencia || row?.evidencia_id);
  const rawStatus =
    evidence?.estado_documental ||
    row?.estado_documental ||
    row?.estado_revision ||
    row?.estado_validacion ||
    "";
  const normalizedStatus = normalizeText(rawStatus);
  const isValidated =
    hasEvidence &&
    (evidence?.estado_documental
      ? normalizedStatus === "verificada"
      : (normalizedStatus.includes("validada") ||
      normalizedStatus.includes("validado") ||
      normalizedStatus.includes("aprobada") ||
      normalizedStatus.includes("aprobado")));

  return {
    hasEvidence,
    label: hasEvidence ? "Sí" : "No",
    status: hasEvidence ? (isValidated ? "Validada" : "No validada") : "",
  };
}

function dependencyLevel(value) {
  const pct = Number(value || 0);

  if (pct >= 60) {
    return {
      label: "Alta",
      tone: "text-[#B42318]",
      panel: "border-[#FDA29B] bg-[#FEF3F2]",
    };
  }

  if (pct >= 30) {
    return {
      label: "Media",
      tone: "text-[#B45309]",
      panel: "border-[#FDBA74] bg-[#FFF7ED]",
    };
  }

  return {
    label: "Baja",
    tone: "text-[#047857]",
    panel: "border-[#A7F3D0] bg-[#ECFDF3]",
  };
}

function buildDecisionModel(data) {
  const kpis = data?.kpis || {};
  const total = Number(kpis.emisiones_totales || data?.total_emisiones || 0);
  const dieselPct = Number(kpis.porcentaje_diesel || 0);
  const topSourcePct = Number(kpis.porcentaje_top_fuente_emision || 0);
  const dieselEmissions = total * (dieselPct / 100);
  const estimatedReduction = dieselEmissions * (DIESEL_REDUCTION_SCENARIO / 100);
  const carKmEquivalent = estimatedReduction * 4;
  const homeMonthsEquivalent = estimatedReduction / 120;
  const dieselLevel = dependencyLevel(dieselPct);
  const criticalSource = kpis.fuente_critica || data?.fuente_critica || "Sin datos";
  const criticalUnit = kpis.unidad_critica || data?.unidad_critica || data?.etapa_critica || "Sin datos";
  const criticalCategory = kpis.categoria_critica || data?.categoria_critica || "Sin datos";

  if (!total) {
    return {
      heroTitle: "Aún no hay emisiones para decidir",
      heroSubtitle:
        "Registra datos de materiales, transporte, maquinaria, energía y residuos para identificar focos de impacto.",
      recommendation:
        "Carga registros de obra con factores de emisión para activar el análisis operativo.",
      dieselLevel,
      estimatedReduction,
      carKmEquivalent,
      homeMonthsEquivalent,
      risks: [
        "Todavía no existen emisiones calculadas para esta organizacion. El primer riesgo operativo es tomar decisiones sin una línea base confiable de materiales, energía, transporte, maquinaria y residuos.",
      ],
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
      )} kg CO2e con una intervención focalizada en ${criticalUnit}. La recomendación es comenzar con un piloto medible antes de avanzar hacia cambios mayores.`
      : "Prioriza la fuente principal para convertir el análisis en acción operativa.";
  const recommendation =
    dieselPct >= 30
      ? `Iniciar un piloto de reducción de diésel del 20% al 30% en ${criticalUnit}`
      : `Iniciar un piloto de reducción sobre ${criticalSource} en ${criticalUnit}`;
  const risks = [];

  if (dieselPct > 50) {
    risks.push(
      `La operación depende fuertemente del diésel: representa el ${formatNumber(
        dieselPct,
        1
      )}% de la huella total. Esto aumenta la exposición a costos de combustible, baja eficiencia energética y posibles exigencias ambientales futuras.`
    );
  }

  if (topSourcePct > 40) {
    risks.push(
      `La huella está muy concentrada en ${criticalSource}: esta fuente representa el ${formatNumber(
        topSourcePct,
        1
      )}% del total. Si no se interviene primero este foco, las reducciones en otras áreas tendrán un impacto limitado.`
    );
  }

  if (criticalUnit !== "Sin datos") {
    risks.push(
      `${criticalUnit} es la etapa que más presiona el resultado ambiental. Conviene priorizarla en la planificación, revisar consumos asociados y validar decisiones antes de avanzar a cambios de mayor costo.`
    );
  }

  if (criticalCategory !== "Sin datos") {
    risks.push(
      `${getConstructionCategoryLabel(
        criticalCategory
      )} domina el perfil de emisiones. El riesgo está en seguir comprando, ejecutando o registrando esta categoría sin trazabilidad suficiente para comparar alternativas.`
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
  const { activeOrganizacion, activeOrganizacionId, loadingOrganizaciones } = useOrganizacionActiva();
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
    if (!activeOrganizacionId) {
      setData(null);
      return undefined;
    }

    let cancelled = false;
    setError("");

    const loadEmisiones = (showLoading = false) => {
      if (showLoading) {
        setLoading(true);
      }

      return getOrganizacionEmisiones(activeOrganizacionId)
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
              "No se pudieron cargar las emisiones de la organizacion."
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
  }, [activeOrganizacionId]);

  const rows = useMemo(() => Array.isArray(data?.rows)
    ? data.rows
    : Array.isArray(data?.results)
      ? data.results
      : Array.isArray(data?.datos)
        ? data.datos
        : Array.isArray(data)
          ? data
          : [], [data]);

  const kpis = data?.kpis ?? {
    emisiones_totales: data?.total_emisiones ?? 0,
    fuente_critica: data?.fuente_critica ?? "Sin datos",
    unidad_critica: data?.unidad_critica ?? data?.etapa_critica ?? "Sin datos",
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
          emisiones: Number(item.emisiones || item.emisiones_kg_co2e || 0),
        }))
        .sort((left, right) => Number(right.emisiones || 0) - Number(left.emisiones || 0));
    }

    const totals = rows.reduce((accumulator, row) => {
      const unidad = row.etapa_nombre || "Sin unidad";
      accumulator[unidad] = (accumulator[unidad] || 0) + getRowEmission(row);
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
          emisiones: Number(item.emisiones || item.emisiones_kg_co2e || 0),
        }))
        .sort((left, right) => Number(right.emisiones || 0) - Number(left.emisiones || 0));
    }

    const totals = rows.reduce((accumulator, row) => {
      const fuente_emision = row.fuente_emision || "Sin fuente";
      accumulator[fuente_emision] =
        (accumulator[fuente_emision] || 0) + getRowEmission(row);
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
        emisiones: getRowEmission(row),
        categoria_visible: getConstructionCategoryLabel(row.categoria, row.fuente_emision),
      })),
    [rows]
  );

  const emissionsByCategory = useMemo(() => {
    const totals = rowsWithCategories.reduce((accumulator, row) => {
      const category = row.categoria_visible || "Otros";
      accumulator[category] = (accumulator[category] || 0) + getRowEmission(row);
      return accumulator;
    }, {});

    return Object.entries(totals)
      .map(([categoria, emisiones]) => ({ categoria, emisiones }))
      .sort((left, right) => Number(right.emisiones || 0) - Number(left.emisiones || 0));
  }, [rowsWithCategories]);

  const criticalCategory =
    emissionsByCategory[0]?.categoria || getConstructionCategoryLabel(kpis.categoria_critica);
  const criticalSource = emissionsByActivity[0]?.fuente_emision || kpis.fuente_critica || "Sin datos";
  const rowsWithEvidence = rowsWithCategories.filter(
    (row) => row.evidencia_asociada || row.evidencia || row.evidencia_id
  ).length;
  const categoryInsight = categoryInsightRules[criticalCategory] || categoryInsightRules.Otros;

  const decisionData = useMemo(
    () => ({
      total_emisiones: kpis.emisiones_totales || 0,
      datos: rowsWithCategories.map((row) => ({
        organizacion: row.organizacion || data?.organizacion?.nombre || activeOrganizacion?.nombre || "",
        fuente_emision: row.fuente_emision,
        fuente_emision_key: row.fuente_emision_key,
        categoria: row.categoria,
        cantidad: row.cantidad,
        unidad: row.unidad,
        factor_emision: row.factor_emision,
        emisiones: getRowEmission(row),
        etapa: row.etapa_nombre,
        codigo_obra: row.codigo_obra || row.obra_codigo,
      })),
    }),
    [activeOrganizacion?.nombre, data?.organizacion?.nombre, kpis.emisiones_totales, rowsWithCategories]
  );

  const categoryOptions = constructionCategories;
  const unitOptions = useMemo(() => uniqueOptions(rows, "etapa_nombre"), [rows]);
  const obraOptions = useMemo(
    () => Array.from(new Set(rows.map((row) => row.codigo_obra || row.obra_codigo).filter(Boolean))).sort(),
    [rows]
  );

  const filteredRows = useMemo(() => {
    const query = normalizeText(search);

    return rowsWithCategories
      .filter((row) => {
        const rowObra = row.codigo_obra || row.obra_codigo;

        if (categoryFilter && row.categoria_visible !== categoryFilter) return false;
        if (unitFilter && row.etapa_nombre !== unitFilter) return false;
        if (obraFilter && rowObra !== obraFilter) return false;
        if (!query) return true;

        return normalizeText(
          [
            row.fuente_emision,
            row.etapa_nombre,
            row.etapa_id,
            rowObra,
            row.obra_nombre,
            row.categoria,
            row.categoria_visible,
            fuelUseLabels[row.tipo_consumo_combustible],
          ].join(" ")
        ).includes(query);
      })
      .sort((left, right) => getRowEmission(right) - getRowEmission(left));
  }, [categoryFilter, obraFilter, rowsWithCategories, search, unitFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / rowsPerPage));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const visibleRows = filteredRows.slice(
    (safeCurrentPage - 1) * rowsPerPage,
    safeCurrentPage * rowsPerPage
  );
  const maxEmission = filteredRows[0]?.emisiones || 0;
  const formatTooltipValue = (value) => [`${formatNumber(value)} kg CO2e`, "Emisiones"];

  useEffect(() => {
    setCurrentPage(1);
  }, [categoryFilter, obraFilter, search, unitFilter]);

  const handleOptimize = async () => {
    try {
      const result = await optimizeScenarioApi(decisionData.datos || []);
      setOptimizedScenario(result);
    } catch {
      setOptimizedScenario(optimizeScenario(decisionData.datos || []));
    }
  };

  const handleAiAnalysis = async () => {
    setAiModalOpen(true);
    const advisorScenario = optimizedScenario || optimizeScenario(decisionData.datos || []);

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
      setAiAnalysis(
        requestError.response?.data?.error || "No se pudo generar el análisis IA."
      );
      setAiSource("");
    } finally {
      setLoadingAi(false);
    }
  };

  const openDecisionCenter = (shouldOptimize = false) => {
    setDecisionModalOpen(true);
    if (shouldOptimize) handleOptimize();
  };

  if (loadingOrganizaciones) {
    return (
      <PlatformLoader
        title="Cargando empresa activa"
        description="Estamos preparando la información ambiental de la empresa seleccionada."
      />
    );
  }

  if (!activeOrganizacionId) {
    if (loading && !data) {
      return (
        <PlatformLoader
          title="Cargando emisiones"
          description="Estamos calculando huella, fuentes críticas, evidencias y registros ambientales."
        />
      );
    }
    return (
      <EmptyState
        title="Selecciona o crea una organizacion para revisar sus emisiones."
        description="La vista Emisiones trabaja siempre sobre la organizacion activa."
      />
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <section className="relative overflow-hidden rounded-[34px] border border-emerald-200/70 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.20),transparent_34%),linear-gradient(135deg,rgba(15,45,39,0.98),rgba(18,61,52,0.96))] p-6 text-white shadow-[0_28px_90px_rgba(15,45,39,0.24)] sm:p-8">
        <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-emerald-300/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-24 left-10 h-72 w-72 rounded-full bg-teal-300/20 blur-3xl" />

        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-4xl">
            <p className="inline-flex items-center gap-2 rounded-full border border-emerald-300/25 bg-white/10 px-3 py-1 text-xs font-black uppercase tracking-[0.2em] text-emerald-100">
              <Flame size={16} />
              Emisiones operativas
            </p>

            <h1 className="mt-5 text-3xl font-black leading-tight tracking-tight sm:text-5xl">
              {decision.heroTitle}
            </h1>

            <p className="mt-4 max-w-3xl text-sm font-semibold leading-7 text-emerald-50/85 sm:text-base">
              {decision.heroSubtitle}
            </p>
          </div>

          <div className="grid min-w-[260px] gap-3">
            <button
              type="button"
              onClick={handleAiAnalysis}
              disabled={loadingAi}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/15 bg-white/10 px-5 py-3 text-sm font-black text-white shadow-[0_16px_32px_rgba(0,0,0,0.12)] transition hover:-translate-y-px hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Sparkles size={18} />
              {loadingAi ? "Analizando..." : "Generar análisis IA"}
            </button>

            <button
              type="button"
              onClick={() => openDecisionCenter(false)}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-300/25 bg-emerald-300/15 px-5 py-3 text-sm font-black text-emerald-50 shadow-[0_16px_32px_rgba(0,0,0,0.12)] transition hover:-translate-y-px hover:bg-emerald-300/20"
            >
              <TrendingDown size={18} />
              Simular escenario
            </button>

            <button
              type="button"
              onClick={() => openDecisionCenter(true)}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-teal-300/25 bg-teal-300/15 px-5 py-3 text-sm font-black text-teal-50 shadow-[0_16px_32px_rgba(0,0,0,0.12)] transition hover:-translate-y-px hover:bg-teal-300/20"
            >
              <Target size={18} />
              Ver plan operativo
            </button>
          </div>
        </div>
      </section>

      {error && (
        <p className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}

      <section className="rounded-3xl border border-emerald-200 bg-emerald-50 p-4 shadow-[var(--shadow-card)] sm:p-6">
        <p className="flex items-center gap-2 text-sm font-semibold text-emerald-700">
          <Target size={18} />
          Insight automático
        </p>
        <h2 className="mt-2 text-2xl font-bold text-emerald-900">{categoryInsight}</h2>
        <p className="mt-2 text-sm leading-6 text-emerald-800">
          Mide el consumo antes y después de cada intervención, revisa resultados semanalmente y escala solo cuando la reducción se mantenga sin afectar la ejecución de obra.
        </p>
      </section>

      <section className="space-y-4">
        <SectionTitle title="Estado actual de registros de emisión" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <DecisionKpi
            icon={<Activity />}
            label="Emisiones totales"
            value={<EmissionValue value={kpis.emisiones_totales || 0} />}
            tone="success"
          />
          <DecisionKpi
            icon={<Layers3 />}
            label="Categoría crítica"
            value={criticalCategory || "Sin datos"}
          />
          <DecisionKpi
            detail={`${formatNumber(kpis.porcentaje_top_fuente_emision || 0, 1)}% del total`}
            icon={<BarChart3 />}
            label="Fuente crítica"
            value={criticalSource}
          />
          <DecisionKpi
            icon={<Factory />}
            label="Registros de emisión"
            value={formatNumber(rows.length, 0)}
          />
          <DecisionKpi
            icon={<Gauge />}
            label="Emisiones con evidencia"
            value={rowsWithEvidence > 0 ? formatNumber(rowsWithEvidence, 0) : "Sin dato disponible"}
          />
          <DecisionKpi
            icon={<Target />}
            label="Etapa crítica"
            value={kpis.unidad_critica || kpis.etapa_critica || "Sin datos"}
          />
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-2">
        <ChartCard title="Emisiones por etapa">
          <div className="h-64 sm:h-72 lg:h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={emissionsByUnit}
                layout="vertical"
                margin={{ top: 10, right: 10, left: 46, bottom: 10 }}
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
                  width={185}
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
                margin={{ top: 10, right: 10, left: 46, bottom: 10 }}
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
                  width={185}
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
                  fill="#059669"
                  barSize={activityBarSize}
                  radius={[0, 10, 10, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border border-red-200 bg-red-50/80 p-4 shadow-[0_12px_28px_rgba(185,28,28,0.08)] sm:p-6">
          <SectionTitle eyebrow="Riesgos" title="Lo que puede afectar la operación" />
          <div className="mt-4 space-y-3">
            {decision.risks.map((risk) => (
              <RiskMessage key={risk}>{risk}</RiskMessage>
            ))}
          </div>
          {Number(kpis.registros_emision_sin_factor || 0) > 0 && (
            <RiskMessage icon={<AlertTriangle size={18} />}>
              Existen registros sin factor de emisión asociado. Antes de cerrar el análisis, valida esos datos para evitar decisiones con una huella subestimada.
            </RiskMessage>
          )}
        </div>

        <div className="rounded-2xl border border-blue-200 bg-blue-50/80 p-4 shadow-[0_12px_28px_rgba(37,99,235,0.08)] sm:p-6">
          <SectionTitle
            eyebrow="Impacto real"
            title={`Si reduces el consumo de diésel en un ${DIESEL_REDUCTION_SCENARIO}%`}
          />
          <div className="mt-4 space-y-3">
            <ImpactRow
              label="Reducción estimada"
              value={<EmissionValue value={decision.estimatedReduction} decimals={0} />}
            />
            <ImpactRow
              label="Equivalente aproximado"
              value={`${formatNumber(decision.carKmEquivalent, 0)} km recorridos en auto`}
            />
            <ImpactRow
              label="Impacto comparable"
              value={`Las emisiones mensuales aproximadas de ${formatNumber(
                decision.homeMonthsEquivalent,
                0
              )} hogares`}
            />
          </div>
        </div>
      </section>

      <section className="rounded-[32px] border border-emerald-200/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(240,253,250,0.82))] p-5 shadow-[0_24px_70px_rgba(15,118,110,0.10)] ring-1 ring-white/80 sm:p-6">
        <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
              Trazabilidad ambiental
            </p>
            <h2 className="mt-1 text-2xl font-black text-slate-950">Registros de emisión</h2>            <p className="mt-1 text-sm text-[var(--text-muted)]">
              {formatNumber(filteredRows.length, 0)} registros encontrados.
            </p>
          </div>
          {loading && <p className="text-sm font-semibold text-emerald-700">Cargando...</p>}
        </div>

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <label className="relative block">
            <Search
              size={18}
              className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar fuente, etapa, obra o categoría"
              className="w-full rounded-2xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-sm text-slate-900 outline-none transition focus:border-emerald-400/60"
            />
          </label>
          <FilterSelect
            label="Todas las categorías"
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
              title="Aún no hay registros de emisión para esta obra."
              description="Agrega emisiones por materiales, transporte, maquinaria, energía, agua o residuos para comenzar a medir la huella del proyecto."
            />
          </div>
        ) : (
          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[1080px] table-fixed border-collapse text-center text-sm">
              <colgroup>
                <col className="w-[16%]" />
                <col className="w-[13%]" />
                <col className="w-[10%]" />
                <col className="w-[15%]" />
                <col className="w-[8%]" />
                <col className="w-[7%]" />
                <col className="w-[11%]" />
                <col className="w-[12%]" />
                <col className="w-[8%]" />
              </colgroup>
              <thead>
                <tr className="border-b border-emerald-100 bg-emerald-50/60 text-center text-xs font-black uppercase tracking-[0.14em] text-emerald-900">
                  <th className="px-3 py-3">Nombre de la obra</th>
                  <th className="px-3 py-3">Etapa / frente</th>
                  <th className="px-3 py-3 text-center">Categoría</th>
                  <th className="px-3 py-3">Fuente de emisión</th>
                  <th className="px-3 py-3 text-right">Cantidad</th>
                  <th className="px-3 py-3 text-right">Factor</th>
                  <th className="px-3 py-3 text-right">Emisiones</th>
                  <th className="px-3 py-3 text-center">Evidencia</th>
                  <th className="px-3 py-3 text-right">Fecha</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row) => {
                  const rowEmission = getRowEmission(row);
                  const isCritical = maxEmission > 0 && rowEmission >= maxEmission * 0.8;
                  const evidenceStatus = getEvidenceStatus(row);
                  const obraName = row.obra_nombre || row.codigo_obra || row.obra_codigo || "-";

                  return (
                    <tr
                      key={row.id}
                      className={`border-b border-slate-100 transition ${isCritical ? "bg-red-50/50" : "hover:bg-emerald-50/50"
                        }`}
                    >
                      <td className="px-3 py-4 font-semibold leading-5 text-slate-900">{obraName}</td>
                      <td className="px-3 py-4 font-semibold leading-5 text-slate-900">
                        {row.etapa_nombre || "Sin etapa"}
                      </td>
                      <td className="px-3 py-4 text-center">
                        <FactorCategoryBadge category={row.categoria_visible} />
                      </td>
                      <td className="px-3 py-4 font-semibold leading-5 text-slate-900">
                        {row.fuente_emision || "Sin fuente"}
                      </td>
                      <td className="whitespace-nowrap px-3 py-4 text-right font-semibold text-slate-700">
                        {formatQuantityWithUnit(row)}
                      </td>
                      <td className="whitespace-nowrap px-3 py-4 text-right text-slate-600">
                        {formatNumber(row.factor_emision || 0, 4)}
                      </td>
                      <td className="whitespace-nowrap px-3 py-4 text-center font-black">
                        <EmissionValue value={rowEmission} />
                      </td>
                      <td className="px-3 py-4 text-center text-slate-600">
                        <div className="space-y-1 whitespace-nowrap">
                          <p className="font-bold text-slate-900">{evidenceStatus.label}</p>
                          {evidenceStatus.status && (
                            <p
                              className={`text-xs font-bold ${evidenceStatus.status === "Validada" ? "text-emerald-700" : "text-red-700"
                                }`}
                            >
                              {evidenceStatus.status}
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-3 py-4 text-right font-semibold text-slate-600">
                        {formatTableDate(row.fecha)}
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
            ariaLabel="Análisis estratégico IA"
            contentClassName="my-4 flex max-h-[calc(100vh-2rem)] w-full max-w-5xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl sm:my-6"
            onBackdropClick={() => setAiModalOpen(false)}
          >
            <div className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-200 bg-white p-4 sm:p-6">
              <div>
                <p className="text-sm font-semibold text-blue-700">Carbono Zero AI</p>
                <h2 className="mt-1 text-2xl font-bold text-slate-900">
                  Análisis estratégico generado por IA
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setAiModalOpen(false)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-500 transition hover:bg-slate-50"
                aria-label="Cerrar análisis IA"
              >
                <X size={18} />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
              {loadingAi ? (
                <p className="rounded-2xl border border-blue-200 bg-blue-50 p-5 text-sm font-semibold text-blue-700">
                  Generando análisis...
                </p>
              ) : (
                <div className="rounded-2xl border border-blue-200 bg-blue-50 p-5 text-slate-700">
                  {aiSource === "carbono_zero_engine" && (
                    <p className="mb-4 text-xs font-semibold text-emerald-700">
                      Generado por motor analítico Carbono Zero
                    </p>
                  )}
                  {aiSource === "openai" && (
                    <p className="mb-4 text-xs font-semibold text-blue-700">Generado con OpenAI</p>
                  )}
                  <p className="whitespace-pre-line leading-7">
                    {aiAnalysis || "Aún no hay análisis disponible."}
                  </p>
                </div>
              )}
            </div>
          </AnimatedModalShell>
        )}

        {decisionModalOpen && (
          <AnimatedModalShell
            ariaLabel="Centro de decisiones"
            contentClassName="my-4 flex max-h-[calc(100vh-2rem)] w-full max-w-6xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl sm:my-6"
            onBackdropClick={() => setDecisionModalOpen(false)}
          >
            <div className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-200 bg-white p-4 sm:p-6">
              <div>
                <p className="text-sm font-semibold text-emerald-700">Centro de decisiones</p>
                <h2 className="mt-1 text-2xl font-bold text-slate-900">
                  Simula y optimiza la operación activa
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setDecisionModalOpen(false)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-500 transition hover:bg-slate-50"
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
      {eyebrow && (
        <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
          {eyebrow}
        </p>
      )}
      <h2 className="mt-1 text-xl font-bold text-[var(--text-main)]">{title}</h2>
    </div>
  );
}

function DecisionKpi({ detail, icon, label, tone = "neutral", value }) {
  const tones = {
    success: {
      card: "border-emerald-200 bg-[linear-gradient(180deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_18px_45px_rgba(15,118,110,0.10)]",
      icon: "border-emerald-200 bg-emerald-50 text-emerald-700",
      value: "text-emerald-700",
    },
    warning: {
      card: "border-amber-200 bg-[linear-gradient(180deg,rgba(255,251,235,0.98),rgba(255,255,255,0.98))] shadow-[0_18px_45px_rgba(180,83,9,0.08)]",
      icon: "border-amber-200 bg-amber-50 text-amber-700",
      value: "text-amber-700",
    },
    danger: {
      card: "border-rose-200 bg-[linear-gradient(180deg,rgba(255,241,242,0.98),rgba(255,255,255,0.98))] shadow-[0_18px_45px_rgba(190,18,60,0.08)]",
      icon: "border-rose-200 bg-rose-50 text-rose-700",
      value: "text-rose-700",
    },
    info: {
      card: "border-sky-200 bg-[linear-gradient(180deg,rgba(240,249,255,0.98),rgba(255,255,255,0.98))] shadow-[0_18px_45px_rgba(2,132,199,0.08)]",
      icon: "border-sky-200 bg-sky-50 text-sky-700",
      value: "text-sky-700",
    },
    neutral: {
      card: "border-slate-200 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.98))] shadow-[0_18px_45px_rgba(15,23,42,0.06)]",
      icon: "border-slate-200 bg-slate-50 text-slate-700",
      value: "text-slate-900",
    },
  };

  const selectedTone = tones[tone] || tones.neutral;

  return (
    <article className={`relative min-h-[170px] rounded-[28px] border p-5 text-center ring-1 ring-white/70 ${selectedTone.card}`}>
      {detail ? (
        <div className="absolute right-4 top-4 rounded-full border border-white/70 bg-white/80 px-3 py-1 text-[11px] font-black uppercase tracking-wide text-slate-600 shadow-sm">
          {detail}
        </div>
      ) : null}

      <div className={`mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border shadow-sm ${selectedTone.icon}`}>
        {icon}
      </div>

      <p className="mt-4 text-xs font-black uppercase tracking-[0.18em] text-slate-500">
        {label}
      </p>

      <div className={`mt-3 flex min-h-[48px] items-center justify-center text-2xl font-black leading-tight ${selectedTone.value}`}>
        {value}
      </div>
    </article>
  );
}

function ImpactRow({ label, value }) {
  return (
    <div className="rounded-2xl border border-emerald-200 bg-white/90 p-4 text-center shadow-[0_12px_28px_rgba(15,118,110,0.08)]">
      <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
        {label}
      </p>
      <p className="mt-2 text-xl font-black text-emerald-900">
        {value}
      </p>
    </div>
  );
}

function RiskMessage({ children, icon = <AlertTriangle size={18} /> }) {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-white/70 p-4 text-sm font-semibold leading-6 text-red-800">
      <span className="mt-0.5 shrink-0 text-red-600">{icon}</span>
      <span>{children}</span>
    </div>
  );
}

function FilterSelect({ label, onChange, options, value }) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-emerald-400/60"
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
