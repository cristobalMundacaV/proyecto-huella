import { useEffect, useState } from "react";
import { Inbox, Loader2, MapPinned, Plus, Route, X } from "lucide-react";

import Pagination from "@/shared/components/Pagination";
import { formatNumber } from "@/shared/utils/formatters";
import { Field } from "../common";
import RouteMapPicker from "../RouteMapPicker";

const transportPageSize = 5;

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
  const [currentPage, setCurrentPage] = useState(1);
  const transportes = selectedObra.transportes || [];
  const totalPages = Math.max(1, Math.ceil(transportes.length / transportPageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const visibleTransportes = transportes.slice(
    (safeCurrentPage - 1) * transportPageSize,
    safeCurrentPage * transportPageSize
  );

  useEffect(() => {
    setCurrentPage(1);
  }, [selectedObra.codigo_obra]);

  return (
    <section className="space-y-6">
      {isModalOpen && (
        <div className="premium-modal-overlay fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4">
          <form
            onSubmit={onTransportSubmit}
            className="premium-modal-shell my-8 w-full max-w-4xl p-4 sm:p-6"
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]">
                  <MapPinned size={18} />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-[var(--text-main)]">Registrar transporte GPS</h2>
                  <p className="text-sm text-[var(--text-muted)]">{selectedObra.codigo_obra}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] text-[var(--text-main)] transition hover:bg-slate-100"
                aria-label="Cerrar modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Vehículo" error={transportFieldErrors.vehiculo?.[0]}>
                <input
                  name="vehiculo"
                  value={transportForm.vehiculo}
                  onChange={onUpdateTransportForm}
                  required
                  className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60"
                />
              </Field>
              <Field label="Patente" error={transportFieldErrors.patente?.[0]}>
                <input
                  name="patente"
                  value={transportForm.patente}
                  onChange={onUpdateTransportForm}
                  required
                  className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60"
                />
              </Field>
              <Field label="Fecha y hora" error={transportFieldErrors.fecha_hora?.[0]}>
                <input
                  type="datetime-local"
                  name="fecha_hora"
                  value={transportForm.fecha_hora}
                  onChange={onUpdateTransportForm}
                  required
                  className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60"
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
                  className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60"
                />
              </Field>
              <Field label="Litros combustible" error={transportFieldErrors.litros_combustible?.[0]}>
                <input
                  type="number"
                  min="0"
                  step="0.001"
                  name="litros_combustible"
                  value={transportForm.litros_combustible}
                  onChange={onUpdateTransportForm}
                  placeholder="Opcional"
                  className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)] outline-none transition focus:border-[var(--primary)]/60"
                />
              </Field>
            </div>

            <div className="mt-5 rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
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
            </div>

            {transportError && (
              <p className="mt-4 rounded-2xl border border-[#F1B8B8] bg-[var(--danger-bg)] p-3 text-sm font-semibold text-[#B42318]">
                {transportError}
              </p>
            )}

            <button
              type="submit"
              disabled={savingTransport}
              className="premium-button-primary mt-6 flex w-full items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60"
            >
              {savingTransport ? <Loader2 className="animate-spin" size={18} /> : <MapPinned size={18} />}
              Guardar ruta y emisiones
            </button>
          </form>
        </div>
      )}

      <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.14em] text-[var(--primary-dark)]">
              Transporte y logística
            </p>
            <h2 className="mt-1 text-2xl font-bold text-[var(--text-main)]">Rutas asociadas a la obra</h2>
            <p className="mt-1 text-sm font-medium text-[var(--text-muted)]">
              Registra viajes de materiales, maquinaria o residuos para estimar emisiones logísticas con mayor trazabilidad.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] px-4 py-3 text-sm font-black text-[#075985]">
              {formatNumber(transportes.length, 0)} rutas
            </div>
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="premium-button-primary flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-bold"
            >
              <Plus size={18} />
              Agregar transporte
            </button>
          </div>
        </div>

        <div className="premium-table-wrapper overflow-x-auto">
          <table className="premium-table min-w-[920px] w-full table-fixed text-sm">
            <thead className="border-b border-[var(--border)] text-[var(--text-muted)]">
              <tr>
                <th className="w-[28%] px-4 py-3 text-center">Destino obra</th>
                <th className="w-[22%] px-4 py-3 text-center">Vehículo</th>
                <th className="w-[14%] px-4 py-3 text-center">Litros</th>
                <th className="w-[16%] px-4 py-3 text-center">Factor diésel</th>
                <th className="w-[20%] px-4 py-3 text-center">Emisiones</th>
              </tr>
            </thead>
            <tbody>
              {transportes.length === 0 && (
                <tr>
                  <td colSpan="5" className="px-4 py-10 text-center">
                    <EmptyTransportState onAction={() => setIsModalOpen(true)} />
                  </td>
                </tr>
              )}

              {visibleTransportes.map((transporte) => {
                const litros = Number(
                  transporte.litros_calculados ?? transporte.litros_combustible ?? 0
                );
                const factorDiesel = Number(transporte.factor_diesel ?? 0);
                const emisiones = Number(transporte.emisiones_transporte_kg_co2e ?? 0);

                return (
                  <tr key={transporte.id} className="border-b border-[#E2E8F0] transition hover:bg-[var(--success-bg)]/45">
                    <td className="px-4 py-4 text-center align-middle font-semibold text-[var(--text-main)]">
                      {transporte.ruta || transporte.destino || "Sin destino"}
                    </td>
                    <td className="px-4 py-4 text-center align-middle text-[var(--text-muted)]">
                      {transporte.vehiculo || "Vehículo"} {transporte.patente ? `· ${transporte.patente}` : ""}
                    </td>
                    <td className="px-4 py-4 text-center align-middle font-semibold text-[var(--text-main)]">
                      {formatNumber(litros, 2)} L
                    </td>
                    <td className="px-4 py-4 text-center align-middle text-[var(--text-muted)]">
                      {formatNumber(factorDiesel, 4)}
                    </td>
                    <td className="px-4 py-4 text-center align-middle font-black text-[#075985]">
                      {formatNumber(emisiones, 2)} kg CO2e
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {transportes.length > transportPageSize && (
          <Pagination
            currentPage={safeCurrentPage}
            itemLabel="rutas"
            onPageChange={setCurrentPage}
            pageSize={transportPageSize}
            totalItems={transportes.length}
          />
        )}
      </section>
    </section>
  );
}

function EmptyTransportState({ onAction }) {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center justify-center rounded-3xl border border-dashed border-[var(--border)] bg-[var(--bg-surface)] px-6 py-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]">
        <Inbox size={22} />
      </div>
      <h3 className="mt-4 text-lg font-black text-[var(--text-main)]">Sin rutas logísticas registradas</h3>
      <p className="mt-2 text-sm font-medium leading-6 text-[var(--text-muted)]">
        Registra viajes de materiales, maquinaria o residuos para calcular litros, distancia y emisiones asociadas al traslado de la obra.
      </p>
      <button
        type="button"
        onClick={onAction}
        className="premium-button-primary mt-5 inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-bold"
      >
        <Route size={18} />
        Agregar primera ruta
      </button>
    </div>
  );
}

export default TransporteTab;
