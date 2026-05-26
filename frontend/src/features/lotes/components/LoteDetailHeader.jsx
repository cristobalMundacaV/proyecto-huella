import { Loader2, Sparkles } from "lucide-react";

import { formatNumber } from "@/shared/utils/formatters";
import { DetailItem } from "./common";

function LoteDetailHeader({ detailLoading, onImportDocumento, selectedLote }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-semibold text-[var(--text-main)]">Detalle de obra</h2>
          {detailLoading && <Loader2 className="animate-spin text-emerald-300" size={20} />}
        </div>
        {selectedLote && onImportDocumento ? (
          <button
            type="button"
            onClick={onImportDocumento}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[#B7DEC9] bg-[var(--success-bg)] px-4 py-3 text-sm font-bold text-[var(--primary-dark)] transition hover:bg-[#DFF3E6]"
          >
            <Sparkles size={16} />
            Importar documento
          </button>
        ) : null}
      </div>

      {selectedLote ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <DetailItem label="Código de obra" value={selectedLote.id_lote} />
          <DetailItem
            label="Constructora / proveedor principal"
            value={selectedLote.empresa_aserradero}
          />
          <DetailItem label="Fecha de inicio" value={selectedLote.fecha} />
          <DetailItem label="Tipo de obra / material principal" value={selectedLote.especie} />
          <DetailItem
            label="Superficie o cantidad base"
            value={`${formatNumber(Number(selectedLote.volumen_m3))} m3`}
          />
          <DetailItem
            label="Balance ambiental"
            value={`${formatNumber(Number(selectedLote.co2_almacenado_kg || 0))} kg`}
          />
          <DetailItem
            label="Emisiones asociadas"
            value={`${formatNumber(Number(selectedLote.emisiones_kg_co2e))} kg CO2e`}
          />
          <DetailItem label="Ubicación de obra" value={selectedLote.origen} />
        </div>
      ) : (
        <p className="text-[var(--text-muted)]">
          Selecciona una obra para ver su trazabilidad.
        </p>
      )}
    </section>
  );
}

export default LoteDetailHeader;
