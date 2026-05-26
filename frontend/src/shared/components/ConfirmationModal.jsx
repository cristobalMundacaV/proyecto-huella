import { AlertTriangle, Loader2, X } from "lucide-react";

import AnimatedModalShell from "./AnimatedModalShell";

function ConfirmationModal({
  cancelLabel = "Cancelar",
  confirmLabel = "Eliminar",
  description,
  loading = false,
  onCancel,
  onConfirm,
  title,
}) {
  return (
    <AnimatedModalShell
      ariaLabel={title}
      contentClassName="my-8 w-full max-w-lg rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-2xl sm:p-6"
      onBackdropClick={onCancel}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="rounded-2xl border border-[#F1B8B8] bg-[var(--danger-bg)] p-3 text-[#B42318]">
            <AlertTriangle size={24} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-[var(--text-main)]">{title}</h2>
            {description && (
              <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">{description}</p>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={onCancel}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] text-[var(--text-muted)] transition hover:text-[var(--text-main)]"
          aria-label="Cerrar confirmacion"
        >
          <X size={18} />
        </button>
      </div>

      <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={onCancel}
          disabled={loading}
          className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-5 py-3 text-sm font-bold text-[var(--text-main)] transition hover:bg-[var(--bg-card)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {cancelLabel}
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[#F1B8B8] bg-[var(--danger-bg)] px-5 py-3 text-sm font-bold text-[#B42318] transition hover:bg-[#FBE2E2] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? <Loader2 className="animate-spin" size={18} /> : null}
          {confirmLabel}
        </button>
      </div>
    </AnimatedModalShell>
  );
}

export default ConfirmationModal;
