import { useEffect, useRef, useState } from "react";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { getKnowledgeAggregate, getKnowledgeCases } from "@/features/knowledge/api/knowledgeApi";
import { Card, CardContent, EmptyState, ErrorState, LoadingState, PageHeader, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";
import { human, State } from "../components/GovernanceShared";

const resource = (status = "loading", data = null) => ({ status, data });

export default function KnowledgePage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ scopeKey: "", cases: resource("loading", []), aggregate: resource() });
  const requestRef = useRef(0);

  useEffect(() => {
    if (!activeOrganizacionId) return undefined;
    const scopeKey = String(activeOrganizacionId);
    const requestId = ++requestRef.current;
    setState({ scopeKey, cases: resource("loading", []), aggregate: resource() });

    Promise.allSettled([
      getKnowledgeCases(activeOrganizacionId),
      getKnowledgeAggregate(activeOrganizacionId),
    ]).then(([casesResult, aggregateResult]) => {
      if (requestRef.current !== requestId) return;
      setState({
        scopeKey,
        cases: casesResult.status === "fulfilled" ? resource("ready", casesResult.value) : resource("error", []),
        aggregate: aggregateResult.status === "fulfilled" ? resource("ready", aggregateResult.value) : resource("error"),
      });
    });

    return () => { requestRef.current += 1; };
  }, [activeOrganizacionId]);

  const requestedScopeKey = activeOrganizacionId ? String(activeOrganizacionId) : "";
  if (state.scopeKey !== requestedScopeKey) return <LoadingState label="Cargando conocimiento" />;

  return <main className="space-y-6">
    <PageHeader
      eyebrow="Gobernanza · Conocimiento"
      title="Conocimiento"
      description="Revisa qué conocimiento medido y verificable puede reutilizar la plataforma."
    />

    {state.aggregate.status === "loading" ? <LoadingState inline label="Cargando contexto agregado" /> : state.aggregate.status === "error" ? <ErrorState description="No se pudo cargar el resumen de casos comparables. Los casos propios siguen disponibles." /> : <Card><CardContent>
      <b>{state.aggregate.data?.casos_comparables ?? 0} casos comparables utilizables</b>
      <p className="text-sm text-[var(--text-muted)]">Antecedentes agregados; no son normativa ni garantizan un resultado futuro.</p>
    </CardContent></Card>}

    {state.cases.status === "loading" ? <LoadingState label="Cargando casos" /> : state.cases.status === "error" ? (
      <ErrorState description="No se pudo cargar el conocimiento de la organización." />
    ) : !state.cases.data.length ? (
      <EmptyState title="Sin casos de conocimiento" description="Los casos aparecen sólo cuando existe una procedencia verificable." />
    ) : <TableShell>
      <TableHead><tr><TableCell as="th">Caso</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Resultado</TableCell><TableCell as="th">Evidencia</TableCell><TableCell as="th">Origen</TableCell><TableCell as="th">Versión / fecha</TableCell></tr></TableHead>
      <TableBody columns={6}>{state.cases.data.map((item) => <tr key={item.id}>
        <TableCell><b>{human(item.categoria_ambiental)}</b><span className="block text-xs text-[var(--text-muted)]">{human(item.tipo_problematica)} · {human(item.tipo_accion)}</span></TableCell>
        <TableCell><State value={item.estado} /></TableCell>
        <TableCell>{human(item.resultado)}</TableCell>
        <TableCell>{human(item.fuerza_evidencia)}{item.fundamento_evidencia?.length > 0 && <details className="mt-1 text-xs"><summary className="cursor-pointer font-bold">Fundamentos</summary><ul className="mt-1 list-disc pl-4">{item.fundamento_evidencia.map((value) => <li key={value}>{human(value)}</li>)}</ul></details>}</TableCell>
        <TableCell>{human(item.origen_conocimiento)}</TableCell>
        <TableCell>v{item.version}<span className="block text-xs text-[var(--text-muted)]">{formatDateTime(item.fecha_caso || item.created_at)}</span></TableCell>
      </tr>)}</TableBody>
    </TableShell>}
  </main>;
}
