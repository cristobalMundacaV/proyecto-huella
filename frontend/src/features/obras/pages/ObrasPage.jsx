import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Building2, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { getActivePreset } from "@/presets/registry";
import WorkCard from "../components/WorkCard";
import { createOrganizationWork, getOrganizationWorks, getWorkContext } from "../services/workspaceApi";
import { Button, EmptyState, ErrorState, Input, Modal, SearchInput, Select } from "@/shared/ui";
import PlatformLoader from "@/shared/components/PlatformLoader";
const initialForm = { codigo_obra: "", nombre: "", fecha_inicio: "", tipo_proyecto: "Otro", superficie_m2: "", ubicacion: "" };
const workId = (work) => String(work?.id || work?.obra_id || work?.codigo_obra || "");
const attentionRank = (status) => {
  if (status === "requiere_atencion") return 0;
  if (status === "cierre_pendiente") return 1;
  if (!status || status === "no_determinado" || status === "no_disponible") return 3;
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
        const aContextError = contextErrorIds.has(aId);
        const bContextError = contextErrorIds.has(bId);
        const aStatus = contexts.get(aId)?.obra?.estado_ambiental
          ?? a.estado_ambiental
          ?? (aContextError ? "no_disponible" : "no_determinado");
        const bStatus = contexts.get(bId)?.obra?.estado_ambiental
          ?? b.estado_ambiental
          ?? (bContextError ? "no_disponible" : "no_determinado");
        return attentionRank(aStatus) - attentionRank(bStatus);
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

  if (status === "loading") {
    return (
      <PlatformLoader
        compact
        title={`Cargando ${preset.unitPluralLabel.toLowerCase()}`}
        description={`Estamos preparando el estado y seguimiento de tus ${preset.unitPluralLabel.toLowerCase()}.`}
      />
    );
  }
  if (status === "error") return <ErrorState description={`No fue posible cargar las ${preset.unitPluralLabel.toLowerCase()} de la organización activa.`} onRetry={load} />;

  return <main className="space-y-6">
    <section className="overflow-hidden rounded-[28px] border border-emerald-700/20 bg-[linear-gradient(135deg,rgba(6,78,59,0.97)_0%,rgba(6,95,70,0.93)_48%,rgba(15,118,110,0.84)_100%)] p-6 text-white shadow-[0_18px_45px_rgba(6,78,59,0.16)]">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-3xl">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-100">
            Mi operación
          </p>

          <h1 className="mt-2 text-3xl font-black">
            {preset.unitPluralLabel}
          </h1>

          <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50/80">
            Revisa el estado de tus {preset.unitPluralLabel.toLowerCase()},
            identifica cuáles requieren atención y entra directamente a gestionarlas.
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-white">
              {works.length} {works.length === 1
                ? preset.unitLabel.toLowerCase()
                : preset.unitPluralLabel.toLowerCase()}
            </span>

            <span className="rounded-full border border-amber-300/40 bg-amber-300/15 px-3 py-1.5 text-xs font-bold text-amber-100">
              {
                works.filter(work => {
                  const id = workId(work);
                  const current =
                    contexts.get(id)?.obra?.estado_ambiental ??
                    work.estado_ambiental;

                  return current === "requiere_atencion" ||
                    current === "cierre_pendiente";
                }).length
              } con atención
            </span>
          </div>
        </div>

        <Button
          variant="secondary"
          leftIcon={Plus}
          onClick={() => setOpen(true)}
          className="self-start border-white/30 bg-white text-emerald-900 shadow-[0_8px_24px_rgba(0,0,0,0.12)] hover:bg-emerald-50 lg:self-center"
        >
          Nueva {preset.unitLabel.toLowerCase()}
        </Button>
      </div>
    </section>
    {works.length > 0 && (
      <section className="rounded-2xl border border-[var(--border-subtle)] bg-white p-4 shadow-[0_10px_30px_rgba(15,23,42,0.04)]">
        <SearchInput
          label={`Buscar ${preset.unitPluralLabel.toLowerCase()}`}
          placeholder="Nombre, código o ubicación"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        {search.trim() && (
          <p className="mt-2 text-right text-xs font-semibold text-[var(--text-muted)]">
            {filtered.length} resultado{filtered.length === 1 ? "" : "s"}
          </p>
        )}
      </section>
    )}
    {works.length ? (
      <>
        {filtered.length ? (
          <div
            className={`grid gap-4 ${filtered.length === 1
              ? "max-w-3xl"
              : "md:grid-cols-2 xl:grid-cols-3"
              }`}
          >
            {filtered.map((work) => {
              const id = workId(work);

              return (
                <WorkCard
                  key={id}
                  work={work}
                  context={contexts.get(id)}
                  contextError={contextErrorIds.has(id)}
                  unitLabel={preset.unitLabel}
                />
              );
            })}
          </div>
        ) : (
          <EmptyState
            title={`No encontramos ${preset.unitPluralLabel.toLowerCase()}`}
            description="Prueba con otro nombre, código o ubicación."
          />
        )}
      </>
    ) : (
      <EmptyState
        icon={Building2}
        title={`Aún no tienes ${preset.unitPluralLabel.toLowerCase()}.`}
        description={`Agrega tu primera ${preset.unitLabel.toLowerCase()} para comenzar el seguimiento ambiental.`}
        primaryAction={
          <Button
            leftIcon={Plus}
            onClick={() => setOpen(true)}
          >
            Crear primera {preset.unitLabel.toLowerCase()}
          </Button>
        }
      />
    )}

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
