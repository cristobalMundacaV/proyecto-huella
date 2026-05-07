import { useEffect } from "react";
import { CheckCircle2, Loader2, X } from "lucide-react";

function Toast({ message, subtitle, onClose, toastKey, loading = false }) {
  useEffect(() => {
    if (!message || loading) {
      return undefined;
    }

    const timeoutId = window.setTimeout(onClose, 2800);

    return () => window.clearTimeout(timeoutId);
  }, [message, onClose, toastKey]);

  if (!message) {
    return null;
  }

  const containerClass = loading
    ? "fixed right-8 top-8 z-50 w-[460px] max-w-[calc(100vw-4rem)] rounded-3xl border border-cyan-400/30 bg-slate-900 px-7 py-6 text-slate-100 shadow-2xl shadow-slate-950/60"
    : "fixed right-8 top-8 z-50 w-[460px] max-w-[calc(100vw-4rem)] rounded-3xl border border-emerald-400/30 bg-slate-900 px-7 py-6 text-slate-100 shadow-2xl shadow-slate-950/60";

  const iconWrapperClass = loading
    ? "rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3"
    : "rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-3";

  const titleClass = loading
    ? "text-lg font-bold leading-6 text-cyan-200"
    : "text-lg font-bold leading-6 text-emerald-200";

  return (
    <div className={containerClass}>
      <div className="flex items-start gap-4">
        <div className={iconWrapperClass}>
          {loading ? (
            <Loader2 size={26} className="animate-spin text-cyan-400" />
          ) : (
            <CheckCircle2 size={26} className="text-emerald-400" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className={titleClass}>{message}</p>
          {subtitle && (
            <p className="mt-2 text-sm leading-5 text-slate-400">
              {subtitle}
            </p>
          )}
        </div>
        {!loading && (
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl p-2 text-slate-400 transition hover:bg-slate-800 hover:text-slate-100"
            aria-label="Cerrar notificacion"
          >
            <X size={18} />
          </button>
        )}
      </div>
    </div>
  );
}

export default Toast;
