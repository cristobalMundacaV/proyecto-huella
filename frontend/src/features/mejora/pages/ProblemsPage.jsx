import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import { Plus } from "lucide-react";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { Button, EmptyState, ErrorState, FilterBar, Input, LoadingState, Modal, PageHeader, SearchInput, SectionHeader, Select, StatusBadge, TableBody, TableCell, TableHead, TableShell, Textarea } from "@/shared/ui";
import { createProblem, listProblems } from "../services/improvementApi";
import { label, problemTone } from "../utils/improvementFormat";

const initial = { titulo: "", descripcion: "", categoria: "", indicador: "", unidad_indicador: "", valor_inicial: "", objetivo_meta: "", fecha_deteccion: new Date().toISOString().slice(0, 10), nivel_riesgo: "medio" };

export default function ProblemsPage({ workScoped = false }) {
  const workspace = useOutletContext() || {};
  const { obraId } = useParams();
  const { activeOrganizacionId } = useOrganizacionActiva();
  const work = workspace.obra;
  const workId = work?.id || work?.obra_id;
  const [state, setState] = useState({ loading: true, rows: [], error: "" });
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setState((current) => ({ ...current, loading: true, error: "" }));
    listProblems(activeOrganizacionId, workScoped ? workId : undefined)
      .then((rows) => setState({ loading: false, rows, error: "" }))
      .catch(() => setState({ loading: false, rows: [], error: "No fue posible cargar las problemáticas." }));
  }, [activeOrganizacionId, workId, workScoped]);
  useEffect(() => { load(); }, [load]);

  const visible = useMemo(() => state.rows.filter((item) =>
    (!query || `${item.titulo} ${item.categoria}`.toLowerCase().includes(query.toLowerCase())) && (!status || item.estado === status),
  ), [query, state.rows, status]);

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    try {
      await createProblem(activeOrganizacionId, { ...form, obra: workScoped ? workId : form.obra || null });
      setForm(null);
      await load();
    } catch {
      setState((current) => ({ ...current, error: "No se pudo registrar la problemática." }));
    } finally {
      setSaving(false);
    }
  }

  const path = (id) => workScoped ? `/obras/${obraId}/problemas/${id}` : `/inteligencia/problemas/${id}`;
  const createAction = <Button leftIcon={Plus} onClick={() => setForm(initial)}>Registrar problemática</Button>;

  return <main className="space-y-5">
    {workScoped
      ? <SectionHeader title="Problemas" description="Identifica qué requiere atención y gestiona su seguimiento." action={createAction} />
      : <PageHeader eyebrow="Inteligencia · Mejora verificable" title="Problemáticas ambientales" description="Identifica qué requiere atención y abre su ciclo de mejora verificable." actions={createAction} />}

    {state.error && <ErrorState description={state.error} onRetry={load} />}
    <FilterBar>
      <SearchInput label="Buscar" placeholder="Título o categoría" value={query} onChange={(event) => setQuery(event.target.value)} />
      <Select label="Estado" value={status} onChange={(event) => setStatus(event.target.value)}>
        <option value="">Todos</option>
        {["detectada", "analizando", "propuesta", "accion_seleccionada", "implementando", "seguimiento", "evaluando", "escalada_profesional", "cerrada"].map((value) => <option key={value}>{value}</option>)}
      </Select>
    </FilterBar>

    {state.loading ? <LoadingState label="Cargando problemáticas" /> : !visible.length ? <EmptyState title="No hay problemáticas ambientales registradas." description={workScoped ? "Esta unidad no tiene problemas vinculados." : "Registra una problemática cuando exista evidencia suficiente."} /> : <TableShell>
      <TableHead><tr><TableCell as="th">Problema</TableCell><TableCell as="th">Categoría</TableCell><TableCell as="th">Riesgo</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Indicador</TableCell><TableCell as="th">Acción</TableCell></tr></TableHead>
      <TableBody columns={6}>{visible.map((item) => <tr key={item.id}>
        <TableCell><Link className="font-bold text-[var(--brand-primary)]" to={path(item.id)}>{item.titulo}</Link><span className="block text-xs text-[var(--text-muted)]">{item.fecha_deteccion}</span></TableCell>
        <TableCell>{label(item.categoria)}</TableCell><TableCell>{label(item.nivel_riesgo)}</TableCell><TableCell><StatusBadge tone={problemTone(item.estado)}>{label(item.estado)}</StatusBadge></TableCell><TableCell>{item.indicador || "Sin indicador"}</TableCell><TableCell>{item.resultado_evaluacion === "pendiente" ? "Resultado pendiente" : label(item.resultado_evaluacion)}</TableCell>
      </tr>)}</TableBody>
    </TableShell>}

    <Modal open={Boolean(form)} title="Registrar problemática" description="Describe el problema y su situación inicial; una acción futura no implica mejora." onClose={() => setForm(null)} footer={<div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => setForm(null)}>Cancelar</Button><Button form="problem-form" loading={saving} type="submit">Registrar</Button></div>}>
      <form id="problem-form" className="grid gap-4 sm:grid-cols-2" onSubmit={submit}>
        <Input required label="Título" value={form?.titulo || ""} onChange={(event) => setForm({ ...form, titulo: event.target.value })} />
        <Input required label="Categoría" value={form?.categoria || ""} onChange={(event) => setForm({ ...form, categoria: event.target.value })} />
        <Textarea required label="Descripción" className="sm:col-span-2" value={form?.descripcion || ""} onChange={(event) => setForm({ ...form, descripcion: event.target.value })} />
        <Input required label="Indicador" value={form?.indicador || ""} onChange={(event) => setForm({ ...form, indicador: event.target.value })} />
        <Input required label="Unidad" value={form?.unidad_indicador || ""} onChange={(event) => setForm({ ...form, unidad_indicador: event.target.value })} />
        <Input required label="Situación inicial" type="number" step="any" value={form?.valor_inicial || ""} onChange={(event) => setForm({ ...form, valor_inicial: event.target.value })} />
        <Input required label="Meta" type="number" step="any" value={form?.objetivo_meta || ""} onChange={(event) => setForm({ ...form, objetivo_meta: event.target.value })} />
        <Input required label="Fecha de detección" type="date" value={form?.fecha_deteccion || ""} onChange={(event) => setForm({ ...form, fecha_deteccion: event.target.value })} />
        <Select label="Riesgo" value={form?.nivel_riesgo || "medio"} onChange={(event) => setForm({ ...form, nivel_riesgo: event.target.value })}>{["bajo", "medio", "alto", "critico"].map((value) => <option key={value}>{value}</option>)}</Select>
      </form>
    </Modal>
  </main>;
}
