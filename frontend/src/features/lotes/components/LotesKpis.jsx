import { formatNumber } from "@/shared/utils/formatters";

function LotesKpis({ lotes, totalCo2Almacenado, totalEmisiones, totalMasaMadera }) {
  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6 xl:grid-cols-4">
      <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <p className="text-sm text-slate-400">Lotes registrados</p>
        <p className="mt-2 text-3xl font-bold text-slate-100">
          {formatNumber(lotes.length, 0)}
        </p>
      </div>
      <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <p className="text-sm text-slate-400">Emisiones asociadas</p>
        <p className="mt-2 text-3xl font-bold text-cyan-200">
          {formatNumber(totalEmisiones)} kg CO2e
        </p>
      </div>
      <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <p className="text-sm text-slate-400">Masa estimada</p>
        <p className="mt-2 text-3xl font-bold text-emerald-300">
          {formatNumber(totalMasaMadera)} kg
        </p>
      </div>
      <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <p className="text-sm text-slate-400">Carbono almacenado</p>
        <p className="mt-2 text-3xl font-bold text-lime-200">
          {formatNumber(totalCo2Almacenado)} kg
        </p>
      </div>
    </section>
  );
}

export default LotesKpis;
