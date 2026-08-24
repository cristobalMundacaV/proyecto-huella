import { useEffect } from "react";
import { AlertCircle, CheckCircle2, Loader2, X } from "lucide-react";

function Toast({ message, subtitle, onClose, toastKey, loading = false, tone = "success" }) {
  useEffect(() => {
    if (!message || loading) return undefined;
    const timeoutId = window.setTimeout(onClose, 3600);
    return () => window.clearTimeout(timeoutId);
  }, [loading, message, onClose, toastKey]);

  if (!message) return null;

  const isError = tone === "error";
  const iconStyle = loading ? "border-slate-200 bg-slate-100 text-slate-600" : isError ? "border-red-200 bg-red-50 text-red-600" : "border-emerald-200 bg-emerald-50 text-emerald-700";
  const titleStyle = loading ? "text-slate-700" : isError ? "text-red-700" : "text-emerald-800";

  return (
    <div role={isError ? "alert" : "status"} aria-live={isError ? "assertive" : "polite"} className="fixed right-4 top-4 z-[70] w-[420px] max-w-[calc(100vw-2rem)] rounded-2xl border border-slate-200 bg-white px-5 py-4 text-slate-900 shadow-2xl sm:right-8 sm:top-8">
      <div className="flex items-start gap-4">
        <div className={`rounded-xl border p-2.5 shadow-sm ${iconStyle}`}>
          {loading ? <Loader2 size={24} className="animate-spin" /> : isError ? <AlertCircle size={24} /> : <CheckCircle2 size={24} />}
        </div>
        <div className="min-w-0 flex-1">
          <p className={`text-base font-bold leading-6 ${titleStyle}`}>{message}</p>
          {subtitle && <p className="mt-1 text-sm leading-5 text-slate-600">{subtitle}</p>}
        </div>
        {!loading && <button type="button" onClick={onClose} className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900" aria-label="Cerrar notificación"><X size={18} /></button>}
      </div>
    </div>
  );
}

export default Toast;
