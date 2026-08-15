import { useCallback, useEffect, useState } from "react";
import { BookOpenCheck } from "lucide-react";
import { getKnowledgeAggregate, getKnowledgeCases } from "../api/knowledgeApi";

export default function EnvironmentalKnowledge({ organizationId }) {
  const [cases, setCases] = useState([]);
  const [aggregate, setAggregate] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!organizationId) return;
    const [own, general] = await Promise.all([getKnowledgeCases(organizationId), getKnowledgeAggregate(organizationId)]);
    setCases(own); setAggregate(general);
  }, [organizationId]);
  useEffect(() => { load().catch(() => setError("No se pudo cargar el conocimiento ambiental.")); }, [load]);
  return <section className="mt-8 rounded-[32px] border border-emerald-200 bg-white p-6 shadow-[var(--shadow-card)]">
    <div className="flex items-start gap-3"><BookOpenCheck className="text-emerald-700"/><div><p className="text-xs font-black uppercase tracking-[0.22em] text-emerald-700">Conocimiento ambiental</p><h2 className="text-2xl font-black">Casos medidos y comparables</h2><p className="text-sm text-slate-600">Los agregados son anónimos y describen antecedentes, no garantías de resultado.</p></div></div>
    {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
    {aggregate && <div className="mt-5 grid gap-3 md:grid-cols-3"><Card label="Casos comparables" value={aggregate.casos_comparables}/><Card label="Resultados" value={Object.entries(aggregate.resultados).map(([key,value])=>`${key}: ${value}`).join(" · ") || "Sin casos"}/><Card label="Evidencia" value={Object.entries(aggregate.fuerza_evidencia).map(([key,value])=>`${key}: ${value}`).join(" · ") || "Sin casos"}/></div>}
    <div className="mt-5 grid gap-3 md:grid-cols-2">{cases.map(item=><article key={item.id} className="rounded-2xl border p-4"><div className="flex justify-between gap-3"><b>{item.categoria_ambiental} · {item.tipo_accion}</b><span className="text-xs font-black uppercase">{item.estado}</span></div><p className="mt-2 text-sm">Resultado: <b>{item.resultado}</b></p><p className="text-sm">Evidencia: <b>{item.fuerza_evidencia}</b> · versión {item.version}</p><p className="mt-2 text-xs text-slate-500">{item.grado_implementacion} · {item.viabilidad}</p></article>)}</div>
  </section>;
}

function Card({ label, value }) { return <div className="rounded-2xl bg-emerald-50 p-4"><p className="text-xs font-black uppercase text-emerald-800">{label}</p><p className="mt-1 font-bold">{value}</p></div>; }
