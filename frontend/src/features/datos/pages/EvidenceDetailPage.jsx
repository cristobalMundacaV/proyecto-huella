import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ExternalLink, ShieldCheck } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { Alert, Card, CardContent, ErrorState, LoadingState, PageHeader, SectionHeader, StatusBadge, Timeline, TimelineItem } from "@/shared/ui";
import { formatDate, formatDateTime } from "@/shared/utils/formatters";
import { evidenceContext, listEvidence, listImports } from "../services/dataApi";
import { evidenceStatusInfo, evidenceTypeLabel, importDisplayName } from "../utils/dataPresentation";

export default function EvidenceDetailPage() {
  const { evidenceId } = useParams();
  const { activeOrganizacionId } = useOrganizacionActiva();
  const scopeKey = `${activeOrganizacionId || ""}:${evidenceId}`;
  const [state, setState] = useState({ scope: null, status: "loading", data: null, document: null, linkedImport: null, supplementalError: false });
  const requestRef = useRef(0);

  useEffect(() => {
    if (!activeOrganizacionId) return undefined;
    const requestId = ++requestRef.current;
    setState({ scope: scopeKey, status: "loading", data: null, document: null, linkedImport: null, supplementalError: false });

    Promise.allSettled([
      evidenceContext(evidenceId),
      listEvidence(activeOrganizacionId),
      listImports(activeOrganizacionId),
    ]).then(([contextResult, evidenceResult, importsResult]) => {
      if (requestRef.current !== requestId) return;
      if (contextResult.status === "rejected") {
        setState({ scope: scopeKey, status: "error", data: null, document: null, linkedImport: null, supplementalError: false });
        return;
      }
      if (String(contextResult.value.references?.organization || "") !== String(activeOrganizacionId)) {
        setState({ scope: scopeKey, status: "missing", data: null, document: null, linkedImport: null, supplementalError: false });
        return;
      }

      const documents = evidenceResult.status === "fulfilled" ? evidenceResult.value : null;
      const document = documents?.find((item) => String(item.id) === String(evidenceId)) || null;
      if (documents && !document) {
        setState({ scope: scopeKey, status: "missing", data: null, document: null, linkedImport: null, supplementalError: importsResult.status === "rejected" });
        return;
      }

      const imports = importsResult.status === "fulfilled" ? importsResult.value : [];
      const linkedImport = imports.find((item) => String(item.version_evidencia_detalle?.evidencia) === String(evidenceId)) || null;
      setState({
        scope: scopeKey,
        status: "ready",
        data: contextResult.value,
        document,
        linkedImport,
        supplementalError: evidenceResult.status === "rejected" || importsResult.status === "rejected",
      });
    });

    return () => { requestRef.current += 1; };
  }, [activeOrganizacionId, evidenceId, scopeKey]);

  if (state.scope !== scopeKey || state.status === "loading") return <LoadingState label="Cargando documento" />;
  if (state.status === "missing") return <ErrorState description="El documento no está disponible en la organización activa." />;
  if (state.status === "error") return <ErrorState description="El documento no existe o no está disponible para tu usuario." />;

  const evidence = state.data.evidencia;
  const versions = state.data.versiones || [];
  const status = evidenceStatusInfo(evidence.estado);
  const scopeLabel = state.document?.obra_nombre || state.document?.organizacion_nombre || "Organización activa";
  const headerDate = evidence.fecha_documento
    ? `Fecha del documento: ${formatDate(evidence.fecha_documento)}`
    : state.document?.created_at
      ? `Ingresó: ${formatDate(state.document.created_at)}`
      : "Fecha: Sin datos";

  return <main className="space-y-6">
    <Link className="inline-flex items-center gap-2 text-sm font-bold text-[var(--text-secondary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to="/datos/evidencias"><ArrowLeft aria-hidden="true" size={16} />Evidencias</Link>
    <PageHeader
      title={evidence.nombre || "Documento"}
      description={scopeLabel}
      status={<StatusBadge tone={status.tone}>{status.label}</StatusBadge>}
      metadata={headerDate}
    />

    {state.supplementalError && <Alert tone="info" title="Detalle parcial">El documento está disponible, pero parte de su contexto relacionado no pudo consultarse.</Alert>}

    <div className="grid gap-5 lg:grid-cols-2">
      <Card><CardContent>
        <SectionHeader title="Documento" description="Archivo y datos documentales disponibles." />
        <dl className="space-y-3 text-sm">
          <div><dt className="text-[var(--text-muted)]">Tipo</dt><dd className="font-medium">{evidenceTypeLabel(evidence.tipo)}</dd></div>
          <div><dt className="text-[var(--text-muted)]">Fecha documental</dt><dd className="font-medium">{evidence.fecha_documento ? formatDate(evidence.fecha_documento) : "Sin datos"}</dd></div>
          <div><dt className="text-[var(--text-muted)]">Estado</dt><dd className="mt-1"><StatusBadge tone={status.tone}>{status.label}</StatusBadge></dd></div>
        </dl>
        {state.document?.archivo_url && <a className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" href={state.document.archivo_url} rel="noreferrer" target="_blank">Abrir archivo original <ExternalLink aria-hidden="true" size={15} /></a>}
        <p className="mt-4 text-xs text-[var(--text-muted)]">El archivo original se conserva. Las versiones procesadas se muestran por separado y no lo reemplazan silenciosamente.</p>
      </CardContent></Card>

      <Card><CardContent>
        <SectionHeader title="Contexto" description="Dónde aplica este documento." />
        <dl className="space-y-3 text-sm">
          <div><dt className="text-[var(--text-muted)]">Alcance</dt><dd className="font-medium">{scopeLabel}</dd></div>
          {state.document?.obra_codigo && <div><dt className="text-[var(--text-muted)]">Código de obra</dt><dd className="font-medium">{state.document.obra_codigo}</dd></div>}
        </dl>
        {state.linkedImport && <Link className="mt-5 inline-flex text-sm font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to={`/datos/importaciones/${state.linkedImport.id}`}>Ver importación: {importDisplayName(state.linkedImport)}</Link>}
      </CardContent></Card>
    </div>

    <section>
      <SectionHeader title="Versiones" description="Historial de archivos procesados para este documento." />
      {versions.length ? <Card><CardContent><Timeline>{versions.map((version, index) => <TimelineItem
        key={version.id}
        icon={ShieldCheck}
        timestamp={formatDateTime(version.created_at)}
        title={`Versión ${version.version}${index === 0 ? " · más reciente" : ""}`}
        description={version.nombre_original || "Archivo sin nombre"}
      />)}</Timeline></CardContent></Card> : <Card><CardContent><p className="text-sm text-[var(--text-muted)]">No hay versiones procesadas disponibles.</p></CardContent></Card>}
    </section>

    <section>
      <SectionHeader title="Trazabilidad" description="Detalles disponibles para responder de dónde salió este documento." />
      <Card><CardContent>
        {versions.length ? <details>
          <summary className="cursor-pointer font-bold text-[var(--text-primary)]">Detalles de trazabilidad</summary>
          <div className="mt-4 space-y-3">{versions.map((version) => <div key={version.id} className="rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface-subtle)] p-3 text-sm"><p className="font-bold">Versión {version.version}</p><p className="mt-1 text-[var(--text-muted)]">Archivo: {version.nombre_original || "Sin datos"}</p><p className="mt-1 break-all text-xs text-[var(--text-muted)]">Checksum: {version.checksum_sha256 || "Sin datos"}</p></div>)}</div>
        </details> : <p className="text-sm text-[var(--text-muted)]">No hay información de versiones para ampliar la trazabilidad.</p>}
        <p className="mt-4 text-xs text-[var(--text-muted)]">El contrato de este detalle no entrega observaciones individuales producidas por el documento; no se reconstruyen ni se infieren.</p>
      </CardContent></Card>
    </section>
  </main>;
}
