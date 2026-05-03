import { Plus } from "lucide-react";

function LotesToolbar({ onOpenCreate }) {
  return (
    <section className="flex flex-col gap-3 rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
      <div>
        <p className="text-xs font-bold uppercase tracking-wide text-emerald-300">
          Gestion de lotes
        </p>
        <h2 className="mt-1 text-xl font-semibold text-slate-100">
          Inventario y trazabilidad
        </h2>
      </div>
      <button
        type="button"
        onClick={onOpenCreate}
        className="flex items-center justify-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200 transition hover:bg-emerald-400/20"
      >
        <Plus size={18} />
        Crear lote
      </button>
    </section>
  );
}

export default LotesToolbar;
