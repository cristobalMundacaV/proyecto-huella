import { updateCapacidad } from "../api/diagnosticoApi";

const estados = ["pendiente_diagnostico", "aplica", "no_aplica", "sin_datos", "construyendo_linea_base", "operativa"];
const label = (value) => value.replaceAll("_", " ");

export default function CapacidadesAmbientales({ organizacionId, capacidades, onChange }) {
  return <div className="grid gap-3 md:grid-cols-2">{capacidades.map((item) => (
    <div key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3"><div><h3 className="font-black text-slate-900">{item.capacidad.nombre}</h3><p className="text-xs text-slate-500">{item.recomendada_por_preset ? "Recomendada por el preset" : "Configuración manual"}</p></div>
      <select aria-label={`Estado de ${item.capacidad.nombre}`} value={item.estado} onChange={async (e) => { await updateCapacidad(organizacionId, item.id, { estado: e.target.value }); onChange?.(); }} className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-bold">
        {estados.map((estado) => <option key={estado} value={estado}>{label(estado)}</option>)}
      </select></div>
    </div>
  ))}</div>;
}
