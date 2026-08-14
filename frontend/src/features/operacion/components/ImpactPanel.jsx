import { useCallback, useEffect, useState } from "react";
import { Calculator } from "lucide-react";
import { calculateImpact, getCalculations, getEligibility } from "../api/calculationV2Api";

export default function ImpactPanel({ organizacionId, activity }) {
  const [eligibility, setEligibility] = useState(null);
  const [calculations, setCalculations] = useState([]);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!activity) return;
    const [eligibilityData, calculationData] = await Promise.all([
      getEligibility(organizacionId, activity.id), getCalculations(organizacionId, activity.id),
    ]);
    setEligibility(eligibilityData); setCalculations(calculationData);
  }, [activity, organizacionId]);
  useEffect(() => { load().catch(() => setError("No se pudo evaluar la actividad.")); }, [load]);
  if (!activity) return null;
  const latest = calculations[0];
  const status = latest ? "calculado" : eligibility?.estado === "no_calculable" ? "no calculable" : eligibility ? "listo para calcular" : "no evaluado";
  return <section className="rounded-2xl border border-violet-200 bg-violet-50/50 p-5">
    <div className="flex items-center gap-2"><Calculator className="text-violet-700"/><h3 className="font-black">Impacto ambiental</h3></div>
    <p className="mt-2 text-sm">Estado: <b>{status}</b></p>
    {eligibility?.metodologia_seleccionada && <div className="mt-3 text-sm"><p>Método: <b>{eligibility.metodologia_seleccionada.nombre} v{eligibility.metodologia_seleccionada.version}</b></p><p>Fórmula: {eligibility.metodologia_seleccionada.formula}</p><p>Factor: {eligibility.metodologia_seleccionada.factor}</p></div>}
    {latest && <div className="mt-3 rounded-xl bg-white p-3 text-sm"><p className="text-lg font-black">{latest.resultado} {latest.unidad_resultado}</p><p>{latest.formula_aplicada}</p><p className="text-xs text-slate-500">Inputs: {latest.inputs.map((item) => `${item.valor_utilizado} ${item.unidad}`).join(" · ")}</p>{latest.advertencias?.map((item) => <p key={item} className="text-amber-700">{item}</p>)}</div>}
    {!latest && eligibility?.estado !== "no_calculable" && <button onClick={async () => { setError(""); try { await calculateImpact(organizacionId, activity.id); await load(); } catch (requestError) { setError(requestError?.response?.data?.error || "No se pudo calcular."); } }} className="mt-3 rounded-xl bg-violet-700 px-4 py-2 text-sm font-black text-white">Calcular impacto</button>}
    {eligibility?.descartados?.map((item) => <p key={item.metodo} className="mt-1 text-xs text-slate-500">{item.metodo}: {item.motivos.join(" ")}</p>)}
    {error && <p className="mt-2 text-xs text-red-700">{error}</p>}
  </section>;
}
