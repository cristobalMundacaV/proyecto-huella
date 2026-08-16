import { useEffect } from "react";
import { CheckCircle2, Loader2, X } from "lucide-react";

function Toast({ message, subtitle, onClose, toastKey, loading = false }) {
  useEffect(() => {
    if (!message || loading) {
      return undefined;
    }

    const timeoutId = window.setTimeout(onClose, 2800);

    return () => window.clearTimeout(timeoutId);
  }, [loading, message, onClose, toastKey]);

  if (!message) {
    return null;
  }

  const containerClass = loading
    ? "fixed right-8 top-8 z-50 w-[460px] max-w-[calc(100vw-4rem)] premium-card rounded-3xl bg-[var(--bg-card)] px-7 py-6 text-[var(--text-main)] shadow-[var(--shadow-premium)]"
    : "fixed right-8 top-8 z-50 w-[460px] max-w-[calc(100vw-4rem)] premium-card rounded-3xl bg-[var(--bg-card)] px-7 py-6 text-[var(--text-main)] shadow-[var(--shadow-premium)]";

  const iconWrapperClass = loading
    ? "rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] p-3 shadow-[var(--shadow-soft)]"
    : "rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] p-3 shadow-[var(--shadow-soft)]";

  const titleClass = loading
    ? "text-lg font-bold leading-6 text-[#075985]"
    : "text-lg font-bold leading-6 text-[var(--primary-dark)]";

  return (
    <div className={containerClass}>
      <div className="flex items-start gap-4">
        <div className={iconWrapperClass}>
          {loading ? (
            <Loader2 size={26} className="animate-spin text-[#075985]" />
          ) : (
            <CheckCircle2 size={26} className="text-[var(--primary-dark)]" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className={titleClass}>{message}</p>
          {subtitle && (
            <p className="mt-2 text-sm leading-5 text-[var(--text-muted)]">
              {subtitle}
            </p>
          )}
        </div>
        {!loading && (
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl p-2 text-[var(--text-muted)] transition hover:bg-[var(--bg-surface)] hover:text-[var(--text-main)]"
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
