import { useEffect, useState } from "react";
import { ClipboardCheck, Factory, Plus, Trash2 } from "lucide-react";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import CapacidadesAmbientales from "../components/CapacidadesAmbientales";
import { createProceso, createUnidad, saveDiagnostico } from "../api/diagnosticoApi";
import { useDiagnostico } from "../hooks/useDiagnostico";

const ESTADOS = ["pendiente", "en_progreso", "completado", "requiere_actualizacion"];
const GRUPOS = [
  ["proceso", "Procesos identificados"],
  ["informacion_disponible", "Información disponible"],
  ["informacion_faltante", "Información faltante"],
  ["fuente", "Fuentes conocidas"],
  ["brecha", "Brechas ambientales"],
];
const emptyForm = { estado: "pendiente", objetivo_principal: "", descripcion_contexto: "", observaciones: "" };
const keyFor = (item) => item.id ? `id-${item.id}` : item.localId;

export default function DiagnosticoAmbientalPage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const state = useDiagnostico(activeOrganizacionId);
  const [form, setForm] = useState(emptyForm);
  const [elementos, setElementos] = useState([]);
  const [dirty, setDirty] = useState(() => new Set());
  const [eliminados, setEliminados] = useState([]);
  const [unidad, setUnidad] = useState("");
  const [proceso, setProceso] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (state.loading) return;
    setForm(state.diagnostico ? {
      estado: state.diagnostico.estado,
      objetivo_principal: state.diagnostico.objetivo_principal || "",
      descripcion_contexto: state.diagnostico.descripcion_contexto || "",
      observaciones: state.diagnostico.observaciones || "",
    } : emptyForm);
    setElementos(state.diagnostico?.elementos || []);
    setDirty(new Set());
    setEliminados([]);
  }, [state.diagnostico, state.loading]);

  function addElemento(tipo) {
    const localId = `new-${Date.now()}-${Math.random()}`;
    setElementos((actuales) => [...actuales, { localId, tipo, nombre: "", descripcion: "" }]);
    setDirty((actuales) => new Set(actuales).add(localId));
  }

  function updateElemento(item, field, value) {
    const key = keyFor(item);
    setElementos((actuales) => actuales.map((actual) => keyFor(actual) === key ? { ...actual, [field]: value } : actual));
    setDirty((actuales) => new Set(actuales).add(key));
  }

  function removeElemento(item) {
    setElementos((actuales) => actuales.filter((actual) => keyFor(actual) !== keyFor(item)));
    if (item.id) setEliminados((actuales) => [...actuales, item.id]);
  }

  async function handleSave() {
    setSaving(true);
    try {
      const modificados = elementos
        .filter((item) => dirty.has(keyFor(item)))
        .map(({ id, tipo, nombre, descripcion }) => ({ ...(id ? { id } : {}), tipo, nombre, descripcion }));
      const payload = { ...form, elementos: [...modificados, ...eliminados.map((id) => ({ id, eliminar: true }))] };
      await saveDiagnostico(activeOrganizacionId, payload, Boolean(state.diagnostico));
      await state.reload();
    } finally {
      setSaving(false);
    }
  }

  if (state.loading) return <p className="p-8 text-slate-500">Cargando diagnóstico ambiental...</p>;

  return <div className="mx-auto max-w-7xl space-y-6">
    <header className="rounded-[28px] border border-emerald-200 bg-emerald-50 p-6">
      <div className="flex items-center gap-3"><ClipboardCheck className="text-emerald-700" size={32}/><div><p className="text-xs font-black uppercase tracking-widest text-emerald-700">Fundación ambiental</p><h1 className="text-3xl font-black text-slate-900">Diagnóstico Ambiental</h1></div></div>
      <p className="mt-3 text-slate-600">Estado: <b>{form.estado.replaceAll("_", " ")}</b> · Siguiente paso: <b>{state.preparacion?.siguiente_paso}</b></p>
    </header>
    {state.error && <p className="rounded-2xl bg-red-50 p-4 text-red-700">{state.error}</p>}

    <section className="rounded-[28px] border border-slate-200 bg-white p-6">
      <h2 className="text-xl font-black">{state.diagnostico ? "Actualizar diagnóstico" : "Iniciar diagnóstico"}</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <label className="text-sm font-bold text-slate-700">Estado<select value={form.estado} onChange={(e) => setForm({...form, estado: e.target.value})} className="mt-1 w-full rounded-xl border p-3 font-normal">{ESTADOS.map((estado) => <option key={estado} value={estado}>{estado.replaceAll("_", " ")}</option>)}</select></label>
        <label className="text-sm font-bold text-slate-700">Objetivo o necesidad principal<input value={form.objetivo_principal} onChange={(e) => setForm({...form, objetivo_principal:e.target.value})} className="mt-1 w-full rounded-xl border p-3 font-normal"/></label>
        <label className="text-sm font-bold text-slate-700">Contexto<textarea value={form.descripcion_contexto} onChange={(e) => setForm({...form, descripcion_contexto:e.target.value})} className="mt-1 min-h-24 w-full rounded-xl border p-3 font-normal"/></label>
        <label className="text-sm font-bold text-slate-700">Observaciones<textarea value={form.observaciones} onChange={(e) => setForm({...form, observaciones:e.target.value})} className="mt-1 min-h-24 w-full rounded-xl border p-3 font-normal"/></label>
      </div>
    </section>

    <section className="grid gap-4 lg:grid-cols-2">
      {GRUPOS.map(([tipo, title]) => <ElementGroup key={tipo} tipo={tipo} title={title} items={elementos.filter((item) => item.tipo === tipo)} onAdd={addElemento} onUpdate={updateElemento} onRemove={removeElemento}/>) }
    </section>

    <button disabled={saving} onClick={handleSave} className="rounded-xl bg-emerald-700 px-5 py-3 font-bold text-white disabled:opacity-60">{saving ? "Guardando..." : "Guardar diagnóstico"}</button>
    <section><h2 className="mb-3 text-xl font-black">Capacidades detectadas y configuradas</h2><CapacidadesAmbientales organizacionId={activeOrganizacionId} capacidades={state.capacidades} onChange={state.reload}/></section>
    <section className="rounded-[28px] border border-slate-200 bg-white p-6"><div className="flex items-center gap-2"><Factory className="text-emerald-700"/><h2 className="text-xl font-black">Estructura operacional</h2></div><div className="mt-4 grid gap-5 md:grid-cols-2"><Structure title="Unidades" items={state.unidades} value={unidad} setValue={setUnidad} onAdd={async()=>{if(unidad){await createUnidad(activeOrganizacionId,{nombre:unidad,tipo:"otro"});setUnidad("");state.reload();}}}/><Structure title="Procesos" items={state.procesos} value={proceso} setValue={setProceso} onAdd={async()=>{if(proceso){await createProceso(activeOrganizacionId,{nombre:proceso,estado:"activo"});setProceso("");state.reload();}}}/></div></section>
  </div>;
}

function ElementGroup({ tipo, title, items, onAdd, onUpdate, onRemove }) {
  return <div className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex items-center justify-between"><h2 className="font-black">{title}</h2><button type="button" onClick={() => onAdd(tipo)} className="flex items-center gap-1 rounded-xl bg-slate-900 px-3 py-2 text-xs font-bold text-white"><Plus size={15}/>Agregar</button></div>
    <div className="mt-3 space-y-3">{items.length === 0 && <p className="text-sm text-slate-500">Aún no se ha registrado información.</p>}{items.map((item) => <div key={keyFor(item)} className="rounded-xl border border-slate-200 p-3"><div className="flex gap-2"><input value={item.nombre} onChange={(e) => onUpdate(item, "nombre", e.target.value)} placeholder="Nombre" className="min-w-0 flex-1 rounded-lg border p-2"/><button type="button" aria-label={`Eliminar ${item.nombre || title}`} onClick={() => onRemove(item)} className="rounded-lg border border-red-200 p-2 text-red-600"><Trash2 size={17}/></button></div><textarea value={item.descripcion || ""} onChange={(e) => onUpdate(item, "descripcion", e.target.value)} placeholder="Descripción opcional" className="mt-2 min-h-16 w-full rounded-lg border p-2"/></div>)}</div>
  </div>;
}

function Structure({title,items,value,setValue,onAdd}) { return <div><h3 className="font-black">{title}</h3><div className="my-2 flex gap-2"><input value={value} onChange={e=>setValue(e.target.value)} placeholder={`Nueva ${title.toLowerCase()}`} className="min-w-0 flex-1 rounded-xl border p-3"/><button onClick={onAdd} className="rounded-xl bg-slate-900 p-3 text-white"><Plus size={18}/></button></div>{items.map(i=><p key={i.id} className="border-b py-2 text-sm">{i.nombre}</p>)}</div>}
