import { ShieldAlert } from "lucide-react";

function EvidenceValidationPanel({ recommendations = [] }) {
  return (
    <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5 text-amber-800 shadow-[0_18px_45px_var(--shadow)]">
      <div className="flex items-center gap-2">
        <ShieldAlert size={20} />
        <h2 className="text-xl font-black">Recomendaciones documentales</h2>
      </div>
      <div className="mt-4 space-y-3">
        {recommendations.map((item) => (
          <p key={item} className="rounded-2xl border border-amber-200 bg-white/70 p-4 text-sm font-semibold leading-6">
            {item}
          </p>
        ))}
      </div>
    </section>
  );
}

export default EvidenceValidationPanel;
