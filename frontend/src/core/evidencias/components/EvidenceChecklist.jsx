import { CheckCircle2 } from "lucide-react";

function EvidenceChecklist({ items = [] }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[0_18px_45px_var(--shadow)]">
      <h2 className="text-xl font-black text-[var(--text-main)]">Checklist documental</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {items.map((item) => (
          <div key={item} className="flex gap-3 rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 text-sm font-semibold text-[var(--text-main)]">
            <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-700" size={18} />
            <span>{item}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

export default EvidenceChecklist;
