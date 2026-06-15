import { useEffect, useMemo, useState } from "react";

import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { DEFAULT_PRESET_KEY, getActivePreset } from "@/presets/registry";
import { aserraderoFactors } from "@/presets/aserradero/factors";
import { construccionFactors } from "@/presets/construccion/factors";
import { transporteFactors } from "@/presets/transporte/factors";
import { industrialFactors } from "@/presets/industrial/factors";
import {
  aplicarFactorRegistroEmision,
  createFactorEmision,
  getEmpresaRegistrosAmbientales,
  getFactoresEmision,
  updateFactorEmision,
} from "@/shared/services/api";

import FactorApplyModal from "../components/FactorApplyModal";
import FactorCatalog from "../components/FactorCatalog";
import FactorCreateModal from "../components/FactorCreateModal";
import FactorHero from "../components/FactorHero";
import FactorKpiGrid from "../components/FactorKpiGrid";
import FactorSuggestionPanel from "../components/FactorSuggestionPanel";
import PendingFactorRecords from "../components/PendingFactorRecords";

const configByPreset = {
  construccion: construccionFactors,
  aserradero: aserraderoFactors,
  transporte: transporteFactors,
  industrial: industrialFactors,
};

function normalizeRows(data) {
  return Array.isArray(data) ? data : data?.results || data?.data || data?.factores || data?.registros || [];
}

function normalizeFactor(factor) {
  return {
    ...factor,
    metadata: factor?.metadata && typeof factor.metadata === "object" ? factor.metadata : {},
    factor_emision: Number(factor?.factor_emision || 0),
    activo: factor?.activo !== false,
  };
}

function FactoresPage() {
  const { activeConstructora, activeConstructoraId } = useConstructoraActiva();
  const activePreset = getActivePreset(activeConstructora?.preset || DEFAULT_PRESET_KEY);
  const config = configByPreset[activePreset.key] || construccionFactors;

  const [factors, setFactors] = useState([]);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [editFactor, setEditFactor] = useState(null);
  const [applyState, setApplyState] = useState(null);

  async function loadData() {
    if (!activeConstructoraId) return;

    try {
      setLoading(true);
      setError("");

      const [factorData, recordData] = await Promise.all([
        getFactoresEmision({ preset: activePreset.key }),
        getEmpresaRegistrosAmbientales(activeConstructoraId),
      ]);

      setFactors(normalizeRows(factorData).map(normalizeFactor));
      setRecords(normalizeRows(recordData).map((row) => ({ ...row, metadata: row.metadata || {} })));
    } catch (requestError) {
      setError(requestError.response?.data?.error || "No se pudieron cargar factores y registros.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConstructoraId, activePreset.key]);

  const scopedRecords = useMemo(() => {
    if (activePreset.key === "construccion") return records;
    const scoped = records.filter((record) => record.metadata?.preset === activePreset.key);
    return scoped.length ? scoped : records.filter((record) => !record.metadata?.preset);
  }, [activePreset.key, records]);

  const pendingRecords = useMemo(
    () => scopedRecords.filter((record) => !Number(record.factor_emision || 0)),
    [scopedRecords]
  );

  const kpis = useMemo(() => config.buildKpis(factors, scopedRecords), [config, factors, scopedRecords]);
  const recommendations = useMemo(() => config.buildRecommendations(factors, pendingRecords), [config, factors, pendingRecords]);
  const status = useMemo(() => config.getFactorQualityStatus(factors, scopedRecords), [config, factors, scopedRecords]);
  const firstSuggestion = pendingRecords[0] ? config.suggestionRules.suggestFactor(pendingRecords[0], factors) : null;

  async function handleCreateFactor(payload) {
    try {
      setError("");
      await createFactorEmision(payload);
      setCreateOpen(false);
      setMessage("Factor creado correctamente.");
      await loadData();
    } catch (requestError) {
      setError(requestError.response?.data?.error || "No se pudo crear el factor.");
    }
  }

  async function handleUpdateFactor(payload) {
    if (!editFactor?.id) return;

    try {
      setError("");
      await updateFactorEmision(editFactor.id, payload);
      setEditFactor(null);
      setMessage("Factor actualizado correctamente.");
      await loadData();
    } catch (requestError) {
      setError(requestError.response?.data?.error || "No se pudo actualizar el factor.");
    }
  }

  async function handleToggleActive(factor) {
    try {
      setError("");
      await updateFactorEmision(factor.id, { activo: !factor.activo });
      setMessage(factor.activo ? "Factor desactivado." : "Factor activado.");
      await loadData();
    } catch (requestError) {
      setError(requestError.response?.data?.error || "No se pudo cambiar el estado del factor.");
    }
  }

  async function handleApplyFactor(factor) {
    if (!applyState?.record || !factor) return;

    try {
      setError("");
      await aplicarFactorRegistroEmision(activeConstructoraId, applyState.record.id, { factor_id: factor.id });
      setApplyState(null);
      setMessage("Factor aplicado y emisiones recalculadas correctamente.");
      await loadData();
    } catch (requestError) {
      setError(requestError.response?.data?.error || "No se pudo aplicar el factor.");
    }
  }

  if (!activeConstructoraId) {
    return (
      <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-8 text-center text-[var(--text-muted)]">
        Selecciona una empresa para gestionar factores de emisión.
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-7xl space-y-8">
      <FactorHero activeConstructora={activeConstructora} config={config} preset={activePreset} status={status} />

      {loading && (
        <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-center text-sm font-semibold text-[var(--text-muted)]">
          Cargando factores...
        </p>
      )}

      {message && (
        <p className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-center text-sm font-bold text-emerald-800">
          {message}
        </p>
      )}

      {error && (
        <p className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-center text-sm font-bold text-rose-800">
          {error}
        </p>
      )}

      <FactorKpiGrid kpis={kpis} />

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_0.8fr]">
        <FactorCatalog
          config={config}
          factors={factors}
          onCreate={() => setCreateOpen(true)}
          onEdit={setEditFactor}
          onToggleActive={handleToggleActive}
        />

        <div className="space-y-4">
          <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-premium)]">
            <h2 className="text-xl font-black text-[var(--text-main)]">Recomendaciones</h2>
            <div className="mt-4 space-y-3">
              {recommendations.map((item) => (
                <p key={item} className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-center text-sm font-semibold text-amber-800">
                  {item}
                </p>
              ))}
            </div>
          </div>

          <FactorSuggestionPanel suggestion={firstSuggestion} />
        </div>
      </section>

      <PendingFactorRecords
        factors={factors}
        pendingRecords={pendingRecords}
        suggestFactor={config.suggestionRules.suggestFactor}
        onApply={(record, suggestion) => setApplyState({ record, suggestion })}
      />

      {createOpen && (
        <FactorCreateModal
          config={config}
          onClose={() => setCreateOpen(false)}
          onSubmit={handleCreateFactor}
          preset={activePreset.key}
        />
      )}

      {editFactor && (
        <FactorCreateModal
          config={config}
          initialFactor={editFactor}
          mode="edit"
          onClose={() => setEditFactor(null)}
          onSubmit={handleUpdateFactor}
          preset={activePreset.key}
        />
      )}

      {applyState && (
        <FactorApplyModal
          factors={factors}
          onApply={handleApplyFactor}
          onClose={() => setApplyState(null)}
          record={applyState.record}
          suggestion={applyState.suggestion}
        />
      )}
    </main>
  );
}

export default FactoresPage;