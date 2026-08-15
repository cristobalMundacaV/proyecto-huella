import { useEffect, useState } from "react";

import {
  createVersionMetodologia,
  getFactoresAmbientalesV2,
  getMetodologiasAmbientales,
  transitionVersionMetodologia,
} from "@/shared/services/api";

const nextState = { borrador: "pruebas", pruebas: "validada", validada: "activa", activa: "obsoleta" };

export default function MethodologyGovernancePanel({ organizacionId, onError, onMessage }) {
  const [methods, setMethods] = useState([]);
  const [factors, setFactors] = useState([]);
  const [draftFor, setDraftFor] = useState(null);
  const [form, setForm] = useState({ fuente_referencia: "", prioridad: 100, factor_ambiental: "", tipo: "transporte_tkm", expresion_legible: "", aplicabilidad: "{}", variables: "[]" });

  async function load() {
    if (!organizacionId) return;
    try {
      const [methodRows, factorRows] = await Promise.all([
        getMetodologiasAmbientales(organizacionId),
        getFactoresAmbientalesV2(organizacionId),
      ]);
      setMethods(methodRows);
      setFactors(factorRows);
    } catch (error) {
      onError(error.response?.data?.detail || "No se pudo cargar la gobernanza metodológica.");
    }
  }

  useEffect(() => { load(); }, [organizacionId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function transition(method, version) {
    try {
      await transitionVersionMetodologia(organizacionId, method.id, version.id, nextState[version.estado]);
      onMessage("Estado metodológico actualizado.");
      await load();
    } catch (error) { onError(error.response?.data?.detail || "No se pudo cambiar el estado."); }
  }

  async function createDraft(event) {
    event.preventDefault();
    try {
      await createVersionMetodologia(organizacionId, draftFor.id, {
        fuente_referencia: form.fuente_referencia,
        prioridad: Number(form.prioridad),
        aplicabilidad: JSON.parse(form.aplicabilidad),
        formula: {
          factor_ambiental: Number(form.factor_ambiental), tipo: form.tipo,
          expresion_legible: form.expresion_legible,
          variables: JSON.parse(form.variables),
        },
      });
      setDraftFor(null); onMessage("Nueva versión borrador creada."); await load();
    } catch (error) { onError(error.response?.data?.detail || "No se pudo crear la versión borrador."); }
  }

  return (
    <section className="space-y-4 rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6">
      <div>
        <p className="text-xs font-bold uppercase tracking-widest text-emerald-700">Motor metodológico gobernado</p>
        <h2 className="mt-1 text-xl font-black text-[var(--text-primary)]">Versiones, vigencia y trazabilidad</h2>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {methods.map((method) => (
          <article key={method.id} className="rounded-2xl border border-[var(--border)] p-4">
            <div className="flex items-start justify-between gap-3">
              <div><h3 className="font-bold">{method.nombre}</h3><p className="text-xs text-[var(--text-muted)]">{method.codigo} · {method.flujo}</p></div>
              {method.organizacion && <button className="rounded-xl border px-3 py-2 text-xs font-bold" onClick={() => setDraftFor(method)}>Nueva versión</button>}
            </div>
            <div className="mt-3 space-y-2">
              {method.versiones.map((version) => (
                <div key={version.id} className="rounded-xl bg-[var(--bg-subtle)] p-3 text-sm">
                  <div className="flex items-center justify-between"><span>v{version.version} · <b>{version.estado}</b></span>
                    {nextState[version.estado] && method.organizacion && <button className="text-xs font-bold text-emerald-700" onClick={() => transition(method, version)}>Pasar a {nextState[version.estado]}</button>}
                  </div>
                  <p className="mt-1 text-xs text-[var(--text-muted)]">Prioridad {version.prioridad} · {version.fuente_referencia || "Sin referencia"}</p>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
      {draftFor && <form className="grid gap-3 rounded-2xl border border-emerald-200 p-4 md:grid-cols-2" onSubmit={createDraft}>
        <input className="rounded-xl border p-2" required placeholder="Fuente técnica" value={form.fuente_referencia} onChange={(e) => setForm({ ...form, fuente_referencia: e.target.value })} />
        <input className="rounded-xl border p-2" type="number" min="0" value={form.prioridad} onChange={(e) => setForm({ ...form, prioridad: e.target.value })} />
        <select className="rounded-xl border p-2" required value={form.factor_ambiental} onChange={(e) => setForm({ ...form, factor_ambiental: e.target.value })}><option value="">Factor versionado</option>{factors.map((factor) => <option key={factor.id} value={factor.id}>{factor.nombre}</option>)}</select>
        <select className="rounded-xl border p-2" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}><option value="transporte_tkm">Transporte t·km</option><option value="transporte_vehiculo_km">Transporte vehículo·km</option><option value="transporte_combustible">Transporte combustible</option></select>
        <input className="rounded-xl border p-2 md:col-span-2" required placeholder="Expresión legible (no ejecutable)" value={form.expresion_legible} onChange={(e) => setForm({ ...form, expresion_legible: e.target.value })} />
        <textarea className="rounded-xl border p-2 font-mono text-xs" aria-label="Aplicabilidad JSON" value={form.aplicabilidad} onChange={(e) => setForm({ ...form, aplicabilidad: e.target.value })} />
        <textarea className="rounded-xl border p-2 font-mono text-xs" aria-label="Variables JSON" value={form.variables} onChange={(e) => setForm({ ...form, variables: e.target.value })} />
        <div className="flex gap-2 md:col-span-2"><button className="rounded-xl bg-emerald-700 px-4 py-2 font-bold text-white">Crear borrador</button><button type="button" onClick={() => setDraftFor(null)}>Cancelar</button></div>
      </form>}
    </section>
  );
}
