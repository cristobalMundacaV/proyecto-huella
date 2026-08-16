import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { FileUp, Search } from "lucide-react";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { Button, EmptyState, ErrorState, LoadingState, PageHeader, SectionHeader, StatusBadge, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDate } from "@/shared/utils/formatters";
import { listEvidence, listWorkEvidence, uploadEvidence, uploadWorkEvidence } from "../services/dataApi";

export default function EvidencePage({ workScoped = false }) {
  const workspace = useOutletContext() || {};
  const { activeOrganizacionId } = useOrganizacionActiva();
  const workCode = workspace.obra?.codigo_obra;
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [uploading, setUploading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setRows(await (workScoped ? listWorkEvidence(workCode) : listEvidence(activeOrganizacionId)));
    } catch {
      setError("No fue posible cargar las evidencias.");
    } finally {
      setLoading(false);
    }
  }, [activeOrganizacionId, workCode, workScoped]);

  useEffect(() => { load(); }, [load]);

  const visible = useMemo(() => rows.filter((row) => (
    (!query || `${row.nombre} ${row.tipo_evidencia} ${row.obra_nombre || ""}`.toLowerCase().includes(query.toLowerCase()))
    && (!status || row.estado_documental === status)
  )), [query, rows, status]);

  async function onFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const data = new FormData();
    data.append("archivo", file);
    data.append("nombre", file.name);
    data.append("tipo_evidencia", "otro");
    data.append("estado_documental", "pendiente");
    setUploading(true);
    setError("");
    try {
      await (workScoped ? uploadWorkEvidence(workCode, data) : uploadEvidence(activeOrganizacionId, data));
      await load();
    } catch {
      setError("No se pudo agregar la evidencia. El archivo original no fue reemplazado.");
    } finally {
      setUploading(false);
    }
  }

  if (loading) return <LoadingState label="Cargando evidencias" />;

  const uploadAction = (
    <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-[var(--brand-primary)] px-4 py-2 text-sm font-bold text-white focus-within:shadow-[var(--focus-ring)]">
      <FileUp aria-hidden="true" size={17} />
      {uploading ? "Subiendo…" : "Agregar evidencia"}
      <input aria-label="Seleccionar archivo de evidencia" className="hidden" disabled={uploading} type="file" onChange={onFile} />
    </label>
  );

  return <main className="space-y-5">
    {workScoped
      ? <SectionHeader title="Evidencias" description="Revisa el respaldo documental vinculado a esta unidad." action={uploadAction} />
      : <PageHeader eyebrow="Datos · Evidencias" title="Evidencias" description="Encuentra el respaldo documental, su contexto y su estado. El archivo original siempre se conserva." actions={uploadAction} />}
    {error && <ErrorState description={error} onRetry={load} />}
    <div className="flex flex-wrap gap-3">
      <label className="flex min-w-64 flex-1 items-center gap-2 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-3">
        <Search aria-hidden="true" size={17} />
        <span className="sr-only">Buscar evidencia</span>
        <input className="w-full bg-transparent py-2 text-[var(--text-primary)] outline-none" placeholder="Buscar por nombre, tipo u obra" value={query} onChange={(event) => setQuery(event.target.value)} />
      </label>
      <select aria-label="Filtrar por estado" className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 text-[var(--text-primary)]" value={status} onChange={(event) => setStatus(event.target.value)}>
        <option value="">Todos los estados</option>
        {["pendiente", "validada", "observada", "rechazada", "sin_vinculo", "vinculada"].map((value) => <option key={value}>{value}</option>)}
      </select>
    </div>
    {!visible.length
      ? <EmptyState title={workScoped ? "Aún no hay respaldo documental vinculado a esta unidad." : "No hay evidencias registradas."} description="Agrega el archivo original para comenzar a construir trazabilidad." primaryAction={<Button onClick={() => document.querySelector('input[type="file"]')?.click()}>Agregar evidencia</Button>} secondaryAction={<Link className="px-3 py-2 text-sm font-bold" to="/datos/importaciones">Importar datos</Link>} />
      : <TableShell>
        <TableHead><tr><TableCell as="th">Evidencia</TableCell><TableCell as="th">Contexto</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Fecha</TableCell><TableCell as="th">Acción</TableCell></tr></TableHead>
        <TableBody columns={5}>{visible.map((row) => <tr key={row.id}><TableCell><b>{row.nombre}</b><span className="block text-xs text-[var(--text-muted)]">{row.tipo_evidencia?.replaceAll("_", " ")}</span></TableCell><TableCell>{row.obra_nombre || "Organización"}</TableCell><TableCell><StatusBadge label={row.estado_documental?.replaceAll("_", " ")} /></TableCell><TableCell>{formatDate(row.fecha_documento || row.created_at)}</TableCell><TableCell><Link className="font-bold text-[var(--brand-primary)]" to={`/datos/evidencias/${row.id}`}>Ver detalle</Link></TableCell></tr>)}</TableBody>
      </TableShell>}
  </main>;
}
