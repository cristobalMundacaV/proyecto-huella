import { useState } from "react";
import { Activity, AlertTriangle, Factory, Upload } from "lucide-react";

import { compareScenarioFiles } from "./services/api";

const formatNumber = (value, maximumFractionDigits = 2) =>
  new Intl.NumberFormat("es-CL", {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  }).format(Number(value));

const formatPercent = (value) => `${formatNumber(value, 1)}%`;

function ComparacionEscenario() {
  const [datasetActual, setDatasetActual] = useState(null);
  const [datasetSimulado, setDatasetSimulado] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const canCompare = datasetActual && datasetSimulado && !loading;

  const handleCompare = async () => {
    if (!canCompare) {
      return;
    }

    setLoading(true);
    setError("");

    try {
      const result = await compareScenarioFiles(datasetActual, datasetSimulado);
      setComparison(result);
    } catch (requestError) {
      setError(
        requestError.response?.data?.error ||
          "No se pudo comparar los escenarios."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-3xl bg-slate-900 border border-slate-800 p-4 sm:p-6 shadow-xl">
      <div className="flex flex-col gap-6">
        <div>
          <p className="text-sm font-semibold text-emerald-300">
            Simulacion de escenarios
          </p>
          <h2 className="mt-1 text-2xl font-bold">
            Compara impacto actual vs optimizado
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_1fr_auto] gap-4">
          <ScenarioUploader
            color="red"
            file={datasetActual}
            label="Dataset base"
            onChange={setDatasetActual}
          />
          <ScenarioUploader
            color="green"
            file={datasetSimulado}
            label="Dataset simulado"
            onChange={setDatasetSimulado}
          />
          <button
            type="button"
            onClick={handleCompare}
            disabled={!canCompare}
            className="w-full lg:w-auto h-full min-h-16 lg:min-h-24 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-6 font-semibold text-emerald-200 transition hover:bg-emerald-400/20 disabled:cursor-not-allowed disabled:border-slate-800 disabled:bg-slate-950 disabled:text-slate-600"
          >
            {loading ? "Comparando..." : "Comparar"}
          </button>
        </div>

        {error && (
          <p className="rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-200">
            {error}
          </p>
        )}

        {comparison && <ComparisonResult comparison={comparison} />}
      </div>
    </section>
  );
}

function ScenarioUploader({ color, file, label, onChange }) {
  const isBase = color === "red";
  const accentClass = isBase
    ? "border-red-400/30 bg-red-400/10 text-red-200"
    : "border-emerald-400/30 bg-emerald-400/10 text-emerald-200";

  return (
    <label
      className={`flex min-h-24 cursor-pointer items-center gap-4 rounded-2xl border px-4 py-4 transition hover:bg-slate-800 ${accentClass}`}
    >
      <div className="rounded-2xl border border-current/20 p-3">
        <Upload size={20} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-slate-400">{label}</p>
        <p className="mt-1 truncate text-sm font-semibold">
          {file?.name || "Seleccionar archivo"}
        </p>
      </div>
      <input
        type="file"
        accept=".csv,.xlsx,.xls"
        onChange={(event) => onChange(event.target.files?.[0] || null)}
        className="hidden"
      />
    </label>
  );
}

function ComparisonResult({ comparison }) {
  const reductionIsPositive = comparison.reduccion_pct >= 0;
  const reductionClass = reductionIsPositive
    ? "text-emerald-300"
    : "text-red-300";

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ComparisonCard
          icon={<Activity />}
          label="Emisiones actuales"
          tone="red"
          value={`${formatNumber(comparison.total_actual)} kg CO2e`}
        />
        <ComparisonCard
          icon={<Activity />}
          label="Emisiones simuladas"
          tone="green"
          value={`${formatNumber(comparison.total_simulado)} kg CO2e`}
        />
        <ComparisonCard
          icon={<Factory />}
          label="Reduccion total"
          tone={reductionIsPositive ? "green" : "red"}
          value={
            <span className={reductionClass}>
              {reductionIsPositive ? "-" : "+"}
              {formatPercent(Math.abs(comparison.reduccion_pct))}
            </span>
          }
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 sm:p-5">
          <div className="flex items-center gap-3 text-slate-300">
            <AlertTriangle size={18} className="text-amber-300" />
            <p className="text-sm font-semibold">Actividad critica</p>
          </div>
          <p className="mt-3 text-lg font-bold">
            <span className="text-red-300">
              {comparison.actividad_critica_actual}
            </span>
            <span className="mx-2 text-slate-500">→</span>
            <span className="text-emerald-300">
              {comparison.actividad_critica_simulada}
            </span>
          </p>
          <p className="mt-2 text-sm text-slate-400">
            {comparison.actividad_critica_cambio
              ? "La actividad critica cambio en el escenario simulado."
              : "La actividad critica se mantiene, pero el impacto puede reducirse."}
          </p>
        </div>

        <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-4 sm:p-5">
          <div className="flex items-center gap-3 text-emerald-200">
            <Factory size={18} />
            <p className="text-sm font-semibold">Empresa mas optimizada</p>
          </div>
          <p className="mt-3 text-lg font-bold text-emerald-200">
            {comparison.empresa_mas_optimizada.empresa}
          </p>
          <p className="mt-2 text-sm text-emerald-300">
            {formatPercent(comparison.empresa_mas_optimizada.reduccion_pct)} de
            reduccion frente al escenario base.
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-sky-400/20 bg-sky-400/10 p-4 sm:p-5">
        <p className="text-sm font-semibold text-sky-200">
          Recomendacion estrategica
        </p>
        <p className="mt-2 text-sm text-sky-100">{comparison.recomendacion}</p>
      </div>
    </div>
  );
}

function ComparisonCard({ icon, label, tone, value }) {
  const toneClass =
    tone === "red"
      ? "border-red-400/20 bg-red-400/10 text-red-200"
      : "border-emerald-400/20 bg-emerald-400/10 text-emerald-200";

  return (
    <div className={`rounded-2xl border p-4 sm:p-5 ${toneClass}`}>
      <div className="mb-4">{icon}</div>
      <p className="text-sm text-slate-400">{label}</p>
      <h3 className="mt-1 text-2xl font-bold">{value}</h3>
    </div>
  );
}

export default ComparacionEscenario;
