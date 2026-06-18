import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, ChevronDown, Leaf, Plus, RefreshCw, Save, Truck } from "lucide-react";

import EmptyState from "@/shared/components/EmptyState";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { formatNumber } from "@/shared/utils/formatters";
import {
  createLoteForestal,
  createTransporteLoteForestal,
  getLotesForestales,
  getLotesForestalesResumen,
} from "@/shared/services/api";

const today = new Date().toISOString().slice(0, 10);

const initialLoteForm = {
  lote_id: "",
  fecha: today,
  especie: "",
  volumen_m3: "",
  origen: "",
  destino: "",
  tipo_producto: "",
  densidad_kg_m3: "",
  porcentaje_carbono: "",
  observaciones: "",
};

const initialTransportForm = {
  fecha: today,
  vehiculo: "",
  patente: "",
  conductor: "",
  origen: "",
  destino: "",
  distancia_km: "",
  litros_diesel: "",
  consumo_estimado_litro_km: "0.3",
  observaciones: "",
};

function compactPayload(values) {
  return Object.fromEntries(Object.entries(values).filter(([, value]) => value !== "" && value !== null && value !== undefined));
}

function statusClass(status) {
  return {
    favorable: "border-emerald-200 bg-emerald-50 text-emerald-700",
    intermedio: "border-amber-200 bg-amber-50 text-amber-700",
    critico: "border-rose-200 bg-rose-50 text-rose-700",
    incompleto: "border-slate-200 bg-slate-50 text-slate-700",
  }[status] || "border-slate-200 bg-slate-50 text-slate-700";
}

function LotesForestalesPage() {
  const { activeConstructora, activeConstructoraId } = useConstructoraActiva();
  const [lotes, setLotes] = useState([]);
  const [summary, setSummary] = useState(null);
  const [form, setForm] = useState(initialLoteForm);
  const [transportForm, setTransportForm] = useState(initialTransportForm);
  const [expandedLote, setExpandedLote] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingTransport, setSavingTransport] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadData = useCallback(async () => {
    if (!activeConstructoraId) {
      setLotes([]);
      setSummary(null);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError("");
      const [lotesData, summaryData] = await Promise.all([
        getLotesForestales(activeConstructoraId),
        getLotesForestalesResumen(activeConstructoraId),
      ]);
      setLotes(Array.isArray(lotesData) ? lotesData : []);
      setSummary(summaryData || null);
    } catch (requestError) {
      setError(requestError.response?.data?.error || "No se pudieron cargar los lotes forestales.");
    } finally {
      setLoading(false);
    }
  }, [activeConstructoraId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const selectedLote = useMemo(
    () => lotes.find((lote) => lote.lote_id === expandedLote),
    [expandedLote, lotes]
  );

  async function handleCreateLote(event) {
    event.preventDefault();
    if (!activeConstructoraId) return;
    try {
      setSaving(true);
      setError("");
      setMessage("");
      await createLoteForestal(activeConstructoraId, compactPayload(form));
      setForm(initialLoteForm);
      setMessage("Lote forestal creado y balance calculado.");
      await loadData();
    } catch (requestError) {
      const data = requestError.response?.data;
      const firstError = data?.error || data?.detail || Object.values(data || {}).flat?.()?.[0];
      setError(firstError || "No se pudo crear el lote forestal.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateTransport(event) {
    event.preventDefault();
    if (!activeConstructoraId || !selectedLote) return;
    try {
      setSavingTransport(true);
      setError("");
      setMessage("");
      await createTransporteLoteForestal(activeConstructoraId, selectedLote.lote_id, compactPayload(transportForm));
      setTransportForm({
        ...initialTransportForm,
        origen: selectedLote.origen || "",
        destino: selectedLote.destino || "",
      });
      setMessage("Transporte asociado y registro de emision sincronizado.");
      await loadData();
    } catch (requestError) {
      const data = requestError.response?.data;
      const firstError = data?.error || data?.detail || Object.values(data || {}).flat?.()?.[0];
      setError(firstError || "No se pudo crear el transporte.");
    } finally {
      setSavingTransport(false);
    }
  }

  if (!activeConstructora) {
    return (
      <EmptyState
        title="Lotes forestales"
        description="Selecciona una empresa activa del preset aserradero para gestionar lotes."
      />
    );
  }

  const inputClass = "w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 text-sm font-semibold text-[var(--text-main)] outline-none transition focus:border-emerald-300 focus:ring-4 focus:ring-emerald-100";

  return (
    <main className="mx-auto max-w-7xl space-y-6">
      <section className="rounded-[28px] border border-emerald-200/70 bg-[linear-gradient(135deg,rgba(236,253,245,0.96),rgba(255,255,255,0.98)_50%,rgba(240,249,255,0.94))] p-5 shadow-[var(--shadow-premium)] sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/80 px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
              <Leaf size={14} />
              Aserradero / Forestal
            </p>
            <h1 className="mt-4 text-3xl font-black tracking-tight text-[var(--text-main)] sm:text-4xl">
              Lotes forestales y balance neto
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">
              Gestiona trazabilidad por lote, CO2 almacenado, emisiones asociadas, transportes y evidencias de la empresa forestal.
            </p>
          </div>
          <button
            type="button"
            onClick={loadData}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-sm font-black text-emerald-700 shadow-[0_12px_28px_rgba(15,118,110,0.08)]"
          >
            <RefreshCw size={16} />
            Actualizar
          </button>
        </div>
      </section>

      {error ? <p className="rounded-2xl border border-rose-200 bg-rose-50 p-3 text-sm font-bold text-rose-700">{error}</p> : null}
      {message ? <p className="rounded-2xl border border-emerald-200 bg-emerald-50 p-3 text-sm font-bold text-emerald-700">{message}</p> : null}

      <KpiGrid summary={summary} />

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <form onSubmit={handleCreateLote} className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[0_18px_45px_var(--shadow)]">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Alta rapida</p>
              <h2 className="mt-1 text-xl font-black text-[var(--text-main)]">Crear lote forestal</h2>
            </div>
            <Plus className="text-emerald-700" size={22} />
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Field className={inputClass} form={form} name="lote_id" onChange={setForm} placeholder="LOTE-PINO-001" required />
            <Field className={inputClass} form={form} name="fecha" onChange={setForm} type="date" required />
            <Field className={inputClass} form={form} name="especie" onChange={setForm} placeholder="Pino radiata" required />
            <Field className={inputClass} form={form} name="volumen_m3" onChange={setForm} placeholder="Volumen m3" required type="number" />
            <Field className={inputClass} form={form} name="origen" onChange={setForm} placeholder="Origen" required />
            <Field className={inputClass} form={form} name="destino" onChange={setForm} placeholder="Destino" />
            <Field className={inputClass} form={form} name="tipo_producto" onChange={setForm} placeholder="Tipo producto" />
            <Field className={inputClass} form={form} name="densidad_kg_m3" onChange={setForm} placeholder="Densidad kg/m3" type="number" />
            <Field className={inputClass} form={form} name="porcentaje_carbono" onChange={setForm} placeholder="Carbono 0.5 o 50" type="number" />
            <textarea
              className={`${inputClass} min-h-24 resize-y md:col-span-2`}
              placeholder="Observaciones"
              value={form.observaciones}
              onChange={(event) => setForm((current) => ({ ...current, observaciones: event.target.value }))}
            />
          </div>
          <button
            type="submit"
            disabled={saving}
            className="mt-4 inline-flex items-center gap-2 rounded-2xl bg-[var(--primary-dark)] px-5 py-3 text-sm font-black text-white shadow-[0_16px_32px_rgba(14,124,102,0.22)] disabled:opacity-60"
          >
            <Save size={17} />
            {saving ? "Guardando..." : "Crear lote"}
          </button>
        </form>

        <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[0_18px_45px_var(--shadow)]">
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-xl font-black text-[var(--text-main)]">Lotes registrados</h2>
              <p className="mt-1 text-sm text-[var(--text-muted)]">
                {loading ? "Cargando..." : `${lotes.length} lotes con balance calculado.`}
              </p>
            </div>
          </div>
          <LotesTable lotes={lotes} onExpand={setExpandedLote} selected={expandedLote} />
        </section>
      </section>

      {selectedLote ? (
        <LoteDetail
          inputClass={inputClass}
          lote={selectedLote}
          onCreateTransport={handleCreateTransport}
          savingTransport={savingTransport}
          setTransportForm={setTransportForm}
          transportForm={transportForm}
        />
      ) : null}
    </main>
  );
}

function Field({ className, form, name, onChange, placeholder, required = false, type = "text" }) {
  return (
    <input
      className={className}
      min={type === "number" ? "0" : undefined}
      name={name}
      onChange={(event) => onChange((current) => ({ ...current, [name]: event.target.value }))}
      placeholder={placeholder}
      required={required}
      step={type === "number" ? "0.001" : undefined}
      type={type}
      value={form[name]}
    />
  );
}

function KpiGrid({ summary }) {
  const items = [
    ["Total lotes", summary?.total_lotes, "lotes"],
    ["Volumen total", summary?.volumen_total_m3, "m3"],
    ["CO2 almacenado", summary?.co2_almacenado_kg, "kg"],
    ["Emisiones generadas", summary?.emisiones_generadas_kg_co2e, "kg"],
    ["Balance neto", summary?.balance_neto_kg_co2e, "kg"],
    ["Favorables / criticos", `${summary?.lotes_balance_favorable || 0} / ${summary?.lotes_balance_critico || 0}`, "lotes"],
  ];

  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-6">
      {items.map(([label, value, unit]) => (
        <article key={label} className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_14px_32px_var(--shadow)]">
          <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
          <p className="mt-2 text-2xl font-black text-[var(--text-main)]">
            {typeof value === "number" ? formatNumber(value, 1) : value || "0"}
          </p>
          <p className="mt-1 text-xs font-bold text-[var(--text-muted)]">{unit}</p>
        </article>
      ))}
    </section>
  );
}

function LotesTable({ lotes, onExpand, selected }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-[var(--border)]">
      <table className="min-w-[1120px] w-full text-center text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] bg-[var(--bg-surface)] text-xs uppercase tracking-wide text-[var(--text-muted)]">
            {["Lote", "Especie", "Volumen", "Origen", "Emisiones", "CO2 almacenado", "Balance", "Estado", "Evidencias", "Transportes", ""].map((header) => (
              <th key={header} className="px-3 py-3">{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {lotes.map((lote) => (
            <tr key={lote.id} className="border-b border-[#C9D6CF] text-[#1F2937] hover:bg-[var(--bg-surface)]">
              <td className="px-3 py-3 font-black">{lote.lote_id}</td>
              <td className="px-3 py-3">{lote.especie}</td>
              <td className="px-3 py-3">{formatNumber(lote.volumen_m3, 1)} m3</td>
              <td className="px-3 py-3">{lote.origen}</td>
              <td className="px-3 py-3">{formatNumber(lote.emisiones_generadas_kg_co2e, 1)}</td>
              <td className="px-3 py-3">{formatNumber(lote.co2_almacenado_kg, 1)}</td>
              <td className="px-3 py-3">{formatNumber(lote.balance_neto_kg_co2e, 1)}</td>
              <td className="px-3 py-3">
                <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-black ${statusClass(lote.estado_balance)}`}>
                  {lote.estado_balance}
                </span>
              </td>
              <td className="px-3 py-3">{lote.cantidad_evidencias || 0}</td>
              <td className="px-3 py-3">{lote.cantidad_transportes || 0}</td>
              <td className="px-3 py-3">
                <button
                  type="button"
                  onClick={() => onExpand(selected === lote.lote_id ? "" : lote.lote_id)}
                  className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-700"
                >
                  <ChevronDown size={14} />
                  Detalle
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!lotes.length ? (
        <p className="p-6 text-center text-sm font-semibold text-[var(--text-muted)]">
          No hay lotes forestales registrados.
        </p>
      ) : null}
    </div>
  );
}

function LoteDetail({ inputClass, lote, onCreateTransport, savingTransport, setTransportForm, transportForm }) {
  useEffect(() => {
    setTransportForm((current) => ({
      ...current,
      origen: current.origen || lote.origen || "",
      destino: current.destino || lote.destino || "",
    }));
  }, [lote, setTransportForm]);

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[0_18px_45px_var(--shadow)]">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Detalle de lote</p>
          <h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">{lote.lote_id}</h2>
          <p className="mt-2 max-w-3xl text-sm font-semibold leading-6 text-[var(--text-muted)]">{lote.descripcion_balance}</p>
        </div>
        {!lote.calculo_completo ? (
          <span className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-black text-amber-700">
            <AlertTriangle size={14} />
            Faltan: {lote.campos_faltantes?.join(", ")}
          </span>
        ) : null}
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <DetailList title="Registros de emision" rows={lote.registros_emision} resolver={(item) => `#${item.id} - ${item.fuente_emision} - ${formatNumber(item.emisiones_kg_co2e, 1)} kg`} />
        <DetailList title="Transportes asociados" rows={lote.transportes} resolver={(item) => `${item.patente || "Sin patente"} - ${formatNumber(item.distancia_km, 1)} km - ${formatNumber(item.emisiones_transporte_kg_co2e, 1)} kg`} />
        <DetailList title="Evidencias asociadas" rows={lote.evidencias} resolver={(item) => item.nombre || `Evidencia #${item.id}`} />
      </div>

      <form onSubmit={onCreateTransport} className="mt-5 rounded-3xl border border-emerald-200 bg-emerald-50/50 p-4">
        <div className="mb-4 flex items-center gap-2">
          <Truck className="text-emerald-700" size={20} />
          <h3 className="text-lg font-black text-[var(--text-main)]">Agregar transporte al lote</h3>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {[
            ["fecha", "date", ""],
            ["patente", "text", "Patente"],
            ["conductor", "text", "Conductor"],
            ["vehiculo", "text", "Vehiculo"],
            ["origen", "text", "Origen"],
            ["destino", "text", "Destino"],
            ["distancia_km", "number", "Distancia km"],
            ["litros_diesel", "number", "Litros diesel"],
            ["consumo_estimado_litro_km", "number", "Consumo L/km"],
          ].map(([name, type, placeholder]) => (
            <Field
              key={name}
              className={inputClass}
              form={transportForm}
              name={name}
              onChange={setTransportForm}
              placeholder={placeholder}
              required={["origen", "destino", "distancia_km"].includes(name)}
              type={type}
            />
          ))}
          <textarea
            className={`${inputClass} min-h-24 resize-y md:col-span-2 xl:col-span-4`}
            placeholder="Observaciones"
            value={transportForm.observaciones}
            onChange={(event) => setTransportForm((current) => ({ ...current, observaciones: event.target.value }))}
          />
        </div>
        <button
          type="submit"
          disabled={savingTransport}
          className="mt-4 inline-flex items-center gap-2 rounded-2xl bg-[var(--primary-dark)] px-5 py-3 text-sm font-black text-white disabled:opacity-60"
        >
          <Truck size={17} />
          {savingTransport ? "Guardando..." : "Agregar transporte"}
        </button>
      </form>
    </section>
  );
}

function DetailList({ title, rows = [], resolver }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
      <h3 className="text-sm font-black text-[var(--text-main)]">{title}</h3>
      <div className="mt-3 space-y-2">
        {rows.length ? rows.slice(0, 6).map((item) => (
          <p key={item.id} className="rounded-xl bg-white px-3 py-2 text-xs font-bold text-[var(--text-muted)]">
            {resolver(item)}
          </p>
        )) : (
          <p className="rounded-xl bg-white px-3 py-2 text-xs font-bold text-[var(--text-muted)]">Sin datos asociados.</p>
        )}
      </div>
    </div>
  );
}

export default LotesForestalesPage;
