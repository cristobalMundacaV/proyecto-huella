const tones={neutral:"bg-[var(--bg-surface-subtle)] text-[var(--status-neutral)]",success:"bg-[var(--success-bg)] text-[var(--status-success)]",warning:"bg-[var(--warning-bg)] text-[var(--status-warning)]",danger:"bg-[var(--danger-bg)] text-[var(--status-danger)]",info:"bg-[var(--info-bg)] text-[var(--status-info)]"};
export default function Badge({children,tone="neutral",className=""}){return <span className={`inline-flex items-center rounded-full border border-current/15 px-2.5 py-1 text-xs font-bold ${tones[tone]||tones.neutral} ${className}`}>{children}</span>}
export function StatusBadge({label,children,...props}){return <Badge {...props}>{label??children}</Badge>}
export function DataQualityBadge({label,tone="neutral"}){return <Badge tone={tone}>{label}</Badge>}
export function ScopeBadge({label}){return <Badge tone="info">{label}</Badge>}
