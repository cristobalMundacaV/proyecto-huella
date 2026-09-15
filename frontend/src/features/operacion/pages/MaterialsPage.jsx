import { Link, useOutletContext, useParams } from "react-router-dom";
import { ClipboardCheck, Plus } from "lucide-react";
import {
  Alert,
  Button,
  ButtonLink,
  EmptyState,
  ErrorState,
  Pagination,
  SectionHeader,
  TableBody,
  TableCell,
  TableHead,
  TableShell,
} from "@/shared/ui";
import { formatDateTime, formatNumber } from "@/shared/utils/formatters";
import OperationDomainShell from "../components/OperationDomainShell";
import { applicability, explicitDomainActivities, isResourceReady, resourceData } from "../utils/operationSelectors";
import { useEffect, useMemo, useState } from "react";
import MaterialEventModal from "../components/MaterialEventModal";
import MaterialReceptionLinkModal from "../components/MaterialReceptionLinkModal";
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

export default function MaterialsPage() {
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
  const [linkEvent, setLinkEvent] = useState(null);

  const persistedWorkId =
    obra?.id ||
    obra?.obra_id;
  const applicabilityState = applicability(context, "materiales");
  const balancesReady = isResourceReady(operation.materials);
  const eventsReady = isResourceReady(operation.materialEvents);
  const events = resourceData(operation.materialEvents, []);
  const materialActivities = useMemo(
    () => explicitDomainActivities(
      events.map((event) => event.actividad_detalle),
      "materiales",
    ),
    [events],
  );
  const materialNames = new Map(events.filter((event) => event.material).map((event) => [String(event.material), event.material_nombre]));
  const materialBalances = resourceData(operation.materials, []);
  const signals = materialBalances.flatMap((material) => material.senales || []);
  const balanceRows = materialBalances.flatMap((material) => (material.balances || [])
    .filter((balance) => balance.unidad)
    .map((balance) => ({
      ...balance,
      materialId: material.material_id,
      materialName: materialNames.get(String(material.material_id)) || "Material",
    })));
  const noApplicable = applicabilityState === "no_aplica";
  const unresolved = ["pendiente", "no_determinado"].includes(applicabilityState);
  const applicabilityBadge = noApplicable ? "No aplica" : unresolved ? "Aplicabilidad por definir" : "Aplica";
  useEffect(() => { setPage(1); }, [events.length, persistedWorkId]);
  const pagedEvents = useMemo(() => events.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), [events, page]);
  const trendRows = useMemo(() => {
    const rows = events.filter((event) => event.cantidad_detalle?.valor_numerico !== null && event.cantidad_detalle?.valor_numerico !== undefined && Number.isFinite(Number(event.cantidad_detalle.valor_numerico)))
      .map((event) => ({ label: formatDateTime(event.fecha_hora), value: Number(event.cantidad_detalle.valor_numerico), unit: event.cantidad_detalle.unidad, timestamp: event.fecha_hora }));
    const unit = rows.at(-1)?.unit;
    return rows.filter((row) => row.unit === unit).toSorted((a, b) => String(a.timestamp).localeCompare(String(b.timestamp))).slice(-12);
  }, [events]);

  return (
    <OperationDomainShell
      domainKey="materiales"
      title="Materiales"
      description="¿Qué materiales están entrando, usándose o saliendo?"
      badges={[applicabilityBadge, eventsReady ? (events.length ? `${events.length} ${events.length === 1 ? "movimiento" : "movimientos"}` : "Sin movimientos") : "Movimientos no disponibles", noApplicable ? "Flujo deshabilitado" : unresolved ? "Requiere definición" : "Flujo habilitado"]}
      primaryAction={!noApplicable && (unresolved ? <ButtonLink leftIcon={ClipboardCheck} to={`/obras/${obraId}/diagnostico`}>Revisar perfil ambiental</ButtonLink> : <Button leftIcon={Plus} onClick={() => setRecordOpen(true)}>Registrar movimiento</Button>)}
      secondaryAction={!noApplicable && <ButtonLink leftIcon={Plus} variant="secondary" to={`/obras/${obraId}/evidencias`}>{unresolved ? "Agregar evidencia" : "Agregar documento"}</ButtonLink>}
    >
      {section === "resumen" && noApplicable && <EmptyState title="No aplica a esta obra" description="Materiales está marcado como no aplicable; la ausencia de movimientos no se interpreta como cero." />}
      {section === "resumen" && unresolved && <EmptyState title="Aplicabilidad por definir" description="Aún no existe información suficiente para determinar si materiales aplica a esta obra." />}
      {section === "resumen" && !noApplicable && !unresolved && eventsReady && !events.length && <EmptyState title="Sin información registrada" description="Aún no hay movimientos de materiales registrados para esta obra." />}
      {section === "resumen" && eventsReady && <FlowQuickRead
        base={`/obras/${obraId}/operacion/materiales`}
        records={eventsReady ? events.length : null}
        latest={events.length ? formatDateTime(events.at(-1)?.fecha_hora) : null}
        quality={signals.length ? `${signals.length} señales para revisar` : "Sin señales del balance disponibles"}
        evidence={`${events.filter((event) => event.evidencia).length} movimientos con evidencia`}
        noData={!events.length}
      />}
      {section === "tendencias" && noApplicable && <EmptyState title="No aplica a esta obra" description="Materiales está marcado como no aplicable; la ausencia de movimientos no se interpreta como cero." />}
      {section === "tendencias" && unresolved && <EmptyState title="Aplicabilidad por definir" description="Aún no existe información suficiente para determinar si materiales aplica a esta obra." />}
      {section === "tendencias" && !noApplicable && !unresolved && (trendRows.length ? <section className="rounded-[22px] border border-slate-200 bg-white p-5 shadow-sm">
        <SectionHeader title="Tendencia de movimientos" description="Últimos valores registrados en una misma unidad; no se suman materiales diferentes." />
        <EnvironmentalTrendChart data={trendRows} color={getFlowChartColor("materiales")} valueFormatter={(value) => `${formatNumber(value)} ${trendRows[0]?.unit || ""}`.trim()} />
      </section> : <EmptyState title="Sin tendencia disponible" description="No hay mediciones numéricas compatibles para representar una serie." />)}
      {!noApplicable && !unresolved && !balancesReady && <ErrorState title="No fue posible cargar los balances de materiales" description="Los eventos continúan disponibles si pudieron cargarse." />}

      {!noApplicable && !unresolved && balancesReady && signals.length > 0 && <Alert tone="warning" title="Requiere revisión">
        <p>{signals.length} {signals.length === 1 ? "señal del balance requiere" : "señales del balance requieren"} revisión.</p>
        <details className="mt-2">
          <summary className="cursor-pointer font-bold">Ver detalles</summary>
          <ul className="mt-2 list-disc space-y-1 pl-5">{signals.slice(0, 10).map((signal, index) => <li key={`${signal.tipo}-${index}`}>{humanize(signal.tipo)}</li>)}</ul>
        </details>
      </Alert>}

      {section === "calidad" && noApplicable && <EmptyState title="No aplica a esta obra" description="Materiales está marcado como no aplicable; la ausencia de movimientos no se interpreta como cero." />}
      {section === "calidad" && unresolved && <EmptyState title="Aplicabilidad por definir" description="Aún no existe información suficiente para determinar si materiales aplica a esta obra." />}
      {section === "calidad" && !noApplicable && !unresolved && balancesReady && balanceRows.length > 0 && <section>
        <SectionHeader
          eyebrow="BALANCE OPERACIONAL"
          title="Balances disponibles"
          description="Cada material conserva su propia unidad; no se suman materiales distintos para crear un total artificial."
        />
        <TableShell>
          <TableHead><tr>
            <TableCell as="th">Material</TableCell>
            <TableCell as="th">Unidad</TableCell>
            <TableCell as="th" numeric>Ingresado</TableCell>
            <TableCell as="th" numeric>Usado</TableCell>
            <TableCell as="th" numeric>Reutilizado</TableCell>
            <TableCell as="th" numeric>Saldo</TableCell>
          </tr></TableHead>
          <TableBody columns={6}>{balanceRows.map((balance, index) => <tr key={`${balance.materialId}-${balance.unidad}-${index}`}>
            <TableCell><span className="font-bold">{balance.materialName}</span><span className="block text-xs text-[var(--text-muted)]">Balance {humanize(balance.calidad_balance)}</span></TableCell>
            <TableCell>{balance.unidad}</TableCell>
            <TableCell numeric>{formatNumber(balance.ingresos_periodo)}</TableCell>
            <TableCell numeric>{formatNumber(balance.cantidad_utilizada)}</TableCell>
            <TableCell numeric>{formatNumber(balance.cantidad_reutilizada)}</TableCell>
            <TableCell numeric>{formatNumber(balance.stock_restante)}</TableCell>
          </tr>)}</TableBody>
        </TableShell>
      </section>}

      {section === "registros" && (noApplicable
        ? <EmptyState title="No aplica a esta unidad" description="Materiales está marcado como no aplicable. La ausencia de movimientos no se presenta como cero." />
        : unresolved
          ? <EmptyState title="Aplicabilidad por definir" description="Aún no existe información suficiente para determinar si materiales aplica a esta obra." />
        : !eventsReady
        ? <ErrorState title="No fue posible cargar los eventos de materiales" description="Los balances continúan disponibles si pudieron calcularse." />
        : !events.length
          ? <EmptyState
                title="Sin información registrada"
                description="Aún no hay entradas, usos o salidas de materiales registradas para esta unidad. Comienza registrando un movimiento o adjuntando documentación de respaldo."
              />
          : <section>
            <SectionHeader
              eyebrow="ACTIVIDAD REGISTRADA"
              title="Movimientos de materiales"
              description="Material, movimiento, cantidad y origen del dato sin exponer identificadores técnicos como información principal."
              count={events.length}
            />
            <TableShell>
              <TableHead><tr>
                <TableCell as="th">Fecha</TableCell>
                <TableCell as="th">Material</TableCell>
                <TableCell as="th">Movimiento</TableCell>
                <TableCell as="th">Cantidad</TableCell>
                <TableCell as="th">Lote</TableCell>
                <TableCell as="th">Origen del dato</TableCell>
                <TableCell as="th">Trazabilidad</TableCell>
              </tr></TableHead>
              <TableBody columns={7}>{pagedEvents.map((event) => {
                const source = event.cantidad_detalle?.fuente_detalle?.nombre;
                const sensorId = event.cantidad_detalle?.sensor_detalle?.id;
                return <tr key={event.id}>
                  <TableCell>{formatDateTime(event.fecha_hora)}</TableCell>
                  <TableCell className="font-bold">{event.material_nombre || "Material sin nombre"}</TableCell>
                  <TableCell>
                    <span className="font-medium">{humanize(event.tipo)}</span>
                    {(event.origen || event.destino) && <span className="block text-xs text-[var(--text-muted)]">{event.origen || "Origen sin informar"} → {event.destino || "Destino sin informar"}</span>}
                  </TableCell>
                  <TableCell>{measurement(event.cantidad_detalle?.valor_numerico, event.cantidad_detalle?.unidad)}</TableCell>
                  <TableCell>{event.lote_codigo || "Sin lote"}</TableCell>
                  <TableCell>{event.evidencia
                    ? <Link className="font-bold text-[var(--brand-primary)]" to={`/datos/evidencias/${event.evidencia}`}>Ver documento</Link>
                    : sensorId
                      ? <Link className="font-bold text-[var(--brand-primary)]" to={`/operacion/sensores/${sensorId}`}>Sensor</Link>
                      : source || "Sin origen identificable"}</TableCell>
                  <TableCell>{["uso", "consumo"].includes(event.tipo)
                    ? event.evento_origen
                      ? <span className="font-medium">Recepción vinculada</span>
                      : <Button type="button" variant="ghost" onClick={() => setLinkEvent(event)}>Vincular recepción</Button>
                    : "No aplica"}</TableCell>
                </tr>;
              })}</TableBody>
            </TableShell>
            <Pagination page={page} totalItems={events.length} pageSize={PAGE_SIZE} onChange={setPage} itemLabel="movimientos" />
          </section>)}
      {section === "sensores" && noApplicable && <EmptyState title="No aplica a esta obra" description="Materiales está marcado como no aplicable; la ausencia de movimientos no se interpreta como cero." />}
      {section === "sensores" && unresolved && <EmptyState title="Aplicabilidad por definir" description="Aún no existe información suficiente para determinar si materiales aplica a esta obra." />}
      {section === "sensores" && !noApplicable && !unresolved && <DomainSensorsPanel
        domain="materiales"
        operation={operation}
        organizationId={
          context?.references?.organization
        }
        workId={persistedWorkId}
        onCreated={
          reloadOperation
        }
      />}
      {section === "calidad" && !noApplicable && !unresolved && <>
      <DomainQualityPanel
        domain="materiales"
        organizationId={
          context?.references?.organization
        }
        workId={
          persistedWorkId
        }
      />
      <DomainCalculationPanel
        domain="materiales"
        operation={operation}
        activities={materialActivities}
        organizationId={
          context?.references?.organization
        }
        onCalculated={
          reloadOperation
        }
      />
      </>}
      <MaterialEventModal
        open={recordOpen}
        onClose={() =>
          setRecordOpen(false)
        }
        organizationId={
          context?.references?.organization
        }
        workId={persistedWorkId}
        events={events}
        onCreated={reloadOperation}
      />
      <MaterialReceptionLinkModal open={Boolean(linkEvent)} onClose={() => setLinkEvent(null)} organizationId={context?.references?.organization} workId={persistedWorkId} event={linkEvent} events={events} onLinked={reloadOperation} />
    </OperationDomainShell>
  );
}
