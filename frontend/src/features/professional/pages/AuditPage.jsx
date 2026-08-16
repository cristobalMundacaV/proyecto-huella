import { useEffect, useRef, useState } from "react";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { getEnvironmentalAudit } from "../api/professionalV2Api";
import { EmptyState, ErrorState, LoadingState, PageHeader, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";
import { auditEntityLabel, human } from "../components/GovernanceShared";

export default function AuditPage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ scopeKey: "", status: "loading", rows: [], error: "" });
  const requestRef = useRef(0);

  useEffect(() => {
    if (!activeOrganizacionId) return undefined;
    const scopeKey = String(activeOrganizacionId);
    const requestId = ++requestRef.current;
    setState({ scopeKey, status: "loading", rows: [], error: "" });
    getEnvironmentalAudit(activeOrganizacionId)
      .then((rows) => {
        if (requestRef.current === requestId) setState({ scopeKey, status: "ready", rows, error: "" });
      })
      .catch(() => {
        if (requestRef.current === requestId) setState({ scopeKey, status: "error", rows: [], error: "No se pudo cargar la auditoría ambiental." });
      });
    return () => { requestRef.current += 1; };
  }, [activeOrganizacionId]);

  const requestedScopeKey = activeOrganizacionId ? String(activeOrganizacionId) : "";
  if (state.scopeKey !== requestedScopeKey || state.status === "loading") return <LoadingState label="Cargando auditoría" />;

  return <main className="space-y-6">
    <PageHeader
      eyebrow="Gobernanza"
      title="Auditoría"
      description="Revisa qué decisiones o cambios gobernados quedaron registrados."
    />
    {state.status === "error" ? <ErrorState description={state.error} /> : !state.rows.length ? (
      <EmptyState title="Sin eventos de auditoría" description="No hay decisiones o cambios gobernados registrados todavía." />
    ) : <TableShell>
      <TableHead><tr><TableCell as="th">Fecha</TableCell><TableCell as="th">Actor</TableCell><TableCell as="th">Acción</TableCell><TableCell as="th">Elemento</TableCell><TableCell as="th">Resultado / contexto</TableCell></tr></TableHead>
      <TableBody columns={5}>{state.rows.map((event) => <tr key={event.id}>
        <TableCell>{formatDateTime(event.timestamp)}</TableCell>
        <TableCell>{event.actor_nombre || "Sistema"}</TableCell>
        <TableCell>{human(event.tipo)}</TableCell>
        <TableCell>{auditEntityLabel(event.entidad)}{event.referencia ? <span className="block text-xs text-[var(--text-muted)]">Referencia {event.referencia}</span> : null}</TableCell>
        <TableCell>{event.resumen || "Sin contexto adicional"}</TableCell>
      </tr>)}</TableBody>
    </TableShell>}
  </main>;
}
