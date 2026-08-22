import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, CheckCircle2, FileText, UploadCloud } from "lucide-react";
import { Link } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { Alert, Card, CardContent, ErrorState, PageHeader, SectionHeader, StatusBadge } from "@/shared/ui";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { formatDateTime } from "@/shared/utils/formatters";
import { listEvidence, listImports } from "../services/dataApi";
import {
  evidenceNeedsAttention,
  evidenceStatusInfo,
  importAttentionReason,
  importDisplayName,
  importNeedsAttention,
  importResultLabel,
  importStatusInfo,
} from "../utils/dataPresentation";

const initialResource = { status: "loading", rows: [] };

export default function DataOverviewPage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ scope: null, evidence: initialResource, imports: initialResource });
  const requestRef = useRef(0);

  const load = useCallback(async () => {
    if (!activeOrganizacionId) return;
    const requestId = ++requestRef.current;
    const scope = String(activeOrganizacionId);
    setState({ scope, evidence: initialResource, imports: initialResource });
    const [evidence, imports] = await Promise.allSettled([
      listEvidence(activeOrganizacionId),
      listImports(activeOrganizacionId),
    ]);
    if (requestRef.current !== requestId) return;
    setState({
      scope,
      evidence: evidence.status === "fulfilled" ? { status: "ready", rows: evidence.value } : { status: "error", rows: [] },
      imports: imports.status === "fulfilled" ? { status: "ready", rows: imports.value } : { status: "error", rows: [] },
    });
  }, [activeOrganizacionId]);

  useEffect(() => {
    load();
    return () => { requestRef.current += 1; };
  }, [load]);

  const priorities = useMemo(() => {
    const importItems = state.imports.status === "ready"
      ? state.imports.rows.filter(importNeedsAttention).map((item) => ({
        key: `import-${item.id}`,
        title: importDisplayName(item),
        reason: importAttentionReason(item),
        status: importStatusInfo(item.estado),
        path: `/datos/importaciones/${item.id}`,
        action: "Revisar carga",
      }))
      : [];
    const evidenceItems = state.evidence.status === "ready"
      ? state.evidence.rows.filter(evidenceNeedsAttention).map((item) => ({
        key: `evidence-${item.id}`,
        title: item.nombre || "Documento",
        reason: item.estado_documental === "observada" ? "El documento tiene observaciones pendientes." : "El documento está pendiente de revisión.",
        status: evidenceStatusInfo(item.estado_documental),
        path: `/datos/evidencias/${item.id}`,
        action: "Revisar documento",
      }))
      : [];
    return [...importItems, ...evidenceItems].slice(0, 5);
  }, [state.evidence, state.imports]);

  const loading = state.scope !== String(activeOrganizacionId) || state.evidence.status === "loading" || state.imports.status === "loading";
  const partialError = state.evidence.status === "error" || state.imports.status === "error";
  if (loading) return <PlatformLoader title="Revisando tus datos" description="Estamos reuniendo importaciones, evidencias y señales de calidad." />;

  const recentEvidence = state.evidence.status === "ready" ? state.evidence.rows.slice(0, 3) : [];
  const recentImports = state.imports.status === "ready" ? state.imports.rows.slice(0, 3) : [];

  return <main className="space-y-7">
    <PageHeader
      title="Datos"
      description="Revisa tus documentos y los procesos que necesitan atención."
      actions={<>
        <Link className="inline-flex items-center rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm font-bold text-[var(--text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to="/datos/evidencias">Ver documentos</Link>
        <Link className="inline-flex items-center rounded-[var(--radius-md)] bg-[var(--brand-primary)] px-3 py-2 text-sm font-bold text-white focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to="/datos/importaciones">Importar información</Link>
      </>}
    />

    <section>
      <SectionHeader title="Requiere atención" description={priorities.length ? "Pendientes que necesitan una acción antes de continuar." : "No hay pendientes detectados en la información disponible."} />
      {priorities.length ? <Card><CardContent className="divide-y divide-[var(--border-subtle)] p-0">
        {priorities.map((item) => <div key={item.key} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2"><h3 className="font-bold text-[var(--text-primary)]">{item.title}</h3><StatusBadge tone={item.status.tone}>{item.status.label}</StatusBadge></div>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">{item.reason}</p>
          </div>
          <Link className="inline-flex shrink-0 items-center gap-2 text-sm font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to={item.path}>{item.action}<ArrowRight aria-hidden="true" size={16} /></Link>
        </div>)}
      </CardContent></Card> : partialError ? <Alert tone="info" title="Revisión parcial">No hay pendientes detectados con la información disponible, pero una fuente no pudo consultarse.</Alert> : <Card><CardContent className="flex items-center gap-3"><CheckCircle2 aria-hidden="true" className="text-[var(--status-success)]" size={20} /><p className="text-sm text-[var(--text-secondary)]">No hay documentos ni cargas que requieran una acción ahora.</p></CardContent></Card>}
    </section>

    <section>
      <SectionHeader title="Evidencias" description="Documentos que respaldan tu información." action={<Link className="text-sm font-bold text-[var(--brand-primary)]" to="/datos/evidencias">Ver evidencias</Link>} />
      {state.evidence.status === "error" ? <ErrorState description="No fue posible cargar los documentos. Las importaciones siguen disponibles." onRetry={load} /> : !state.evidence.rows.length ? <Card><CardContent><div className="flex items-start gap-3"><FileText aria-hidden="true" className="text-[var(--text-muted)]" /><div><p className="font-bold">No hay documentos todavía.</p><p className="mt-1 text-sm text-[var(--text-muted)]">Agrega un documento cuando necesites respaldar información de tu operación.</p></div></div></CardContent></Card> : <Card><CardContent>
        <p className="text-sm text-[var(--text-muted)]">{state.evidence.rows.length} {state.evidence.rows.length === 1 ? "documento registrado" : "documentos registrados"}</p>
        <div className="mt-3 divide-y divide-[var(--border-subtle)]">{recentEvidence.map((item) => {
          const status = evidenceStatusInfo(item.estado_documental);
          return <Link key={item.id} className="flex items-center justify-between gap-3 py-3 focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to={`/datos/evidencias/${item.id}`}><span className="min-w-0"><span className="block truncate font-bold text-[var(--text-primary)]">{item.nombre || "Documento"}</span><span className="block text-xs text-[var(--text-muted)]">{item.obra_nombre || "Organización"}</span></span><StatusBadge tone={status.tone}>{status.label}</StatusBadge></Link>;
        })}</div>
      </CardContent></Card>}
    </section>

    <section>
      <SectionHeader title="Importaciones recientes" description="Últimas cargas de información y su resultado." action={<Link className="text-sm font-bold text-[var(--brand-primary)]" to="/datos/importaciones">Ver importaciones</Link>} />
      {state.imports.status === "error" ? <ErrorState description="No fue posible cargar el historial de importaciones. Tus documentos siguen disponibles." onRetry={load} /> : !state.imports.rows.length ? <Card><CardContent><div className="flex items-start gap-3"><UploadCloud aria-hidden="true" className="text-[var(--text-muted)]" /><div><p className="font-bold">No hay importaciones anteriores.</p><p className="mt-1 text-sm text-[var(--text-muted)]">Puedes iniciar una nueva carga desde Importaciones.</p></div></div></CardContent></Card> : <Card><CardContent className="divide-y divide-[var(--border-subtle)] p-0">{recentImports.map((item) => {
        const status = importStatusInfo(item.estado);
        return <Link key={item.id} className="flex flex-col gap-2 p-4 focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] sm:flex-row sm:items-center sm:justify-between" to={`/datos/importaciones/${item.id}`}><span className="min-w-0"><span className="block truncate font-bold text-[var(--text-primary)]">{importDisplayName(item)}</span><span className="block text-xs text-[var(--text-muted)]">{importResultLabel(item)} · {formatDateTime(item.created_at)}</span></span><StatusBadge tone={status.tone}>{status.label}</StatusBadge></Link>;
      })}</CardContent></Card>}
    </section>
  </main>;
}
