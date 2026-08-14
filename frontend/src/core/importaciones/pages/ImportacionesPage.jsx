import { useMemo, useState } from "react";

import {
  confirmarImportOrganizaciones,
  confirmarImportEtapasForOrganizacion,
  confirmarImportFactores,
  confirmarImportObrasForOrganizacion,
  confirmRegistroEmisionImportForOrganizacion,
  createEmpresaRegistroAmbiental,
  previewImportOrganizaciones,
  previewImportEtapasForOrganizacion,
  previewImportFactores,
  previewImportGenerica,
  previewImportObrasForOrganizacion,
  previewRegistroEmisionImportForOrganizacion,
} from "@/shared/services/api";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { DEFAULT_PRESET_KEY, getActivePreset } from "@/presets/registry";
import { aserraderoImport } from "@/presets/aserradero/import";
import { construccionImport } from "@/presets/construccion/import";
import { industrialImport } from "@/presets/industrial/import";
import { transporteImport } from "@/presets/transporte/import";
import {
  buildImportSummary,
  mapPresetImportPayload,
  normalizeImportRows,
} from "@/presets/shared/importConfig";

import ImportConfirmPanel from "../components/ImportConfirmPanel";
import ImportEmptyState from "../components/ImportEmptyState";
import ImportHero from "../components/ImportHero";
import ImportPresetSelector from "../components/ImportPresetSelector";
import ImportPreviewTable from "../components/ImportPreviewTable";
import ImportTemplatePanel from "../components/ImportTemplatePanel";
import ImportUploadPanel from "../components/ImportUploadPanel";
import ImportValidationSummary from "../components/ImportValidationSummary";
import IngestionV2Flow from "@/features/importaciones/components/IngestionV2Flow";

const importByPreset = {
  construccion: construccionImport,
  forestal: aserraderoImport,
  aserradero: aserraderoImport,
  transporte: transporteImport,
  industrial: industrialImport,
};

const constructionPreview = {
  organizaciones: previewImportOrganizaciones,
  factores: previewImportFactores,
  etapas: previewImportEtapasForOrganizacion,
  obras: previewImportObrasForOrganizacion,
  registros: previewRegistroEmisionImportForOrganizacion,
};

const constructionConfirm = {
  organizaciones: confirmarImportOrganizaciones,
  factores: confirmarImportFactores,
  etapas: confirmarImportEtapasForOrganizacion,
  obras: confirmarImportObrasForOrganizacion,
  registros: confirmRegistroEmisionImportForOrganizacion,
};
function hasOperationalAmount(data) {
  return [
    "cantidad",
    "consumo_kwh",
    "energia_kwh",
    "volumen_m3",
    "volumen_entrada_m3",
    "volumen_salida_m3",
    "volumen_secado_m3",
    "distancia_km",
    "litros_diesel",
    "carga_m3",
    "horas_secado",
    "superficie_m2",
    "peso_ton",
  ].some((field) => String(data?.[field] || "").trim());
}

function validatePreviewRows(rows, columns) {
  return normalizeImportRows(rows).map((row) => {
    const data = row.data || {};
    const errors = [];

    columns.forEach((column) => {
      if (!(column in data)) {
        errors.push(`Falta columna ${column}`);
      }
    });

    if (!hasOperationalAmount(data)) {
      errors.push("Falta cantidad operacional.");
    }

    return {
      ...row,
      status: errors.length ? "error" : "valid",
      errors,
      warnings: Number(data.factor_emision || 0) ? [] : ["Sin factor de emisión"],
    };
  });
}
function ImportacionesPage({ onImportConfirmed }) {
  const { activeOrganizacion, activeOrganizacionId, refreshOrganizaciones } = useOrganizacionActiva();
  const activePreset = getActivePreset(activeOrganizacion?.preset || DEFAULT_PRESET_KEY);
  const config = importByPreset[activePreset.key] || construccionImport;
  const [selectedModule, setSelectedModule] = useState(config.modules[0]?.key || "");
  const [previewRows, setPreviewRows] = useState([]);
  const [backendBatchId, setBackendBatchId] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const moduleConfig = useMemo(
    () => config.modules.find((item) => item.key === selectedModule) || config.modules[0],
    [config.modules, selectedModule]
  );

  async function handleFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !moduleConfig) return;

    setLoading(true);
    setError("");
    setMessage("");
    setBackendBatchId(null);

    try {
      if (activePreset.key === "construccion" && constructionPreview[selectedModule]) {
        const previewFn = constructionPreview[selectedModule];
        const result = ["etapas", "obras", "registros"].includes(selectedModule)
          ? await previewFn(activeOrganizacionId, file)
          : await previewFn(file);

        const rows = normalizeImportRows(result.rows || result);
        setPreviewRows(rows);
        setSummary(result.summary || buildImportSummary(rows));
        setBackendBatchId(result.batch_id || null);
      } else {
        const result = await previewImportGenerica(file, {
          columns: moduleConfig.columns,
          module: selectedModule,
        });

        const rows = validatePreviewRows(result.rows || result, moduleConfig.columns);
        setPreviewRows(rows);
        setSummary(result.summary || buildImportSummary(rows));
        setBackendBatchId(result.batch_id || null);
      }
    } catch (requestError) {
      setError(
        requestError.response?.data?.error ||
        requestError.message ||
        "No se pudo previsualizar el archivo."
      );
    } finally {
      setLoading(false);
    }
  }

  function handlePreviewRowsChange(nextRows) {
    const rows = validatePreviewRows(nextRows, moduleConfig?.columns || []);
    setPreviewRows(rows);
    setSummary(buildImportSummary(rows));
    setBackendBatchId(null);
  }

  async function handleConfirm() {
    if (!activeOrganizacionId || !moduleConfig || !previewRows.length) return;
    setSaving(true);
    setError("");
    setMessage("");

    try {
      if (activePreset.key === "construccion" && constructionConfirm[selectedModule]) {
        const confirmFn = constructionConfirm[selectedModule];
        const payload = backendBatchId ? { batch_id: backendBatchId } : { rows: previewRows.filter((row) => row.status === "valid") };
        const result = ["etapas", "obras", "registros"].includes(selectedModule)
          ? await confirmFn(activeOrganizacionId, payload)
          : await confirmFn(payload);
        setMessage(`Importacion confirmada. Creados: ${result.creados ?? result.created ?? 0}.`);
        await refreshOrganizaciones().catch(() => undefined);
        await onImportConfirmed?.();
      } else if (activePreset.key === "aserradero" && moduleConfig.supported) {
        const payloads = mapPresetImportPayload("aserradero", selectedModule, previewRows, config.buildPayload);
        for (const payload of payloads) {
          await createEmpresaRegistroAmbiental(activeOrganizacionId, payload);
        }
        setMessage(`${payloads.length} registros forestales importados correctamente.`);
        await onImportConfirmed?.();
      } else {
        setMessage("Modulo preparado. La confirmacion masiva quedara conectada en una fase backend posterior.");
      }
    } catch (requestError) {
      setError(requestError.response?.data?.error || requestError.message || "No se pudo confirmar la importacion.");
    } finally {
      setSaving(false);
    }
  }

  if (!activeOrganizacion) {
    return (
      <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-8 text-center text-[var(--text-muted)]">
        Selecciona o crea una empresa para comenzar importaciones.
      </div>
    );
  }

  const recommendations = config.buildRecommendations(summary || {});
  const canConfirm = Boolean(activeOrganizacionId && previewRows.some((row) => row.status === "valid") && moduleConfig?.supported);

  return (
    <main className="mx-auto max-w-7xl space-y-8">
      <ImportHero activeOrganizacion={activeOrganizacion} config={config} preset={activePreset} />
      <IngestionV2Flow organizacionId={activeOrganizacionId} />
      {message && <p className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-black text-emerald-800">{message}</p>}
      {error && <p className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm font-black text-rose-800">{error}</p>}

      <ImportPresetSelector modules={config.modules} selectedModule={selectedModule} onChange={(next) => { setSelectedModule(next); setPreviewRows([]); setSummary(null); }} />
      <ImportTemplatePanel modules={config.templates} />

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <ImportUploadPanel disabled={loading || !moduleConfig?.supported} module={moduleConfig} onFile={handleFile} />
        <div className="rounded-3xl border border-amber-200 bg-amber-50 p-5 text-amber-800">
          <h2 className="text-xl font-black">Recomendaciones</h2>
          <div className="mt-3 space-y-2">
            {recommendations.map((item) => <p key={item} className="text-sm font-semibold leading-6">{item}</p>)}
          </div>
        </div>
      </section>

      {summary ? <ImportValidationSummary summary={summary} /> : <ImportEmptyState message={config.emptyMessage} />}
      <ImportPreviewTable
        columns={moduleConfig?.columns || []}
        rows={previewRows}
        onRowsChange={handlePreviewRowsChange}
      />
      <ImportConfirmPanel
        canConfirm={canConfirm}
        message={moduleConfig?.supported ? "Confirma solo filas validas y con empresa activa." : "Modulo preparado para proxima conexion backend."}
        onConfirm={handleConfirm}
        saving={saving}
      />
    </main>
  );
}


export default ImportacionesPage;
