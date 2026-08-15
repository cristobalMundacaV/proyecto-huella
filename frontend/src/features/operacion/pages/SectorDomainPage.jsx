import { Link, useOutletContext, useParams } from "react-router-dom";
import { Alert, DataQualityBadge, EmptyState, ErrorState, KpiCard, SectionHeader, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime, formatNumber } from "@/shared/utils/formatters";
import { additiveMetrics, DOMAIN_CONFIG, domainMetrics, domainRecords, isResourceReady, nonAdditiveMetrics, recordMeasurements, resourceData } from "../utils/operationSelectors";
import DomainApplicability from "../components/DomainApplicability";

const qualityTone = (state) => state === "validada" ? "success" : state === "rechazada" ? "danger" : "warning";

export default function SectorDomainPage({ domain }) {
  const { obraId } = useParams();
  const { context, indicators, operation } = useOutletContext();
  const config = DOMAIN_CONFIG[domain];
  const recordsReady = isResourceReady(operation.records);
  const records = domainRecords(resourceData(operation.records, []), domain);
  const measurements = recordMeasurements(records);
  const additive = additiveMetrics(indicators, domain);
  const series = nonAdditiveMetrics(indicators, domain);
  const ambiguous = domainMetrics(indicators, domain).filter((metric) => metric.registros_ambiguos > 0);
  const pointsReady = isResourceReady(operation.points);
  const pointNames = new Map(resourceData(operation.points, []).map((point) => [String(point.id), point.nombre]));

  return <div className="space-y-6">
    <SectionHeader title={config.label} description={domain === "ruido" ? "Mediciones acústicas operacionales; los decibeles nunca se suman." : domain === "hidrica-suelo" ? "Inspecciones y hechos de drenaje, erosión, sedimentos y suelo." : "Datos operacionales registrados dentro de esta obra."} />
    <DomainApplicability context={context} capability={config.capability} />
    {!recordsReady && <ErrorState title={`No fue posible cargar los registros de ${config.label.toLowerCase()}`} description="Los demás dominios operacionales continúan disponibles." />}
    {recordsReady && !pointsReady && <Alert tone="warning">No fue posible cargar los puntos ambientales. Los registros disponibles se muestran sin el nombre del punto.</Alert>}
    {recordsReady && <>
    {ambiguous.length > 0 && <Alert tone="warning" title="Requiere revisión">Hay registros con múltiples mediciones que el backend marca como ambiguos. No se sumaron automáticamente.</Alert>}
    {additive.length > 0 && <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{additive.slice(0, 4).map((metric) => <KpiCard key={`${metric.flujo}-${metric.concepto}-${metric.unidad}`} label={metric.concepto.replaceAll("_", " ")} value={metric.registros_ambiguos ? null : metric.total} unit={metric.unidad} helper={metric.registros_ambiguos ? "Requiere revisión" : `${metric.mediciones} mediciones`} />)}</section>}
    {series.length > 0 && <section><SectionHeader title="Mediciones no aditivas" description="Se muestran rango y cantidad; nunca un total." /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{series.slice(0, 4).map((metric) => <KpiCard key={`${metric.flujo}-${metric.concepto}-${metric.unidad}`} label={metric.concepto.replaceAll("_", " ")} value={metric.mediciones} unit="mediciones" helper={`Rango: ${formatNumber(metric.minimo)}–${formatNumber(metric.maximo)} ${metric.unidad || ""}`} />)}</div></section>}
    {!records.length ? <EmptyState title={`No hay datos de ${config.label.toLowerCase()} para esta obra`} description="Puedes incorporar respaldo documental o importar datos operacionales." primaryAction={<Link className="font-bold text-[var(--brand-primary)]" to="/datos/evidencias">Agregar evidencia</Link>} secondaryAction={<Link className="font-bold text-[var(--text-secondary)]" to="/datos/importaciones">Importar datos</Link>} /> : <section><SectionHeader title={domain === "ruido" ? "Mediciones acústicas" : domain === "hidrica-suelo" ? "Inspecciones y observaciones" : "Registros recientes"} count={measurements.length} />
      <TableShell><TableHead><tr><TableCell as="th">Fecha</TableCell><TableCell as="th">Concepto</TableCell><TableCell as="th">Valor</TableCell><TableCell as="th">Contexto</TableCell><TableCell as="th">Calidad</TableCell><TableCell as="th">Origen</TableCell></tr></TableHead><TableBody columns={6} empty={!measurements.length}>{measurements.map(({ record, observation }) => <tr key={observation.id}><TableCell>{formatDateTime(observation.timestamp_observacion || record.periodo_inicio)}</TableCell><TableCell><span className="font-bold">{observation.concepto.replaceAll("_", " ")}</span><span className="block text-xs text-[var(--text-muted)]">{record.tipo_recurso || record.metrica || record.flujo}</span></TableCell><TableCell>{observation.valor_numerico === null ? observation.valor_texto : formatNumber(observation.valor_numerico)} {observation.unidad}</TableCell><TableCell>{pointNames.get(String(record.punto)) || record.proceso || record.activo || record.granularidad}</TableCell><TableCell><DataQualityBadge label={observation.estado.replaceAll("_", " ")} tone={qualityTone(observation.estado)} /></TableCell><TableCell>{observation.evidencia ? <Link className="text-sm font-bold text-[var(--brand-primary)]" to={`/obras/${obraId}/evidencias`}>Ver origen</Link> : observation.fuente_detalle?.nombre || "Sin evidencia"}</TableCell></tr>)}</TableBody></TableShell>
    </section>}
    </>}
  </div>;
}
