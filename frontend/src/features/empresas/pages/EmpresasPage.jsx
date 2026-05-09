import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  Boxes,
  Building2,
  Eye,
  Factory,
  FileCheck2,
  Gauge,
  Leaf,
  Loader2,
  Plus,
  Search,
  ShieldCheck,
  Target,
  Trash2,
} from "lucide-react";

import EmpresaForm from "../components/EmpresaForm";
import ConfirmationModal from "@/shared/components/ConfirmationModal";
import EmptyState from "@/shared/components/EmptyState";
import Pagination from "@/shared/components/Pagination";
import Tabs from "@/shared/components/Tabs";
import Toast from "@/shared/components/Toast";
import {
  createEmpresa,
  deleteEmpresa,
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

const rowsPerPage = 8;

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
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [createModalOpen, setCreateModalOpen] = useState(initialOpenCreate);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [fieldErrors, setFieldErrors] = useState({});
  const [selectedEmpresaId, setSelectedEmpresaId] = useState("");
  const [activeDetailTab, setActiveDetailTab] = useState("resumen");
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [unidadesOperativas, setUnidadesOperativas] = useState([]);
  const [loadingUnidades, setLoadingUnidades] = useState(false);
  const {
    activeEmpresa,
    activeEmpresaId,
    clearActiveEmpresa,
    refreshEmpresas,
    setActiveEmpresa,
  } = useEmpresaActiva();
  const { clearToast, showToast, toast } = useToast();

  const metrics = useMemo(
    () => buildCompanyMetrics(empresas, unidadesOperativas, activeEmpresaId, activeEmpresa),
    [activeEmpresa, activeEmpresaId, empresas, unidadesOperativas]
  );
  const selectedEmpresa = useMemo(
    () => empresas.find((empresa) => String(empresa.id) === String(selectedEmpresaId)),
    [empresas, selectedEmpresaId]
  );
  const filteredEmpresas = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return empresas;
    }

    return empresas.filter((empresa) =>
      [
        empresa.empresa_id,
        empresa.nombre,
        empresa.rut,
        empresa.region,
        empresa.comuna,
        empresa.rubro,
        empresa.email,
        empresa.telefono,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [empresas, search]);
  const totalPages = Math.max(1, Math.ceil(filteredEmpresas.length / rowsPerPage));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * rowsPerPage;
  const visibleEmpresas = filteredEmpresas.slice(startIndex, startIndex + rowsPerPage);

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
      setSelectedEmpresaId(String(createdEmpresa.id));
      setActiveDetailTab("resumen");
      setForm(emptyForm);
      setCreateModalOpen(false);
      setCurrentPage(1);
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

  const handleDeleteEmpresa = async () => {
    if (!deleteTarget) {
      return;
    }

    setDeleting(true);
    setError("");

    try {
      await deleteEmpresa(deleteTarget.empresa_id);
      setEmpresas((currentEmpresas) =>
        currentEmpresas.filter((empresa) => empresa.id !== deleteTarget.id)
      );
      if (String(selectedEmpresaId) === String(deleteTarget.id)) {
        setSelectedEmpresaId("");
      }
      if (String(activeEmpresaId) === String(deleteTarget.empresa_id)) {
        clearActiveEmpresa();
      }
      await refreshEmpresas();
      showToast("Empresa eliminada.");
      setDeleteTarget(null);
    } catch (requestError) {
      setError(
        requestError.response?.data?.error ||
          "No se pudo eliminar la empresa seleccionada."
      );
    } finally {
      setDeleting(false);
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
          Lectura operativa de la empresa activa
        </h2>
        <p className="mt-3 max-w-5xl text-sm leading-7 text-cyan-50">
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

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
        <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Tabla de empresas</h2>
            <p className="mt-1 text-sm text-slate-400">
              {formatNumber(filteredEmpresas.length, 0)} empresas encontradas.
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
            onChange={(event) => {
              setSearch(event.target.value);
              setCurrentPage(1);
            }}
            placeholder="Buscar empresa, RUT, region, comuna, rubro o email"
            className="w-full rounded-2xl border border-slate-700 bg-slate-950 py-3 pl-11 pr-4 text-sm text-slate-100 outline-none transition focus:border-emerald-400/60"
          />
        </label>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1380px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs text-slate-400">
                <th className="px-4 py-3">RUT</th>
                <th className="px-4 py-3">Empresa</th>
                <th className="px-4 py-3">Region</th>
                <th className="px-4 py-3">Rubro</th>
                <th className="px-4 py-3 text-right">Unidades</th>
                <th className="px-4 py-3 text-right">Lotes</th>
                <th className="px-4 py-3 text-right">Actividades</th>
                <th className="px-4 py-3 text-right">Emisiones</th>
                <th className="px-4 py-3 text-right">Carbono almacenado</th>
                <th className="px-4 py-3 text-right">Balance</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3 text-center">Detalle</th>
              </tr>
            </thead>
            <tbody>
              {visibleEmpresas.map((empresa) => {
                const isActiveEmpresa =
                  metrics.activeCompany && metrics.activeCompany.id === empresa.id;

                return (
                  <tr
                    key={empresa.id}
                    className={`group border-b border-slate-800/80 transition ${
                      String(selectedEmpresaId) === String(empresa.id)
                        ? "bg-emerald-400/5"
                        : isActiveEmpresa
                          ? "bg-cyan-400/5 hover:bg-cyan-400/10"
                          : "hover:bg-slate-800/40"
                    }`}
                  >
                    <td className="px-4 py-4 text-slate-300">{empresa.rut || "-"}</td>
                    <td className="px-4 py-4">
                      <p className="font-semibold text-slate-100">{empresa.nombre}</p>
                    </td>
                    <td className="px-4 py-4 text-slate-300">{empresa.region || "-"}</td>
                    <td className="px-4 py-4 text-slate-300">{empresa.rubro || "-"}</td>
                    <td className="px-4 py-4 text-right font-semibold text-slate-200">
                      {formatNumber(empresa.unidades_count || 0, 0)}
                    </td>
                    <td className="px-4 py-4 text-right font-semibold text-slate-200">
                      {formatNumber(empresa.lotes_count || 0, 0)}
                    </td>
                    <td className="px-4 py-4 text-right font-semibold text-slate-200">
                      {formatNumber(empresa.actividades_count || 0, 0)}
                    </td>
                    <td className="px-4 py-4 text-right font-bold text-cyan-200">
                      {formatNumber(Number(empresa.emisiones_totales_kg_co2e || 0), 1)}
                    </td>
                    <td className="px-4 py-4 text-right font-bold text-emerald-200">
                      {formatNumber(Number(empresa.co2_almacenado_kg || 0), 1)}
                    </td>
                    <td className="px-4 py-4 text-right font-semibold">
                      <span className={balanceTone(empresa.balance_neto_kg_co2e)}>
                        {formatNumber(Number(empresa.balance_neto_kg_co2e || 0), 1)}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <CompanyStatusBadge empresa={empresa} />
                    </td>
                    <td className="px-4 py-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedEmpresaId(String(empresa.id));
                            setActiveDetailTab("resumen");
                          }}
                          className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 text-cyan-200 transition hover:bg-cyan-400/20"
                          aria-label={`Ver detalle de ${empresa.nombre}`}
                        >
                          <Eye size={18} />
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeleteTarget(empresa)}
                          className="inline-flex h-10 w-10 translate-x-3 items-center justify-center rounded-2xl border border-red-400/20 bg-red-400/10 text-red-200 opacity-0 transition-all duration-300 ease-out hover:bg-red-400/20 group-hover:translate-x-0 group-hover:opacity-100 focus:translate-x-0 focus:opacity-100"
                          aria-label={`Eliminar ${empresa.nombre}`}
                        >
                          <Trash2 size={17} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!loading && visibleEmpresas.length === 0 && (
                <tr>
                  <td className="px-1 py-8 text-center text-slate-400" colSpan={12}>
                    No hay empresas para mostrar.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination
          currentPage={safeCurrentPage}
          itemLabel="empresas"
          onPageChange={setCurrentPage}
          pageSize={rowsPerPage}
          totalItems={filteredEmpresas.length}
        />
      </section>

      <EmpresaDetailPanel
        activeTab={activeDetailTab}
        empresa={selectedEmpresa}
        metrics={metrics}
        onTabChange={setActiveDetailTab}
      />

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

      {deleteTarget && (
        <ConfirmationModal
          title="Eliminar empresa"
          description={`Esta accion eliminara "${deleteTarget.nombre}" junto a sus unidades, lotes y emisiones asociadas. No se puede deshacer.`}
          confirmLabel="Eliminar empresa"
          loading={deleting}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={handleDeleteEmpresa}
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
      ? "alta concentracion"
      : metrics.topEmissionShare >= 35
        ? "concentracion moderada"
        : "distribucion relativamente balanceada";
  const balanceText =
    metrics.globalBalance < 0
      ? "El balance global es favorable gracias al carbono almacenado registrado."
      : "El balance global sigue siendo intensivo en emisiones y requiere priorizar acciones de reduccion.";
  const traceabilityText = metrics.topTraceability
    ? `${metrics.topTraceability.nombre} destaca por su nivel de trazabilidad disponible.`
    : "Aun no hay una unidad claramente destacada en trazabilidad.";

  return `${metrics.activeCompany.nombre} registra ${formatNumber(
    metrics.totalUnits,
    0
  )} unidades operativas activas. ${metrics.topOperational?.nombre || "Sin datos"} concentra la mayor carga operativa y ${metrics.topEmitter?.nombre || "Sin datos"} concentra la mayor huella de carbono, con ${formatNumber(
    metrics.topEmissionShare,
    1
  )}% de las emisiones de la empresa. La estructura actual refleja ${concentration} del peso operativo entre unidades. ${traceabilityText} ${balanceText}`;
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

function CompanyStatusBadge({ empresa }) {
  const balance = Number(empresa.balance_neto_kg_co2e || 0);
  const emissions = Number(empresa.emisiones_totales_kg_co2e || 0);

  if (balance < 0) {
    return (
      <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-bold text-emerald-200">
        Favorable
      </span>
    );
  }

  if (!emissions) {
    return (
      <span className="rounded-full border border-slate-500/30 bg-slate-400/10 px-3 py-1 text-xs font-bold text-slate-200">
        Sin emisiones
      </span>
    );
  }

  return (
    <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-1 text-xs font-bold text-amber-200">
      Intensiva
    </span>
  );
}

function EmpresaDetailPanel({ activeTab, empresa, metrics, onTabChange }) {
  if (!empresa) {
    return (
      <EmptyState
        title="Selecciona una empresa"
        description="Selecciona una empresa para revisar su resumen, unidades, lotes, emisiones, pasaportes y evidencias."
      />
    );
  }

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-emerald-300">Detalle empresa</p>
          <h2 className="mt-1 text-2xl font-bold text-slate-100">{empresa.nombre}</h2>
          <p className="mt-2 text-sm text-slate-400">
            {empresa.rut || "Sin RUT"} · {empresa.rubro || "Sin rubro"} ·{" "}
            {empresa.region || "Sin region"} · {empresa.comuna || "Sin comuna"}
          </p>
          <p className="mt-1 text-sm text-slate-500">
            {empresa.email || empresa.telefono || empresa.contacto || "Sin contacto registrado"}
          </p>
          {empresa.observaciones && (
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
              {empresa.observaciones}
            </p>
          )}
        </div>
        <div className="space-y-2 text-left lg:text-right">
          <CompanyStatusBadge empresa={empresa} />
          <p className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm font-bold text-cyan-200">
            Balance {formatNumber(Number(empresa.balance_neto_kg_co2e || 0), 1)} kg CO2e
          </p>
        </div>
      </div>

      <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <DetailMetric label="Unidades" value={Number(empresa.unidades_count || 0)} />
        <DetailMetric label="Lotes" value={Number(empresa.lotes_count || 0)} />
        <DetailMetric label="Actividades" value={Number(empresa.actividades_count || 0)} />
        <DetailMetric
          label="Emisiones"
          tone="cyan"
          value={`${formatNumber(Number(empresa.emisiones_totales_kg_co2e || 0), 1)} kg CO2e`}
        />
        <DetailMetric
          label="Carbono almacenado"
          tone="emerald"
          value={`${formatNumber(Number(empresa.co2_almacenado_kg || 0), 1)} kg`}
        />
        <DetailMetric
          label="Balance"
          value={`${formatNumber(Number(empresa.balance_neto_kg_co2e || 0), 1)} kg CO2e`}
        />
        <DetailMetric label="Pasaportes" value={Number(empresa.pasaportes_emitidos || 0)} />
        <DetailMetric label="Evidencias" value={Number(empresa.evidencias_count || 0)} />
      </div>

      <Tabs
        activeTab={activeTab}
        onChange={onTabChange}
        tabs={[
          { label: "Resumen", value: "resumen" },
          { label: "Unidades", value: "unidades" },
          { label: "Lotes", value: "lotes" },
          { label: "Emisiones", value: "emisiones" },
          { label: "Pasaportes", value: "pasaportes" },
          { label: "Evidencias", value: "evidencias" },
          { label: "Historial", value: "historial" },
        ]}
      />

      <div className="mt-5">
        {activeTab === "resumen" && (
          <EmpresaResumen empresa={empresa} metrics={metrics} />
        )}
        {activeTab === "unidades" && (
          <SimpleTable
            columns={["Unidad", "Tipo", "Region", "Comuna", "Lotes", "Actividades", "Emisiones"]}
            rows={(empresa.unidades_resumen || []).map((unidad) => [
              unidad.nombre,
              unidad.tipo || "-",
              unidad.region || "-",
              unidad.comuna || "-",
              formatNumber(unidad.lotes_count || 0, 0),
              formatNumber(unidad.actividades_count || 0, 0),
              `${formatNumber(Number(unidad.emisiones_totales_kg_co2e || 0), 1)} kg CO2e`,
            ])}
          />
        )}
        {activeTab === "lotes" && (
          <SimpleTable
            columns={["Lote", "Unidad", "Especie", "Emisiones", "Carbono almacenado", "Balance"]}
            rows={(empresa.lotes_resumen || []).map((lote) => [
              lote.id_lote,
              lote.unidad || "-",
              lote.especie || "-",
              `${formatNumber(Number(lote.emisiones_kg_co2e || 0), 1)} kg CO2e`,
              `${formatNumber(Number(lote.co2_almacenado_kg || 0), 1)} kg`,
              `${formatNumber(Number(lote.balance_neto_kg_co2e || 0), 1)} kg CO2e`,
            ])}
          />
        )}
        {activeTab === "emisiones" && (
          <SimpleTable
            columns={["Actividad", "Categoria", "Asignacion", "Lote/Unidad", "Emisiones"]}
            rows={(empresa.actividades_resumen || []).map((actividad) => [
              actividad.actividad,
              actividad.categoria || "-",
              actividad.tipo_asignacion || "-",
              actividad.lote || actividad.unidad_operativa || "Empresa",
              `${formatNumber(Number(actividad.emisiones_kg_co2e || 0), 1)} kg CO2e`,
            ])}
          />
        )}
        {activeTab === "pasaportes" && (
          <SimpleTable
            columns={["Lote", "Estado", "Balance", "Evidencias"]}
            rows={(empresa.lotes_resumen || []).map((lote) => [
              lote.id_lote,
              lote.estado_pasaporte || "Sin pasaporte",
              `${formatNumber(Number(lote.balance_neto_kg_co2e || 0), 1)} kg CO2e`,
              formatNumber(lote.evidencias_count || 0, 0),
            ])}
          />
        )}
        {activeTab === "evidencias" && (
          <SimpleTable
            columns={["Lote", "Documento", "Estado", "Fecha"]}
            rows={(empresa.evidencias_resumen || []).map((evidencia) => [
              evidencia.lote,
              evidencia.tipo_documento,
              evidencia.estado_validacion,
              evidencia.fecha || "-",
            ])}
          />
        )}
        {activeTab === "historial" && (
          <EmptyState
            title="Historial no disponible"
            description="La estructura visual queda preparada para incorporar eventos historicos de empresa."
          />
        )}
      </div>
    </section>
  );
}

function EmpresaResumen({ empresa, metrics }) {
  const emissionShare =
    metrics.totalEmissions > 0
      ? (Number(empresa.emisiones_totales_kg_co2e || 0) / metrics.totalEmissions) * 100
      : 0;
  const dominantUnit =
    [...(empresa.unidades_resumen || [])].sort(
      (left, right) =>
        Number(right.actividades_count || 0) - Number(left.actividades_count || 0)
    )[0] || null;

  return (
    <div className="space-y-4">
      <div className="rounded-3xl border border-emerald-400/20 bg-emerald-400/10 p-5">
        <p className="text-sm font-semibold text-emerald-200">Insight corporativo</p>
        <p className="mt-2 text-sm leading-7 text-emerald-50">
          {empresa.nombre} representa el {formatNumber(emissionShare, 1)}% de las emisiones
          agregadas del sistema. {dominantUnit?.nombre || "Sin unidad dominante"} es el
          frente operativo con mayor actividad registrada. La empresa cuenta con{" "}
          {formatNumber(empresa.pasaportes_emitidos || 0, 0)} pasaportes y{" "}
          {formatNumber(empresa.evidencias_count || 0, 0)} evidencias asociadas para
          trazabilidad.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <DetailMetric label="Frente dominante" value={dominantUnit?.nombre || "Sin datos"} />
        <DetailMetric label="Unidades" value={Number(empresa.unidades_count || 0)} />
        <DetailMetric label="Lotes" value={Number(empresa.lotes_count || 0)} />
        <DetailMetric
          label="Peso en emisiones"
          tone="cyan"
          value={`${formatNumber(emissionShare, 1)}%`}
        />
      </div>
    </div>
  );
}

function DetailMetric({ detail, label, tone = "slate", value }) {
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
      <p className={`mt-2 line-clamp-2 text-2xl font-bold ${toneClass}`}>{value}</p>
      {detail && <p className="mt-1 text-sm text-slate-400">{detail}</p>}
    </div>
  );
}

function SimpleTable({ columns, rows }) {
  if (!rows.length) {
    return (
      <EmptyState
        title="Sin datos"
        description="Esta empresa aun no tiene registros para esta seccion."
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[860px] border-collapse text-sm">
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
          {rows.map((row, rowIndex) => (
            <tr key={`${row[0]}-${rowIndex}`} className="border-b border-slate-800/70">
              {row.map((cell, cellIndex) => (
                <td
                  key={`${row[0]}-${cellIndex}`}
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
  );
}

function balanceTone(value) {
  const balance = Number(value || 0);

  if (balance < 0) {
    return "text-emerald-300";
  }

  if (balance <= 500) {
    return "text-amber-300";
  }

  return "text-red-300";
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
