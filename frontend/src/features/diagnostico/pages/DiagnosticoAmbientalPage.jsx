import { useState } from "react";
import { ClipboardCheck, Factory, Plus } from "lucide-react";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import CapacidadesAmbientales from "../components/CapacidadesAmbientales";
import { createProceso, createUnidad, saveDiagnostico } from "../api/diagnosticoApi";
import { useDiagnostico } from "../hooks/useDiagnostico";

export default function DiagnosticoAmbientalPage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const state = useDiagnostico(activeOrganizacionId);
  const [form, setForm] = useState({ objetivo_principal: "", descripcion_contexto: "" });
  const [unidad, setUnidad] = useState(""); const [proceso, setProceso] = useState("");
  if (state.loading) return <p className="p-8 text-slate-500">Cargando diagnóstico ambiental...</p>;
  const elementos = state.diagnostico?.elementos || [];
  const grupo = (tipo) => elementos.filter((e) => e.tipo === tipo);
  return <div className="mx-auto max-w-7xl space-y-6">
    <header className="rounded-[28px] border border-emerald-200 bg-emerald-50 p-6"><div className="flex items-center gap-3"><ClipboardCheck className="text-emerald-700" size={32}/><div><p className="text-xs font-black uppercase tracking-widest text-emerald-700">Fundación ambiental</p><h1 className="text-3xl font-black text-slate-900">Diagnóstico Ambiental</h1></div></div><p className="mt-3 text-slate-600">Estado: <b>{state.diagnostico?.estado?.replaceAll("_", " ") || "pendiente"}</b> · Siguiente paso: <b>{state.preparacion?.siguiente_paso}</b></p></header>
    {state.error && <p className="rounded-2xl bg-red-50 p-4 text-red-700">{state.error}</p>}
    <section className="grid gap-4 md:grid-cols-2"><Info title="Información disponible" items={grupo("informacion_disponible")}/><Info title="Brechas e información faltante" items={[...grupo("brecha"), ...grupo("informacion_faltante")]}/></section>
    <section className="rounded-[28px] border border-slate-200 bg-white p-6"><h2 className="text-xl font-black">{state.diagnostico ? "Actualizar diagnóstico" : "Iniciar diagnóstico"}</h2><div className="mt-4 grid gap-3 md:grid-cols-2"><input value={form.objetivo_principal} onChange={(e)=>setForm({...form, objetivo_principal:e.target.value})} placeholder="Objetivo o necesidad principal" className="rounded-xl border p-3"/><input value={form.descripcion_contexto} onChange={(e)=>setForm({...form, descripcion_contexto:e.target.value})} placeholder="Contexto de la organización" className="rounded-xl border p-3"/></div><button onClick={async()=>{await saveDiagnostico(activeOrganizacionId,{...form,estado:"en_progreso"},Boolean(state.diagnostico)); state.reload();}} className="mt-3 rounded-xl bg-emerald-700 px-4 py-2 font-bold text-white">Guardar diagnóstico</button></section>
    <section><h2 className="mb-3 text-xl font-black">Capacidades detectadas y configuradas</h2><CapacidadesAmbientales organizacionId={activeOrganizacionId} capacidades={state.capacidades} onChange={state.reload}/></section>
    <section className="rounded-[28px] border border-slate-200 bg-white p-6"><div className="flex items-center gap-2"><Factory className="text-emerald-700"/><h2 className="text-xl font-black">Estructura operacional</h2></div><div className="mt-4 grid gap-5 md:grid-cols-2"><Structure title="Unidades" items={state.unidades} value={unidad} setValue={setUnidad} onAdd={async()=>{if(unidad){await createUnidad(activeOrganizacionId,{nombre:unidad,tipo:"otro"});setUnidad("");state.reload();}}}/><Structure title="Procesos" items={state.procesos} value={proceso} setValue={setProceso} onAdd={async()=>{if(proceso){await createProceso(activeOrganizacionId,{nombre:proceso,estado:"activo"});setProceso("");state.reload();}}}/></div></section>
  </div>;
}
function Info({title,items}) { return <div className="rounded-2xl border border-slate-200 bg-white p-5"><h2 className="font-black">{title}</h2>{items.length ? <ul className="mt-2 list-disc pl-5 text-sm text-slate-600">{items.map(i=><li key={i.id}>{i.nombre}</li>)}</ul>:<p className="mt-2 text-sm text-slate-500">Aún no se ha registrado información.</p>}</div> }
function Structure({title,items,value,setValue,onAdd}) { return <div><h3 className="font-black">{title}</h3><div className="my-2 flex gap-2"><input value={value} onChange={e=>setValue(e.target.value)} placeholder={`Nueva ${title.toLowerCase()}`} className="min-w-0 flex-1 rounded-xl border p-3"/><button onClick={onAdd} className="rounded-xl bg-slate-900 p-3 text-white"><Plus size={18}/></button></div>{items.map(i=><p key={i.id} className="border-b py-2 text-sm">{i.nombre}</p>)}</div>}
