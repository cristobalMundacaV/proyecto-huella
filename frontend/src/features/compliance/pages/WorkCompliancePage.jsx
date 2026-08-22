import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, FileText, ShieldCheck } from "lucide-react";
import { useOutletContext } from "react-router-dom";

import PlatformLoader from "@/shared/components/PlatformLoader";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { EmptyState, ErrorState, KpiCard, SectionHeader, StatusBadge, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { getComplianceAlerts, getComplianceDocuments, getComplianceSummary } from "../api/complianceApi";

const rowsFrom = (value) => Array.isArray(value) ? value : value?.results || value?.data || [];
const errorMessage = (reason, fallback) => reason?.response?.data?.error || reason?.response?.data?.detail || fallback;

export default function WorkCompliancePage() {
  const workspace = useOutletContext() || {};
  const { activeOrganizacionId } = useOrganizacionActiva();
  const workId = workspace.obra?.id || workspace.obra?.obra_id;
  const scope = activeOrganizacionId && workId ? `${activeOrganizacionId}:${workId}` : "";
  const requestRef = useRef(0);
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

  if (!activeOrganizacionId || !workId) return <EmptyState icon={ShieldCheck} title="Obra no disponible" description="Selecciona una obra válida de la organización activa para revisar su cumplimiento." />;
  if (state.scope !== scope || state.loading) return <PlatformLoader title="Cargando cumplimiento" description="Estamos reuniendo documentos, indicadores y alertas de esta obra." />;
  if (state.summaryError && state.documentsError && state.alertsError) return <ErrorState description="No fue posible cargar la información de cumplimiento de esta obra." onRetry={load} />;

  const noData = !state.summaryError && !state.documentsError && !state.alertsError && !state.documents.length && !state.alerts.length
    && (state.summary?.total_documentos === 0 || state.summary?.total_documentos == null)
    && (state.summary?.alertas_abiertas === 0 || state.summary?.alertas_abiertas == null);

  return <main className="space-y-6">
    <SectionHeader eyebrow="CUMPLIMIENTO" title="Cumplimiento ambiental" description="Documentos y alertas correspondientes exclusivamente a esta obra." />
    {noData ? <EmptyState icon={ShieldCheck} title="Sin información de cumplimiento" description="Esta obra todavía no tiene documentos ni alertas ambientales asociados." /> : <>
      {state.summaryError ? <ErrorState description={state.summaryError} onRetry={load} /> : <div className="grid gap-4 md:grid-cols-4">
        <KpiCard label="Documentos" value={state.summary?.total_documentos} icon={FileText} />
        <KpiCard label="Validados" value={state.summary?.documentos_validados} icon={CheckCircle2} status="success" />
        <KpiCard label="Alertas abiertas" value={state.summary?.alertas_abiertas} icon={AlertTriangle} status="warning" />
        <KpiCard label="Cumplimiento" value={state.summary?.compliance_pct} unit="%" icon={ShieldCheck} />
      </div>}

      <section className="space-y-3"><SectionHeader eyebrow="ANTECEDENTES" title="Documentos ambientales" />
        {state.documentsError ? <ErrorState description={state.documentsError} onRetry={load} /> : !state.documents.length ? <EmptyState icon={FileText} title="Sin documentos asociados" description="Todavía no existen documentos ambientales vinculados a esta obra." /> :
          <TableShell><TableHead><tr><TableCell as="th">Documento</TableCell><TableCell as="th">Tipo</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Fecha</TableCell></tr></TableHead><TableBody columns={4}>{state.documents.map((item) => <tr key={item.id}><TableCell><b>{item.nombre || item.nombre_archivo || `Documento ${item.id}`}</b></TableCell><TableCell>{item.tipo_documento || item.tipo || "—"}</TableCell><TableCell><StatusBadge>{String(item.estado_validacion || item.estado || "pendiente").replaceAll("_", " ")}</StatusBadge></TableCell><TableCell>{item.fecha_documento || item.created_at || "—"}</TableCell></tr>)}</TableBody></TableShell>}
      </section>

      <section className="space-y-3"><SectionHeader eyebrow="ALERTAS" title="Alertas de cumplimiento" />
        {state.alertsError ? <ErrorState description={state.alertsError} onRetry={load} /> : !state.alerts.length ? <EmptyState icon={CheckCircle2} title="Sin alertas abiertas" description="No existen alertas de cumplimiento asociadas a esta obra." /> :
          <TableShell><TableHead><tr><TableCell as="th">Alerta</TableCell><TableCell as="th">Severidad</TableCell><TableCell as="th">Estado</TableCell></tr></TableHead><TableBody columns={3}>{state.alerts.map((item) => <tr key={item.id}><TableCell>{item.mensaje || item.descripcion || `Alerta ${item.id}`}</TableCell><TableCell><StatusBadge tone={item.severidad === "rojo" ? "danger" : item.severidad === "amarillo" ? "warning" : "success"}>{item.severidad || "Sin clasificar"}</StatusBadge></TableCell><TableCell><StatusBadge>{String(item.estado || "pendiente").replaceAll("_", " ")}</StatusBadge></TableCell></tr>)}</TableBody></TableShell>}
      </section>
    </>}
  </main>;
}
