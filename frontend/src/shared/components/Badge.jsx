function Badge({ children, tone = "cyan" }) {
  const tones = {
    amber: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]",
    blue: "border-[#BFDBFE] bg-[#EFF6FF] text-[#075985]",
    cyan: "border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]",
    emerald: "border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]",
    lime: "border-[#BEF264] bg-[#F7FEE7] text-[#3F6212]",
    orange: "border-[#FDBA74] bg-[#FFF7ED] text-[#9A3412]",
    rose: "border-[#F1B8B8] bg-[var(--danger-bg)] text-[#B42318]",
    slate: "border-[var(--border)] bg-[var(--bg-surface)] text-[var(--text-main)]",
    violet: "border-[#C4B5FD] bg-[#F1EDFF] text-[#5B21B6]",
  };

  return (
    <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold ${tones[tone] || tones.cyan}`}>
      {children}
    </span>
  );
}

export default Badge;
