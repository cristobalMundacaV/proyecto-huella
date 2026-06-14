import { UploadCloud } from "lucide-react";

function EvidenceEmptyState({ message }) {
  return (
    <section className="rounded-3xl border border-dashed border-[var(--border)] bg-[var(--bg-card)] p-8 text-center shadow-[var(--shadow-card)]">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl border border-emerald-200 bg-emerald-50 text-emerald-700">
        <UploadCloud size={28} />
      </div>
      <h2 className="mt-4 text-2xl font-black text-[var(--text-main)]">Sin evidencias cargadas</h2>
      <p className="mx-auto mt-3 max-w-2xl text-sm font-semibold leading-7 text-[var(--text-muted)]">{message}</p>
    </section>
  );
}

export default EvidenceEmptyState;
