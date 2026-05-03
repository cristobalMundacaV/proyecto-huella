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
      contentClassName="my-8 w-full max-w-lg rounded-3xl border border-slate-800 bg-slate-900 p-5 shadow-2xl sm:p-6"
      onBackdropClick={onCancel}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="rounded-2xl border border-red-400/20 bg-red-400/10 p-3 text-red-300">
            <AlertTriangle size={24} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100">{title}</h2>
            {description && (
              <p className="mt-2 text-sm leading-6 text-slate-400">{description}</p>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={onCancel}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-slate-700 bg-slate-950 text-slate-300 transition hover:bg-slate-800"
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
          className="rounded-2xl border border-slate-700 bg-slate-950 px-5 py-3 text-sm font-bold text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {cancelLabel}
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-2xl border border-red-400/20 bg-red-400/10 px-5 py-3 text-sm font-bold text-red-200 transition hover:bg-red-400/20 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? <Loader2 className="animate-spin" size={18} /> : null}
          {confirmLabel}
        </button>
      </div>
    </AnimatedModalShell>
  );
}

export default ConfirmationModal;
