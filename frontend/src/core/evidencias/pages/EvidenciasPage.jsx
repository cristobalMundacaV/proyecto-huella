import { useEffect, useMemo, useState } from "react";
import { FileText, FileUp, X } from "lucide-react";

import EmptyState from "@/shared/components/EmptyState";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import {
  crearEvidenciaOrganizacion,
  getEvidenciasOrganizacion,
  getEmpresaRegistrosAmbientales,
  getLotesForestales,
} from "@/shared/services/api";
import { createEnvironmentalDocument } from "@/features/environmental/services/environmentalComplianceApi";
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
  forestal: aserraderoEvidence,
  aserradero: aserraderoEvidence,
  transporte: transporteEvidence,
  industrial: industrialEvidence,
};

const initialEnvironmentalDocumentForm = {
  tipo_documento: "",
  nombre: "",
  fecha_documento: "",
  fuente_origen: "manual",
  resumen: "",
};

function EvidenciasPage() {
  const { activeOrganizacionId, activeOrganizacion } = useOrganizacionActiva();
  const activePreset = getActivePreset(activeOrganizacion?.preset || DEFAULT_PRESET_KEY);
  const config = evidenceByPreset[activePreset.key] || construccionEvidence;
  const [evidencias, setEvidencias] = useState([]);
  const [records, setRecords] = useState([]);
  const [lotesForestales, setLotesForestales] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [documentSaving, setDocumentSaving] = useState(false);
  const [error, setError] = useState("");
  const [documentFeedback, setDocumentFeedback] = useState("");
  const [loteFilter, setLoteFilter] = useState("");
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isDocumentModalOpen, setIsDocumentModalOpen] = useState(false);
  const [documentForm, setDocumentForm] = useState(initialEnvironmentalDocumentForm);

  const environmentalDocumentTypes = useMemo(() => {
    const fromEvidence = [...(config.requiredEvidenceTypes || []), ...(config.optionalEvidenceTypes || [])].map((item) => ({
      label: item.label,
      value: item.key || item.backendType || item.label,
    }));
    return [...fromEvidence, { label: "Otro", value: "otro" }];
  }, [config]);

  async function loadData() {
    if (!activeOrganizacionId) return;
    try {
      setLoading(true);
      setError("");
      const [evidenciasData, recordsData, lotesData] = await Promise.allSettled([
        getEvidenciasOrganizacion(activeOrganizacionId),
        getEmpresaRegistrosAmbientales(activeOrganizacionId),
        ["forestal", "aserradero"].includes(activePreset.key) ? getLotesForestales(activeOrganizacionId) : Promise.resolve([]),
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
      setError(requestError?.response?.data?.error || "No se pudieron cargar las evidencias ambientales.");
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
  }, [activeOrganizacionId, activePreset.key]);

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
    if (!activeOrganizacionId) return;
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

      await crearEvidenciaOrganizacion(activeOrganizacionId, formData);
      await loadData();
      setIsUploadModalOpen(false);
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

  async function handleEnvironmentalDocumentSubmit(event) {
    event.preventDefault();
    if (!activeOrganizacionId) return;
    const selectedType = documentForm.tipo_documento || environmentalDocumentTypes[0]?.value || "otro";
    const selectedLabel = environmentalDocumentTypes.find((item) => item.value === selectedType)?.label || selectedType;
    try {
      setDocumentSaving(true);
      setError("");
      setDocumentFeedback("");
      await createEnvironmentalDocument(activeOrganizacionId, {
        ...documentForm,
        tipo_documento: selectedType,
        nombre: documentForm.nombre || selectedLabel,
        fecha_documento: documentForm.fecha_documento || new Date().toISOString().slice(0, 10),
        fuente_origen: documentForm.fuente_origen || "manual",
        resumen: documentForm.resumen || `Documento ambiental registrado desde Evidencias Ambientales: ${selectedLabel}.`,
      });
      setDocumentForm(initialEnvironmentalDocumentForm);
      setIsDocumentModalOpen(false);
      setDocumentFeedback("Documento ambiental registrado correctamente.");
      window.setTimeout(() => setDocumentFeedback(""), 3200);
    } catch (requestError) {
      setError(requestError?.response?.data?.error || "No se pudo registrar el documento ambiental.");
    } finally {
      setDocumentSaving(false);
    }
  }

  if (!activeOrganizacionId) {
    return (
      <EmptyState
        title="Evidencias Ambientales"
        description="Selecciona o crea una empresa para gestionar respaldos documentales ambientales."
      />
    );
  }

  if (loading && !hasLoaded) {
    return (
      <PlatformLoader
        title="Cargando evidencias ambientales"
        description="Estamos preparando documentos, cobertura, pendientes críticos y checklist ambiental."
      />
    );
  }

  return (
    <main className="mx-auto max-w-7xl space-y-8">
      <EvidenceHero
        activeOrganizacion={activeOrganizacion}
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

      {documentFeedback ? (
        <p className="rounded-2xl border border-emerald-200 bg-emerald-50 p-3 text-sm font-black text-emerald-800">
          {documentFeedback}
        </p>
      ) : null}

      <section className="flex flex-col gap-4 rounded-3xl border border-emerald-200 bg-emerald-50/70 p-5 shadow-[var(--shadow-card)] sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-800">Evidencias Ambientales</p>
          <h2 className="mt-1 text-xl font-black text-[var(--text-main)]">Documentos, respaldos y trazabilidad ambiental</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-700">
            Toda carga documental ambiental se gestiona aquí. Importaciones queda separado para carga masiva y configuraciones.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <button
            type="button"
            onClick={() => {
              setDocumentForm({ ...initialEnvironmentalDocumentForm, tipo_documento: environmentalDocumentTypes[0]?.value || "" });
              setIsDocumentModalOpen(true);
            }}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-200 bg-white px-5 py-3 text-sm font-black text-emerald-800 shadow-sm hover:bg-emerald-50"
          >
            <FileText size={18} />
            Registrar documento ambiental
          </button>
          <button
            type="button"
            onClick={() => setIsUploadModalOpen(true)}
            className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white shadow-[0_14px_30px_rgba(15,124,109,0.18)] hover:bg-[var(--primary-dark)]"
          >
            <FileUp size={18} />
            Subir evidencia
          </button>
        </div>
      </section>

      <EvidenceKpiGrid kpis={kpis} />

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <EvidenceChecklist items={config.checklist} />
        <EvidenceValidationPanel recommendations={recommendations} />
      </section>

      {["forestal", "aserradero"].includes(activePreset.key) && lotesForestales.length ? (
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

      {isUploadModalOpen ? (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-950/35 px-4 py-6 backdrop-blur-sm">
          <div className="relative max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-[32px] border border-emerald-100 bg-white p-4 shadow-[0_30px_90px_rgba(15,23,42,0.22)] sm:p-6">
            <button
              type="button"
              onClick={() => setIsUploadModalOpen(false)}
              className="absolute right-4 top-4 z-10 rounded-2xl border border-slate-200 bg-white p-2 text-slate-600 shadow-sm hover:bg-slate-50"
              aria-label="Cerrar modal"
            >
              <X size={18} />
            </button>
            <EvidenceUploadPanel
              config={config}
              organizacionId={activeOrganizacionId}
              lotesForestales={lotesForestales}
              onSubmit={handleSubmit}
              presetKey={activePreset.key}
              records={records}
              saving={saving}
            />
          </div>
        </div>
      ) : null}

      {isDocumentModalOpen ? (
        <div className="fixed inset-0 z-[75] flex items-center justify-center bg-slate-950/35 px-4 py-6 backdrop-blur-sm">
          <form onSubmit={handleEnvironmentalDocumentSubmit} className="w-full max-w-xl rounded-3xl border border-emerald-100 bg-white p-5 shadow-[0_30px_90px_rgba(15,23,42,0.22)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-black text-[var(--text-main)]">Registrar documento ambiental</h2>
                <p className="mt-1 text-sm text-[var(--text-muted)]">Registro manual para iniciar trazabilidad documental ambiental.</p>
              </div>
              <button type="button" onClick={() => setIsDocumentModalOpen(false)} className="rounded-xl border border-[var(--border)] p-2 text-[var(--text-muted)]">
                <X size={18} />
              </button>
            </div>

            <div className="mt-5 grid gap-4">
              <label className="text-sm font-bold text-[var(--text-main)]">
                Tipo de documento
                <select value={documentForm.tipo_documento} onChange={(event) => setDocumentForm((current) => ({ ...current, tipo_documento: event.target.value }))} className="mt-2 w-full px-3 py-2">
                  {environmentalDocumentTypes.map((item) => (
                    <option key={item.value} value={item.value}>{item.label}</option>
                  ))}
                </select>
              </label>
              <label className="text-sm font-bold text-[var(--text-main)]">
                Nombre
                <input value={documentForm.nombre} onChange={(event) => setDocumentForm((current) => ({ ...current, nombre: event.target.value }))} className="mt-2 w-full px-3 py-2" />
              </label>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-bold text-[var(--text-main)]">
                  Fecha documento
                  <input type="date" value={documentForm.fecha_documento} onChange={(event) => setDocumentForm((current) => ({ ...current, fecha_documento: event.target.value }))} className="mt-2 w-full px-3 py-2" />
                </label>
                <label className="text-sm font-bold text-[var(--text-main)]">
                  Fuente origen
                  <select value={documentForm.fuente_origen} onChange={(event) => setDocumentForm((current) => ({ ...current, fuente_origen: event.target.value }))} className="mt-2 w-full px-3 py-2">
                    {["manual", "excel", "csv", "pdf", "foto", "cems", "laboratorio", "otro"].map((item) => (
                      <option key={item} value={item}>{item}</option>
                    ))}
                  </select>
                </label>
              </div>
              <label className="text-sm font-bold text-[var(--text-main)]">
                Resumen
                <textarea value={documentForm.resumen} onChange={(event) => setDocumentForm((current) => ({ ...current, resumen: event.target.value }))} rows={3} className="mt-2 w-full px-3 py-2" />
              </label>
            </div>

            <div className="mt-5 flex justify-end gap-3">
              <button type="button" onClick={() => setIsDocumentModalOpen(false)} className="rounded-xl border border-[var(--border)] bg-white px-4 py-2 text-sm font-black text-[var(--text-muted)]">
                Cancelar
              </button>
              <button type="submit" disabled={documentSaving} className="rounded-xl border border-emerald-200 bg-emerald-600 px-4 py-2 text-sm font-black text-white disabled:opacity-60">
                {documentSaving ? "Guardando..." : "Guardar"}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </main>
  );
}

export default EvidenciasPage;
