import { Link, useOutletContext, useParams } from "react-router-dom";
import { Alert, DataQualityBadge, EmptyState, KpiCard, SectionHeader, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime, formatNumber } from "@/shared/utils/formatters";
import DomainApplicability from "../components/DomainApplicability";

export default function MaterialsPage() {
  const { obraId } = useParams();
  const { context, operation } = useOutletContext();
  const events = operation.materialEvents || [];
  const balances = (operation.materials || []).flatMap((material) => (material.balances || []).map((balance) => ({ ...balance, materialId: material.material_id, signals: material.senales || [] })));
  const signals = balances.flatMap((balance) => balance.signals);
  const summary = [
    ["Ingresado", "ingresos_periodo"], ["Consumido o usado", "cantidad_utilizada"],
    ["Reutilizado", "cantidad_reutilizada"], ["Residuo", "cantidad_residuo"], ["Saldo", "stock_restante"],
  ].map(([label, key]) => {
    const compatible = balances.filter((item) => item.unidad && item[key] !== null && item[key] !== undefined);
    const units = new Set(compatible.map((item) => item.unidad));
    return units.size === 1 ? { label, value: compatible.reduce((sum, item) => sum + Number(item[key]), 0), unit: compatible[0].unidad } : { label, value: null, unit: undefined };
  });
  return <div className="space-y-6">
    <SectionHeader title="Materiales" description="Balance determinístico y eventos trazables dentro de esta obra." />
    <DomainApplicability context={context} capability="materiales" />
    {signals.length > 0 && <Alert tone="warning" title="Datos por revisar">{signals.length} señales del balance requieren revisión. No se utilizó cantidad inicial como autoridad.</Alert>}
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">{summary.map((item) => <KpiCard key={item.label} label={item.label} value={item.value} unit={item.unit} helper={item.value === null ? "No calculable en una unidad única" : undefined} />)}</section>
    {!events.length ? <EmptyState title="No hay eventos de materiales para esta obra" description="La carga documental permitirá reconstruir recepción, uso, devolución, reutilización y residuo." primaryAction={<Link className="font-bold text-[var(--brand-primary)]" to="/datos/evidencias">Agregar evidencia</Link>} /> : <section><SectionHeader title="Lineage de materiales" description="Evento y referencia de origen, sin construir un grafo artificial." count={events.length} />
      <TableShell><TableHead><tr><TableCell as="th">Fecha</TableCell><TableCell as="th">Material</TableCell><TableCell as="th">Evento</TableCell><TableCell as="th">Lote</TableCell><TableCell as="th">Cantidad</TableCell><TableCell as="th">Origen → destino</TableCell><TableCell as="th">Calidad/origen</TableCell></tr></TableHead><TableBody columns={7}>{events.map((event) => <tr key={event.id}><TableCell>{formatDateTime(event.fecha_hora)}</TableCell><TableCell className="font-bold">{event.material_nombre}</TableCell><TableCell>{event.tipo.replaceAll("_", " ")}{event.evento_origen && <span className="block text-xs text-[var(--text-muted)]">Origen: evento {event.evento_origen}</span>}</TableCell><TableCell>{event.lote_codigo || "Sin lote"}</TableCell><TableCell>{formatNumber(event.cantidad_detalle?.valor_numerico)} {event.cantidad_detalle?.unidad}</TableCell><TableCell>{event.origen || "—"} → {event.destino || "—"}</TableCell><TableCell>{event.cantidad_detalle?.estado ? <DataQualityBadge label={event.cantidad_detalle.estado} tone={event.cantidad_detalle.estado === "validada" ? "success" : "warning"} /> : "Sin cantidad"}{event.evidencia && <Link className="mt-1 block text-xs font-bold text-[var(--brand-primary)]" to={`/obras/${obraId}/evidencias`}>Ver origen</Link>}</TableCell></tr>)}</TableBody></TableShell>
    </section>}
  </div>;
}
