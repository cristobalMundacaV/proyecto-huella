import { formatNumber } from "@/shared/utils/formatters";
import { DetailItem } from "../common";
import { balanceTone, confidenceTone } from "../constants";

function ResumenTab({ balanceData, selectedLote }) {
  const tone = balanceTone[balanceData?.estado_balance] || balanceTone.medio;
  const confidenceClass =
    confidenceTone[balanceData?.estado_confianza] ||
    confidenceTone["Baja confianza"];

  return (
    <div className="space-y-6">
      <section className={`rounded-3xl border p-4 sm:p-6 ${tone.className}`}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide opacity-80">
              Balance neto del lote
            </p>
            <p className="mt-2 text-2xl font-bold">
              {formatNumber(Number(balanceData?.balance_neto_kg_co2e || 0))} kg CO2e
            </p>
            <p className="mt-2 text-sm font-semibold">
              Lote {selectedLote.id_lote}: emisiones generadas{" "}
              {formatNumber(
                Number(
                  balanceData?.emisiones_generadas_kg_co2e ||
                    selectedLote.emisiones_kg_co2e ||
                    0
                )
              )}{" "}
              kg CO2e, CO2 almacenado{" "}
              {formatNumber(Number(balanceData?.co2_almacenado_kg || 0))} kg,
              balance neto{" "}
              {formatNumber(Number(balanceData?.balance_neto_kg_co2e || 0))} kg
              CO2e.
            </p>
          </div>
          <div className="rounded-2xl border border-current/20 bg-slate-950/40 px-4 py-3 text-sm font-bold">
            {tone.label}
          </div>
        </div>
        <p className="mt-4 text-sm opacity-90">
          {balanceData?.descripcion_balance}
        </p>
      </section>

      <section className={`rounded-3xl border p-4 sm:p-6 ${confidenceClass}`}>
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide opacity-80">
              Confianza del dato
            </p>
            <h2 className="mt-2 text-2xl font-bold">
              {balanceData?.estado_confianza || "Baja confianza"}
            </h2>
            <p className="mt-2 text-sm font-semibold opacity-90">
              {balanceData?.descripcion_confianza}
            </p>
          </div>
          <div className="rounded-2xl border border-current/20 bg-slate-950/40 px-5 py-4 text-center">
            <p className="text-xs font-bold uppercase opacity-70">
              Score confianza
            </p>
            <p className="mt-1 text-3xl font-bold">
              {formatNumber(Number(balanceData?.confianza_score || 0), 0)}%
            </p>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <DetailItem
            label="Datos completos"
            value={`${formatNumber(
              Number(balanceData?.datos_completos_score || 0) * 0.3,
              0
            )} / 30 pts`}
          />
          <DetailItem
            label="Documentos adjuntos"
            value={`${formatNumber(
              Number(balanceData?.documentos_adjuntos_score || 0) * 0.25,
              0
            )} / 25 pts`}
          />
          <DetailItem
            label="Factores validos"
            value={`${formatNumber(
              Number(balanceData?.factores_validos_score || 0) * 0.25,
              0
            )} / 25 pts`}
          />
          <DetailItem
            label="Trazabilidad"
            value={`${formatNumber(
              Number(balanceData?.trazabilidad_confianza_score || 0) * 0.2,
              0
            )} / 20 pts`}
          />
        </div>
      </section>
    </div>
  );
}

export default ResumenTab;
