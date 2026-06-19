import { useEffect, useMemo, useState } from "react";

import EmptyState from "@/shared/components/EmptyState";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import {
  crearEvidenciaConstructora,
  getEvidenciasConstructora,
  getEmpresaRegistrosAmbientales,
  getLotesForestales,
} from "@/shared/services/api";
import { DEFAULT_PRESET_KEY, getActivePreset } from "@/presets/registry";
import { construccionEvidence } from "@/presets/construccion/evidence";
import { aserraderoEvidence } from "@/presets/aserradero/evidence";
import { transporteEvidence } from "@/presets/transporte/evidence";
import { industrialEvidence } from "@/presets/industrial/evidence";
import {
  getEvidenceCoverage,
  normalizeEvidenceRows,
} from "@/presets/shared/evidenceConfig";

import EvidenceChecklist from "../components/EvidenceChecklist";
import EvidenceEmptyState from "../components/EvidenceEmptyState";
import EvidenceHero from "../components/EvidenceHero";
import EvidenceKpiGrid from "../components/EvidenceKpiGrid";
import EvidenceTable from "../components/EvidenceTable";
import EvidenceUploadPanel from "../components/EvidenceUploadPanel";
import EvidenceValidationPanel from "../components/EvidenceValidationPanel";

const evidenceByPreset = {
  construccion: construccionEvidence,
  aserradero: aserraderoEvidence,
  transporte: transporteEvidence,
  industrial: industrialEvidence,
};

function EvidenciasPage() {
  const { activeConstructoraId, activeConstructora } = useConstructoraActiva();
  const activePreset = getActivePreset(activeConstructora?.preset || DEFAULT_PRESET_KEY);
  const config = evidenceByPreset[activePreset.key] || construccionEvidence;
  const [evidencias, setEvidencias] = useState([]);
  const [records, setRecords] = useState([]);
  const [lotesForestales, setLotesForestales] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [loteFilter, setLoteFilter] = useState("");

  async function loadData() {
    if (!activeConstructoraId) return;
    try {
      setLoading(true);
      setError("");
      const [evidenciasData, recordsData, lotesData] = await Promise.allSettled([
        getEvidenciasConstructora(activeConstructoraId),
        getEmpresaRegistrosAmbientales(activeConstructoraId),
        activePreset.key === "aserradero" ? getLotesForestales(activeConstructoraId) : Promise.resolve([]),
      ]);

      if (evidenciasData.status === "fulfilled") {
        setEvidencias(normalizeEvidenceRows(evidenciasData.value));
      } else {
        setEvidencias([]);
      }

      if (recordsData.status === "fulfilled") {
        setRecords(Array.isArray(recordsData.value) ? recordsData.value : recordsData.value?.results || []);
      } else {
        setRecords([]);
      }

      if (lotesData.status === "fulfilled") {
        setLotesForestales(Array.isArray(lotesData.value) ? lotesData.value : []);
      } else {
        setLotesForestales([]);
      }

      if (evidenciasData.status === "rejected" && recordsData.status === "rejected") {
        throw evidenciasData.reason || recordsData.reason;
      }
    } catch (requestError) {
      setError(requestError?.response?.data?.error || "No se pudieron cargar las evidencias.");
    } finally {
      setHasLoaded(true);
      setLoading(false);
    }
  }

  useEffect(() => {
    setHasLoaded(false);
    setEvidencias([]);
    setRecords([]);
    setLotesForestales([]);
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConstructoraId, activePreset.key]);

  const presetRows = useMemo(() => {
    const matching = evidencias.filter((row) => row.metadata?.preset === activePreset.key);
    const baseRows = matching.length ? matching : evidencias;
    if (!loteFilter) return baseRows;
    return baseRows.filter((row) => row.lote_forestal_id === loteFilter || row.metadata?.lote === loteFilter);
  }, [activePreset.key, evidencias, loteFilter]);

  const coverage = useMemo(
    () => getEvidenceCoverage(presetRows, config.requiredEvidenceTypes),
    [config.requiredEvidenceTypes, presetRows]
  );

  const kpis = useMemo(() => config.buildKpis(presetRows), [config, presetRows]);
  const recommendations = useMemo(() => config.buildRecommendations(presetRows, records), [config, presetRows, records]);

  async function handleSubmit(form) {
    if (!activeConstructoraId) return;
    if (!form.archivo || !form.nombre.trim()) {
      setError("Nombre y archivo son obligatorios.");
      return;
    }

    const metadata = {
      preset: activePreset.key,
      evidence_type: form.evidenceType,
      evidence_label: form.selectedType?.label || form.evidenceType,
      module: form.metadata?.module || "",
      lote: form.lote_id || form.metadata?.lote || "",
      ...Object.fromEntries(
        Object.entries(form.metadata || {}).filter(([, value]) => value !== undefined && value !== null && value !== "")
      ),
    };

    try {
      setSaving(true);
      setError("");
      const formData = new FormData();
      formData.append("nombre", form.nombre.trim());
      formData.append("tipo_evidencia", form.selectedType?.backendType || "otro");
      formData.append("archivo", form.archivo);
      formData.append("estado_documental", form.estado_documental || "pendiente");
      formData.append("metadata_extraccion", JSON.stringify(metadata));
      if (form.fecha_documento) formData.append("fecha_documento", form.fecha_documento);
      if (form.registro_emision) formData.append("registro_emision", form.registro_emision);
      if (form.lote_forestal) formData.append("lote_forestal", form.lote_forestal);
      if (form.lote_id) formData.append("lote_id", form.lote_id);
      if (form.observaciones.trim()) formData.append("observaciones", form.observaciones.trim());

      await crearEvidenciaConstructora(activeConstructoraId, formData);
      await loadData();
    } catch (requestError) {
      const responseData = requestError?.response?.data;
      const firstError =
        responseData?.error ||
        (typeof responseData === "object" && responseData !== null
          ? Object.values(responseData).flat().find(Boolean)
          : null);
      setError(firstError || "No se pudo crear la evidencia.");
    } finally {
      setSaving(false);
    }
  }

  if (!activeConstructoraId) {
    return (
      <EmptyState
        title="Evidencias"
        description="Selecciona o crea una empresa para gestionar respaldos documentales."
      />
    );
  }

  if (loading && !hasLoaded) {
    return (
      <PlatformLoader
        title="Cargando evidencias"
        description="Estamos preparando documentos, cobertura, pendientes críticos y checklist ambiental."
      />
    );
  }

  return (
    <main className="mx-auto max-w-7xl space-y-8">
      <EvidenceHero
        activeConstructora={activeConstructora}
        config={config}
        coverage={coverage}
        preset={activePreset}
        rows={presetRows}
      />

      {error ? (
        <p className="rounded-2xl border border-[#F1B8B8] bg-[var(--danger-bg)] p-3 text-sm text-[#B42318]">
          {error}
        </p>
      ) : null}

      <EvidenceKpiGrid kpis={kpis} />

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <EvidenceUploadPanel
          config={config}
          constructoraId={activeConstructoraId}
          lotesForestales={lotesForestales}
          onSubmit={handleSubmit}
          presetKey={activePreset.key}
          records={records}
          saving={saving}
        />
        <div className="space-y-6">
          <EvidenceChecklist items={config.checklist} />
          <EvidenceValidationPanel recommendations={recommendations} />
        </div>
      </section>

      {activePreset.key === "aserradero" && lotesForestales.length ? (
        <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_12px_28px_var(--shadow)]">
          <label className="text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)]">
            Filtrar por lote forestal
          </label>
          <select
            className="mt-2 w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm font-semibold text-[var(--text-main)] outline-none focus:border-emerald-300 focus:ring-4 focus:ring-emerald-100 sm:max-w-md"
            value={loteFilter}
            onChange={(event) => setLoteFilter(event.target.value)}
          >
            <option value="">Todos los lotes</option>
            {lotesForestales.map((lote) => (
              <option key={lote.id} value={lote.lote_id}>
                {lote.lote_id} - {lote.especie}
              </option>
            ))}
          </select>
        </section>
      ) : null}

      {!loading && presetRows.length === 0 ? (
        <EvidenceEmptyState message={config.emptyMessage} />
      ) : (
        <EvidenceTable config={config} rows={presetRows} />
      )}
    </main>
  );
}

export default EvidenciasPage;
