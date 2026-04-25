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

const formatNumber = (value, maximumFractionDigits = 2) =>
  new Intl.NumberFormat("es-CL", {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  }).format(Number(value));

const tooltipContentStyle = {
  backgroundColor: "#0F172A",
  border: "1px solid #1E293B",
  borderRadius: "12px",
  color: "#F8FAFC",
};

function SimuladorOptimizacion({ data, onSimulationChange }) {
  const [dieselReduction, setDieselReduction] = useState(25);
  const [electricityIncrease, setElectricityIncrease] = useState(10);
  const [selectedCompany, setSelectedCompany] = useState("Todas");

  const companies = useMemo(() => {
    const uniqueCompanies = new Set(data.datos.map((row) => row.empresa));
    return ["Todas", ...Array.from(uniqueCompanies)];
  }, [data]);

  const simulation = useMemo(() => {
    const appliesToCompany = (row) =>
      selectedCompany === "Todas" || row.empresa === selectedCompany;

    const rows = data.datos.map((row) => {
      const activity = String(row.actividad).toLowerCase();
      let simulatedQuantity = Number(row.cantidad);

      if (appliesToCompany(row) && activity === "diesel") {
        simulatedQuantity *= 1 - dieselReduction / 100;
      }

      if (appliesToCompany(row) && activity === "electricidad") {
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
    const activityTotals = rows.reduce((totals, row) => {
      totals[row.actividad] =
        (totals[row.actividad] || 0) + row.emisiones_simuladas;
      return totals;
    }, {});
    const companyTotals = rows.reduce((totals, row) => {
      totals[row.empresa] = (totals[row.empresa] || 0) + row.emisiones_simuladas;
      return totals;
    }, {});
    const criticalActivity =
      Object.entries(activityTotals).sort((a, b) => b[1] - a[1])[0]?.[0] ||
      "Sin datos";
    const companyChart = Object.entries(companyTotals).map(
      ([empresa, emisiones]) => ({
        empresa,
        emisiones,
      })
    );

    return {
      rows,
      totalActual,
      totalSimulado,
      reductionPct,
      criticalActivity,
      companyChart,
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
      criticalActivity: simulation.criticalActivity,
      executiveInsight,
    });
  }, [
    dieselReduction,
    electricityIncrease,
    executiveInsight,
    onSimulationChange,
    selectedCompany,
    simulation.criticalActivity,
    simulation.reductionPct,
    simulation.totalActual,
    simulation.totalSimulado,
  ]);

  return (
    <section className="rounded-3xl bg-slate-900 border border-slate-800 p-6 shadow-xl">
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="flex items-center gap-2 text-sm font-semibold text-emerald-300">
              <SlidersHorizontal size={16} />
              Simulador de optimizacion
            </p>
            <h2 className="mt-1 text-2xl font-bold">
              Ajusta decisiones y mide impacto en vivo
            </h2>
          </div>

          <label className="min-w-56">
            <span className="text-xs text-slate-500">Empresa</span>
            <select
              value={selectedCompany}
              onChange={(event) => setSelectedCompany(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200 outline-none transition focus:border-emerald-400/50"
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
            label="Aumentar electricidad"
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
          <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-5">
            <p className="flex items-center gap-2 text-sm font-semibold text-emerald-200">
              <Lightbulb size={18} />
              Recomendacion ejecutiva
            </p>
            <p className="mt-3 text-lg font-bold text-emerald-100">
              {executiveInsight}
            </p>
            <p className="mt-2 text-sm leading-6 text-emerald-300">
              Reducir diesel en {dieselReduction}% y ajustar electricidad en{" "}
              {electricityIncrease}% deja como actividad critica a{" "}
              <strong>{simulation.criticalActivity}</strong>.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
            <h3 className="text-sm font-semibold text-slate-200">
              Emisiones simuladas por empresa
            </h3>
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={simulation.companyChart}>
                  <XAxis dataKey="empresa" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" tickFormatter={formatNumber} />
                  <Tooltip
                    contentStyle={tooltipContentStyle}
                    cursor={false}
                    formatter={(value) => [
                      `${formatNumber(value)} kg CO2e`,
                      "Emisiones",
                    ]}
                    labelStyle={{ color: "#F8FAFC" }}
                    itemStyle={{ color: "#34D399" }}
                  />
                  <Bar
                    animationDuration={650}
                    dataKey="emisiones"
                    fill="#34D399"
                    radius={[10, 10, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function SliderControl({ color, label, max, onChange, value }) {
  const accent = color === "sky" ? "text-sky-300" : "text-emerald-300";

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm font-semibold text-slate-200">{label}</p>
        <p className={`text-lg font-bold ${accent}`}>{value}%</p>
      </div>
      <input
        type="range"
        min="0"
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-5 w-full accent-emerald-400"
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
      ? "border-red-400/20 bg-red-400/10 text-red-200"
      : "border-emerald-400/20 bg-emerald-400/10 text-emerald-200";

  return (
    <div className={`rounded-2xl border p-5 transition ${toneClass}`}>
      <div className="mb-4">{icon}</div>
      <p className="text-sm text-slate-400">{label}</p>
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
