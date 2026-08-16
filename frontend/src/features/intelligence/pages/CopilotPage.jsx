import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { Alert, Button, Card, CardContent, EmptyState, ErrorState, LoadingState, Modal, PageHeader, Select, StatusBadge, Textarea } from "@/shared/ui";
import { listProblems } from "@/features/mejora/services/improvementApi";
import { problemStatusLabel } from "@/features/mejora/utils/improvementFormat";
import { confirmCommand, createProposal, getProblemContext, getProposals, sendFeedback } from "../services/copilotApi";

const resource = (status = "idle", data = null) => ({ status, data });
const proposalStatus = (value) => ({
  propuesta: ["Propuesta", "info"],
  ajustada: ["Ajustada", "info"],
  aceptada: ["Preparada para confirmar", "warning"],
  rechazada: ["Rechazada", "neutral"],
  descartada: ["Descartada", "neutral"],
})[value] || [String(value || "").replaceAll("_", " "), "neutral"];

export default function CopilotPage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const [problems, setProblems] = useState({ scopeKey: "", status: "loading", data: [], error: "" });
  const [problemId, setProblemId] = useState("");
  const [resources, setResources] = useState({ scopeKey: "", context: resource(), proposals: resource() });
  const [message, setMessage] = useState("");
  const [dialog, setDialog] = useState(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const problemsRequestRef = useRef(0);
  const resourceRequestRef = useRef(0);

  useEffect(() => {
    if (!activeOrganizacionId) return undefined;
    const requestId = ++problemsRequestRef.current;
    resourceRequestRef.current += 1;
    setProblemId("");
    const scopeKey = String(activeOrganizacionId);
    setProblems({ scopeKey, status: "loading", data: [], error: "" });
    setResources({ scopeKey: "", context: resource(), proposals: resource() });

    listProblems(activeOrganizacionId)
      .then((items) => {
        if (problemsRequestRef.current !== requestId) return;
        setProblems({ scopeKey, status: "ready", data: items, error: "" });
        setProblemId(String(items[0]?.id || ""));
      })
      .catch(() => {
        if (problemsRequestRef.current === requestId) {
          setProblems({ scopeKey, status: "error", data: [], error: "No fue posible cargar los problemas." });
        }
      });

    return () => {
      problemsRequestRef.current += 1;
      resourceRequestRef.current += 1;
    };
  }, [activeOrganizacionId]);

  const load = useCallback(() => {
    if (!problemId) {
      setResources({ scopeKey: "", context: resource(), proposals: resource() });
      return Promise.resolve();
    }
    const scopeKey = `${activeOrganizacionId}:${problemId}`;
    const requestId = ++resourceRequestRef.current;
    setResources({ scopeKey, context: resource("loading"), proposals: resource("loading", []) });

    return Promise.allSettled([getProblemContext(problemId), getProposals(problemId)]).then(([context, proposals]) => {
      if (resourceRequestRef.current !== requestId) return;
      setResources({
        scopeKey,
        context: context.status === "fulfilled"
          ? { status: "ready", data: context.value }
          : { status: "error", data: null },
        proposals: proposals.status === "fulfilled"
          ? { status: "ready", data: proposals.value || [] }
          : { status: "error", data: [] },
      });
    });
  }, [activeOrganizacionId, problemId]);

  useEffect(() => {
    setMessage("");
    setActionError("");
    load();
    return () => { resourceRequestRef.current += 1; };
  }, [load]);

  async function propose() {
    if (!problemId || resources.scopeKey !== `${activeOrganizacionId}:${problemId}` || resourceState.context.status !== "ready" || !message.trim()) return;
    setBusy(true);
    setActionError("");
    try {
      await createProposal(problemId, message.trim());
      setMessage("");
      await load();
    } catch (error) {
      setActionError(error?.response?.data?.detail || "No se pudo preparar una propuesta.");
    } finally {
      setBusy(false);
    }
  }

  async function feedback(proposal, decision, explanation = "") {
    setBusy(true);
    setActionError("");
    try {
      const result = await sendFeedback(problemId, proposal.id, decision, explanation);
      if (result.requiere_confirmacion && result.comando) {
        setDialog({ type: "command", command: result.comando, proposal });
      } else {
        setDialog(null);
        await load();
      }
    } catch (error) {
      setActionError(error?.response?.data?.detail || "No se pudo registrar esta decisión.");
    } finally {
      setBusy(false);
    }
  }

  async function submitDialog() {
    if (!dialog) return;
    if (dialog.type === "refute") {
      if (!dialog.message?.trim()) return;
      return feedback(dialog.proposal, "refutar", dialog.message.trim());
    }

    setBusy(true);
    setActionError("");
    try {
      await confirmCommand(dialog.command);
      setDialog(null);
      await load();
    } catch (error) {
      setActionError(error?.response?.data?.detail || "No se pudo crear la acción formal.");
    } finally {
      setBusy(false);
    }
  }

  const organizationScopeKey = String(activeOrganizacionId || "");
  const problemsState = problems.scopeKey === organizationScopeKey ? problems : { scopeKey: organizationScopeKey, status: "loading", data: [], error: "" };
  const resourceScopeKey = problemId ? `${activeOrganizacionId}:${problemId}` : "";
  const resourceState = resources.scopeKey === resourceScopeKey ? resources : { scopeKey: resourceScopeKey, context: resource("loading"), proposals: resource("loading", []) };

  return <main className="space-y-6">
    <PageHeader
      title="Copiloto ambiental"
      description="Consulta el contexto de un problema y revisa propuestas antes de convertirlas en acciones."
    />

    {problemsState.status === "loading" ? <LoadingState label="Cargando problemas" /> : problemsState.status === "error" ? <ErrorState description={problemsState.error} /> : !problemsState.data.length ? <EmptyState
      title="No hay problemas disponibles para consultar."
      description="El Copiloto trabaja sobre un problema real y acotado."
      primaryAction={<Link className="font-bold text-[var(--brand-primary)]" to="/inteligencia/problemas">Ver problemas</Link>}
    /> : <>
      <Select label="Problema" value={problemId} onChange={(event) => setProblemId(event.target.value)}>
        {problemsState.data.map((item) => <option key={item.id} value={item.id}>{item.titulo} · {problemStatusLabel(item.estado)}</option>)}
      </Select>

      {actionError && <Alert tone="danger">{Array.isArray(actionError) ? actionError.join(" ") : actionError}</Alert>}

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px]">
        <section className="space-y-4">
          <Card><CardContent>
            <Textarea
              label="¿Qué necesitas entender?"
              placeholder="Por ejemplo: ¿qué restricciones debería revisar antes de decidir?"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
            />
            {resourceState.context.status === "error" && <div className="mt-3"><Alert tone="warning">El contexto no está disponible. Puedes revisar propuestas anteriores, pero no preparar una nueva hasta recuperar el contexto.</Alert></div>}
            <Button
              className="mt-3"
              disabled={!message.trim() || resourceState.context.status !== "ready"}
              loading={busy}
              onClick={propose}
            >
              Preparar propuesta
            </Button>
          </CardContent></Card>

          {resourceState.proposals.status === "loading" ? <LoadingState label="Cargando propuestas" /> : resourceState.proposals.status === "error" ? <ErrorState description="No fue posible cargar las propuestas. El contexto del problema puede seguir disponible." /> : !resourceState.proposals.data.length ? <EmptyState
            title="No hay propuestas para este problema."
            description="Cuando tengas una pregunta concreta, puedes preparar una propuesta usando el contexto disponible."
          /> : resourceState.proposals.data.map((proposal) => {
            const [status, tone] = proposalStatus(proposal.estado);
            return <Card key={proposal.id}><CardContent>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <h2 className="font-bold">{proposal.titulo || "Propuesta"}</h2>
                <StatusBadge tone={tone}>{status}</StatusBadge>
              </div>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">{proposal.justificacion || proposal.descripcion || "Sin explicación adicional."}</p>
              {!!proposal.restricciones_consideradas?.length && <p className="mt-3 text-sm"><b>Restricciones consideradas:</b> {proposal.restricciones_consideradas.slice(0, 3).join(", ")}</p>}

              {(proposal.kpis_afectados?.length || proposal.referencias_contexto?.length || proposal.requisitos?.length || proposal.riesgos?.length) && <details className="mt-3 text-sm">
                <summary className="cursor-pointer font-bold text-[var(--text-secondary)]">Detalles considerados</summary>
                {!!proposal.requisitos?.length && <p className="mt-2"><b>Requisitos:</b> {proposal.requisitos.join(", ")}</p>}
                {!!proposal.riesgos?.length && <p className="mt-2"><b>Riesgos:</b> {proposal.riesgos.join(", ")}</p>}
                {!!proposal.kpis_afectados?.length && <p className="mt-2"><b>Indicadores:</b> {proposal.kpis_afectados.join(", ")}</p>}
                {!!proposal.referencias_contexto?.length && <p className="mt-2"><b>Referencias:</b> {proposal.referencias_contexto.join(", ")}</p>}
              </details>}

              {["propuesta", "ajustada"].includes(proposal.estado) && <div className="mt-4 flex flex-wrap gap-2">
                <Button size="sm" onClick={() => feedback(proposal, "aceptar")}>Preparar acción</Button>
                <Button size="sm" variant="secondary" onClick={() => setDialog({ type: "refute", proposal, message: "" })}>Indicar por qué no aplica</Button>
                <Button size="sm" variant="ghost" onClick={() => feedback(proposal, "rechazar")}>Rechazar</Button>
              </div>}
            </CardContent></Card>;
          })}
        </section>

        <aside>
          <Card><CardContent>
            <h2 className="font-bold">Contexto utilizado</h2>
            {resourceState.context.status === "loading" ? <div className="mt-3"><LoadingState label="Cargando contexto" /></div> : resourceState.context.status === "error" ? <p className="mt-3 text-sm text-[var(--text-muted)]">Contexto no disponible.</p> : resourceState.context.status === "ready" ? <>
              <p className="mt-3 text-sm">Indicadores: {resourceState.context.data?.kpis?.length ?? 0}</p>
              <p className="text-sm">Acciones anteriores: {resourceState.context.data?.acciones_probadas?.length ?? 0}</p>
              <p className="text-sm">Restricciones: {resourceState.context.data?.restricciones?.length ?? 0}</p>
              <p className="text-sm">Evidencias resumidas: {resourceState.context.data?.evidencia?.totales?.evidencias ?? 0}</p>
            </> : null}
            <p className="mt-3 text-xs text-[var(--text-muted)]">Las propuestas se basan en referencias estructuradas del problema; cualquier acción requiere una decisión humana explícita.</p>
            <Link className="mt-4 inline-flex text-sm font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to={`/inteligencia/problemas/${problemId}`}>Ver problema</Link>
          </CardContent></Card>
        </aside>
      </div>
    </>}

    <Modal
      open={Boolean(dialog)}
      title={dialog?.type === "command" ? "Confirmar creación de acción" : "Indicar por qué no aplica"}
      description={dialog?.type === "command"
        ? "Se creará una acción formal a partir de esta propuesta. La propuesta por sí sola no ejecuta ninguna intervención."
        : "Describe la restricción o corrección que debe considerarse antes de preparar otra alternativa."}
      onClose={() => { const wasCommand = dialog?.type === "command"; setDialog(null); if (wasCommand) load(); }}
      footer={<div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={() => { const wasCommand = dialog?.type === "command"; setDialog(null); if (wasCommand) load(); }}>Cancelar</Button>
        <Button disabled={dialog?.type === "refute" && !dialog?.message?.trim()} loading={busy} onClick={submitDialog}>{dialog?.type === "command" ? "Crear acción" : "Guardar restricción"}</Button>
      </div>}
    >
      {dialog?.type === "command"
        ? <Alert tone="warning">La acción sólo se creará después de esta confirmación.</Alert>
        : <Textarea required label="Motivo o restricción" value={dialog?.message || ""} onChange={(event) => setDialog({ ...dialog, message: event.target.value })} />}
    </Modal>
  </main>;
}
