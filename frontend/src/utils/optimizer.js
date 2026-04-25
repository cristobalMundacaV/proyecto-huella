export function optimizeScenario(rows) {
  let bestScenario = null;
  let evaluatedScenarios = 0;

  const currentTotal = rows.reduce(
    (acc, row) => acc + Number(row.emisiones),
    0
  );

  for (let dieselReduction = 0; dieselReduction <= 80; dieselReduction += 5) {
    for (
      let electricityIncrease = 0;
      electricityIncrease <= 60;
      electricityIncrease += 5
    ) {
      evaluatedScenarios += 1;
      const simulatedRows = rows.map((row) => {
        let cantidad = Number(row.cantidad);
        const actividad = String(row.actividad).toLowerCase();

        if (actividad === "diesel") {
          cantidad *= 1 - dieselReduction / 100;
        }

        if (actividad === "electricidad") {
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
