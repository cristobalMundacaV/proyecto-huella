import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Building2, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { getActivePreset } from "@/presets/registry";
import WorkCard from "../components/WorkCard";
import { createOrganizationWork, getOrganizationWorks, getWorkContext } from "../services/workspaceApi";
import { Button, EmptyState, ErrorState, Input, LoadingState, Modal, PageHeader, SearchInput, Select } from "@/shared/ui";

const initialForm = { codigo_obra: "", nombre: "", fecha_inicio: "", tipo_proyecto: "Otro", superficie_m2: "", ubicacion: "" };
const workId = (work) => String(work?.id || work?.obra_id || work?.codigo_obra || "");
const attentionRank = (status, unknown) => {
  if (status === "requiere_atencion") return 0;
  if (status === "cierre_pendiente") return 1;
  if (unknown || !status || status === "no_determinado") return 3;
  return 2;
};

export default function ObrasPage() {
  const navigate = useNavigate();
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const preset = getActivePreset(activeOrganizacion?.preset || "construccion");
  const [works, setWorks] = useState([]);
  const [contexts, setContexts] = useState(new Map());
  const [contextErrorIds, setContextErrorIds] = useState(new Set());
  const [status, setStatus] = useState("loading");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const requestRef = useRef(0);

  const load = useCallback(async () => {
    if (!activeOrganizacionId) return;
    const requestId = ++requestRef.current;
    setStatus("loading");
    try {
      const nextWorks = await getOrganizationWorks(activeOrganizacionId);
      if (requestRef.current !== requestId) return;
      const settled = await Promise.allSettled(nextWorks.map((work) => getWorkContext(activeOrganizacionId, work)));
      if (requestRef.current !== requestId) return;

      const nextContexts = new Map();
      const nextContextErrors = new Set();
      settled.forEach((item, index) => {
        const id = workId(nextWorks[index]);
        if (item.status === "fulfilled") nextContexts.set(id, item.value.context);
        else nextContextErrors.add(id);
      });

      setWorks(nextWorks);
      setContexts(nextContexts);
      setContextErrorIds(nextContextErrors);
      setStatus("ready");
    } catch {
      if (requestRef.current === requestId) setStatus("error");
    }
  }, [activeOrganizacionId]);

  useEffect(() => {
    load();
    return () => { requestRef.current += 1; };
  }, [load]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return works
      .filter((work) => !query || `${work.nombre || ""} ${work.codigo_obra || ""} ${work.ubicacion || ""}`.toLowerCase().includes(query))
      .sort((a, b) => {
        const aId = workId(a);
        const bId = workId(b);
        const aStatus = contexts.get(aId)?.obra?.estado_ambiental ?? a.estado_ambiental;
        const bStatus = contexts.get(bId)?.obra?.estado_ambiental ?? b.estado_ambiental;
        const aUnknown = contextErrorIds.has(aId);
        const bUnknown = contextErrorIds.has(bId);
        return attentionRank(aStatus, aUnknown) - attentionRank(bStatus, bUnknown);
      });
  }, [contextErrorIds, contexts, search, works]);

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setFormError("");
    const payload = {
      nombre: form.nombre.trim(),
      fecha_inicio: form.fecha_inicio,
    };
    if (form.codigo_obra.trim()) payload.codigo_obra = form.codigo_obra.trim();
    if (form.ubicacion.trim()) payload.ubicacion = form.ubicacion.trim();
    if (preset.key === "construccion") {
      payload.tipo_proyecto = form.tipo_proyecto;
      if (form.superficie_m2 !== "") payload.superficie_m2 = form.superficie_m2;
    }

    try {
      const created = await createOrganizationWork(activeOrganizacionId, payload);
      setOpen(false);
      setForm(initialForm);
      navigate(`/obras/${created.id || created.obra_id || created.codigo_obra}/resumen`);
    } catch (error) {
      setFormError(error.response?.data?.detail || "No fue posible crear esta unidad. Revisa los datos ingresados.");
    } finally {
      setSaving(false);
    }
  };

  const closeModal = () => {
    if (saving) return;
    setOpen(false);
    setFormError("");
  };

  if (status === "loading") return <LoadingState label={`Cargando ${preset.unitPluralLabel.toLowerCase()}`} />;
  if (status === "error") return <ErrorState description={`No fue posible cargar las ${preset.unitPluralLabel.toLowerCase()} de la organización activa.`} onRetry={load} />;

  return <main className="space-y-6">
    <PageHeader
      title={preset.unitPluralLabel}
      description={`Revisa el estado de tus ${preset.unitPluralLabel.toLowerCase()} y entra a la que necesitas gestionar.`}
      actions={<Button leftIcon={Plus} onClick={() => setOpen(true)}>Nueva {preset.unitLabel.toLowerCase()}</Button>}
    />

    {works.length ? <>
      <div className="max-w-xl">
        <SearchInput
          label="Buscar"
          placeholder={`Nombre, código o ubicación`}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </div>
      {filtered.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((work) => {
          const id = workId(work);
          return <WorkCard
            key={id}
            work={work}
            context={contexts.get(id)}
            contextError={contextErrorIds.has(id)}
            unitLabel={preset.unitLabel}
          />;
        })}
      </div> : <EmptyState title={`No encontramos ${preset.unitPluralLabel.toLowerCase()}`} description="Prueba con otro nombre, código o ubicación." />}
    </> : <EmptyState
      icon={Building2}
      title={`Aún no tienes ${preset.unitPluralLabel.toLowerCase()}.`}
      description={`Agrega tu primera ${preset.unitLabel.toLowerCase()} para comenzar el seguimiento ambiental.`}
      primaryAction={<Button leftIcon={Plus} onClick={() => setOpen(true)}>Crear primera {preset.unitLabel.toLowerCase()}</Button>}
    />}

    <Modal
      open={open}
      onClose={closeModal}
      title={`Nueva ${preset.unitLabel.toLowerCase()}`}
      description={`Ingresa los datos básicos de la ${preset.unitLabel.toLowerCase()}. Podrás completar la información ambiental después.`}
    >
      <form className="space-y-5" onSubmit={submit}>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input required label="Nombre" value={form.nombre} onChange={(event) => setForm((value) => ({ ...value, nombre: event.target.value }))} />
          <Input required type="date" label="Fecha de inicio" value={form.fecha_inicio} onChange={(event) => setForm((value) => ({ ...value, fecha_inicio: event.target.value }))} />
        </div>

        <details className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-subtle)] p-4">
          <summary className="cursor-pointer font-bold text-[var(--text-primary)]">Agregar detalles opcionales</summary>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Input label="Código" value={form.codigo_obra} onChange={(event) => setForm((value) => ({ ...value, codigo_obra: event.target.value }))} />
            <Input label="Ubicación" value={form.ubicacion} onChange={(event) => setForm((value) => ({ ...value, ubicacion: event.target.value }))} />
            {preset.key === "construccion" && <>
              <Select label="Tipo de proyecto" value={form.tipo_proyecto} onChange={(event) => setForm((value) => ({ ...value, tipo_proyecto: event.target.value }))}>
                <option>Vivienda</option><option>Edificio habitacional</option><option>Infraestructura</option><option>Industrial</option><option>Comercial</option><option>Obra publica</option><option>Urbanizacion</option><option>Otro</option>
              </Select>
              <Input min="0" step="0.001" type="number" label="Superficie (m²)" value={form.superficie_m2} onChange={(event) => setForm((value) => ({ ...value, superficie_m2: event.target.value }))} />
            </>}
          </div>
        </details>

        {formError && <p className="text-sm text-[var(--status-danger)]" role="alert">{formError}</p>}
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="secondary" onClick={closeModal}>Cancelar</Button>
          <Button loading={saving} type="submit">Crear {preset.unitLabel.toLowerCase()}</Button>
        </div>
      </form>
    </Modal>
  </main>;
}
