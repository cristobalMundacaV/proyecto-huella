import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { FileUp, Search } from "lucide-react";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { Alert, Button, EmptyState, ErrorState, LoadingState, PageHeader, SectionHeader, StatusBadge, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDate } from "@/shared/utils/formatters";
import { listEvidence, listWorkEvidence, uploadEvidence, uploadWorkEvidence } from "../services/dataApi";
import { evidenceStatusInfo, evidenceTypeLabel } from "../utils/dataPresentation";

const evidenceStates = ["pendiente", "validada", "observada", "rechazada", "sin_vinculo", "vinculada"];

export default function EvidencePage({ workScoped = false }) {
  const workspace = useOutletContext() || {};
  const { activeOrganizacionId } = useOrganizacionActiva();
  const workCode = workspace.obra?.codigo_obra;
  const scopeKey = `${activeOrganizacionId || ""}:${workScoped ? workCode || "" : "organization"}`;
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [uploadFeedback, setUploadFeedback] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loadedScope, setLoadedScope] = useState("");
  const requestRef = useRef(0);
  const scopeGenerationRef = useRef(0);
  const fileInputRef = useRef(null);

  const load = useCallback(async () => {
    if (!activeOrganizacionId || (workScoped && !workCode)) return;
    const requestId = ++requestRef.current;
    setLoading(true);
    setLoadError("");
    try {
      const nextRows = await (workScoped ? listWorkEvidence(workCode) : listEvidence(activeOrganizacionId));
      if (requestRef.current !== requestId) return;
      setRows(nextRows);
      setLoadedScope(scopeKey);
    } catch {
      if (requestRef.current === requestId) {
        setLoadError("No fue posible cargar los documentos.");
        setLoadedScope(scopeKey);
      }
    } finally {
      if (requestRef.current === requestId) setLoading(false);
    }
  }, [activeOrganizacionId, scopeKey, workCode, workScoped]);

  useEffect(() => {
    scopeGenerationRef.current += 1;
    setRows([]);
    setQuery("");
    setStatus("");
    setUploadError("");
    setUploadFeedback("");
    setUploading(false);
    load();
    return () => { requestRef.current += 1; };
  }, [load]);

  const visible = useMemo(() => rows.filter((row) => {
    const text = `${row.nombre || ""} ${row.tipo_evidencia || ""} ${row.obra_nombre || ""}`.toLowerCase();
    return (!query || text.includes(query.toLowerCase())) && (!status || row.estado_documental === status);
  }), [query, rows, status]);

  async function onFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const organizationAtStart = activeOrganizacionId;
    const workAtStart = workCode;
    const scopeGeneration = scopeGenerationRef.current;
    const data = new FormData();
    data.append("archivo", file);
    data.append("nombre", file.name);
    data.append("tipo_evidencia", "otro");
    data.append("estado_documental", "pendiente");
    setUploading(true);
    setUploadError("");
    setUploadFeedback("");
    try {
      await (workScoped ? uploadWorkEvidence(workAtStart, data) : uploadEvidence(organizationAtStart, data));
      if (scopeGenerationRef.current !== scopeGeneration) return;
      setUploadFeedback(workScoped
        ? "El documento quedó agregado a esta unidad. Revisa su estado cuando necesites continuar con su seguimiento."
        : "El documento fue agregado. Revisa su estado y contexto antes de usarlo como respaldo operacional.");
      await load();
    } catch {
      if (scopeGenerationRef.current === scopeGeneration) {
        setUploadError("No se pudo agregar el documento. El archivo original no fue reemplazado.");
      }
    } finally {
      if (scopeGenerationRef.current === scopeGeneration) setUploading(false);
    }
  }

  const uploadAction = (
    <label className="inline-flex cursor-pointer items-center gap-2 rounded-[var(--radius-md)] bg-[var(--brand-primary)] px-4 py-2.5 text-sm font-bold text-white transition hover:bg-[var(--brand-hover)] focus-within:shadow-[var(--focus-ring)]">
      <FileUp aria-hidden="true" size={17} />
      {uploading ? "Subiendo…" : "Agregar documento"}
      <input ref={fileInputRef} aria-label="Seleccionar documento" className="hidden" disabled={uploading} type="file" onChange={onFile} />
    </label>
  );

  if (loadedScope !== scopeKey || (loading && !rows.length)) return <LoadingState label="Cargando documentos" />;

  return <main className="space-y-5">
    {workScoped
      ? <SectionHeader title="Evidencias" description="Documentos vinculados a esta unidad y su estado de revisión." action={uploadAction} />
      : <PageHeader title="Evidencias" description="Revisa los documentos que respaldan tu información y su estado." actions={uploadAction} />}

    {uploadFeedback && <Alert tone="success" title="Documento agregado">{uploadFeedback}</Alert>}
    {uploadError && <Alert tone="danger" title="No pudimos agregar el documento">{uploadError}</Alert>}
    {loadError && <ErrorState description={loadError} onRetry={load} />}

    {!!rows.length && <div className="flex flex-wrap gap-3">
      <label className="flex min-w-64 flex-1 items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3">
        <Search aria-hidden="true" size={17} />
        <span className="sr-only">Buscar documentos</span>
        <input className="w-full bg-transparent py-2 text-[var(--text-primary)] outline-none" placeholder="Buscar por documento o contexto" value={query} onChange={(event) => setQuery(event.target.value)} />
      </label>
      <select aria-label="Filtrar documentos por estado" className="rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 text-[var(--text-primary)]" value={status} onChange={(event) => setStatus(event.target.value)}>
        <option value="">Todos los estados</option>
        {evidenceStates.map((value) => <option key={value} value={value}>{evidenceStatusInfo(value).label}</option>)}
      </select>
    </div>}

    {!rows.length && !loadError
      ? <EmptyState
        title={workScoped ? "No hay documentos en esta unidad." : "No hay documentos todavía."}
        description={workScoped ? "Agrega facturas, respaldos u otros archivos que documenten esta unidad." : "Sube facturas, respaldos u otros archivos que documenten tu operación."}
        primaryAction={<Button onClick={() => fileInputRef.current?.click()}>Agregar documento</Button>}
        secondaryAction={!workScoped ? <Link className="px-3 py-2 text-sm font-bold text-[var(--text-secondary)]" to="/datos/importaciones">Importar información</Link> : null}
      />
      : rows.length && !visible.length
        ? <EmptyState title="No encontramos documentos" description="Prueba con otra búsqueda o cambia el estado seleccionado." />
        : !!visible.length && <TableShell>
          <TableHead><tr><TableCell as="th">Documento</TableCell><TableCell as="th">Contexto</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Ingresó</TableCell><TableCell as="th">Acción</TableCell></tr></TableHead>
          <TableBody columns={5}>{visible.map((row) => {
            const rowStatus = evidenceStatusInfo(row.estado_documental);
            return <tr key={row.id}>
              <TableCell><b>{row.nombre || "Documento"}</b><span className="block text-xs text-[var(--text-muted)]">{evidenceTypeLabel(row.tipo_evidencia)}</span></TableCell>
              <TableCell>{row.obra_nombre || row.organizacion_nombre || "Organización"}</TableCell>
              <TableCell><StatusBadge tone={rowStatus.tone}>{rowStatus.label}</StatusBadge></TableCell>
              <TableCell>{formatDate(row.created_at)}</TableCell>
              <TableCell><Link className="font-bold text-[var(--brand-primary)]" to={`/datos/evidencias/${row.id}`}>Ver documento</Link></TableCell>
            </tr>;
          })}</TableBody>
        </TableShell>}
  </main>;
}
