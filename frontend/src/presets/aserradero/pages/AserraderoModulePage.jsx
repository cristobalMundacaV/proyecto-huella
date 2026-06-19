import { useCallback, useEffect, useMemo, useState } from "react";
import { FilePlus2, X } from "lucide-react";

import PresetComingSoon from "@/shared/components/PresetComingSoon";
import {
  createEmpresaRegistroAmbiental,
  getEmpresaRegistrosAmbientales,
} from "@/shared/services/api";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";

import AserraderoModuleShell from "../components/AserraderoModuleShell";
import AserraderoOperationalKpis from "../components/AserraderoOperationalKpis";
import AserraderoQuickForm from "../components/AserraderoQuickForm";
import AserraderoRecentRecords from "../components/AserraderoRecentRecords";
import {
  ASERRADERO_PRESET_KEY,
  getAserraderoModuleConfig,
  getBackendCategoryForAserradero,
} from "../operationalConfig";

function normalizeRows(input) {
  if (Array.isArray(input)) return input;
  return input?.results || input?.data || input?.registros || input?.registros_emision || [];
}

function compactObject(input) {
  return Object.fromEntries(
    Object.entries(input || {}).filter(([, value]) => value !== undefined && value !== null && value !== "")
  );
}

function AserraderoModulePage({ moduleKey }) {
  const config = getAserraderoModuleConfig(moduleKey);
  const { activeConstructora, activeConstructoraId } = useConstructoraActiva();
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isQuickFormOpen, setIsQuickFormOpen] = useState(false);

  const loadRecords = useCallback(async () => {
    if (!activeConstructoraId) {
      setRecords([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const data = await getEmpresaRegistrosAmbientales(activeConstructoraId);
      setRecords(normalizeRows(data));
    } catch (requestError) {
      setError(requestError.response?.data?.error || "No se pudieron cargar los registros operativos.");
    } finally {
      setLoading(false);
    }
  }, [activeConstructoraId]);

  useEffect(() => {
    loadRecords();
  }, [loadRecords]);

  const moduleRecords = useMemo(
    () =>
      records.filter(
        (record) =>
          record?.metadata?.preset === ASERRADERO_PRESET_KEY && record?.metadata?.module === moduleKey
      ),
    [moduleKey, records]
  );

  const handleSubmit = async (form) => {
    if (!activeConstructoraId || !config) return;

    setSaving(true);
    setError("");
    setMessage("");

    const factor = Number(form.factor_emision || 0);
    const metadata = compactObject(form.metadata);
    const payload = {
      categoria: getBackendCategoryForAserradero(config.category),
      fuente_emision: config.defaultSource,
      cantidad: Number(form.cantidad || 0),
      unidad: form.unidad || config.defaultUnit,
      factor_emision: factor,
      fecha: form.fecha || null,
      proveedor: form.proveedor || "",
      observaciones: form.observaciones || "",
      origen_transporte: metadata.origen || "",
      destino_transporte: metadata.destino || "",
      distancia_km: metadata.distancia_km || null,
      metadata: {
        preset: ASERRADERO_PRESET_KEY,
        module: moduleKey,
        operation_type: "forestal_aserradero",
        aserradero_category: config.category,
        backend_category: getBackendCategoryForAserradero(config.category),
        ...metadata,
      },
    };

    try {
      await createEmpresaRegistroAmbiental(activeConstructoraId, payload);
      setMessage(
        factor > 0
          ? "Registro ambiental calculado correctamente."
          : "Registro operativo creado. Falta asociar factor de emisión para cerrar cálculo ambiental."
      );
      await loadRecords();
      setIsQuickFormOpen(false);
    } catch (requestError) {
      const data = requestError.response?.data;
      const firstError =
        typeof data === "string"
          ? data
          : data?.error || data?.detail || Object.values(data || {})?.flat?.()?.[0];
      setError(firstError || "No se pudo registrar la operación.");
    } finally {
      setSaving(false);
    }
  };

  if (!config) {
    return (
      <PresetComingSoon
        title="Módulo no configurado"
        description="Este módulo todavía no tiene configuración operativa para el preset aserradero."
        presetName="Aserradero / Forestal"
      />
    );
  }

  if (!activeConstructora) {
    return (
      <PresetComingSoon
        title={config.title}
        description="Selecciona una empresa activa para registrar operaciones del preset aserradero."
        presetName="Aserradero / Forestal"
        items={["Empresa activa", "Registros operativos", "KPIs del módulo"]}
      />
    );
  }

  return (
    <AserraderoModuleShell config={config} error={error} loading={loading} message={message}>
      <AserraderoOperationalKpis moduleKey={moduleKey} records={moduleRecords} />

      <section className="flex flex-col gap-4 rounded-3xl border border-emerald-200 bg-emerald-50/70 p-5 shadow-[var(--shadow-card)] lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-800">Acción operacional</p>
          <h2 className="mt-1 text-xl font-black text-[var(--text-main)]">Registrar {config.title.toLowerCase()}</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-700">
            El formulario se abre como modal para mantener el proceso enfocado en indicadores, historial y trazabilidad ambiental.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setIsQuickFormOpen(true)}
          disabled={!activeConstructoraId}
          className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white shadow-[0_14px_30px_rgba(15,124,109,0.18)] hover:bg-[var(--primary-dark)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <FilePlus2 size={18} />
          Nuevo registro
        </button>
      </section>

      <AserraderoRecentRecords records={moduleRecords} />

      {isQuickFormOpen ? (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-950/35 px-4 py-6 backdrop-blur-sm">
          <div className="relative max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-[32px] border border-emerald-100 bg-white p-4 shadow-[0_30px_90px_rgba(15,23,42,0.22)] sm:p-6">
            <button
              type="button"
              onClick={() => setIsQuickFormOpen(false)}
              className="absolute right-4 top-4 z-10 rounded-2xl border border-slate-200 bg-white p-2 text-slate-600 shadow-sm hover:bg-slate-50"
              aria-label="Cerrar modal"
            >
              <X size={18} />
            </button>
            <AserraderoQuickForm config={config} disabled={!activeConstructoraId} onSubmit={handleSubmit} saving={saving} />
          </div>
        </div>
      ) : null}
    </AserraderoModuleShell>
  );
}

export default AserraderoModulePage;
