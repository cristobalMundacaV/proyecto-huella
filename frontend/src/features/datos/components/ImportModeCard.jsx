export default function ImportModeCard({ icon: Icon, title, description, helper, badge, selected = false, disabled = false, onSelect, onClick }) {
  return <button
    type="button"
    aria-pressed={selected}
    disabled={disabled}
    onClick={onSelect || onClick}
    className={`flex h-full w-full flex-col items-start rounded-[20px] border p-4 text-left transition focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] ${selected ? "border-emerald-500 bg-emerald-50 shadow-[0_10px_28px_rgba(5,150,105,0.12)]" : "border-slate-200 bg-white hover:border-emerald-300 hover:bg-emerald-50/40"} disabled:cursor-not-allowed disabled:bg-slate-50 disabled:opacity-65`}
  >
    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700"><Icon aria-hidden="true" size={19} /></span>
    <span className="mt-3 font-black text-[var(--text-primary)]">{title}</span>
    <span className="mt-1 text-sm leading-5 text-[var(--text-secondary)]">{description}</span>
    {helper && <span className="mt-auto pt-3 text-xs font-bold text-[var(--text-muted)]">{helper}</span>}
    {(badge || disabled) && <span className="mt-2 rounded-full bg-slate-200 px-2 py-1 text-[10px] font-black uppercase tracking-wide text-slate-600">{badge || "Próximamente"}</span>}
  </button>;
}
