import { formatNumber } from "@/shared/utils/formatters";

function EmissionValue({
    value,
    decimals = 1,
    className = "",
    unitClassName = "",
}) {
    return (
        <span className={`inline-flex items-baseline justify-center gap-1 text-emerald-700 ${className}`}>
            <span>{formatNumber(value || 0, decimals)}</span>
            <span className={`text-[0.62em] font-black uppercase tracking-tight text-emerald-800 ${unitClassName}`}>
                kg CO<sub>2</sub>e
            </span>
        </span>
    );
}

export default EmissionValue;