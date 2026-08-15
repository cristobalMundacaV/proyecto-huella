import { useCallback, useEffect, useState } from "react";
import { Activity, Database, Plus, X } from "lucide-react";

import { getProcesos, getUnidades } from "@/features/diagnostico/api/diagnosticoApi";
import { createActividad, createFuente, createObservacion, getActividad, getActividades, getFuentes } from "../api/activityCoreApi";
import ImpactPanel from "./ImpactPanel";
import ActivityQualityPanel from "@/features/quality/components/ActivityQualityPanel";

const nowLocal = () => new Date().toISOString().slice(0, 16);
const activityInitial = { tipo: "transporte", codigo: "", nombre: "", timestamp_inicio: nowLocal(), estado: "registrada", unidad_operacional: "", proceso_operacional: "" };
const sourceInitial = { nombre: "", tipo: "manual", descripcion: "" };
const observationInitial = { fuente: "", concepto: "", valor_numerico: "", valor_texto: "", unidad: "", timestamp_observacion: nowLocal(), metodo_captura: "manual", naturaleza: "declarativo" };

export default function ActivityCorePanel({ organizacionId }) {
  const [data, setData] = useState({ actividades: [], fuentes: [], unidades: [], procesos: [] });
  const [selected, setSelected] = useState(null);
  const [modal, setModal] = useState("");
  const [activityForm, setActivityForm] = useState(activityInitial);
  const [sourceForm, setSourceForm] = useState(sourceInitial);
  const [observationForm, setObservationForm] = useState(observationInitial);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!organizacionId) return;
    try {
      const [actividades, fuentes, unidades, procesos] = await Promise.all([getActividades(organizacionId), getFuentes(organizacionId), getUnidades(organizacionId), getProcesos(organizacionId)]);
      setData({ actividades, fuentes, unidades, procesos });
      if (selected?.id) setSelected(await getActividad(organizacionId, selected.id));
    } catch (requestError) { setError(requestError?.response?.data?.detail || "No se pudo cargar el núcleo operacional."); }
  }, [organizacionId, selected?.id]);
  useEffect(() => { load(); }, [load]);

  async function submit(action) {
    setError("");
    try { await action(); setModal(""); await load(); }
    catch (requestError) { setError(JSON.stringify(requestError?.response?.data || "No se pudo guardar.")); }
  }

  return <section className="rounded-[32px] border border-cyan-200 bg-white p-6 shadow-[var(--shadow-card)]">
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between"><div><p className="text-xs font-black uppercase tracking-[0.22em] text-cyan-700">Activity Core</p><h2 className="mt-1 text-2xl font-black">Actividades operacionales</h2><p className="mt-1 text-sm text-slate-500">Hechos operacionales y datos observados, sin cálculo de emisiones.</p></div><div className="flex flex-wrap gap-2"><Action onClick={()=>setModal("fuente")} icon={Database}>Nueva fuente</Action><Action onClick={()=>setModal("actividad")} icon={Plus}>Nueva actividad</Action>{selected && <Action onClick={()=>setModal("observacion")} icon={Plus}>Nueva observación</Action>}</div></div>
    {error && <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(360px,0.9fr)]"><div className="overflow-x-auto"><table className="w-full min-w-[720px] text-sm"><thead><tr className="border-b text-left text-xs uppercase text-slate-500"><th className="p-3">Actividad</th><th>Tipo</th><th>Proceso / unidad</th><th>Fecha</th><th>Estado</th><th>Datos</th></tr></thead><tbody>{data.actividades.map((item)=><tr key={item.id} onClick={async()=>setSelected(await getActividad(organizacionId,item.id))} className="cursor-pointer border-b hover:bg-cyan-50"><td className="p-3 font-black">{item.nombre}<span className="block text-xs font-normal text-slate-500">{item.codigo}</span></td><td>{item.tipo.replaceAll("_"," ")}</td><td>{item.proceso_nombre || "—"}<span className="block text-xs text-slate-500">{item.unidad_nombre || "Sin unidad"}</span></td><td>{String(item.timestamp_inicio).slice(0,10)}</td><td>{item.estado.replaceAll("_"," ")}</td><td>{item.observaciones_count}</td></tr>)}</tbody></table>{data.actividades.length===0&&<p className="p-6 text-center text-sm text-slate-500">No hay actividades registradas.</p>}</div><div className="space-y-4"><ActivityDetail activity={selected}/><ActivityQualityPanel organizacionId={organizacionId} activity={selected}/><ImpactPanel organizacionId={organizacionId} activity={selected}/></div></div>
    {modal && <Modal title={modal === "actividad" ? "Nueva actividad" : modal === "fuente" ? "Nueva fuente de datos" : "Nueva observación"} onClose={()=>setModal("")}>{modal === "actividad" ? <ActivityForm value={activityForm} setValue={setActivityForm} data={data} onSave={()=>submit(()=>createActividad(organizacionId, clean(activityForm)))}/> : modal === "fuente" ? <SourceForm value={sourceForm} setValue={setSourceForm} onSave={()=>submit(()=>createFuente(organizacionId,sourceForm))}/> : <ObservationForm value={observationForm} setValue={setObservationForm} fuentes={data.fuentes} onSave={()=>submit(()=>createObservacion(organizacionId,selected.id,clean(observationForm)))}/>}</Modal>}
  </section>;
}

const clean = (value) => Object.fromEntries(Object.entries(value).filter(([,item]) => item !== ""));
function Action({children,icon:Icon,onClick}) { return <button type="button" onClick={onClick} className="inline-flex items-center gap-2 rounded-xl border border-cyan-200 bg-cyan-50 px-3 py-2 text-xs font-black text-cyan-900"><Icon size={15}/>{children}</button> }
function Modal({title,onClose,children}) { return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4"><div className="w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl"><div className="flex justify-between"><h3 className="text-xl font-black">{title}</h3><button onClick={onClose}><X/></button></div><div className="mt-5">{children}</div></div></div> }
const Input = ({label,...props}) => <label className="text-sm font-bold text-slate-700">{label}<input {...props} className="mt-1 w-full rounded-xl border p-3 font-normal"/></label>;
const Select = ({label,children,...props}) => <label className="text-sm font-bold text-slate-700">{label}<select {...props} className="mt-1 w-full rounded-xl border p-3 font-normal">{children}</select></label>;
function Save({onClick}) { return <button type="button" onClick={onClick} className="mt-4 rounded-xl bg-cyan-700 px-4 py-2 font-black text-white">Guardar</button> }
function ActivityForm({value,setValue,data,onSave}) { const set=(field)=>(e)=>setValue({...value,[field]:e.target.value}); return <div className="grid gap-3 md:grid-cols-2"><Input label="Código estable" value={value.codigo} onChange={set("codigo")}/><Input label="Nombre" value={value.nombre} onChange={set("nombre")}/><Select label="Tipo" value={value.tipo} onChange={set("tipo")}>{["transporte","consumo_energia","consumo_agua","consumo_combustible","consumo_combustible_estacionario","operacion_maquinaria","movimiento_material","gestion_residuo","generacion_energia","monitoreo_ruido","gestion_hidrica_suelo","proceso_productivo","otro"].map(x=><option key={x}>{x}</option>)}</Select><Input label="Inicio" type="datetime-local" value={value.timestamp_inicio} onChange={set("timestamp_inicio")}/><Select label="Unidad" value={value.unidad_operacional} onChange={set("unidad_operacional")}><option value="">Sin unidad</option>{data.unidades.map(x=><option key={x.id} value={x.id}>{x.nombre}</option>)}</Select><Select label="Proceso" value={value.proceso_operacional} onChange={set("proceso_operacional")}><option value="">Sin proceso</option>{data.procesos.map(x=><option key={x.id} value={x.id}>{x.nombre}</option>)}</Select><div><Save onClick={onSave}/></div></div> }
function SourceForm({value,setValue,onSave}) { const set=(field)=>(e)=>setValue({...value,[field]:e.target.value}); return <div className="grid gap-3 md:grid-cols-2"><Input label="Nombre" value={value.nombre} onChange={set("nombre")}/><Select label="Tipo" value={value.tipo} onChange={set("tipo")}>{["manual","documento","excel_csv","api","gps","sensor","telemetria","erp","sistema_externo","sistema","otro"].map(x=><option key={x}>{x}</option>)}</Select><Input label="Descripción" value={value.descripcion} onChange={set("descripcion")}/><div><Save onClick={onSave}/></div></div> }
function ObservationForm({value,setValue,fuentes,onSave}) { const set=(field)=>(e)=>setValue({...value,[field]:e.target.value}); return <div className="grid gap-3 md:grid-cols-2"><Select label="Fuente" value={value.fuente} onChange={set("fuente")}><option value="">Seleccionar</option>{fuentes.map(x=><option key={x.id} value={x.id}>{x.nombre}</option>)}</Select><Input label="Concepto normalizado" placeholder="distancia_recorrida_km" value={value.concepto} onChange={set("concepto")}/><Input label="Valor numérico" type="number" step="any" value={value.valor_numerico} onChange={set("valor_numerico")}/><Input label="Valor textual (alternativo)" value={value.valor_texto} onChange={set("valor_texto")}/><Input label="Unidad" value={value.unidad} onChange={set("unidad")}/><Input label="Momento observado" type="datetime-local" value={value.timestamp_observacion} onChange={set("timestamp_observacion")}/><Select label="Método" value={value.metodo_captura} onChange={set("metodo_captura")}>{["manual","extraido_automaticamente","importado","api","instrumental","derivado"].map(x=><option key={x}>{x}</option>)}</Select><div><Save onClick={onSave}/></div></div> }
function ActivityDetail({activity}) { if(!activity)return <div className="rounded-2xl border border-dashed p-6 text-sm text-slate-500"><Activity className="mb-3"/>Selecciona una actividad para reconstruir sus datos y fuentes.</div>; return <div className="rounded-2xl border border-slate-200 p-5"><h3 className="text-xl font-black">{activity.nombre}</h3><p className="text-xs text-slate-500">{activity.codigo} · {activity.estado.replaceAll("_"," ")}</p><h4 className="mt-5 font-black">Datos observados</h4><div className="mt-2 space-y-2">{activity.observaciones.map(x=><div key={x.id} className="rounded-xl bg-slate-50 p-3 text-sm"><b>{x.concepto}</b><span className="block">{x.valor_numerico ?? x.valor_texto} {x.unidad}</span><span className="text-xs text-slate-500">{x.fuente_detalle?.nombre} · {x.metodo_captura} · {String(x.timestamp_observacion).slice(0,16)}</span>{x.evidencia_detalle&&<span className="block text-xs text-emerald-700">Fuente documental: {x.evidencia_detalle.nombre}</span>}{x.version_evidencia_detalle&&<span className="block text-xs text-emerald-700">Versión: {x.version_evidencia_detalle.version} · Archivo: {x.version_evidencia_detalle.nombre_original}</span>}</div>)}{activity.observaciones.length===0&&<p className="text-sm text-slate-500">Sin observaciones todavía.</p>}</div><h4 className="mt-5 font-black">Fuentes</h4><p className="text-sm text-slate-600">{[...new Set(activity.observaciones.map(x=>x.fuente_detalle?.nombre).filter(Boolean))].join(", ") || "Sin fuentes observadas"}</p></div> }
