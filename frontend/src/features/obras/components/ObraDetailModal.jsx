import { Loader2, X } from "lucide-react";

import AnimatedModalShell from "@/shared/components/AnimatedModalShell";
import { formatNumber } from "@/shared/utils/formatters";
import { DetailItem } from "./common";

function ObraDetailModal({ detailLoading, obra, onClose }) {
  return (
    <AnimatedModalShell
      ariaLabel="Detalle de obra"
      contentClassName="my-8 w-full max-w-5xl rounded-3xl border border-slate-800 bg-slate-900 p-4 shadow-2xl sm:p-6"
      onBackdropClick={onClose}
    >
      <section>
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">Detalle de obra</h2>
            <p className="mt-1 text-sm text-slate-400">
              Información resumida de la obra seleccionada.
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

        {detailLoading && !obra ? (
          <div className="flex min-h-[220px] items-center justify-center gap-3 rounded-3xl border border-slate-800 bg-slate-950 px-6 py-10 text-slate-400">
            <Loader2 className="animate-spin text-emerald-300" size={20} />
            Cargando detalle...
          </div>
        ) : obra ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <DetailItem label="Código de obra" value={obra.codigo_obra} />
            <DetailItem
              label="organizacion / proveedor principal"
              value={obra.organizacion_nombre}
            />
            <DetailItem label="Fecha de inicio" value={obra.fecha} />
            <DetailItem label="Tipo de obra / material principal" value={obra.tipo_proyecto} />
            <DetailItem
              label="Superficie o cantidad base"
              value={`${formatNumber(Number(obra.superficie_m2))} m3`}
            />
            <DetailItem
              label="Balance ambiental"
              value={`${formatNumber(Number(obra.balance_ambiental_kg || 0))} kg`}
            />
            <DetailItem
              label="Emisiones asociadas"
              value={`${formatNumber(Number(obra.emisiones_kg_co2e || 0))} kg CO2e`}
            />
            <DetailItem label="Ubicación de obra" value={obra.origen} />
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

export default ObraDetailModal;
