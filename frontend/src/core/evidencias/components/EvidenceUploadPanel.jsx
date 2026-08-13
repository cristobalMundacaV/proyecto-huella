import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, BrainCircuit, CheckCircle2, FileSearch, UploadCloud } from "lucide-react";

import { extraerEvidenciaDocumento } from "@/shared/services/api";

function buildInitialMetadata(fields) {
  return Object.fromEntries(fields.map((field) => [field.key, ""]));
}

function findEvidenceType(evidenceTypes, documentType, fallback) {
  return (
    evidenceTypes.find((type) => type.key === documentType) ||
    evidenceTypes.find((type) => type.backendType === documentType) ||
    evidenceTypes.find((type) => type.key === fallback) ||
    evidenceTypes[0]
  );
}

function buildPreviewUrl(file) {
  if (!file) return "";

  const isPreviewable =
    file.type?.startsWith("image/") ||
    file.type === "application/pdf" ||
    file.type?.startsWith("text/");

  return isPreviewable ? URL.createObjectURL(file) : "";
}

function EvidenceUploadPanel({ config, organizacionId, lotesForestales = [], onSubmit, presetKey = "", records = [], saving }) {
  const evidenceTypes = [...config.requiredEvidenceTypes, ...config.optionalEvidenceTypes];
  const metadataFields = config.getUploadMetadataFields();
  const initialMetadata = useMemo(() => buildInitialMetadata(metadataFields), [metadataFields]);

  const [form, setForm] = useState({
    nombre: "",
    evidenceType: evidenceTypes[0]?.key || "otro",
    fecha_documento: "",
    archivo: null,
    lote_id: "",
    lote_forestal: "",
    registro_emision: "",
    estado_documental: "pendiente",
    observaciones: "",
    metadata: initialMetadata,
  });
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");

  const selectedType = evidenceTypes.find((item) => item.key === form.evidenceType) || evidenceTypes[0];

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function updateMetadata(key, value) {
    setForm((current) => ({
      ...current,
      metadata: {
        ...current.metadata,
        [key]: value,
      },
    }));
  }

  function applyAnalysis(result, file) {
    const suggestedType = findEvidenceType(evidenceTypes, result.tipo_documento, form.evidenceType);

    setForm((current) => ({
      ...current,
      nombre:
        current.nombre ||
        result.tipo_documento_label ||
        file?.name ||
        "Evidencia ambiental",
      evidenceType: suggestedType?.key || current.evidenceType,
      fecha_documento: current.fecha_documento || result.fecha || "",
      estado_documental: result.campos_faltantes?.length ? "observada" : "pendiente",
      observaciones:
        current.observaciones ||
        [
          result.proveedor ? `Proveedor detectado: ${result.proveedor}` : "",
          result.fuente_emision_sugerida
            ? `Fuente sugerida: ${result.fuente_emision_sugerida}`
            : "",
          result.cantidad_sugerida
            ? `Cantidad sugerida: ${result.cantidad_sugerida} ${result.unidad_sugerida}`
            : "",
        ]
          .filter(Boolean)
          .join("\n"),
      metadata: {
        ...current.metadata,
        document_type: result.tipo_documento,
        document_type_label: result.tipo_documento_label,
        proveedor: result.proveedor || "",
        categoria_sugerida: result.categoria_sugerida || "",
        fuente_emision_sugerida: result.fuente_emision_sugerida || "",
        cantidad_sugerida: result.cantidad_sugerida || "",
        unidad_sugerida: result.unidad_sugerida || "",
        factor_sugerido: result.factor_sugerido || "",
        confianza_extraccion: result.confianza ?? "",
        campos_faltantes: result.campos_faltantes || [],
        extraction_engine: result.metadata?.extraction_engine || "heuristic_v1",
        requires_human_review: Boolean(result.metadata?.requires_human_review),
      },
    }));
  }

  async function handleFileChange(event) {
    const file = event.target.files?.[0] || null;

    setForm((current) => ({ ...current, archivo: file }));
    setAnalysis(null);
    setAnalysisError("");

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    setPreviewUrl(buildPreviewUrl(file));

    if (!file || !organizacionId) return;

    try {
      setAnalyzing(true);
      const result = await extraerEvidenciaDocumento(organizacionId, file);
      setAnalysis(result);
      applyAnalysis(result, file);
    } catch (requestError) {
      setAnalysisError(
        requestError.response?.data?.error ||
        "No se pudo analizar automáticamente el documento. Puedes completar los datos manualmente."
      );
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();

    await onSubmit({
      ...form,
      selectedType,
      metadata: {
        ...form.metadata,
        extraction_result: analysis || null,
      },
    });

    setForm({
      nombre: "",
      evidenceType: evidenceTypes[0]?.key || "otro",
      fecha_documento: "",
      archivo: null,
      lote_id: "",
      lote_forestal: "",
      registro_emision: "",
      estado_documental: "pendiente",
      observaciones: "",
      metadata: initialMetadata,
    });
    setAnalysis(null);
    setAnalysisError("");

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl("");
    }

    event.currentTarget.reset();
  }

  const inputClass =
    "w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-center text-sm text-[var(--text-main)] outline-none transition focus:border-emerald-300 focus:ring-4 focus:ring-emerald-100";

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-[32px] border border-emerald-200/70 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_34%),linear-gradient(135deg,rgba(236,253,245,0.96),rgba(255,255,255,0.98))] p-5 shadow-[0_24px_70px_rgba(15,118,110,0.12)] ring-1 ring-white/80"
    >
      <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
            Evidencia inteligente
          </p>
          <h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">
            Subir y analizar documento
          </h2>
          <p className="mt-2 max-w-2xl text-sm font-semibold leading-6 text-[var(--text-muted)]">
            El sistema intenta identificar el tipo de documento, extraer datos clave y completar el formulario automáticamente.
          </p>
        </div>

        <div className="rounded-2xl border border-emerald-200 bg-white/80 px-4 py-3 text-center shadow-[0_12px_28px_rgba(15,118,110,0.08)]">
          <BrainCircuit className="mx-auto text-emerald-700" size={22} />
          <p className="mt-1 text-xs font-black uppercase tracking-wide text-emerald-700">
            Heurística v1
          </p>
        </div>
      </div>

      <div className="mb-5 rounded-3xl border border-dashed border-emerald-300/70 bg-white/70 p-4">
        <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl bg-emerald-50/70 px-5 py-6 text-center transition hover:bg-emerald-50">
          <UploadCloud className="text-emerald-700" size={32} />
          <span className="mt-2 text-sm font-black text-[var(--text-main)]">
            Seleccionar documento ambiental
          </span>
          <span className="mt-1 text-xs font-semibold text-[var(--text-muted)]">
            PDF, imagen, TXT, CSV, XML u otro respaldo documental
          </span>
          <input
            type="file"
            className="hidden"
            onChange={handleFileChange}
            required
          />
        </label>

        {form.archivo ? (
          <div className="mt-3 rounded-2xl border border-emerald-200 bg-white p-3 text-center text-sm font-bold text-emerald-800">
            Archivo seleccionado: {form.archivo.name}
          </div>
        ) : null}

        {analyzing ? (
          <p className="mt-3 rounded-2xl border border-sky-200 bg-sky-50 p-3 text-center text-sm font-bold text-sky-800">
            Analizando documento...
          </p>
        ) : null}

        {analysisError ? (
          <p className="mt-3 rounded-2xl border border-amber-200 bg-amber-50 p-3 text-center text-sm font-bold text-amber-800">
            {analysisError}
          </p>
        ) : null}
      </div>

      {analysis ? (
        <DocumentAnalysisPanel analysis={analysis} />
      ) : null}

      {previewUrl ? (
        <DocumentPreview file={form.archivo} previewUrl={previewUrl} />
      ) : null}

      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2">
        <input
          className={inputClass}
          placeholder="Nombre de la evidencia"
          value={form.nombre}
          onChange={(event) =>
            setForm((current) => ({ ...current, nombre: event.target.value }))
          }
          required
        />

        <select
          className={inputClass}
          value={form.evidenceType}
          onChange={(event) =>
            setForm((current) => ({ ...current, evidenceType: event.target.value }))
          }
        >
          {evidenceTypes.map((type) => (
            <option key={type.key} value={type.key}>
              {type.label}
            </option>
          ))}
        </select>

        <input
          type="date"
          className={inputClass}
          value={form.fecha_documento}
          onChange={(event) =>
            setForm((current) => ({ ...current, fecha_documento: event.target.value }))
          }
        />

        <select
          className={inputClass}
          value={form.estado_documental}
          onChange={(event) =>
            setForm((current) => ({ ...current, estado_documental: event.target.value }))
          }
        >
          <option value="pendiente">Pendiente revisión</option>
          <option value="vinculada">Completa</option>
          <option value="observada">Incompleta</option>
          <option value="rechazada">Crítica</option>
          <option value="sin_vinculo">Sin vincular</option>
        </select>

        <select
          className={`${inputClass} md:col-span-2`}
          value={form.registro_emision}
          onChange={(event) =>
            setForm((current) => ({ ...current, registro_emision: event.target.value }))
          }
        >
          <option value="">Registro ambiental vinculado</option>
          {records.slice(0, 100).map((record) => (
            <option key={record.id} value={record.id}>
              #{record.id} - {record.fuente_emision || "Sin fuente"} ({record.fecha || "Sin fecha"})
            </option>
          ))}
        </select>

        {["forestal", "aserradero"].includes(presetKey) ? (
          <select
            className={`${inputClass} md:col-span-2`}
            value={form.lote_forestal}
            onChange={(event) => {
              const lote = lotesForestales.find((item) => String(item.id) === event.target.value);
              setForm((current) => ({
                ...current,
                lote_forestal: event.target.value,
                lote_id: lote?.lote_id || "",
                metadata: {
                  ...current.metadata,
                  lote: lote?.lote_id || current.metadata.lote || "",
                },
              }));
            }}
          >
            <option value="">Lote forestal vinculado</option>
            {lotesForestales.map((lote) => (
              <option key={lote.id} value={lote.id}>
                {lote.lote_id} - {lote.especie}
              </option>
            ))}
          </select>
        ) : null}

        {metadataFields.map((field) =>
          field.type === "select" ? (
            <select
              key={field.key}
              className={inputClass}
              value={form.metadata[field.key] || ""}
              onChange={(event) => updateMetadata(field.key, event.target.value)}
            >
              <option value="">{field.label}</option>
              {(field.options || []).map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          ) : (
            <input
              key={field.key}
              type={field.type || "text"}
              className={inputClass}
              placeholder={field.label}
              value={form.metadata[field.key] || ""}
              onChange={(event) => updateMetadata(field.key, event.target.value)}
            />
          )
        )}

        <textarea
          className={`${inputClass} min-h-28 resize-y md:col-span-2`}
          placeholder="Observaciones"
          value={form.observaciones}
          onChange={(event) =>
            setForm((current) => ({ ...current, observaciones: event.target.value }))
          }
        />
      </div>

      <button
        type="submit"
        disabled={saving || analyzing}
        className="mt-5 inline-flex items-center gap-2 rounded-2xl bg-[var(--primary-dark)] px-5 py-3 text-sm font-black text-white shadow-[0_16px_32px_rgba(14,124,102,0.22)] transition hover:-translate-y-px disabled:opacity-60"
      >
        <UploadCloud size={18} />
        {saving ? "Guardando..." : "Guardar evidencia"}
      </button>
    </form>
  );
}

function DocumentAnalysisPanel({ analysis }) {
  const confidence = Number(analysis.confianza || 0);
  const strong = confidence >= 0.75;

  return (
    <section className="mb-5 rounded-3xl border border-emerald-200 bg-white/85 p-4 shadow-[0_12px_28px_rgba(15,118,110,0.08)]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
            Resultado del análisis
          </p>
          <h3 className="mt-1 text-xl font-black text-[var(--text-main)]">
            {analysis.tipo_documento_label || "Documento ambiental"}
          </h3>
          <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
            Confianza: {Math.round(confidence * 100)}%
          </p>
        </div>

        <span
          className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-black ${strong
              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
              : "border-amber-200 bg-amber-50 text-amber-700"
            }`}
        >
          {strong ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
          {strong ? "Lectura confiable" : "Revisar manualmente"}
        </span>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <DetectedField label="Proveedor" value={analysis.proveedor} />
        <DetectedField label="Fecha" value={analysis.fecha} />
        <DetectedField label="Categoría sugerida" value={analysis.categoria_sugerida} />
        <DetectedField label="Fuente sugerida" value={analysis.fuente_emision_sugerida} />
        <DetectedField
          label="Cantidad sugerida"
          value={
            analysis.cantidad_sugerida
              ? `${analysis.cantidad_sugerida} ${analysis.unidad_sugerida || ""}`
              : ""
          }
        />
        <DetectedField
          label="Campos faltantes"
          value={analysis.campos_faltantes?.length ? analysis.campos_faltantes.join(", ") : "Sin faltantes críticos"}
        />
      </div>
    </section>
  );
}

function DetectedField({ label, value }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-3 text-center">
      <p className="text-[11px] font-black uppercase tracking-wide text-[var(--text-muted)]">
        {label}
      </p>
      <p className="mt-1 text-sm font-bold text-[var(--text-main)]">
        {value || "No detectado"}
      </p>
    </div>
  );
}

function DocumentPreview({ file, previewUrl }) {
  if (!previewUrl) return null;

  const isImage = file?.type?.startsWith("image/");
  const isPdf = file?.type === "application/pdf";

  return (
    <section className="mb-5 rounded-3xl border border-[var(--border)] bg-white/80 p-4 shadow-[0_12px_28px_rgba(15,23,42,0.06)]">
      <div className="mb-3 flex items-center gap-2">
        <FileSearch className="text-emerald-700" size={18} />
        <h3 className="text-sm font-black text-[var(--text-main)]">
          Previsualización del archivo
        </h3>
      </div>

      {isImage ? (
        <img
          src={previewUrl}
          alt="Previsualización del documento"
          className="max-h-[420px] w-full rounded-2xl object-contain"
        />
      ) : isPdf ? (
        <iframe
          src={previewUrl}
          title="Previsualización PDF"
          className="h-[420px] w-full rounded-2xl border border-[var(--border)]"
        />
      ) : (
        <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 text-center text-sm font-semibold text-[var(--text-muted)]">
          Este tipo de archivo no tiene previsualización embebida, pero será guardado como evidencia.
        </p>
      )}
    </section>
  );
}

export default EvidenceUploadPanel;
