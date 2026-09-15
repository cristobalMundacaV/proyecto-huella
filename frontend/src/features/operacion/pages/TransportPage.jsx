import { Link, useOutletContext, useParams } from "react-router-dom";
import { ClipboardCheck, Plus } from "lucide-react";
import { Button, ButtonLink, EmptyState, ErrorState, KpiCard, Pagination, SectionHeader, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime, formatNumber } from "@/shared/utils/formatters";
import { applicability, explicitDomainActivities, isResourceReady, resourceData, transportMetrics } from "../utils/operationSelectors";
import { useEffect, useMemo, useState } from "react";
import TransportRecordModal from "../components/TransportRecordModal";
import OperationDomainShell from "../components/OperationDomainShell";
import DomainSensorsPanel from "../components/DomainSensorsPanel";
import DomainQualityPanel from "../components/DomainQualityPanel";
import DomainCalculationPanel from "../components/DomainCalculationPanel";
import { useFlowSection } from "../components/FlowWorkspaceNav";
import FlowQuickRead from "../components/FlowQuickRead";
import EnvironmentalTrendChart from "@/shared/charts/EnvironmentalTrendChart";
import { getFlowChartColor } from "@/shared/config/environmentalDomains";

const humanize = (value) => value ? String(value).replaceAll("_", " ") : "Sin información";
const PAGE_SIZE = 8;

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
  const section = useFlowSection();
  const { obraId } = useParams();
  const {
    obra,
    context,
    operation,
    reloadOperation,
  } = useOutletContext();

  const [recordOpen, setRecordOpen] =
    useState(false);
  const [page, setPage] = useState(1);

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
  const applicabilityBadge = noApplicable ? "No aplica" : unresolved ? "Aplicabilidad por definir" : "Aplica";
  useEffect(() => { setPage(1); }, [journeys.length, persistedWorkId]);
  const pagedJourneys = useMemo(() => journeys.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), [journeys, page]);
  const distanceTrend = useMemo(() => journeys.filter((journey) => journey.metricas?.distancia_km !== null && journey.metricas?.distancia_km !== undefined && Number.isFinite(Number(journey.metricas.distancia_km)))
    .map((journey) => ({ label: formatDateTime(journey.fecha_salida), value: Number(journey.metricas.distancia_km), unit: "km", timestamp: journey.fecha_salida }))
    .toSorted((a, b) => String(a.timestamp).localeCompare(String(b.timestamp))).slice(-12), [journeys]);
  const transportActivities = useMemo(
    () => explicitDomainActivities(
      journeys.map((journey) => journey.actividad_detalle),
      "transporte",
    ),
    [journeys],
  );

  return (
    <OperationDomainShell
      domainKey="transporte"
      title="Transporte"
      description="¿Cómo se está moviendo carga o personas en esta obra?"
      badges={[applicabilityBadge, journeysReady ? (journeys.length ? `${journeys.length} ${journeys.length === 1 ? "viaje" : "viajes"}` : "Sin viajes") : "Viajes no disponibles", noApplicable ? "Flujo deshabilitado" : unresolved ? "Requiere definición" : "Flujo habilitado"]}
      primaryAction={!noApplicable && (unresolved ? <ButtonLink leftIcon={ClipboardCheck} to={`/obras/${obraId}/diagnostico`}>Revisar perfil ambiental</ButtonLink> : <Button leftIcon={Plus} onClick={() => setRecordOpen(true)}>Registrar viaje</Button>)}
      secondaryAction={!noApplicable && <ButtonLink leftIcon={Plus} variant="secondary" to={`/obras/${obraId}/evidencias`}>{unresolved ? "Agregar evidencia" : "Agregar documento"}</ButtonLink>}
    >
      {section === "resumen" && noApplicable && <EmptyState title="No aplica a esta obra" description="Transporte está marcado como no aplicable; la ausencia de viajes no se interpreta como cero." />}
      {section === "resumen" && unresolved && <EmptyState title="Aplicabilidad por definir" description="Aún no existe información suficiente para determinar si transporte aplica a esta obra." />}
      {section === "resumen" && !noApplicable && !unresolved && journeysReady && !journeys.length && <EmptyState title="Sin viajes registrados" description="Aún no hay viajes registrados para esta obra." />}
      {section === "resumen" && journeysReady && <FlowQuickRead
        base={`/obras/${obraId}/operacion/transporte`}
        records={journeysReady ? journeys.length : null}
        latest={journeys.length ? formatDateTime(journeys.at(-1)?.fecha_salida) : null}
        quality={"Ver estado de los viajes"}
        evidence={`${journeys.filter((journey) => journey.distancia_detalle?.evidencia || journey.carga_detalle?.evidencia || journey.combustible_detalle?.evidencia).length} viajes con evidencia`}
        noData={!journeys.length}
      />}
      {section === "tendencias" && noApplicable && <EmptyState title="No aplica a esta obra" description="Transporte está marcado como no aplicable; la ausencia de viajes no se interpreta como cero." />}
      {section === "tendencias" && unresolved && <EmptyState title="Aplicabilidad por definir" description="Aún no existe información suficiente para determinar si transporte aplica a esta obra." />}
      {section === "tendencias" && !noApplicable && !unresolved && (distanceTrend.length ? <section className="rounded-[22px] border border-slate-200 bg-white p-5 shadow-sm">
        <SectionHeader title="Distancia por viaje" description="Distancias observadas en orden cronológico, sin estimar viajes faltantes." />
        <EnvironmentalTrendChart data={distanceTrend} color={getFlowChartColor("transporte")} valueFormatter={(value) => `${formatNumber(value)} km`} />
      </section> : <EmptyState title="Sin tendencia disponible" description="No hay distancias numéricas registradas para representar una serie." />)}
      {section === "resumen" && !noApplicable && !unresolved && (indicatorsReady
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
        : <ErrorState title="No fue posible cargar el resumen de transporte" description="Los viajes continúan disponibles si pudieron cargarse." />)}

      {section === "registros" && (noApplicable
        ? <EmptyState title="No aplica a esta unidad" description="Transporte está marcado como no aplicable. La ausencia de viajes no se presenta como cero operacional." />
        : unresolved
          ? <EmptyState title="Aplicabilidad por definir" description="Aún no existe información suficiente para determinar si transporte aplica a esta obra." />
        : !journeysReady
        ? <ErrorState title="No fue posible cargar los viajes" description="El resumen de transporte continúa disponible si pudo calcularse." />
        : !journeys.length
          ? <EmptyState
                title="Sin viajes registrados"
                description="Aún no hay movimientos de transporte registrados para esta unidad. Comienza registrando un viaje o adjuntando documentación de respaldo."
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
              <TableBody columns={6}>{pagedJourneys.map((journey) => {
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
            <Pagination page={page} totalItems={journeys.length} pageSize={PAGE_SIZE} onChange={setPage} itemLabel="viajes" />
          </section>)}
      {section === "sensores" && noApplicable && <EmptyState title="No aplica a esta obra" description="Transporte está marcado como no aplicable; la ausencia de viajes no se interpreta como cero." />}
      {section === "sensores" && unresolved && <EmptyState title="Aplicabilidad por definir" description="Aún no existe información suficiente para determinar si transporte aplica a esta obra." />}
      {section === "sensores" && !noApplicable && !unresolved && <DomainSensorsPanel
        domain="transporte"
        operation={operation}
        organizationId={
          context?.references?.organization
        }
        workId={persistedWorkId}
        onCreated={
          reloadOperation
        }
      />}
      {section === "calidad" && noApplicable && <EmptyState title="No aplica a esta obra" description="Transporte está marcado como no aplicable; la ausencia de viajes no se interpreta como cero." />}
      {section === "calidad" && unresolved && <EmptyState title="Aplicabilidad por definir" description="Aún no existe información suficiente para determinar si transporte aplica a esta obra." />}
      {section === "calidad" && !noApplicable && !unresolved && <>
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
        activities={transportActivities}
        organizationId={
          context?.references?.organization
        }
        onCalculated={
          reloadOperation
        }
      />
      </>}
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
