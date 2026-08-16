import { Link } from "react-router-dom";
import { StatusBadge } from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";

export const labels={pendiente:"Pendiente",validada:"Validada",validada_con_observaciones:"Validada con observaciones",solicita_antecedentes:"Solicita antecedentes",rechazada:"Rechazada",abierto:"Abierto",cerrado:"Cerrado",detectada:"Detectada",requiere_revision:"Requiere revisión",resuelta:"Resuelta"};
export const human=(value)=>labels[value]||String(value||"Sin datos").replaceAll("_"," ");
export const statusTone=(value)=>["validada","resuelta","cerrado","confiable"].includes(value)?"success":["rechazada","no_confiable"].includes(value)?"danger":["pendiente","detectada","requiere_revision","solicita_antecedentes"].includes(value)?"warning":"neutral";
export function State({value}){return <StatusBadge tone={statusTone(value)}>{human(value)}</StatusBadge>}
export function Meta({date,children}){return <p className="text-xs text-[var(--text-muted)]">{children}{date?` · ${formatDateTime(date)}`:""}</p>}
export function Section({title,description,children,action}){return <section className="space-y-3"><div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-xl font-black">{title}</h2>{description&&<p className="text-sm text-[var(--text-muted)]">{description}</p>}</div>{action}</div>{children}</section>}
export function DossierLink({id,children="Ver expediente"}){return <Link className="font-bold text-[var(--brand-primary)]" to={`/gobernanza/expedientes/${id}`}>{children}</Link>}
