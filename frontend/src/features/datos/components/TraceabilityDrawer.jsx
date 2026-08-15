import { Link } from "react-router-dom";
import { Drawer, StatusBadge } from "@/shared/ui";
import { formatDateTime, formatNumber } from "@/shared/utils/formatters";

function Row({ label, value }) { return value === undefined || value === null || value === "" ? null : <div className="grid grid-cols-[130px_1fr] gap-3 border-b border-[var(--border-default)] py-2 text-sm"><dt className="text-[var(--text-muted)]">{label}</dt><dd className="break-words font-medium">{value}</dd></div>; }
export default function TraceabilityDrawer({ observation, open, onClose, workId }) {
  const source = observation?.fuente_detalle || observation?.fuente;
  const evidence = observation?.evidencia_detalle || observation?.evidencia;
  const version = observation?.version_evidencia_detalle || observation?.version_evidencia;
  return <Drawer open={open} onClose={onClose} title="Origen del dato">{!observation ? <p className="text-sm text-[var(--text-muted)]">No hay trazabilidad identificable para este dato.</p> : <div className="space-y-6">
    <section><h3 className="font-bold">Dato observado</h3><dl><Row label="Valor" value={observation.valor_numerico === null ? observation.valor_texto : `${formatNumber(observation.valor_numerico)} ${observation.unidad || ""}`} /><Row label="Concepto" value={observation.concepto?.replaceAll("_", " ")} /><Row label="Estado" value={<StatusBadge label={(observation.estado || "sin estado").replaceAll("_", " ")} />} /><Row label="Fecha" value={formatDateTime(observation.timestamp_observacion)} /></dl></section>
    <section><h3 className="font-bold">Captura y calidad</h3><dl><Row label="Método" value={observation.metodo_captura} /><Row label="Naturaleza" value={observation.naturaleza} /><Row label="Calidad" value={observation.estado_calidad || observation.estado} /><Row label="Valor original" value={observation.valor_original} /></dl></section>
    <section><h3 className="font-bold">Fuente de datos</h3><dl><Row label="Nombre" value={source?.nombre || (typeof source === "string" ? source : null)} /><Row label="Tipo" value={source?.tipo_fuente} /><Row label="Confiabilidad" value={source?.confiabilidad} /><Row label="Origen externo" value={source?.identificador_externo} /></dl></section>
    {(evidence || version) && <section><h3 className="font-bold">Evidencia documental</h3><dl><Row label="Documento" value={evidence?.nombre || observation.evidencia_nombre} /><Row label="Versión" value={version?.version || observation.version_evidencia_version} /><Row label="Archivo" value={version?.nombre_original || observation.version_evidencia_nombre_original} /><Row label="Integridad" value={(version?.checksum_sha256 || observation.version_evidencia_checksum_sha256)?.slice(0, 12)} /></dl>{evidence?.id && <Link className="mt-3 inline-flex text-sm font-bold text-[var(--brand-primary)]" to={`/datos/evidencias/${evidence.id}`}>Ver evidencia</Link>}</section>}
    {observation.registro_extraido && <section><h3 className="font-bold">Proceso de importación</h3><dl><Row label="Fila" value={observation.registro_extraido.numero_fila} /><Row label="Valor original" value={JSON.stringify(observation.registro_extraido.datos_originales)} /></dl></section>}
    {workId && <Link className="text-sm font-bold text-[var(--brand-primary)]" to={`/obras/${workId}/operacion`}>Ver operación de la obra</Link>}
  </div>}</Drawer>;
}
