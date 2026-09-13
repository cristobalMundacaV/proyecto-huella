import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatNumber } from "@/shared/utils/formatters";

const FALLBACK_COLOR = "#0891b2";

/**
 * Reusable time-evolution line chart (GEI, energía, agua, residuos, …).
 * `data` must already be backend-computed period values — never estimated
 * here — each row is `{ label, value }`.
 */
export default function EnvironmentalTrendChart({
  data = [],
  height = 260,
  color = FALLBACK_COLOR,
  valueFormatter = (value) => formatNumber(value),
  emptyLabel = "Sin evolución disponible para este período",
}) {
  const rows = data.filter((row) => row.value !== null && row.value !== undefined);

  if (rows.length < 2) {
    return (
      <div className="flex h-full min-h-[180px] items-center justify-center text-center text-sm text-[var(--text-muted)]">
        {rows.length === 1 ? "Se requiere más de un período para mostrar una tendencia." : emptyLabel}
      </div>
    );
  }

  return (
    <div style={{ height }}>
      <ResponsiveContainer height="100%" width="100%">
        <LineChart data={rows} margin={{ top: 10, right: 12, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" />
          <YAxis tickFormatter={(value) => formatNumber(value, 0)} width={56} />
          <Tooltip formatter={(value) => valueFormatter(value)} />
          <Line dataKey="value" dot={{ r: 3 }} stroke={color} strokeWidth={3} type="monotone" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
