import { useEffect, useMemo, useState } from "react";
import { ClipboardCheck, Plus } from "lucide-react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import {
  Alert,
  Button,
  ButtonLink,
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
import OperationDomainShell from "../components/OperationDomainShell";
import ManualFlowRecordModal from "../components/ManualFlowRecordModal";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import DomainSensorsPanel from "../components/DomainSensorsPanel";
import DomainQualityPanel from "../components/DomainQualityPanel";
import { getEnvironmentalDomain } from "@/shared/config/environmentalDomains";

const PAGE_SIZE = 8;

const qualityTone = (state) =>
  state === "validada"
    ? "success"
    : state === "rechazada"
      ? "danger"
      : "warning";

const DISPLAY_LABELS = {
  diesel: "Diésel",
  gasolina: "Gasolina",
  gas_licuado: "Gas licuado",
  gas_natural: "Gas natural",

  generador: "Generador",
  maquinaria: "Maquinaria",
  vehiculo: "Vehículo",
  equipo_menor: "Equipo menor",
  calefaccion: "Calefacción",

  obra: "Obra",
  manual: "Manual",
  declarativo: "Declarativo",
  pendiente: "Pendiente",
  validada: "Validada",
  rechazada: "Rechazada",

  combustible_consumido:
    "Combustible consumido",
};

function humanize(value) {
  if (!value) {
    return "Sin información";
  }

  const raw =
    String(value);

  if (DISPLAY_LABELS[raw]) {
    return DISPLAY_LABELS[raw];
  }

  const normalized =
    raw.replaceAll(
      "_",
      " ",
    );

  return (
    normalized
      .charAt(0)
      .toUpperCase() +
    normalized.slice(1)
  );
}

function resourceLabel(value) {
  if (!value) {
    return "Sin tipo informado";
  }

  return (
    DISPLAY_LABELS[value] ||
    humanize(value)
  );
}

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
  const applicabilityState = applicability(context, config.capabilities || config.capability);
  const recordsReady = isResourceReady(operation.records);
  const records = domainRecords(resourceData(operation.records, []), domain);
  const measurements = recordMeasurements(records);
  const additive = ["ruido", "emisiones-atmosfericas", "suelo"].includes(domain) ? [] : additiveMetrics(indicators, domain);
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
      value: metric.registros_ambiguos
        ? null
        : metric.total,
      unit:
        metric.unidad ||
        undefined,
      helper:
        metric.registros_ambiguos
          ? "Requiere revisión"
          : `${metric.mediciones} mediciones`,
    })),

    ...series.map((metric) => ({
      key: `series-${metric.flujo}-${metric.concepto}-${metric.unidad}`,
      label: humanize(metric.concepto),
      value: metric.mediciones,
      unit: "mediciones",
      helper: rangeHelper(metric),
    })),
  ].slice(0, 3);

  const fuelTotalMetric =
    additive.find(
      (metric) =>
        metric.concepto ===
        "combustible_consumido" &&
        !metric.registros_ambiguos,
    );

  const fuelSummaryCards =
    useMemo(
      () => {
        if (
          domain !==
          "combustibles" ||
          !records.length
        ) {
          return [];
        }

        const resourceCounts =
          new Map();

        const destinationCounts =
          new Map();

        for (
          const record
          of records
        ) {
          if (
            record.tipo_recurso
          ) {
            resourceCounts.set(
              record.tipo_recurso,
              (
                resourceCounts.get(
                  record.tipo_recurso,
                ) || 0
              ) + 1,
            );
          }

          if (
            record.destino_operacional &&
            record.destino_operacional !==
            "sin_clasificar"
          ) {
            destinationCounts.set(
              record.destino_operacional,
              (
                destinationCounts.get(
                  record.destino_operacional,
                ) || 0
              ) + 1,
            );
          }
        }

        const mostFrequent =
          (map) =>
            [
              ...map.entries(),
            ].sort(
              (
                left,
                right,
              ) =>
                right[1] -
                left[1],
            )[0] || null;

        const mostUsedFuel =
          mostFrequent(
            resourceCounts,
          );

        const mostUsedDestination =
          mostFrequent(
            destinationCounts,
          );

        return [
          {
            key:
              "fuel-total",

            label:
              "Consumo acumulado",

            value:
              fuelTotalMetric
                ?.total ??
              null,

            unit:
              fuelTotalMetric
                ?.unidad ||
              undefined,

            helper:
              `${records.length} ${records.length ===
                1
                ? "registro"
                : "registros"
              }`,
          },

          {
            key:
              "fuel-type",

            label:
              "Combustible predominante",

            value:
              mostUsedFuel
                ? resourceLabel(
                  mostUsedFuel[0],
                )
                : "Sin datos",

            helper:
              mostUsedFuel
                ? `${mostUsedFuel[1]} ${mostUsedFuel[1] ===
                  1
                  ? "registro"
                  : "registros"
                }`
                : "Sin registros clasificados",
          },

          {
            key:
              "fuel-destination",

            label:
              "Destino principal",

            value:
              mostUsedDestination
                ? humanize(
                  mostUsedDestination[0],
                )
                : "Sin datos",

            helper:
              mostUsedDestination
                ? `${mostUsedDestination[1]} ${mostUsedDestination[1] ===
                  1
                  ? "registro"
                  : "registros"
                }`
                : "Sin uso informado",
          },
        ];
      },
      [
        domain,
        records,
        fuelTotalMetric,
      ],
    );

  const visibleMetricCards =
    domain ===
      "combustibles"
      ? fuelSummaryCards
      : metricCards;

  const noApplicable = applicabilityState === "no_aplica";
  const unresolved = ["pendiente", "no_determinado"].includes(applicabilityState);
  useEffect(() => { setPage(1); }, [domain, measurements.length, persistedWorkId]);
  const pagedMeasurements = useMemo(() => measurements.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), [measurements, page]);
  const latestMeasurement =
    useMemo(
      () => {
        if (
          !measurements.length
        ) {
          return null;
        }

        return [
          ...measurements,
        ].sort(
          (
            left,
            right,
          ) => {
            const leftDate =
              left.observation
                ?.timestamp_observacion ||
              left.record
                ?.periodo_inicio;

            const rightDate =
              right.observation
                ?.timestamp_observacion ||
              right.record
                ?.periodo_inicio;

            return (
              new Date(
                rightDate,
              ) -
              new Date(
                leftDate,
              )
            );
          },
        )[0];
      },
      [measurements],
    );

  const heroStats =
    domain ===
      "combustibles" &&
      latestMeasurement
      ? [
        {
          label:
            "Último registro",

          value:
            formatDateTime(
              latestMeasurement
                .observation
                ?.timestamp_observacion ||
              latestMeasurement
                .record
                ?.periodo_inicio,
            ),
        },

        {
          label:
            "Consumo registrado",

          value:
            fuelTotalMetric
              ?.total !==
              null &&
              fuelTotalMetric
                ?.total !==
              undefined
              ? `${formatNumber(
                fuelTotalMetric.total,
              )} ${fuelTotalMetric.unidad || ""}`.trim()
              : "Sin total disponible",
        },

        {
          label:
            "Último origen",

          value:
            latestMeasurement
              .observation
              ?.fuente_detalle
              ?.nombre ||
            "Sin fuente identificada",
        },

        {
          label:
            "Estado del dato",

          value:
            humanize(
              latestMeasurement
                .observation
                ?.estado,
            ),
        },
      ]
      : [];

  return (
    <OperationDomainShell
      domainKey={domain}
      heroStats={heroStats}
      title={config.label}
      description={config.question}
      badges={[
        noApplicable
          ? "Flujo deshabilitado"
          : "Flujo habilitado",

        recordsReady
          ? records.length
            ? `${records.length} ${records.length === 1
              ? "registro"
              : "registros"
            }`
            : "Sin registros"
          : "Registros no disponibles",
      ]}
      primaryAction={!noApplicable && (unresolved ? <ButtonLink leftIcon={ClipboardCheck} to={`/obras/${obraId}/diagnostico`}>Revisar perfil ambiental</ButtonLink> : <Button leftIcon={Plus} onClick={() => setCaptureOpen(true)}>Registrar información</Button>)}
      secondaryAction={!noApplicable && <ButtonLink leftIcon={Plus} variant="secondary" to={`/obras/${obraId}/evidencias`}>{unresolved ? "Agregar evidencia" : "Agregar documento"}</ButtonLink>}
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

        {!noApplicable && !unresolved && visibleMetricCards.length > 0 && <section>
          <SectionHeader
            eyebrow="LECTURA DEL ÁMBITO"
            title="Resumen"
            description={
              domain === "combustibles"
                ? "Lectura rápida del consumo y uso de combustibles registrados en esta obra."
                : ["ruido", "emisiones-atmosfericas", "suelo"].includes(domain)
                  ? "Las mediciones no aditivas se muestran como serie o rango, nunca como total acumulado."
                  : "Sólo se agregan magnitudes que el contrato declara como sumables."
            } />
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{visibleMetricCards.map((metric) => <KpiCard
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
            />
            : !records.length
              ? <EmptyState
                title="Sin información registrada"
                description={`Aún no hay registros de ${config.label.toLowerCase()} para esta obra. Comienza registrando información o adjuntando documentación de respaldo.`}
              />
              : <section>
                <SectionHeader
                  eyebrow="ACTIVIDAD REGISTRADA"
                  title={
                    domain === "ruido"
                      ? "Mediciones acústicas"
                      : domain === "suelo"
                        ? "Condiciones registradas"
                        : "Registros recientes"
                  }
                  description={
                    domain === "combustibles"
                      ? "Consumos registrados, uso, fuente y trazabilidad documental."
                      : "Valor observado, contexto y origen se mantienen separados."
                  }
                  count={
                    domain ===
                      "combustibles"
                      ? undefined
                      : measurements.length
                  }
                />
                {!measurements.length
                  ? <EmptyState title="Sin mediciones disponibles" description="Existen registros del dominio, pero no contienen observaciones visibles en el contrato actual." />
                  : (
                    <TableShell>
                      <TableHead>
                        <tr>
                          {domain ===
                            "combustibles" ? (
                            <>
                              <TableCell as="th">
                                Fecha
                              </TableCell>

                              <TableCell as="th">
                                Tipo de combustible
                              </TableCell>

                              <TableCell as="th">
                                Cantidad
                              </TableCell>

                              <TableCell as="th">
                                Uso / destino
                              </TableCell>

                              <TableCell as="th">
                                Calidad
                              </TableCell>

                              <TableCell as="th">
                                Fuente
                              </TableCell>

                              <TableCell as="th">
                                Origen
                              </TableCell>
                            </>
                          ) : (
                            <>
                              <TableCell as="th">
                                Fecha
                              </TableCell>

                              <TableCell as="th">
                                Concepto
                              </TableCell>

                              <TableCell as="th">
                                Valor
                              </TableCell>

                              <TableCell as="th">
                                Contexto
                              </TableCell>

                              <TableCell as="th">
                                Calidad
                              </TableCell>

                              <TableCell as="th">
                                Origen
                              </TableCell>
                            </>
                          )}
                        </tr>
                      </TableHead>

                      <TableBody
                        columns={
                          domain ===
                            "combustibles"
                            ? 7
                            : 6
                        }
                      >
                        {pagedMeasurements.map(
                          ({
                            record,
                            observation,
                          }) => {
                            const contextLabel =
                              pointNames.get(
                                String(
                                  record.punto,
                                ),
                              ) ||
                              record.ubicacion_contexto ||
                              humanize(
                                record.granularidad,
                              );

                            const hasTrace =
                              observation.evidencia ||
                              observation.fuente_detalle;

                            const sourceName =
                              observation
                                .fuente_detalle
                                ?.nombre ||
                              "Sin fuente identificada";

                            if (
                              domain ===
                              "combustibles"
                            ) {
                              return (
                                <tr
                                  key={
                                    observation.id
                                  }
                                >
                                  <TableCell>
                                    {formatDateTime(
                                      observation.timestamp_observacion ||
                                      record.periodo_inicio,
                                    )}
                                  </TableCell>

                                  <TableCell>
                                    <span className="font-black">
                                      {resourceLabel(
                                        record.tipo_recurso,
                                      )}
                                    </span>
                                  </TableCell>

                                  <TableCell>
                                    <span className="font-black">
                                      {measurementValue(
                                        observation,
                                      )}
                                    </span>
                                  </TableCell>

                                  <TableCell>
                                    {humanize(
                                      record.destino_operacional,
                                    )}
                                  </TableCell>

                                  <TableCell>
                                    <DataQualityBadge
                                      label={humanize(
                                        observation.estado,
                                      )}
                                      tone={qualityTone(
                                        observation.estado,
                                      )}
                                    />
                                  </TableCell>

                                  <TableCell>
                                    <span className="font-medium">
                                      {sourceName}
                                    </span>
                                  </TableCell>

                                  <TableCell>
                                    {observation.sensor_detalle ? (
                                      <Link
                                        className="
                                      font-bold
                                      text-[var(--brand-primary)]
                                    "
                                        to={`/operacion/sensores/${observation.sensor_detalle.id}`}
                                      >
                                        Sensor
                                      </Link>
                                    ) : hasTrace ? (
                                      <TraceabilityLink
                                        label="Ver origen"
                                        iconOnly
                                        onClick={() =>
                                          setTrace({
                                            ...observation,
                                            __record:
                                              record,
                                          })
                                        }
                                      />
                                    ) : (
                                      "Sin origen identificable"
                                    )}
                                  </TableCell>
                                </tr>
                              );
                            }

                            return (
                              <tr
                                key={
                                  observation.id
                                }
                              >
                                <TableCell>
                                  {formatDateTime(
                                    observation.timestamp_observacion ||
                                    record.periodo_inicio,
                                  )}
                                </TableCell>

                                <TableCell>
                                  <span className="font-bold">
                                    {humanize(
                                      observation.concepto,
                                    )}
                                  </span>

                                  {(record.tipo_recurso ||
                                    record.metrica) && (
                                      <span className="
                                  block text-xs
                                  text-[var(--text-muted)]
                                ">
                                        {resourceLabel(
                                          record.tipo_recurso ||
                                          record.metrica,
                                        )}
                                      </span>
                                    )}
                                </TableCell>

                                <TableCell>
                                  {measurementValue(
                                    observation,
                                  )}
                                </TableCell>

                                <TableCell>
                                  {contextLabel}
                                </TableCell>

                                <TableCell>
                                  <DataQualityBadge
                                    label={humanize(
                                      observation.estado,
                                    )}
                                    tone={qualityTone(
                                      observation.estado,
                                    )}
                                  />
                                </TableCell>

                                <TableCell>
                                  {hasTrace ? (
                                    <TraceabilityLink
                                      onClick={() =>
                                        setTrace({
                                          ...observation,
                                          __record:
                                            record,
                                        })
                                      }
                                    />
                                  ) : (
                                    "Sin origen identificable"
                                  )}
                                </TableCell>
                              </tr>
                            );
                          },
                        )}
                      </TableBody>
                    </TableShell>
                  )}
                <Pagination page={page} totalItems={measurements.length} pageSize={PAGE_SIZE} onChange={setPage} itemLabel={domain === "ruido" ? "mediciones acústicas" : "registros"} />
              </section>}
      </>}
      {!noApplicable && !unresolved && records.length > 0 && <>
        <DomainQualityPanel
          domain={domain}
          organizationId={
            activeOrganizacionId
          }
          workId={
            persistedWorkId
          }
          records={records}
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
