import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, FileText, Loader2, UploadCloud, X } from "lucide-react";

import Modal from "@/shared/components/Modal";
import {
  createRegistroEmision,
  extractDocumentJson,
  extractDocumentJsonById,
  extractDocumentText,
  extractDocumentTextById,
  getOrganizacionObras,
  getFactoresEmision,
  uploadObraEvidencia,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import { inferDocumentImportSuggestion } from "@/shared/utils/documentImportRules";

function toFileName(value) {
  return String(value || "evidencia").split(/[\\/]/).pop() || "evidencia";
}

async function downloadFileAsFile(fileUrl, fileName) {
  const response = await fetch(fileUrl, { credentials: "include" });

  if (!response.ok) {
    throw new Error("No se pudo descargar el evidencia para analizarlo.");
  }

  const blob = await response.blob();
  const inferredName = toFileName(fileName || fileUrl);
  return new File([blob], inferredName, { type: blob.type || response.headers.get("content-type") || "application/octet-stream" });
}

function FieldLabel({ children }) {
  return <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--text-muted)]">{children}</p>;
}

function ImportarEvidenciaObraModal({
  activeOrganizacionId,
  archivoNombre = "",
  archivoUrl = "",
  evidenciaId = "",
  initialObraId = "",
  initialTitle = "Importar evidencia de obra",
  onClose,
  onCreatedEmission,
  onEvidenceSaved,
  open,
}) {
  const [obras, setObras] = useState([]);
  const [factors, setFactors] = useState([]);
  const [selectedObraCodigo, setSelectedObraId] = useState(initialObraId || "");
  const [documentType, setDocumentType] = useState("guia_despacho");
  const [documentDate, setDocumentDate] = useState("");
  const [file, setFile] = useState(null);
  const [resolvedFile, setResolvedFile] = useState(null);
  const [sourceLabel, setSourceLabel] = useState(archivoNombre || "");
  const [loadingCatalogs, setLoadingCatalogs] = useState(false);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [savingEvidence, setSavingEvidence] = useState(false);
  const [savingEmission, setSavingEmission] = useState(false);
  const [error, setError] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [draft, setDraft] = useState({
    source: "",
    category: "Otros",
    quantity: "",
    unit: "",
    factorEmision: "",
    factorEmisionId: "",
    estimatedEmissions: "",
  });

  useEffect(() => {
    if (!open || !activeOrganizacionId) {
      return;
    }

    let cancelled = false;

    async function loadCatalogs() {
      try {
        setLoadingCatalogs(true);
        const [obrasData, factorsData] = await Promise.all([getOrganizacionObras(activeOrganizacionId), getFactoresEmision()]);

        if (cancelled) {
          return;
        }

        setObras(Array.isArray(obrasData) ? obrasData : []);
        setFactors(Array.isArray(factorsData) ? factorsData : []);
        setSelectedObraId((current) => current || initialObraId || (Array.isArray(obrasData) && obrasData[0]?.codigo_obra ? String(obrasData[0].codigo_obra) : ""));
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError?.response?.data?.error || "No se pudo cargar el catalogo de obras o factores.");
        }
      } finally {
        if (!cancelled) {
          setLoadingCatalogs(false);
        }
      }
    }

    loadCatalogs();

    return () => {
      cancelled = true;
    };
  }, [activeOrganizacionId, initialObraId, open]);

  useEffect(() => {
    if (!open) {
      return;
    }

    setError("");
    setLoadingAnalysis(false);
    setSavingEvidence(false);
    setSavingEmission(false);
    setAnalysis(null);
    setResolvedFile(null);
    setDocumentType("guia_despacho");
    setDocumentDate("");
    setFile(null);
    setSourceLabel(archivoNombre || "");
    setDraft({
      source: "",
      category: "Otros",
      quantity: "",
      unit: "",
      factorEmision: "",
      factorEmisionId: "",
      estimatedEmissions: "",
    });
    setSelectedObraId(initialObraId || "");
  }, [archivoNombre, initialObraId, open]);

  const selectedObra = useMemo(
    () => obras.find((item) => String(item.codigo_obra) === String(selectedObraCodigo)) || null,
    [obras, selectedObraCodigo]
  );

  const factorOptions = useMemo(() => analysis?.emission?.factorSuggestions || factors.slice(0, 3), [analysis, factors]);

  const isExistingSource = Boolean(evidenciaId || archivoUrl);

  async function resolveSourceFile() {
    if (file) {
      return file;
    }

    if (archivoUrl) {
      const downloadedFile = await downloadFileAsFile(archivoUrl, archivoNombre || sourceLabel || archivoUrl);
      setResolvedFile(downloadedFile);
      return downloadedFile;
    }

    return null;
  }

  function buildStructuredPayload(textResult, jsonResult) {
    const structured = jsonResult?.datos_sugeridos || jsonResult?.data || jsonResult || {};
    const text = textResult?.texto_extraido || textResult?.texto || textResult?.text || "";
    const suggestion = inferDocumentImportSuggestion({
      text,
      structured,
      fileName: file?.name || archivoNombre || sourceLabel || toFileName(archivoUrl || evidenciaId || "evidencia"),
      factors,
    });

    setAnalysis({
      ...suggestion,
      structured,
      text,
    });
    setDraft({
      source: suggestion.emission.source || "",
      category: suggestion.emission.category || "Otros",
      quantity: suggestion.emission.quantity || "",
      unit: suggestion.emission.unit || "",
      factorEmision: suggestion.emission.factorEmision || "",
      factorEmisionId: String(suggestion.emission.factorEmisionId || ""),
      estimatedEmissions: suggestion.emission.estimatedEmissions || "",
    });
    setDocumentDate(structured?.fecha || suggestion.document?.date || documentDate || "");
    setSourceLabel(file?.name || archivoNombre || sourceLabel || suggestion.document?.fileName || "");
  }

  async function runAnalysis(sourceFileOverride = null) {
    try {
      setLoadingAnalysis(true);
      setError("");

      if (evidenciaId) {
        const [textResult, jsonResult] = await Promise.all([
          extractDocumentTextById(evidenciaId),
          extractDocumentJsonById(evidenciaId),
        ]);
        buildStructuredPayload(textResult, jsonResult);
        return;
      }

      const sourceFile = sourceFileOverride || (await resolveSourceFile());

      if (!sourceFile) {
        if (!file) {
          throw new Error("Carga un archivo o selecciona un evidencia existente para iniciar el analisis.");
        }
        throw new Error("No se pudo resolver el archivo a analizar.");
      }

      const [textResult, jsonResult] = await Promise.all([
        extractDocumentText({ file: sourceFile }),
        extractDocumentJson({ file: sourceFile }),
      ]);
      buildStructuredPayload(textResult, jsonResult);
    } catch (analysisError) {
      setError(analysisError?.response?.data?.error || analysisError?.message || "No se pudo analizar el evidencia.");
    } finally {
      setLoadingAnalysis(false);
    }
  }

  async function handleFileChange(event) {
    const nextFile = event.target.files?.[0] || null;
    setFile(nextFile);
    setResolvedFile(nextFile);
    setSourceLabel(nextFile?.name || "");
    setAnalysis(null);
    setError("");
    if (nextFile) {
      runAnalysis(nextFile);
    }
  }

  useEffect(() => {
    if (!open || loadingCatalogs || analysis || (!evidenciaId && !archivoUrl)) {
      return;
    }

    runAnalysis();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, evidenciaId, archivoUrl, loadingCatalogs]);

  async function handleSaveEvidence() {
    try {
      if (!selectedObraCodigo) {
        throw new Error("Selecciona una obra para guardar la evidencia.");
      }

      const sourceFile = resolvedFile || file;
      if (!sourceFile) {
        throw new Error("Este evidencia no tiene archivo descargable para guardarlo como evidencia.");
      }

      if (!documentDate) {
        throw new Error("Indica la fecha del evidencia antes de guardar la evidencia.");
      }

      setSavingEvidence(true);
      setError("");
      await uploadObraEvidencia(selectedObraCodigo, {
        tipo_evidencia: documentType,
        fecha: documentDate,
        archivo: sourceFile,
      });

      onEvidenceSaved?.({ obraId: selectedObraCodigo, fileName: sourceFile.name, documentType, documentDate });
      onClose?.();
    } catch (saveError) {
      setError(saveError?.response?.data?.error || saveError?.message || "No se pudo guardar la evidencia.");
    } finally {
      setSavingEvidence(false);
    }
  }

  async function handleCreateEmission() {
    try {
      if (!selectedObraCodigo) {
        throw new Error("Selecciona una obra para crear el registro.");
      }

      if (!draft.quantity) {
        throw new Error("Indica una cantidad antes de confirmar el registro.");
      }

      if (!draft.factorEmisionId && !draft.factorEmision) {
        throw new Error("Selecciona un factor sugerido o ingresa un factor manual antes de confirmar.");
      }

      setSavingEmission(true);
      setError("");

      const payload = {
        fuente_emision: draft.source || draft.source || "Evidencia importado",
        cantidad: draft.quantity,
        unidad: draft.unit || "unidad",
        fecha: documentDate || new Date().toISOString().slice(0, 10),
      };

      if (draft.factorEmisionId) {
        payload.factor_emision_id = draft.factorEmisionId;
      } else if (draft.factorEmision) {
        payload.factor_emision = draft.factorEmision;
      }

      const result = await createRegistroEmision(selectedObraCodigo, payload);
      onCreatedEmission?.(result);
      onClose?.();
    } catch (saveError) {
      setError(saveError?.response?.data?.error || saveError?.message || "No se pudo crear el registro de emission.");
    } finally {
      setSavingEmission(false);
    }
  }

  if (!open) {
    return null;
  }

  return (
    <Modal onClose={onClose}>
      <div className="flex items-start justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div className="flex items-start gap-4">
          <div className="rounded-2xl border border-[#B7DEC9] bg-[var(--success-bg)] p-3 text-[var(--primary-dark)]">
            <FileText size={24} />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--primary-dark)]">Importación inteligente</p>
            <h2 className="mt-1 text-2xl font-bold text-[var(--text-main)]">{initialTitle}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-muted)]">
              Extrae texto del evidencia, sugiere la lectura de obra y confirma manualmente antes de guardar.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] text-[var(--text-muted)] transition hover:text-[var(--text-main)]"
          aria-label="Cerrar importacion"
        >
          <X size={18} />
        </button>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="space-y-4 rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 sm:p-5">
          <div>
            <FieldLabel>Origen del evidencia</FieldLabel>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-[var(--text-muted)]">
              <span className="rounded-full border border-[var(--border)] bg-[var(--bg-card)] px-3 py-1 font-semibold text-[var(--text-main)]">
                {sourceLabel || (evidenciaId ? `Evidencia ${evidenciaId}` : archivoUrl ? "Evidencia vinculada" : "Archivo nuevo")}
              </span>
              <span className="rounded-full border border-[var(--border)] bg-[var(--bg-card)] px-3 py-1 font-semibold text-[var(--text-main)]">
                {analysis?.review?.confidence ? `Confianza ${analysis.review.confidence}` : "Pendiente de analisis"}
              </span>
              {isExistingSource ? (
                <span className="rounded-full border border-[#B9D8D3] bg-[var(--info-bg)] px-3 py-1 font-semibold text-[#075985]">
                  Evidencia existente
                </span>
              ) : null}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-2 text-sm font-semibold text-[var(--text-main)]">
              <span>Obra destino</span>
              <select
                value={selectedObraCodigo}
                onChange={(event) => setSelectedObraId(event.target.value)}
                className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 text-sm text-[var(--text-main)] outline-none transition focus:border-[var(--primary-dark)]"
              >
                <option value="">Selecciona una obra</option>
                {obras.map((item) => (
                  <option key={item.codigo_obra} value={item.codigo_obra}>
                    {item.codigo_obra} - {item.organizacion_nombre || item.origen || "Obra"}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-2 text-sm font-semibold text-[var(--text-main)]">
              <span>Tipo de evidencia</span>
              <select
                value={documentType}
                onChange={(event) => setDocumentType(event.target.value)}
                className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 text-sm text-[var(--text-main)] outline-none transition focus:border-[var(--primary-dark)]"
              >
                <option value="guia_despacho">Guia de despacho</option>
                <option value="factura">Factura</option>
                <option value="orden_compra">Orden de compra</option>
                <option value="certificado">Certificado</option>
                <option value="otro">Otro respaldo</option>
              </select>
            </label>

            <label className="space-y-2 text-sm font-semibold text-[var(--text-main)]">
              <span>Fecha del evidencia</span>
              <input
                type="date"
                value={documentDate}
                onChange={(event) => setDocumentDate(event.target.value)}
                className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 text-sm text-[var(--text-main)] outline-none transition focus:border-[var(--primary-dark)]"
              />
            </label>

            <label className="space-y-2 text-sm font-semibold text-[var(--text-main)]">
              <span>Archivo</span>
              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.txt"
                onChange={handleFileChange}
                className="block w-full text-sm text-[var(--text-muted)] file:mr-4 file:rounded-2xl file:border-0 file:bg-[var(--primary-dark)] file:px-4 file:py-2 file:text-sm file:font-bold file:text-white hover:file:bg-[var(--primary-dark-hover)]"
              />
            </label>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={runAnalysis}
              disabled={loadingAnalysis || (!file && !evidenciaId && !archivoUrl)}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[var(--primary-dark)] bg-[var(--primary-dark)] px-4 py-3 text-sm font-bold text-white transition hover:bg-[var(--primary-dark-hover)] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loadingAnalysis ? <Loader2 className="animate-spin" size={18} /> : <UploadCloud size={18} />}
              {loadingAnalysis ? "Analizando" : "Analizar evidencia"}
            </button>
            <button
              type="button"
              onClick={handleSaveEvidence}
              disabled={savingEvidence || loadingAnalysis}
              className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 text-sm font-bold text-[var(--text-main)] transition hover:bg-[var(--bg-surface)] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {savingEvidence ? "Guardando..." : "Guardar solo evidencia"}
            </button>
            <button
              type="button"
              onClick={handleCreateEmission}
              disabled={savingEmission || loadingAnalysis}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[#B7DEC9] bg-[var(--success-bg)] px-4 py-3 text-sm font-bold text-[var(--primary-dark)] transition hover:bg-[#DFF3E6] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {savingEmission ? <Loader2 className="animate-spin" size={18} /> : <CheckCircle2 size={18} />}
              {savingEmission ? "Confirmando" : "Confirmar y crear registro"}
            </button>
          </div>

          {error ? (
            <p className="rounded-2xl border border-[#F1B8B8] bg-[var(--danger-bg)] p-3 text-sm font-semibold text-[#B42318]">
              {error}
            </p>
          ) : null}

          <div className="rounded-3xl border border-[#B9D8D3] bg-[var(--info-bg)] p-4">
            <p className="text-sm font-semibold text-[#075985]">
              {analysis?.review?.note || "La importacion inteligente muestra una lectura preliminar y no guarda nada hasta que confirmes."}
            </p>
            <p className="mt-2 text-xs text-[#075985]/80">
              Si el evidencia no se lee bien, puedes guardar la evidencia y completar el registro manualmente.
            </p>
          </div>
        </section>

        <section className="space-y-4 rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 sm:p-5">
          <div>
            <FieldLabel>Lectura sugerida</FieldLabel>
            <h3 className="mt-2 text-xl font-bold text-[var(--text-main)]">Resumen del evidencia</h3>
            <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
              Usa esta vista para validar categoria, cantidad, unidad y factor antes de crear el registro.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-2 text-sm font-semibold text-[var(--text-main)]">
              <span>Categoria</span>
              <input
                value={draft.category}
                onChange={(event) => setDraft((current) => ({ ...current, category: event.target.value }))}
                className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] outline-none"
              />
            </label>
            <label className="space-y-2 text-sm font-semibold text-[var(--text-main)]">
              <span>Fuente / fuente_emision</span>
              <input
                value={draft.source}
                onChange={(event) => setDraft((current) => ({ ...current, source: event.target.value }))}
                className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] outline-none"
              />
            </label>
            <label className="space-y-2 text-sm font-semibold text-[var(--text-main)]">
              <span>Cantidad</span>
              <input
                value={draft.quantity}
                onChange={(event) => setDraft((current) => ({ ...current, quantity: event.target.value }))}
                className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] outline-none"
              />
            </label>
            <label className="space-y-2 text-sm font-semibold text-[var(--text-main)]">
              <span>Etapa</span>
              <input
                value={draft.unit}
                onChange={(event) => setDraft((current) => ({ ...current, unit: event.target.value }))}
                className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] outline-none"
              />
            </label>
          </div>

          <label className="space-y-2 text-sm font-semibold text-[var(--text-main)]">
            <span>Factor sugerido</span>
            <select
              value={draft.factorEmisionId || "manual"}
              onChange={(event) => {
                const selected = factorOptions.find((item) => String(item.id || item.factor_emision_id) === event.target.value);
                setDraft((current) => ({
                  ...current,
                  factorEmisionId: selected ? String(selected.id || selected.factor_emision_id || "") : "",
                  factorEmision: selected ? String(selected.factor_emision || "") : current.factorEmision,
                }));
              }}
              className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] outline-none"
            >
              <option value="manual">Factor manual</option>
              {factorOptions.map((item) => (
                <option key={item.id || item.factor_emision_id || item.label} value={item.id || item.factor_emision_id}>
                  {item.label || item.fuente_emision} {item.unidad ? `| ${item.unidad}` : ""}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-2 text-sm font-semibold text-[var(--text-main)]">
            <span>Factor numérico</span>
            <input
              type="number"
              step="any"
              value={draft.factorEmision}
              onChange={(event) => setDraft((current) => ({ ...current, factorEmision: event.target.value, factorEmisionId: "" }))}
              className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] outline-none"
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--text-muted)]">Factor elegido</p>
              <p className="mt-2 text-sm font-semibold text-[var(--text-main)]">
                {analysis?.emission?.factorLabel || draft.factorEmisionId || "Sin factor sugerido"}
              </p>
            </div>
            <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--text-muted)]">Emisiones estimadas</p>
              <p className="mt-2 text-sm font-semibold text-[var(--text-main)]">
                {draft.estimatedEmissions ? `${formatNumber(Number(draft.estimatedEmissions), 3)} kg CO2e` : "Pendiente de factor y cantidad"}
              </p>
            </div>
          </div>

          <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--text-muted)]">Texto extraido</p>
            <p className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap text-sm leading-6 text-[var(--text-main)]">
              {analysis?.text || "Aun no se analizo el evidencia."}
            </p>
          </div>

          <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--text-muted)]">Contexto de obra</p>
            <p className="mt-2 text-sm text-[var(--text-main)]">
              {selectedObra ? `${selectedObra.codigo_obra} · ${selectedObra.organizacion_nombre || selectedObra.origen || "Obra"}` : "Selecciona una obra destino para continuar."}
            </p>
            {loadingCatalogs ? <p className="mt-2 text-xs text-[var(--text-muted)]">Cargando catalogo de obras y factores...</p> : null}
          </div>
        </section>
      </div>
    </Modal>
  );
}

export default ImportarEvidenciaObraModal;
