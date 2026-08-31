import { createElement, useEffect, useRef, useState } from "react";
import { ArrowLeft, BadgeCheck, FileCheck2, FileText, History, MessageSquareText, Receipt, ShieldCheck } from "lucide-react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { Alert, ButtonLink, EmptyState, ErrorState, SectionHeader, StatusBadge, Timeline, TimelineItem } from "@/shared/ui";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { formatDate, formatDateTime } from "@/shared/utils/formatters";
import EvidenceDocumentViewer, { documentPresentation, FileActions } from "../components/EvidenceDocumentViewer";
import { evidenceContext, listEvidence, listImports } from "../services/dataApi";
import { evidenceStatusInfo, evidenceTypeLabel, importDisplayName } from "../utils/dataPresentation";

const evidenceIcon = (type, presentation) => {
  const value = String(type || "").toLowerCase();
  if (value.includes("factura")) return Receipt;
  if (value.includes("certificado")) return BadgeCheck;
  if (value.includes("informe")) return FileText;
  return presentation.Icon || FileCheck2;
};

export default function EvidenceDetailPage() {
  const { evidenceId, obraId } = useParams();
  const workContext = useOutletContext();
  const { activeOrganizacionId } = useOrganizacionActiva();
  const scopeKey = `${activeOrganizacionId || ""}:${evidenceId}`;
  const [state, setState] = useState({ scope: null, status: "loading", data: null, document: null, linkedImport: null, supplementalError: false });
  const requestRef = useRef(0);

  useEffect(() => {
    if (!activeOrganizacionId) return undefined;
    const requestId = ++requestRef.current;
    setState({ scope: scopeKey, status: "loading", data: null, document: null, linkedImport: null, supplementalError: false });
    Promise.allSettled([evidenceContext(evidenceId), listEvidence(activeOrganizacionId), listImports(activeOrganizacionId)]).then(([contextResult, evidenceResult, importsResult]) => {
      if (requestRef.current !== requestId) return;
      if (contextResult.status === "rejected") return setState({ scope: scopeKey, status: "error", data: null, document: null, linkedImport: null, supplementalError: false });
      if (String(contextResult.value.references?.organization || "") !== String(activeOrganizacionId)) return setState({ scope: scopeKey, status: "missing", data: null, document: null, linkedImport: null, supplementalError: false });
      const documents = evidenceResult.status === "fulfilled" ? evidenceResult.value : null;
      const document = documents?.find((item) => String(item.id) === String(evidenceId)) || null;
      if (documents && !document) return setState({ scope: scopeKey, status: "missing", data: null, document: null, linkedImport: null, supplementalError: importsResult.status === "rejected" });
      if (obraId && document && ![document.obra, document.obra_codigo].map(String).includes(String(obraId))) return setState({ scope: scopeKey, status: "missing", data: null, document: null, linkedImport: null, supplementalError: false });
      const imports = importsResult.status === "fulfilled" ? importsResult.value : [];
      setState({ scope: scopeKey, status: "ready", data: contextResult.value, document, linkedImport: imports.find((item) => String(item.version_evidencia_detalle?.evidencia) === String(evidenceId)) || null, supplementalError: evidenceResult.status === "rejected" || importsResult.status === "rejected" });
    });
    return () => { requestRef.current += 1; };
  }, [activeOrganizacionId, evidenceId, obraId, scopeKey]);

  if (state.scope !== scopeKey || state.status === "loading") return <PlatformLoader title="Cargando documento" description="Estamos reuniendo el archivo, sus versiones y relaciones de trazabilidad." />;
  if (state.status === "missing") return <ErrorState description="El documento no está disponible en la organización activa." />;
  if (state.status === "error") return <ErrorState description="El documento no existe o no está disponible para tu usuario." />;

  const evidence = state.data.evidencia;
  const versions = state.data.versiones || [];
  const document = state.document || {};
  const status = evidenceStatusInfo(evidence.estado || document.estado_documental);
  const type = evidence.tipo || document.tipo_evidencia;
  const typeLabel = evidenceTypeLabel(type);
  const scopeLabel = document.obra_nombre || document.organizacion_nombre || "Organización activa";
  const documentDate = evidence.fecha_documento || document.fecha_documento;
  const extractedDate = document.metadata_extraccion?.validacion_documental?.comparaciones?.find((item) => item.campo === "fecha")?.documental || document.metadata_extraccion?.extraccion_documental?.claims?.fecha;
  const latestVersion = versions[0];
  const fileUrl = document.archivo_url || evidence.archivo_url || "";
  const fileName = latestVersion?.nombre_original || document.archivo?.split("/").pop() || evidence.nombre || document.nombre || "Documento original";
  const mime = latestVersion?.metadata_tecnica?.mime_type || document.metadata_extraccion?.mime_type;
  const presentation = documentPresentation({ url: fileUrl, name: fileName, mime });
  const observations = evidence.observaciones || evidence.descripcion || document.observaciones;

  return <main className="space-y-6">
    <div className="flex flex-wrap items-center gap-2 text-sm font-bold text-[var(--text-secondary)]">
      <Link className="inline-flex items-center gap-2 focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to={obraId ? `/obras/${obraId}/evidencias` : "/datos/evidencias"}><ArrowLeft aria-hidden="true" size={16} />{obraId ? workContext?.obra?.nombre || "Unidad" : "Datos"}</Link>
      <span aria-hidden="true">→</span><Link to={obraId ? `/obras/${obraId}/evidencias` : "/datos/evidencias"}>Evidencias</Link>
      <span aria-hidden="true">→</span><span>{evidence.nombre || document.nombre || "Documento"}</span>
    </div>
    <header className="flex flex-wrap items-start justify-between gap-4 border-b border-[var(--border-default)] pb-5"><div className="flex min-w-0 items-start gap-3"><span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">{createElement(evidenceIcon(type, presentation), { "aria-hidden": true, size: 23 })}</span><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h1 className="text-2xl font-black text-[var(--text-primary)]">{evidence.nombre || document.nombre || "Documento"}</h1><StatusBadge tone={status.tone}>{status.label}</StatusBadge></div><p className="mt-1 text-sm text-[var(--text-secondary)]">{typeLabel} · {scopeLabel}</p><p className="mt-1 text-xs text-[var(--text-muted)]">{documentDate ? `Fecha informada: ${formatDate(documentDate)}` : extractedDate ? `Fecha encontrada en documento: ${formatDate(extractedDate)}` : "Fecha no extraída"}</p></div></div><FileActions url={fileUrl} name={fileName} /></header>
    {state.supplementalError && <Alert tone="info" title="Detalle parcial">El documento está disponible, pero parte de su contexto relacionado no pudo consultarse.</Alert>}

    <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,7fr)_minmax(280px,3fr)]">
      <EvidenceDocumentViewer url={fileUrl} name={fileName} mime={mime} />
      <aside className="rounded-[24px] border border-[var(--border-default)] bg-white p-5 shadow-[0_12px_32px_rgba(15,23,42,0.05)] lg:sticky lg:top-24"><p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">Información</p><dl className="mt-4 space-y-4 text-sm"><div><dt className="text-[var(--text-muted)]">Tipo</dt><dd className="font-bold">{typeLabel}</dd></div><div><dt className="text-[var(--text-muted)]">Estado</dt><dd className="font-bold">{status.label}</dd></div><div><dt className="text-[var(--text-muted)]">Fecha informada en metadata</dt><dd className="font-bold">{documentDate ? formatDate(documentDate) : "Sin datos"}</dd></div><div><dt className="text-[var(--text-muted)]">Fecha encontrada en documento</dt><dd className="font-bold">{extractedDate ? formatDate(extractedDate) : "No extraída"}</dd></div><div><dt className="text-[var(--text-muted)]">Obra o alcance</dt><dd className="font-bold">{scopeLabel}</dd></div>{document.organizacion_nombre && <div><dt className="text-[var(--text-muted)]">Organización</dt><dd className="font-bold">{document.organizacion_nombre}</dd></div>}</dl>{obraId && <ButtonLink className="mt-5" variant="secondary" to={`/obras/${obraId}/operacion`}>Ver operación relacionada →</ButtonLink>}{state.linkedImport && <div className="mt-6 border-t border-[var(--border-default)] pt-5"><p className="text-xs font-black uppercase tracking-[0.14em] text-[var(--text-muted)]">Origen de incorporación</p><p className="mt-2 text-sm font-bold">{importDisplayName(state.linkedImport)}</p><ButtonLink className="mt-3" variant="secondary" to={`/datos/importaciones/${state.linkedImport.id}`}>Ver importación →</ButtonLink></div>}</aside>
    </div>

    {observations && <section className="flex gap-3 rounded-[20px] border border-teal-200 bg-teal-50/50 p-5"><MessageSquareText aria-hidden="true" className="shrink-0 text-teal-700" size={21} /><div><h2 className="font-black">Observaciones documentales</h2><p className="mt-1 text-sm leading-6 text-[var(--text-secondary)]">{observations}</p></div></section>}

    <section><SectionHeader title="Versiones" description="Historial documental conservado sin reemplazar silenciosamente el archivo original." />{versions.length ? <div className="mt-4 rounded-[22px] border border-[var(--border-default)] bg-white p-5"><Timeline>{versions.map((version, index) => <TimelineItem key={version.id} icon={ShieldCheck} timestamp={formatDateTime(version.created_at)} title={`Versión ${version.version}${index === 0 ? " · más reciente" : ""}`} description={version.nombre_original || "Archivo sin nombre"} />)}</Timeline></div> : <EmptyState compact icon={History} title="Sin versiones adicionales" description="Este documento conserva únicamente su archivo original." />}</section>

    <section><SectionHeader title="Trazabilidad" description="Información disponible para responder de dónde salió este documento." /><div className="mt-4 rounded-[22px] border border-[var(--border-default)] bg-white p-5"><div className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4"><Trace label="Archivo original" value={fileName} /><Trace label="Contexto" value={scopeLabel} /><Trace label="Versionado" value={versions.length ? `${versions.length} ${versions.length === 1 ? "versión" : "versiones"}` : "Archivo original"} /><Trace label="Importación" value={state.linkedImport ? importDisplayName(state.linkedImport) : "Sin importación vinculada"} /></div><details className="mt-5 border-t border-[var(--border-default)] pt-4"><summary className="cursor-pointer font-bold">Información técnica</summary><dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">{document.obra_codigo && <Technical label="Código de obra" value={document.obra_codigo} />}<Technical label="Identificador documental" value={evidenceId} />{latestVersion && <><Technical label="Nombre original" value={latestVersion.nombre_original || "Sin datos"} /><Technical label="Versión" value={latestVersion.version} /><div className="sm:col-span-2"><Technical label="Checksum" value={latestVersion.checksum_sha256 || "Sin datos"} mono /></div></>}</dl></details><p className="mt-4 text-xs text-[var(--text-muted)]">El contrato no entrega observaciones individuales producidas por este documento; no se reconstruyen ni se infieren.</p></div></section>
  </main>;
}

function Trace({ label, value }) { return <div><p className="text-[var(--text-muted)]">{label}</p><p className="mt-1 font-bold">{value}</p></div>; }
function Technical({ label, value, mono = false }) { return <div><dt className="text-[var(--text-muted)]">{label}</dt><dd className={`break-all font-medium ${mono ? "font-mono text-xs" : ""}`}>{value}</dd></div>; }
