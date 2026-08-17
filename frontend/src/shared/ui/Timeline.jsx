import {
    Activity,
    AlertTriangle,
    CheckCircle2,
    DatabaseZap,
    FileCheck2,
    ShieldCheck,
} from "lucide-react";

const presentationByType = value => {
    const type = String(value || "").toLowerCase();

    if (
        type.includes("evidencia") ||
        type.includes("documento")
    ) {
        return {
            Icon: FileCheck2,
            label: "Evidencia",
            iconClass: "bg-emerald-100 text-emerald-700",
            borderClass: "border-l-emerald-500",
            surfaceClass: "bg-emerald-50/70",
        };
    }

    if (
        type.includes("import") ||
        type.includes("ingesta")
    ) {
        return {
            Icon: DatabaseZap,
            label: "Importación",
            iconClass: "bg-teal-100 text-teal-700",
            borderClass: "border-l-teal-500",
            surfaceClass: "bg-teal-50/70",
        };
    }

    if (
        type.includes("problema") ||
        type.includes("alerta")
    ) {
        return {
            Icon: AlertTriangle,
            label: "Atención",
            iconClass: "bg-amber-100 text-amber-700",
            borderClass: "border-l-amber-500",
            surfaceClass: "bg-amber-50/70",
        };
    }

    if (
        type.includes("revision") ||
        type.includes("validacion")
    ) {
        return {
            Icon: ShieldCheck,
            label: "Revisión",
            iconClass: "bg-sky-100 text-sky-700",
            borderClass: "border-l-sky-500",
            surfaceClass: "bg-sky-50/70",
        };
    }

    if (
        type.includes("accion") ||
        type.includes("resultado")
    ) {
        return {
            Icon: CheckCircle2,
            label: "Gestión",
            iconClass: "bg-emerald-100 text-emerald-700",
            borderClass: "border-l-emerald-600",
            surfaceClass: "bg-emerald-50/70",
        };
    }

    return {
        Icon: Activity,
        label: "Actividad",
        iconClass: "bg-slate-100 text-slate-600",
        borderClass: "border-l-slate-400",
        surfaceClass: "bg-slate-50/80",
    };
};

export function Timeline({
    children,
    className = "",
}) {
    return (
        <ol className={`space-y-3 ${className}`}>
            {children}
        </ol>
    );
}

export function TimelineItem({
    timestamp,
    title,
    description,
    type,
    icon,
    label,
    status,
    compact = false,
}) {
    const presentation =
        presentationByType(type || status);

    const Icon = icon || presentation.Icon;

    const resolvedLabel =
        label || presentation.label;

    return (
        <li>
            <article
                className={`rounded-xl border border-[var(--border-subtle)] border-l-4 ${presentation.borderClass} ${presentation.surfaceClass} ${compact ? "p-3" : "p-3.5"
                    } transition hover:-translate-y-0.5 hover:shadow-sm`}
            >
                <div className="flex items-start gap-3">
                    <div
                        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${presentation.iconClass}`}
                    >
                        <Icon
                            aria-hidden="true"
                            size={18}
                        />
                    </div>

                    <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="text-[11px] font-black uppercase tracking-[0.12em] text-[var(--text-muted)]">
                                {resolvedLabel}
                            </span>

                            {timestamp && (
                                <time className="text-[11px] text-[var(--text-muted)]">
                                    {timestamp}
                                </time>
                            )}
                        </div>

                        <h3 className="mt-1 font-black leading-snug text-[var(--text-primary)]">
                            {title}
                        </h3>

                        {description && (
                            <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">
                                {description}
                            </p>
                        )}
                    </div>
                </div>
            </article>
        </li>
    );
}