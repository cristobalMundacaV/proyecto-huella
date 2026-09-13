import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Database, ShieldCheck } from "lucide-react";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { EmptyState, ErrorState, LoadingState, Pagination, Select, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime, formatNumber } from "@/shared/utils/formatters";
import { getDiscrepancies, getQualityEvaluations, getSourcePolicies } from "../api/professionalV2Api";
import { human, isOpenDiscrepancy, Section, State } from "../components/GovernanceShared";

const PAGE_SIZE = 8;
const resource = (status = "loading", data = []) => ({ status, data });

export default function QualityGovernancePage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ scopeKey: "", quality: resource(), discrepancies: resource(), policies: resource() });
  const [discrepancyFilter, setDiscrepancyFilter] = useState("abiertas");
  const [pages, setPages] = useState({ discrepancies: 1, quality: 1, policies: 1 });
  const requestRef = useRef(0);
  useEffect(() => {
    if (!activeOrganizacionId) return undefined;
    const scopeKey = String(activeOrganizacionId); const requestId = ++requestRef.current;
    setState({ scopeKey, quality: resource(), discrepancies: resource(), policies: resource() });
    Promise.allSettled([getQualityEvaluations(activeOrganizacionId), getDiscrepancies(activeOrganizacionId), getSourcePolicies(activeOrganizacionId)]).then(([qualityResult, discrepancyResult, policiesResult]) => {
      if (requestRef.current !== requestId) return;
      setState({ scopeKey, quality: qualityResult.status === "fulfilled" ? resource("ready", qualityResult.value) : resource("error"), discrepancies: discrepancyResult.status === "fulfilled" ? resource("ready", discrepancyResult.value) : resource("error"), policies: policiesResult.status === "fulfilled" ? resource("ready", policiesResult.value) : resource("error") });
    });
    return () => { requestRef.current += 1; };
  }, [activeOrganizacionId]);
  useEffect(() => { setPages({ discrepancies: 1, quality: 1, policies: 1 }); }, [activeOrganizacionId, discrepancyFilter, state.discrepancies.data, state.quality.data, state.policies.data]);
  const requestedScopeKey = activeOrganizacionId ? String(activeOrganizacionId) : "";
  if (state.scopeKey !== requestedScopeKey) return <LoadingState label="Cargando calidad" />;
  const discrepancies = state.discrepancies.data.filter((item) => discrepancyFilter === "abiertas" ? isOpenDiscrepancy(item) : !discrepancyFilter ? true : item.estado === discrepancyFilter);
  const openDiscrepancies = state.discrepancies.data.filter(isOpenDiscrepancy);
  const criticalDiscrepancies = openDiscrepancies.filter((item) => ["alta", "critica"].includes(item.severidad)).length;
  const usableQuality = state.quality.data.filter((item) => ["utilizable", "confiable", "confiable_con_observaciones"].includes(item.estado)).length;
  const pageRows = (rows, key) => rows.slice((pages[key] - 1) * PAGE_SIZE, pages[key] * PAGE_SIZE);
  const pagination = (rows, key, label) => <Pagination page={pages[key]} totalItems={rows.length} pageSize={PAGE_SIZE} onChange={(page) => setPages((current) => ({ ...current, [key]: page }))} itemLabel={label} />;

  return <main className="space-y-8">
    <section className="overflow-hidden rounded-[28px] border border-emerald-700/20 bg-[radial-gradient(circle_at_top_right,rgba(52,211,153,0.24),transparent_34%),linear-gradient(135deg,rgba(6,78,59,0.98),rgba(6,95,70,0.94)_52%,rgba(15,118,110,0.86))] p-6 text-white shadow-[0_18px_45px_rgba(6,78,59,0.16)]">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between"><div className="max-w-3xl"><p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-100">Gobernanza · Integridad del dato</p><h1 className="mt-2 text-3xl font-black">Calidad y discrepancias</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50/85">Supervisa contradicciones, evaluaciones y reglas de fuente antes de utilizar información ambiental en decisiones o reportes.</p></div><span className="inline-flex w-fit items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-2 text-xs font-bold text-emerald-50"><ShieldCheck size={16} />Control con trazabilidad</span></div>
    </section>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Resumen de calidad">
      <QualityMetric icon={AlertTriangle} label="Discrepancias abiertas" value={state.discrepancies.status === "ready" ? openDiscrepancies.length : "—"} helper="requieren contraste" tone="amber" />
      <QualityMetric icon={AlertTriangle} label="Alta severidad" value={state.discrepancies.status === "ready" ? criticalDiscrepancies : "—"} helper="prioridad de revisión" tone="rose" />
      <QualityMetric icon={ShieldCheck} label="Datos utilizables" value={state.quality.status === "ready" ? usableQuality : "—"} helper={`de ${state.quality.status === "ready" ? state.quality.data.length : "—"} evaluaciones`} tone="emerald" />
      <QualityMetric icon={Database} label="Políticas de fuente" value={state.policies.status === "ready" ? state.policies.data.length : "—"} helper="reglas vigentes registradas" tone="sky" />
    </section>
    <Section title="Discrepancias" description="La interfaz no resuelve contradicciones ni mezcla confiabilidad de fuente con calidad del dato."><div className="max-w-xs"><Select label="Estado" value={discrepancyFilter} onChange={(event) => setDiscrepancyFilter(event.target.value)}><option value="abiertas">Abiertas</option><option value="">Todas</option><option value="detectada">Detectadas</option><option value="requiere_revision">Requieren revisión</option><option value="resuelta">Resueltas</option><option value="aceptada">Aceptadas</option></Select></div>
      {state.discrepancies.status === "loading" ? <LoadingState inline label="Cargando discrepancias" /> : state.discrepancies.status === "error" ? <ErrorState description="No se pudieron cargar las discrepancias." /> : !discrepancies.length ? <EmptyState title={discrepancyFilter === "abiertas" ? "No hay discrepancias abiertas registradas." : "No hay discrepancias con este estado."} description="La ausencia de discrepancias abiertas no significa calidad perfecta." /> : <><TableShell><TableHead><tr><TableCell as="th">Dato o concepto</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Motivo</TableCell><TableCell as="th">Observaciones</TableCell><TableCell as="th">Siguiente paso</TableCell></tr></TableHead><TableBody columns={5}>{pageRows(discrepancies, "discrepancies").map((item) => <tr key={item.id}><TableCell><b>{human(item.concepto)}</b><span className="block text-xs text-[var(--text-muted)]">Discrepancia #{item.id}</span></TableCell><TableCell><State value={item.estado} /></TableCell><TableCell>{item.motivo || item.resolucion || "Motivo no informado"}</TableCell><TableCell align="center">{item.observaciones?.length || 0} involucradas{item.severidad && <span className="block text-xs text-[var(--text-muted)]">Severidad: {human(item.severidad)}</span>}</TableCell><TableCell>{isOpenDiscrepancy(item) ? <span className="font-medium">Revisar discrepancia</span> : <span className="text-[var(--text-muted)]">Decisión registrada</span>}</TableCell></tr>)}</TableBody></TableShell>{pagination(discrepancies, "discrepancies", "discrepancias")}</>}
    </Section>
    <Section title="Calidad del dato" description="La evaluación corresponde al dato observado; no hereda automáticamente la confiabilidad de su fuente.">{state.quality.status === "loading" ? <LoadingState inline label="Cargando evaluaciones" /> : state.quality.status === "error" ? <ErrorState description="No se pudieron cargar las evaluaciones; las demás secciones siguen disponibles." /> : !state.quality.data.length ? <EmptyState title="Sin evaluaciones registradas" description="No hay evaluaciones de calidad disponibles." /> : <><TableShell><TableHead><tr><TableCell as="th">Dato</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Motivos</TableCell><TableCell as="th">Evaluación</TableCell></tr></TableHead><TableBody columns={4}>{pageRows(state.quality.data, "quality").map((item) => <tr key={item.id}><TableCell><b>{human(item.observacion_detalle?.concepto)}</b><span className="block text-xs text-[var(--text-muted)]">{item.observacion_detalle?.valor === null || item.observacion_detalle?.valor === undefined ? "Sin datos" : `${formatNumber(item.observacion_detalle.valor)} ${item.observacion_detalle?.unidad || ""}`.trim()}</span></TableCell><TableCell><State value={item.estado} /></TableCell><TableCell>{item.motivos?.join?.(", ") || "Sin observaciones"}</TableCell><TableCell>{item.automatica ? "Automática" : "Profesional"}<span className="block text-xs">{formatDateTime(item.fecha_evaluacion)}</span></TableCell></tr>)}</TableBody></TableShell>{pagination(state.quality.data, "quality", "evaluaciones")}</>}</Section>
    <Section title="Confiabilidad de fuentes" description="La prioridad de una fuente no convierte automáticamente una observación en válida.">{state.policies.status === "loading" ? <LoadingState inline label="Cargando políticas" /> : state.policies.status === "error" ? <ErrorState description="No se pudieron cargar las políticas de fuente." /> : !state.policies.data.length ? <EmptyState title="Sin políticas registradas" description="No hay reglas de prioridad de fuente disponibles." /> : <><TableShell><TableHead><tr><TableCell as="th">Concepto</TableCell><TableCell as="th">Tipo de fuente</TableCell><TableCell as="th">Prioridad</TableCell><TableCell as="th">Alcance</TableCell><TableCell as="th">Descripción</TableCell></tr></TableHead><TableBody columns={5}>{pageRows(state.policies.data, "policies").map((item) => <tr key={item.id}><TableCell>{human(item.concepto)}</TableCell><TableCell>{human(item.tipo_fuente)}</TableCell><TableCell align="center">{item.prioridad}</TableCell><TableCell align="center">{item.organizacion ? "Organización" : "Global"}</TableCell><TableCell>{item.descripcion || "Sin descripción"}</TableCell></tr>)}</TableBody></TableShell>{pagination(state.policies.data, "policies", "políticas")}</>}</Section>
  </main>;
}

function QualityMetric({ icon: Icon, label, value, helper, tone }) {
  const tones = {
    amber: "border-amber-200 bg-amber-50/55 text-amber-800",
    rose: "border-rose-200 bg-rose-50/55 text-rose-800",
    emerald: "border-emerald-200 bg-emerald-50/55 text-emerald-800",
    sky: "border-sky-200 bg-sky-50/55 text-sky-800",
  };
  return <article className={`rounded-[22px] border p-5 shadow-[0_10px_28px_rgba(15,23,42,0.045)] ${tones[tone]}`}>
    <div className="flex items-start justify-between gap-3"><div><p className="text-xs font-black uppercase tracking-[0.1em] opacity-75">{label}</p><p className="mt-2 text-3xl font-black text-[var(--text-primary)]">{value}</p></div><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/75 shadow-sm"><Icon size={19} /></span></div>
    <p className="mt-2 text-xs font-semibold opacity-75">{helper}</p>
  </article>;
}
