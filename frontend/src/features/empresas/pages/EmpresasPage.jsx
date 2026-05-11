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

import EmpresaForm from "../components/EmpresaForm";
import Toast from "@/shared/components/Toast";
import {
  createEmpresa,
  getEmpresaUnidades,
  getEmpresas,
} from "@/shared/services/api";
import { useToast } from "@/shared/hooks/useToast";
import { formatNumber } from "@/shared/utils/formatters";
import {
  isValidChileanRut,
  isValidEmail,
  isValidPhone,
} from "@/shared/utils/validators";
import { useEmpresaActiva } from "@/features/empresas/context/EmpresaActivaContext";
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
  backgroundColor: "#0F172A",
  border: "1px solid #1E293B",
  borderRadius: "12px",
  color: "#F8FAFC",
};

const monthFormatter = new Intl.DateTimeFormat("es-CL", {
  month: "short",
  year: "2-digit",
});

function EmpresasView({
  onSetActiveView,
  initialOpenCreate = false,
  openCreateSignal = 0,
}) {
  const [empresas, setEmpresas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createModalOpen, setCreateModalOpen] = useState(initialOpenCreate);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [fieldErrors, setFieldErrors] = useState({});
  const [unidadesOperativas, setUnidadesOperativas] = useState([]);
  const [loadingUnidades, setLoadingUnidades] = useState(false);
  const {
    activeEmpresa,
    activeEmpresaId,
    refreshEmpresas,
    setActiveEmpresa,
  } = useEmpresaActiva();
  const { clearToast, showToast, toast } = useToast();

  const metrics = useMemo(
    () => buildCompanyMetrics(empresas, unidadesOperativas, activeEmpresaId, activeEmpresa),
    [activeEmpresa, activeEmpresaId, empresas, unidadesOperativas]
  );

  useEffect(() => {
    let isCancelled = false;

    async function loadEmpresas() {
      try {
        const data = await getEmpresas();

        if (!isCancelled) {
          setEmpresas(Array.isArray(data) ? data : []);
        }
      } catch (requestError) {
        if (!isCancelled) {
          setError(
            requestError.response?.data?.error ||
              "No se pudieron cargar las empresas."
          );
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    loadEmpresas();

    return () => {
      isCancelled = true;
    };
  }, []);

  useEffect(() => {
    let isCancelled = false;

    async function loadUnidades() {
      if (!activeEmpresaId) {
        setUnidadesOperativas([]);
        return;
      }

      setLoadingUnidades(true);

      try {
        const data = await getEmpresaUnidades(activeEmpresaId, { detail: "1" });

        if (!isCancelled) {
          setUnidadesOperativas(Array.isArray(data) ? data : []);
        }
      } catch {
        if (!isCancelled) {
          setUnidadesOperativas([]);
        }
      } finally {
        if (!isCancelled) {
          setLoadingUnidades(false);
        }
      }
    }

    loadUnidades();

    return () => {
      isCancelled = true;
    };
  }, [activeEmpresaId]);

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

  const handleCreateEmpresa = async (event) => {
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
      const createdEmpresa = await createEmpresa(form);
      setEmpresas((currentEmpresas) => [createdEmpresa, ...currentEmpresas]);
      setActiveEmpresa(createdEmpresa);
      await refreshEmpresas();
      setForm(emptyForm);
      setCreateModalOpen(false);
      onSetActiveView?.("dashboard");
    } catch (requestError) {
      const responseData = requestError.response?.data;

      if (responseData && typeof responseData === "object") {
        setFieldErrors(responseData);
      }

      setError("Revisa los datos de la empresa antes de guardarla.");
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
          <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-3">
            <Building2 className="text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold sm:text-4xl">Empresas</h1>
            <p className="max-w-3xl text-slate-400">
              Gestiona las empresas, unidades, lotes y actividades desde un mismo
              lugar, con trazabilidad lista para análisis, reportes y decisiones ambientales.
            </p>
          </div>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200">
            {formatNumber(empresas.length, 0)} empresas
          </div>
          <button
            type="button"
            onClick={() => {
              setError("");
              setFieldErrors({});
              setCreateModalOpen(true);
            }}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200 transition hover:bg-emerald-400/20"
          >
            <Plus size={18} />
            Nueva empresa
          </button>
        </div>
      </header>


      <section className="rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-4 sm:p-6">
        <p className="text-sm font-semibold text-cyan-200">Resumen estrategico</p>
        <h2 className="mt-2 text-2xl font-bold text-slate-100">
          Lectura operativa de la empresa
        </h2>
        <p className="mt-3 max-w-5xl whitespace-pre-line text-sm leading-7 text-cyan-50">
          {loadingUnidades ? "Cargando unidades operativas..." : buildStrategicSummary(metrics)}
        </p>
      </section>

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <CompanyKpi
          icon={<Building2 />}
          label="Empresa seleccionada"
          value={metrics.activeCompany?.nombre || "Sin datos"}
        />
        <CompanyKpi
          icon={<Factory />}
          label="Unidades activas"
          value={metrics.totalUnits}
        />
        <CompanyKpi icon={<Boxes />} label="Lotes registrados" value={metrics.totalLotes} />
        <CompanyKpi
          icon={<Activity />}
          label="Actividades registradas"
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
          label="Carbono almacenado"
          tone="emerald"
          value={`${formatNumber(metrics.totalStoredCarbon, 1)} kg`}
        />
        <CompanyKpi
          detail={`${formatNumber(
            metrics.topEmitter?.emisiones_totales_kg_co2e || 0,
            1
          )} kg CO2e`}
          icon={<BarChart3 />}
          label="Unidad con mayor emisión"
          value={metrics.topEmitter?.nombre || "Sin datos"}
        />
        <CompanyKpi
          detail={`${formatNumber(
            Math.abs(Number(metrics.bestBalance?.balance_neto_kg_co2e || 0)),
            1
          )} kg CO2e`}
          icon={<ShieldCheck />}
          label="Unidad con mejor balance"
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
          label="Unidad lider en emisiones"
          value={metrics.topEmitter?.nombre || "Sin datos"}
        />
        <InsightCard
          icon={<Factory />}
          label="Unidad con mayor actividad"
          value={metrics.topOperational?.nombre || "Sin datos"}
        />
        <InsightCard
          icon={<Leaf />}
          label="Unidad con mayor carbono almacenado"
          value={metrics.topStorage?.nombre || "Sin datos"}
        />
        <InsightCard
          icon={<FileCheck2 />}
          label="Unidad con mayor trazabilidad"
          value={metrics.topTraceability?.nombre || "Sin datos"}
        />
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <UnitMetricBarChart
          color="#22D3EE"
          dataKey="emisiones"
          description="Permite identificar rapidamente donde se concentra el mayor problema ambiental."
          rows={metrics.unitComparisonRows}
          title="Emisiones por unidad operativa"
          valueLabel="Emisiones"
        />

        <UnitMetricBarChart
          color="#34D399"
          dataKey="carbono_almacenado"
          description="Muestra que unidades aportan mas al balance ambiental positivo."
          rows={metrics.unitComparisonRows}
          title="Carbono almacenado por unidad operativa"
          valueLabel="Carbono almacenado"
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
        <EmpresaForm
          error={error}
          fieldErrors={fieldErrors}
          form={form}
          loading={saving}
          onClose={() => {
            setCreateModalOpen(false);
            setError("");
          }}
          onSubmit={handleCreateEmpresa}
          onUpdateForm={updateForm}
          onClearError={() => setError("")}
        />
      )}
    </div>
  );
}

function buildCompanyMetrics(empresas, unidades = [], activeEmpresaId = "", activeEmpresa = null) {
  const activeCompany =
    empresas.find((empresa) => String(empresa.empresa_id) === String(activeEmpresaId)) ||
    empresas.find((empresa) => String(empresa.id) === String(activeEmpresaId)) ||
    activeEmpresa ||
    empresas[0] ||
    null;
  const scopedUnits = unidades.filter((unidad) => {
    if (!activeCompany) {
      return true;
    }

    return (
      String(unidad.empresa_id || "") === String(activeCompany.empresa_id || "") ||
      String(unidad.empresa || "") === String(activeCompany.id || "")
    );
  });
  const totals = {
    totalCompanies: empresas.length,
    totalUnits: scopedUnits.length || Number(activeCompany?.unidades_count || 0),
    totalLotes: scopedUnits.length
      ? scopedUnits.reduce((acc, unidad) => acc + Number(unidad.lotes_count || 0), 0)
      : Number(activeCompany?.lotes_count || 0),
    totalActivities: scopedUnits.length
      ? scopedUnits.reduce((acc, unidad) => acc + Number(unidad.actividades_count || 0), 0)
      : Number(activeCompany?.actividades_count || 0),
    totalEmissions: scopedUnits.length
      ? scopedUnits.reduce(
          (acc, unidad) => acc + Number(unidad.emisiones_totales_kg_co2e || 0),
          0
        )
      : Number(activeCompany?.emisiones_totales_kg_co2e || 0),
    totalStoredCarbon: scopedUnits.length
      ? scopedUnits.reduce((acc, unidad) => acc + getUnitStoredCarbon(unidad), 0)
      : Number(activeCompany?.co2_almacenado_kg || 0),
    totalPassports: scopedUnits.length
      ? scopedUnits.reduce((acc, unidad) => acc + Number(unidad.pasaportes_count || 0), 0)
      : Number(activeCompany?.pasaportes_emitidos || 0),
    totalEvidence: scopedUnits.length
      ? scopedUnits.reduce((acc, unidad) => acc + Number(unidad.evidencias_count || 0), 0)
      : Number(activeCompany?.evidencias_count || 0),
  };

  const topEmitter = maxBy(scopedUnits, (unidad) =>
    Number(unidad.emisiones_totales_kg_co2e || 0)
  );
  const topOperational = maxBy(scopedUnits, (unidad) =>
    Number(unidad.lotes_count || 0) + Number(unidad.actividades_count || 0)
  );
  const topStorage = maxBy(scopedUnits, getUnitStoredCarbon);
  const topTraceability = maxBy(scopedUnits, (unidad) =>
    Number(unidad.pasaportes_count || 0) + Number(unidad.evidencias_count || 0)
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
        unidad: unidad.nombre || unidad.unidad_id || "Sin unidad",
        carbono_almacenado: storedCarbon,
        emisiones: emissions,
        emisiones_comparacion: emissions ? -emissions : 0,
      };
    })
    .sort(
      (left, right) =>
        Math.max(right.emisiones, right.carbono_almacenado) -
        Math.max(left.emisiones, left.carbono_almacenado)
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
    return "Aun no hay una empresa activa. Crea o selecciona una empresa para estructurar unidades, lotes, actividades y trazabilidad dentro del sistema Carbono Zero.";
  }

  if (!metrics.totalUnits) {
    return `${metrics.activeCompany.nombre} aun no tiene unidades operativas registradas. Carga unidades para analizar emisiones, trazabilidad y cobertura territorial por operacion.`;
  }

  const concentration =
    metrics.topEmissionShare >= 60
      ? "alta concentración"
      : metrics.topEmissionShare >= 35
        ? "concentración moderada"
        : "distribución relativamente balanceada";
  const balanceText =
    metrics.globalBalance < 0
      ? "En términos generales, el balance global es favorable gracias al carbono almacenado."
      : "En términos generales, el balance global sigue siendo intensivo en emisiones y requiere priorizar acciones de reducción.";
  const traceabilityText = metrics.topTraceability
    ? `Además, ${metrics.topTraceability.nombre} destaca por contar con un buen nivel de trazabilidad disponible.`
    : "Además, aún no hay una unidad claramente destacada en trazabilidad.";

  return `${metrics.activeCompany.nombre} registra ${formatNumber(
    metrics.totalUnits,
    0
  )} unidades operativas activas. ${metrics.topOperational?.nombre || "Sin datos"} concentra la mayor carga operativa, mientras que ${metrics.topEmitter?.nombre || "Sin datos"} representa la mayor huella de carbono, con un ${formatNumber(
    metrics.topEmissionShare,
    0
  )}% de las emisiones totales de la empresa.

La estructura actual muestra una ${concentration} del peso operativo entre sus unidades. ${traceabilityText}

${balanceText}`;
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
            <CartesianGrid horizontal={false} stroke="#1E293B" />
            <XAxis
              axisLine={{ stroke: "#334155" }}
              tick={{ fill: "#94A3B8", fontSize: 12 }}
              tickFormatter={(value) => formatNumber(Number(value || 0), 0)}
              tickLine={false}
              type="number"
            />
            <YAxis
              axisLine={{ stroke: "#334155" }}
              dataKey="unidad"
              tick={{ fill: "#CBD5E1", fontSize: 12 }}
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
              labelStyle={{ color: "#E2E8F0", fontWeight: 700 }}
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
    (row) => Number(row.emisiones || 0) > 0 || Number(row.carbono_almacenado || 0) > 0
  );
  const chartHeight = Math.max(320, Math.min(560, visibleRows.length * 58 + 120));

  if (!visibleRows.length) {
    return null;
  }

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
      <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <ChartHeading
          description="Contraste entre la huella generada y el carbono almacenado por cada unidad."
          title="Emisiones vs carbono almacenado"
        />
        <div className="flex flex-wrap gap-3 text-xs font-semibold">
          <span className="inline-flex items-center gap-2 text-cyan-200">
            <span className="h-2.5 w-2.5 rounded-full bg-cyan-300" />
            Emisiones
          </span>
          <span className="inline-flex items-center gap-2 text-emerald-200">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-300" />
            Carbono almacenado
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
              axisLine={{ stroke: "#334155" }}
              tick={{ fill: "#94A3B8", fontSize: 12 }}
              tickFormatter={(value) => formatNumber(Math.abs(Number(value || 0)), 0)}
              tickLine={false}
              type="number"
            />
            <YAxis
              axisLine={{ stroke: "#334155" }}
              dataKey="unidad"
              tick={{ fill: "#CBD5E1", fontSize: 12 }}
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
                    : "Carbono almacenado";

                return [
                  `${formatNumber(Math.abs(Number(value || 0)), 1)} kg CO2e`,
                  label,
                ];
              }}
              labelStyle={{ color: "#E2E8F0", fontWeight: 700 }}
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
              dataKey="carbono_almacenado"
              fill="#34D399"
              name="Carbono almacenado"
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
            <CartesianGrid stroke="#1E293B" vertical={false} />
            <XAxis
              axisLine={{ stroke: "#334155" }}
              dataKey="mes_label"
              tick={{ fill: "#94A3B8", fontSize: 12 }}
              tickLine={false}
            />
            <YAxis
              axisLine={{ stroke: "#334155" }}
              tick={{ fill: "#94A3B8", fontSize: 12 }}
              tickFormatter={(value) => formatNumber(Number(value || 0), 0)}
              tickLine={false}
            />
            <Tooltip
              contentStyle={unitChartTooltipStyle}
              formatter={(value, name) => [
                `${formatNumber(Number(value || 0), 1)} kg CO2e`,
                trendLabels[name] || name,
              ]}
              labelStyle={{ color: "#E2E8F0", fontWeight: 700 }}
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
              dataKey="carbono_almacenado"
              dot={{ r: 3 }}
              name="Carbono almacenado"
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
    .filter((row) => Number(row.emisiones || 0) > 0 || Number(row.carbono_almacenado || 0) > 0)
    .sort(
      (left, right) =>
        Number(right.emisiones || 0) - Number(left.emisiones || 0) ||
        Number(right.carbono_almacenado || 0) - Number(left.carbono_almacenado || 0)
    );
  const chartHeight = Math.max(340, Math.min(560, visibleRows.length * 62 + 120));

  if (!visibleRows.length) {
    return null;
  }

  return (
    <ChartPanel
      description="Este grafico compara las emisiones y el carbono almacenado por unidad operativa. Las unidades se ordenan por mayor emision para identificar donde actuar primero y que unidades aportan mas al balance ambiental."
      title="Emisiones y carbono almacenado por unidad"
    >
      <div className="w-full" style={{ height: chartHeight }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={visibleRows}
            layout="vertical"
            margin={{ top: 8, right: 24, bottom: 8, left: 24 }}
          >
            <CartesianGrid horizontal={false} stroke="#1E293B" />
            <XAxis
              axisLine={{ stroke: "#334155" }}
              tick={{ fill: "#94A3B8", fontSize: 12 }}
              tickFormatter={(value) => formatNumber(Number(value || 0), 0)}
              tickLine={false}
              type="number"
            />
            <YAxis
              axisLine={{ stroke: "#334155" }}
              dataKey="unidad"
              tick={{ fill: "#94A3B8", fontSize: 12 }}
              tickLine={false}
              type="category"
              width={180}
            />
            <Tooltip
              contentStyle={unitChartTooltipStyle}
              formatter={(value, name) => {
                const label =
                  name === "carbono_almacenado"
                    ? "Carbono almacenado por unidad"
                    : "Emisiones por unidad";

                return [
                  `${formatNumber(Number(value || 0), 1)} kg CO2e`,
                  label,
                ];
              }}
              labelStyle={{ color: "#E2E8F0", fontWeight: 700 }}
            />
            <Bar
              barSize={16}
              dataKey="emisiones"
              fill="#22D3EE"
              name="Emisiones por unidad"
              radius={[0, 8, 8, 0]}
            />
            <Bar
              barSize={16}
              dataKey="carbono_almacenado"
              fill="#34D399"
              name="Carbono almacenado por unidad"
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
      label: "Carbono almacenado",
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
      description="Resume el resultado ambiental entre carbono almacenado y emisiones acumuladas."
      title="Balance ambiental"
    >
      <div className="grid gap-4">
        {rows.map((row) => {
          const width = `${Math.max(6, (Math.abs(row.value) / maxValue) * 100)}%`;

          return (
            <div key={row.label} className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)]">
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
    <section className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 shadow-[var(--shadow-card)] sm:p-6">
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

function buildMonthlyRows(unidades) {
  const months = new Map();

  unidades.forEach((unidad) => {
    (unidad.actividades_resumen || []).forEach((actividad) => {
      const monthKey = getMonthKey(actividad.fecha);

      if (!monthKey) {
        return;
      }

      const row = ensureMonth(months, monthKey);
      row.emisiones += Number(actividad.emisiones_kg_co2e || 0);
    });

    (unidad.lotes_resumen || []).forEach((lote) => {
      const monthKey = getMonthKey(lote.fecha);

      if (!monthKey) {
        return;
      }

      const row = ensureMonth(months, monthKey);
      row.carbono_almacenado += Math.max(
        Number(lote.emisiones_kg_co2e || 0) - Number(lote.balance_neto_kg_co2e || 0),
        0
      );
    });
  });

  return Array.from(months.values())
    .sort((left, right) => left.mes.localeCompare(right.mes))
    .map((row) => ({
      ...row,
      balance_neto: row.carbono_almacenado - row.emisiones,
      mes_label: formatMonth(row.mes),
    }));
}

function ensureMonth(months, monthKey) {
  if (!months.has(monthKey)) {
    months.set(monthKey, {
      mes: monthKey,
      emisiones: 0,
      carbono_almacenado: 0,
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
  carbono_almacenado: "Carbono almacenado",
  emisiones: "Emisiones",
};

function getUnitStoredCarbon(unidad) {
  const directValue = Number(unidad.co2_almacenado_kg || 0);

  if (directValue) {
    return directValue;
  }

  return (unidad.lotes_resumen || []).reduce((acc, lote) => {
    const explicitCarbon = Number(lote.co2_almacenado_kg || 0);

    if (explicitCarbon) {
      return acc + explicitCarbon;
    }

    return (
      acc +
      Math.max(
        Number(lote.emisiones_kg_co2e || 0) - Number(lote.balance_neto_kg_co2e || 0),
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

function InsightCard({ icon, label, value }) {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900 p-4">
      <div className="mb-3 flex items-center gap-3">
        <div className="text-emerald-300">{icon}</div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {label}
        </p>
      </div>
      <p className="mt-2 line-clamp-2 text-lg font-bold text-slate-100">{value}</p>
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

export default EmpresasView;
