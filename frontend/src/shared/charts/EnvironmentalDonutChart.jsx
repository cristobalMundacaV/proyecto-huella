import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { formatNumber } from "@/shared/utils/formatters";

const FALLBACK_COLOR = "#64748b";

/**
 * Reusable donut/pie chart for environmental distributions (alcance,
 * flujo, materiales, etc). Never computes a total or a share itself —
 * `data` must already carry the real, backend-computed values.
 */
export default function EnvironmentalDonutChart({
  data = [],
  height = 260,
  innerRadius = 66,
  outerRadius = 100,
  valueFormatter = (value) => formatNumber(value),
  centerLabel,
  centerValue,
  centerUnit,
  emptyLabel = "Sin datos para graficar",
}) {
  const rows = data.filter((row) => row.value !== null && row.value !== undefined && Number(row.value) > 0);

  if (!rows.length) {
    return (
      <div className="flex h-full min-h-[180px] items-center justify-center text-sm text-[var(--text-muted)]">
        {emptyLabel}
      </div>
    );
  }

  return (
    <div className="relative" style={{ height }}>
      <ResponsiveContainer height="100%" width="100%">
        <PieChart>
          <Pie
            data={rows}
            dataKey="value"
            innerRadius={innerRadius}
            nameKey="name"
            outerRadius={outerRadius}
            paddingAngle={rows.length > 1 ? 2 : 0}
          >
            {rows.map((row) => (
              <Cell fill={row.color || FALLBACK_COLOR} key={row.name} />
            ))}
          </Pie>

          <Tooltip formatter={(value) => valueFormatter(value)} />
        </PieChart>
      </ResponsiveContainer>

      {(centerLabel || centerValue !== undefined) && (
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          {centerLabel && (
            <span className="text-[10px] font-black uppercase tracking-widest text-[var(--text-muted)]">
              {centerLabel}
            </span>
          )}

          {centerValue !== undefined && (
            <b className="mt-1 text-lg text-[var(--text-primary)]">{centerValue}</b>
          )}

          {centerUnit && <span className="text-xs text-[var(--text-muted)]">{centerUnit}</span>}
        </div>
      )}
    </div>
  );
}

export function DonutLegend({ data = [], valueFormatter = (value) => formatNumber(value) }) {
  const rows = data.filter((row) => row.value !== null && row.value !== undefined);
  const total = rows.reduce((sum, row) => sum + Number(row.value || 0), 0);

  if (!rows.length) return null;

  return (
    <ul className="mt-3 space-y-1.5">
      {rows.map((row) => (
        <li className="flex items-center justify-between gap-3 text-sm" key={row.name}>
          <span className="flex min-w-0 items-center gap-2">
            <span aria-hidden="true" className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: row.color || FALLBACK_COLOR }} />
            <span className="min-w-0 leading-4 text-[var(--text-secondary)]">{row.name}</span>
          </span>

          <span className="shrink-0 font-bold text-[var(--text-primary)]">
            {valueFormatter(row.value)}
            {total > 0 && (
              <span className="ml-1.5 text-xs font-semibold text-[var(--text-muted)]">
                {Math.round((Number(row.value) / total) * 100)}%
              </span>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
