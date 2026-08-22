import { Link, useOutletContext } from "react-router-dom";
import { Alert, Card, CardContent, SectionHeader } from "@/shared/ui";
import { formatDateTime, formatNumber } from "@/shared/utils/formatters";
import {
  applicability,
  domainMetrics,
  domainRecords,
  domainState,
  isResourceReady,
  latestMeasurement,
  latestRecord,
  primaryAdditiveMetric,
  resourceData,
} from "../utils/operationSelectors";
import OperationDomainCard from "../components/OperationDomainCard";
import { getEnvironmentalDomain } from "@/shared/config/environmentalDomains";

const domains = [
  "energia", "agua", "combustibles", "transporte", "materiales", "residuos", "ruido", "hidrica-suelo",
].map((key) => { const identity = getEnvironmentalDomain(key); return [key, identity.label, identity.icon]; });

const capabilityFor = (key) => key === "hidrica-suelo" ? "gestion_hidrica_suelo" : key;

function measurementSignal(measurement) {
  const observation = measurement?.observation;
  if (!observation) return null;
  if (observation.valor_numerico !== null && observation.valor_numerico !== undefined) {
    return observation.unidad ? `${formatNumber(observation.valor_numerico)} ${observation.unidad}` : null;
  }
  return observation.valor_texto || null;
}

function sectorDescriptor(key, title, icon, context, indicators, operation) {
  const ready = isResourceReady(operation.records);
  const records = domainRecords(resourceData(operation.records, []), key);
  const metrics = domainMetrics(indicators, key);
  const ambiguousCount = metrics.reduce((sum, metric) => sum + Number(metric.registros_ambiguos || 0), 0);
  const state = domainState({
    applicabilityState: applicability(context, capabilityFor(key)),
    records,
    ambiguous: ambiguousCount > 0,
    available: ready,
  });
  const latest = latestRecord(records, "periodo_inicio");
  const additive = primaryAdditiveMetric(indicators, key);
  let signal = null;

  if (state === "requiere_revision") {
    signal = `${ambiguousCount} ${ambiguousCount === 1 ? "registro ambiguo" : "registros ambiguos"}`;
  } else if (key === "ruido") {
    signal = measurementSignal(latestMeasurement(records));
  } else if (additive && !additive.registros_ambiguos) {
    signal = `${formatNumber(additive.total)} ${additive.unidad}`;
  } else if (records.length) {
    signal = `${records.length} ${records.length === 1 ? "registro" : "registros"}`;
  }

  return {
    key,
    title,
    icon,
    to: key,
    state,
    signal,
    latestAt: latest?.periodo_inicio || null,
    activityCount: records.length,
    reviewReason: state === "requiere_revision" ? "Hay mediciones ambiguas que no se agregaron automáticamente." : null,
  };
}

function transportDescriptor(context, operation) {
  const journeysReady = isResourceReady(operation.journeys);
  const indicatorsReady = isResourceReady(operation.transport);
  const journeys = resourceData(operation.journeys, []);
  const transport = resourceData(operation.transport, null);
  const state = domainState({
    applicabilityState: applicability(context, "transporte"),
    records: journeys,
    available: journeysReady,
  });
  const latest = latestRecord(journeys, "fecha_salida");
  const signal = journeys.length
    ? indicatorsReady && transport?.km_totales !== null && transport?.km_totales !== undefined
      ? `${formatNumber(transport.km_totales)} km`
      : `${journeys.length} ${journeys.length === 1 ? "viaje" : "viajes"}`
    : null;

  return {
    key: "transporte",
    title: "Transporte",
    icon: getEnvironmentalDomain("transporte").icon,
    to: "transporte",
    state,
    signal,
    latestAt: latest?.fecha_salida || null,
    activityCount: journeys.length,
    reviewReason: null,
  };
}

function materialsDescriptor(context, operation) {
  const eventsReady = isResourceReady(operation.materialEvents);
  const balancesReady = isResourceReady(operation.materials);
  const events = resourceData(operation.materialEvents, []);
  const signals = balancesReady
    ? resourceData(operation.materials, []).flatMap((material) => material.senales || [])
    : [];
  const state = domainState({
    applicabilityState: applicability(context, "materiales"),
    records: events,
    ambiguous: signals.length > 0,
    available: eventsReady,
  });
  const latest = latestRecord(events, "fecha_hora");

  return {
    key: "materiales",
    title: "Materiales",
    icon: getEnvironmentalDomain("materiales").icon,
    to: "materiales",
    state,
    signal: signals.length
      ? `${signals.length} ${signals.length === 1 ? "señal por revisar" : "señales por revisar"}`
      : events.length ? `${events.length} ${events.length === 1 ? "evento" : "eventos"}` : null,
    latestAt: latest?.fecha_hora || null,
    activityCount: events.length,
    reviewReason: signals.length ? "El balance de materiales informó señales que requieren revisión." : null,
  };
}

export default function OperacionOverviewPage() {
  const { context, indicators, operation, resourceErrors } = useOutletContext();
  const descriptors = domains.map(([key, title, icon]) => {
    if (key === "transporte") return transportDescriptor(context, operation);
    if (key === "materiales") return materialsDescriptor(context, operation);
    return sectorDescriptor(key, title, icon, context, indicators, operation);
  });

  const activeDomains = descriptors
    .filter((domain) => ["con_datos", "requiere_revision"].includes(domain.state))
    .toSorted((left, right) => String(right.latestAt || "").localeCompare(String(left.latestAt || "")));
  const attention = descriptors.filter((domain) => domain.state === "requiere_revision").slice(0, 5);
  const recent = activeDomains
    .filter((domain) => domain.latestAt)
    .toSorted((left, right) => String(right.latestAt).localeCompare(String(left.latestAt)))
    .slice(0, 3);
  const activityCount = activeDomains.length;
  const unavailableCount = descriptors.filter((domain) => domain.state === "error").length;
  const secondaryUnavailable = Boolean(
    resourceErrors?.indicators
    || (!isResourceReady(operation.transport) && isResourceReady(operation.journeys))
    || (!isResourceReady(operation.materials) && isResourceReady(operation.materialEvents)),
  );

  return <div className="space-y-6">
    <section>
      <SectionHeader
        eyebrow="ESTADO OPERACIONAL"
        title="Resumen de operación"
        description="Actividad registrada, cambios recientes y ámbitos que necesitan revisión."
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:max-w-2xl">
        <Card>
          <CardContent>
            <p className="text-sm text-[var(--text-muted)]">
              Ámbitos con actividad
            </p>

            <p className="mt-1 text-2xl font-black">
              {activityCount}
            </p>
          </CardContent>
        </Card>

        {(attention.length > 0 || unavailableCount > 0) && (
          <Card>
            <CardContent>
              <p className="text-sm text-[var(--text-muted)]">
                {attention.length > 0
                  ? "Ámbitos por revisar"
                  : "Ámbitos no disponibles"}
              </p>

              <p className="mt-1 text-2xl font-black">
                {attention.length > 0
                  ? attention.length
                  : unavailableCount}
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {secondaryUnavailable && (
        <div className="mt-3">
          <Alert tone="warning">
            Algunas señales complementarias no están disponibles. La actividad que sí pudo cargarse se mantiene visible.
          </Alert>
        </div>
      )}
    </section>
    {(attention.length > 0 || recent.length > 0) && <section className="grid gap-4 lg:grid-cols-2">
      {attention.length > 0 && <Card><CardContent>
        <SectionHeader title="Requiere atención" description="Información que necesita revisión antes de interpretarse como normal." />
        <div className="space-y-2">{attention.map((domain) => <Link
          key={domain.key}
          className="flex items-center justify-between gap-3 rounded-[var(--radius-md)] border border-[var(--border-default)] p-3 text-sm focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
          to={domain.to}
        ><span><b>{domain.title}</b><span className="block text-xs text-[var(--text-muted)]">{domain.reviewReason}</span></span><span className="font-bold text-[var(--brand-primary)]">Revisar</span></Link>)}</div>
      </CardContent></Card>}

      {recent.length > 0 && <Card><CardContent>
        <SectionHeader title="Actividad reciente" description="Últimos movimientos o períodos disponibles por dominio." />
        <div className="space-y-2">{recent.map((domain) => <Link
          key={domain.key}
          className="flex items-center justify-between gap-3 rounded-[var(--radius-md)] border border-[var(--border-default)] p-3 text-sm focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
          to={domain.to}
        ><span><b>{domain.title}</b><span className="block text-xs text-[var(--text-muted)]">{domain.signal || "Actividad registrada"}</span></span><span className="shrink-0 text-xs text-[var(--text-muted)]">{formatDateTime(domain.latestAt)}</span></Link>)}</div>
      </CardContent></Card>}
    </section>}

    <section>
      <SectionHeader
        eyebrow="ACTIVIDAD OPERACIONAL"
        title="Actividad registrada"
        description="Ámbitos donde ya existen registros o mediciones asociadas a esta obra."
      />

      <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {descriptors.map((domain) => <OperationDomainCard key={domain.key} domainKey={domain.key} icon={domain.icon} title={domain.title} state={domain.state} signal={domain.signal} detail={domain.reviewReason || (domain.latestAt ? `Último registro: ${formatDateTime(domain.latestAt)}` : "Abre el dominio para revisar su configuración y registros.")} to={domain.to} />)}
      </div>

    </section>
  </div>;
}
