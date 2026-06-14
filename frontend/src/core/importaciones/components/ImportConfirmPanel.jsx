import { Save } from "lucide-react";

function ImportConfirmPanel({ canConfirm, message, onConfirm, saving }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)]">
      <h2 className="text-xl font-black text-[var(--text-main)]">Confirmacion</h2>
      <p className="mt-2 text-sm font-semibold text-[var(--text-muted)]">{message}</p>
      <button
        type="button"
        onClick={onConfirm}
        disabled={!canConfirm || saving}
        className="mt-4 inline-flex items-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Save size={18} />
        {saving ? "Importando..." : "Confirmar importacion"}
      </button>
    </section>
  );
}

export default ImportConfirmPanel;
