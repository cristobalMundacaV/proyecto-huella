function Badge({ children, tone = "cyan" }) {
  const tones = {
    amber: "border-amber-400/30 bg-amber-400/10 text-amber-200",
    blue: "border-blue-400/30 bg-blue-400/10 text-blue-200",
    cyan: "border-cyan-400/30 bg-cyan-400/10 text-cyan-200",
    emerald: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
    lime: "border-lime-400/30 bg-lime-400/10 text-lime-200",
    orange: "border-orange-400/30 bg-orange-400/10 text-orange-200",
    rose: "border-rose-400/30 bg-rose-400/10 text-rose-200",
    slate: "border-slate-700 bg-slate-900 text-slate-300",
    violet: "border-violet-400/30 bg-violet-400/10 text-violet-200",
  };

  return (
    <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold ${tones[tone] || tones.cyan}`}>
      {children}
    </span>
  );
}

export default Badge;
