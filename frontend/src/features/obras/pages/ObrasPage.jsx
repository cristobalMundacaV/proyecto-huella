import { useCallback, useEffect, useMemo, useState } from "react";
import { Building2, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import WorkCard from "../components/WorkCard";
import { createOrganizationWork, getOrganizationWorks, getWorkWorkspace } from "../services/workspaceApi";
import { Button, EmptyState, ErrorState, FilterBar, Input, LoadingState, Modal, PageHeader, SearchInput, Select } from "@/shared/ui";

const initialForm = { codigo_obra: "", nombre: "", fecha_inicio: "", tipo_proyecto: "Otro", superficie_m2: "", ubicacion: "" };

export default function ObrasPage() {
  const navigate = useNavigate();
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const [works, setWorks] = useState([]);
  const [contexts, setContexts] = useState(new Map());
  const [status, setStatus] = useState("loading");
  const [filters, setFilters] = useState({ search: "", operational: "", environmental: "", profile: "" });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const load = useCallback(async () => {
    if (!activeOrganizacionId) return;
    setStatus("loading");
    try {
      const nextWorks = await getOrganizationWorks(activeOrganizacionId);
      setWorks(nextWorks);
      const settled = await Promise.allSettled(nextWorks.map((work) => getWorkWorkspace(activeOrganizacionId, work.id || work.obra_id || work.codigo_obra)));
      setContexts(new Map(settled.filter((item) => item.status === "fulfilled").map((item) => [String(item.value.obra.id || item.value.obra.obra_id), item.value.context])));
      setStatus("ready");
    } catch { setStatus("error"); }
  }, [activeOrganizacionId]);
  useEffect(() => { load(); }, [load]);

  const options = (key) => [...new Set(works.map((work) => work[key]).filter(Boolean))];
  const environmentalOptions = [...new Set([...contexts.values()].map((context) => context.obra?.estado_ambiental).filter(Boolean))];
  const filtered = useMemo(() => works.filter((work) => {
    const text = `${work.nombre || ""} ${work.codigo_obra || ""} ${work.tipo_proyecto || ""}`.toLowerCase();
    const environmental = contexts.get(String(work.id || work.obra_id))?.obra?.estado_ambiental;
    return (!filters.search || text.includes(filters.search.toLowerCase())) && (!filters.operational || work.estado === filters.operational) && (!filters.environmental || environmental === filters.environmental) && (!filters.profile || work.perfil_ambiental === filters.profile);
  }), [contexts, filters, works]);

  const submit = async (event) => {
    event.preventDefault(); setSaving(true); setFormError("");
    try {
      const created = await createOrganizationWork(activeOrganizacionId, form);
      setOpen(false); setForm(initialForm);
      navigate(`/obras/${created.id || created.obra_id || created.codigo_obra}/resumen`);
    } catch (error) {
      setFormError(error.response?.data?.detail || "No fue posible crear la obra. Revisa los campos.");
    } finally { setSaving(false); }
  };

  if (status === "loading") return <LoadingState label="Cargando obras" />;
  if (status === "error") return <ErrorState description="No fue posible cargar las obras de la organización activa." onRetry={load} />;
  return <div className="space-y-6">
    <PageHeader eyebrow={activeOrganizacion?.nombre} title="Obras" description="Encuentra, compara y abre la frontera ambiental de cada proyecto." actions={<Button leftIcon={Plus} onClick={() => setOpen(true)}>Nueva obra</Button>} />
    {works.length ? <>
      <FilterBar>
        <div className="min-w-56 flex-1"><SearchInput label="Buscar" placeholder="Nombre, código o tipo" value={filters.search} onChange={(event) => setFilters((value) => ({ ...value, search: event.target.value }))} /></div>
        <Select label="Estado operacional" value={filters.operational} onChange={(event) => setFilters((value) => ({ ...value, operational: event.target.value }))}><option value="">Todos</option>{options("estado").map((value) => <option key={value}>{value}</option>)}</Select>
        <Select label="Estado ambiental" value={filters.environmental} onChange={(event) => setFilters((value) => ({ ...value, environmental: event.target.value }))}><option value="">Todos</option>{environmentalOptions.map((value) => <option key={value}>{value}</option>)}</Select>
        <Select label="Perfil" value={filters.profile} onChange={(event) => setFilters((value) => ({ ...value, profile: event.target.value }))}><option value="">Todos</option>{options("perfil_ambiental").map((value) => <option key={value}>{value}</option>)}</Select>
      </FilterBar>
      {filtered.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{filtered.map((work) => <WorkCard key={work.id || work.codigo_obra} work={work} context={contexts.get(String(work.id || work.obra_id))} />)}</div> : <EmptyState title="No encontramos obras" description="Ajusta los filtros para volver a ver resultados." />}
    </> : <EmptyState icon={Building2} title="Aún no hay obras" description="Las obras delimitan el seguimiento ambiental de cada proyecto." primaryAction={<Button leftIcon={Plus} onClick={() => setOpen(true)}>Crear primera obra</Button>} />}

    <Modal open={open} onClose={() => setOpen(false)} title="Nueva obra" description="Registra la información base disponible. Los campos corresponden al contrato actual.">
      <form className="grid gap-4 sm:grid-cols-2" onSubmit={submit}>
        <Input required label="Código de obra" value={form.codigo_obra} onChange={(event) => setForm((value) => ({ ...value, codigo_obra: event.target.value }))} />
        <Input label="Nombre" value={form.nombre} onChange={(event) => setForm((value) => ({ ...value, nombre: event.target.value }))} />
        <Input required type="date" label="Fecha de inicio" value={form.fecha_inicio} onChange={(event) => setForm((value) => ({ ...value, fecha_inicio: event.target.value }))} />
        <Select required label="Tipo de obra" value={form.tipo_proyecto} onChange={(event) => setForm((value) => ({ ...value, tipo_proyecto: event.target.value }))}><option>Vivienda</option><option>Edificio habitacional</option><option>Infraestructura</option><option>Industrial</option><option>Comercial</option><option>Obra publica</option><option>Urbanizacion</option><option>Otro</option></Select>
        <Input required min="0" step="0.001" type="number" label="Superficie o cantidad base" value={form.superficie_m2} onChange={(event) => setForm((value) => ({ ...value, superficie_m2: event.target.value }))} />
        <Input label="Ubicación" value={form.ubicacion} onChange={(event) => setForm((value) => ({ ...value, ubicacion: event.target.value }))} />
        {formError && <p className="text-sm text-[var(--status-danger)] sm:col-span-2" role="alert">{formError}</p>}
        <div className="flex justify-end gap-2 sm:col-span-2"><Button variant="secondary" onClick={() => setOpen(false)}>Cancelar</Button><Button loading={saving} type="submit">Crear obra</Button></div>
      </form>
    </Modal>
  </div>;
}
