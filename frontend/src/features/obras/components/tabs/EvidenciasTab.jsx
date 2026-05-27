import { useEffect, useState } from "react";
import { CheckCircle2, FileText, Inbox, Loader2, Plus, Search, X } from "lucide-react";

import Pagination from "@/shared/components/Pagination";
import { formatNumber } from "@/shared/utils/formatters";
import {
  getConstructionEvidenceReviewLabel,
  getConstructionWorkDocumentTypeLabel,
} from "@/shared/utils/constructionEvidenceLabels";
import { DetailItem, Field } from "../common";
import { documentStatusTone, documentTypes, ocrFields } from "../constants";

const evidenciasPageSize = 5;

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
  const [currentPage, setCurrentPage] = useState(1);
  const evidencias = selectedObra.evidencias || [];
  const totalPages = Math.max(1, Math.ceil(evidencias.length / evidenciasPageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const visibleEvidencias = evidencias.slice(
    (safeCurrentPage - 1) * evidenciasPageSize,
    safeCurrentPage * evidenciasPageSize
  );

  useEffect(() => {
    setCurrentPage(1);
  }, [selectedObra.codigo_obra]);

  return (
    <section className="space-y-6">
      {isModalOpen && (
        <div className="premium-modal-overlay fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4">
          <form
            onSubmit={onDocumentSubmit}
            className="premium-modal-shell my-8 w-full max-w-2xl p-4 sm:p-6"
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]">
                  <FileText size={18} />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-[var(--text-main)]">Subir evidencia</h2>
                  <p className="text-sm text-[var(--text-muted)]">{selectedObra.codigo_obra}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] text-[var(--text-main)] transition hover:bg-slate-100"
                aria-label="Cerrar modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className="grid grid-cols-1 gap-4">
              <Field label="Tipo de evidencia" error={documentFieldErrors.tipo_evidencia?.[0]}>
                <select
                  name="tipo_evidencia"
                  value={documentForm.tipo_evidencia}
                  onChange={onUpdateDocumentForm}
                  required
                  className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60"
                >
                  {documentTypes.map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
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
                  className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60"
                />
              </Field>

              <Field label="Archivo" error={documentFieldErrors.archivo?.[0]}>
                <input
                  type="file"
                  name="archivo"
                  onChange={onUpdateDocumentForm}
                  required
                  className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] file:mr-4 file:rounded-xl file:border-0 file:bg-[var(--success-bg)] file:px-3 file:py-2 file:font-bold file:text-[var(--primary-dark)]"
                />
              </Field>
            </div>

            {documentError && (
              <p className="mt-4 rounded-2xl border border-[#F1B8B8] bg-[var(--danger-bg)] p-3 text-sm font-semibold text-[#B42318]">
                {documentError}
              </p>
            )}

            <button
              type="submit"
              disabled={savingDocument}
              className="premium-button-primary mt-6 flex w-full items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60"
            >
              {savingDocument ? <Loader2 className="animate-spin" size={18} /> : <FileText size={18} />}
              Subir evidencia
            </button>
          </form>
        </div>
      )}

      <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.14em] text-[var(--primary-dark)]">
              Evidencias documentales
            </p>
            <h2 className="mt-1 text-2xl font-bold text-[var(--text-main)]">Respaldo y validación de obra</h2>
            <p className="mt-1 text-sm font-medium text-[var(--text-muted)]">
              {selectedObra.codigo_obra} · documentos que respaldan consumos, proveedores y cálculos ambientales.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] px-4 py-3 text-sm font-black text-[#075985]">
              {formatNumber(evidencias.length, 0)} evidencias
            </div>
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="premium-button-primary flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-bold"
            >
              <Plus size={18} />
              Subir evidencia
            </button>
          </div>
        </div>

        {ocrError && (
          <p className="mb-4 rounded-2xl border border-[#F1B8B8] bg-[var(--danger-bg)] p-3 text-sm font-semibold text-[#B42318]">
            {ocrError}
          </p>
        )}

        {evidencias.length === 0 && (
          <EmptyEvidenceState onAction={() => setIsModalOpen(true)} />
        )}

        {evidencias.length > 0 && (
          <>
            <div className="space-y-3">
              {visibleEvidencias.map((evidencia) => (
                <EvidenceCard
                  key={evidencia.id}
                  evidencia={evidencia}
                  extractingDocumentId={extractingDocumentId}
                  onRunOcr={onRunOcr}
                  onRunStructuredExtraction={onRunStructuredExtraction}
                  readingDocumentId={readingDocumentId}
                />
              ))}
            </div>

            {evidencias.length > evidenciasPageSize && (
              <Pagination
                currentPage={safeCurrentPage}
                itemLabel="evidencias"
                onPageChange={setCurrentPage}
                pageSize={evidenciasPageSize}
                totalItems={evidencias.length}
              />
            )}
          </>
        )}

        {activeExtraction && (
          <div className="mt-5 rounded-3xl border border-[#B8D6DE] bg-[var(--info-bg)] p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-[#075985]">
                  Datos sugeridos por evidencia
                </p>
                <p className="mt-1 text-sm text-[var(--text-muted)]">
                  La automatización sugiere datos; el equipo valida antes de aplicar al cálculo.
                </p>
              </div>
              <div className="rounded-2xl border border-[#B8D6DE] bg-white px-4 py-2 text-sm font-bold text-[#075985]">
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
                    className="w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60"
                  />
                </Field>
              ))}
            </div>

            <div className="mt-4 flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={onValidateExtraction}
                disabled={validatingExtraction}
                className="premium-button-primary flex items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60"
              >
                {validatingExtraction ? <Loader2 className="animate-spin" size={16} /> : <CheckCircle2 size={16} />}
                Validar y aplicar
              </button>
              <button
                type="button"
                onClick={onRejectExtraction}
                className="premium-button-secondary rounded-2xl px-5 py-3 text-sm font-bold"
              >
                Rechazar sugerencia
              </button>
            </div>
          </div>
        )}

        {documentInsight && (
          <div className="mt-5 rounded-3xl border border-[#B8D6DE] bg-[var(--info-bg)] p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-[#075985]">
                  Datos estructurados
                </p>
                <p className="mt-1 text-sm text-[var(--text-muted)]">
                  La evidencia puede alimentar campos listos para cálculo cuando el flujo esté habilitado.
                </p>
              </div>
              <div className="rounded-2xl border border-[#B8D6DE] bg-white px-4 py-2 text-sm font-bold text-[#075985]">
                {documentInsight.confianza != null
                  ? `${formatNumber(Number(documentInsight.confianza) * 100, 0)}% confianza`
                  : "Sin confianza"}
              </div>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <DetailItem label="Tipo de evidencia" value={documentInsight.tipo_evidencia} />
              <DetailItem label="Fecha" value={documentInsight.fecha} />
              <DetailItem
                label="Litros diésel"
                value={documentInsight.litros_diesel != null ? formatNumber(Number(documentInsight.litros_diesel)) : "Sin dato"}
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

function EvidenceCard({
  evidencia,
  extractingDocumentId,
  onRunOcr,
  onRunStructuredExtraction,
  readingDocumentId,
}) {
  const statusClass = documentStatusTone[evidencia.estado_validacion] || documentStatusTone.pendiente;
  const fileName = evidencia.archivo?.split("/").pop() || "Ver archivo";

  return (
    <div className="grid grid-cols-1 gap-4 rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 shadow-[0_8px_22px_rgba(15,23,42,0.04)] transition hover:border-[var(--primary)]/25 hover:bg-[var(--success-bg)]/30 md:grid-cols-[minmax(0,1fr)_auto]">
      <div className="min-w-0">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-[var(--border)] bg-white text-[var(--primary-dark)]">
            <FileText size={18} />
          </div>
          <div className="min-w-0">
            <p className="font-black text-[var(--text-main)]">
              {getConstructionWorkDocumentTypeLabel(evidencia.tipo_evidencia)}
            </p>
            <p className="mt-1 text-sm font-medium text-[var(--text-muted)]">
              Fecha: {evidencia.fecha || "Pendiente"}
            </p>
            <a
              href={evidencia.archivo_url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-flex max-w-full items-center gap-2 truncate text-sm font-bold text-[var(--primary-dark)] hover:text-[var(--primary)]"
            >
              <FileText size={16} className="shrink-0" />
              {fileName}
            </a>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <button
            type="button"
            onClick={() => onRunOcr(evidencia.id)}
            disabled={readingDocumentId === evidencia.id}
            className="premium-button-secondary flex w-fit items-center gap-2 rounded-2xl px-4 py-2 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60"
          >
            {readingDocumentId === evidencia.id ? <Loader2 className="animate-spin" size={16} /> : <Search size={16} />}
            Analizar evidencia
          </button>
          <button
            type="button"
            onClick={() => onRunStructuredExtraction(evidencia.id)}
            disabled={extractingDocumentId === evidencia.id}
            className="flex w-fit items-center gap-2 rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] px-4 py-2 text-sm font-bold text-[#075985] transition hover:bg-[#DDF0F4] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {extractingDocumentId === evidencia.id ? <Loader2 className="animate-spin" size={16} /> : <FileText size={16} />}
            Extraer datos
          </button>
        </div>
      </div>

      <div className={`h-fit rounded-2xl border px-4 py-2 text-center text-sm font-black ${statusClass}`}>
        {getConstructionEvidenceReviewLabel(evidencia.estado_validacion)}
      </div>
    </div>
  );
}

function EmptyEvidenceState({ onAction }) {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center justify-center rounded-3xl border border-dashed border-[var(--border)] bg-[var(--bg-surface)] px-6 py-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]">
        <Inbox size={22} />
      </div>
      <h3 className="mt-4 text-lg font-black text-[var(--text-main)]">Sin evidencias vinculadas</h3>
      <p className="mt-2 text-sm font-medium leading-6 text-[var(--text-muted)]">
        Sube facturas, guías de despacho, tickets de pesaje o documentos técnicos para respaldar los registros ambientales de esta obra.
      </p>
      <button
        type="button"
        onClick={onAction}
        className="premium-button-primary mt-5 inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-bold"
      >
        <Plus size={18} />
        Subir primera evidencia
      </button>
    </div>
  );
}

export default EvidenciasTab;
