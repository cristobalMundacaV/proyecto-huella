import { Download, Loader2, QrCode } from "lucide-react";

import {
  getLoteExportCsvUrl,
  getLoteExportJsonUrl,
  getLoteFichaTecnicaUrl,
  getLoteIntegracionUrl,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import { DetailItem } from "../common";
import { pasaporteTone } from "../constants";

function PasaporteTab({
  balanceData,
  generatingCertificate,
  onDownloadCertificate,
  selectedLote,
}) {
  const passportTone =
    pasaporteTone[balanceData?.estado_pasaporte] ||
    pasaporteTone["Sin pasaporte"];
  const balanceNeto = Number(balanceData?.balance_neto_kg_co2e || 0);

  return (
    <div className="space-y-6">
      <section className={`rounded-3xl border p-4 sm:p-6 ${passportTone.className}`}>
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide opacity-80">
              Regla del Pasaporte Verde
            </p>
            <h2 className="mt-2 text-2xl font-bold">
              {balanceData?.estado_pasaporte || "Sin pasaporte"}
            </h2>
            <p className="mt-2 text-sm font-semibold opacity-90">
              {balanceData?.razon_pasaporte}
            </p>
          </div>
          <div className="rounded-2xl border border-current/20 bg-slate-950/40 px-5 py-4 text-center">
            <p className="text-xs font-bold uppercase opacity-70">Score MVP</p>
            <p className="mt-1 text-3xl font-bold">
              {formatNumber(Number(balanceData?.pasaporte_score || 0), 0)}%
            </p>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <DetailItem
            label="Trazabilidad"
            value={`${formatNumber(Number(balanceData?.trazabilidad_score || 0), 0)}%`}
          />
          <DetailItem
            label="Completitud de datos"
            value={`${formatNumber(Number(balanceData?.completitud_score || 0), 0)}%`}
          />
          <DetailItem
            label="Factores encontrados"
            value={`${formatNumber(Number(balanceData?.factor_score || 0), 0)}%`}
          />
        </div>
      </section>

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
        <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-emerald-300">
              Certificado digital verificable
            </p>
            <h2 className="mt-2 text-2xl font-bold text-slate-100">
              Vista previa del Pasaporte Verde
            </h2>
          </div>
          <button
            type="button"
            onClick={onDownloadCertificate}
            disabled={generatingCertificate}
            className="flex w-full items-center justify-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-200 transition hover:bg-emerald-400/20 disabled:cursor-not-allowed disabled:opacity-60 sm:w-fit"
          >
            {generatingCertificate ? (
              <Loader2 className="animate-spin" size={18} />
            ) : (
              <Download size={18} />
            )}
            Generar Pasaporte Verde
          </button>
        </div>

        <div className="rounded-3xl border border-slate-700 bg-slate-950 p-5 sm:p-7">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-sm font-bold uppercase tracking-wide text-emerald-300">
                Pasaporte Verde
              </p>
              <h3 className="mt-2 text-3xl font-bold text-slate-100">
                {selectedLote.id_lote}
              </h3>
              <p className="mt-2 text-sm text-slate-400">
                Emitido para {selectedLote.empresa_aserradero}
              </p>
            </div>
            <div className="flex h-28 w-28 shrink-0 items-center justify-center rounded-2xl border border-slate-700 bg-white text-slate-950">
              <QrCode size={74} />
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <PassportMetric label="Fecha del lote" value={selectedLote.fecha} />
            <PassportMetric label="Especie" value={selectedLote.especie} />
            <PassportMetric
              label="Volumen"
              value={`${formatNumber(Number(selectedLote.volumen_m3 || 0))} m3`}
            />
            <PassportMetric
              label="Emisiones generadas"
              value={`${formatNumber(
                Number(
                  balanceData?.emisiones_generadas_kg_co2e ||
                    selectedLote.emisiones_kg_co2e ||
                    0
                )
              )} kg CO2e`}
              tone="cyan"
            />
            <PassportMetric
              label="CO2 almacenado"
              value={`${formatNumber(Number(balanceData?.co2_almacenado_kg || 0))} kg`}
              tone="emerald"
            />
            <PassportMetric
              label="Balance neto"
              value={`${balanceNeto > 0 ? "+" : ""}${formatNumber(balanceNeto)} kg CO2e`}
              tone={balanceNeto < 0 ? "emerald" : balanceNeto > 0 ? "red" : "amber"}
              badge={balanceNeto < 0 ? "Positivo" : balanceNeto > 0 ? "Negativo" : "Neutro"}
            />
            <PassportMetric
              label="Estado del pasaporte"
              value={balanceData?.estado_pasaporte || "Sin pasaporte"}
              tone="emerald"
            />
            <PassportMetric
              label="Fecha de emision"
              value={new Date().toLocaleDateString("es-CL")}
            />
          </div>

          <div className="mt-6 rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-4">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-cyan-200">
                  Integracion BIM / API
                </p>
                <p className="mt-2 text-sm text-slate-300">
                  Exporta este lote para modelos BIM, fichas tecnicas y sistemas de constructoras.
                </p>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <a
                  href={getLoteIntegracionUrl(selectedLote.id_lote)}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-2xl border border-cyan-400/20 bg-slate-950/50 px-4 py-3 text-center text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/10"
                >
                  API lote
                </a>
                <a
                  href={getLoteExportJsonUrl(selectedLote.id_lote)}
                  className="rounded-2xl border border-cyan-400/20 bg-slate-950/50 px-4 py-3 text-center text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/10"
                >
                  JSON
                </a>
                <a
                  href={getLoteExportCsvUrl(selectedLote.id_lote)}
                  className="rounded-2xl border border-cyan-400/20 bg-slate-950/50 px-4 py-3 text-center text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/10"
                >
                  CSV
                </a>
                <a
                  href={getLoteFichaTecnicaUrl(selectedLote.id_lote)}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-2xl border border-cyan-400/20 bg-slate-950/50 px-4 py-3 text-center text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/10"
                >
                  Ficha tecnica
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default PasaporteTab;

function PassportMetric({ badge, label, tone = "slate", value }) {
  const toneClass = {
    amber: "border-amber-400/30 bg-amber-400/10 text-amber-100",
    cyan: "border-cyan-400/30 bg-cyan-400/10 text-cyan-100",
    emerald: "border-emerald-400/30 bg-emerald-400/10 text-emerald-100",
    red: "border-red-400/30 bg-red-400/10 text-red-100",
    slate: "border-slate-700 bg-slate-950 text-slate-100",
  }[tone];

  const badgeClass = {
    amber: "border-amber-400/30 bg-amber-400/15 text-amber-100",
    cyan: "border-cyan-400/30 bg-cyan-400/15 text-cyan-100",
    emerald: "border-emerald-400/30 bg-emerald-400/15 text-emerald-100",
    red: "border-red-400/30 bg-red-400/15 text-red-100",
    slate: "border-slate-600 bg-slate-800 text-slate-200",
  }[tone];

  return (
    <div className={`rounded-2xl border p-5 ${toneClass}`}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide opacity-70">
          {label}
        </p>
        {badge && (
          <span className={`rounded-full border px-3 py-1 text-xs font-bold ${badgeClass}`}>
            {badge}
          </span>
        )}
      </div>
      <p className="mt-3 text-2xl font-bold leading-tight">{value || "-"}</p>
    </div>
  );
}
