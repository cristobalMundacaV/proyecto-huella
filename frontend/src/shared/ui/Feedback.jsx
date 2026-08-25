import {
    AlertCircle,
    Inbox,
    Loader2,
} from "lucide-react";

import { Button } from "./Button";

export function EmptyState({
    icon: Icon = Inbox,
    title,
    description,
    primaryAction,
    secondaryAction,
    action,
    guidance,
    suggestions = [],
    className = "",
}) {
    return (
        <section
            className={`relative overflow-hidden rounded-[var(--radius-lg)] border border-emerald-100/90 bg-[radial-gradient(circle_at_top,rgba(16,185,129,0.10),transparent_48%),linear-gradient(180deg,var(--bg-surface),var(--bg-surface-subtle))] p-8 text-center shadow-[0_14px_36px_rgba(15,23,42,0.06)] ${className}`}
        >
            <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100">
                <Icon aria-hidden="true" size={22} />
            </span>

            <h2 className="mt-3 text-lg font-bold">
                {title}
            </h2>

            <p className="mx-auto mt-2 max-w-xl text-sm text-[var(--text-muted)]">
                {description}
            </p>

            {guidance && <p className="mx-auto mt-3 max-w-xl text-sm font-semibold text-emerald-900">{guidance}</p>}

            {suggestions.length > 0 && <div className="mx-auto mt-5 flex max-w-2xl flex-wrap justify-center gap-2">{suggestions.map((suggestion) => <span key={suggestion} className="rounded-full border border-emerald-200 bg-white/80 px-3 py-1.5 text-xs font-bold text-emerald-900 shadow-sm">{suggestion}</span>)}</div>}

            {(primaryAction ||
                secondaryAction ||
                action) && (
                    <div className="mt-5 flex flex-wrap justify-center gap-2">
                        {primaryAction || action}
                        {secondaryAction}
                    </div>
                )}
        </section>
    );
}

export function LoadingState({
    label = "Cargando…",
    inline = false,
}) {
    return (
        <div
            className={`flex items-center justify-center gap-2 text-sm text-[var(--text-muted)] ${inline ? "py-2" : "min-h-40"
                }`}
            role="status"
        >
            <Loader2
                className="animate-spin"
                size={18}
            />

            {label}
        </div>
    );
}

export function ErrorState({
    title = "No pudimos cargar la información",
    description,
    onRetry,
    details,
}) {
    return (
        <section className="rounded-[var(--radius-lg)] border border-[var(--status-danger)]/25 bg-[var(--danger-bg)] p-6">
            <AlertCircle className="text-[var(--status-danger)]" />

            <h2 className="mt-2 font-bold">
                {title}
            </h2>

            <p className="mt-1 text-sm text-[var(--text-secondary)]">
                {description}
            </p>

            {details && (
                <p className="mt-2 text-xs text-[var(--text-muted)]">
                    {details}
                </p>
            )}

            {onRetry && (
                <Button
                    className="mt-4"
                    variant="secondary"
                    onClick={onRetry}
                >
                    Reintentar
                </Button>
            )}
        </section>
    );
}

const alertTones = {
    info: "border-[var(--status-info)]/25 bg-[var(--info-bg)]",
    success:
        "border-[var(--status-success)]/25 bg-[var(--success-bg)]",
    warning:
        "border-[var(--status-warning)]/25 bg-[var(--warning-bg)]",
    danger:
        "border-[var(--status-danger)]/25 bg-[var(--danger-bg)]",
};

export function Alert({
    children,
    title,
    tone = "info",
}) {
    return (
        <div
            role="alert"
            className={`rounded-[var(--radius-md)] border p-4 ${alertTones[tone]}`}
        >
            {title && (
                <p className="font-bold">
                    {title}
                </p>
            )}

            <div className="text-sm text-[var(--text-secondary)]">
                {children}
            </div>
        </div>
    );
}
