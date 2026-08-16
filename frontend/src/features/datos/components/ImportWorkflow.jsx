import { useEffect, useRef, useState } from "react";
import { FileSpreadsheet, UploadCloud } from "lucide-react";
import { Alert, Button, Card, CardContent, StatusBadge } from "@/shared/ui";
import { analyzeImport, confirmImport, createImport, previewImport, saveImportMapping } from "../services/dataApi";
import { destinationLabel } from "../utils/dataPresentation";

const concepts = ["", "identificador_actividad", "fecha_actividad", "periodo_inicio", "periodo_fin", "distancia_recorrida_km", "masa_transportada_t", "combustible_consumido_l", "consumo_energia", "consumo_agua", "material", "cantidad_material", "cantidad_residuo", "nivel_ruido", "unidad", "obra", "proceso", "activo", "punto_medicion"];
const destinations = ["actividad_generica", "transporte", "material", "flujo_ambiental"];
const steps = ["Subir", "Entender", "Revisar", "Confirmar", "Resultado"];
const humanize = (value) => String(value || "").replaceAll("_", " ");
const resultValue = (value) => value === null || value === undefined ? "Sin datos" : value;

export default function ImportWorkflow({ organizationId, work, onCompleted }) {
  const [stage, setStage] = useState(1);
  const [process, setProcess] = useState(null);
  const [mappings, setMappings] = useState([]);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [source, setSource] = useState("Fuente operacional");
  const [destination, setDestination] = useState("actividad_generica");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const mountedRef = useRef(true);

  useEffect(() => () => { mountedRef.current = false; }, []);

  async function upload(file) {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const created = await createImport(organizationId, file, source, { destination });
      if (!mountedRef.current) return;
      setProcess(created);
      onCompleted?.();
      const analyzed = await analyzeImport(organizationId, created.id);
      if (!mountedRef.current) return;
      setMappings(analyzed.columnas || []);
      setProcess((current) => ({ ...current, ...analyzed }));
      setStage(2);
      onCompleted?.();
    } catch (requestError) {
      if (!mountedRef.current) return;
      setError(requestError?.response?.data?.error || "No se pudo analizar el archivo. Si el proceso alcanzó a guardarse, seguirá disponible en el historial.");
      onCompleted?.();
    } finally {
      if (mountedRef.current) setBusy(false);
    }
  }

  async function mapAndPreview() {
    setBusy(true);
    setError("");
    try {
      const workId = work?.id || work?.obra_id;
      await saveImportMapping(organizationId, process.id, mappings, {
        destination,
        context: workId ? { obra_id: workId } : {},
      });
      const nextPreview = await previewImport(organizationId, process.id);
      if (!mountedRef.current) return;
      setPreview(nextPreview);
      setStage(3);
      onCompleted?.();
    } catch (requestError) {
      if (!mountedRef.current) return;
      setError(requestError?.response?.data?.error || "No se pudo preparar la revisión de la carga.");
    } finally {
      if (mountedRef.current) setBusy(false);
    }
  }

  async function confirm() {
    setBusy(true);
    setError("");
    try {
      const confirmed = await confirmImport(organizationId, process.id);
      if (!mountedRef.current) return;
      setResult(confirmed);
      setStage(5);
      onCompleted?.();
    } catch (requestError) {
      if (!mountedRef.current) return;
      setError(requestError?.response?.data?.error || "La confirmación falló. Revisa el detalle antes de intentar nuevamente.");
    } finally {
      if (mountedRef.current) setBusy(false);
    }
  }

  function reset() {
    setStage(1);
    setProcess(null);
    setMappings([]);
    setPreview(null);
    setResult(null);
    setError("");
  }

  const reviewRows = preview?.filas?.filter((row) => row.estado === "requiere_revision" || row.problemas?.length || row.errores?.length) || [];
  const mappedColumns = mappings.filter((item) => item.concepto_normalizado).length;

  return <Card><CardContent>
    <div className="flex items-center gap-3">
      <FileSpreadsheet aria-hidden="true" className="text-[var(--brand-primary)]" />
      <div><p className="text-xs font-bold uppercase tracking-wider text-[var(--brand-primary)]">Nueva importación</p><h2 className="text-xl font-bold">Carga información desde una planilla</h2></div>
    </div>

    <ol aria-label="Progreso de la importación" className="mt-5 grid grid-cols-2 gap-2 text-sm sm:grid-cols-5">
      {steps.map((label, index) => {
        const step = index + 1;
        const current = stage === step;
        const complete = stage > step;
        return <li key={label} aria-current={current ? "step" : undefined} className={`rounded-[var(--radius-md)] border p-2 text-center font-bold ${current ? "border-[var(--brand-primary)] bg-[var(--info-bg)] text-[var(--brand-primary)]" : complete ? "border-[var(--border-default)] bg-[var(--bg-surface-subtle)] text-[var(--text-primary)]" : "border-[var(--border-default)] text-[var(--text-muted)]"}`}><span className="block text-xs font-normal">Paso {step}{current ? " · actual" : ""}</span>{label}</li>;
      })}
    </ol>

    {error && <div className="mt-4"><Alert tone="danger" title="No pudimos continuar">{error}</Alert></div>}

    {stage === 1 && <section className="mt-5">
      <p className="text-sm text-[var(--text-secondary)]">Selecciona un archivo y dinos qué tipo de información contiene. Se aceptan CSV, XLS y XLSX.</p>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <label className="text-sm font-bold">Fuente de datos<input className="mt-1 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-2 font-normal text-[var(--text-primary)]" value={source} onChange={(event) => setSource(event.target.value)} /></label>
        <label className="text-sm font-bold">¿Qué información contiene?<select className="mt-1 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-2 font-normal text-[var(--text-primary)]" value={destination} onChange={(event) => setDestination(event.target.value)}>{destinations.map((value) => <option key={value} value={value}>{destinationLabel(value)}</option>)}</select></label>
        <label className="flex cursor-pointer items-center justify-center gap-2 rounded-[var(--radius-md)] border border-dashed border-[var(--border-strong)] bg-[var(--bg-surface-subtle)] p-3 font-bold focus-within:shadow-[var(--focus-ring)]"><UploadCloud aria-hidden="true" />{busy ? "Analizando…" : "Seleccionar archivo"}<input aria-label="Seleccionar planilla para importar" accept=".csv,.xls,.xlsx" className="hidden" disabled={busy} type="file" onChange={(event) => { const file = event.target.files?.[0]; event.target.value = ""; upload(file); }} /></label>
      </div>
    </section>}

    {process && stage >= 2 && <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface-subtle)] p-3 text-sm">
      <b>Encontramos:</b> {humanize(process.clasificacion_sugerida) || "tipo no determinado"}. <span className="ml-1 text-[var(--text-muted)]">Confirma el significado de las columnas antes de importar.</span>
      <span className="mt-1 block"><b>Contexto:</b> {work?.nombre || work?.codigo_obra || "Organización"}</span>
    </div>}

    {stage === 2 && <section className="mt-5">
      <h3 className="font-bold">Indica qué significa cada columna</h3>
      <p className="mt-1 text-sm text-[var(--text-muted)]">Puedes dejar sin asociar columnas que no correspondan. La revisión siguiente mostrará qué información falta.</p>
      {!mappings.length ? <Alert tone="warning" title="No encontramos columnas para asociar">Revisa el archivo desde el historial o inicia una carga nueva con una planilla compatible.</Alert> : <>
        <div className="mt-3 max-h-80 space-y-2 overflow-auto">{mappings.map((item, index) => <div key={`${item.columna_origen}-${index}`} className="grid gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-3 md:grid-cols-[1fr_1fr_120px]">
          <span><b>{item.columna_origen}</b><small className="block text-[var(--text-muted)]">Columna del archivo</small></span>
          <select aria-label={`Significado de ${item.columna_origen}`} className="rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-2 text-[var(--text-primary)]" value={item.concepto_normalizado || ""} onChange={(event) => setMappings((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, concepto_normalizado: event.target.value } : row))}>{concepts.map((value) => <option key={value} value={value}>{value ? humanize(value) : "No usar esta columna"}</option>)}</select>
          <input aria-label={`Unidad de ${item.columna_origen}`} className="rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-2 text-[var(--text-primary)]" placeholder="Unidad" value={item.unidad_esperada || ""} onChange={(event) => setMappings((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, unidad_esperada: event.target.value } : row))} />
        </div>)}</div>
        <Button className="mt-4" disabled={busy || mappedColumns === 0} loading={busy} onClick={mapAndPreview}>Revisar información</Button>
      </>}
    </section>}

    {stage === 3 && preview && <section className="mt-5">
      <h3 className="font-bold">Revisa antes de confirmar</h3>
      <p className="mt-1 text-sm text-[var(--text-muted)]">Comprueba el resultado de la lectura y los problemas detectados.</p>
      <div className="mt-4 flex flex-wrap gap-2"><StatusBadge tone="success">{preview.filas_validas} {preview.filas_validas === 1 ? "fila preparada" : "filas preparadas"}</StatusBadge><StatusBadge tone={preview.filas_problematicas ? "warning" : "neutral"}>{preview.filas_problematicas} {preview.filas_problematicas === 1 ? "fila con observaciones" : "filas con observaciones"}</StatusBadge></div>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3"><div><dt className="text-[var(--text-muted)]">Se incorporará en</dt><dd className="font-bold">{destinationLabel(preview.destino || destination)}</dd></div><div><dt className="text-[var(--text-muted)]">Fuente</dt><dd className="font-bold">{source}</dd></div><div><dt className="text-[var(--text-muted)]">Contexto</dt><dd className="font-bold">{work?.nombre || work?.codigo_obra || "Organización"}</dd></div></dl>
      {!!reviewRows.length && <details className="mt-4 rounded-[var(--radius-md)] border border-[var(--border-default)] p-3"><summary className="cursor-pointer font-bold">Ver detalles de filas con observaciones ({reviewRows.length})</summary><div className="mt-3 max-h-64 space-y-2 overflow-auto">{reviewRows.slice(0, 20).map((row) => <article key={row.numero_fila} className="rounded-[var(--radius-md)] bg-[var(--bg-surface-subtle)] p-3 text-sm"><b>Fila {row.numero_fila}</b>{(row.problemas || row.errores || []).map((problem, index) => <p key={`${problem.codigo || "problema"}-${problem.campo || index}-${index}`} className="mt-1 text-[var(--status-danger)]">{problem.campo ? `${humanize(problem.campo)}: ` : ""}{problem.detalle || humanize(problem.codigo)}</p>)}</article>)}</div>{reviewRows.length > 20 && <p className="mt-2 text-xs text-[var(--text-muted)]">Mostrando 20 de {reviewRows.length} filas.</p>}</details>}
      <Button className="mt-4" onClick={() => setStage(4)}>Continuar a confirmar</Button>
    </section>}

    {stage === 4 && preview && <section className="mt-5">
      <h3 className="font-bold">Confirmar importación</h3>
      <Alert tone="info" title="Esta acción guardará los datos preparados">Se intentarán procesar {preview.filas_validas} {preview.filas_validas === 1 ? "fila preparada" : "filas preparadas"}. Las filas con problemas pueden terminar con error y quedarán registradas en el resultado.</Alert>
      <div className="mt-4 flex flex-wrap gap-2"><StatusBadge tone="success">{preview.filas_validas} preparadas</StatusBadge><StatusBadge tone={preview.filas_problematicas ? "warning" : "neutral"}>{preview.filas_problematicas} con observaciones</StatusBadge></div>
      <div className="mt-4 flex flex-wrap gap-2"><Button variant="secondary" onClick={() => setStage(3)}>Volver a revisar</Button><Button disabled={busy || preview.filas_validas === 0} loading={busy} onClick={confirm}>Confirmar importación</Button></div>
    </section>}

    {stage === 5 && result && <section className="mt-5">
      <Alert tone={result.filas_con_error === null || result.filas_con_error === undefined ? "info" : Number(result.filas_con_error) > 0 ? "warning" : "success"} title={Number(result.filas_con_error) > 0 ? "Importación completada con observaciones" : "Importación completada"}>La carga terminó y el resultado quedó registrado.</Alert>
      <dl className="mt-4 grid gap-3 sm:grid-cols-3"><div className="rounded-[var(--radius-md)] bg-[var(--bg-surface-subtle)] p-3"><dt className="text-sm text-[var(--text-muted)]">Actividades creadas</dt><dd className="mt-1 text-xl font-bold">{resultValue(result.actividades_creadas)}</dd></div><div className="rounded-[var(--radius-md)] bg-[var(--bg-surface-subtle)] p-3"><dt className="text-sm text-[var(--text-muted)]">Datos observados</dt><dd className="mt-1 text-xl font-bold">{resultValue(result.observaciones_creadas)}</dd></div><div className="rounded-[var(--radius-md)] bg-[var(--bg-surface-subtle)] p-3"><dt className="text-sm text-[var(--text-muted)]">Filas con error</dt><dd className="mt-1 text-xl font-bold">{resultValue(result.filas_con_error)}</dd></div></dl>
      <Button className="mt-4" variant="secondary" onClick={reset}>Cargar otro archivo</Button>
    </section>}
  </CardContent></Card>;
}
