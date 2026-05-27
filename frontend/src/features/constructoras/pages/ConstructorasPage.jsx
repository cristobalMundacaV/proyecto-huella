import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  Boxes,
  Building2,
  Factory,
  Gauge,
  Plus,
} from "lucide-react";

import ConstructoraForm from "../components/ConstructoraForm";
import RealtimeIotMonitoring from "@/features/dashboard/components/RealtimeIotMonitoring";
import Toast from "@/shared/components/Toast";
import {
  createConstructora,
  getConstructoraEtapas,
  getConstructoras,
} from "@/shared/services/api";
import { useToast } from "@/shared/hooks/useToast";
import { formatNumber } from "@/shared/utils/formatters";
import {
  isValidChileanRut,
  isValidEmail,
  isValidPhone,
} from "@/shared/utils/validators";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { getConstructionCategoryLabel } from "@/features/obras/utils/constructionEmissionCategories";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const emptyForm = {
  rut: "",
  nombre: "",
  region: "",
  comuna: "",
  rubro: "",
  direccion: "",
  email: "",
  telefono: "",
  observaciones: "",
};

const unitChartTooltipStyle = {
  backgroundColor: "#FCFDFC",
  border: "1px solid #B7C6BD",
  borderRadius: "12px",
  color: "#1F2937",
  boxShadow: "0 16px 35px rgba(15, 23, 42, 0.12)",
};

const stageBarColors = [
  "#0891B2",
  "#0F766E",
  "#2563EB",
  "#7C3AED",
  "#D97706",
  "#DC2626",
  "#475569",
];

const categoryColorMap = {
  materiales: "#0F766E",
  residuos: "#D97706",
  maquinaria: "#2563EB",
  energia: "#7C3AED",
  transporte: "#DC2626",
  agua: "#0891B2",
  otros: "#64748B",
};

const categoryFallbackColors = ["#0F766E", "#D97706", "#2563EB", "#7C3AED", "#DC2626", "#0891B2", "#64748B"];

const monthFormatter = new Intl.DateTimeFormat("es-CL", {
  month: "short",
  year: "2-digit",
});

function ConstructorasView({
  onSetActiveView,
  initialOpenCreate = false,
  openCreateSignal = 0,
}) {
  const [constructoras, setConstructoras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createModalOpen, setCreateModalOpen] = useState(initialOpenCreate);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [fieldErrors, setFieldErrors] = useState({});
  const [etapasOperativas, setEtapasOperativas] = useState([]);
  const [loadingEtapas, setLoadingEtapas] = useState(false);
  const {
    activeConstructora,
    activeConstructoraId,
    refreshConstructoras,
    setActiveConstructora,
  } = useConstructoraActiva();
  const { clearToast, showToast, toast } = useToast();

  const metrics = useMemo(
    () => buildCompanyMetrics(constructoras, etapasOperativas, activeConstructoraId, activeConstructora),
    [activeConstructora, activeConstructoraId, constructoras, etapasOperativas]
  );

  useEffect(() => {
    let isCancelled = false;

    async function loadconstructoras() {
      try {
        const data = await getConstructoras();

        if (!isCancelled) {
          setConstructoras(Array.isArray(data) ? data : []);
        }
      } catch (requestError) {
        if (!isCancelled) {
          setError(
            requestError.response?.data?.error ||
              "No se pudieron cargar las constructoras."
          );
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    loadconstructoras();

    return () => {
      isCancelled = true;
    };
  }, []);

  useEffect(() => {
    let isCancelled = false;

    async function loadEtapas() {
      if (!activeConstructoraId) {
        setEtapasOperativas([]);
        return;
      }

      setLoadingEtapas(true);

      try {
        const data = await getConstructoraEtapas(activeConstructoraId, { detail: "1" });

        if (!isCancelled) {
          setEtapasOperativas(Array.isArray(data) ? data : []);
        }
      } catch {
        if (!isCancelled) {
          setEtapasOperativas([]);
        }
      } finally {
        if (!isCancelled) {
          setLoadingEtapas(false);
        }
      }
    }

    loadEtapas();

    return () => {
      isCancelled = true;
    };
  }, [activeConstructoraId]);

  useEffect(() => {
    if (openCreateSignal > 0) {
      setError("");
      setFieldErrors({});
      setCreateModalOpen(true);
    }
  }, [openCreateSignal]);

  const updateForm = (event) => {
    const { name, value } = event.target;

    setForm((currentForm) => {
      if (name === "region") {
        return {
          ...currentForm,
          region: value,
          comuna: "",
        };
      }

      return { ...currentForm, [name]: value };
    });

    setFieldErrors((currentErrors) => ({
      ...currentErrors,
      [name]: null,
    }));
  };

  const handleCreateConstructora = async (event) => {
    event.preventDefault();
    const missingFields = ["rut", "nombre", "region", "comuna", "rubro", "email"].filter(
      (field) => !String(form[field] || "").trim()
    );
    const nextFieldErrors = {};

    missingFields.forEach((field) => {
      nextFieldErrors[field] = ["Campo obligatorio"];
    });

    if (form.rut && !isValidChileanRut(form.rut)) {
      nextFieldErrors.rut = ["Ingresa un RUT chileno válido."];
    }

    if (form.email && !isValidEmail(form.email)) {
      nextFieldErrors.email = ["Ingresa un email válido."];
    }

    if (form.telefono && !isValidPhone(form.telefono)) {
      nextFieldErrors.telefono = ["Ingresa un teléfono válido."];
    }

    if (Object.keys(nextFieldErrors).length > 0) {
      setFieldErrors(nextFieldErrors);
      if (missingFields.length === 1) {
        showToast(`Falta completar ${fieldLabels[missingFields[0]]}.`);
      } else if (missingFields.length > 1) {
        showToast("Hay campos vacíos.");
      } else {
        showToast("Hay campos con formato inválido.");
      }
      return;
    }

    setSaving(true);
    setError("");
    setFieldErrors({});

    try {
      const createdConstructora = await createConstructora(form);
      setConstructoras((currentConstructoras) => [createdConstructora, ...currentConstructoras]);
      setActiveConstructora(createdConstructora);
      await refreshConstructoras();
      setForm(emptyForm);
      setCreateModalOpen(false);
      onSetActiveView?.("dashboard");
    } catch (requestError) {
      const responseData = requestError.response?.data;

      if (responseData && typeof responseData === "object") {
        setFieldErrors(responseData);
      }

      setError("Revisa los datos de la constructora antes de guardarla.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <Toast
        message={toast?.message}
        onClose={clearToast}
        toastKey={toast?.id}
      />

      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="premium-card-interactive rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-3 shadow-[var(--shadow-soft)]">
            <Building2 className="text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold sm:text-4xl">Constructora</h1>
            <p className="max-w-3xl text-slate-400">
              Gestiona la constructora activa, sus etapas, obras y registros desde un mismo lugar, con trazabilidad lista para análisis, reportes y decisiones ambientales.
            </p>
          </div>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] px-5 py-3 text-sm font-bold text-[var(--primary-dark)]">
            Constructora activa
          </div>
          <button
            type="button"
            onClick={() => {
              setError("");
              setFieldErrors({});
              setCreateModalOpen(true);
            }}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] px-5 py-3 text-sm font-bold text-[var(--primary-dark)] transition hover:border-[var(--primary)]/40 hover:bg-[#D9F0E6]"
          >
            <Plus size={18} />
            Nueva constructora
          </button>
        </div>
      </header>

      <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--info-bg)] p-4 shadow-[var(--shadow-card)] sm:p-6">
        <p className="text-sm font-bold text-[#075985]">Resumen ejecutivo</p>
        <h2 className="mt-2 text-2xl font-bold text-[var(--text-main)]">
          Lectura operativa de la constructora
        </h2>
        <p className="mt-3 max-w-6xl text-base font-medium leading-8 text-[#334155]">
          {loadingEtapas ? "Cargando etapas / frentes..." : buildStrategicSummary(metrics)}
        </p>
      </section>

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <CompanyKpi
          icon={<Gauge />}
          label="Emisiones acumuladas"
          tone="cyan"
          value={`${formatNumber(metrics.totalEmissions, 1)} kg CO2e`}
        />
        <CompanyKpi
          detail={`${formatNumber(metrics.topObra?.emisiones || 0, 1)} kg CO2e`}
          icon={<Building2 />}
          label="Obra con más emisiones"
          value={metrics.topObra?.label || "Sin datos"}
        />
        <CompanyKpi
          detail={`${formatNumber(metrics.topCategory?.emisiones || 0, 1)} kg CO2e`}
          icon={<Boxes />}
          label="Categoría con más emisiones"
          value={metrics.topCategory?.label || "Sin datos"}
        />
        <CompanyKpi
          detail={`${formatNumber(metrics.topEmitter?.emisiones_totales_kg_co2e || 0, 1)} kg CO2e`}
          icon={<BarChart3 />}
          label="Etapa con más emisiones"
          value={metrics.topEmitter?.nombre || "Sin datos"}
        />
      </section>

      <RealtimeIotMonitoring activeConstructoraId={activeConstructoraId} />

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <UnitMetricBarChart
          dataKey="emisiones"
          description="Permite identificar rápidamente dónde se concentra el mayor problema ambiental."
          rows={metrics.unitComparisonRows}
          title="Emisiones por etapa / frente"
          valueLabel="Emisiones"
        />

        <CategoryStackedBarChart
          rows={metrics.categoryStackRows}
          segments={metrics.categoryStackSegments}
        />
      </section>

      <MonthlyEnvironmentalTrend rows={metrics.monthlyRows} />

      {error && (
        <p className="rounded-2xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
          {error}
        </p>
      )}

      {createModalOpen && (
        <ConstructoraForm
          error={error}
          fieldErrors={fieldErrors}
          form={form}
          loading={saving}
          onClose={() => {
            setCreateModalOpen(false);
            setError("");
          }}
          onSubmit={handleCreateConstructora}
          onUpdateForm={updateForm}
          onClearError={() => setError("")}
        />
      )}
    </div>
  );
}

function buildCompanyMetrics(constructoras, etapas = [], activeConstructoraId = "", activeConstructora = null) {
  const activeCompany =
    constructoras.find((constructora) => String(constructora.constructora_id) === String(activeConstructoraId)) ||
    constructoras.find((constructora) => String(constructora.id) === String(activeConstructoraId)) ||
    activeConstructora ||
    constructoras[0] ||
    null;
  const scopedUnits = etapas.filter((unidad) => {
    if (!activeCompany) {
      return true;
    }

    return (
      String(unidad.constructora_id || "") === String(activeCompany.constructora_id || "") ||
      String(unidad.constructora || "") === String(activeCompany.id || "")
    );
  });
  const registros = collectEmissionRecords(scopedUnits);
  const totals = {
    totalCompanies: constructoras.length,
    totalUnits: scopedUnits.length || Number(activeCompany?.etapas_count || 0),
    totalObras: scopedUnits.length
      ? scopedUnits.reduce((acc, unidad) => acc + Number(unidad.obras_count || 0), 0)
      : Number(activeCompany?.obras_count || 0),
    totalActivities: scopedUnits.length
      ? scopedUnits.reduce((acc, unidad) => acc + Number(unidad.registros_count || 0), 0)
      : Number(activeCompany?.registros_count || 0),
    totalEmissions: scopedUnits.length
      ? scopedUnits.reduce(
          (acc, unidad) => acc + Number(unidad.emisiones_totales_kg_co2e || 0),
          0
        )
      : Number(activeCompany?.emisiones_totales_kg_co2e || 0),
  };

  const topEmitter = maxBy(scopedUnits, (unidad) =>
    Number(unidad.emisiones_totales_kg_co2e || 0)
  );
  const topOperational = maxBy(scopedUnits, (unidad) =>
    Number(unidad.obras_count || 0) + Number(unidad.registros_count || 0)
  );
  const topObra = buildTopEmissionGroup(registros, (registro) =>
    registro.obra_nombre || registro.obra_codigo || registro.codigo_obra || "Sin obra"
  );
  const topCategory = buildTopEmissionGroup(registros, (registro) =>
    getConstructionCategoryLabel(registro.categoria, registro.fuente_emision) || "Otros"
  );
  const topEmissionShare =
    totals.totalEmissions > 0 && topEmitter
      ? (Number(topEmitter.emisiones_totales_kg_co2e || 0) / totals.totalEmissions) * 100
      : 0;
  const unitComparisonRows = scopedUnits
    .map((unidad, index) => ({
      unidad: unidad.nombre || unidad.etapa_id || "Sin etapa",
      emisiones: Number(unidad.emisiones_totales_kg_co2e || 0),
      color: stageBarColors[index % stageBarColors.length],
    }))
    .sort((left, right) => Number(right.emisiones || 0) - Number(left.emisiones || 0))
    .map((row, index) => ({
      ...row,
      color: stageBarColors[index % stageBarColors.length],
    }));
  const categoryStack = buildCategoryStackData(scopedUnits);
  const monthlyRows = buildMonthlyRows(scopedUnits);

  return {
    ...totals,
    activeCompany,
    topCategory,
    topEmitter,
    topEmissionShare,
    topObra,
    topOperational,
    categoryStackRows: categoryStack.rows,
    categoryStackSegments: categoryStack.segments,
    monthlyRows,
    unitComparisonRows,
  };
}

function collectEmissionRecords(etapas) {
  return etapas.flatMap((unidad) =>
    (unidad.registros_emision_resumen || []).map((registro) => ({
      ...registro,
      etapa_nombre: registro.etapa_nombre || unidad.nombre || unidad.etapa_id || "Sin etapa",
    }))
  );
}

function getRecordEmission(registro) {
  return Number(registro?.emisiones_kg_co2e || registro?.emisiones || 0);
}

function buildTopEmissionGroup(registros, labelSelector) {
  const totals = new Map();

  registros.forEach((registro) => {
    const emissions = getRecordEmission(registro);
    if (!emissions) return;
    const label = labelSelector(registro) || "Sin datos";
    totals.set(label, Number(totals.get(label) || 0) + emissions);
  });

  return Array.from(totals.entries())
    .map(([label, emisiones]) => ({ label, emisiones }))
    .sort((left, right) => right.emisiones - left.emisiones)[0] || null;
}

function buildCategoryStackData(etapas) {
  const categoryMap = new Map();
  const categoryTotals = new Map();
  const rows = etapas.map((unidad) => {
    const row = {
      unidad: unidad.nombre || unidad.etapa_id || "Sin etapa",
      total: 0,
    };

    (unidad.registros_emision_resumen || []).forEach((registro) => {
      const categoryLabel = getConstructionCategoryLabel(
        registro.categoria,
        registro.fuente_emision
      ) || "Otros";
      const emissions = getRecordEmission(registro);

      if (!emissions) return;

      if (!categoryMap.has(categoryLabel)) {
        categoryMap.set(categoryLabel, `categoria_${categoryMap.size}`);
      }

      const key = categoryMap.get(categoryLabel);
      row[key] = Number(row[key] || 0) + emissions;
      row.total += emissions;
      categoryTotals.set(categoryLabel, Number(categoryTotals.get(categoryLabel) || 0) + emissions);
    });

    return row;
  });

  const segments = Array.from(categoryMap.entries())
    .map(([label, key], index) => ({
      key,
      label,
      total: Number(categoryTotals.get(label) || 0),
      color: getCategoryColor(label, index),
    }))
    .sort((left, right) => right.total - left.total);

  return {
    rows: rows.filter((row) => row.total > 0).sort((left, right) => right.total - left.total),
    segments,
  };
}

function normalizeColorKey(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function getCategoryColor(label, index = 0) {
  const key = normalizeColorKey(label);
  return categoryColorMap[key] || categoryFallbackColors[index % categoryFallbackColors.length];
}

function buildStrategicSummary(metrics) {
  if (!metrics.activeCompany) {
    return "Selecciona o crea una constructora para comenzar a organizar sus etapas, obras, registros y evidencias dentro de Carbono Zero.";
  }

  const companyName = metrics.activeCompany.nombre || "La constructora";

  if (!metrics.totalUnits) {
    return `${companyName} aún no tiene etapas o frentes registrados. El siguiente paso es crear su estructura operativa para ordenar obras, asociar registros de emisión y activar una lectura ambiental confiable.`;
  }

  const topOperationalName = metrics.topOperational?.nombre || "la etapa con mayor actividad";
  const topEmitterName = metrics.topEmitter?.nombre || "la etapa con mayor huella";
  const topCategoryName = metrics.topCategory?.label || "la categoría principal";
  const hasEmissions = Number(metrics.totalEmissions || 0) > 0;
  const emissionShare = formatNumber(metrics.topEmissionShare, 1);
  const sameOperationalAndEmitter =
    normalizeColorKey(topOperationalName) === normalizeColorKey(topEmitterName);
  const concentration =
    metrics.topEmissionShare >= 60
      ? "una concentración alta"
      : metrics.topEmissionShare >= 35
        ? "una concentración relevante"
        : "una distribución relativamente balanceada";

  if (!hasEmissions) {
    return `${companyName} cuenta con ${formatNumber(metrics.totalUnits, 0)} etapas activas y su mayor carga operativa se observa en ${topOperationalName}. Aún no existe una huella de carbono suficientemente registrada para definir una etapa crítica por emisiones, por lo que el foco inmediato debe ser completar registros, vincular evidencias y validar factores de emisión antes de tomar decisiones de reducción.`;
  }

  const stageReading = sameOperationalAndEmitter
    ? `${topEmitterName} coincide como la etapa con mayor carga operativa y mayor concentración de emisiones: representa el ${emissionShare}% de la huella registrada.`
    : `La mayor carga operativa se observa en ${topOperationalName}, mientras que ${topEmitterName} concentra el ${emissionShare}% de las emisiones registradas.`;

  return `${companyName} cuenta con ${formatNumber(metrics.totalUnits, 0)} etapas activas. ${stageReading} ${topCategoryName} es la categoría con mayor impacto, lo que muestra ${concentration} del resultado ambiental. La decisión más importante es priorizar este foco, revisar sus fuentes principales y ejecutar acciones medibles donde exista mayor potencial de reducción.`;
}

function UnitMetricBarChart({ dataKey, description, rows, title, valueLabel }) {
  const visibleRows = (rows || [])
    .filter((row) => Number(row[dataKey] || 0) > 0)
    .sort((left, right) => Number(right[dataKey] || 0) - Number(left[dataKey] || 0));
  const chartHeight = Math.max(300, Math.min(470, visibleRows.length * 48 + 105));
  const legendItems = visibleRows.map((row) => ({ label: row.unidad, color: row.color }));

  if (!visibleRows.length) {
    return null;
  }

  return (
    <ChartPanel description={description} title={title}>
      <div className="w-full" style={{ height: chartHeight }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={visibleRows}
            layout="vertical"
            margin={{ top: 8, right: 18, bottom: 8, left: 10 }}
          >
            <CartesianGrid horizontal={false} stroke="#D8E1DC" />
            <XAxis
              axisLine={{ stroke: "#64748B" }}
              tick={{ fill: "#475569", fontSize: 11, fontWeight: 600 }}
              tickFormatter={(value) => formatNumber(Number(value || 0), 0)}
              tickLine={false}
              type="number"
            />
            <YAxis
              axisLine={{ stroke: "#64748B" }}
              dataKey="unidad"
              tick={{ fill: "#475569", fontSize: 11, fontWeight: 600 }}
              tickLine={false}
              type="category"
              width={135}
            />
            <Tooltip
              contentStyle={unitChartTooltipStyle}
              cursor={{ fill: "rgba(148, 163, 184, 0.08)" }}
              formatter={(value) => [
                `${formatNumber(Number(value || 0), 1)} kg CO2e`,
                valueLabel,
              ]}
              labelStyle={{ color: "#1F2937", fontWeight: 700 }}
            />
            <Bar
              barSize={18}
              dataKey={dataKey}
              name={valueLabel}
              radius={[0, 10, 10, 0]}
            >
              {visibleRows.map((row) => (
                <Cell key={row.unidad} fill={row.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ChartLegend items={legendItems} />
    </ChartPanel>
  );
}

function CategoryStackedBarChart({ rows, segments }) {
  const visibleRows = rows || [];
  const visibleSegments = (segments || []).filter((segment) => Number(segment.total || 0) > 0);
  const chartHeight = Math.max(300, Math.min(470, visibleRows.length * 48 + 105));

  if (!visibleRows.length || !visibleSegments.length) {
    return null;
  }

  return (
    <ChartPanel
      description="Muestra cómo se distribuyen las emisiones de cada etapa según sus categorías principales."
      title="Emisiones por categoría"
    >
      <div className="w-full" style={{ height: chartHeight }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={visibleRows}
            layout="vertical"
            margin={{ top: 8, right: 18, bottom: 8, left: 10 }}
          >
            <CartesianGrid horizontal={false} stroke="#D8E1DC" />
            <XAxis
              axisLine={{ stroke: "#64748B" }}
              tick={{ fill: "#475569", fontSize: 11, fontWeight: 600 }}
              tickFormatter={(value) => formatNumber(Number(value || 0), 0)}
              tickLine={false}
              type="number"
            />
            <YAxis
              axisLine={{ stroke: "#64748B" }}
              dataKey="unidad"
              tick={{ fill: "#475569", fontSize: 11, fontWeight: 600 }}
              tickLine={false}
              type="category"
              width={135}
            />
            <Tooltip
              contentStyle={unitChartTooltipStyle}
              cursor={{ fill: "rgba(148, 163, 184, 0.08)" }}
              formatter={(value, name) => [
                `${formatNumber(Number(value || 0), 1)} kg CO2e`,
                name,
              ]}
              labelStyle={{ color: "#1F2937", fontWeight: 700 }}
            />
            {visibleSegments.map((segment, index) => (
              <Bar
                key={segment.key}
                barSize={22}
                dataKey={segment.key}
                fill={segment.color}
                name={segment.label}
                radius={index === visibleSegments.length - 1 ? [0, 10, 10, 0] : [0, 0, 0, 0]}
                stackId="emisiones_categoria"
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ChartLegend items={visibleSegments.map((segment) => ({ label: segment.label, color: segment.color }))} />
    </ChartPanel>
  );
}

function ChartLegend({ items }) {
  if (!items?.length) {
    return null;
  }

  return (
    <div className="mt-4 flex flex-wrap justify-center gap-2.5 border-t border-slate-100 pt-4">
      {items.map((item) => (
        <span
          key={`${item.label}-${item.color}`}
          className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-bold text-slate-600 shadow-[0_4px_10px_rgba(15,23,42,0.04)]"
        >
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
          {item.label}
        </span>
      ))}
    </div>
  );
}

function MonthlyEnvironmentalTrend({ rows }) {
  if (!rows?.length) {
    return null;
  }

  return (
    <ChartPanel
      description="Ayuda a ver si la operación aumenta o reduce sus emisiones en el tiempo."
      title="Evolución mensual de emisiones"
    >
      <div className="h-[360px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 10, right: 24, bottom: 8, left: 8 }}>
            <CartesianGrid stroke="#B8C6BE" vertical={false} />
            <XAxis
              axisLine={{ stroke: "#64748B" }}
              dataKey="mes_label"
              tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }}
              tickLine={false}
            />
            <YAxis
              axisLine={{ stroke: "#64748B" }}
              tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }}
              tickFormatter={(value) => formatNumber(Number(value || 0), 0)}
              tickLine={false}
            />
            <Tooltip
              contentStyle={unitChartTooltipStyle}
              formatter={(value, name) => [
                `${formatNumber(Number(value || 0), 1)} kg CO2e`,
                trendLabels[name] || name,
              ]}
              labelStyle={{ color: "#1F2937", fontWeight: 700 }}
            />
            <Line
              dataKey="emisiones"
              dot={{ r: 3 }}
              name="Emisiones"
              stroke="#0891B2"
              strokeWidth={3}
              type="monotone"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </ChartPanel>
  );
}

function ChartPanel({ children, description, title }) {
  return (
    <section className="premium-card premium-card-interactive rounded-2xl bg-[var(--bg-surface)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <ChartHeading description={description} title={title} />
      {children}
    </section>
  );
}

function ChartHeading({ description, title }) {
  return (
    <div className="mb-5">
      <h2 className="mt-2 text-2xl font-bold text-[var(--text-main)]">{title}</h2>
      {description && (
        <p className="mt-2 max-w-4xl text-sm font-medium leading-6 text-[var(--text-muted)]">{description}</p>
      )}
    </div>
  );
}

function buildMonthlyRows(etapas) {
  const months = new Map();

  etapas.forEach((unidad) => {
    (unidad.registros_emision_resumen || []).forEach((fuente_emision) => {
      const monthKey = getMonthKey(fuente_emision.fecha);

      if (!monthKey) {
        return;
      }

      const row = ensureMonth(months, monthKey);
      row.emisiones += getRecordEmission(fuente_emision);
    });
  });

  return Array.from(months.values())
    .sort((left, right) => left.mes.localeCompare(right.mes))
    .map((row) => ({
      ...row,
      mes_label: formatMonth(row.mes),
    }));
}

function ensureMonth(months, monthKey) {
  if (!months.has(monthKey)) {
    months.set(monthKey, {
      mes: monthKey,
      emisiones: 0,
    });
  }

  return months.get(monthKey);
}

function getMonthKey(value) {
  if (!value) {
    return "";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function formatMonth(monthKey) {
  const [year, month] = String(monthKey || "").split("-");
  const date = new Date(Number(year), Number(month) - 1, 1);

  if (Number.isNaN(date.getTime())) {
    return monthKey;
  }

  return monthFormatter.format(date).replace(".", "");
}

const trendLabels = {
  emisiones: "Emisiones",
};

function maxBy(items, selector) {
  if (!items.length) {
    return null;
  }

  return items.reduce((best, item) => (selector(item) > selector(best) ? item : best), items[0]);
}

function CompanyKpi({ detail, icon, label, tone = "slate", value }) {
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

const fieldLabels = {
  rut: "RUT",
  nombre: "nombre",
  region: "región",
  comuna: "comuna",
  rubro: "rubro",
  email: "email",
};

export default ConstructorasView;
