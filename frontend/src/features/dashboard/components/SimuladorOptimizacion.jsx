import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, Factory, Lightbulb, SlidersHorizontal } from "lucide-react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  isDieselEmission,
  isElectricityEmission,
  isTransportEmission,
} from "@/shared/utils/emissionSemantics";

const formatNumber = (value, maximumFractionDigits = 2) =>
  new Intl.NumberFormat("es-CL", {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  }).format(Number(value));

const tooltipContentStyle = {
  backgroundColor: "#FCFDFC",
  border: "1px solid #B7C6BD",
  borderRadius: "12px",
  color: "#1F2937",
  boxShadow: "0 16px 35px rgba(15, 23, 42, 0.12)",
};

const horizontalActiveBarStyle = {
  fill: "#6B7F75",
  fillOpacity: 0.32,
  radius: [0, 10, 10, 0],
};

function truncateChartLabel(value) {
  const text = String(value || "");
  return text.length > 28 ? `${text.slice(0, 28)}...` : text;
}

function SimuladorOptimizacion({ data, onSimulationChange }) {
  const [dieselReduction, setDieselReduction] = useState(25);
  const [electricityIncrease, setElectricityIncrease] = useState(10);
  const [selectedCompany, setSelectedCompany] = useState("Todas");

  const companies = useMemo(() => {
    const uniqueCompanies = new Set(data.datos.map((row) => row.constructora));
    return ["Todas", ...Array.from(uniqueCompanies)];
  }, [data]);

  const simulation = useMemo(() => {
    const appliesToCompany = (row) =>
      selectedCompany === "Todas" || row.constructora === selectedCompany;

    const rows = data.datos.map((row) => {
      let simulatedQuantity = Number(row.cantidad);

      if (appliesToCompany(row) && isDieselEmission(row) && !isTransportEmission(row)) {
        simulatedQuantity *= 1 - dieselReduction / 100;
      }

      if (appliesToCompany(row) && isElectricityEmission(row)) {
        simulatedQuantity *= 1 + electricityIncrease / 100;
      }

      return {
        ...row,
        cantidad_simulada: simulatedQuantity,
        emisiones_simuladas:
          simulatedQuantity * Number(row.factor_emision || 0),
      };
    });

    const totalActual = data.datos.reduce(
      (total, row) => total + Number(row.emisiones || 0),
      0
    );
    const totalSimulado = rows.reduce(
      (total, row) => total + Number(row.emisiones_simuladas || 0),
      0
    );
    const reductionPct =
      totalActual > 0 ? ((totalActual - totalSimulado) / totalActual) * 100 : 0;
    const sourceTotals = rows.reduce((totals, row) => {
      totals[row.fuente_emision] =
        (totals[row.fuente_emision] || 0) + row.emisiones_simuladas;
      return totals;
    }, {});
    const unitTotals = rows.reduce((totals, row) => {
      const unitLabel = row.etapa || "Sin unidad";
      totals[unitLabel] = (totals[unitLabel] || 0) + row.emisiones_simuladas;
      return totals;
    }, {});
    const criticalSource =
      Object.entries(sourceTotals).sort((a, b) => b[1] - a[1])[0]?.[0] ||
      "Sin datos";
    const unitChart = Object.entries(unitTotals).map(
      ([unidad, emisiones]) => ({
        unidad,
        emisiones,
      })
    );

    return {
      rows,
      totalActual,
      totalSimulado,
      reductionPct,
      criticalSource,
      unitChart,
    };
  }, [data, dieselReduction, electricityIncrease, selectedCompany]);

  const executiveInsight =
    simulation.reductionPct >= 5
      ? `Reduccion significativa del ${formatNumber(
          simulation.reductionPct,
          1
        )}% en emisiones totales.`
      : simulation.reductionPct > 0
        ? `Reduccion moderada del ${formatNumber(
            simulation.reductionPct,
            1
          )}% en emisiones totales.`
        : `El escenario aumenta las emisiones en ${formatNumber(
            Math.abs(simulation.reductionPct),
            1
          )}%. Revisa el crecimiento electrico o el alcance seleccionado.`;
  const unitChartRows = simulation.unitChart.length;
  const unitBarSize =
    unitChartRows <= 1 ? 34 : unitChartRows <= 2 ? 30 : unitChartRows <= 4 ? 24 : 18;
  const unitChartHeight =
    unitChartRows <= 1
      ? 220
      : Math.min(380, Math.max(280, unitChartRows * 72));

  useEffect(() => {
    if (!onSimulationChange) {
      return;
    }

    onSimulationChange({
      dieselReduction,
      electricityIncrease,
      selectedCompany,
      totalActual: simulation.totalActual,
      totalSimulado: simulation.totalSimulado,
      reductionPct: simulation.reductionPct,
      criticalSource: simulation.criticalSource,
      executiveInsight,
    });
  }, [
    dieselReduction,
    electricityIncrease,
    executiveInsight,
    onSimulationChange,
    selectedCompany,
    simulation.criticalSource,
    simulation.reductionPct,
    simulation.totalActual,
    simulation.totalSimulado,
  ]);

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="flex items-center gap-2 text-sm font-bold text-[var(--primary-dark)]">
              <SlidersHorizontal size={16} />
              Simulador de optimizacion
            </p>
            <h2 className="mt-1 text-2xl font-bold text-[var(--text-main)]">
              Ajusta decisiones y mide impacto en vivo
            </h2>
          </div>

          <label className="min-w-56">
            <span className="text-xs font-medium text-[var(--text-muted)]">Constructora</span>
            <select
              value={selectedCompany}
              onChange={(event) => setSelectedCompany(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/50"
            >
              {companies.map((company) => (
                <option key={company} value={company}>
                  {company}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SliderControl
            color="emerald"
            label="Reducir diesel"
            max={80}
            onChange={setDieselReduction}
            value={dieselReduction}
          />
          <SliderControl
            color="sky"
            label="ElectrificaciÃ³n de procesos"
            max={60}
            onChange={setElectricityIncrease}
            value={electricityIncrease}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SimulatorCard
            icon={<Activity />}
            label="Emisiones actuales"
            tone="red"
            value={simulation.totalActual}
            suffix=" kg CO2e"
          />
          <SimulatorCard
            icon={<Activity />}
            label="Emisiones simuladas"
            tone="green"
            value={simulation.totalSimulado}
            suffix=" kg CO2e"
          />
          <SimulatorCard
            icon={<Factory />}
            label="Impacto estimado"
            tone={simulation.reductionPct >= 0 ? "green" : "red"}
            value={Math.abs(simulation.reductionPct)}
            prefix={simulation.reductionPct >= 0 ? "-" : "+"}
            suffix="%"
            maximumFractionDigits={1}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.2fr] gap-4">
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] p-4 sm:p-5">
            <p className="flex items-center gap-2 text-sm font-bold text-[var(--primary-dark)]">
              <Lightbulb size={18} />
              Recomendacion ejecutiva
            </p>
            <p className="mt-3 text-lg font-bold text-[var(--text-main)]">
              {executiveInsight}
            </p>
            <p className="mt-2 text-sm font-medium leading-6 text-[#334155]">
              Reducir diesel en {dieselReduction}% y ajustar electricidad en{" "}
              {electricityIncrease}% deja como fuente_emision critica a{" "}
              <strong>{simulation.criticalSource}</strong>.
            </p>
          </div>

          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 sm:p-5">
            <h3 className="text-sm font-bold text-[var(--text-main)]">
              Emisiones simuladas por etapa
            </h3>
            <div className="mt-4" style={{ height: unitChartHeight }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={simulation.unitChart}
                  layout="vertical"
                  margin={{ top: 10, right: 10, left: 24, bottom: 10 }}
                >
                  <XAxis
                    type="number"
                    stroke="#64748B"
                    tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }}
                    tickFormatter={formatNumber}
                  />
                  <YAxis
                    dataKey="unidad"
                    interval={0}
                    stroke="#64748B"
                    tick={{ fill: "#475569", fontSize: 11, fontWeight: 600 }}
                    tickFormatter={truncateChartLabel}
                    type="category"
                    width={150}
                  />
                  <Tooltip
                    contentStyle={tooltipContentStyle}
                    cursor={false}
                    formatter={(value) => [
                      `${formatNumber(value)} kg CO2e`,
                      "Emisiones",
                    ]}
                    labelStyle={{ color: "#1F2937" }}
                    itemStyle={{ color: "#0B7D5D" }}
                  />
                  <Bar
                    activeBar={horizontalActiveBarStyle}
                    animationDuration={650}
                    barSize={unitBarSize}
                    dataKey="emisiones"
                    fill="#34D399"
                    radius={[0, 10, 10, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-2 text-xs font-medium text-[var(--text-muted)]">
              Pasa el cursor sobre cada barra para ver el detalle de la etapa.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function SliderControl({ color, label, max, onChange, value }) {
  const accent = color === "sky" ? "text-[var(--secondary)]" : "text-[var(--primary-dark)]";

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 sm:p-5">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm font-semibold text-[var(--text-main)]">{label}</p>
        <p className={`text-lg font-bold ${accent}`}>{value}%</p>
      </div>
      <input
        type="range"
        min="0"
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-5 w-full accent-[var(--primary)]"
      />
    </div>
  );
}

function SimulatorCard({
  icon,
  label,
  maximumFractionDigits = 2,
  prefix = "",
  suffix = "",
  tone,
  value,
}) {
  const displayValue = useCountUp(value, maximumFractionDigits);
  const toneClass =
    tone === "red"
      ? "border-[#F1B8B8] bg-[var(--danger-bg)] text-[#B42318]"
      : "border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]";

  return (
    <div className={`rounded-2xl border p-4 shadow-[var(--shadow-soft)] transition sm:p-5 ${toneClass}`}>
      <div className="mb-4 flex items-center gap-3">
        <div>{icon}</div>
        <p className="text-sm font-medium text-[var(--text-muted)]">{label}</p>
      </div>
      <h3 className="mt-1 text-2xl font-bold">
        {prefix}
        {displayValue}
        {suffix}
      </h3>
    </div>
  );
}

function useCountUp(value, maximumFractionDigits) {
  const [displayValue, setDisplayValue] = useState(value);
  const displayValueRef = useRef(value);

  useEffect(() => {
    const startValue = displayValueRef.current;
    const endValue = Number(value);
    const duration = 450;
    const startTime = performance.now();
    let frameId;

    const animate = (time) => {
      const progress = Math.min((time - startTime) / duration, 1);
      const easedProgress = 1 - (1 - progress) ** 3;
      const nextValue = startValue + (endValue - startValue) * easedProgress;
      displayValueRef.current = nextValue;
      setDisplayValue(nextValue);

      if (progress < 1) {
        frameId = requestAnimationFrame(animate);
      }
    };

    frameId = requestAnimationFrame(animate);

    return () => cancelAnimationFrame(frameId);
  }, [value]);

  return formatNumber(displayValue, maximumFractionDigits);
}

export default SimuladorOptimizacion;
