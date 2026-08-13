import { Download, Loader2, QrCode } from "lucide-react";

import {
  getObraExportCsvUrl,
  getObraExportJsonUrl,
  getObraFichaTecnicaUrl,
  getObraIntegracionUrl,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import { DetailItem } from "../common";
import { ficha_ambientalTone } from "../constants";

function FichaAmbientalTab({
  balanceData,
  generatingCertificate,
  onDownloadCertificate,
  selectedObra,
}) {
  const passportTone =
    ficha_ambientalTone[balanceData?.estado_ficha_ambiental] ||
    ficha_ambientalTone["Sin ficha_ambiental"];
  const balanceNeto = Number(balanceData?.balance_neto_kg_co2e || 0);
  const fichaStatus = getFichaStatusLabel(balanceData?.estado_ficha_ambiental);

  return (
    <div className="space-y-6">
      <section className={`rounded-3xl border p-4 sm:p-6 ${passportTone.className}`}>
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide opacity-80">
              Regla de ficha ambiental
            </p>
            <h2 className="mt-2 text-2xl font-bold">
              {fichaStatus}
            </h2>
            <p className="mt-2 text-sm font-semibold opacity-90">
              {balanceData?.razon_ficha_ambiental}
            </p>
          </div>
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-5 py-4 text-center text-[var(--text-main)] shadow-[var(--shadow-card)]">
            <p className="text-xs font-bold uppercase opacity-70">Score MVP</p>
            <p className="mt-1 text-3xl font-bold">
              {formatNumber(Number(balanceData?.ficha_ambiental_score || 0), 0)}%
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

      <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
        <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[var(--primary-dark)]">
              Reporte ambiental verificable
            </p>
            <h2 className="mt-2 text-2xl font-bold text-[var(--text-main)]">
              Vista previa de ficha ambiental
            </h2>
          </div>
          <button
            type="button"
            onClick={onDownloadCertificate}
            disabled={generatingCertificate}
            className="flex w-full items-center justify-center gap-2 rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] px-5 py-3 text-sm font-bold text-[var(--primary-dark)] transition hover:border-[var(--primary)] hover:bg-[#D9F0E6] disabled:cursor-not-allowed disabled:opacity-60 sm:w-fit"
          >
            {generatingCertificate ? (
              <Loader2 className="animate-spin" size={18} />
            ) : (
              <Download size={18} />
            )}
            Generar ficha ambiental
          </button>
        </div>

        <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 sm:p-7">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-sm font-bold uppercase tracking-wide text-[var(--primary-dark)]">
                Ficha ambiental
              </p>
              <h3 className="mt-2 text-3xl font-bold text-[var(--text-main)]">
                {selectedObra.codigo_obra}
              </h3>
              <p className="mt-2 text-sm font-medium text-[var(--text-muted)]">
                Emitido para {selectedObra.organizacion_nombre}
              </p>
            </div>
            <div className="flex h-28 w-28 shrink-0 items-center justify-center rounded-2xl border border-slate-700 bg-white text-slate-950">
              <QrCode size={74} />
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <PassportMetric label="Fecha de obra" value={selectedObra.fecha} />
            <PassportMetric label="Material principal / tipo de obra" value={selectedObra.tipo_proyecto} />
            <PassportMetric
              label="Cantidad base / superficie"
              value={`${formatNumber(Number(selectedObra.superficie_m2 || 0))} m3`}
            />
            <PassportMetric
              label="Emisiones generadas"
              value={`${formatNumber(
                Number(
                  balanceData?.emisiones_generadas_kg_co2e ||
                    selectedObra.emisiones_kg_co2e ||
                    0
                )
              )} kg CO2e`}
              tone="cyan"
            />
            <PassportMetric
              label="Balance ambiental"
              value={`${formatNumber(Number(balanceData?.balance_ambiental_kg || 0))} kg`}
              tone="emerald"
            />
            <PassportMetric
              label="Balance neto"
              value={`${balanceNeto > 0 ? "+" : ""}${formatNumber(balanceNeto)} kg CO2e`}
              tone={balanceNeto < 0 ? "emerald" : balanceNeto > 0 ? "red" : "amber"}
              badge={balanceNeto < 0 ? "Positivo" : balanceNeto > 0 ? "Negativo" : "Neutro"}
            />
            <PassportMetric
              label="Estado de ficha"
              value={fichaStatus}
              tone="emerald"
            />
            <PassportMetric
              label="Fecha de emision"
              value={new Date().toLocaleDateString("es-CL")}
            />
          </div>

          <div className="mt-6 rounded-3xl border border-[var(--border)] bg-[var(--info-bg)] p-4">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-[#075985]">
                  Integracion BIM / API
                </p>
                <p className="mt-2 text-sm font-medium text-[var(--text-muted)]">
                  Exporta esta obra para modelos BIM, reportes ambientales y sistemas de organizaciones.
                </p>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <a
                  href={getObraIntegracionUrl(selectedObra.codigo_obra)}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-2xl border border-[#B8D6DE] bg-[var(--bg-card)] px-4 py-3 text-center text-sm font-bold text-[#075985] transition hover:bg-[#DDF0F4]"
                >
                  API obra
                </a>
                <a
                  href={getObraExportJsonUrl(selectedObra.codigo_obra)}
                  className="rounded-2xl border border-[#B8D6DE] bg-[var(--bg-card)] px-4 py-3 text-center text-sm font-bold text-[#075985] transition hover:bg-[#DDF0F4]"
                >
                  JSON
                </a>
                <a
                  href={getObraExportCsvUrl(selectedObra.codigo_obra)}
                  className="rounded-2xl border border-[#B8D6DE] bg-[var(--bg-card)] px-4 py-3 text-center text-sm font-bold text-[#075985] transition hover:bg-[#DDF0F4]"
                >
                  CSV
                </a>
                <a
                  href={getObraFichaTecnicaUrl(selectedObra.codigo_obra)}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-2xl border border-[#B8D6DE] bg-[var(--bg-card)] px-4 py-3 text-center text-sm font-bold text-[#075985] transition hover:bg-[#DDF0F4]"
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

export default FichaAmbientalTab;

function getFichaStatusLabel(status) {
  const statusLabels = {
    "Sin ficha_ambiental": "Sin ficha",
    "FichaAmbiental Base": "Ficha base",
    "FichaAmbiental Verde": "Ficha ambiental",
    "FichaAmbiental Verde Plus": "Ficha ambiental plus",
  };

  return statusLabels[status] || status || "Sin ficha";
}

function PassportMetric({ badge, label, tone = "slate", value }) {
  const toneClass = {
    amber: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]",
    cyan: "border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]",
    emerald: "border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]",
    red: "border-[#F1B8B8] bg-[var(--danger-bg)] text-[#B42318]",
    slate: "border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-main)]",
  }[tone];

  const badgeClass = {
    amber: "border-[#E1C56F] bg-[#FFF9E8] text-[#7A4F00]",
    cyan: "border-[#B8D6DE] bg-[#DDF0F4] text-[#075985]",
    emerald: "border-[var(--border)] bg-[#D9F0E6] text-[var(--primary-dark)]",
    red: "border-[#F1B8B8] bg-[#FBE2E2] text-[#B42318]",
    slate: "border-[var(--border)] bg-[var(--bg-surface)] text-[var(--text-main)]",
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
