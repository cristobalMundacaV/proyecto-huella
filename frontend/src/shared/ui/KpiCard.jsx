import { createElement, isValidElement } from "react";
import { Card, CardContent } from "./Card";

const statusColors = {
    neutral: "text-[var(--status-neutral)]",
    success: "text-[var(--status-success)]",
    emerald: "text-[var(--status-success)]",
    warning: "text-[var(--status-warning)]",
    amber: "text-[var(--status-warning)]",
    danger: "text-[var(--status-danger)]",
    info: "text-[var(--status-info)]",
    cyan: "text-[var(--status-info)]",
};

export default function KpiCard({
    label,
    title,
    value,
    unit,
    helper,
    detail,
    icon,
    loading = false,
    status = "neutral",
    tone,
}) {
    const missing = value === null || value === undefined || value === "";
    const visualStatus = tone || status;

    const isIconComponent =
        typeof icon === "function" ||
        (typeof icon === "object" &&
            icon !== null &&
            "$$typeof" in icon);

    const renderedIcon = isValidElement(icon)
        ? icon
        : isIconComponent
            ? createElement(icon, {
                size: 20,
                "aria-hidden": true,
            })
            : null;

    return (
        <Card>
            <CardContent>
                <div className="flex items-start justify-between gap-3">
                    <div>
                        <p className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
                            {label || title}
                        </p>

                        <p className="mt-2 text-2xl font-black text-[var(--text-primary)]">
                            {loading ? (
                                "Cargando…"
                            ) : missing ? (
                                "Sin datos"
                            ) : (
                                <>
                                    {value}
                                    {unit && (
                                        <span className="ml-1 text-sm text-[var(--text-secondary)]">
                                            {unit}
                                        </span>
                                    )}
                                </>
                            )}
                        </p>

                        {(helper || detail) && (
                            <p className="mt-2 text-sm text-[var(--text-muted)]">
                                {helper || detail}
                            </p>
                        )}
                    </div>

                    {renderedIcon && (
                        <span
                            className={
                                statusColors[visualStatus] || statusColors.neutral
                            }
                        >
                            {renderedIcon}
                        </span>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}