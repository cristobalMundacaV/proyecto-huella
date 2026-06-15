import { Leaf, Loader2 } from "lucide-react";

function PlatformLoader({
  title = "Preparando información ambiental",
  description = "Carbono Zero está cargando datos, validando registros y preparando la lectura de la empresa.",
  fullScreen = false,
}) {
  return (
    <section
      className={`flex items-center justify-center ${
        fullScreen ? "min-h-screen" : "min-h-[calc(100vh-7rem)]"
      }`}
    >
      <div className="relative w-full max-w-2xl overflow-hidden rounded-[34px] border border-emerald-200/70 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.18),transparent_34%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] p-8 text-center shadow-[0_28px_90px_rgba(15,118,110,0.16)] ring-1 ring-white/80">
        <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-emerald-300/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-24 left-10 h-64 w-64 rounded-full bg-teal-300/20 blur-3xl" />

        <div className="relative mx-auto flex h-20 w-20 items-center justify-center rounded-3xl border border-emerald-200 bg-white text-emerald-700 shadow-[0_18px_42px_rgba(15,118,110,0.16)]">
          <Leaf size={34} />
          <Loader2 className="absolute -right-2 -top-2 animate-spin rounded-full bg-emerald-700 p-1 text-white" size={26} />
        </div>

        <p className="relative mt-6 text-xs font-black uppercase tracking-[0.22em] text-emerald-700">
          Carbono Zero
        </p>
        <h2 className="relative mt-2 text-3xl font-black tracking-tight text-slate-950">
          {title}
        </h2>
        <p className="relative mx-auto mt-3 max-w-xl text-sm font-semibold leading-7 text-slate-600">
          {description}
        </p>

        <div className="relative mt-6 h-2 overflow-hidden rounded-full bg-emerald-100">
          <div className="h-full w-1/2 animate-pulse rounded-full bg-emerald-600" />
        </div>
      </div>
    </section>
  );
}

export default PlatformLoader;