import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatNumber } from "@/shared/utils/formatters";

const FALLBACK_COLOR = "#0f766e";

/**
 * Reusable bar chart for per-flow / per-category comparisons. `data` must
 * already carry backend-computed values — this component only renders.
 */
export default function EnvironmentalBarChart({
  data = [],
  height = 260,
  valueFormatter = (value) => formatNumber(value),
  emptyLabel = "Sin datos para graficar",
  color = FALLBACK_COLOR,
}) {
  const rows = data.filter((row) => row.value !== null && row.value !== undefined);

  if (!rows.length) {
    return (
      <div className="flex h-full min-h-[180px] items-center justify-center text-sm text-[var(--text-muted)]">
        {emptyLabel}
      </div>
    );
  }

  return (
    <div style={{ height }}>
      <ResponsiveContainer height="100%" width="100%">
        <BarChart data={rows} margin={{ top: 10, right: 8, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" interval={0} angle={rows.length > 4 ? -15 : 0} height={rows.length > 4 ? 52 : 30} textAnchor={rows.length > 4 ? "end" : "middle"} />
          <YAxis tickFormatter={(value) => formatNumber(value, 0)} width={56} />
          <Tooltip formatter={(value) => valueFormatter(value)} />
          <Bar dataKey="value" radius={[8, 8, 0, 0]}>
            {rows.map((row) => (
              <Cell fill={row.color || color} key={row.name} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
