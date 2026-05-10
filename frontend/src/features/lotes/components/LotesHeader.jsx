import { Boxes, Plus } from "lucide-react";

function LotesHeader({ onOpenCreate }) {
  return (
    <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex items-center gap-3">
        <div className="p-3 rounded-2xl bg-emerald-400/10 border border-emerald-400/20">
          <Boxes className="text-emerald-400" />
        </div>
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold">Lotes</h1>
          <p className="text-slate-400">
            Registra y consulta la trazabilidad de cada lote: especie, volumen, emisiones y carbono almacenado para el Pasaporte Verde.
          </p>
        </div>
      </div>
      <button
        type="button"
        onClick={onOpenCreate}
        className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200 transition hover:bg-emerald-400/20"
      >
        <Plus size={18} />
        Nuevo lote
      </button>
    </header>
  );
}

export default LotesHeader;
