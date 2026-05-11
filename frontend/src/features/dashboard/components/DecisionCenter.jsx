import SimuladorOptimizacion from "./SimuladorOptimizacion";
import { formatNumber } from "@/shared/utils/formatters";

function DecisionCenter({
  data,
  optimizedScenario,
  onOptimize,
  onSimulationChange,
}) {
  return (
    <div className="space-y-6">
      <SimuladorOptimizacion
        data={data}
        onSimulationChange={onSimulationChange}
      />

      <div className="space-y-6 rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-[var(--shadow-card)]">
        <div>
          <p className="text-sm font-bold text-[var(--primary-dark)]">
            Optimizacion automatica
          </p>
          <h3 className="text-xl font-bold text-[var(--text-main)]">
            Carbono Zero recomienda el mejor escenario
          </h3>
        </div>


        {optimizedScenario && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-5">
              <p className="text-sm font-medium text-[var(--text-muted)]">Reducir diesel</p>
              <h3 className="text-2xl font-bold text-[var(--primary-dark)]">
                {optimizedScenario.dieselReduction}%
              </h3>
            </div>

            <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-5">
              <p className="text-sm font-medium text-[var(--text-muted)]">Ajustar electricidad</p>
              <h3 className="text-2xl font-bold text-[#075985]">
                +{optimizedScenario.electricityIncrease}%
              </h3>
            </div>

            <div className="rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] p-5">
              <p className="text-sm font-medium text-[var(--text-muted)]">Reduccion estimada</p>
              <h3 className="text-2xl font-bold text-[var(--primary-dark)]">
                {formatNumber(optimizedScenario.reductionPct, 1)}%
              </h3>
            </div>
          </div>
        )}

        {optimizedScenario && (
          <div className="space-y-4 rounded-2xl border border-[var(--border)] bg-[var(--info-bg)] p-5">
            <p className="text-sm font-bold text-[#075985]">
              Decision generada por Carbono Zero
            </p>
            <p className="mt-2 leading-7 text-[var(--text-main)]">
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
            <p className="rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] px-4 py-3 text-sm font-medium text-[var(--primary-dark)]">
              Recomendacion: ejecutar un piloto con esta configuracion y
              monitorear la reduccion real antes de escalarla al resto de la
              operacion.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default DecisionCenter;
