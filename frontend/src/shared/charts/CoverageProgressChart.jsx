const TONE_COLORS = {
  success: "#247a45",
  warning: "#a65b12",
  danger: "#b13a35",
  info: "#28699a",
  neutral: "#647067",
};

function toneForValue(value, thresholds) {
  if (value === null || value === undefined) return "neutral";
  if (value >= thresholds.success) return "success";
  if (value >= thresholds.warning) return "warning";
  return "danger";
}

/**
 * Small radial "readiness"-style progress indicator — 0-100%, backend
 * computed. Pure SVG (no chart-library dependency needed for one ring).
 */
export default function CoverageProgressChart({
  value,
  label,
  helper,
  size = 132,
  strokeWidth = 12,
  tone,
  thresholds = { success: 90, warning: 70 },
}) {
  const missing = value === null || value === undefined;
  const clamped = missing ? 0 : Math.min(100, Math.max(0, Number(value)));
  const resolvedTone = tone || toneForValue(missing ? null : clamped, thresholds);
  const color = TONE_COLORS[resolvedTone] || TONE_COLORS.neutral;

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);

  return (
    <div className="flex items-center gap-4">
      <div className="relative shrink-0" style={{ height: size, width: size }}>
        <svg height={size} viewBox={`0 0 ${size} ${size}`} width={size}>
          <circle cx={size / 2} cy={size / 2} fill="none" r={radius} stroke="var(--border-subtle)" strokeWidth={strokeWidth} />
          {!missing && (
            <circle
              cx={size / 2}
              cy={size / 2}
              fill="none"
              r={radius}
              stroke={color}
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              strokeWidth={strokeWidth}
              transform={`rotate(-90 ${size / 2} ${size / 2})`}
            />
          )}
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-black text-[var(--text-primary)]">{missing ? "—" : `${Math.round(clamped)}%`}</span>
        </div>
      </div>

      {(label || helper) && (
        <div className="min-w-0">
          {label && <p className="text-sm font-black text-[var(--text-primary)]">{label}</p>}
          {helper && <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">{helper}</p>}
        </div>
      )}
    </div>
  );
}
