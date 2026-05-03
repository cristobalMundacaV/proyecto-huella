import { Loader2, X } from "lucide-react";

import AnimatedModalShell from "@/shared/components/AnimatedModalShell";
import { formatNumber } from "@/shared/utils/formatters";
import { DetailItem } from "./common";

function LoteDetailModal({ detailLoading, lote, onClose }) {
  return (
    <AnimatedModalShell
      ariaLabel="Detalle del lote"
      contentClassName="my-8 w-full max-w-5xl rounded-3xl border border-slate-800 bg-slate-900 p-4 shadow-2xl sm:p-6"
      onBackdropClick={onClose}
    >
      <section>
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">Detalle del lote</h2>
            <p className="mt-1 text-sm text-slate-400">
              Información resumida del lote seleccionado.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-slate-700 bg-slate-950 text-slate-300 transition hover:bg-slate-800"
            aria-label="Cerrar modal"
          >
            <X size={18} />
          </button>
        </div>

        {detailLoading && !lote ? (
          <div className="flex min-h-[220px] items-center justify-center gap-3 rounded-3xl border border-slate-800 bg-slate-950 px-6 py-10 text-slate-400">
            <Loader2 className="animate-spin text-emerald-300" size={20} />
            Cargando detalle...
          </div>
        ) : lote ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <DetailItem label="ID lote" value={lote.id_lote} />
            <DetailItem
              label="Empresa / aserradero"
              value={lote.empresa_aserradero}
            />
            <DetailItem label="Fecha" value={lote.fecha} />
            <DetailItem label="Especie" value={lote.especie} />
            <DetailItem
              label="Volumen"
              value={`${formatNumber(Number(lote.volumen_m3))} m3`}
            />
            <DetailItem
              label="Densidad"
              value={`${formatNumber(Number(lote.densidad_kg_m3 || 0))} kg/m3`}
            />
            <DetailItem
              label="Carbono en madera"
              value={`${formatNumber(Number(lote.porcentaje_carbono || 0) * 100, 1)}%`}
            />
            <DetailItem
              label="Masa estimada"
              value={`${formatNumber(Number(lote.masa_madera_kg || 0))} kg`}
            />
            <DetailItem
              label="CO2 almacenado"
              value={`${formatNumber(Number(lote.co2_almacenado_kg || 0))} kg`}
            />
            <DetailItem
              label="Emisiones asociadas"
              value={`${formatNumber(Number(lote.emisiones_kg_co2e || 0))} kg CO2e`}
            />
            <DetailItem label="Origen" value={lote.origen} />
          </div>
        ) : (
          <p className="rounded-3xl border border-slate-800 bg-slate-950 px-6 py-10 text-slate-400">
            No hay detalle disponible para mostrar.
          </p>
        )}
      </section>
    </AnimatedModalShell>
  );
}

export default LoteDetailModal;
