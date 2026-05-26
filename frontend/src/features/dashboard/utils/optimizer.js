import {
  isDieselActivity,
  isElectricityActivity,
  isTransportActivity,
} from "@/shared/utils/activitySemantics";

export function optimizeScenario(rows) {
  let bestScenario = null;
  let evaluatedScenarios = 0;

  const currentTotal = rows.reduce(
    (acc, row) => acc + Number(row.emisiones),
    0
  );
  const hasDiesel = rows.some(
    (row) => isDieselActivity(row) && !isTransportActivity(row)
  );
  const hasElectricity = rows.some(isElectricityActivity);

  if (!hasDiesel && !hasElectricity) {
    return {
      dieselReduction: 0,
      electricityIncrease: 0,
      currentTotal,
      evaluatedScenarios: 0,
      simulatedTotal: currentTotal,
      reductionPct: 0,
      rows,
      message: "No hay registros optimizables detectados.",
    };
  }

  const dieselOptions = hasDiesel
    ? Array.from({ length: 17 }, (_, index) => index * 5)
    : [0];
  const electricityOptions = hasElectricity
    ? Array.from({ length: 13 }, (_, index) => index * 5)
    : [0];

  for (const dieselReduction of dieselOptions) {
    for (const electricityIncrease of electricityOptions) {
      evaluatedScenarios += 1;
      const simulatedRows = rows.map((row) => {
        let cantidad = Number(row.cantidad);

        if (isDieselActivity(row) && !isTransportActivity(row)) {
          cantidad *= 1 - dieselReduction / 100;
        }

        if (isElectricityActivity(row)) {
          cantidad *= 1 + electricityIncrease / 100;
        }

        const emisiones = cantidad * Number(row.factor_emision);

        return {
          ...row,
          cantidad,
          emisiones,
        };
      });

      const simulatedTotal = simulatedRows.reduce(
        (acc, row) => acc + Number(row.emisiones),
        0
      );

      const reductionPct =
        currentTotal > 0
          ? ((currentTotal - simulatedTotal) / currentTotal) * 100
          : 0;

      if (!bestScenario || reductionPct > bestScenario.reductionPct) {
        bestScenario = {
          dieselReduction,
          electricityIncrease,
          currentTotal,
          evaluatedScenarios,
          simulatedTotal,
          reductionPct,
          rows: simulatedRows,
        };
      }
    }
  }

  return bestScenario;
}
