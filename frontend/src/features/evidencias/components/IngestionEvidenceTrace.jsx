import { useEffect, useState } from "react";
import { FileClock } from "lucide-react";

import { getIngestas } from "@/features/importaciones/services/ingestionV2Api";

export default function IngestionEvidenceTrace({ organizacionId }) {
  const [ingestas, setIngestas] = useState([]);
  useEffect(() => {
    let active = true;
    if (organizacionId) getIngestas(organizacionId).then((rows) => { if (active) setIngestas(rows); }).catch(() => { if (active) setIngestas([]); });
    return () => { active = false; };
  }, [organizacionId]);
  if (!ingestas.length) return null;
  return <section className="rounded-[28px] border border-cyan-200 bg-white p-5 shadow-[var(--shadow-card)]"><div className="flex items-center gap-2"><FileClock className="text-cyan-700"/><div><p className="text-xs font-black uppercase tracking-widest text-cyan-700">Trazabilidad de ingestas</p><h2 className="text-xl font-black">Evidencia → ingesta → actividad</h2></div></div><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[760px] text-sm"><thead><tr className="border-b text-left text-xs uppercase text-slate-500"><th className="p-3">Archivo</th><th>Versión</th><th>Tipo</th><th>Fecha</th><th>Fuente</th><th>Estado</th><th>Actividades / filas</th></tr></thead><tbody>{ingestas.map(item=><tr key={item.id} className="border-b"><td className="p-3 font-black">{item.version_evidencia_detalle?.nombre_original}</td><td>v{item.version_evidencia_detalle?.version}</td><td>{item.tipo_ingesta}</td><td>{String(item.created_at).slice(0,10)}</td><td>{item.fuente_nombre}</td><td>{item.estado.replaceAll("_"," ")}</td><td>{item.filas_procesadas} / {item.filas_detectadas}</td></tr>)}</tbody></table></div></section>;
}
