import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { ErrorState, LoadingState, PageHeader, StatusBadge, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";
import ImportWorkflow from "../components/ImportWorkflow";
import { listImports } from "../services/dataApi";

export default function ImportsPage() {
  const { activeOrganizacionId } = useOrganizacionActiva(); const [state, setState] = useState({ loading: true, rows: [], error: "" });
  const load = useCallback(() => { setState((current) => ({ ...current, loading: true, error: "" })); listImports(activeOrganizacionId).then((rows) => setState({ loading: false, rows, error: "" })).catch(() => setState((current) => ({ ...current, loading: false, error: "No fue posible cargar el historial. Puedes iniciar una nueva importación igualmente." }))); }, [activeOrganizacionId]);
  useEffect(() => { load(); }, [load]);
  return <main className="space-y-6"><PageHeader eyebrow="Datos · Importaciones" title="Importaciones" description="Inicia un proceso o revisa el historial sin perder el archivo, el mapping ni sus excepciones." /><ImportWorkflow organizationId={activeOrganizacionId} />
    <section><h2 className="mb-3 text-xl font-bold">Historial de procesos</h2>{state.loading ? <LoadingState label="Cargando historial" /> : state.error ? <ErrorState description={state.error} onRetry={load} /> : <TableShell><TableHead><tr><TableCell as="th">Archivo o fuente</TableCell><TableCell as="th">Canal</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Registros</TableCell><TableCell as="th">Fecha</TableCell><TableCell as="th">Acción</TableCell></tr></TableHead><TableBody columns={6} empty={!state.rows.length}>{state.rows.map((row) => <tr key={row.id}><TableCell><b>{row.version_evidencia_detalle?.nombre_original || row.fuente_nombre || "Importación"}</b><span className="block text-xs text-[var(--text-muted)]">{row.destino_operacional?.replaceAll("_", " ")}</span></TableCell><TableCell>{row.tipo_ingesta}</TableCell><TableCell><StatusBadge label={row.estado?.replaceAll("_", " ")} /></TableCell><TableCell>{row.filas_procesadas ?? 0} procesados · {row.filas_con_error ?? 0} errores</TableCell><TableCell>{formatDateTime(row.created_at)}</TableCell><TableCell><Link className="font-bold text-[var(--brand-primary)]" to={`/datos/importaciones/${row.id}`}>Ver detalle</Link></TableCell></tr>)}</TableBody></TableShell>}</section>
  </main>;
}
