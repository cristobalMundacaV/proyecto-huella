import { useEffect, useRef, useState } from "react";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { EmptyState, ErrorState, LoadingState, PageHeader, Pagination, Select, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
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
  const pageRows = (rows, key) => rows.slice((pages[key] - 1) * PAGE_SIZE, pages[key] * PAGE_SIZE);
  const pagination = (rows, key, label) => <Pagination page={pages[key]} totalItems={rows.length} pageSize={PAGE_SIZE} onChange={(page) => setPages((current) => ({ ...current, [key]: page }))} itemLabel={label} />;

  return <main className="space-y-8"><PageHeader eyebrow="Gobernanza" title="Calidad y discrepancias" description="Revisa qué datos tienen discrepancias o requieren revisión." />
    <Section title="Discrepancias" description="La interfaz no resuelve contradicciones ni mezcla confiabilidad de fuente con calidad del dato."><div className="max-w-xs"><Select label="Estado" value={discrepancyFilter} onChange={(event) => setDiscrepancyFilter(event.target.value)}><option value="abiertas">Abiertas</option><option value="">Todas</option><option value="detectada">Detectadas</option><option value="requiere_revision">Requieren revisión</option><option value="resuelta">Resueltas</option><option value="aceptada">Aceptadas</option></Select></div>
      {state.discrepancies.status === "loading" ? <LoadingState inline label="Cargando discrepancias" /> : state.discrepancies.status === "error" ? <ErrorState description="No se pudieron cargar las discrepancias." /> : !discrepancies.length ? <EmptyState title={discrepancyFilter === "abiertas" ? "No hay discrepancias abiertas registradas." : "No hay discrepancias con este estado."} description="La ausencia de discrepancias abiertas no significa calidad perfecta." /> : <><TableShell><TableHead><tr><TableCell as="th">Dato o concepto</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Motivo</TableCell><TableCell as="th">Observaciones</TableCell><TableCell as="th">Siguiente paso</TableCell></tr></TableHead><TableBody columns={5}>{pageRows(discrepancies, "discrepancies").map((item) => <tr key={item.id}><TableCell><b>{human(item.concepto)}</b><span className="block text-xs text-[var(--text-muted)]">Discrepancia #{item.id}</span></TableCell><TableCell><State value={item.estado} /></TableCell><TableCell>{item.motivo || item.resolucion || "Motivo no informado"}</TableCell><TableCell align="center">{item.observaciones?.length || 0} involucradas{item.severidad && <span className="block text-xs text-[var(--text-muted)]">Severidad: {human(item.severidad)}</span>}</TableCell><TableCell>{isOpenDiscrepancy(item) ? <span className="font-medium">Revisar discrepancia</span> : <span className="text-[var(--text-muted)]">Decisión registrada</span>}</TableCell></tr>)}</TableBody></TableShell>{pagination(discrepancies, "discrepancies", "discrepancias")}</>}
    </Section>
    <Section title="Calidad del dato" description="La evaluación corresponde al dato observado; no hereda automáticamente la confiabilidad de su fuente.">{state.quality.status === "loading" ? <LoadingState inline label="Cargando evaluaciones" /> : state.quality.status === "error" ? <ErrorState description="No se pudieron cargar las evaluaciones; las demás secciones siguen disponibles." /> : !state.quality.data.length ? <EmptyState title="Sin evaluaciones registradas" description="No hay evaluaciones de calidad disponibles." /> : <><TableShell><TableHead><tr><TableCell as="th">Dato</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Motivos</TableCell><TableCell as="th">Evaluación</TableCell></tr></TableHead><TableBody columns={4}>{pageRows(state.quality.data, "quality").map((item) => <tr key={item.id}><TableCell><b>{human(item.observacion_detalle?.concepto)}</b><span className="block text-xs text-[var(--text-muted)]">{item.observacion_detalle?.valor === null || item.observacion_detalle?.valor === undefined ? "Sin datos" : `${formatNumber(item.observacion_detalle.valor)} ${item.observacion_detalle?.unidad || ""}`.trim()}</span></TableCell><TableCell><State value={item.estado} /></TableCell><TableCell>{item.motivos?.join?.(", ") || "Sin observaciones"}</TableCell><TableCell>{item.automatica ? "Automática" : "Profesional"}<span className="block text-xs">{formatDateTime(item.fecha_evaluacion)}</span></TableCell></tr>)}</TableBody></TableShell>{pagination(state.quality.data, "quality", "evaluaciones")}</>}</Section>
    <Section title="Confiabilidad de fuentes" description="La prioridad de una fuente no convierte automáticamente una observación en válida.">{state.policies.status === "loading" ? <LoadingState inline label="Cargando políticas" /> : state.policies.status === "error" ? <ErrorState description="No se pudieron cargar las políticas de fuente." /> : !state.policies.data.length ? <EmptyState title="Sin políticas registradas" description="No hay reglas de prioridad de fuente disponibles." /> : <><TableShell><TableHead><tr><TableCell as="th">Concepto</TableCell><TableCell as="th">Tipo de fuente</TableCell><TableCell as="th">Prioridad</TableCell><TableCell as="th">Alcance</TableCell><TableCell as="th">Descripción</TableCell></tr></TableHead><TableBody columns={5}>{pageRows(state.policies.data, "policies").map((item) => <tr key={item.id}><TableCell>{human(item.concepto)}</TableCell><TableCell>{human(item.tipo_fuente)}</TableCell><TableCell align="center">{item.prioridad}</TableCell><TableCell align="center">{item.organizacion ? "Organización" : "Global"}</TableCell><TableCell>{item.descripcion || "Sin descripción"}</TableCell></tr>)}</TableBody></TableShell>{pagination(state.policies.data, "policies", "políticas")}</>}</Section>
  </main>;
}
