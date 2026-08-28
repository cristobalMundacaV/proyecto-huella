import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import { ArrowLeft, Plus } from "lucide-react";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import TraceabilityDrawer from "@/features/datos/components/TraceabilityDrawer";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { Alert, Button, Card, CardContent, DataQualityBadge, EmptyState, ErrorState, Input, LoadingState, Modal, PageHeader, SectionHeader, Select, StatusBadge, TableBody, TableCell, TableHead, TableShell, Textarea, Timeline, TimelineItem, TraceabilityLink } from "@/shared/ui";
import { formatDate, formatNumber } from "@/shared/utils/formatters";
import { humanizeApiError } from "@/shared/utils/apiErrors";
import {
  createMeasurement,
  createProblemAction,
  escalateProblem,
  evaluateProblem,
  getBaseSnapshot,
  getCycles,
  getHistory,
  getMeasurements,
  getProblem,
  getProblemActions,
  getProblemIndicators,
  getProblemScope,
  measureFromEngine,
  reevaluateProblem,
  selectProblemAction,
  startProblemAction,
} from "../services/improvementApi";
import { actionStatusLabel, currentAction, currentCycle, label, problemNextStep, problemStatusLabel, problemTone, resultLabel, riskLabel } from "../utils/improvementFormat";

const resource = (data = null) => ({ status: "loading", data });
const closedProblem = (state) => ["cerrada", "resuelta"].includes(state);
const professionalProblem = (state) => ["escalada_profesional", "escalada"].includes(state);
const measurementAllowed = (state) => ["implementando", "seguimiento", "en_implementacion", "en_seguimiento"].includes(state);
const resultMetricLabel = (value) => ({
  mejoro: "Mejoró según la dirección definida",
  empeoro: "Empeoró según la dirección definida",
  sin_cambio: "Sin cambio según la dirección definida",
})[value] || label(value);
const historyLabel = (value) => ({
  deteccion: "Problema detectado",
  recomendacion: "Acción propuesta",
  accion_seleccionada: "Acción seleccionada",
  inicio_implementacion: "Implementación iniciada",
  medicion: "Medición registrada",
  evaluacion_intervencion: "Resultado evaluado",
  escalamiento_profesional: "Enviado a revisión profesional",
  verificacion: "Resultado verificado",
  transicion: "Estado actualizado",
})[value] || label(value);

export default function ProblemDetailPage({ workScoped = false }) {
  const { problemId, obraId } = useParams();
  const workspace = useOutletContext() || {};
  const { activeOrganizacionId } = useOrganizacionActiva();
  const workId = workScoped ? workspace.obra?.id || workspace.obra?.obra_id : undefined;
  const [state, setState] = useState({
    scopeKey: "",
    problem: resource(),
    scope: resource([]),
    indicators: resource([]),
    actions: resource([]),
    measurements: resource([]),
    cycles: resource([]),
    history: resource([]),
    base: resource(),
  });
  const [dialog, setDialog] = useState(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [dialogError, setDialogError] = useState("");
  const [trace, setTrace] = useState(null);
  const requestRef = useRef(0);

  const load = useCallback(async () => {
    if (!activeOrganizacionId || !problemId || (workScoped && !workId)) return;
    const scopeKey = `${activeOrganizacionId}:${workScoped ? workId : "global"}:${problemId}`;
    const requestId = ++requestRef.current;
    setState({
      scopeKey,
      problem: resource(),
      scope: resource([]),
      indicators: resource([]),
      actions: resource([]),
      measurements: resource([]),
      cycles: resource([]),
      history: resource([]),
      base: resource(),
    });

    const calls = [
      getProblem(activeOrganizacionId, problemId, workId),
      getProblemScope(activeOrganizacionId, problemId, workId),
      getProblemIndicators(activeOrganizacionId, problemId, workId),
      getProblemActions(activeOrganizacionId, problemId, workId),
      getMeasurements(activeOrganizacionId, problemId, workId),
      getCycles(activeOrganizacionId, problemId, workId),
      getHistory(activeOrganizacionId, problemId, workId),
      getBaseSnapshot(activeOrganizacionId, problemId, workId),
    ];
    const results = await Promise.allSettled(calls);
    if (requestRef.current !== requestId) return;

    const names = ["problem", "scope", "indicators", "actions", "measurements", "cycles", "history", "base"];
    const resources = Object.fromEntries(results.map((result, index) => {
      const name = names[index];
      const missingBase = name === "base"
        && result.status === "rejected"
        && result.reason?.response?.status === 404
        && result.reason?.response?.data?.detail === "Snapshot BASE no disponible.";
      if (result.status === "fulfilled") return [name, { status: "ready", data: result.value }];
      if (missingBase) return [name, { status: "missing", data: null }];
      return [name, { status: "error", data: name === "problem" || name === "base" ? null : [] }];
    }));
    setState({ scopeKey, ...resources });
  }, [activeOrganizacionId, problemId, workId, workScoped]);

  useEffect(() => {
    load();
    return () => { requestRef.current += 1; };
  }, [load]);

  const problem = state.problem.data;
  const actions = state.actions.data || [];
  const measurements = useMemo(() => state.measurements.data || [], [state.measurements.data]);
  const cycles = state.cycles.data || [];
  const base = state.base.data;
  const cycle = currentCycle(cycles);
  const activeAction = currentAction(actions, cycle);
  const principal = (state.indicators.data || []).find((item) => item.rol === "principal");
  const result = cycle?.resultado_detalle || null;
  const comparison = result?.metricas_comparadas || [];
  const latestMeasurement = useMemo(() => {
    if (!measurements.length) return null;
    return [...measurements].sort((a, b) => String(b.fecha || b.created_at).localeCompare(String(a.fecha || a.created_at)))[0];
  }, [measurements]);
  const next = problemNextStep({ problem, action: activeAction, measurements, cycles });
  const closedCycles = cycles.filter((item) => item.fecha_cierre).length;
  const actionCreationAllowed = ["detectada", "analizando", "en_analisis"].includes(problem?.estado);
  const canSelectAction = state.indicators.status === "ready" && (state.indicators.data || []).length > 0;

  async function mutate(call, message) {
    setBusy(true);
    setFeedback("");
    setDialogError("");
    try {
      await call();
      setDialog(null);
      setFeedback(message);
      await load();
    } catch (error) {
      const message = humanizeApiError(error);
      if (dialog) setDialogError(message); else setFeedback(message);
    } finally {
      setBusy(false);
    }
  }

  const requestedScopeKey = activeOrganizacionId && problemId && (!workScoped || workId) ? `${activeOrganizacionId}:${workScoped ? workId : "global"}:${problemId}` : "";
  if (state.scopeKey !== requestedScopeKey || state.problem.status === "loading") return <PlatformLoader title="Cargando problemática" description="Estamos reuniendo situación inicial, acciones, mediciones e historial." />;
  if (state.problem.status === "error") return <ErrorState description="El problema no existe o no está disponible en este contexto." />;

  const back = workScoped ? `/obras/${obraId}/problemas` : "/inteligencia/problemas";
  const escalationAction = closedCycles >= 3 && !closedProblem(problem.estado) && !professionalProblem(problem.estado)
    ? <Button variant="secondary" onClick={() => setDialog({ type: "escalate", motivo: "" })}>Solicitar revisión profesional</Button>
    : null;

  const resultValue = result?.estado || problem.resultado_evaluacion;
  const baseValue = base?.valores?.[0];
  const baseSignal = state.base.status === "missing"
    ? "BASE pendiente"
    : state.base.status === "error"
      ? "No disponible"
      : baseValue
        ? `${formatNumber(baseValue.valor)} ${baseValue.unidad || ""}`.trim()
        : "Sin datos";
  const measurementSignal = latestMeasurement
    ? `${formatNumber(latestMeasurement.valor)} ${latestMeasurement.unidad || ""}`.trim()
    : "Aún sin medición";
  const actionSignal = activeAction?.titulo || "Aún sin acción seleccionada";
  const resultSignal = resultLabel(resultValue);

  function openMeasurement() {
    setDialog({
      type: "measurement",
      fecha: new Date().toISOString().slice(0, 10),
      valor: "",
      unidad: problem.unidad_indicador || "",
      fuente: "manual",
      observaciones: "",
    });
  }

  function nextActionControl() {
    if (next.type === "start" && activeAction) {
      return <Button onClick={() => setDialog({ type: "start", action: activeAction })}>Iniciar acción</Button>;
    }
    if (next.type === "measurement") {
      return <Button onClick={openMeasurement}>Agregar medición</Button>;
    }
    if (next.type === "evaluate" && measurements.length) {
      return <Button disabled={busy} onClick={() => mutate(() => evaluateProblem(activeOrganizacionId, problemId, workId), "Resultado evaluado con la información disponible.")}>Evaluar resultado</Button>;
    }
    if (next.type === "actions") {
      return <a className="text-sm font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" href="#accion">Revisar acciones</a>;
    }
    if (next.type === "professional" && closedCycles >= 3 && !professionalProblem(problem.estado)) {
      return <Button variant="secondary" onClick={() => setDialog({ type: "escalate", motivo: "" })}>Solicitar revisión profesional</Button>;
    }
    if (next.type === "result") {
      return <a className="text-sm font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" href="#seguimiento">Ver resultado</a>;
    }
    if (next.type === "review" || next.type === "evaluate") {
      return <a className="text-sm font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" href="#resumen">Revisar contexto</a>;
    }
    return null;
  }

  return <main className="space-y-7">
    <Link className="inline-flex items-center gap-2 text-sm font-bold text-[var(--text-secondary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to={back}>
      <ArrowLeft aria-hidden="true" size={16} />Problemas
    </Link>

    {workScoped ? <SectionHeader
      title={problem.titulo}
      description={problem.descripcion}
      action={escalationAction}
    /> : <PageHeader
      title={problem.titulo}
      description={problem.descripcion}
      status={<StatusBadge tone={problemTone(problem.estado)}>{problemStatusLabel(problem.estado)}</StatusBadge>}
      metadata={<span>{problem.categoria || "Sin categoría"} · Riesgo {riskLabel(problem.nivel_riesgo)} · Detectado {formatDate(problem.fecha_deteccion)}</span>}
      actions={escalationAction}
    />}

    {workScoped && <div className="flex flex-wrap items-center gap-2 text-sm text-[var(--text-secondary)]">
      <StatusBadge tone={problemTone(problem.estado)}>{problemStatusLabel(problem.estado)}</StatusBadge>
      <span>Riesgo {riskLabel(problem.nivel_riesgo)}</span>
      <span>Detectado {formatDate(problem.fecha_deteccion)}</span>
    </div>}

    {feedback && <Alert tone={String(feedback).startsWith("No ") ? "danger" : "info"}>{Array.isArray(feedback) ? feedback.join(" ") : feedback}</Alert>}

    <nav aria-label="Secciones del problema" className="flex gap-1 overflow-x-auto border-b border-[var(--border-default)]">
      {[["resumen", "Resumen"], ["accion", "Acción"], ["seguimiento", "Seguimiento"], ["historial", "Historial"]].map(([id, text]) => <a key={id} className="shrink-0 px-3 py-2 text-sm font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" href={`#${id}`}>{text}</a>)}
    </nav>

    <section id="resumen" className="space-y-4">
      <Card>
        <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">Siguiente paso</p>
            <h2 className="mt-1 text-xl font-bold">{next.title}</h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">{next.description}</p>
          </div>
          {nextActionControl()}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card><CardContent>
          <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">{cycle?.fecha_cierre ? "Acción del último ciclo" : "Acción actual"}</p>
          <p className="mt-2 font-bold">{actionSignal}</p>
          {activeAction?.justificacion && <p className="mt-2 text-sm text-[var(--text-secondary)]">{activeAction.justificacion}</p>}
        </CardContent></Card>
        <Card><CardContent>
          <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">Resultado</p>
          <p className="mt-2 font-bold">{resultSignal}</p>
          {result?.conclusion_estructurada && <p className="mt-2 text-sm text-[var(--text-secondary)]">{result.conclusion_estructurada.texto || result.conclusion_estructurada.resumen}</p>}
        </CardContent></Card>
      </div>

      <details className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
        <summary className="cursor-pointer p-4 font-bold">Contexto del problema</summary>
        <div className="space-y-5 border-t border-[var(--border-subtle)] p-4">
          <ResourceSection title="Alcance" state={state.scope}>
            {!state.scope.data?.length ? <p className="text-sm text-[var(--text-muted)]">No hay alcance adicional registrado.</p> : <div className="grid gap-3 sm:grid-cols-2">
              {state.scope.data.map((item) => <Card key={item.id}><CardContent>
                <dl className="grid grid-cols-2 gap-2 text-sm">
                  <dt className="text-[var(--text-muted)]">Unidad</dt><dd>{item.unidad_operacional ? "Vinculada" : "No vinculada"}</dd>
                  <dt className="text-[var(--text-muted)]">Proceso</dt><dd>{item.proceso_operacional ? "Vinculado" : "No vinculado"}</dd>
                  <dt className="text-[var(--text-muted)]">Activo</dt><dd>{item.activo_operacional ? "Vinculado" : "No vinculado"}</dd>
                  <dt className="text-[var(--text-muted)]">Actividad</dt><dd>{item.actividad_operacional ? "Vinculada" : "No vinculada"}</dd>
                </dl>
              </CardContent></Card>)}
            </div>}
          </ResourceSection>

          <ResourceSection title="Indicadores" state={state.indicators}>
            {!state.indicators.data?.length ? <p className="text-sm text-[var(--text-muted)]">No hay indicadores asociados.</p> : <TableShell>
              <TableHead><tr><TableCell as="th">Indicador</TableCell><TableCell as="th">Rol</TableCell><TableCell as="th">Meta</TableCell><TableCell as="th">Dirección</TableCell><TableCell as="th">BASE</TableCell></tr></TableHead>
              <TableBody columns={5}>{state.indicators.data.map((item) => {
                const snapshotValue = base?.valores?.find((value) => String(value.indicador) === String(item.indicador));
                return <tr key={item.id}>
                  <TableCell className="font-bold">{item.indicador_nombre || "Indicador"}</TableCell>
                  <TableCell>{label(item.rol)}</TableCell>
                  <TableCell>{item.valor_objetivo === null || item.valor_objetivo === undefined ? "Sin datos" : formatNumber(item.valor_objetivo)}</TableCell>
                  <TableCell>{label(item.direccion_deseada)}</TableCell>
                  <TableCell>{snapshotValue ? `${formatNumber(snapshotValue.valor)} ${snapshotValue.unidad || ""}`.trim() : state.base.status === "missing" ? "BASE pendiente" : "Sin datos"}</TableCell>
                </tr>;
              })}</TableBody>
            </TableShell>}
          </ResourceSection>
        </div>
      </details>
    </section>

    <section id="accion" className="space-y-4">
      <SectionHeader
        title="Acción"
        description="La acción elegida es una intervención; implementarla no demuestra por sí sola una mejora."
        action={actionCreationAllowed ? <Button leftIcon={Plus} onClick={() => setDialog({ type: "action", titulo: "", descripcion: "", justificacion: "", responsable: "", fecha_objetivo: "" })}>Proponer acción</Button> : undefined}
      />
      {state.indicators.status === "ready" && !canSelectAction && actions.some((action) => ["propuesta", "ajustada"].includes(action.estado)) && <Alert tone="warning">Para seleccionar una acción, el problema necesita al menos un indicador asociado.</Alert>}
      {state.actions.status === "loading" ? <LoadingState label="Cargando acciones" /> : state.actions.status === "error" ? <ErrorState description="No fue posible cargar las acciones. Las demás secciones permanecen disponibles." /> : !actions.length ? <EmptyState title="No hay acciones propuestas." description="Puedes registrar una alternativa cuando exista una decisión operacional que evaluar." /> : <>
        {activeAction && <Card><CardContent>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div><h3 className="text-lg font-bold">{activeAction.titulo}</h3><p className="mt-1 text-sm text-[var(--text-secondary)]">{activeAction.descripcion}</p></div>
            <StatusBadge tone={["implementada", "evaluada"].includes(activeAction.estado) ? "success" : ["descartada", "cancelada"].includes(activeAction.estado) ? "neutral" : "info"}>{actionStatusLabel(activeAction.estado)}</StatusBadge>
          </div>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-[var(--text-muted)]">
            <span>Responsable: {activeAction.responsable || "Sin asignar"}</span>
            <span>Fecha objetivo: {activeAction.fecha_objetivo ? formatDate(activeAction.fecha_objetivo) : "Sin fecha"}</span>
          </div>
          {activeAction.justificacion && <p className="mt-3 text-sm"><b>Justificación:</b> {activeAction.justificacion}</p>}
        </CardContent></Card>}

        {actions.filter((action) => action.id !== activeAction?.id).length > 0 && <details>
          <summary className="cursor-pointer font-bold text-[var(--text-secondary)]">Otras acciones propuestas</summary>
          <div className="mt-3 space-y-3">
            {actions.filter((action) => action.id !== activeAction?.id).map((action) => <Card key={action.id}><CardContent className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div><h3 className="font-bold">{action.titulo}</h3><p className="mt-1 text-sm text-[var(--text-secondary)]">{action.descripcion}</p><p className="mt-2 text-xs text-[var(--text-muted)]">{actionStatusLabel(action.estado)}</p></div>
              <div className="flex shrink-0 flex-wrap gap-2">
                {cycle?.fecha_cierre && cycles.length < 3 && !closedProblem(problem.estado) && <Button size="sm" variant="secondary" disabled={!canSelectAction} onClick={() => mutate(() => reevaluateProblem(activeOrganizacionId, problemId, action.id, workId), "Nuevo ciclo creado sin sobrescribir el anterior.")}>Nuevo ciclo con esta acción</Button>}
                {!cycle?.fecha_cierre && ["propuesta", "ajustada"].includes(action.estado) && !closedProblem(problem.estado) && <Button size="sm" disabled={!canSelectAction} onClick={() => mutate(() => selectProblemAction(activeOrganizacionId, problemId, action.id, workId), "Acción seleccionada. La situación BASE quedó preparada para este ciclo.")}>Seleccionar</Button>}
              </div>
            </CardContent></Card>)}
          </div>
        </details>}
      </>}
    </section>

    <section id="seguimiento" className="space-y-5">
      <SectionHeader title="Seguimiento" description="La secuencia de verificación es BASE → Acción → Medición → RESULT." />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["BASE", baseSignal],
          ["Acción", actionSignal],
          ["Medición", measurementSignal],
          ["RESULT", resultSignal],
        ].map(([title, value]) => <Card key={title}><CardContent><p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">{title}</p><p className="mt-2 font-bold">{value}</p></CardContent></Card>)}
      </div>

      {result && <Card><CardContent>
        <div className="flex flex-wrap items-center gap-2"><h3 className="font-bold">Evaluación registrada</h3><StatusBadge tone={result.estado === "positiva" ? "success" : result.estado === "negativa" ? "danger" : "warning"}>{resultLabel(result.estado)}</StatusBadge></div>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">{result.conclusion_estructurada?.texto || result.conclusion_estructurada?.resumen || "El resultado fue evaluado con las reglas definidas para sus indicadores."}</p>
        {!!result.limitaciones?.length && <details className="mt-3 text-sm"><summary className="cursor-pointer font-bold">Limitaciones de la evaluación</summary><ul className="mt-2 list-disc space-y-1 pl-5">{result.limitaciones.map((item, index) => <li key={`lim-${index}`}>{item}</li>)}</ul></details>}
      </CardContent></Card>}

      {!!comparison.length && <TableShell>
        <TableHead><tr><TableCell as="th">Indicador</TableCell><TableCell as="th">BASE</TableCell><TableCell as="th">RESULT</TableCell><TableCell as="th">Conclusión</TableCell></tr></TableHead>
        <TableBody columns={4}>{comparison.map((metric, index) => <tr key={`${metric.indicador || index}`}>
          <TableCell>{metric.nombre || principal?.indicador_nombre || "Indicador"}</TableCell>
          <TableCell>{metric.base === null || metric.base === undefined ? "Sin datos" : formatNumber(metric.base)} {metric.unidad || ""}</TableCell>
          <TableCell>{metric.resultado === null || metric.resultado === undefined ? "Sin datos" : formatNumber(metric.resultado)} {metric.unidad || ""}</TableCell>
          <TableCell>{resultMetricLabel(metric.estado)}</TableCell>
        </tr>)}</TableBody>
      </TableShell>}

      <ResourceSection title="Mediciones" state={state.measurements} action={measurementAllowed(problem.estado) ? <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => mutate(() => measureFromEngine(activeOrganizacionId, problemId, workId), "Medición obtenida desde los datos disponibles.")}>Obtener desde datos actuales</Button>
        <Button onClick={openMeasurement}>Agregar medición</Button>
      </div> : undefined}>
        {!measurements.length ? <EmptyState title="No hay mediciones de seguimiento." description="Una acción implementada todavía no demuestra un resultado." /> : <TableShell>
          <TableHead><tr><TableCell as="th">Fecha</TableCell><TableCell as="th">Valor</TableCell><TableCell as="th">Fuente</TableCell><TableCell as="th">Calidad / origen</TableCell></tr></TableHead>
          <TableBody columns={4}>{measurements.map((item) => <tr key={item.id}>
            <TableCell>{formatDate(item.fecha)}</TableCell>
            <TableCell>{item.valor === null || item.valor === undefined ? "Sin datos" : formatNumber(item.valor)} {item.unidad || ""}</TableCell>
            <TableCell>{item.fuente === "manual" ? "Manual / declarado" : label(item.fuente)}</TableCell>
            <TableCell>
              {item.metadata?.calidad && <DataQualityBadge label={item.metadata.calidad} />}
              {item.evidencia && <TraceabilityLink onClick={() => setTrace({
                concepto: problem.indicador,
                valor_numerico: item.valor,
                unidad: item.unidad,
                estado: item.metadata?.calidad,
                metodo_captura: item.fuente,
                evidencia_detalle: { id: item.evidencia, nombre: "Evidencia vinculada" },
              })} />}
              {!item.metadata?.calidad && !item.evidencia && "Sin origen adicional"}
            </TableCell>
          </tr>)}</TableBody>
        </TableShell>}
      </ResourceSection>
    </section>

    <ResourceSection id="historial" title="Historial" state={state.history}>
      {cycles.length > 0 && <div className="mb-5 grid gap-3 md:grid-cols-2">
        {cycles.map((item) => {
          const action = actions.find((candidate) => String(candidate.id) === String(item.accion));
          return <Card key={item.id}><CardContent>
            <h3 className="font-bold">Ciclo {item.numero}</h3>
            <p className="mt-1 text-sm">{action?.titulo || "Acción registrada"}</p>
            <p className="mt-1 text-sm text-[var(--text-muted)]">Inicio {formatDate(item.fecha_inicio)} · {item.fecha_cierre ? `Cierre ${formatDate(item.fecha_cierre)}` : "En curso"}</p>
            <p className="mt-2 text-sm">Resultado: {resultLabel(item.resultado_detalle?.estado)}</p>
          </CardContent></Card>;
        })}
      </div>}
      {state.history.data?.length ? <Timeline>
        {state.history.data.map((item) => <TimelineItem key={item.id} timestamp={formatDate(item.created_at)} title={historyLabel(item.evento)} description={item.detalle || (item.estado_nuevo ? problemStatusLabel(item.estado_nuevo) : undefined)} />)}
      </Timeline> : <EmptyState title="Sin eventos registrados." description="El historial aparecerá cuando existan cambios reales." />}
    </ResourceSection>

    <ProblemDialog
      dialog={dialog}
      error={dialogError}
      busy={busy}
      onClose={() => { if (!busy) { setDialog(null); setDialogError(""); } }}
      onSubmit={(payload) => {
        if (dialog.type === "start") return mutate(() => startProblemAction(activeOrganizacionId, problemId, dialog.action.id, workId), "Acción iniciada. La situación BASE quedó congelada para este ciclo.");
        if (dialog.type === "escalate") return mutate(() => escalateProblem(activeOrganizacionId, problemId, payload.motivo, workId), "Problema enviado a revisión profesional.");
        if (dialog.type === "action") return mutate(() => createProblemAction(activeOrganizacionId, problemId, payload, workId), "Acción propuesta; todavía no representa una mejora.");
        return mutate(() => createMeasurement(activeOrganizacionId, problemId, payload, workId), "Medición manual registrada.");
      }}
      onChange={setDialog}
    />
    <TraceabilityDrawer observation={trace} open={Boolean(trace)} onClose={() => setTrace(null)} workId={obraId} />
  </main>;
}

function ResourceSection({ id = undefined, title, state, action = null, children }) {
  return <section id={id}>
    <SectionHeader title={title} action={action} />
    {state.status === "loading"
      ? <LoadingState label={`Cargando ${title.toLowerCase()}`} />
      : state.status === "error"
        ? <ErrorState description={`No fue posible cargar ${title.toLowerCase()}. Las demás secciones permanecen disponibles.`} />
        : children}
  </section>;
}

function ProblemDialog({ dialog, busy, error, onClose, onSubmit, onChange }) {
  if (!dialog) return null;
  const titles = {
    start: "Iniciar acción",
    escalate: "Solicitar revisión profesional",
    action: "Proponer acción",
    measurement: "Agregar medición manual",
  };
  return <Modal
    open
    eyebrow="MEJORA CONTINUA"
    icon={Plus}
    title={titles[dialog.type]}
    description={dialog.type === "start" ? "Al confirmar, la situación BASE del ciclo quedará congelada para poder comparar el resultado después." : undefined}
    onClose={onClose}
    footer={<div className="flex justify-end gap-2"><Button variant="secondary" disabled={busy} onClick={onClose}>Cancelar</Button><Button loading={busy} onClick={() => onSubmit(dialog)}>{dialog.type === "start" ? "Confirmar inicio" : dialog.type === "escalate" ? "Enviar a revisión" : dialog.type === "action" ? "Crear acción" : "Registrar medición"}</Button></div>}
  >
    {error && <Alert tone="danger" title="No pudimos completar la acción">{error}</Alert>}
    {dialog.type === "start" ? <Alert tone="warning">Iniciar la acción no significa que el problema esté resuelto. El resultado deberá verificarse después.</Alert>
      : dialog.type === "escalate" ? <Textarea required label="Motivo de la revisión" value={dialog.motivo} onChange={(event) => onChange({ ...dialog, motivo: event.target.value })} />
        : dialog.type === "action" ? <div className="space-y-4">
          <Input required label="Título" value={dialog.titulo} onChange={(event) => onChange({ ...dialog, titulo: event.target.value })} />
          <Textarea required label="Descripción" value={dialog.descripcion} onChange={(event) => onChange({ ...dialog, descripcion: event.target.value })} />
          <Textarea label="Justificación" value={dialog.justificacion} onChange={(event) => onChange({ ...dialog, justificacion: event.target.value })} />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Responsable" value={dialog.responsable} onChange={(event) => onChange({ ...dialog, responsable: event.target.value })} />
            <Input type="date" label="Fecha objetivo" value={dialog.fecha_objetivo} onChange={(event) => onChange({ ...dialog, fecha_objetivo: event.target.value })} />
          </div>
        </div>
          : <div className="grid gap-4 sm:grid-cols-2">
            <Input required type="date" label="Fecha" value={dialog.fecha} onChange={(event) => onChange({ ...dialog, fecha: event.target.value })} />
            <Input required type="number" step="any" label="Valor" value={dialog.valor} onChange={(event) => onChange({ ...dialog, valor: event.target.value })} />
            <Input required label="Unidad" value={dialog.unidad} onChange={(event) => onChange({ ...dialog, unidad: event.target.value })} />
            <Select label="Origen" value={dialog.fuente} onChange={(event) => onChange({ ...dialog, fuente: event.target.value })}><option value="manual">Manual / declarado</option></Select>
            <div className="sm:col-span-2"><Textarea label="Observaciones" value={dialog.observaciones} onChange={(event) => onChange({ ...dialog, observaciones: event.target.value })} /></div>
          </div>}
  </Modal>;
}
