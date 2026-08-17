import { Boxes, Sparkles } from "lucide-react";

function PresetComingSoon({ title, description, presetName, items = [] }) {
  const visibleItems = items.length
    ? items
    : [
        "Informaci?n operacional",
        "Importaciones y evidencias",
        "Indicadores y reportes",
      ];

  return (
    <div className="mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <section className="overflow-hidden rounded-3xl border border-[var(--border)] bg-[linear-gradient(135deg,#ECFDF5_0%,#FFFFFF_48%,#EFF6FF_100%)] p-6 shadow-[var(--shadow-premium)] ring-1 ring-white/70 sm:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-[var(--primary)]/20 bg-white/80 px-3 py-1 text-xs font-black uppercase tracking-[0.16em] text-[var(--primary-dark)] shadow-[0_8px_18px_rgba(15,23,42,0.05)]">
              <Sparkles size={14} />
              {presetName}
            </div>
            <h1 className="mt-4 text-3xl font-black tracking-tight text-[var(--text-main)] sm:text-4xl">
              {title}
            </h1>
            <p className="mt-3 max-w-3xl text-base font-medium leading-7 text-[var(--text-muted)]">
              {description}
            </p>
          </div>

          <div className="rounded-2xl border border-[var(--primary)]/20 bg-white/80 p-4 text-sm font-bold text-[var(--primary-dark)] shadow-[0_14px_30px_rgba(14,124,102,0.10)]">
            Esta capacidad no est? disponible para la configuraci?n activa.
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {visibleItems.map((item) => (
          <article
            key={item}
            className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-card)] ring-1 ring-white/60"
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[var(--primary)]/15 bg-[var(--success-bg)] text-[var(--primary-dark)]">
              <Boxes size={20} />
            </div>
            <p className="mt-4 text-sm font-black uppercase tracking-[0.12em] text-[var(--text-muted)]">
              Informaci?n relacionada
            </p>
            <h2 className="mt-2 text-lg font-black text-[var(--text-main)]">{item}</h2>
          </article>
        ))}
      </section>
    </div>
  );
}

export default PresetComingSoon;
