import { useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import {
  Alert,
  Button,
  DataQualityBadge,
  EmptyState,
  ErrorState,
  KpiCard,
  Pagination,
  SectionHeader,
  TableBody,
  TableCell,
  TableHead,
  TableShell,
  TraceabilityLink,
} from "@/shared/ui";
import TraceabilityDrawer from "@/features/datos/components/TraceabilityDrawer";
import { formatDateTime, formatNumber } from "@/shared/utils/formatters";
import DomainCalculationPanel from "../components/DomainCalculationPanel";
import {
  additiveMetrics,
  applicability,
  DOMAIN_CONFIG,
  domainMetrics,
  domainRecords,
  isResourceReady,
  nonAdditiveMetrics,
  recordMeasurements,
  resourceData,
} from "../utils/operationSelectors";
import DomainApplicability from "../components/DomainApplicability";
import OperationDomainShell from "../components/OperationDomainShell";
import ManualFlowRecordModal from "../components/ManualFlowRecordModal";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import DomainSensorsPanel from "../components/DomainSensorsPanel";
import DomainQualityPanel from "../components/DomainQualityPanel";
import { getEnvironmentalDomain } from "@/shared/config/environmentalDomains";

const PAGE_SIZE = 8;

const qualityTone = (state) => state === "validada" ? "success" : state === "rechazada" ? "danger" : "warning";
const humanize = (value) => value ? String(value).replaceAll("_", " ") : "Sin información";

function measurementValue(observation) {
  if (observation.valor_numerico !== null && observation.valor_numerico !== undefined) {
    return observation.unidad
      ? `${formatNumber(observation.valor_numerico)} ${observation.unidad}`
      : `${formatNumber(observation.valor_numerico)} · unidad no informada`;
  }
  return observation.valor_texto || "Sin datos";
}

function rangeHelper(metric) {
  if (metric.minimo === null || metric.minimo === undefined || metric.maximo === null || metric.maximo === undefined) {
    return `${metric.mediciones} mediciones`;
  }
  return `Rango: ${formatNumber(metric.minimo)}–${formatNumber(metric.maximo)}${metric.unidad ? ` ${metric.unidad}` : ""}`;
}

export default function SectorDomainPage({ domain }) {
  const [trace, setTrace] = useState(null);
  const [captureOpen, setCaptureOpen] = useState(false);
  const [page, setPage] = useState(1);
  const { obraId } = useParams();
  const {
    activeOrganizacionId,
  } = useOrganizacionActiva();
  const {
    obra,
    context,
    indicators,
    operation,
    resourceErrors,
    reloadOperation,
  } = useOutletContext();

  const persistedWorkId =
    obra?.id ||
    obra?.obra_id;
  const config = DOMAIN_CONFIG[domain];
  const applicabilityState = applicability(context, config.capability);
  const recordsReady = isResourceReady(operation.records);
  const records = domainRecords(resourceData(operation.records, []), domain);
  const measurements = recordMeasurements(records);
  const additive = domain === "ruido" ? [] : additiveMetrics(indicators, domain);
  const series = nonAdditiveMetrics(indicators, domain);
  const ambiguous = domainMetrics(indicators, domain).filter((metric) => metric.registros_ambiguos > 0);
  const pointsReady = isResourceReady(operation.points);
  const pointNames = new Map(resourceData(operation.points, []).map((point) => [String(point.id), point.nombre]));
  const generationRecords = domain === "energia" ? records.filter((record) => record.flujo === "generacion_propia") : [];
  const generationIdentity = getEnvironmentalDomain("generacion_propia");
  const GenerationIcon = generationIdentity.icon;

  const metricCards = [
    ...additive.map((metric) => ({
      key: `add-${metric.flujo}-${metric.concepto}-${metric.unidad}`,
      label: humanize(metric.concepto),
      value: metric.registros_ambiguos ? null : metric.total,
      unit: metric.unidad || undefined,
      helper: metric.registros_ambiguos ? "Requiere revisión" : `${metric.mediciones} mediciones`,
    })),
    ...series.map((metric) => ({
      key: `series-${metric.flujo}-${metric.concepto}-${metric.unidad}`,
      label: humanize(metric.concepto),
      value: metric.mediciones,
      unit: "mediciones",
      helper: rangeHelper(metric),
    })),
  ].slice(0, 3);

  const noApplicable = applicabilityState === "no_aplica";
  const unresolved = ["pendiente", "no_determinado"].includes(applicabilityState);
  useEffect(() => { setPage(1); }, [domain, measurements.length, persistedWorkId]);
  const pagedMeasurements = useMemo(() => measurements.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), [measurements, page]);

  return (
    <OperationDomainShell
      domainKey={domain}
      title={config.label}
      description={config.question}
      applicability={
        <DomainApplicability
          context={context}
          capability={config.capability}
        />
      }
      action={!noApplicable && !unresolved && records.length > 0 ? <Button leftIcon={Plus} onClick={() => setCaptureOpen(true)}>Registrar información</Button> : undefined}
    >
      {!recordsReady && <ErrorState
        title={`No fue posible cargar ${config.label.toLowerCase()}`}
        description="Los demás dominios operacionales continúan disponibles."
      />}

      {recordsReady && !pointsReady && <Alert tone="warning">No fue posible cargar los puntos de medición. Los registros disponibles se mantienen visibles sin ese nombre de contexto.</Alert>}
      {recordsReady && resourceErrors?.indicators && <Alert tone="warning">No fue posible cargar el resumen de mediciones. Los registros disponibles se mantienen visibles, pero no se infiere agregación ni ausencia de ambigüedades.</Alert>}

      {recordsReady && <>
        {ambiguous.length > 0 && <Alert tone="warning" title="Requiere revisión">
          Hay registros con múltiples mediciones que el sistema marca como ambiguos. No se agregaron automáticamente.
        </Alert>}

        {generationRecords.length > 0 && <section className={`flex items-center gap-3 rounded-[20px] border p-4 ${generationIdentity.border} ${generationIdentity.softBg}`}>
          <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white ${generationIdentity.text}`}><GenerationIcon aria-hidden="true" size={19} /></span>
          <div><p className="font-black">Generación propia</p><p className="mt-1 text-sm text-[var(--text-muted)]">{generationRecords.length} {generationRecords.length === 1 ? "registro diferenciado del consumo eléctrico" : "registros diferenciados del consumo eléctrico"}.</p></div>
        </section>}

        {!noApplicable && !unresolved && metricCards.length > 0 && <section>
          <SectionHeader
            eyebrow="LECTURA DEL ÁMBITO"
            title="Resumen"
            description={domain === "ruido" || domain === "hidrica-suelo" ? "Las mediciones no aditivas se muestran como serie o rango, nunca como total acumulado." : "Sólo se agregan magnitudes que el contrato declara como sumables."} />
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{metricCards.map((metric) => <KpiCard
            key={metric.key}
            label={metric.label}
            value={metric.value}
            unit={metric.unit}
            helper={metric.helper}
          />)}</div>
        </section>}

        {noApplicable
          ? <EmptyState
              title="No aplica a esta obra"
              description="Este ámbito está marcado como no aplicable. La ausencia de registros no se interpreta como cero."
            />
          : unresolved
            ? <EmptyState
                title="Aplicabilidad por definir"
                description="Aún no existe información suficiente para determinar si este ámbito aplica a la obra."
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
            : !records.length
              ? <EmptyState
                title="Sin información registrada"
                description={`Aún no hay registros de ${config.label.toLowerCase()} para esta obra.`}
                primaryAction={<Button leftIcon={Plus} onClick={() => setCaptureOpen(true)}>Registrar información</Button>}
                secondaryAction={<Link className="font-bold text-[var(--text-secondary)]" to={`/obras/${obraId}/evidencias`}>Agregar documento</Link>}
              />
          : <section>
            <SectionHeader
              eyebrow="ACTIVIDAD REGISTRADA"
              title={
                domain === "ruido"
                  ? "Mediciones acústicas"
                  : domain === "hidrica-suelo"
                    ? "Condiciones registradas"
                    : "Registros recientes"
              }
              description="Valor observado, contexto y origen se mantienen separados."
              count={measurements.length}
            />
            {!measurements.length
              ? <EmptyState title="Sin mediciones disponibles" description="Existen registros del dominio, pero no contienen observaciones visibles en el contrato actual." />
              : <TableShell>
                <TableHead><tr>
                  <TableCell as="th">Fecha</TableCell>
                  <TableCell as="th">Concepto</TableCell>
                  <TableCell as="th">Valor</TableCell>
                  <TableCell as="th">Contexto</TableCell>
                  <TableCell as="th">Calidad</TableCell>
                  <TableCell as="th">Origen</TableCell>
                </tr></TableHead>
                <TableBody columns={6}>{pagedMeasurements.map(({ record, observation }) => {
                  const contextLabel = pointNames.get(String(record.punto))
                    || record.ubicacion_contexto
                    || humanize(record.granularidad);
                  const hasTrace = observation.evidencia || observation.fuente_detalle;
                  return <tr key={observation.id}>
                    <TableCell>{formatDateTime(observation.timestamp_observacion || record.periodo_inicio)}</TableCell>
                    <TableCell><span className="font-bold">{humanize(observation.concepto)}</span>{(record.tipo_recurso || record.metrica) && <span className="block text-xs text-[var(--text-muted)]">{record.tipo_recurso || record.metrica}</span>}</TableCell>
                    <TableCell>{measurementValue(observation)}</TableCell>
                    <TableCell>{contextLabel}</TableCell>
                    <TableCell><DataQualityBadge label={humanize(observation.estado)} tone={qualityTone(observation.estado)} /></TableCell>
                    <TableCell>{observation.sensor_detalle
                      ? <Link className="font-bold text-[var(--brand-primary)]" to={`/operacion/sensores/${observation.sensor_detalle.id}`}>Sensor</Link>
                      : hasTrace
                        ? <TraceabilityLink onClick={() => setTrace(observation)} />
                        : "Sin origen identificable"}</TableCell>
                  </tr>;
                })}</TableBody>
              </TableShell>}
            <Pagination page={page} totalItems={measurements.length} pageSize={PAGE_SIZE} onChange={setPage} itemLabel={domain === "ruido" ? "mediciones acústicas" : "registros"} />
          </section>}
      </>}
      {!noApplicable && !unresolved && records.length > 0 && <>
      <DomainSensorsPanel
        domain={domain}
        operation={operation}
        organizationId={
          activeOrganizacionId
        }
        workId={
          persistedWorkId
        }
        onCreated={
          reloadOperation
        }
      />

      <DomainQualityPanel
        domain={domain}
        organizationId={
          activeOrganizacionId
        }
        workId={
          persistedWorkId
        }
      />

      <DomainCalculationPanel
        domain={domain}
        operation={operation}
        organizationId={
          activeOrganizacionId
        }
        onCalculated={
          reloadOperation
        }
      />
      </>}

      <TraceabilityDrawer
        observation={trace}
        open={Boolean(trace)}
        onClose={() => setTrace(null)}
        workId={obraId}
      />
      <ManualFlowRecordModal
        open={captureOpen}
        onClose={() =>
          setCaptureOpen(false)
        }
        organizationId={
          activeOrganizacionId
        }
        workId={
          persistedWorkId
        }
        domain={domain}
        onCreated={
          reloadOperation
        }
      />
    </OperationDomainShell>
  );
}
