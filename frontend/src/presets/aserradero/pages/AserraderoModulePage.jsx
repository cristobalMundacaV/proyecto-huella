import { useCallback, useEffect, useMemo, useState } from "react";

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
          : "Registro operativo creado. Falta asociar factor de emision para cerrar calculo ambiental."
      );
      await loadRecords();
    } catch (requestError) {
      const data = requestError.response?.data;
      const firstError =
        typeof data === "string"
          ? data
          : data?.error || data?.detail || Object.values(data || {})?.flat?.()?.[0];
      setError(firstError || "No se pudo registrar la operacion.");
    } finally {
      setSaving(false);
    }
  };

  if (!config) {
    return (
      <PresetComingSoon
        title="Modulo no configurado"
        description="Este modulo todavia no tiene configuracion operativa para el preset aserradero."
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
        items={["Empresa activa", "Registros operativos", "KPIs del modulo"]}
      />
    );
  }

  return (
    <AserraderoModuleShell config={config} error={error} loading={loading} message={message}>
      <AserraderoOperationalKpis moduleKey={moduleKey} records={moduleRecords} />
      <div className="grid grid-cols-1 gap-6 2xl:grid-cols-[1.05fr_0.95fr]">
        <AserraderoQuickForm config={config} disabled={!activeConstructoraId} onSubmit={handleSubmit} saving={saving} />
        <AserraderoRecentRecords records={moduleRecords} />
      </div>
    </AserraderoModuleShell>
  );
}

export default AserraderoModulePage;
