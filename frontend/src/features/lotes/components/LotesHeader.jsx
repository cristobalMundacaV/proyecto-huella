import { Boxes, Plus } from "lucide-react";

function LotesHeader({ onOpenCreate }) {
  return (
    <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex items-center gap-3">
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] p-3">
          <Boxes className="text-[var(--primary-dark)]" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-[var(--text-main)] sm:text-4xl">Lotes</h1>
          <p className="text-[var(--text-muted)]">
            Registra y consulta la trazabilidad de cada lote: especie, volumen, emisiones y carbono almacenado para el Pasaporte Verde.
          </p>
        </div>
      </div>
      <button
        type="button"
        onClick={onOpenCreate}
        className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] px-5 py-3 text-sm font-bold text-[var(--primary-dark)] transition hover:border-[var(--primary)]/40 hover:bg-[#D9F0E6]"
      >
        <Plus size={18} />
        Nuevo lote
      </button>
    </header>
  );
}

export default LotesHeader;
