import { useState } from "react";

function FactorCreateModal({ config, onClose, onSubmit, preset }) {
  const [form, setForm] = useState({
    preset,
    module: "",
    categoria: config.categories[0] || "Otros",
    actividad: "",
    unidad: "",
    factor_emision: "",
    fuente: "Referencia interna - validar antes de uso oficial",
    anio: new Date().getFullYear(),
    alcance: "Referencial",
    descripcion: "",
    activo: true,
    metadata: { requires_validation: true },
  });
  const inputClass = "rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-main)]";
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm">
      <form onSubmit={(e) => { e.preventDefault(); onSubmit(form); }} className="w-full max-w-2xl rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-2xl">
        <h2 className="text-2xl font-black text-[var(--text-main)]">Nuevo factor</h2>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <select className={inputClass} value={form.categoria} onChange={(e) => setForm((x) => ({ ...x, categoria: e.target.value }))}>{config.categories.map((item) => <option key={item} value={item}>{item}</option>)}</select>
          <select className={inputClass} value={form.module} onChange={(e) => setForm((x) => ({ ...x, module: e.target.value }))}><option value="">Modulo</option>{config.modules.map((item) => <option key={item} value={item}>{item}</option>)}</select>
          <input className={inputClass} placeholder="Actividad" value={form.actividad} onChange={(e) => setForm((x) => ({ ...x, actividad: e.target.value }))} required />
          <input className={inputClass} placeholder="Unidad" value={form.unidad} onChange={(e) => setForm((x) => ({ ...x, unidad: e.target.value }))} required />
          <input className={inputClass} type="number" step="any" placeholder="Factor" value={form.factor_emision} onChange={(e) => setForm((x) => ({ ...x, factor_emision: e.target.value }))} required />
          <input className={inputClass} type="number" placeholder="Anio" value={form.anio} onChange={(e) => setForm((x) => ({ ...x, anio: e.target.value }))} required />
          <input className={`${inputClass} md:col-span-2`} placeholder="Fuente" value={form.fuente} onChange={(e) => setForm((x) => ({ ...x, fuente: e.target.value }))} required />
          <textarea className={`${inputClass} md:col-span-2`} placeholder="Descripcion" value={form.descripcion} onChange={(e) => setForm((x) => ({ ...x, descripcion: e.target.value }))} />
        </div>
        <div className="mt-5 flex justify-end gap-3"><button type="button" onClick={onClose} className="rounded-xl border px-4 py-3 font-bold">Cancelar</button><button className="rounded-xl bg-[var(--primary)] px-4 py-3 font-black text-white">Crear factor</button></div>
      </form>
    </div>
  );
}

export default FactorCreateModal;
