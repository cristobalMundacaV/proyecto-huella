import { useEffect, useMemo, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { getDiscrepancies, getObservationQuality } from "../api/qualityV2Api";

export default function ActivityQualityPanel({ organizacionId, activity }) {
  const [quality, setQuality] = useState([]); const [discrepancies, setDiscrepancies] = useState([]);
  useEffect(() => { if (!organizacionId || !activity) return; Promise.all([getObservationQuality(organizacionId), getDiscrepancies(organizacionId)]).then(([q,d])=>{ setQuality(q); setDiscrepancies(d); }).catch(()=>{}); }, [organizacionId, activity]);
  const ids = useMemo(()=>new Set((activity?.observaciones || []).map(x=>x.id)),[activity]); if (!activity) return null;
  const scoped = quality.filter(x=>ids.has(x.observacion)); const alerts = discrepancies.filter(x=>x.actividad===activity.id);
  return <div className="rounded-2xl border border-emerald-200 p-5"><h4 className="flex items-center gap-2 font-black"><ShieldCheck size={18}/>Calidad de datos</h4><div className="mt-3 space-y-2">{scoped.map(x=><div key={x.id} className="rounded-xl bg-emerald-50 p-3 text-xs"><b>{x.observacion_detalle.concepto}</b> · {x.observacion_detalle.fuente}<span className="block text-emerald-800">{x.estado.replaceAll("_"," ")}</span></div>)}</div><p className="mt-3 text-xs text-slate-600">Discrepancias: {alerts.length} · La selección automática solo se aplica con una política inequívoca.</p></div>;
}
