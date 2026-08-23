import { createElement, isValidElement } from "react";
import { Card, CardContent } from "./Card";
import { formatNumber } from "@/shared/utils/formatters";

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
    const numericValue = (typeof value === "number" || (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value))))
        ? formatNumber(value)
        : value;

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
        <Card className="border-slate-200/80 bg-[linear-gradient(145deg,rgba(255,255,255,1),rgba(248,250,252,0.92))] shadow-[0_10px_28px_rgba(15,23,42,0.055)]">
            <CardContent className="h-full">
                <div className="flex items-start justify-between gap-3">
                    <div>
                        <p className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
                            {label || title}
                        </p>

                        <p className="mt-2 text-2xl font-black text-[var(--text-primary)]">
                            {loading ? (
                                <span className="block h-7 w-24 animate-pulse rounded-lg bg-slate-200" aria-label="Cargando valor" />
                            ) : missing ? (
                                "Sin datos"
                            ) : (
                                <>
                                    {numericValue}
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
                            className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white shadow-sm ring-1 ring-slate-200/80 ${statusColors[visualStatus] || statusColors.neutral}`}
                        >
                            {renderedIcon}
                        </span>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
