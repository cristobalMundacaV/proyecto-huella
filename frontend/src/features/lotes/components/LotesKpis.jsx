import { Activity, Boxes, Leaf, Scale } from "lucide-react";
import { formatNumber } from "@/shared/utils/formatters";

function LotesKpis({ lotes, totalCo2Almacenado, totalEmisiones, totalMasaMadera }) {
  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6 xl:grid-cols-4">
      <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <div className="mb-3 flex items-center gap-3">
          <Boxes className="text-cyan-300" size={22} />
          <p className="text-sm text-slate-400">Lotes registrados</p>
        </div>
        <p className="mt-2 text-3xl font-bold text-slate-100">
          {formatNumber(lotes.length, 0)}
        </p>
      </div>
      <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <div className="mb-3 flex items-center gap-3">
          <Activity className="text-cyan-300" size={22} />
          <p className="text-sm text-slate-400">Emisiones asociadas</p>
        </div>
        <p className="mt-2 text-3xl font-bold text-cyan-200">
          {formatNumber(totalEmisiones)} kg CO2e
        </p>
      </div>
      <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <div className="mb-3 flex items-center gap-3">
          <Scale className="text-cyan-300" size={22} />
          <p className="text-sm text-slate-400">Masa estimada</p>
        </div>
        <p className="mt-2 text-3xl font-bold text-emerald-300">
          {formatNumber(totalMasaMadera)} kg
        </p>
      </div>
      <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <div className="mb-3 flex items-center gap-3">
          <Leaf className="text-cyan-300" size={22} />
          <p className="text-sm text-slate-400">Carbono almacenado</p>
        </div>
        <p className="mt-2 text-3xl font-bold text-lime-200">
          {formatNumber(totalCo2Almacenado)} kg
        </p>
      </div>
    </section>
  );
}

export default LotesKpis;
