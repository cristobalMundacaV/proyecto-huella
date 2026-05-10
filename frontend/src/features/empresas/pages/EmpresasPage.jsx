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

      <section className="rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-4 sm:p-6">
        <p className="text-sm font-semibold text-cyan-200">Resumen estrategico</p>
        <h2 className="mt-2 text-2xl font-bold text-slate-100">
          Lectura operativa de la empresa
        </h2>
        <p className="mt-3 max-w-5xl whitespace-pre-line text-sm leading-7 text-cyan-50">
          {loadingUnidades ? "Cargando unidades operativas..." : buildStrategicSummary(metrics)}
        </p>
      </section>

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
      <div className="mb-3 text-cyan-300">{icon}</div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
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
      <div className="mb-3 text-emerald-300">{icon}</div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
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
