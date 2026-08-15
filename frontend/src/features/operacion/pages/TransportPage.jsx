import { Link, useOutletContext, useParams } from "react-router-dom";
import { Alert, EmptyState, ErrorState, KpiCard, SectionHeader, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime, formatNumber } from "@/shared/utils/formatters";
import { isResourceReady, resourceData, transportMetrics } from "../utils/operationSelectors";
import DomainApplicability from "../components/DomainApplicability";

export default function TransportPage() {
  const { obraId } = useParams();
  const { context, operation } = useOutletContext();
  const indicatorsReady = isResourceReady(operation.transport);
  const journeysReady = isResourceReady(operation.journeys);
  const transport = resourceData(operation.transport, null);
  const metrics = indicatorsReady ? transportMetrics(transport) : [];
  const journeys = resourceData(operation.journeys, []);
  return <div className="space-y-6">
    <SectionHeader title="Transporte" description="Viajes y eficiencia logística vinculados por backend a esta obra." />
    <DomainApplicability context={context} capability="transporte" />
    {indicatorsReady ? <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{metrics.map((metric) => <KpiCard key={metric.key} label={metric.label} value={metric.value} unit={metric.unit} />)}</section> : <ErrorState title="No fue posible cargar los indicadores de transporte" description="La tabla de viajes continúa disponible si sus datos pudieron cargarse." />}
    {(transport?.oportunidades || []).length > 0 && <Alert tone="warning" title="Atención requerida">{transport.oportunidades.map((item) => <p key={`${item.tipo}-${item.ruta || "general"}`}>{item.tipo.replaceAll("_", " ")}: {formatNumber(item.valor)} {item.unidad}</p>)}</Alert>}
    {!journeysReady ? <ErrorState title="No fue posible cargar los viajes" description="Los indicadores de transporte continúan disponibles si pudieron calcularse." /> : !journeys.length ? <EmptyState title="No hay viajes registrados para esta obra" description="Importa datos o agrega evidencia logística para comenzar el seguimiento." primaryAction={<Link className="font-bold text-[var(--brand-primary)]" to="/datos/importaciones">Importar datos</Link>} /> : <section><SectionHeader title="Viajes" count={journeys.length} />
      <TableShell><TableHead><tr><TableCell as="th">Fecha</TableCell><TableCell as="th">Viaje y ruta</TableCell><TableCell as="th">Vehículo</TableCell><TableCell as="th" numeric>Distancia</TableCell><TableCell as="th" numeric>Carga</TableCell><TableCell as="th">Retorno</TableCell><TableCell as="th">Origen</TableCell></tr></TableHead><TableBody columns={7}>{journeys.map((journey) => <tr key={journey.id}><TableCell>{formatDateTime(journey.fecha_salida)}</TableCell><TableCell><span className="font-bold">{journey.codigo}</span><span className="block text-xs text-[var(--text-muted)]">{journey.origen_nombre} → {journey.destino_nombre}</span></TableCell><TableCell>{journey.vehiculo_detalle?.patente || journey.vehiculo_detalle?.nombre}</TableCell><TableCell numeric>{formatNumber(journey.metricas?.distancia_km)} km</TableCell><TableCell numeric>{formatNumber(journey.metricas?.carga_t)} t</TableCell><TableCell>{journey.tipo_trayecto.replaceAll("_", " ")} · {journey.estado_carga.replaceAll("_", " ")}</TableCell><TableCell>{journey.distancia_detalle?.evidencia ? <Link className="font-bold text-[var(--brand-primary)]" to={`/obras/${obraId}/evidencias`}>Ver origen</Link> : journey.distancia_detalle?.fuente_detalle?.nombre || "Sin evidencia"}</TableCell></tr>)}</TableBody></TableShell>
    </section>}
  </div>;
}
