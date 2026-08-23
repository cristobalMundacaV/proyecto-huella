import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, FileSpreadsheet } from "lucide-react";
import { Link } from "react-router-dom";

import { Alert, Button, Card, CardContent } from "@/shared/ui";
import { getEnvironmentalDomain, OPERATIONAL_DOMAIN_KEYS } from "@/shared/config/environmentalDomains";
import { getOrganizationWorks, getWorkContext } from "@/features/obras/services/workspaceApi";
import { analyzeImport, confirmImport, createImport, previewImport, saveImportMapping } from "../services/dataApi";
import { destinationLabel } from "../utils/dataPresentation";
import FileDropzone from "./FileDropzone";
import ImportContextSummary from "./ImportContextSummary";
import ImportScopeSelector from "./ImportScopeSelector";
import MappingTable from "./MappingTable";

const concepts = ["", "identificador_actividad", "fecha_actividad", "periodo_inicio", "periodo_fin", "distancia_recorrida_km", "masa_transportada_t", "combustible_consumido_l", "consumo_energia", "consumo_agua", "material", "cantidad_material", "cantidad_residuo", "nivel_ruido", "unidad", "obra", "proceso", "activo", "punto_medicion"];
const destinations = ["actividad_generica", "transporte", "material", "flujo_ambiental"];
const steps = ["Alcance", "Archivo", "Entender", "Revisar", "Confirmar", "Resultado"];
const scopeLabels = { organizacion: "Organización completa", obra: "Obra específica", dominio: "Ámbito ambiental" };
const conceptLabels = {
  identificador_actividad: "Identificador de actividad", fecha_actividad: "Fecha de actividad", periodo_inicio: "Inicio del período", periodo_fin: "Fin del período",
  distancia_recorrida_km: "Distancia recorrida", masa_transportada_t: "Masa transportada", combustible_consumido_l: "Combustible consumido",
  consumo_energia: "Consumo de energía", consumo_agua: "Consumo de agua", material: "Material", cantidad_material: "Cantidad de material",
  cantidad_residuo: "Cantidad de residuo", nivel_ruido: "Nivel de ruido", unidad: "Unidad", obra: "Obra", proceso: "Proceso", activo: "Activo", punto_medicion: "Punto de medición",
};
const domainFlow = { energia: "energia", agua: "agua", combustibles: "combustible_estacionario", residuos: "residuo", ruido: "ruido", hidrica_suelo: "gestion_hidrica_suelo" };
const domainDestination = { transporte: "transporte", materiales: "material" };
const rowsFrom = (value) => Array.isArray(value) ? value : value?.results || [];
const resultValue = (value) => value === null || value === undefined ? "Sin datos" : value;

export default function ImportWorkflow({ organizationId, onCompleted, onClose }) {
  const [stage, setStage] = useState(1);
  const [scope, setScope] = useState("");
  const [workId, setWorkId] = useState("");
  const [domain, setDomain] = useState("");
  const [works, setWorks] = useState([]);
  const [applicableDomains, setApplicableDomains] = useState([]);
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [file, setFile] = useState(null);
  const [process, setProcess] = useState(null);
  const [mappings, setMappings] = useState([]);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const mountedRef = useRef(true);

  useEffect(() => () => { mountedRef.current = false; }, []);
  useEffect(() => {
    getOrganizationWorks(organizationId).then((data) => mountedRef.current && setWorks(rowsFrom(data))).catch(() => mountedRef.current && setError("No fue posible cargar las obras de la organización."));
  }, [organizationId]);
  useEffect(() => {
    setDomain("");
    setApplicableDomains([]);
    if (!workId || scope !== "dominio") return;
    getWorkContext(organizationId, workId).then(({ context }) => {
      if (!mountedRef.current) return;
      const states = new Map((context?.diagnostico_obra?.aplicabilidad || []).map((item) => [item.clave, item.estado_obra]));
      setApplicableDomains(OPERATIONAL_DOMAIN_KEYS.filter((key) => {
        const capability = key === "hidrica_suelo" ? "gestion_hidrica_suelo" : key;
        return ["aplica", "sin_datos"].includes(states.get(capability));
      }));
    }).catch(() => mountedRef.current && setError("No fue posible verificar la aplicabilidad de esta obra."));
  }, [organizationId, scope, workId]);

  const selectedWork = works.find((work) => String(work.id || work.obra_id) === String(workId));
  const selectedDomain = getEnvironmentalDomain(domain);
  const context = useMemo(() => ({
    alcance: scope,
    alcance_label: scopeLabels[scope],
    ...(workId ? { obra_id: Number(workId), obra_nombre: selectedWork?.nombre || "" } : {}),
    ...(domain ? { dominio: domain, dominio_label: selectedDomain?.label || "" } : {}),
  }), [domain, scope, selectedDomain?.label, selectedWork?.nombre, workId]);
  const summary = {
    scopeLabel: scopeLabels[scope], workName: selectedWork?.nombre, domainLabel: selectedDomain?.label,
    source, destinationLabel: destinationLabel(destination), fileName: file?.name || process?.version_evidencia_detalle?.nombre_original,
  };
  const scopeComplete = scope === "organizacion" || (scope === "obra" && workId) || (scope === "dominio" && workId && domain);
  const contextComplete = scopeComplete && destination && source.trim();
  const reviewRows = preview?.filas?.filter((row) => row.estado === "requiere_revision" || row.problemas?.length || row.errores?.length) || [];
  const mappedColumns = mappings.filter((item) => item.concepto_normalizado).length;

  function selectScope(next) {
    setScope(next); setWorkId(""); setDomain("");
  }
  function resetWorkflow() {
    setStage(1); setScope(""); setWorkId(""); setDomain(""); setSource(""); setDestination("");
    setFile(null); setProcess(null); setMappings([]); setPreview(null); setResult(null); setError("");
  }
  function selectDomain(next) {
    setDomain(next);
    setDestination(domainDestination[next] || "flujo_ambiental");
  }
  async function uploadAndAnalyze() {
    if (!file || !contextComplete) return;
    setBusy(true); setError("");
    try {
      const created = await createImport(organizationId, file, source.trim(), { destination, flow: domainFlow[domain] || "", context });
      if (!mountedRef.current) return;
      setProcess(created); onCompleted?.();
      const analyzed = await analyzeImport(organizationId, created.id);
      if (!mountedRef.current) return;
      setMappings(analyzed.columnas || []); setProcess((current) => ({ ...current, ...analyzed })); setStage(3); onCompleted?.();
    } catch (requestError) {
      if (mountedRef.current) setError(requestError?.response?.data?.error || "No se pudo analizar el archivo. El proceso, si fue creado, permanece en el historial.");
    } finally { if (mountedRef.current) setBusy(false); }
  }
  async function mapAndPreview() {
    setBusy(true); setError("");
    try {
      await saveImportMapping(organizationId, process.id, mappings, { destination, flow: domainFlow[domain] || "", context });
      const nextPreview = await previewImport(organizationId, process.id);
      if (!mountedRef.current) return;
      setPreview(nextPreview); setStage(4); onCompleted?.();
    } catch (requestError) { if (mountedRef.current) setError(requestError?.response?.data?.error || "No se pudo preparar la revisión de la carga."); }
    finally { if (mountedRef.current) setBusy(false); }
  }
  async function confirm() {
    setBusy(true); setError("");
    try {
      const confirmed = await confirmImport(organizationId, process.id);
      if (!mountedRef.current) return;
      setResult(confirmed); setStage(6); onCompleted?.();
    } catch (requestError) { if (mountedRef.current) setError(requestError?.response?.data?.error || "La confirmación falló. Revisa el detalle antes de intentar nuevamente."); }
    finally { if (mountedRef.current) setBusy(false); }
  }

  return <Card><CardContent>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-3"><FileSpreadsheet aria-hidden="true" className="text-emerald-700" /><div><p className="text-xs font-black uppercase tracking-wider text-emerald-700">Nueva importación guiada</p><h2 className="text-xl font-black">Define el contexto antes de incorporar datos</h2></div></div>
      {onClose && <Button variant="ghost" onClick={onClose}>Cerrar</Button>}
    </div>
    <ol aria-label="Progreso de la importación" className="mt-5 grid grid-cols-2 gap-2 text-sm sm:grid-cols-3 xl:grid-cols-6">{steps.map((label, index) => { const step = index + 1; return <li key={label} aria-current={stage === step ? "step" : undefined} className={`rounded-[var(--radius-md)] border p-2 text-center font-bold ${stage === step ? "border-emerald-500 bg-emerald-50 text-emerald-800" : stage > step ? "border-slate-200 bg-slate-50 text-slate-700" : "border-slate-200 text-slate-400"}`}><span className="block text-xs font-normal">Paso {step}</span>{label}</li>; })}</ol>
    {error && <div className="mt-4"><Alert tone="danger" title="No pudimos continuar">{error}</Alert></div>}

    {stage === 1 && <section className="mt-6 space-y-5">
      <div><h3 className="font-black">¿Dónde aplica esta información?</h3><p className="mt-1 text-sm text-[var(--text-muted)]">Selecciona el alcance explícitamente. No se asignarán obras o ámbitos de forma automática.</p></div>
      <ImportScopeSelector value={scope} onChange={selectScope} />
      {scope !== "organizacion" && <label className="block text-sm font-bold">Obra<select className="mt-1 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-white p-2.5 font-normal" value={workId} onChange={(event) => setWorkId(event.target.value)}><option value="">Selecciona una obra</option>{works.map((work) => <option key={work.id || work.obra_id} value={work.id || work.obra_id}>{work.nombre}</option>)}</select></label>}
      {scope === "dominio" && workId && <label className="block text-sm font-bold">Ámbito ambiental<select className="mt-1 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-white p-2.5 font-normal" value={domain} onChange={(event) => selectDomain(event.target.value)}><option value="">Selecciona un ámbito aplicable</option>{applicableDomains.map((key) => { const item = getEnvironmentalDomain(key); return <option key={key} value={key}>{item?.label || key}</option>; })}</select><span className="mt-1 block text-xs font-normal text-[var(--text-muted)]">Solo se muestran ámbitos confirmados como aplicables o sin datos.</span></label>}
      <div className="grid gap-4 md:grid-cols-2">
        <label className="text-sm font-bold">¿Qué información contiene?<select className="mt-1 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-white p-2.5 font-normal" value={destination} onChange={(event) => setDestination(event.target.value)}><option value="">Selecciona el contenido</option>{destinations.map((value) => <option key={value} value={value}>{destinationLabel(value)}</option>)}</select><span className="mt-1 block text-xs font-normal text-[var(--text-muted)]">La sugerencia del ámbito debe ser confirmada por ti.</span></label>
        <label className="text-sm font-bold">¿De dónde proviene esta información?<input className="mt-1 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-white p-2.5 font-normal" placeholder="Ej. ERP de abastecimiento" value={source} onChange={(event) => setSource(event.target.value)} /><span className="mt-1 block text-xs font-normal text-[var(--text-muted)]">Identifica el sistema, documento, proveedor o proceso que originó los datos.</span></label>
      </div>
      <Button disabled={!contextComplete} rightIcon={ArrowRight} onClick={() => setStage(2)}>Continuar al archivo</Button>
    </section>}

    {stage === 2 && <section className="mt-6 space-y-4"><ImportContextSummary context={summary} /><div><h3 className="font-black">Selecciona el archivo</h3><p className="mt-1 text-sm text-[var(--text-muted)]">El archivo permanecerá local hasta que confirmes el inicio del análisis.</p></div><FileDropzone file={file} onChange={setFile} disabled={busy} /><div className="flex flex-wrap gap-2"><Button variant="secondary" leftIcon={ArrowLeft} onClick={() => setStage(1)}>Volver al alcance</Button><Button disabled={!file || busy} loading={busy} rightIcon={ArrowRight} onClick={uploadAndAnalyze}>Crear y analizar importación</Button></div></section>}

    {process && stage >= 3 && <div className="mt-5"><ImportContextSummary context={summary} /></div>}
    {stage === 3 && <section className="mt-5 space-y-4"><div><h3 className="font-black">Detectamos esta estructura</h3><p className="mt-1 text-sm text-[var(--text-muted)]">Clasificación sugerida: <b>{process.clasificacion_sugerida || "No determinada"}</b>. Confirma el significado de las columnas.</p></div>{!mappings.length ? <Alert tone="warning" title="No encontramos columnas para asociar">Revisa el archivo o inicia una carga nueva con una planilla compatible.</Alert> : <><MappingTable mappings={mappings} concepts={concepts} conceptLabel={(value) => conceptLabels[value] || value} onChange={(index, field, value) => setMappings((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, [field]: value } : row))} /><Button disabled={busy || mappedColumns === 0} loading={busy} onClick={mapAndPreview}>Validar información</Button></>}</section>}

    {stage === 4 && preview && <section className="mt-5 space-y-4"><div><h3 className="font-black">Revisa antes de confirmar</h3><p className="mt-1 text-sm text-[var(--text-muted)]">El backend separó filas preparadas y filas que requieren revisión.</p></div><div className="grid gap-3 sm:grid-cols-3"><Metric label="Filas leídas" value={preview.filas_detectadas} /><Metric label="Filas válidas" value={preview.filas_validas} tone="success" /><Metric label="Con observaciones" value={preview.filas_problematicas} tone={preview.filas_problematicas ? "warning" : "neutral"} /></div>{reviewRows.length > 0 && <details className="rounded-[var(--radius-md)] border border-amber-200 bg-amber-50/40 p-3"><summary className="cursor-pointer font-bold">Filas que requieren revisión ({reviewRows.length})</summary><div className="mt-3 max-h-64 space-y-2 overflow-auto">{reviewRows.slice(0, 20).map((row) => <article key={row.numero_fila} className="rounded-xl bg-white p-3 text-sm"><b>Fila {row.numero_fila}</b>{(row.problemas || row.errores || []).map((problem, index) => <p key={`${problem.codigo || "problema"}-${index}`} className="mt-1 text-amber-800">{problem.campo ? `${conceptLabels[problem.campo] || problem.campo}: ` : ""}{problem.detalle || problem.codigo}</p>)}</article>)}</div></details>}<div className="flex gap-2"><Button variant="secondary" onClick={() => setStage(3)}>Volver al mapeo</Button><Button disabled={preview.filas_validas === 0} onClick={() => setStage(5)}>Continuar a confirmar</Button></div></section>}

    {stage === 5 && preview && <section className="mt-5 space-y-4"><h3 className="font-black">Confirmar importación</h3><Alert tone="info" title="Efecto de la confirmación">Se intentarán incorporar {preview.filas_validas} filas válidas a {destinationLabel(destination)}{selectedWork?.nombre ? ` de ${selectedWork.nombre}` : " de la organización"}. {preview.filas_problematicas} filas presentan observaciones y permanecerán trazables.</Alert><div className="flex flex-wrap gap-2"><Button variant="secondary" onClick={() => setStage(4)}>Volver a revisar</Button><Button disabled={busy || preview.filas_validas === 0} loading={busy} onClick={confirm}>Confirmar importación</Button></div></section>}

    {stage === 6 && result && <section className="mt-5 space-y-4"><Alert tone={Number(result.filas_con_error) > 0 ? "warning" : "success"} title={Number(result.filas_con_error) > 0 ? "Importación completada con observaciones" : "Importación completada"}>El resultado y su contexto quedaron registrados.</Alert><div className="grid gap-3 sm:grid-cols-3"><Metric label="Actividades creadas" value={resultValue(result.actividades_creadas)} /><Metric label="Observaciones creadas" value={resultValue(result.observaciones_creadas)} /><Metric label="Filas con error" value={resultValue(result.filas_con_error)} /></div><div className="flex flex-wrap gap-2"><Button variant="secondary" onClick={resetWorkflow}>Cargar otro archivo</Button>{process?.id && <Link className="inline-flex items-center justify-center rounded-[var(--radius-md)] border border-[var(--border-default)] bg-white px-4 py-2.5 text-sm font-bold" to={`/datos/importaciones/${process.id}`}>Ver detalle</Link>}</div></section>}
  </CardContent></Card>;
}

function Metric({ label, value, tone = "neutral" }) {
  const tones = { success: "border-emerald-200 bg-emerald-50/50", warning: "border-amber-200 bg-amber-50/50", neutral: "border-slate-200 bg-white" };
  return <div className={`rounded-[var(--radius-md)] border p-3 text-center ${tones[tone]}`}><p className="text-xs font-bold text-[var(--text-muted)]">{label}</p><p className="mt-1 text-2xl font-black">{resultValue(value)}</p></div>;
}
