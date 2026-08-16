import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import { Plus } from "lucide-react";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { formatDate } from "@/shared/utils/formatters";
import { Alert, Button, EmptyState, ErrorState, FilterBar, Input, LoadingState, Modal, PageHeader, SearchInput, SectionHeader, Select, StatusBadge, TableBody, TableCell, TableHead, TableShell, Textarea } from "@/shared/ui";
import { createProblem, listProblems } from "../services/improvementApi";
import { problemNextStep, problemStatusLabel, problemTone, riskLabel } from "../utils/improvementFormat";

const statusOptions = [
  "detectada", "analizando", "propuesta", "accion_seleccionada", "implementando",
  "seguimiento", "evaluando", "escalada_profesional", "cerrada",
  "en_analisis", "accion_propuesta", "en_implementacion", "en_seguimiento",
  "resuelta", "mejora_insuficiente", "no_resuelta", "escalada",
];

const initialProblem = () => ({
  titulo: "",
  descripcion: "",
  categoria: "",
  indicador: "co2e_total_kg",
  unidad_indicador: "kgCO2e",
  valor_inicial: "",
  objetivo_meta: "",
  fecha_deteccion: new Date().toISOString().slice(0, 10),
  nivel_riesgo: "medio",
});

export default function ProblemsPage({ workScoped = false }) {
  const workspace = useOutletContext() || {};
  const { obraId } = useParams();
  const { activeOrganizacionId } = useOrganizacionActiva();
  const work = workspace.obra;
  const workId = work?.id || work?.obra_id;
  const [state, setState] = useState({ scopeKey: "", status: "loading", rows: [], error: "" });
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [mutationError, setMutationError] = useState("");
  const requestRef = useRef(0);

  const load = useCallback((reset = false) => {
    if (!activeOrganizacionId || (workScoped && !workId)) return Promise.resolve();
    const scopeKey = `${activeOrganizacionId}:${workScoped ? workId : "global"}`;
    const requestId = ++requestRef.current;
    setState((current) => ({ scopeKey, status: "loading", rows: reset ? [] : current.scopeKey === scopeKey ? current.rows : [], error: "" }));
    return listProblems(activeOrganizacionId, workScoped ? workId : undefined)
      .then((rows) => {
        if (requestRef.current === requestId) setState({ scopeKey, status: "ready", rows, error: "" });
      })
      .catch(() => {
        if (requestRef.current === requestId) {
          setState((current) => ({ ...current, scopeKey, status: "error", error: "No fue posible cargar los problemas." }));
        }
      });
  }, [activeOrganizacionId, workId, workScoped]);

  useEffect(() => {
    load(true);
    return () => { requestRef.current += 1; };
  }, [load]);

  const visible = useMemo(() => state.rows.filter((item) => {
    const haystack = `${item.titulo || ""} ${item.categoria || ""} ${item.unidad_operacional || ""}`.toLowerCase();
    return (!query || haystack.includes(query.toLowerCase())) && (!status || item.estado === status);
  }), [query, state.rows, status]);

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setMutationError("");
    try {
      await createProblem(activeOrganizacionId, { ...form, obra: workScoped ? workId : null });
      setForm(null);
      await load(false);
    } catch (error) {
      setMutationError(error?.response?.data?.detail || "No se pudo registrar el problema.");
    } finally {
      setSaving(false);
    }
  }

  const requestedScopeKey = activeOrganizacionId && (!workScoped || workId) ? `${activeOrganizacionId}:${workScoped ? workId : "global"}` : "";
  const scopeChanged = state.scopeKey !== requestedScopeKey;

  const path = (id) => workScoped ? `/obras/${obraId}/problemas/${id}` : `/inteligencia/problemas/${id}`;
  const createAction = <Button leftIcon={Plus} onClick={() => { setMutationError(""); setForm(initialProblem()); }}>Registrar problema</Button>;

  return <main className="space-y-5">
    {workScoped
      ? <SectionHeader title="Problemas" description="Gestiona situaciones ambientales desde su detección hasta verificar el resultado." action={createAction} />
      : <PageHeader title="Problemas" description="Gestiona situaciones ambientales desde su detección hasta verificar el resultado." actions={createAction} />}

    {mutationError && <Alert tone="danger">{mutationError}</Alert>}
    {state.status === "error" && <ErrorState description={state.error} onRetry={() => load(false)} />}

    <FilterBar>
      <SearchInput label="Buscar" placeholder="Título, categoría o contexto" value={query} onChange={(event) => setQuery(event.target.value)} />
      <Select label="Estado" value={status} onChange={(event) => setStatus(event.target.value)}>
        <option value="">Todos</option>
        {statusOptions.map((value) => <option key={value} value={value}>{problemStatusLabel(value)}</option>)}
      </Select>
    </FilterBar>

    {scopeChanged ? <LoadingState label="Cargando problemas" /> : state.status === "loading" && !state.rows.length ? <LoadingState label="Cargando problemas" /> : state.status !== "error" && !visible.length ? <EmptyState
      title={state.rows.length ? "No hay problemas que coincidan con los filtros." : "No hay problemas registrados."}
      description={state.rows.length ? "Ajusta la búsqueda o el estado." : workScoped ? "Esta unidad no tiene problemas vinculados." : "Registra un problema cuando exista una situación que deba gestionarse."}
    /> : !scopeChanged && visible.length > 0 && <TableShell>
      <TableHead><tr>
        <TableCell as="th">Problema</TableCell>
        <TableCell as="th">Estado</TableCell>
        <TableCell as="th">Riesgo</TableCell>
        <TableCell as="th">Contexto</TableCell>
        <TableCell as="th">Siguiente paso</TableCell>
      </tr></TableHead>
      <TableBody columns={5}>{visible.map((item) => {
        const next = problemNextStep({ problem: item });
        const context = item.unidad_operacional || item.area_operacional || (item.obra ? "Unidad vinculada" : "Organización");
        return <tr key={item.id}>
          <TableCell>
            <Link className="font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to={path(item.id)}>{item.titulo}</Link>
            {item.fecha_deteccion && <span className="block text-xs text-[var(--text-muted)]">Detectado {formatDate(item.fecha_deteccion)}</span>}
          </TableCell>
          <TableCell><StatusBadge tone={problemTone(item.estado)}>{problemStatusLabel(item.estado)}</StatusBadge></TableCell>
          <TableCell>{riskLabel(item.nivel_riesgo)}</TableCell>
          <TableCell>{context}</TableCell>
          <TableCell><span className="text-sm font-medium">{next.title}</span></TableCell>
        </tr>;
      })}</TableBody>
    </TableShell>}

    <Modal
      open={Boolean(form)}
      title="Registrar problema"
      description="Describe la situación y define cómo se verificará. Registrar un problema no selecciona ni ejecuta una acción."
      onClose={() => setForm(null)}
      footer={<div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => setForm(null)}>Cancelar</Button><Button form="problem-form" loading={saving} type="submit">Registrar</Button></div>}
    >
      <form id="problem-form" className="space-y-5" onSubmit={submit}>
        <section className="space-y-3">
          <h3 className="font-bold">Problema</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input required label="Título" value={form?.titulo || ""} onChange={(event) => setForm({ ...form, titulo: event.target.value })} />
            <Input required label="Categoría" value={form?.categoria || ""} onChange={(event) => setForm({ ...form, categoria: event.target.value })} />
            <div className="sm:col-span-2"><Textarea required label="Descripción" value={form?.descripcion || ""} onChange={(event) => setForm({ ...form, descripcion: event.target.value })} /></div>
            <Select label="Riesgo" value={form?.nivel_riesgo || "medio"} onChange={(event) => setForm({ ...form, nivel_riesgo: event.target.value })}>
              {["bajo", "medio", "alto", "critico"].map((value) => <option key={value} value={value}>{riskLabel(value)}</option>)}
            </Select>
            <Input required label="Fecha de detección" type="date" value={form?.fecha_deteccion || ""} onChange={(event) => setForm({ ...form, fecha_deteccion: event.target.value })} />
          </div>
        </section>

        <section className="space-y-3">
          <h3 className="font-bold">Medición inicial</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input required label="Indicador" value={form?.indicador || ""} onChange={(event) => setForm({ ...form, indicador: event.target.value })} />
            <Input required label="Unidad" value={form?.unidad_indicador || ""} onChange={(event) => setForm({ ...form, unidad_indicador: event.target.value })} />
            <Input required label="Situación actual" type="number" step="any" value={form?.valor_inicial || ""} onChange={(event) => setForm({ ...form, valor_inicial: event.target.value })} />
            <Input required label="Meta" type="number" step="any" value={form?.objetivo_meta || ""} onChange={(event) => setForm({ ...form, objetivo_meta: event.target.value })} />
          </div>
        </section>
      </form>
    </Modal>
  </main>;
}
