import { useEffect, useState } from "react";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { EmptyState, ErrorState, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";
import { getSaaSAudit } from "../services/saasApi";

export default function SaaSAuditPage() {
  const [state, setState] = useState({ status: "loading", rows: [] });
  useEffect(() => { getSaaSAudit().then((rows) => setState({ status: "ready", rows })).catch(() => setState({ status: "error", rows: [] })); }, []);
  if (state.status === "loading") return <PlatformLoader title="Cargando auditoría SaaS" />;
  if (state.status === "error") return <ErrorState description="No fue posible cargar el historial administrativo." />;
  return <div className="space-y-6"><header className="rounded-[28px] bg-gradient-to-r from-slate-900 to-emerald-900 p-7 text-white"><p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-300">Gobernanza global</p><h1 className="mt-2 text-3xl font-black">Auditoría SaaS</h1><p className="mt-2 text-sm text-slate-200">Historial inmutable de cambios comerciales y acciones críticas de plataforma.</p></header>{!state.rows.length ? <EmptyState title="Sin acciones administrativas" description="Los cambios de plan, preset, suspensiones y reactivaciones aparecerán aquí." /> : <TableShell><TableHead><tr><TableCell as="th">Fecha</TableCell><TableCell as="th">Organización</TableCell><TableCell as="th">Administrador</TableCell><TableCell as="th">Acción</TableCell><TableCell as="th">Detalle</TableCell></tr></TableHead><TableBody columns={5}>{state.rows.map((row) => <tr key={row.id}><TableCell>{formatDateTime(row.created_at)}</TableCell><TableCell className="font-bold">{row.organizacion}</TableCell><TableCell>{row.actor}</TableCell><TableCell className="capitalize">{row.accion.replaceAll("_", " ")}</TableCell><TableCell>{row.detalle || "Cambio administrativo registrado"}</TableCell></tr>)}</TableBody></TableShell>}</div>;
}
