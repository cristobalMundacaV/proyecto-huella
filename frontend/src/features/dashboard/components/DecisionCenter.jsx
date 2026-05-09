import SimuladorOptimizacion from "./SimuladorOptimizacion";
import { formatNumber } from "@/shared/utils/formatters";

function DecisionCenter({
  data,
  optimizedScenario,
  onOptimize,
  onSimulationChange,
}) {
  return (
    <section className="rounded-3xl bg-slate-900 border border-slate-800 p-6 space-y-6 shadow-xl">

      <SimuladorOptimizacion
        data={data}
        onSimulationChange={onSimulationChange}
      />

      <div className="rounded-3xl border border-slate-800 bg-slate-950 p-6 space-y-6">
        <div>
          <p className="text-emerald-400 text-sm font-semibold">
            Optimizacion automatica
          </p>
          <h3 className="text-xl font-bold">
            Carbono Zero recomienda el mejor escenario
          </h3>
        </div>


        {optimizedScenario && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-2xl bg-slate-950 border border-slate-800 p-5">
              <p className="text-slate-400 text-sm">Reducir diesel</p>
              <h3 className="text-2xl font-bold text-emerald-300">
                {optimizedScenario.dieselReduction}%
              </h3>
            </div>

            <div className="rounded-2xl bg-slate-950 border border-slate-800 p-5">
              <p className="text-slate-400 text-sm">Ajustar electricidad</p>
              <h3 className="text-2xl font-bold text-cyan-300">
                +{optimizedScenario.electricityIncrease}%
              </h3>
            </div>

            <div className="rounded-2xl bg-emerald-400/10 border border-emerald-400/20 p-5">
              <p className="text-slate-400 text-sm">Reduccion estimada</p>
              <h3 className="text-2xl font-bold text-emerald-300">
                {formatNumber(optimizedScenario.reductionPct, 1)}%
              </h3>
            </div>
          </div>
        )}

        {optimizedScenario && (
          <div className="rounded-2xl bg-cyan-400/10 border border-cyan-400/20 p-5 space-y-4">
            <p className="text-cyan-300 text-sm font-semibold">
              Decision generada por Carbono Zero
            </p>
            <p className="text-slate-200 mt-2 leading-7">
              Carbono Zero evaluo automaticamente{" "}
              <strong>{optimizedScenario.evaluatedScenarios}</strong>{" "}
              combinaciones posibles de decision y selecciono la de mayor
              reduccion neta: reducir diesel en{" "}
              <strong>{optimizedScenario.dieselReduction}%</strong> y ajustar la
              electricidad en{" "}
              <strong>{optimizedScenario.electricityIncrease}%</strong>. Esto
              permitiria bajar las emisiones desde{" "}
              <strong>
                {formatNumber(optimizedScenario.currentTotal, 1)} kg CO2e
              </strong>{" "}
              a{" "}
              <strong>
                {formatNumber(optimizedScenario.simulatedTotal, 1)} kg CO2e
              </strong>
              .
            </p>
            <p className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">
              Recomendacion: ejecutar un piloto con esta configuracion y
              monitorear la reduccion real antes de escalarla al resto de la
              operacion.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

export default DecisionCenter;
