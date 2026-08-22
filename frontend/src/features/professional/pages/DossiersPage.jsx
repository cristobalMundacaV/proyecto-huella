import { useEffect, useRef, useState } from "react";
import { Eye } from "lucide-react";
import { Link } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { EmptyState, ErrorState, PageHeader, Pagination, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";
import { getDossiers } from "../api/professionalV2Api";
import { State } from "../components/GovernanceShared";

export default function DossiersPage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ scopeKey: "", status: "loading", rows: [], error: "" });
  const [page, setPage] = useState(1);
  const requestRef = useRef(0);
  useEffect(() => {
    if (!activeOrganizacionId) return undefined;
    const scopeKey = String(activeOrganizacionId); const requestId = ++requestRef.current;
    setState({ scopeKey, status: "loading", rows: [], error: "" });
    getDossiers(activeOrganizacionId).then((rows) => { if (requestRef.current === requestId) setState({ scopeKey, status: "ready", rows, error: "" }); }).catch(() => { if (requestRef.current === requestId) setState({ scopeKey, status: "error", rows: [], error: "No se pudieron cargar los expedientes." }); });
    return () => { requestRef.current += 1; };
  }, [activeOrganizacionId]);
  useEffect(() => { setPage(1); }, [activeOrganizacionId, state.rows]);
  const requestedScopeKey = activeOrganizacionId ? String(activeOrganizacionId) : "";
  if (state.scopeKey !== requestedScopeKey || state.status === "loading") return <PlatformLoader title="Cargando expedientes" description="Estamos preparando los antecedentes formales disponibles." />;
  const rows = state.rows.slice((page - 1) * 8, page * 8);
  return <main className="space-y-6"><PageHeader eyebrow="Gobernanza" title="Expedientes" description="Revisa qué antecedentes formales están preparados y en qué estado se encuentran." />
    {state.status === "error" ? <ErrorState description={state.error} /> : !state.rows.length ? <EmptyState title="Sin expedientes" description="Los expedientes aparecen cuando existe un problema con antecedentes formales reunidos." /> : <>
      <TableShell><TableHead><tr><TableCell as="th">Expediente</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Revisión profesional</TableCell><TableCell as="th">Informe vigente</TableCell><TableCell as="th">Fecha</TableCell><TableCell as="th">Acción</TableCell></tr></TableHead><TableBody columns={6}>{rows.map((item) => <tr key={item.id}><TableCell><b>{item.problematica_titulo || `Expediente #${item.id}`}</b><span className="block text-xs text-[var(--text-muted)]">Expediente #{item.id} · Versión {item.version}</span></TableCell><TableCell><State value={item.estado} /></TableCell><TableCell>{item.ultima_revision ? <><State value={item.ultima_revision.estado} /><span className="block text-xs text-[var(--text-muted)]">{item.ultima_revision.profesional || "Profesional no informado"}</span></> : "Sin revisión registrada"}</TableCell><TableCell>{item.informe_vigente ? <><State value={item.informe_vigente.estado} /><span className="block text-xs text-[var(--text-muted)]">Versión {item.informe_vigente.version}</span></> : "Sin informe"}</TableCell><TableCell align="center">{formatDateTime(item.created_at)}</TableCell><TableCell align="center"><Link to={`/gobernanza/expedientes/${item.id}`} aria-label={`Abrir expediente ${item.id}`} title="Abrir expediente" className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-cyan-200 bg-cyan-50 text-cyan-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-700"><Eye aria-hidden="true" size={18} /></Link></TableCell></tr>)}</TableBody></TableShell>
      <Pagination page={page} totalItems={state.rows.length} pageSize={8} onChange={setPage} itemLabel="expedientes" />
    </>}
  </main>;
}
