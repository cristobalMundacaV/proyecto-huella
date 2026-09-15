import { Link } from "react-router-dom";

export default function FlowQuickRead({ base, records, latest, quality, evidence, alert, noData }) {
  const items = [
    { label: "Actividad", value: records === null ? "No disponible" : `${records} ${records === 1 ? "registro" : "registros"}`, to: `${base}/registros` },
    { label: "Último dato", value: latest || "Sin dato reciente", to: `${base}/tendencias` },
    { label: "Calidad", value: quality || "Revisión disponible", to: `${base}/calidad` },
    { label: "Respaldo", value: evidence || "Ver trazabilidad", to: `${base}/calidad` },
  ];
  return <section className="rounded-[22px] border border-slate-200 bg-white p-5 shadow-sm" aria-label="Lectura rápida del flujo">
    <h2 className="text-lg font-black text-slate-950">Lectura rápida</h2>
    <p className="mt-1 text-sm text-slate-600">{noData ? "Aún no hay datos suficientes para interpretar este flujo." : alert || "Revisa la actividad y la trazabilidad antes de tomar una decisión."}</p>
    <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{items.map((item) => <Link key={item.label} to={item.to} className="rounded-2xl border border-slate-200 bg-slate-50 p-3 transition hover:border-emerald-300 hover:bg-emerald-50">
      <span className="block text-xs font-bold uppercase tracking-wide text-slate-500">{item.label}</span>
      <span className="mt-1 block text-sm font-black text-slate-900">{item.value}</span>
    </Link>)}</div>
  </section>;
}
