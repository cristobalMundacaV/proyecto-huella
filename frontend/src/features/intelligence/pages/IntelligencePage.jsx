import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { Card, CardContent, EmptyState, ErrorState, LoadingState, PageHeader, SectionHeader, StatusBadge } from "@/shared/ui";
import { getEnvironmentalDecisionPriorities } from "@/features/environmental/services/environmentalDecisionPriorityApi";
import { getEnvironmentalRecommendations } from "@/features/environmental/services/environmentalRecommendationApi";
import { getEnvironmentalScenarios } from "@/features/environmental/services/environmentalScenarioApi";

const resource = () => ({ status: "loading", data: [] });
const priorityTone = (value) => value === "critica" ? "danger" : value === "alta" ? "warning" : value === "media" ? "info" : "neutral";
const priorityLabel = (value) => ({ critica: "Crítica", alta: "Alta", media: "Media", baja: "Baja" })[value] || String(value || "").replaceAll("_", " ");
const scenarioStatus = (value) => ({
  available: ["Disponible", "info"],
  partial: ["Información parcial", "warning"],
  missing: ["Faltan datos", "neutral"],
})[value] || [String(value || "").replaceAll("_", " "), "neutral"];

function ResourceState({ resourceState, loading, error, children }) {
  if (resourceState.status === "loading") return <LoadingState label={loading} />;
  if (resourceState.status === "error") return <ErrorState description={error} />;
  return children;
}

export default function IntelligencePage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ scopeKey: "", priorities: resource(), recommendations: resource(), scenarios: resource() });
  const requestRef = useRef(0);

  useEffect(() => {
    if (!activeOrganizacionId) return undefined;
    const requestId = ++requestRef.current;
    const scopeKey = String(activeOrganizacionId);
    setState({ scopeKey, priorities: resource(), recommendations: resource(), scenarios: resource() });

    Promise.allSettled([
      getEnvironmentalDecisionPriorities(activeOrganizacionId),
      getEnvironmentalRecommendations(activeOrganizacionId),
      getEnvironmentalScenarios(activeOrganizacionId),
    ]).then(([priorities, recommendations, scenarios]) => {
      if (requestRef.current !== requestId) return;
      setState({
        scopeKey,
        priorities: priorities.status === "fulfilled"
          ? { status: "ready", data: priorities.value?.priorities || [] }
          : { status: "error", data: [] },
        recommendations: recommendations.status === "fulfilled"
          ? { status: "ready", data: recommendations.value?.recommendations || [] }
          : { status: "error", data: [] },
        scenarios: scenarios.status === "fulfilled"
          ? { status: "ready", data: scenarios.value?.scenarios || [] }
          : { status: "error", data: [] },
      });
    });

    return () => { requestRef.current += 1; };
  }, [activeOrganizacionId]);

  const currentScopeKey = String(activeOrganizacionId || "");
  if (state.scopeKey !== currentScopeKey) return <LoadingState label="Cargando inteligencia" />;

  const priorities = state.priorities.data.slice(0, 5);
  const recommendations = state.recommendations.data.slice(0, 3);
  const scenarios = state.scenarios.data.slice(0, 3);
  const allReady = [state.priorities, state.recommendations, state.scenarios].every((item) => item.status === "ready");
  const noSignals = allReady && !priorities.length && !recommendations.length && !scenarios.length;

  return <main className="space-y-8">
    <PageHeader
      title="Inteligencia"
      description="Señales y análisis que pueden ayudarte a decidir dónde profundizar."
      actions={<>
        <Link className="rounded-lg border border-[var(--border-default)] px-4 py-2 text-sm font-bold focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to="/inteligencia/problemas">Ver problemas</Link>
        <Link className="rounded-lg bg-[var(--brand-primary)] px-4 py-2 text-sm font-bold text-white focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to="/inteligencia/copiloto">Abrir Copiloto</Link>
      </>}
    />

    {noSignals && <EmptyState title="No hay señales nuevas con los datos disponibles." description="La ausencia de señales no certifica que todo esté resuelto." />}

    {(state.priorities.status !== "ready" || priorities.length > 0) && <section>
      <SectionHeader title="Qué merece atención" description="Prioridades construidas a partir de señales ya disponibles." />
      <ResourceState resourceState={state.priorities} loading="Cargando prioridades" error="No fue posible cargar las prioridades. Las demás señales permanecen disponibles.">
        {!priorities.length ? <EmptyState title="No hay prioridades nuevas." description="Recomendaciones y escenarios pueden seguir aportando contexto." /> : <div className="space-y-3">
          {priorities.map((item) => <Card key={item.id}>
            <CardContent className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-bold">{item.title || "Prioridad ambiental"}</h2>
                  {item.priority && <StatusBadge tone={priorityTone(item.priority)}>{priorityLabel(item.priority)}</StatusBadge>}
                </div>
                <p className="mt-2 text-sm text-[var(--text-secondary)]">{item.why_now || "Sin explicación adicional."}</p>
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--text-muted)]">
                  {item.area && <span>Área: {String(item.area).replaceAll("_", " ")}</span>}
                  {item.next_step && <span>Siguiente paso: {item.next_step}</span>}
                </div>
                {(item.technical_basis || item.evidence?.length) && <details className="mt-3 text-sm">
                  <summary className="cursor-pointer font-bold text-[var(--text-secondary)]">Detalles considerados</summary>
                  {item.technical_basis && <p className="mt-2 text-[var(--text-secondary)]">{item.technical_basis}</p>}
                  {!!item.evidence?.length && <ul className="mt-2 list-disc space-y-1 pl-5 text-[var(--text-muted)]">{item.evidence.slice(0, 4).map((value, index) => <li key={`${item.id}-e-${index}`}>{value}</li>)}</ul>}
                </details>}
              </div>
              <Link className="shrink-0 text-sm font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to={item.problematica ? `/inteligencia/problemas/${item.problematica}` : "/inteligencia/problemas"}>
                {item.problematica ? "Ver problema" : "Revisar problemas"}
              </Link>
            </CardContent>
          </Card>)}
        </div>}
      </ResourceState>
    </section>}

    {(state.recommendations.status !== "ready" || recommendations.length > 0) && <section>
      <SectionHeader title="Recomendaciones" description="Alternativas sugeridas para revisar; todavía no son acciones implementadas." />
      <ResourceState resourceState={state.recommendations} loading="Cargando recomendaciones" error="No fue posible cargar las recomendaciones. Las prioridades y escenarios permanecen disponibles.">
        {!recommendations.length ? <EmptyState title="No hay recomendaciones disponibles." description="La sección permanece vacía hasta que existan señales suficientes." /> : <div className="grid gap-4 lg:grid-cols-3">
          {recommendations.map((item) => <Card key={item.id}><CardContent>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h3 className="font-bold">{item.title || "Recomendación"}</h3>
              {item.severity && <StatusBadge tone={priorityTone(item.severity)}>{priorityLabel(item.severity)}</StatusBadge>}
            </div>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">{item.technical_recommendation || item.diagnosis || "Sin detalle adicional."}</p>
            {item.source?.label && <p className="mt-3 text-xs text-[var(--text-muted)]">Origen: {item.source.label}</p>}
            {(item.evidence?.length || item.decision_required || item.expected_impact) && <details className="mt-3 text-sm">
              <summary className="cursor-pointer font-bold text-[var(--text-secondary)]">Ver contexto</summary>
              {item.decision_required && <p className="mt-2"><b>Decisión a revisar:</b> {item.decision_required}</p>}
              {item.expected_impact && <p className="mt-2"><b>Impacto esperado:</b> {item.expected_impact}</p>}
            </details>}
          </CardContent></Card>)}
        </div>}
      </ResourceState>
    </section>}

    {(state.scenarios.status !== "ready" || scenarios.length > 0) && <section>
      <SectionHeader title="Escenarios disponibles" description="Comparaciones para explorar después de revisar las señales principales." />
      <ResourceState resourceState={state.scenarios} loading="Cargando escenarios" error="No fue posible cargar los escenarios. Las prioridades y recomendaciones permanecen disponibles.">
        {!scenarios.length ? <EmptyState title="No hay escenarios disponibles." description="No se crean alternativas de relleno cuando faltan datos." /> : <div className="grid gap-4 lg:grid-cols-3">
          {scenarios.map((item) => {
            const [status, tone] = scenarioStatus(item.status);
            return <Card key={item.id}><CardContent>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h3 className="font-bold">{item.title || "Escenario"}</h3>
                {item.status && <StatusBadge tone={tone}>{status}</StatusBadge>}
              </div>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">{item.reason || "Sin descripción adicional."}</p>
              {item.scenario_value !== null && item.scenario_value !== undefined && <p className="mt-3 font-bold">{item.scenario_value} {item.unit || ""}</p>}
              {item.decision_hint && <details className="mt-3 text-sm"><summary className="cursor-pointer font-bold text-[var(--text-secondary)]">Qué revisar</summary><p className="mt-2">{item.decision_hint}</p></details>}
            </CardContent></Card>;
          })}
        </div>}
      </ResourceState>
    </section>}
  </main>;
}
