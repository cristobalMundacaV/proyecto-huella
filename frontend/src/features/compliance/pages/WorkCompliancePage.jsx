import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, FileText, ShieldCheck } from "lucide-react";
import { Link, useOutletContext } from "react-router-dom";

import PlatformLoader from "@/shared/components/PlatformLoader";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { EmptyState, ErrorState, KpiCard, Pagination, SectionHeader, StatusBadge, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDate } from "@/shared/utils/formatters";
import { getComplianceAlerts, getComplianceDocuments, getComplianceSummary } from "../api/complianceApi";

const rowsFrom = (value) => Array.isArray(value) ? value : value?.results || value?.data || [];
const errorMessage = (reason, fallback) => reason?.response?.data?.error || reason?.response?.data?.detail || fallback;
const PAGE_SIZE = 8;
const DOCUMENT_TYPE_LABELS = {
  balance_consumos: "Balance de consumos",
  medicion_ruido: "Medición de ruido",
};
const humanize = (value) => String(value || "Sin datos").replaceAll("_", " ");
const documentTypeLabel = (value) => DOCUMENT_TYPE_LABELS[value] || humanize(value);
const statusTone = (value) => {
  const status = String(value || "").toLowerCase();
  if (["valido", "válido", "validado", "resuelta", "cerrada"].includes(status)) return "success";
  if (["rechazado", "vencido", "error"].includes(status)) return "danger";
  if (["pendiente", "observado", "abierta", "en_revision"].includes(status)) return "warning";
  return "info";
};

export default function WorkCompliancePage() {
  const workspace = useOutletContext() || {};
  const { activeOrganizacionId } = useOrganizacionActiva();
  const workId = workspace.obra?.id || workspace.obra?.obra_id;
  const scope = activeOrganizacionId && workId ? `${activeOrganizacionId}:${workId}` : "";
  const requestRef = useRef(0);
  const [documentsPage, setDocumentsPage] = useState(1);
  const [state, setState] = useState({ scope: "", loading: true, summary: null, documents: [], alerts: [], summaryError: "", documentsError: "", alertsError: "" });

  const load = useCallback(async () => {
    if (!activeOrganizacionId || !workId) {
      requestRef.current += 1;
      setState({ scope: "", loading: false, summary: null, documents: [], alerts: [], summaryError: "", documentsError: "", alertsError: "" });
      return;
    }
    const requestId = ++requestRef.current;
    const requestScope = `${activeOrganizacionId}:${workId}`;
    setState({ scope: requestScope, loading: true, summary: null, documents: [], alerts: [], summaryError: "", documentsError: "", alertsError: "" });
    const params = { obra: workId };
    const [summary, documents, alerts] = await Promise.allSettled([
      getComplianceSummary(activeOrganizacionId, params),
      getComplianceDocuments(activeOrganizacionId, params),
      getComplianceAlerts(activeOrganizacionId, params),
    ]);
    if (requestRef.current !== requestId) return;
    setState({
      scope: requestScope,
      loading: false,
      summary: summary.status === "fulfilled" ? summary.value : null,
      documents: documents.status === "fulfilled" ? rowsFrom(documents.value) : [],
      alerts: alerts.status === "fulfilled" ? rowsFrom(alerts.value) : [],
      summaryError: summary.status === "rejected" ? errorMessage(summary.reason, "No se pudo cargar el resumen de cumplimiento.") : "",
      documentsError: documents.status === "rejected" ? errorMessage(documents.reason, "No se pudieron cargar los documentos ambientales.") : "",
      alertsError: alerts.status === "rejected" ? errorMessage(alerts.reason, "No se pudieron cargar las alertas de cumplimiento.") : "",
    });
  }, [activeOrganizacionId, workId]);

  useEffect(() => {
    load();
    return () => { requestRef.current += 1; };
  }, [load]);

  useEffect(() => {
    setDocumentsPage(1);
  }, [scope]);

  const visibleDocuments = useMemo(() => {
    const start = (documentsPage - 1) * PAGE_SIZE;
    return state.documents.slice(start, start + PAGE_SIZE);
  }, [documentsPage, state.documents]);

  if (!activeOrganizacionId || !workId) return <EmptyState icon={ShieldCheck} title="Obra no disponible" description="Selecciona una obra válida de la organización activa para revisar su cumplimiento." />;
  if (state.scope !== scope || state.loading) return <PlatformLoader title="Cargando cumplimiento" description="Estamos reuniendo documentos, indicadores y alertas de esta obra." />;
  if (state.summaryError && state.documentsError && state.alertsError) return <ErrorState description="No fue posible cargar la información de cumplimiento de esta obra." onRetry={load} />;

  const noData = !state.summaryError && !state.documentsError && !state.alertsError && !state.documents.length && !state.alerts.length
    && state.summary?.total_documentos === 0
    && state.summary?.alertas_abiertas === 0;

  const alertCount = state.summary?.alertas_abiertas;
  const hasAlerts = state.alerts.length > 0 || (alertCount !== null && alertCount !== undefined && alertCount > 0);

  return <main className="space-y-7">
    <section className={`overflow-hidden rounded-[28px] border p-6 shadow-[0_16px_40px_rgba(15,23,42,0.06)] ${hasAlerts ? "border-amber-200 bg-[linear-gradient(135deg,rgba(255,251,235,0.98),rgba(255,255,255,0.96))]" : "border-cyan-200 bg-[linear-gradient(135deg,rgba(236,254,255,0.98),rgba(255,255,255,0.96))]"}`}>
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-center">
        <SectionHeader eyebrow="CUMPLIMIENTO" title="Cumplimiento ambiental" description="Qué está respaldado y qué necesita revisión dentro de esta obra." />
        <div className={`rounded-[20px] border p-4 ${hasAlerts ? "border-amber-200 bg-amber-50/80" : "border-cyan-200 bg-cyan-50/80"}`}>
          <div className="flex items-start gap-3"><span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${hasAlerts ? "bg-amber-100 text-amber-700" : "bg-cyan-100 text-cyan-800"}`}>{hasAlerts ? <AlertTriangle aria-hidden="true" size={20} /> : <ShieldCheck aria-hidden="true" size={20} />}</span><div><p className="text-xs font-black uppercase tracking-[0.12em] text-[var(--text-muted)]">Lectura actual</p><p className="mt-1 font-black">{hasAlerts ? "Requiere revisión" : alertCount === 0 ? "Sin alertas abiertas" : "Estado parcial"}</p><p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">{hasAlerts ? "Revisa primero las alertas abiertas y sus antecedentes." : "La lectura refleja únicamente los datos disponibles."}</p></div></div>
        </div>
      </div>
    </section>
    {noData ? <EmptyState icon={ShieldCheck} title="Sin información de cumplimiento" description="Esta obra todavía no tiene documentos ni alertas ambientales asociados." /> : <>
      {state.summaryError ? <ErrorState description={state.summaryError} onRetry={load} /> : <div className="grid gap-4 md:grid-cols-3">
        <KpiCard label="Documentos respaldados" value={state.summary?.total_documentos} helper={state.summary?.documentos_validados === null || state.summary?.documentos_validados === undefined ? "Validación no disponible" : `${state.summary.documentos_validados} validados`} icon={FileText} />
        <KpiCard label="Alertas abiertas" value={alertCount} helper={hasAlerts ? "Requieren atención" : alertCount === 0 ? "Sin alertas abiertas" : "Estado no disponible"} icon={AlertTriangle} status={hasAlerts ? "warning" : alertCount === 0 ? "success" : "neutral"} />
        <KpiCard label="Cumplimiento" value={state.summary?.compliance_pct} unit={state.summary?.compliance_pct === null || state.summary?.compliance_pct === undefined ? undefined : "%"} helper="Porcentaje informado por el servicio de cumplimiento" icon={ShieldCheck} />
      </div>}

      <section className="space-y-3"><SectionHeader eyebrow="PRIORIDAD" title="Requiere atención" description="Alertas que deben revisarse antes de interpretar el cumplimiento como completo." />
        {state.alertsError ? <ErrorState description={state.alertsError} onRetry={load} /> : !state.alerts.length ? <EmptyState icon={CheckCircle2} title="Sin alertas abiertas" description="No existen alertas de cumplimiento asociadas a esta obra." /> :
          <div className="grid gap-3">{state.alerts.slice(0, 5).map((item) => <article key={item.id} className="flex flex-col gap-3 rounded-[20px] border border-amber-200 bg-amber-50/60 p-4 sm:flex-row sm:items-center sm:justify-between"><div className="flex items-start gap-3"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-amber-700"><AlertTriangle aria-hidden="true" size={18} /></span><div><b>{item.titulo || item.mensaje || item.descripcion || `Alerta ${item.id}`}</b><p className="mt-1 text-xs text-[var(--text-muted)]">Requiere revisión documental o de vigencia.</p></div></div><div className="flex flex-wrap gap-2"><StatusBadge tone={item.severidad === "rojo" ? "danger" : item.severidad === "amarillo" ? "warning" : "info"}>{item.severidad || "Sin clasificar"}</StatusBadge><StatusBadge tone={statusTone(item.estado)}>{humanize(item.estado || "pendiente")}</StatusBadge></div></article>)}</div>}
      </section>

      <section className="space-y-3"><SectionHeader eyebrow="ANTECEDENTES" title="Documentos ambientales" action={<Link className="text-sm font-bold text-[var(--brand-primary)]" to="../evidencias">Ir a evidencias</Link>} />
        {state.documentsError ? <ErrorState description={state.documentsError} onRetry={load} /> : !state.documents.length ? <EmptyState icon={FileText} title="Sin documentos asociados" description="Todavía no existen documentos ambientales vinculados a esta obra." /> :
          <><TableShell><TableHead><tr><TableCell as="th" align="left">Documento</TableCell><TableCell as="th" align="center">Tipo</TableCell><TableCell as="th" align="center">Estado</TableCell><TableCell as="th" align="center">Fecha</TableCell></tr></TableHead><TableBody columns={4}>{visibleDocuments.map((item) => { const documentStatus = item.estado_validacion || item.estado || "pendiente"; return <tr key={item.id}><TableCell align="left"><b>{item.nombre || item.nombre_archivo || `Documento ${item.id}`}</b></TableCell><TableCell align="center">{documentTypeLabel(item.tipo_documento || item.tipo)}</TableCell><TableCell align="center"><StatusBadge tone={statusTone(documentStatus)}>{humanize(documentStatus)}</StatusBadge></TableCell><TableCell align="center">{formatDate(item.fecha_documento || item.created_at)}</TableCell></tr>; })}</TableBody></TableShell>{state.documents.length > PAGE_SIZE ? <Pagination page={documentsPage} totalItems={state.documents.length} pageSize={PAGE_SIZE} onChange={setDocumentsPage} itemLabel="documentos" /> : null}</>}
      </section>
    </>}
  </main>;
}
