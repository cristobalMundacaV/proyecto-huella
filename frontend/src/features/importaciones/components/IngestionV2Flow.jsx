import { useState } from "react";
import { FileSpreadsheet, UploadCloud } from "lucide-react";

import { analyzeIngesta, confirmIngesta, createIngesta, getPreview, saveMapping } from "../services/ingestionV2Api";

const concepts = ["", "identificador_actividad", "fecha_actividad", "periodo_inicio", "periodo_fin", "distancia_recorrida_km", "masa_transportada_t", "combustible_consumido_l", "consumo_energia", "consumo_agua", "combustible_consumido", "energia_generada", "energia_autoconsumida", "energia_exportada", "material", "cantidad_material", "tipo_evento_material", "lote_material", "cantidad_residuo", "nivel_ruido", "superficie_intervenida", "estado_drenaje", "desborde", "erosion_observada", "unidad", "obra", "proceso", "activo", "punto_medicion"];
const destinations = [{ value: "transporte", label: "Transporte" }, { value: "material", label: "Materiales" }, { value: "flujo_ambiental", label: "Flujo ambiental" }, { value: "actividad_generica", label: "Actividad genérica" }];
const flows = [{ value: "energia", label: "Energía" }, { value: "agua", label: "Agua" }, { value: "combustible_estacionario", label: "Combustible estacionario" }, { value: "generacion_propia", label: "Generación propia" }, { value: "residuo", label: "Residuos" }, { value: "ruido", label: "Ruido" }, { value: "gestion_hidrica_suelo", label: "Gestión hídrica/suelo" }];

export default function IngestionV2Flow({ organizacionId }) {
  const [stage, setStage] = useState(1);
  const [ingesta, setIngesta] = useState(null);
  const [mappings, setMappings] = useState([]);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [sourceName, setSourceName] = useState("Fuente operacional");
  const [destination, setDestination] = useState("transporte");
  const [flow, setFlow] = useState("energia");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function upload(file) {
    if (!file) return;
    setBusy(true); setError("");
    try {
      const created = await createIngesta(organizacionId, file, sourceName, { destino: destination, flujo: destination === "flujo_ambiental" ? flow : "" });
      setIngesta(created); setStage(2);
      const analysis = await analyzeIngesta(organizacionId, created.id);
      setMappings(analysis.columnas); setStage(3);
    } catch (requestError) { setError(requestError?.response?.data?.error || "No se pudo analizar el archivo."); }
    finally { setBusy(false); }
  }

  async function mappingAndPreview() {
    setBusy(true); setError("");
    try {
      await saveMapping(organizacionId, ingesta.id, mappings, { destino: destination, flujo: destination === "flujo_ambiental" ? flow : "" });
      setStage(4); setPreview(await getPreview(organizacionId, ingesta.id)); setStage(5);
    } catch (requestError) { setError(requestError?.response?.data?.error || "No se pudo confirmar el mapeo."); }
    finally { setBusy(false); }
  }

  async function process() {
    setBusy(true); setError("");
    try { setResult(await confirmIngesta(organizacionId, ingesta.id)); setStage(7); }
    catch (requestError) { setError(requestError?.response?.data?.error || "No se pudo procesar la ingesta."); }
    finally { setBusy(false); }
  }

  return <section className="rounded-[32px] border border-cyan-200 bg-white p-6 shadow-[var(--shadow-card)]">
    <div className="flex items-center gap-3"><FileSpreadsheet className="text-cyan-700"/><div><p className="text-xs font-black uppercase tracking-widest text-cyan-700">Ingesta multiflujo</p><h2 className="text-2xl font-black">Evidencia → hechos operacionales trazables</h2></div></div>
    <div className="mt-4 grid grid-cols-2 gap-2 text-center text-xs font-black sm:grid-cols-7">{["Cargar","Analizar","Mapear","Contexto","Preview","Confirmar","Resultado"].map((label,index)=><span key={label} className={`rounded-xl p-2 ${stage>=index+1?"bg-cyan-700 text-white":"bg-slate-100 text-slate-500"}`}>{index+1}. {label}</span>)}</div>
    {error && <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {!ingesta && <div className="mt-5 grid gap-3 md:grid-cols-2">
      <label className="text-sm font-bold">Fuente lógica<input value={sourceName} onChange={event=>setSourceName(event.target.value)} className="mt-1 w-full rounded-xl border p-3 font-normal"/></label>
      <label className="text-sm font-bold">Destino<select value={destination} onChange={event=>setDestination(event.target.value)} className="mt-1 w-full rounded-xl border p-3 font-normal">{destinations.map(item=><option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
      {destination === "flujo_ambiental" && <label className="text-sm font-bold">Flujo<select value={flow} onChange={event=>setFlow(event.target.value)} className="mt-1 w-full rounded-xl border p-3 font-normal">{flows.map(item=><option key={item.value} value={item.value}>{item.label}</option>)}</select></label>}
      <label className="flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-cyan-300 bg-cyan-50 p-4 font-black text-cyan-800"><UploadCloud/> {busy?"Analizando...":"Cargar CSV/XLSX"}<input type="file" accept=".csv,.xlsx,.xls" className="hidden" disabled={busy} onChange={event=>upload(event.target.files?.[0])}/></label>
    </div>}
    {ingesta && <div className="mt-4 rounded-xl bg-cyan-50 p-3 text-sm"><b>Clasificación sugerida:</b> {ingesta.clasificacion_sugerida || "otro"} · <b>Destino:</b> {ingesta.destino_operacional}{ingesta.flujo ? ` / ${ingesta.flujo}` : ""}</div>}
    {mappings.length>0 && !preview && <div className="mt-5"><h3 className="font-black">Columnas detectadas y mapeo</h3><div className="mt-3 space-y-2">{mappings.map((item,index)=><div key={item.columna_normalizada} className="grid gap-2 rounded-xl border p-3 md:grid-cols-[1fr_1fr_120px]"><span><b>{item.columna_origen}</b><small className="block text-slate-500">{item.reconocida?`Reconocida por ${item.origen_mapeo}`:"Requiere mapeo"}</small></span><select value={item.concepto_normalizado} onChange={event=>setMappings(current=>current.map((row,rowIndex)=>rowIndex===index?{...row,concepto_normalizado:event.target.value}:row))} className="rounded-lg border p-2">{concepts.map(value=><option key={value} value={value}>{value||"Sin mapear"}</option>)}</select><input placeholder="Unidad" value={item.unidad_esperada} onChange={event=>setMappings(current=>current.map((row,rowIndex)=>rowIndex===index?{...row,unidad_esperada:event.target.value}:row))} className="rounded-lg border p-2"/></div>)}</div><button disabled={busy||mappings.some(item=>!item.concepto_normalizado)} onClick={mappingAndPreview} className="mt-4 rounded-xl bg-cyan-700 px-4 py-2 font-black text-white disabled:opacity-40">Guardar mapeo y previsualizar</button></div>}
    {preview && !result && <div className="mt-5"><div className="flex gap-3"><b>{preview.filas_validas} filas válidas</b><b className="text-amber-700">{preview.filas_problematicas} requieren revisión</b></div><div className="mt-3 max-h-96 space-y-3 overflow-auto rounded-xl border p-3">{preview.filas.map(row=><article key={row.numero_fila} className="rounded-xl border p-3 text-sm"><div className="flex justify-between"><b>Fila {row.numero_fila} · {row.estado}</b><span>{row.destino}{row.flujo ? ` / ${row.flujo}` : ""}</span></div><div className="mt-2 grid gap-2 md:grid-cols-2"><pre className="overflow-auto rounded-lg bg-slate-50 p-2 text-xs"><b>RAW</b>{"\n"}{JSON.stringify(row.datos_originales, null, 2)}</pre><pre className="overflow-auto rounded-lg bg-cyan-50 p-2 text-xs"><b>NORMALIZADO</b>{"\n"}{JSON.stringify(row.datos_normalizados, null, 2)}</pre></div>{row.problemas?.map(problem=><p key={`${problem.codigo}-${problem.campo}`} className="mt-2 text-red-700">{problem.codigo} · {problem.campo}: {problem.detalle}</p>)}</article>)}</div><button disabled={busy || preview.filas_validas === 0} onClick={process} className="mt-4 rounded-xl bg-emerald-700 px-4 py-2 font-black text-white disabled:opacity-40">Confirmar hechos operacionales</button></div>}
    {result && <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 p-5"><h3 className="font-black text-emerald-900">Ingesta completada</h3><p className="mt-2 text-sm">{result.actividades_creadas} actividades · {result.observaciones_creadas ?? 0} observaciones · {result.filas_con_error} filas con error</p></div>}
  </section>;
}
