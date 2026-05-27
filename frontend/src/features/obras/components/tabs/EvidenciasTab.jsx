import { useState } from "react";
import { FileText, Loader2, Plus, X } from "lucide-react";

import { formatNumber } from "@/shared/utils/formatters";
import {
  getConstructionEvidenceReviewLabel,
  getConstructionWorkDocumentTypeLabel,
} from "@/shared/utils/constructionEvidenceLabels";
import { DetailItem, Field } from "../common";
import { documentStatusTone, documentTypes, ocrFields } from "../constants";

function EvidenciasTab({
  activeExtraction,
  documentError,
  documentFieldErrors,
  documentForm,
  documentInsight,
  extractingDocumentId,
  ocrError,
  ocrForm,
  onDocumentSubmit,
  onRejectExtraction,
  onRunOcr,
  onRunStructuredExtraction,
  onUpdateDocumentForm,
  onUpdateOcrForm,
  onValidateExtraction,
  readingDocumentId,
  savingDocument,
  selectedObra,
  validatingExtraction,
}) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <section className="space-y-6">
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/80 p-4 backdrop-blur-sm">
      <form
        onSubmit={onDocumentSubmit}
            className="my-8 w-full max-w-2xl rounded-3xl border border-slate-800 bg-slate-900 p-4 shadow-2xl sm:p-6"
      >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-emerald-400/20 bg-emerald-400/10 text-emerald-300">
                  <FileText size={18} />
                </div>
                <div>
                  <h2 className="text-xl font-semibold">Subir evidencia</h2>
                  <p className="text-sm text-slate-400">{selectedObra.codigo_obra}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-slate-700 bg-slate-950 text-slate-300 transition hover:bg-slate-800"
                aria-label="Cerrar modal"
              >
                <X size={18} />
              </button>
          </div>

        <div className="grid grid-cols-1 gap-4">
          <Field
            label="Tipo de evidencia"
            error={documentFieldErrors.tipo_evidencia?.[0]}
          >
            <select
              name="tipo_evidencia"
              value={documentForm.tipo_evidencia}
              onChange={onUpdateDocumentForm}
              required
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
            >
              {documentTypes.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Fecha" error={documentFieldErrors.fecha?.[0]}>
            <input
              type="date"
              name="fecha"
              value={documentForm.fecha}
              onChange={onUpdateDocumentForm}
              required
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
            />
          </Field>

          <Field label="Archivo" error={documentFieldErrors.archivo?.[0]}>
            <input
              type="file"
              name="archivo"
              onChange={onUpdateDocumentForm}
              required
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 file:mr-4 file:rounded-xl file:border-0 file:bg-emerald-400/10 file:px-3 file:py-2 file:font-bold file:text-emerald-200"
            />
          </Field>
        </div>

        {documentError && (
          <p className="mt-4 text-sm text-red-300">{documentError}</p>
        )}

        <button
          type="submit"
          disabled={savingDocument}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200 transition hover:bg-emerald-400/20 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {savingDocument ? (
            <Loader2 className="animate-spin" size={18} />
          ) : (
            <FileText size={18} />
          )}
          Subir evidencia
        </button>
      </form>
        </div>
      )}

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Evidencias de obra</h2>
            <p className="mt-1 text-sm text-slate-400">{selectedObra.codigo_obra}</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm font-bold text-slate-200">
              {formatNumber(selectedObra.evidencias?.length || 0, 0)} evidencias
            </div>
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="flex items-center justify-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm font-bold text-emerald-200 transition hover:bg-emerald-400/20"
            >
              <Plus size={18} />
              Subir evidencia
            </button>
          </div>
        </div>

        {ocrError && (
          <p className="mb-4 rounded-2xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
            {ocrError}
          </p>
        )}

        {(selectedObra.evidencias?.length || 0) === 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-[760px] w-full text-sm">
              <tbody>
                <tr className="border-y border-slate-800/60">
                  <td className="py-8 text-center text-slate-400">
                    No hay evidencias documentales asociadas a esta obra.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {(selectedObra.evidencias?.length || 0) > 0 && (
          <div className="space-y-3">
            {selectedObra.evidencias?.map((evidencia) => (
            <div
              key={evidencia.id}
              className="grid grid-cols-1 gap-3 rounded-2xl border border-slate-800 bg-slate-950 p-4 md:grid-cols-[minmax(0,1fr)_auto]"
            >
              <div className="min-w-0">
                <p className="font-semibold text-slate-100">
                  {getConstructionWorkDocumentTypeLabel(evidencia.tipo_evidencia)}
                </p>
                <p className="mt-1 text-sm text-slate-400">
                  Fecha: {evidencia.fecha}
                </p>
                <a
                  href={evidencia.archivo_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-flex max-w-full items-center gap-2 truncate text-sm font-semibold text-emerald-300 hover:text-emerald-200"
                >
                  <FileText size={16} className="shrink-0" />
                  {evidencia.archivo?.split("/").pop() || "Ver archivo"}
                </a>
                <button
                  type="button"
                  onClick={() => onRunOcr(evidencia.id)}
                  disabled={readingDocumentId === evidencia.id}
                  className="mt-3 flex w-fit items-center gap-2 rounded-2xl border border-sky-400/20 bg-sky-400/10 px-4 py-2 text-sm font-bold text-sky-200 transition hover:bg-sky-400/20 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {readingDocumentId === evidencia.id ? (
                    <Loader2 className="animate-spin" size={16} />
                  ) : (
                    <FileText size={16} />
                  )}
                  Analizar evidencia
                </button>
                <button
                  type="button"
                  onClick={() => onRunStructuredExtraction(evidencia.id)}
                  disabled={extractingDocumentId === evidencia.id}
                  className="mt-2 flex w-fit items-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {extractingDocumentId === evidencia.id ? (
                    <Loader2 className="animate-spin" size={16} />
                  ) : (
                    <FileText size={16} />
                  )}
                  Extraer datos
                </button>
              </div>
              <div
                className={`h-fit rounded-2xl border px-4 py-2 text-sm font-bold ${
                  documentStatusTone[evidencia.estado_validacion] ||
                  documentStatusTone.pendiente
                }`}
              >
                {getConstructionEvidenceReviewLabel(evidencia.estado_validacion)}
              </div>
            </div>
            ))}
          </div>
        )}

        {activeExtraction && (
          <div className="mt-5 rounded-3xl border border-sky-400/20 bg-sky-400/10 p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-sky-200">
                  Datos sugeridos por evidencia
                </p>
                <p className="mt-1 text-sm text-slate-300">
                  La automatización sugiere, el equipo valida antes de aplicar al cálculo.
                </p>
              </div>
              <div className="rounded-2xl border border-sky-400/20 bg-slate-950/50 px-4 py-2 text-sm font-bold text-sky-200">
                {activeExtraction.estado_revision_label}
              </div>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {ocrFields.map(([name, label]) => (
                <Field key={name} label={label}>
                  <input
                    name={name}
                    value={ocrForm[name] ?? ""}
                    onChange={onUpdateOcrForm}
                    className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-sky-400/60"
                  />
                </Field>
              ))}
            </div>

            <div className="mt-4 flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={onValidateExtraction}
                disabled={validatingExtraction}
                className="flex items-center justify-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200 transition hover:bg-emerald-400/20 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {validatingExtraction ? (
                  <Loader2 className="animate-spin" size={16} />
                ) : (
                  <Plus size={16} />
                )}
                Validar y aplicar
              </button>
              <button
                type="button"
                onClick={onRejectExtraction}
                className="rounded-2xl border border-slate-700 bg-slate-950 px-5 py-3 text-sm font-bold text-slate-200 transition hover:bg-slate-800"
              >
                Rechazar sugerencia
              </button>
            </div>
          </div>
        )}

        {documentInsight && (
          <div className="mt-5 rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-cyan-200">
                  Datos estructurados
                </p>
                <p className="mt-1 text-sm text-slate-300">
                  El evidencia puede alimentar campos listos para cálculo cuando el flujo esté habilitado.
                </p>
              </div>
              <div className="rounded-2xl border border-cyan-400/20 bg-slate-950/50 px-4 py-2 text-sm font-bold text-cyan-200">
                {documentInsight.confianza != null
                  ? `${formatNumber(Number(documentInsight.confianza) * 100, 0)}% confianza`
                  : "Sin confianza"}
              </div>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <DetailItem
                label="Tipo de evidencia"
                value={documentInsight.tipo_evidencia}
              />
              <DetailItem label="Fecha" value={documentInsight.fecha} />
              <DetailItem
                label="Litros diesel"
                value={
                  documentInsight.litros_diesel != null
                    ? formatNumber(Number(documentInsight.litros_diesel))
                    : "Sin dato"
                }
              />
              <DetailItem label="Patente" value={documentInsight.patente} />
              <DetailItem label="Código de obra" value={documentInsight.codigo_obra} />
              <DetailItem label="Fuente" value={documentInsight.fuente} />
            </div>
          </div>
        )}
      </section>
    </section>
  );
}

export default EvidenciasTab;
