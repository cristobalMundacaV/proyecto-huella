import { RotateCcw } from "lucide-react";
import { Button } from "@/shared/ui";

export function suggestedRelations(areaKeys, flowKeys, suggestions) {
  return Object.fromEntries(areaKeys.map((area) => [area, (suggestions[area] || []).filter((flow) => flowKeys.includes(flow))]));
}

export default function AreaFlowMatrix({ areas, flows, relations, suggestions, onChange }) {
  const toggle = (area, flow) => { const current = relations[area] || []; onChange({ ...relations, [area]: current.includes(flow) ? current.filter((item) => item !== flow) : [...current, flow] }); };
  const restore = () => onChange(suggestedRelations(areas.map((row) => row.tipo), flows.map((row) => row.clave), suggestions));
  return <section className="mt-8 border-t border-slate-200 pt-7"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-2xl font-black">¿De dónde proviene la información?</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Carbono Zero preparó estas relaciones según tu estructura y sector. Indican dónde puede originarse o administrarse información; no conceden permisos ni responsabilidad legal.</p></div><Button variant="secondary" leftIcon={RotateCcw} onClick={restore}>Restaurar sugerencias</Button></div><div className="mt-6 space-y-4">{areas.map((area) => <article key={area.tipo} className="rounded-2xl border border-slate-200 p-5"><h3 className="font-black">{area.nombre}</h3><div className="mt-3 flex flex-wrap gap-2">{flows.map((flow) => { const checked = (relations[area.tipo] || []).includes(flow.clave); return <button key={flow.clave} type="button" aria-pressed={checked} onClick={() => toggle(area.tipo, flow.clave)} className={`rounded-full border px-3 py-2 text-xs font-bold transition ${checked ? "border-emerald-500 bg-emerald-100 text-emerald-900" : "border-slate-200 bg-white text-slate-600 hover:border-emerald-300"}`}>{checked ? "✓ " : ""}{flow.nombre}</button>})}</div></article>)}</div></section>;
}
