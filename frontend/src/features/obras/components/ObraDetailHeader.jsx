import { Loader2, Sparkles } from "lucide-react";

import { formatNumber } from "@/shared/utils/formatters";
import { DetailItem } from "./common";

function ObraDetailHeader({ detailLoading, onImportEvidencia, selectedObra }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-semibold text-[var(--text-main)]">Detalle de obra</h2>
          {detailLoading && <Loader2 className="animate-spin text-emerald-300" size={20} />}
        </div>
        {selectedObra && onImportEvidencia ? (
          <button
            type="button"
            onClick={onImportEvidencia}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[#B7DEC9] bg-[var(--success-bg)] px-4 py-3 text-sm font-bold text-[var(--primary-dark)] transition hover:bg-[#DFF3E6]"
          >
            <Sparkles size={16} />
            Importar evidencia
          </button>
        ) : null}
      </div>

      {selectedObra ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <DetailItem label="Código de obra" value={selectedObra.codigo_obra} />
          <DetailItem
            label="organizacion / proveedor principal"
            value={selectedObra.organizacion_nombre}
          />
          <DetailItem label="Fecha de inicio" value={selectedObra.fecha} />
          <DetailItem label="Tipo de obra / material principal" value={selectedObra.tipo_proyecto} />
          <DetailItem
            label="Superficie o cantidad base"
            value={`${formatNumber(Number(selectedObra.superficie_m2))} m3`}
          />
          <DetailItem
            label="Balance ambiental"
            value={`${formatNumber(Number(selectedObra.balance_ambiental_kg || 0))} kg`}
          />
          <DetailItem
            label="Emisiones asociadas"
            value={`${formatNumber(Number(selectedObra.emisiones_kg_co2e))} kg CO2e`}
          />
          <DetailItem label="Ubicación de obra" value={selectedObra.origen} />
        </div>
      ) : (
        <p className="text-[var(--text-muted)]">
          Selecciona una obra para ver su trazabilidad.
        </p>
      )}
    </section>
  );
}

export default ObraDetailHeader;
