import { Link } from "react-router-dom";
import { StatusBadge } from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";

const LABELS = {
  pendiente: "Pendiente", validada: "Validada", validada_con_observaciones: "Validada con observaciones", solicita_antecedentes: "Requiere antecedentes", rechazada: "Rechazada",
  abierto: "Abierto", recopilando_antecedentes: "Recopilando antecedentes", en_revision: "En revisión", requiere_antecedentes: "Requiere antecedentes", validado: "Validado", cerrado: "Cerrado", reabierto: "Reabierto",
  detectada: "Detectada", requiere_revision: "Requiere revisión", resuelta: "Resuelta", aceptada: "Aceptada", confiable: "Confiable", confiable_con_observaciones: "Confiable con observaciones", no_confiable: "No confiable",
  utilizable: "Utilizable", candidato: "Candidato", activa: "Activa", activo: "Activo", obsoleto: "Obsoleto", borrador: "Borrador", generado: "Generado", publicado: "Publicado", critica: "Crítica", media: "Media", baja: "Baja", alta: "Alta",
};
const OBJECT_LABELS = { evidencia: "Evidencia", observacion: "Observación", calculo: "Cálculo", indicador: "Indicador", problematica: "Problema", intervencion: "Intervención", expediente: "Expediente", metodologia: "Metodología" };
const AUDIT_ENTITY_LABELS = { RevisionProfesionalAmbiental: "Revisión profesional", ExpedienteAmbiental: "Expediente", InformeAmbiental: "Informe", CorreccionHistoricaAmbiental: "Corrección histórica", CalculoAmbiental: "Cálculo", ProblematicaAmbiental: "Problema", ResultadoIntervencion: "Resultado de intervención" };
const TONES = { validada: "success", validado: "success", resuelta: "success", aceptada: "success", cerrado: "success", confiable: "success", utilizable: "success", publicado: "success", validada_con_observaciones: "warning", confiable_con_observaciones: "warning", pendiente: "warning", detectada: "warning", requiere_revision: "warning", solicita_antecedentes: "warning", requiere_antecedentes: "warning", en_revision: "warning", critica: "danger", rechazada: "danger", no_confiable: "danger", obsoleto: "neutral" };
export const human = (value) => value === null || value === undefined || value === "" ? "Sin datos" : LABELS[value] || String(value).replaceAll("_", " ");
export const objectTypeLabel = (value) => OBJECT_LABELS[value] || human(value);
export const auditEntityLabel = (value) => AUDIT_ENTITY_LABELS[value] || human(value);
export const statusTone = (value) => TONES[value] || "neutral";
export function State({ value }) { return <StatusBadge tone={statusTone(value)}>{human(value)}</StatusBadge>; }
export function Meta({ date, children }) { return <p className="text-xs text-[var(--text-muted)]">{children}{date ? ` · ${formatDateTime(date)}` : ""}</p>; }
export function Section({ title, description, children, action }) { return <section className="space-y-3"><div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-xl font-black">{title}</h2>{description && <p className="text-sm text-[var(--text-muted)]">{description}</p>}</div>{action}</div>{children}</section>; }
export function DossierLink({ id, children = "Ver expediente" }) { return <Link className="font-bold text-[var(--brand-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]" to={`/gobernanza/expedientes/${id}`}>{children}</Link>; }
export function reviewReference(review) { const type = review?.tipo; const value = type ? review?.[type] : null; const id = typeof value === "object" ? value?.id : value; return { type, id, title: id ? `${objectTypeLabel(type)} #${id}` : objectTypeLabel(type) }; }
const SEVERITY_ORDER = { baja: 1, media: 2, alta: 3, critica: 4 };
export function maxFindingSeverity(findings = []) { return findings.reduce((current, finding) => { const next = finding?.severidad; return (SEVERITY_ORDER[next] || 0) > (SEVERITY_ORDER[current] || 0) ? next : current; }, ""); }
export const isOpenDiscrepancy = (item) => ["detectada", "requiere_revision"].includes(item?.estado);
export const isProfessionalValidation = (review) => ["validada", "validada_con_observaciones"].includes(review?.estado);
