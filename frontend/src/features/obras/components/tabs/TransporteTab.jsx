import { useState } from "react";
import { Loader2, MapPinned, Plus, X } from "lucide-react";

import { formatNumber } from "@/shared/utils/formatters";
import { Field } from "../common";
import RouteMapPicker from "../RouteMapPicker";

function TransporteTab({
  onUpdateTransportDestination,
  onTransportSubmit,
  onUpdateTransportForm,
  onUpdateTransportOrigin,
  savingTransport,
  selectedObra,
  transportError,
  transportFieldErrors,
  transportForm,
  transportRouteGeometry,
}) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <section className="space-y-6">
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/80 p-4 backdrop-blur-sm">
      <form
        onSubmit={onTransportSubmit}
            className="my-8 w-full max-w-4xl rounded-3xl border border-slate-800 bg-slate-900 p-4 shadow-2xl sm:p-6"
      >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-sky-400/20 bg-sky-400/10 text-sky-200">
                  <MapPinned size={18} />
                </div>
                <div>
                  <h2 className="text-xl font-semibold">Registrar transporte GPS</h2>
                  <p className="text-sm text-slate-400">{selectedObra.codigo_obra}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-slate-700 bg-slate-950 text-slate-300 transition hover:bg-slate-800"
                aria-label="Cerrar modal"
              >
                <X size={18} />
              </button>
          </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Vehí­culo" error={transportFieldErrors.vehiculo?.[0]}>
            <input
              name="vehiculo"
              value={transportForm.vehiculo}
              onChange={onUpdateTransportForm}
              required
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-sky-400/60"
            />
          </Field>
          <Field label="Patente" error={transportFieldErrors.patente?.[0]}>
            <input
              name="patente"
              value={transportForm.patente}
              onChange={onUpdateTransportForm}
              required
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-sky-400/60"
            />
          </Field>
          <Field label="Fecha y hora" error={transportFieldErrors.fecha_hora?.[0]}>
            <input
              type="datetime-local"
              name="fecha_hora"
              value={transportForm.fecha_hora}
              onChange={onUpdateTransportForm}
              required
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-sky-400/60"
            />
          </Field>
          <Field
            label="Consumo estimado"
            error={transportFieldErrors.consumo_estimado_litro_km?.[0]}
          >
            <input
              type="number"
              min="0"
              step="0.0001"
              name="consumo_estimado_litro_km"
              value={transportForm.consumo_estimado_litro_km}
              onChange={onUpdateTransportForm}
              required
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-sky-400/60"
            />
          </Field>
          <Field
            label="Litros combustible"
            error={transportFieldErrors.litros_combustible?.[0]}
          >
            <input
              type="number"
              min="0"
              step="0.001"
              name="litros_combustible"
              value={transportForm.litros_combustible}
              onChange={onUpdateTransportForm}
              placeholder="Opcional"
              className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-sky-400/60"
            />
          </Field>
        </div>

        <RouteMapPicker
          destinationCoords={transportForm.destino_coords}
          destinationValue={transportForm.destino}
          onDestinationChange={onUpdateTransportDestination}
          onOriginChange={onUpdateTransportOrigin}
          originCoords={transportForm.punto_partida_coords}
          originValue={transportForm.punto_partida}
          routeGeometry={transportRouteGeometry}
          onDistanceCalculated={(km) =>
            onUpdateTransportForm({ target: { name: "distancia_km", value: km ?? "" } })
          }
        />

        {transportError && (
          <p className="mt-4 text-sm text-red-300">{transportError}</p>
        )}

        <button
          type="submit"
          disabled={savingTransport}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl border border-sky-400/20 bg-sky-400/10 px-5 py-3 text-sm font-bold text-sky-200 transition hover:bg-sky-400/20 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {savingTransport ? (
            <Loader2 className="animate-spin" size={18} />
          ) : (
            <MapPinned size={18} />
          )}
          Guardar ruta y emisiones
        </button>
      </form>
        </div>
      )}

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Rutas y movimiento</h2>
            <p className="mt-1 text-sm text-slate-400">
              Registra viajes asociados a materiales, maquinaria o residuos para estimar emisiones logí­sticas de la obra.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="rounded-2xl border border-sky-400/20 bg-sky-400/10 px-4 py-3 text-sm font-bold text-sky-200">
              {formatNumber(selectedObra.transportes?.length || 0, 0)} rutas
            </div>
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="flex items-center justify-center gap-2 rounded-2xl border border-sky-400/20 bg-sky-400/10 px-4 py-3 text-sm font-bold text-sky-200 transition hover:bg-sky-400/20"
            >
              <Plus size={18} />
              Agregar transporte
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-[920px] w-full text-sm">
            <thead className="border-b border-slate-800 text-slate-400">
              <tr>
                <th className="py-3 text-left">Destino obra</th>
                <th className="py-3 text-left">Vehí­culo</th>
                <th className="py-3 text-right">Litros</th>
                <th className="py-3 text-right">Factor diesel</th>
                <th className="py-3 text-right">Emisiones</th>
              </tr>
            </thead>
            <tbody>
              {(selectedObra.transportes?.length || 0) === 0 && (
                <tr>
                  <td colSpan="5" className="py-8 text-center text-slate-400">
                    No hay viajes registrados para esta obra.
                  </td>
                </tr>
              )}

              {selectedObra.transportes?.map((transporte) => (
                <tr key={transporte.id} className="border-b border-slate-800/60">
                  <td className="py-3 font-semibold text-slate-100">
                    {transporte.ruta}
                  </td>
                  <td className="py-3">
                    {transporte.vehiculo} | {transporte.patente}
                  </td>
                  <td className="py-3 text-right">
                    {formatNumber(Number(transporte.litros_calculados))} l
                  </td>
                  <td className="py-3 text-right">
                    {formatNumber(Number(transporte.factor_diesel), 6)}
                  </td>
                  <td className="py-3 text-right font-semibold text-sky-200">
                    {formatNumber(Number(transporte.emisiones_transporte_kg_co2e))} kg CO2e
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}

export default TransporteTab;
