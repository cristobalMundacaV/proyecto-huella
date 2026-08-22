import { useEffect, useRef, useState } from "react";
import { ArrowLeft, FileCheck2 } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { Alert, Card, CardContent, ErrorState, PageHeader, SectionHeader, StatusBadge } from "@/shared/ui";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { formatDateTime } from "@/shared/utils/formatters";
import { getImport } from "../services/dataApi";
import { destinationLabel, importDisplayName, importProgressStep, importResultLabel, importStatusInfo } from "../utils/dataPresentation";

const steps = ["Subir", "Entender", "Revisar", "Confirmar", "Resultado"];
const displayValue = (value) => value === null || value === undefined ? "Sin datos" : value;
const terminalStates = ["completado", "completado_con_observaciones"];

export default function ImportDetailPage() {
  const { processId } = useParams();
  const { activeOrganizacionId } = useOrganizacionActiva();
  const scopeKey = `${activeOrganizacionId || ""}:${processId}`;
  const [state, setState] = useState({ scope: null, loading: true, data: null, error: "" });
  const requestRef = useRef(0);

  useEffect(() => {
    if (!activeOrganizacionId) return undefined;
    const requestId = ++requestRef.current;
    setState({ scope: scopeKey, loading: true, data: null, error: "" });
    getImport(activeOrganizacionId, processId)
      .then((data) => { if (requestRef.current === requestId) setState({ scope: scopeKey, loading: false, data, error: "" }); })
      .catch(() => { if (requestRef.current === requestId) setState({ scope: scopeKey, loading: false, data: null, error: "La importación no existe o no está disponible en esta organización." }); });
    return () => { requestRef.current += 1; };
  }, [activeOrganizacionId, processId, scopeKey]);

  if (state.scope !== scopeKey || state.loading) return <PlatformLoader title="Cargando importación" description="Estamos reconstruyendo su estado, resultado y trazabilidad documental." />;
  if (state.error) return <ErrorState description={state.error} />;

  const item = state.data;
  const records = item.registros_extraidos || [];
  const status = importStatusInfo(item.estado);
  const currentStep = importProgressStep(item.estado);
  const failed = item.estado === "fallido";
  const reviewRows = records.filter((record) => record.estado === "requiere_revision" || record.estado === "error" || record.errores?.length);
  const resultAvailable = terminalStates.includes(item.estado);
  const analysisAvailable = ["requiere_mapeo", "listo_para_confirmar", "procesando", "completado", "completado_con_observaciones"].includes(item.estado);
  const version = item.version_evidencia_detalle;
  const workId = item.contexto_confirmado?.obra_id;

  return <main className="space-y-6">
    <Link className="inline-flex items-center gap-2 text-sm font-bold text-[var(--text-secondary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to="/datos/importaciones"><ArrowLeft aria-hidden="true" size={16} />Importaciones</Link>
    <PageHeader title={importDisplayName(item)} description={formatDateTime(item.created_at)} status={<StatusBadge tone={status.tone}>{status.label}</StatusBadge>} />

    <section>
      <SectionHeader title="Estado" description="Dónde se encuentra esta carga dentro del proceso." />
      <Card><CardContent>
        <ol aria-label="Progreso de la importación" className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-5">{steps.map((label, index) => {
          const step = index + 1;
          const current = currentStep === step;
          const complete = currentStep !== null && currentStep > step;
          return <li key={label} aria-current={current ? "step" : undefined} className={`rounded-[var(--radius-md)] border p-2 text-center font-bold ${current ? "border-[var(--brand-primary)] bg-[var(--info-bg)] text-[var(--brand-primary)]" : complete ? "border-[var(--border-default)] bg-[var(--bg-surface-subtle)] text-[var(--text-primary)]" : "border-[var(--border-default)] text-[var(--text-muted)]"}`}><span className="block text-xs font-normal">Paso {step}{current ? " · actual" : ""}</span>{label}</li>;
        })}</ol>
        {failed && <div className="mt-4"><Alert tone="danger" title="Importación fallida">El proceso no llegó a completarse. No es posible determinar con precisión qué pasos anteriores alcanzó.</Alert></div>}
        <p className="mt-4 text-sm text-[var(--text-secondary)]">{failed ? "Estado del proceso" : "Resultado actual"}: <b>{importResultLabel(item)}</b></p>
      </CardContent></Card>
    </section>

    <section>
      <SectionHeader title="Resumen" description="Cantidades disponibles sin completar ceros que aún no existen." />
      <div className="grid gap-3 sm:grid-cols-3">
        <Card><CardContent><p className="text-sm text-[var(--text-muted)]">Filas detectadas</p><p className="mt-1 text-2xl font-bold">{analysisAvailable ? displayValue(item.filas_detectadas) : "Sin datos"}</p></CardContent></Card>
        <Card><CardContent><p className="text-sm text-[var(--text-muted)]">Procesadas</p><p className="mt-1 text-2xl font-bold">{resultAvailable ? displayValue(item.filas_procesadas) : "Sin datos"}</p></CardContent></Card>
        <Card><CardContent><p className="text-sm text-[var(--text-muted)]">Con error</p><p className="mt-1 text-2xl font-bold">{resultAvailable ? displayValue(item.filas_con_error) : "Sin datos"}</p></CardContent></Card>
      </div>
    </section>

    {(item.resumen_errores || reviewRows.length) && <section>
      <SectionHeader title="Errores y revisión" description="Primero el alcance del problema; el detalle queda disponible cuando lo necesitas." />
      {item.resumen_errores && <Alert tone="danger" title="La carga informó un problema">{item.resumen_errores}</Alert>}
      {!!reviewRows.length && <Card><CardContent>
        <p className="font-bold">{reviewRows.length} {reviewRows.length === 1 ? "fila requiere" : "filas requieren"} revisión</p>
        <details className="mt-3"><summary className="cursor-pointer font-bold text-[var(--brand-primary)]">Ver detalles</summary><div className="mt-3 max-h-80 space-y-2 overflow-auto">{reviewRows.slice(0, 20).map((record) => <article key={record.id} className="rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface-subtle)] p-3 text-sm"><p className="font-bold">Fila {record.numero_fila}</p>{(record.errores || []).map((problem, index) => <p key={`${problem.codigo || "error"}-${index}`} className="mt-1 text-[var(--status-danger)]">{problem.campo ? `${String(problem.campo).replaceAll("_", " ")}: ` : ""}{problem.detalle || problem.codigo || "Error de procesamiento"}</p>)}</article>)}</div>{reviewRows.length > 20 && <p className="mt-2 text-xs text-[var(--text-muted)]">Mostrando 20 de {reviewRows.length} filas.</p>}</details>
      </CardContent></Card>}
    </section>}

    <div className="grid gap-5 lg:grid-cols-2">
      <Card><CardContent>
        <SectionHeader title="Origen y destino" />
        <dl className="space-y-3 text-sm">
          <div><dt className="text-[var(--text-muted)]">Fuente de datos</dt><dd className="font-medium">{item.fuente_nombre || "Sin datos"}</dd></div>
          <div><dt className="text-[var(--text-muted)]">Se incorporará en</dt><dd className="font-medium">{destinationLabel(item.destino_operacional)}</dd></div>
          {item.flujo && <div><dt className="text-[var(--text-muted)]">Flujo</dt><dd className="font-medium">{String(item.flujo).replaceAll("_", " ")}</dd></div>}
          {workId && <div><dt className="text-[var(--text-muted)]">Obra</dt><dd><Link className="font-bold text-[var(--brand-primary)]" to={`/obras/${workId}/resumen`}>Ver obra #{workId}</Link></dd></div>}
        </dl>
      </CardContent></Card>

      <Card><CardContent>
        <SectionHeader title="Trazabilidad" description="Fuente de datos y evidencia documental se mantienen separadas." />
        {version ? <div className="space-y-3 text-sm">
          <div className="flex items-start gap-3"><FileCheck2 aria-hidden="true" className="mt-0.5 text-[var(--brand-primary)]" size={18} /><div><p className="font-bold">{version.evidencia_nombre || version.nombre_original || "Documento"}</p><p className="text-[var(--text-muted)]">Versión {version.version} · {version.nombre_original}</p></div></div>
          {version.evidencia && <Link className="inline-flex font-bold text-[var(--brand-primary)]" to={`/datos/evidencias/${version.evidencia}`}>Ver documento</Link>}
          <details className="rounded-[var(--radius-md)] border border-[var(--border-default)] p-3"><summary className="cursor-pointer font-bold">Detalles de trazabilidad</summary><dl className="mt-3 space-y-2"><div><dt className="text-[var(--text-muted)]">Integridad</dt><dd className="break-all">{version.checksum_sha256 || "Sin datos"}</dd></div>{item.plantilla?.nombre && <div><dt className="text-[var(--text-muted)]">Configuración de columnas</dt><dd>{item.plantilla.nombre}</dd></div>}</dl></details>
        </div> : <p className="text-sm text-[var(--text-muted)]">Esta carga no tiene evidencia documental asociada en el contrato actual.</p>}
      </CardContent></Card>
    </div>
  </main>;
}
