import { Loader2 } from "lucide-react";

import { formatNumber } from "@/shared/utils/formatters";
import { DetailItem } from "./common";

function LoteDetailHeader({ detailLoading, selectedLote }) {
  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
      <div className="mb-5 flex items-center justify-between gap-4">
        <h2 className="text-xl font-semibold">Detalle del lote</h2>
        {detailLoading && (
          <Loader2 className="animate-spin text-emerald-300" size={20} />
        )}
      </div>

      {selectedLote ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <DetailItem label="ID lote" value={selectedLote.id_lote} />
          <DetailItem
            label="Empresa / aserradero"
            value={selectedLote.empresa_aserradero}
          />
          <DetailItem label="Fecha" value={selectedLote.fecha} />
          <DetailItem label="Especie" value={selectedLote.especie} />
          <DetailItem
            label="Volumen"
            value={`${formatNumber(Number(selectedLote.volumen_m3))} m3`}
          />
          <DetailItem
            label="Densidad"
            value={`${formatNumber(Number(selectedLote.densidad_kg_m3 || 0))} kg/m3`}
          />
          <DetailItem
            label="Carbono en madera"
            value={`${formatNumber(
              Number(selectedLote.porcentaje_carbono || 0) * 100,
              1
            )}%`}
          />
          <DetailItem
            label="Masa estimada"
            value={`${formatNumber(Number(selectedLote.masa_madera_kg || 0))} kg`}
          />
          <DetailItem
            label="Carbono almacenado"
            value={`${formatNumber(Number(selectedLote.co2_almacenado_kg || 0))} kg`}
          />
          <DetailItem
            label="Emisiones asociadas"
            value={`${formatNumber(Number(selectedLote.emisiones_kg_co2e))} kg CO2e`}
          />
          <DetailItem label="Origen" value={selectedLote.origen} />
        </div>
      ) : (
        <p className="text-slate-400">
          Selecciona un lote para ver su trazabilidad.
        </p>
      )}
    </section>
  );
}

export default LoteDetailHeader;
