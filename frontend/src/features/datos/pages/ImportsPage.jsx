import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { EmptyState, ErrorState, LoadingState, PageHeader, SectionHeader, StatusBadge, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";
import ImportWorkflow from "../components/ImportWorkflow";
import { listImports } from "../services/dataApi";
import { destinationLabel, importDisplayName, importResultLabel, importStatusInfo } from "../utils/dataPresentation";

export default function ImportsPage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const scope = String(activeOrganizacionId || "");
  const [state, setState] = useState({ scope: null, loading: true, rows: [], error: "" });
  const requestRef = useRef(0);

  const load = useCallback(async () => {
    if (!activeOrganizacionId) return;
    const requestId = ++requestRef.current;
    const organizationAtStart = String(activeOrganizacionId);
    setState((current) => ({ ...current, scope: organizationAtStart, loading: true, error: "" }));
    try {
      const rows = await listImports(activeOrganizacionId);
      if (requestRef.current === requestId) setState({ scope: organizationAtStart, loading: false, rows, error: "" });
    } catch {
      if (requestRef.current === requestId) setState((current) => ({ ...current, scope: organizationAtStart, loading: false, error: "No fue posible cargar el historial. Puedes iniciar una nueva importación igualmente." }));
    }
  }, [activeOrganizacionId]);

  useEffect(() => {
    setState({ scope, loading: true, rows: [], error: "" });
    load();
    return () => { requestRef.current += 1; };
  }, [load, scope]);

  if (state.scope !== scope) return <LoadingState label="Preparando importaciones" />;

  return <main className="space-y-7">
    <PageHeader title="Importaciones" description="Carga información nueva o revisa una carga anterior." />

    <ImportWorkflow key={activeOrganizacionId} organizationId={activeOrganizacionId} onCompleted={load} />

    <section>
      <SectionHeader title="Historial" description="Cargas anteriores, su estado y el resultado disponible." />
      {state.loading ? <LoadingState label="Cargando historial" /> : state.error ? <ErrorState description={state.error} onRetry={load} /> : !state.rows.length ? <EmptyState title="No hay importaciones anteriores." description="La nueva carga está disponible arriba cuando quieras comenzar." /> : <TableShell>
        <TableHead><tr><TableCell as="th">Archivo / fuente</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Resultado</TableCell><TableCell as="th">Fecha</TableCell><TableCell as="th">Acción</TableCell></tr></TableHead>
        <TableBody columns={5}>{state.rows.map((row) => {
          const status = importStatusInfo(row.estado);
          return <tr key={row.id}>
            <TableCell><b>{importDisplayName(row)}</b><span className="block text-xs text-[var(--text-muted)]">{destinationLabel(row.destino_operacional)}</span></TableCell>
            <TableCell><StatusBadge tone={status.tone}>{status.label}</StatusBadge></TableCell>
            <TableCell>{importResultLabel(row)}</TableCell>
            <TableCell>{formatDateTime(row.created_at)}</TableCell>
            <TableCell><Link className="font-bold text-[var(--brand-primary)]" to={`/datos/importaciones/${row.id}`}>Ver</Link></TableCell>
          </tr>;
        })}</TableBody>
      </TableShell>}
    </section>
  </main>;
}
