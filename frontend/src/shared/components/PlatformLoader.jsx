import { Loader2 } from "lucide-react";

function PlatformLoader({
  title = "Preparando información",
  description = "Estamos organizando los datos para mostrarte una lectura clara y actualizada.",
  fullScreen = false,
  inline = false,
  compact = false,
}) {
  if (inline) {
    return (
      <div
        className="flex items-center gap-2 py-2 text-sm font-medium text-[var(--text-muted)]"
        role="status"
        aria-live="polite"
      >
        <Loader2
          aria-hidden="true"
          className="animate-spin text-emerald-700"
          size={18}
        />

        <span>{title}</span>
      </div>
    );
  }

  return (
    <section
      className={`flex items-center justify-center ${fullScreen
          ? "min-h-screen px-4"
          : compact
            ? "min-h-[220px]"
            : "min-h-[360px]"
        }`}
      role="status"
      aria-live="polite"
    >
      <div
        className={`relative w-full overflow-hidden border border-emerald-200/70 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_36%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] text-center shadow-[0_20px_60px_rgba(15,118,110,0.12)] ring-1 ring-white/80 ${compact
            ? "max-w-xl rounded-[26px] p-6"
            : "max-w-2xl rounded-[34px] p-8"
          }`}
      >
        <div className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-emerald-300/20 blur-3xl" />

        <div className="pointer-events-none absolute -bottom-24 left-10 h-56 w-56 rounded-full bg-teal-300/20 blur-3xl" />

        <div className="relative mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-200 bg-white shadow-[0_14px_36px_rgba(15,118,110,0.14)]">
          <img
            src="/brand/carbono-zero-mark.png"
            alt=""
            aria-hidden="true"
            className="h-10 w-10 object-contain"
          />

          <Loader2
            aria-hidden="true"
            className="absolute -right-2 -top-2 animate-spin rounded-full bg-emerald-700 p-1 text-white shadow-sm"
            size={24}
          />
        </div>

        <p className="relative mt-5 text-[11px] font-black uppercase tracking-[0.22em] text-emerald-700">
          Carbono Zero
        </p>

        <h2
          className={`relative mt-2 font-black tracking-tight text-slate-950 ${compact ? "text-xl" : "text-2xl sm:text-3xl"
            }`}
        >
          {title}
        </h2>

        {description && (
          <p className="relative mx-auto mt-3 max-w-xl text-sm font-medium leading-6 text-slate-600">
            {description}
          </p>
        )}

        <div className="relative mt-6 h-1.5 overflow-hidden rounded-full bg-emerald-100">
          <div className="h-full w-1/2 animate-pulse rounded-full bg-gradient-to-r from-emerald-700 to-teal-500" />
        </div>
      </div>
    </section>
  );
}

export default PlatformLoader;