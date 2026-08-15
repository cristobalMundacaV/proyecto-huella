import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ShieldCheck } from "lucide-react";
import { Card, CardContent, ErrorState, LoadingState, PageHeader, StatusBadge, Timeline, TimelineItem } from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";
import { evidenceContext } from "../services/dataApi";

export default function EvidenceDetailPage() {
  const { evidenceId } = useParams(); const [state, setState] = useState({ loading: true, data: null, error: "" });
  useEffect(() => { let current = true; evidenceContext(evidenceId).then((data) => current && setState({ loading: false, data, error: "" })).catch(() => current && setState({ loading: false, data: null, error: "La evidencia no existe o no está disponible en esta organización." })); return () => { current = false; }; }, [evidenceId]);
  if (state.loading) return <LoadingState label="Cargando evidencia" />; if (state.error) return <ErrorState description={state.error} />;
  const evidence = state.data.evidencia; const versions = state.data.versiones || [];
  return <main className="space-y-6"><Link className="inline-flex items-center gap-2 text-sm font-bold" to="/datos/evidencias"><ArrowLeft size={16} />Evidencias</Link><PageHeader eyebrow="Datos · Evidencias" title={evidence.nombre} description="Archivo original, versiones procesadas e integridad documental." status={<StatusBadge label={evidence.estado?.replaceAll("_", " ")} />} />
    <div className="grid gap-5 lg:grid-cols-[1fr_1.4fr]"><Card><CardContent><h2 className="font-bold">Documento lógico</h2><dl className="mt-3 space-y-2 text-sm"><div><dt className="text-[var(--text-muted)]">Tipo</dt><dd>{evidence.tipo?.replaceAll("_", " ")}</dd></div><div><dt className="text-[var(--text-muted)]">Fecha documental</dt><dd>{evidence.fecha_documento || "Sin fecha"}</dd></div></dl><p className="mt-5 text-xs text-[var(--text-muted)]">Carbono Zero conserva el documento lógico y distingue cada archivo concreto procesado.</p></CardContent></Card><Card><CardContent><h2 className="font-bold">Historial de versiones</h2>{versions.length ? <Timeline>{versions.map((version, index) => <TimelineItem key={version.id} icon={ShieldCheck} timestamp={formatDateTime(version.created_at)} title={`Versión ${version.version}${index === 0 ? " · actual" : ""}`} description={`${version.nombre_original} · Integridad ${version.checksum_sha256?.slice(0, 12) || "no informada"}`} />)}</Timeline> : <p className="mt-3 text-sm text-[var(--text-muted)]">No hay versiones procesadas disponibles.</p>}</CardContent></Card></div>
  </main>;
}
