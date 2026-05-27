import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  Boxes,
  Building2,
  Factory,
  FileCheck2,
  Gauge,
  Leaf,
  Plus,
  ShieldCheck,
  Target,
} from "lucide-react";

import ConstructoraForm from "../components/ConstructoraForm";
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
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
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
      nextFieldErrors.rut = ["Ingresa un RUT chileno valido."];
    }

    if (form.email && !isValidEmail(form.email)) {
      nextFieldErrors.email = ["Ingresa un email valido."];
    }

    if (form.telefono && !isValidPhone(form.telefono)) {
      nextFieldErrors.telefono = ["Ingresa un telefono valido."];
    }

    if (Object.keys(nextFieldErrors).length > 0) {
      setFieldErrors(nextFieldErrors);
      if (missingFields.length === 1) {
        showToast(`Falta completar ${fieldLabels[missingFields[0]]}.`);
      } else if (missingFields.length > 1) {
        showToast("Hay campos vacios.");
      } else {
        showToast("Hay campos con formato invalido.");
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
          icon={<Building2 />}
          label="constructora seleccionada"
          value={metrics.activeCompany?.nombre || "Sin datos"}
        />
        <CompanyKpi
          icon={<Factory />}
          label="Etapas activas"
          value={metrics.totalUnits}
        />
        <CompanyKpi icon={<Boxes />} label="Obras registradas" value={metrics.totalObras} />
        <CompanyKpi
          icon={<Activity />}
          label="Registros"
          value={metrics.totalActivities}
        />
        <CompanyKpi
          icon={<Gauge />}
          label="Emisiones acumuladas"
          tone="cyan"
          value={`${formatNumber(metrics.totalEmissions, 1)} kg CO2e`}
        />
        <CompanyKpi
          icon={<Leaf />}
          label="Balance ambiental"
          tone="emerald"
          value={`${formatNumber(metrics.totalStoredCarbon, 1)} kg`}
        />
        <CompanyKpi
          detail={`${formatNumber(
            metrics.topEmitter?.emisiones_totales_kg_co2e || 0,
            1
          )} kg CO2e`}
          icon={<BarChart3 />}
          label="Etapa con mayor emision"
          value={metrics.topEmitter?.nombre || "Sin datos"}
        />
        <CompanyKpi
          detail={`${formatNumber(
            Math.abs(Number(metrics.bestBalance?.balance_neto_kg_co2e || 0)),
            1
          )} kg CO2e`}
          icon={<ShieldCheck />}
          label="Etapa con mejor balance"
          tone="emerald"
          value={metrics.bestBalance?.nombre || "Sin datos"}
        />
      </section>

      <EnvironmentalBalanceWaterfall
        emissions={metrics.totalEmissions}
        storedCarbon={metrics.totalStoredCarbon}
      />

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <InsightCard
          icon={<Gauge />}
          label="Etapa lider en emisiones"
          value={metrics.topEmitter?.nombre || "Sin datos"}
        />
        <InsightCard
          icon={<Factory />}
          label="Etapa con mayor fuente_emision"
          value={metrics.topOperational?.nombre || "Sin datos"}
        />
        <InsightCard
          icon={<Leaf />}
          label="Etapa con mayor balance ambiental"
          value={metrics.topStorage?.nombre || "Sin datos"}
        />
        <InsightCard
          icon={<FileCheck2 />}
          label="Etapa con mayor trazabilidad"
          value={metrics.topTraceability?.nombre || "Sin datos"}
        />
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <UnitMetricBarChart
          color="#22D3EE"
          dataKey="emisiones"
          description="Permite identificar rapidamente donde se concentra el mayor problema ambiental."
          rows={metrics.unitComparisonRows}
          title="Emisiones por etapa / frente"
          valueLabel="Emisiones"
        />

        <UnitMetricBarChart
          color="#34D399"
          dataKey="balance_ambiental"
          description="Muestra qué etapas aportan más al balance ambiental positivo."
          rows={metrics.unitComparisonRows}
          title="Balance ambiental por etapa / frente"
          valueLabel="Balance ambiental"
        />
      </section>

      <UnitEmissionsCarbonChart rows={metrics.unitComparisonRows} />

      <MonthlyEnvironmentalTrend rows={metrics.monthlyRows} />

      <OrderedUnitComparisonChart rows={metrics.unitComparisonRows} />

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
    totalStoredCarbon: scopedUnits.length
      ? scopedUnits.reduce((acc, unidad) => acc + getUnitStoredCarbon(unidad), 0)
      : Number(activeCompany?.balance_ambiental_kg || 0),
    totalPassports: scopedUnits.length
      ? scopedUnits.reduce((acc, unidad) => acc + Number(unidad.fichas_ambientales_count || 0), 0)
      : Number(activeCompany?.fichas_ambientales_emitidas || 0),
    totalEvidence: scopedUnits.length
      ? scopedUnits.reduce((acc, unidad) => acc + Number(unidad.evidencias_count || 0), 0)
      : Number(activeCompany?.evidencias_count || 0),
  };

  const topEmitter = maxBy(scopedUnits, (unidad) =>
    Number(unidad.emisiones_totales_kg_co2e || 0)
  );
  const topOperational = maxBy(scopedUnits, (unidad) =>
    Number(unidad.obras_count || 0) + Number(unidad.registros_count || 0)
  );
  const topStorage = maxBy(scopedUnits, getUnitStoredCarbon);
  const topTraceability = maxBy(scopedUnits, (unidad) =>
    Number(unidad.fichas_ambientales_count || 0) + Number(unidad.evidencias_count || 0)
  );
  const bestBalance =
    scopedUnits
      .map((unidad) => ({
        ...unidad,
        balance_neto_kg_co2e:
          Number(unidad.emisiones_totales_kg_co2e || 0) - getUnitStoredCarbon(unidad),
      }))
      .filter((unidad) => Number(unidad.balance_neto_kg_co2e || 0) < 0)
      .sort(
        (left, right) =>
          Number(left.balance_neto_kg_co2e || 0) -
          Number(right.balance_neto_kg_co2e || 0)
      )[0] || null;
  const topEmissionShare =
    totals.totalEmissions > 0 && topEmitter
      ? (Number(topEmitter.emisiones_totales_kg_co2e || 0) / totals.totalEmissions) * 100
      : 0;
  const globalBalance = totals.totalEmissions - totals.totalStoredCarbon;
  const unitComparisonRows = scopedUnits
    .map((unidad) => {
      const emissions = Number(unidad.emisiones_totales_kg_co2e || 0);
      const storedCarbon = getUnitStoredCarbon(unidad);

      return {
        unidad: unidad.nombre || unidad.etapa_id || "Sin etapa",
        balance_ambiental: storedCarbon,
        emisiones: emissions,
        emisiones_comparacion: emissions ? -emissions : 0,
      };
    })
    .sort(
      (left, right) =>
        Math.max(right.emisiones, right.balance_ambiental) -
        Math.max(left.emisiones, left.balance_ambiental)
    );
  const monthlyRows = buildMonthlyRows(scopedUnits);

  return {
    ...totals,
    activeCompany,
    bestBalance,
    globalBalance,
    topEmitter,
    topEmissionShare,
    topOperational,
    topStorage,
    topTraceability,
    monthlyRows,
    unitComparisonRows,
  };
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
  const topTraceabilityName = metrics.topTraceability?.nombre || "la etapa con mejor trazabilidad";
  const hasEmissions = Number(metrics.totalEmissions || 0) > 0;
  const emissionShare = formatNumber(metrics.topEmissionShare, 1);
  const concentration =
    metrics.topEmissionShare >= 60
      ? "una concentración alta"
      : metrics.topEmissionShare >= 35
        ? "una concentración relevante"
        : "una distribución relativamente balanceada";
  const balanceText =
    metrics.globalBalance < 0
      ? "El balance general se mantiene favorable gracias al aporte ambiental registrado, por lo que conviene proteger esa ventaja con evidencia y seguimiento."
      : "El balance general todavía requiere acciones de reducción, por lo que conviene priorizar los focos con mayor impacto antes de escalar cambios operativos.";

  if (!hasEmissions) {
    return `${companyName} cuenta con ${formatNumber(metrics.totalUnits, 0)} etapas activas y su mayor carga operativa se observa en ${topOperationalName}. Aún no existe una huella de carbono suficientemente registrada para definir una etapa crítica por emisiones, por lo que el foco inmediato debe ser completar registros, vincular evidencias y validar factores de emisión antes de tomar decisiones de reducción.`;
  }

  return `${companyName} cuenta con ${formatNumber(metrics.totalUnits, 0)} etapas activas. La mayor carga operativa se observa en ${topOperationalName}, mientras que ${topEmitterName} concentra el ${emissionShare}% de las emisiones registradas, lo que muestra ${concentration} del impacto ambiental. ${topTraceabilityName} presenta el mejor respaldo documental disponible, pero la decisión más importante es cruzar esa trazabilidad con los focos de mayor huella para priorizar acciones medibles. ${balanceText}`;
}

function UnitMetricBarChart({ color, dataKey, description, rows, title, valueLabel }) {
  const visibleRows = (rows || [])
    .filter((row) => Number(row[dataKey] || 0) > 0)
    .sort((left, right) => Number(right[dataKey] || 0) - Number(left[dataKey] || 0));
  const chartHeight = Math.max(300, Math.min(520, visibleRows.length * 52 + 110));

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
            margin={{ top: 8, right: 24, bottom: 8, left: 24 }}
          >
            <CartesianGrid horizontal={false} stroke="#B8C6BE" />
            <XAxis
              axisLine={{ stroke: "#64748B" }}
              tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }}
              tickFormatter={(value) => formatNumber(Number(value || 0), 0)}
              tickLine={false}
              type="number"
            />
            <YAxis
              axisLine={{ stroke: "#64748B" }}
              dataKey="unidad"
              tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }}
              tickLine={false}
              type="category"
              width={180}
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
              fill={color}
              name={valueLabel}
              radius={[0, 10, 10, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartPanel>
  );
}

function UnitEmissionsCarbonChart({ rows }) {
  const visibleRows = (rows || []).filter(
    (row) => Number(row.emisiones || 0) > 0 || Number(row.balance_ambiental || 0) > 0
  );
  const chartHeight = Math.max(320, Math.min(560, visibleRows.length * 58 + 120));

  if (!visibleRows.length) {
    return null;
  }

  return (
    <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <ChartHeading
          description="Contraste entre la huella generada y el balance ambiental por cada etapa."
          title="Emisiones vs balance ambiental"
        />
        <div className="flex flex-wrap gap-3 text-xs font-semibold">
          <span className="inline-flex items-center gap-2 text-[#075985]">
            <span className="h-2.5 w-2.5 rounded-full bg-cyan-300" />
            Emisiones
          </span>
          <span className="inline-flex items-center gap-2 text-[var(--primary-dark)]">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-300" />
            Balance ambiental
          </span>
        </div>
      </div>

      <div className="w-full" style={{ height: chartHeight }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={visibleRows}
            layout="vertical"
            margin={{ top: 8, right: 24, bottom: 8, left: 24 }}
          >
            <XAxis
              axisLine={{ stroke: "#64748B" }}
              tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }}
              tickFormatter={(value) => formatNumber(Math.abs(Number(value || 0)), 0)}
              tickLine={false}
              type="number"
            />
            <YAxis
              axisLine={{ stroke: "#64748B" }}
              dataKey="unidad"
              tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }}
              tickLine={false}
              type="category"
              width={170}
            />
            <Tooltip
              contentStyle={unitChartTooltipStyle}
              cursor={{ fill: "rgba(148, 163, 184, 0.08)" }}
              formatter={(value, name) => {
                const label =
                  name === "emisiones_comparacion"
                    ? "Emisiones"
                    : "Balance ambiental";

                return [
                  `${formatNumber(Math.abs(Number(value || 0)), 1)} kg CO2e`,
                  label,
                ];
              }}
              labelStyle={{ color: "#1F2937", fontWeight: 700 }}
            />
            <ReferenceLine stroke="#64748B" x={0} />
            <Bar
              barSize={18}
              dataKey="emisiones_comparacion"
              fill="#22D3EE"
              name="Emisiones"
              radius={[10, 0, 0, 10]}
            />
            <Bar
              barSize={18}
              dataKey="balance_ambiental"
              fill="#34D399"
              name="Balance ambiental"
              radius={[0, 10, 10, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function MonthlyEnvironmentalTrend({ rows }) {
  if (!rows?.length) {
    return null;
  }

  return (
    <ChartPanel
      description="Ayuda a ver si la operacion esta aumentando o reduciendo su impacto en el tiempo."
      title="Evolucion mensual de emisiones, carbono y balance"
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
              stroke="#22D3EE"
              strokeWidth={3}
              type="monotone"
            />
            <Line
              dataKey="balance_ambiental"
              dot={{ r: 3 }}
              name="Balance ambiental"
              stroke="#34D399"
              strokeWidth={3}
              type="monotone"
            />
            <Line
              dataKey="balance_neto"
              dot={{ r: 3 }}
              name="Balance neto"
              stroke="#FBBF24"
              strokeWidth={3}
              type="monotone"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </ChartPanel>
  );
}

function OrderedUnitComparisonChart({ rows }) {
  const visibleRows = (rows || [])
    .filter((row) => Number(row.emisiones || 0) > 0 || Number(row.balance_ambiental || 0) > 0)
    .sort(
      (left, right) =>
        Number(right.emisiones || 0) - Number(left.emisiones || 0) ||
        Number(right.balance_ambiental || 0) - Number(left.balance_ambiental || 0)
    );
  const chartHeight = Math.max(340, Math.min(560, visibleRows.length * 62 + 120));

  if (!visibleRows.length) {
    return null;
  }

  return (
    <ChartPanel
      description="Este grafico compara las emisiones y el balance ambiental por etapa. Las etapas se ordenan por mayor emision para identificar donde actuar primero."
      title="Emisiones y balance ambiental por etapa"
    >
      <div className="w-full" style={{ height: chartHeight }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={visibleRows}
            layout="vertical"
            margin={{ top: 8, right: 24, bottom: 8, left: 24 }}
          >
            <CartesianGrid horizontal={false} stroke="#B8C6BE" />
            <XAxis
              axisLine={{ stroke: "#64748B" }}
              tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }}
              tickFormatter={(value) => formatNumber(Number(value || 0), 0)}
              tickLine={false}
              type="number"
            />
            <YAxis
              axisLine={{ stroke: "#64748B" }}
              dataKey="unidad"
              tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }}
              tickLine={false}
              type="category"
              width={180}
            />
            <Tooltip
              contentStyle={unitChartTooltipStyle}
              formatter={(value, name) => {
                const label =
                  name === "balance_ambiental"
                    ? "Balance ambiental por etapa"
                    : "Emisiones por etapa";

                return [
                  `${formatNumber(Number(value || 0), 1)} kg CO2e`,
                  label,
                ];
              }}
              labelStyle={{ color: "#1F2937", fontWeight: 700 }}
            />
            <Bar
              barSize={16}
              dataKey="emisiones"
              fill="#22D3EE"
              name="Emisiones por etapa"
              radius={[0, 8, 8, 0]}
            />
            <Bar
              barSize={16}
              dataKey="balance_ambiental"
              fill="#34D399"
              name="Balance ambiental por etapa"
              radius={[0, 8, 8, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartPanel>
  );
}

function EnvironmentalBalanceWaterfall({ emissions, storedCarbon }) {
  const totalEmissions = Number(emissions || 0);
  const totalStoredCarbon = Number(storedCarbon || 0);
  const balance = totalStoredCarbon - totalEmissions;
  const maxValue = Math.max(totalEmissions, totalStoredCarbon, Math.abs(balance), 1);
  const rows = [
    {
      color: "bg-[var(--primary)]",
      label: "Balance ambiental",
      tone: "text-[var(--primary-dark)]",
      value: totalStoredCarbon,
    },
    {
      color: "bg-[#0EA5C6]",
      label: "Emisiones generadas",
      tone: "text-[#075985]",
      value: -totalEmissions,
    },
    {
      color: balance >= 0 ? "bg-[var(--primary)]" : "bg-[#D92D20]",
      label: "Balance ambiental neto",
      tone: balance >= 0 ? "text-[var(--primary-dark)]" : "text-[#B42318]",
      value: balance,
    },
  ];

  return (
    <ChartPanel
      description="Resume el resultado ambiental entre balance calculado y emisiones acumuladas."
      title="Balance ambiental"
    >
      <div className="grid gap-4">
        {rows.map((row) => {
          const width = `${Math.max(6, (Math.abs(row.value) / maxValue) * 100)}%`;

          return (
            <div key={row.label} className="premium-card-interactive rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)]">
              <div className="mb-3 flex items-center justify-between gap-4">
                <p className="text-sm font-bold text-[var(--text-muted)]">{row.label}</p>
                <p className={`text-lg font-bold ${row.tone}`}>
                  {row.value >= 0 ? "+" : "-"}
                  {formatNumber(Math.abs(row.value), 1)} kg CO2e
                </p>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-[#DDE6E0]">
                <div className={`h-full rounded-full ${row.color}`} style={{ width }} />
              </div>
            </div>
          );
        })}
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
      row.emisiones += Number(fuente_emision.emisiones_kg_co2e || 0);
    });

    (unidad.obras_resumen || []).forEach((obra) => {
      const monthKey = getMonthKey(obra.fecha);

      if (!monthKey) {
        return;
      }

      const row = ensureMonth(months, monthKey);
      row.balance_ambiental += Math.max(
        Number(obra.emisiones_kg_co2e || 0) - Number(obra.balance_neto_kg_co2e || 0),
        0
      );
    });
  });

  return Array.from(months.values())
    .sort((left, right) => left.mes.localeCompare(right.mes))
    .map((row) => ({
      ...row,
      balance_neto: row.balance_ambiental - row.emisiones,
      mes_label: formatMonth(row.mes),
    }));
}

function ensureMonth(months, monthKey) {
  if (!months.has(monthKey)) {
    months.set(monthKey, {
      mes: monthKey,
      emisiones: 0,
      balance_ambiental: 0,
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
  balance_neto: "Balance neto",
  balance_ambiental: "Balance ambiental",
  emisiones: "Emisiones",
};

function getUnitStoredCarbon(unidad) {
  const directValue = Number(unidad.balance_ambiental_kg || 0);

  if (directValue) {
    return directValue;
  }

  return (unidad.obras_resumen || []).reduce((acc, obra) => {
    const explicitCarbon = Number(obra.balance_ambiental_kg || 0);

    if (explicitCarbon) {
      return acc + explicitCarbon;
    }

    return (
      acc +
      Math.max(
        Number(obra.emisiones_kg_co2e || 0) - Number(obra.balance_neto_kg_co2e || 0),
        0
      )
    );
  }, 0);
}

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

function InsightCard({ icon, label, value }) {
  return (
    <div className="premium-card-interactive rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)]">
      <div className="mb-3 flex items-center gap-3">
        <div className="text-[var(--primary-dark)]">{icon}</div>
        <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
          {label}
        </p>
      </div>
      <p className="mt-2 line-clamp-2 text-lg font-bold text-[var(--text-main)]">{value}</p>
    </div>
  );
}

const fieldLabels = {
  rut: "RUT",
  nombre: "nombre",
  region: "region",
  comuna: "comuna",
  rubro: "rubro",
  email: "email",
};

export default ConstructorasView;
