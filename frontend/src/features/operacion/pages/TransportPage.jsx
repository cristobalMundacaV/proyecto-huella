import { Link, useOutletContext, useParams } from "react-router-dom";
import { EmptyState, ErrorState, KpiCard, SectionHeader, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime, formatNumber } from "@/shared/utils/formatters";
import { applicability, isResourceReady, resourceData, transportMetrics } from "../utils/operationSelectors";
import DomainApplicability from "../components/DomainApplicability";
import { useState } from "react";
import TransportRecordModal from "../components/TransportRecordModal";
import OperationDomainShell from "../components/OperationDomainShell";
import DomainSensorsPanel from "../components/DomainSensorsPanel";
import DomainQualityPanel from "../components/DomainQualityPanel";
import DomainCalculationPanel from "../components/DomainCalculationPanel";

const humanize = (value) => value ? String(value).replaceAll("_", " ") : "Sin información";

function measurement(value, unit) {
  if (value === null || value === undefined) return "Sin datos";
  return unit ? `${formatNumber(value)} ${unit}` : `${formatNumber(value)} · unidad no informada`;
}

function observationOrigin(label, observation) {
  if (!observation) return null;
  const evidenceId = observation.evidencia;
  const sensorId = observation.sensor_detalle?.id;
  const source = observation.fuente_detalle?.nombre;
  if (!evidenceId && !sensorId && !source) return null;
  return { label, evidenceId, sensorId, source };
}

export default function TransportPage() {
  const { obraId } = useParams();
  const {
    obra,
    context,
    operation,
    reloadOperation,
  } = useOutletContext();

  const [recordOpen, setRecordOpen] =
    useState(false);

  const persistedWorkId =
    obra?.id ||
    obra?.obra_id;
  const applicabilityState = applicability(context, "transporte");
  const indicatorsReady = isResourceReady(operation.transport);
  const journeysReady = isResourceReady(operation.journeys);
  const transport = resourceData(operation.transport, null);
  const metrics = indicatorsReady ? transportMetrics(transport) : [];
  const journeys = resourceData(operation.journeys, []);
  const summaryMetrics = ["numero_viajes", "km_totales", "tonelaje_transportado"]
    .map((key) => metrics.find((metric) => metric.key === key))
    .filter(Boolean);
  const noApplicable = applicabilityState === "no_aplica";
  const unresolved = ["pendiente", "no_determinado"].includes(applicabilityState);

  return (
    <OperationDomainShell
      title="Transporte"
      description="¿Cómo se está moviendo carga o personas en esta obra?"
      applicability={
        <DomainApplicability
          context={context}
          capability="transporte"
        />
      }
    >
      <div className="flex justify-end">
        <button
          type="button"
          className="font-bold text-[var(--brand-primary)]"
          onClick={() =>
            setRecordOpen(true)
          }
        >
          Registrar viaje
        </button>
      </div>

      {indicatorsReady
        ? summaryMetrics.length > 0 && <section>
          <SectionHeader
            eyebrow="LECTURA DEL ÁMBITO"
            title="Resumen"
            description="Viajes, distancia y carga se mantienen como magnitudes operacionales separadas."
          />
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{summaryMetrics.map((metric) => <KpiCard
            key={metric.key}
            label={metric.label}
            value={metric.value}
            unit={metric.unit}
          />)}</div>
        </section>
        : <ErrorState title="No fue posible cargar el resumen de transporte" description="Los viajes continúan disponibles si pudieron cargarse." />}

      {!journeysReady
        ? <ErrorState title="No fue posible cargar los viajes" description="El resumen de transporte continúa disponible si pudo calcularse." />
        : !journeys.length
          ? noApplicable
            ? <EmptyState title="No aplica a esta unidad" description="Transporte está marcado como no aplicable. La ausencia de viajes no se presenta como cero operacional." />
            : unresolved
              ? <EmptyState
                title="Aplicabilidad por definir"
                description="Aún no existe información suficiente para determinar si transporte aplica a esta obra."
                primaryAction={
                  <Link
                    className="font-bold text-[var(--brand-primary)]"
                    to={`/obras/${obraId}/diagnostico`}
                  >
                    Revisar diagnóstico
                  </Link>
                }
                secondaryAction={
                  <Link
                    className="font-bold text-[var(--text-secondary)]"
                    to={`/obras/${obraId}/evidencias`}
                  >
                    Agregar evidencia
                  </Link>
                }
              />
              : <EmptyState
                title="Sin viajes registrados"
                description="Aún no hay movimientos de transporte registrados para esta unidad."
                primaryAction={<Link className="font-bold text-[var(--brand-primary)]" to="/datos/importaciones">Importar información</Link>}
                secondaryAction={<Link className="font-bold text-[var(--text-secondary)]" to={`/obras/${obraId}/evidencias`}>Agregar documento</Link>}
              />
          : <section>
            <SectionHeader
              eyebrow="ACTIVIDAD REGISTRADA"
              title="Viajes"
              description="Origen y destino primero; el detalle técnico queda disponible cuando aporta contexto."
              count={journeys.length}
            />
            <TableShell>
              <TableHead><tr>
                <TableCell as="th">Fecha</TableCell>
                <TableCell as="th">Ruta</TableCell>
                <TableCell as="th" numeric>Distancia</TableCell>
                <TableCell as="th" numeric>Carga</TableCell>
                <TableCell as="th">Estado</TableCell>
                <TableCell as="th">Origen del dato</TableCell>
              </tr></TableHead>
              <TableBody columns={6}>{journeys.map((journey) => {
                const distance = journey.metricas?.distancia_km;
                const load = journey.metricas?.carga_t;
                const fuel = journey.metricas?.combustible_l;
                const origins = [
                  observationOrigin("Distancia", journey.distancia_detalle),
                  observationOrigin("Carga", journey.carga_detalle),
                  observationOrigin("Combustible", journey.combustible_detalle),
                ].filter(Boolean);
                const methodology = typeof journey.metodologia_tercerizado === "string" ? journey.metodologia_tercerizado : "";
                return <tr key={journey.id}>
                  <TableCell>{formatDateTime(journey.fecha_salida)}</TableCell>
                  <TableCell>
                    <span className="font-bold">{journey.origen_nombre || "Origen sin informar"} → {journey.destino_nombre || "Destino sin informar"}</span>
                    {journey.codigo && <span className="block text-xs text-[var(--text-muted)]">{journey.codigo}</span>}
                  </TableCell>
                  <TableCell numeric>{measurement(distance, "km")}</TableCell>
                  <TableCell numeric>{measurement(load, "t")}</TableCell>
                  <TableCell>
                    <span className="font-medium">{humanize(journey.estado)}</span>
                    <details className="mt-1">
                      <summary className="cursor-pointer text-xs font-bold text-[var(--brand-primary)]">Más detalles</summary>
                      <dl className="mt-2 space-y-1 text-xs text-[var(--text-muted)]">
                        {journey.vehiculo_detalle && <div><dt className="inline font-bold">Vehículo: </dt><dd className="inline">{journey.vehiculo_detalle.patente || journey.vehiculo_detalle.nombre || "Sin información"}</dd></div>}
                        <div><dt className="inline font-bold">Trayecto: </dt><dd className="inline">{humanize(journey.tipo_trayecto)} · {humanize(journey.estado_carga)}</dd></div>
                        {fuel !== null && fuel !== undefined && <div><dt className="inline font-bold">Combustible: </dt><dd className="inline">{measurement(fuel, "L")}</dd></div>}
                        {methodology && <div><dt className="inline font-bold">Metodología tercerizada: </dt><dd className="inline">{humanize(methodology)}</dd></div>}
                      </dl>
                    </details>
                  </TableCell>
                  <TableCell>{origins.length
                    ? <details>
                      <summary className="cursor-pointer font-bold text-[var(--brand-primary)]">Ver trazabilidad</summary>
                      <div className="mt-2 space-y-1 text-xs">{origins.map((origin) => <div key={`${origin.label}-${origin.evidenceId || origin.sensorId || origin.source}`}>
                        <b>{origin.label}:</b>{" "}
                        {origin.evidenceId
                          ? <Link className="font-bold text-[var(--brand-primary)]" to={`/datos/evidencias/${origin.evidenceId}`}>Documento</Link>
                          : origin.sensorId
                            ? <Link className="font-bold text-[var(--brand-primary)]" to={`/operacion/sensores/${origin.sensorId}`}>Sensor</Link>
                            : origin.source}
                      </div>)}</div>
                    </details>
                    : "Sin origen identificable"}</TableCell>
                </tr>;
              })}</TableBody>
            </TableShell>
          </section>}
      <DomainSensorsPanel
        domain="transporte"
        operation={operation}
        organizationId={
          context?.references?.organization
        }
        workId={persistedWorkId}
        onCreated={
          reloadOperation
        }
      />
      <DomainQualityPanel
        domain="transporte"
        organizationId={
          context?.references?.organization
        }
        workId={
          persistedWorkId
        }
      />
      <DomainCalculationPanel
        domain="transporte"
        operation={operation}
        organizationId={
          context?.references?.organization
        }
        onCalculated={
          reloadOperation
        }
      />
      <TransportRecordModal
        open={recordOpen}
        onClose={() =>
          setRecordOpen(false)
        }
        organizationId={
          context?.references?.organization
        }
        workId={persistedWorkId}
        onCreated={reloadOperation}
      />
    </OperationDomainShell>
  );
}