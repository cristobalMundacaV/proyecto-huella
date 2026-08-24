import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Clock3, FileUp, Loader2 } from "lucide-react";
import Toast from "@/shared/components/Toast";
import { Button, EmptyState } from "@/shared/ui";
import { api } from "@/shared/services/api";
import { useOperationalWorkspace } from "../context/OperationalWorkspaceContext";

const tone = { Procesado: "bg-emerald-100 text-emerald-800", Rechazado: "bg-red-100 text-red-700", "Necesita información": "bg-amber-100 text-amber-800" };

export default function OperationalHome() {
  const { activeWorkspace } = useOperationalWorkspace();
  const inputRef = useRef(null);
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [toast, setToast] = useState(null);
  const load = () => api.get("/contexto-operativo/subir-informacion/").then(({ data }) => setUploads(data)).finally(() => setLoading(false));
  useEffect(() => { load(); }, [activeWorkspace?.id]);
  const upload = async (event) => {
    const file = event.target.files?.[0]; if (!file) return;
    const data = new FormData(); data.append("archivo", file);
    setSending(true); setToast({ id: Date.now(), loading: true, message: "Cargando información", subtitle: "Estamos recibiendo y preparando el archivo." });
    try { await api.post("/contexto-operativo/subir-informacion/", data); setToast({ id: Date.now(), message: "Información recibida", subtitle: "Carbono Zero comenzará a procesarla con el contexto de tu espacio." }); await load(); }
    catch (error) { setToast({ id: Date.now(), tone: "error", message: "No pudimos recibir el archivo", subtitle: error.response?.data?.archivo?.[0] || "Revisa el archivo e inténtalo nuevamente." }); }
    finally { setSending(false); event.target.value = ""; }
  };
  const pending = uploads.filter((item) => item.estado === "Necesita información").length;
  return <div className="mx-auto max-w-5xl space-y-6"><Toast {...toast} toastKey={toast?.id} onClose={() => setToast(null)} /><header className="rounded-3xl bg-gradient-to-r from-slate-900 to-emerald-900 p-7 text-white shadow-xl"><p className="text-sm font-bold text-emerald-300">{activeWorkspace?.obra?.nombre || activeWorkspace?.organizacion?.nombre}</p><h1 className="mt-1 text-3xl font-black">{activeWorkspace?.area?.nombre}</h1><p className="mt-3 max-w-2xl text-slate-200">Entrega la información generada por tu área. Carbono Zero se encargará de procesarla y preparar los datos necesarios para la gestión ambiental.</p></header><section className="rounded-3xl border border-emerald-200 bg-white p-6 shadow-sm"><div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-xl font-black">Subir información</h2><p className="mt-1 text-sm text-slate-600">PDF, imágenes, Excel o CSV. El contexto se asignará automáticamente.</p></div><input ref={inputRef} className="hidden" type="file" accept=".pdf,.png,.jpg,.jpeg,.xlsx,.xls,.csv" onChange={upload} /><Button loading={sending} leftIcon={FileUp} onClick={() => inputRef.current?.click()}>Seleccionar archivo</Button></div></section>{pending > 0 && <section className="flex items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900"><Clock3 /><b>{pending} archivo{pending === 1 ? " requiere" : "s requieren"} confirmación.</b></section>}<section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="text-xl font-black">Últimos envíos</h2>{loading ? <div className="flex items-center gap-2 py-8 text-slate-500"><Loader2 className="animate-spin" /> Cargando envíos</div> : uploads.length ? <div className="mt-4 divide-y divide-slate-100">{uploads.map((item) => <div key={item.id} className="flex items-center justify-between gap-4 py-4"><span className="flex min-w-0 items-center gap-3"><CheckCircle2 className="shrink-0 text-slate-400" size={20} /><b className="truncate">{item.nombre}</b></span><span className={`shrink-0 rounded-full px-3 py-1 text-xs font-bold ${tone[item.estado] || "bg-slate-100 text-slate-700"}`}>{item.estado}</span></div>)}</div> : <EmptyState title="Aún no hay envíos" description="Los archivos que compartas desde este espacio aparecerán aquí." />}</section></div>;
}
