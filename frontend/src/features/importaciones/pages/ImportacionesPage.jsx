import { useMemo, useState } from "react";
import {
  AlertTriangle,
  Boxes,
  Building2,
  CheckCircle2,
  DatabaseZap,
  Download,
  Factory,
  FileSpreadsheet,
  Loader2,
  Save,
  Upload,
} from "lucide-react";

import Toast from "@/shared/components/Toast";
import EmptyState from "@/shared/components/EmptyState";
import ImportarEvidenciaObraModal from "@/shared/components/ImportarEvidenciaObraModal";
import {
  confirmarImportFactores,
  confirmarImportConstructoras,
  confirmarImportacionCompletaConstruccion,
  confirmarImportObrasForConstructora,
  confirmarImportEtapasForConstructora,
  confirmRegistroEmisionImportForConstructora,
  previewImportacionCompletaConstruccion,
  previewImportConstructoras,
  previewImportFactores,
  previewImportObrasForConstructora,
  previewImportEtapasForConstructora,
  previewRegistroEmisionImportForConstructora,
  getPlantillaImportacionConstruccionUrl,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { useFactores } from "@/features/factores/context/FactoresContext";

const emptyImportState = {
  fileName: "",
  loading: false,
  saving: false,
  error: "",
  result: null,
  savedMessage: "",
};

const factorSummaryLabels = [
  ["total_filas", "Total filas"],
  ["validas", "Válidas"],
  ["con_error", "Con error"],
  ["duplicadas", "Duplicadas"],
  ["posibles_creaciones", "Nuevas"],
  ["posibles_actualizaciones", "Actualizaciones"],
];

const companySummaryLabels = [
  ["total_filas", "Total filas"],
  ["validas", "Válidas"],
  ["con_error", "Con error"],
  ["duplicadas", "Duplicadas"],
  ["posibles_creaciones", "Empresas nuevas"],
  ["posibles_actualizaciones", "Actualizaciones"],
];

const registroSummaryLabels = [
  ["filas_validas", "Filas válidas"],
  ["filas_con_error", "Filas con error"],
  ["factores_encontrados", "Factores encontrados"],
  ["factores_faltantes", "Factores faltantes"],
  ["obras_encontrados", "Obras encontradas"],
  ["obras_nuevos_detectados", "Obras nuevas"],
];

const obraSummaryLabels = [
  ["validas", "Filas válidas"],
  ["con_error", "Filas con error"],
  ["obras_nuevos", "Obras nuevas"],
  ["obras_existentes", "Obras existentes"],
  ["duplicadas", "Duplicadas"],
];

const unitSummaryLabels = [
  ["validas", "Filas válidas"],
  ["con_error", "Filas con error"],
  ["nuevas", "Etapas nuevas"],
  ["existentes", "Etapas existentes"],
  ["duplicadas", "Duplicadas"],
];

const previewColumnsByType = {
  factors: [
    ["row_number", "Fila"],
    ["status", "Estado"],
    ["fuente_emision", "Fuente de emisión"],
    ["categoria", "Categoría"],
    ["unidad", "Unidad"],
    ["factor_emision", "Factor"],
    ["fuente", "Fuente"],
    ["anio", "Año"],
    ["observaciones", "Observaciones"],
  ],
  constructoras: [
    ["row_number", "Fila"],
    ["status", "Estado"],
    ["constructora_id", "ID constructora"],
    ["nombre", "Nombre"],
    ["rut", "RUT"],
    ["region", "Región"],
    ["comuna", "Comuna"],
    ["direccion", "Dirección"],
    ["rubro", "Rubro"],
    ["email", "Email"],
    ["telefono", "Teléfono"],
    ["contacto", "Contacto"],
    ["observaciones", "Observaciones"],
  ],
  etapas: [
    ["row_number", "Fila"],
    ["status", "Estado"],
    ["etapa_id", "ID etapa"],
    ["constructora_id", "ID constructora"],
    ["nombre", "Nombre"],
    ["tipo", "Tipo"],
    ["region", "Región"],
    ["comuna", "Comuna"],
    ["estado", "Estado etapa"],
    ["observaciones", "Observaciones"],
  ],
  obras: [
    ["row_number", "Fila"],
    ["status", "Estado"],
    ["codigo_obra", "Código de obra"],
    ["constructora_id", "ID constructora"],
    ["etapa_id", "ID etapa"],
    ["nombre", "Obra / proyecto"],
    ["tipo_proyecto", "Tipo"],
    ["fecha", "Fecha"],
    ["superficie_m2", "Superficie"],
    ["ubicacion", "Ubicación"],
    ["observaciones", "Observaciones"],
  ],
  registros: [
    ["row_number", "Fila"],
    ["status", "Estado"],
    ["registro_id", "ID registro"],
    ["codigo_obra", "Código de obra"],
    ["etapa_id", "ID etapa"],
    ["fuente_emision", "Fuente"],
    ["categoria", "Categoría"],
    ["cantidad", "Cantidad"],
    ["unidad", "Unidad"],
    ["factor_emision", "Factor"],
    ["fecha", "Fecha"],
    ["observaciones", "Observaciones"],
  ],
};

function isPlainObject(value) {
  return value && typeof value === "object" && !Array.isArray(value);
}

function normalizeTextList(value) {
  if (Array.isArray(value)) {
    return value
      .flatMap((item) => normalizeTextList(item))
      .filter(Boolean);
  }

  if (isPlainObject(value)) {
    return Object.entries(value)
      .map(([key, item]) => `${key}: ${normalizeTextList(item).join(", ")}`)
      .filter(Boolean);
  }

  if (value === null || value === undefined || value === "") {
    return [];
  }

  return [String(value)];
}

function getRowValue(row, key) {
  if (key === "row_number") return row.row_number;
  if (key === "status") return row.status;
  return row.data?.[key] ?? row[key] ?? "";
}

function getRowMessages(row) {
  const errors = normalizeTextList(row.errors);
  const warnings = normalizeTextList(row.warnings);
  const observations = normalizeTextList(row.data?.observaciones);

  if (errors.length) return { type: "error", text: errors.join("; ") };
  if (warnings.length) return { type: "warning", text: warnings.join("; ") };
  if (observations.length) return { type: "info", text: observations.join("; ") };
  if (row.db_action === "actualizar") return { type: "info", text: "Posible actualización" };
  return { type: "success", text: "Listo para guardar" };
}

function SummaryGrid({ summary, labels }) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
      {labels.map(([key, label]) => (
        <div
          key={key}
          className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 text-center shadow-[var(--shadow-soft)]"
        >
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--text-muted)]">
            {label}
          </p>
          <p className="mt-2 text-2xl font-black text-[var(--text-main)]">
            {formatNumber(Number(summary?.[key] || 0), 0)}
          </p>
        </div>
      ))}
    </div>
  );
}

function StatusBadge({ row }) {
  const isValid = row.status === "valid";
  return (
    <span
      className={`inline-flex items-center justify-center gap-2 rounded-full border px-3 py-1 text-xs font-black ${
        isValid
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : "border-red-200 bg-red-50 text-red-700"
      }`}
    >
      {isValid ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
      {isValid ? "Válida" : "Error"}
    </span>
  );
}

function PreviewTable({ rows = [], type = "registros" }) {
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 8;
  const columns = previewColumnsByType[type] || previewColumnsByType.registros;
  const totalPages = Math.max(1, Math.ceil(rows.length / rowsPerPage));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * rowsPerPage;
  const visibleRows = rows.slice(startIndex, startIndex + rowsPerPage);

  if (!rows.length) {
    return (
      <div className="mt-4 rounded-3xl border border-dashed border-[var(--border)] bg-[var(--bg-surface)] p-8 text-center">
        <p className="text-base font-bold text-[var(--text-main)]">Sin filas para previsualizar</p>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Carga un archivo con datos válidos para revisar el detalle antes de confirmar.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-4 space-y-4">
      <div className="overflow-x-auto rounded-3xl border border-[var(--border)] bg-[var(--bg-card)]">
        <table className="min-w-[980px] w-full text-sm">
          <thead className="border-b border-[var(--border)] bg-[var(--bg-surface)] text-[var(--text-muted)]">
            <tr>
              {columns.map(([key, label]) => (
                <th key={key} className="px-4 py-4 text-center text-xs font-black uppercase tracking-[0.08em]">
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row) => {
              const messages = getRowMessages(row);
              return (
                <tr key={`${row.row_number}-${row.status}`} className="border-b border-[var(--border)] last:border-b-0 hover:bg-emerald-50/40">
                  {columns.map(([key]) => {
                    if (key === "status") {
                      return (
                        <td key={key} className="px-4 py-4 text-center">
                          <StatusBadge row={row} />
                        </td>
                      );
                    }

                    if (key === "observaciones") {
                      const tone =
                        messages.type === "error"
                          ? "text-red-700"
                          : messages.type === "warning"
                            ? "text-amber-700"
                            : messages.type === "success"
                              ? "text-emerald-700"
                              : "text-[var(--text-muted)]";
                      return (
                        <td key={key} className={`px-4 py-4 text-center text-xs font-semibold ${tone}`}>
                          {messages.text}
                        </td>
                      );
                    }

                    const value = getRowValue(row, key);
                    return (
                      <td key={key} className="px-4 py-4 text-center font-semibold text-[var(--text-main)]">
                        {value || "-"}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {rows.length > rowsPerPage && (
        <div className="flex flex-col gap-3 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs font-semibold text-[var(--text-muted)]">
            Mostrando {startIndex + 1}-{Math.min(startIndex + rowsPerPage, rows.length)} de {rows.length} filas.
          </p>
          <div className="flex items-center justify-center gap-2">
            <button
              type="button"
              onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
              disabled={safeCurrentPage === 1}
              className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-xs font-bold text-[var(--text-main)] disabled:opacity-50"
            >
              Anterior
            </button>
            <span className="rounded-xl bg-[var(--primary-dark)] px-3 py-2 text-xs font-black text-white">
              {safeCurrentPage} / {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
              disabled={safeCurrentPage === totalPages}
              className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-xs font-bold text-[var(--text-main)] disabled:opacity-50"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ImportPanel({ title, icon, columns, state, type, summaryLabels, onPreview, onConfirm }) {
  const validRows = useMemo(
    () => state.result?.rows?.filter((row) => row.status === "valid") || [],
    [state.result]
  );

  return (
    <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--bg-card)] p-4 sm:p-6">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-emerald-200 bg-emerald-50 text-[var(--primary-dark)] shadow-[var(--shadow-soft)]">
            {icon}
          </div>
          <div>
            <h2 className="text-xl font-black text-[var(--text-main)]">{title}</h2>
            <p className="text-sm leading-6 text-[var(--text-muted)]">{columns.join(", ")}</p>
          </div>
        </div>

        <label className="premium-button premium-button-secondary flex w-full cursor-pointer items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-bold lg:w-fit">
          {state.loading ? <Loader2 className="animate-spin" size={18} /> : <Upload size={18} />}
          {state.loading ? "Previsualizando" : "Cargar archivo"}
          <input
            type="file"
            accept=".csv,.xlsx"
            disabled={state.loading || state.saving}
            onChange={onPreview}
            className="hidden"
          />
        </label>
      </div>

      {state.fileName && (
        <p className="mb-4 text-sm text-[var(--text-muted)]">
          Archivo: <span className="font-bold text-[var(--text-main)]">{state.fileName}</span>
        </p>
      )}

      {state.error && (
        <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
          {state.error}
        </div>
      )}

      {state.savedMessage && (
        <div className="mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-700">
          {state.savedMessage}
        </div>
      )}

      {state.result && (
        <div className="space-y-4">
          <SummaryGrid summary={state.result.summary} labels={summaryLabels} />
          <PreviewTable rows={state.result.rows || []} type={type} />
          <button
            type="button"
            onClick={() => onConfirm(validRows, state.result?.batch_id)}
            disabled={!validRows.length || state.saving}
            className="premium-button premium-button-primary inline-flex w-full items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60 sm:w-fit"
          >
            {state.saving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
            Confirmar importación
          </button>
        </div>
      )}
    </section>
  );
}

function CompleteSummaryCard({ label, value }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 text-center shadow-[var(--shadow-soft)]">
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--text-muted)]">{label}</p>
      <p className="mt-2 text-2xl font-black text-[var(--text-main)]">{value}</p>
    </div>
  );
}

function CompleteSectionCheck({ title, section }) {
  const total = section?.total || 0;
  const validas = section?.validas ?? section?.validos ?? 0;
  const errores = section?.errores || 0;

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-black text-[var(--text-main)]">{title}</p>
          <p className="mt-1 text-xs font-semibold text-[var(--text-muted)]">
            {formatNumber(validas, 0)} válidas de {formatNumber(total, 0)} filas
          </p>
        </div>
        <span
          className={`rounded-full border px-3 py-1 text-xs font-black ${
            errores > 0
              ? "border-red-200 bg-red-50 text-red-700"
              : "border-emerald-200 bg-emerald-50 text-emerald-700"
          }`}
        >
          {errores > 0 ? `${errores} errores` : "Correcto"}
        </span>
      </div>
    </div>
  );
}

function ConstructoraCompletaImportPanel({ state, onPreview, onConfirm }) {
  const blockingErrors = normalizeTextList(state.result?.blocking_errors);
  const sectionErrors =
    Number(state.result?.etapas?.errores || 0) +
    Number(state.result?.obras?.errores || 0) +
    Number(state.result?.registros_emision?.errores || 0) +
    Number(state.result?.factores?.errores || 0) +
    Number(state.result?.evidencias?.errores || 0);
  const constructoraData = state.result?.constructora?.data || {};

  return (
    <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--bg-card)] p-4 sm:p-6">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-cyan-200 bg-cyan-50 text-cyan-700 shadow-[var(--shadow-soft)]">
            <Building2 size={18} />
          </div>
          <div>
            <h2 className="text-xl font-black text-[var(--text-main)]">Importar operación completa</h2>
            <p className="text-sm leading-6 text-[var(--text-muted)]">
              Archivo XLSX con hojas constructora, etapas, obras, registros, factores y evidencias de obra.
            </p>
          </div>
        </div>

        <div className="flex w-full flex-col gap-2 sm:flex-row lg:w-fit">
          <a
            href={getPlantillaImportacionConstruccionUrl()}
            className="premium-button premium-button-secondary inline-flex items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-bold"
          >
            <Download size={18} />
            Descargar plantilla
          </a>
          <label className="premium-button premium-button-secondary inline-flex cursor-pointer items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-bold">
            {state.loading ? <Loader2 className="animate-spin" size={18} /> : <Upload size={18} />}
            {state.loading ? "Previsualizando" : "Cargar archivo"}
            <input
              type="file"
              accept=".xlsx"
              disabled={state.loading || state.saving}
              onChange={onPreview}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {state.fileName && (
        <p className="mb-4 text-sm text-[var(--text-muted)]">
          Archivo: <span className="font-bold text-[var(--text-main)]">{state.fileName}</span>
        </p>
      )}

      {state.error && (
        <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
          {state.error}
        </div>
      )}

      {state.savedMessage && (
        <div className="mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-700">
          {state.savedMessage}
        </div>
      )}

      {state.result && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">
            <CompleteSummaryCard
              label="Constructora"
              value={state.result?.constructora?.status === "valid" ? "Lista" : "Revisar"}
            />
            <CompleteSummaryCard label="Etapas" value={formatNumber(state.result?.etapas?.total || 0, 0)} />
            <CompleteSummaryCard label="Obras" value={formatNumber(state.result?.obras?.total || 0, 0)} />
            <CompleteSummaryCard label="Registros" value={formatNumber(state.result?.registros_emision?.total || 0, 0)} />
            <CompleteSummaryCard label="Factores" value={formatNumber(state.result?.factores?.total || 0, 0)} />
          </div>

          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
            <h3 className="text-base font-black text-[var(--text-main)]">Datos de la constructora</h3>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {[
                ["nombre", "Nombre"],
                ["rut", "RUT"],
                ["region", "Región"],
                ["comuna", "Comuna"],
                ["direccion", "Dirección"],
                ["rubro", "Rubro"],
                ["email", "Email"],
                ["telefono", "Teléfono"],
                ["contacto", "Contacto"],
              ].map(([key, label]) => (
                <div key={key} className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-3 text-center">
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--text-muted)]">{label}</p>
                  <p className="mt-1 break-words text-sm font-black text-[var(--text-main)]">
                    {constructoraData[key] || "-"}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <CompleteSectionCheck title="Factores" section={state.result?.factores} />
            <CompleteSectionCheck title="Etapas" section={state.result?.etapas} />
            <CompleteSectionCheck title="Obras" section={state.result?.obras} />
            <CompleteSectionCheck title="Registros de emisión" section={state.result?.registros_emision} />
            <CompleteSectionCheck title="Evidencias" section={state.result?.evidencias} />
          </div>

          {blockingErrors.length > 0 && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
              {blockingErrors.join("; ")}
            </div>
          )}

          <button
            type="button"
            onClick={() => onConfirm(state.result?.batch_id)}
            disabled={!state.result?.batch_id || blockingErrors.length > 0 || sectionErrors > 0 || state.saving}
            className="premium-button premium-button-primary inline-flex w-full items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60 sm:w-fit"
          >
            {state.saving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
            Confirmar importación completa
          </button>
        </div>
      )}
    </section>
  );
}

function ImportacionesView({ onImportConfirmed }) {
  const [factors, setFactors] = useState(emptyImportState);
  const [units, setUnits] = useState(emptyImportState);
  const [obras, setObras] = useState(emptyImportState);
  const [constructoras, setConstructoras] = useState(emptyImportState);
  const [constructoraCompleta, setConstructoraCompleta] = useState(emptyImportState);
  const [registros, setRegistros] = useState(emptyImportState);
  const [toast, setToast] = useState(null);
  const [documentImportOpen, setDocumentImportOpen] = useState(false);
  const { activeConstructora, activeConstructoraId, refreshConstructoras } = useConstructoraActiva();
  const { invalidate: invalidateFactores } = useFactores();

  const showToast = (message) => {
    setToast({ id: Date.now(), message });
  };

  const previewFile = async (event, previewFn, setState) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setState({ ...emptyImportState, fileName: file.name, loading: true });

    try {
      const result = await previewFn(file);
      setState((current) => ({ ...current, loading: false, result }));
    } catch (requestError) {
      const resp = requestError.response?.data || {};
      setState((current) => ({
        ...current,
        loading: false,
        result: resp.result || (resp.rows ? { rows: resp.rows, summary: resp.summary || {} } : null),
        error: resp.error || resp.detail || "No se pudo previsualizar el archivo.",
      }));
    } finally {
      event.target.value = "";
    }
  };

  const confirmRows = async (rows, confirmFn, setState, batchId = null, onSuccess = null) => {
    setState((current) => ({ ...current, saving: true, error: "", savedMessage: "" }));

    try {
      const payload = batchId ? { batch_id: batchId } : { rows };
      const result = await confirmFn(payload);
      const createdCount = result.creados ?? result.created ?? 0;
      const updatedCount = result.actualizados ?? 0;
      const rejectedCount = result.rechazados ?? 0;
      const message = `${formatNumber(createdCount, 0)} creados, ${formatNumber(updatedCount, 0)} actualizados, ${formatNumber(rejectedCount, 0)} rechazados.`;

      if (typeof onSuccess === "function") {
        onSuccess();
      }

      await refreshConstructoras().catch(() => undefined);
      await onImportConfirmed?.();
      showToast(message);

      setState((current) => ({ ...current, saving: false, savedMessage: message }));
    } catch (requestError) {
      setState((current) => ({
        ...current,
        saving: false,
        error: requestError.response?.data?.error || requestError.response?.data?.detail || "No se pudo guardar.",
      }));
    }
  };

  const confirmConstructoraCompleta = async (batchId) => {
    if (!batchId) {
      setConstructoraCompleta((current) => ({ ...current, error: "Falta batch_id para confirmar la importación." }));
      return;
    }

    setConstructoraCompleta((current) => ({ ...current, saving: true, error: "", savedMessage: "" }));

    try {
      const result = await confirmarImportacionCompletaConstruccion({ batch_id: batchId });
      const message = "Archivo importado correctamente. Los datos fueron agregados a la constructora.";

      await refreshConstructoras().catch(() => undefined);
      await onImportConfirmed?.();
      showToast(message);

      setConstructoraCompleta((current) => ({
        ...current,
        saving: false,
        savedMessage: message,
        result: {
          ...current.result,
          errores: result.errores || [],
          etapas_creadas: result.etapas_creadas || 0,
          obras_creados: result.obras_creados || 0,
          registros_emision_creadas: result.registros_emision_creadas || 0,
          factores_creados: result.factores_creados || 0,
          evidencias_creadas: result.evidencias_creadas || 0,
        },
      }));
    } catch (requestError) {
      setConstructoraCompleta((current) => ({
        ...current,
        saving: false,
        error: requestError.response?.data?.error || requestError.response?.data?.detail || "Error al confirmar la importación completa.",
      }));
    }
  };

  if (!activeConstructora) {
    return (
      <div className="mx-auto max-w-7xl">
        <EmptyState
          title="Selecciona o crea una constructora para comenzar"
          description="Las importaciones operan dentro del contexto de la constructora activa."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <Toast message={toast?.message} onClose={() => setToast(null)} toastKey={toast?.id} />

      <header className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-3 text-[var(--primary-dark)] shadow-[var(--shadow-soft)]">
            <DatabaseZap />
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tight text-[var(--text-main)] sm:text-4xl">Importaciones</h1>
            <p className="text-[var(--text-muted)]">
              Carga masiva de datos de obra para mantener actualizada la gestión ambiental de {activeConstructora.nombre}.
            </p>
          </div>
        </div>
      </header>

      <section className="rounded-3xl border border-cyan-200 bg-cyan-50 p-4 text-sm font-semibold leading-6 text-cyan-800 sm:p-5">
        Para evitar errores de relación entre datos, importa en este orden: constructoras, factores de emisión, etapas, obras y registros. También puedes usar la plantilla completa para cargar todo en un solo archivo XLSX.
      </section>

      <section className="rounded-3xl border border-[#B7DEC9] bg-[var(--success-bg)] p-5 shadow-[0_18px_45px_var(--shadow)] sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.18em] text-[var(--primary-dark)]">Flujo inteligente</p>
            <h2 className="mt-2 text-2xl font-black text-[var(--text-main)]">Importar evidencia de obra</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[#344054]">
              Analiza una evidencia, revisa la lectura sugerida y confirma manualmente antes de crear el registro de emisión.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setDocumentImportOpen(true)}
            className="inline-flex items-center justify-center rounded-2xl border border-[var(--primary-dark)] bg-[var(--primary-dark)] px-5 py-3 text-sm font-bold text-white transition hover:bg-[var(--primary-dark-hover)]"
          >
            Importar evidencia de obra
          </button>
        </div>
      </section>

      <ConstructoraCompletaImportPanel
        state={constructoraCompleta}
        onPreview={(event) => previewFile(event, previewImportacionCompletaConstruccion, setConstructoraCompleta)}
        onConfirm={confirmConstructoraCompleta}
      />

      <ImportPanel
        title="Importar constructoras"
        icon={<Building2 size={18} />}
        columns={["ID constructora", "Nombre", "RUT", "Región", "Comuna", "Dirección", "Rubro", "Email", "Teléfono", "Contacto", "Observaciones"]}
        state={constructoras}
        type="constructoras"
        summaryLabels={companySummaryLabels}
        onPreview={(event) => previewFile(event, previewImportConstructoras, setConstructoras)}
        onConfirm={(rows, batchId) => confirmRows(rows, confirmarImportConstructoras, setConstructoras, batchId)}
      />

      <ImportPanel
        title="Importar factores de emisión"
        icon={<FileSpreadsheet size={18} />}
        columns={["Fuente de emisión", "Categoría", "Unidad", "Factor de Emisión", "Fuente", "Año", "Observaciones"]}
        state={factors}
        type="factors"
        summaryLabels={factorSummaryLabels}
        onPreview={(event) => previewFile(event, previewImportFactores, setFactors)}
        onConfirm={(rows, batchId) => confirmRows(rows, confirmarImportFactores, setFactors, batchId, invalidateFactores)}
      />

      <ImportPanel
        title="Importar etapas"
        icon={<Factory size={18} />}
        columns={["ID Etapa", "ID constructora", "Nombre", "Tipo", "Región", "Comuna", "Dirección", "Estado"]}
        state={units}
        type="etapas"
        summaryLabels={unitSummaryLabels}
        onPreview={(event) => previewFile(event, (file) => previewImportEtapasForConstructora(activeConstructoraId, file), setUnits)}
        onConfirm={(rows, batchId) =>
          confirmRows(rows, (payload) => confirmarImportEtapasForConstructora(activeConstructoraId, payload), setUnits, batchId)
        }
      />

      <ImportPanel
        title="Importar obras"
        icon={<Boxes size={18} />}
        columns={["Código de obra", "ID Etapa", "Fecha", "Material / tipo de obra", "Cantidad base", "Ubicación / origen"]}
        state={obras}
        type="obras"
        summaryLabels={obraSummaryLabels}
        onPreview={(event) => previewFile(event, (file) => previewImportObrasForConstructora(activeConstructoraId, file), setObras)}
        onConfirm={(rows, batchId) =>
          confirmRows(rows, (payload) => confirmarImportObrasForConstructora(activeConstructoraId, payload), setObras, batchId)
        }
      />

      <ImportPanel
        title="Importar registros de emisión"
        icon={<DatabaseZap size={18} />}
        columns={["ID Registro", "Código de obra", "ID Etapa", "Fuente", "Categoría", "Cantidad", "Unidad", "Factor", "Fecha", "Observación"]}
        state={registros}
        type="registros"
        summaryLabels={registroSummaryLabels}
        onPreview={(event) => previewFile(event, (file) => previewRegistroEmisionImportForConstructora(activeConstructoraId, file), setRegistros)}
        onConfirm={(rows, batchId) =>
          confirmRows(rows, (payload) => confirmRegistroEmisionImportForConstructora(activeConstructoraId, payload), setRegistros, batchId)
        }
      />

      <ImportarEvidenciaObraModal
        activeConstructoraId={activeConstructoraId}
        initialTitle="Importar evidencia de obra"
        onClose={() => setDocumentImportOpen(false)}
        open={documentImportOpen}
      />
    </div>
  );
}

export default ImportacionesView;
