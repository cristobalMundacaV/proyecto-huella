import { useState } from "react";
import { FileSpreadsheet, UploadCloud } from "lucide-react";

import { analyzeIngesta, confirmIngesta, createIngesta, getPreview, saveMapping } from "../services/ingestionV2Api";

const concepts = ["", "identificador_actividad", "fecha_actividad", "distancia_recorrida_km", "masa_transportada_t", "combustible_consumido_l"];

export default function IngestionV2Flow({ organizacionId }) {
  const [stage, setStage] = useState(1);
  const [ingesta, setIngesta] = useState(null);
  const [mappings, setMappings] = useState([]);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [sourceName, setSourceName] = useState("Planilla logística mensual");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function upload(file) {
    if (!file) return;
    setBusy(true); setError("");
    try {
      const created = await createIngesta(organizacionId, file, sourceName);
      setIngesta(created); setStage(2);
      const analysis = await analyzeIngesta(organizacionId, created.id);
      setMappings(analysis.columnas); setStage(3);
    } catch (e) { setError(e?.response?.data?.error || "No se pudo analizar el archivo."); }
    finally { setBusy(false); }
  }

  async function mappingAndPreview() {
    setBusy(true); setError("");
    try { await saveMapping(organizacionId, ingesta.id, mappings); setStage(4); setPreview(await getPreview(organizacionId, ingesta.id)); setStage(5); }
    catch (e) { setError(e?.response?.data?.error || "No se pudo confirmar el mapeo."); }
    finally { setBusy(false); }
  }

  async function process() {
    setBusy(true); setError("");
    try { setResult(await confirmIngesta(organizacionId, ingesta.id)); setStage(7); }
    catch (e) { setError(e?.response?.data?.error || "No se pudo procesar la ingesta."); }
    finally { setBusy(false); }
  }

  return <section className="rounded-[32px] border border-cyan-200 bg-white p-6 shadow-[var(--shadow-card)]">
    <div className="flex items-center gap-3"><FileSpreadsheet className="text-cyan-700"/><div><p className="text-xs font-black uppercase tracking-widest text-cyan-700">Ingesta y evidencia v2</p><h2 className="text-2xl font-black">Documento → actividades → observaciones</h2></div></div>
    <div className="mt-4 grid grid-cols-2 gap-2 text-center text-xs font-black sm:grid-cols-7">{["Cargar","Analizar","Mapear","Confirmar","Preview","Procesar","Resultado"].map((label,index)=><span key={label} className={`rounded-xl p-2 ${stage>=index+1?"bg-cyan-700 text-white":"bg-slate-100 text-slate-500"}`}>{index+1}. {label}</span>)}</div>
    {error && <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {!ingesta && <div className="mt-5 grid gap-3 md:grid-cols-[1fr_1fr]"><label className="text-sm font-bold">Fuente lógica<input value={sourceName} onChange={e=>setSourceName(e.target.value)} className="mt-1 w-full rounded-xl border p-3 font-normal"/></label><label className="flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-cyan-300 bg-cyan-50 p-4 font-black text-cyan-800"><UploadCloud/> {busy?"Analizando...":"Cargar CSV/XLSX"}<input type="file" accept=".csv,.xlsx,.xls" className="hidden" disabled={busy} onChange={e=>upload(e.target.files?.[0])}/></label></div>}
    {mappings.length>0 && !preview && <div className="mt-5"><h3 className="font-black">Columnas detectadas y mapeo</h3><div className="mt-3 space-y-2">{mappings.map((item,index)=><div key={item.columna_normalizada} className="grid gap-2 rounded-xl border p-3 md:grid-cols-[1fr_1fr_120px]"><span><b>{item.columna_origen}</b><small className="block text-slate-500">{item.reconocida?`Reconocida por ${item.origen_mapeo}`:"Requiere mapeo"}</small></span><select value={item.concepto_normalizado} onChange={e=>setMappings(current=>current.map((row,i)=>i===index?{...row,concepto_normalizado:e.target.value}:row))} className="rounded-lg border p-2">{concepts.map(value=><option key={value} value={value}>{value||"Sin mapear"}</option>)}</select><input placeholder="Unidad" value={item.unidad_esperada} onChange={e=>setMappings(current=>current.map((row,i)=>i===index?{...row,unidad_esperada:e.target.value}:row))} className="rounded-lg border p-2"/></div>)}</div><button disabled={busy||mappings.some(x=>!x.concepto_normalizado)} onClick={mappingAndPreview} className="mt-4 rounded-xl bg-cyan-700 px-4 py-2 font-black text-white disabled:opacity-40">Confirmar mapeo y previsualizar</button></div>}
    {preview && !result && <div className="mt-5"><div className="flex gap-3"><b>{preview.filas_validas} filas válidas</b><b className="text-amber-700">{preview.filas_problematicas} problemáticas</b></div><div className="mt-3 max-h-72 overflow-auto rounded-xl border"><table className="w-full text-sm"><thead><tr><th className="p-2 text-left">Fila</th><th className="text-left">Actividad prevista</th><th className="text-left">Observaciones</th><th className="text-left">Errores</th></tr></thead><tbody>{preview.filas.map(row=><tr key={row.numero_fila} className="border-t"><td className="p-2">{row.numero_fila}</td><td>{row.actividad?.codigo||"—"}</td><td>{row.actividad?.observaciones??0}</td><td className="text-red-600">{row.errores.join(", ")}</td></tr>)}</tbody></table></div><button disabled={busy} onClick={process} className="mt-4 rounded-xl bg-emerald-700 px-4 py-2 font-black text-white">Procesar actividades y observaciones</button></div>}
    {result && <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 p-5"><h3 className="font-black text-emerald-900">Ingesta completada</h3><p className="mt-2 text-sm">{result.actividades_creadas} actividades · {result.observaciones_creadas ?? 0} observaciones · {result.filas_con_error} filas con error</p></div>}
  </section>;
}
