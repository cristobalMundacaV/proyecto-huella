import { useEffect } from "react";
import { CheckCircle2, X } from "lucide-react";

function Toast({ message, onClose, toastKey }) {
  useEffect(() => {
    if (!message) {
      return undefined;
    }

    const timeoutId = window.setTimeout(onClose, 2800);

    return () => window.clearTimeout(timeoutId);
  }, [message, onClose, toastKey]);

  if (!message) {
    return null;
  }

  return (
    <div className="fixed right-8 top-8 z-50 w-[460px] max-w-[calc(100vw-4rem)] rounded-3xl border border-emerald-400/30 bg-slate-900 px-7 py-6 text-slate-100 shadow-2xl shadow-slate-950/60">
      <div className="flex items-start gap-4">
        <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-3">
          <CheckCircle2 size={26} className="text-emerald-400" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-lg font-bold leading-6 text-emerald-200">
            {message}
          </p>
          <p className="mt-2 text-sm leading-5 text-slate-400">
            Seleccionamos el dataset que ya estaba cargado.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-xl p-2 text-slate-400 transition hover:bg-slate-800 hover:text-slate-100"
          aria-label="Cerrar notificacion"
        >
          <X size={18} />
        </button>
      </div>
    </div>
  );
}

export default Toast;
