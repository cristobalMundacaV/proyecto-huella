import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Clock3, Lightbulb, Loader2, Plus, Sparkles, X } from "lucide-react";

import {
  createTraceableAction,
  deleteTraceableAction,
  getTraceableActions,
  updateTraceableAction,
} from "../services/traceableActionsApi";

const inputClass = "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-900 outline-none transition focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100";

const statusOptions = [
  { value: "pendiente", label: "Pendiente" },
  { value: "en_progreso", label: "En progreso" },
  { value: "validacion", label: "En validación" },
  { value: "completada", label: "Completada" },
];

function todayPlus(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function buildInitialAction(card) {
  return {
    title: card?.title || "Acción ambiental",
    description: card?.recommended_action || card?.diagnosis || "Definir acción ambiental medible.",
    responsible: "Equipo ambiental",
    dueDate: todayPlus(7),
    status: "pendiente",
    source: card?.area || card?.source || card?.stage || "Inteligencia ambiental",
    evidence: card?.id === "trazabilidad_soporte" ? "Evidencia documental vinculada" : "Registro operativo y respaldo documental",
    trackingKpi: card?.tracking_kpi || "avance semanal de acción ambiental",
    sourceCardId: card?.id || "manual",
    metadata: {
      source_card: card?.id || "manual",
      priority: card?.priority || "media",
    },
  };
}

function statusTone(status) {
  return {
    pendiente: "border-amber-200 bg-amber-50 text-amber-800",
    en_progreso: "border-sky-200 bg-sky-50 text-sky-800",
    validacion: "border-violet-200 bg-violet-50 text-violet-800",
    completada: "border-emerald-200 bg-emerald-50 text-emerald-800",
  }[status] || "border-slate-200 bg-slate-50 text-slate-700";
}

function statusLabel(status) {
  return statusOptions.find((option) => option.value === status)?.label || "Pendiente";
}

function TraceableActionsPanel({ cards = [], constructoraId }) {
  const [actions, setActions] = useState([]);
  const [draft, setDraft] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadActions() {
      if (!constructoraId) return;
      try {
        setLoading(true);
        setError("");
        const data = await getTraceableActions(constructoraId);
        if (!cancelled) setActions(Array.isArray(data) ? data : []);
      } catch (requestError) {
        if (!cancelled) setError(requestError?.response?.data?.error || "No se pudieron cargar las acciones ambientales.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    setDraft(null);
    loadActions();

    return () => {
      cancelled = true;
    };
  }, [constructoraId]);

  const stats = useMemo(() => {
    const total = actions.length;
    const completed = actions.filter((action) => action.status === "completada").length;
    const inProgress = actions.filter((action) => ["en_progreso", "validacion"].includes(action.status)).length;
    return { total, completed, inProgress };
  }, [actions]);

  function openDraft(card) {
    setDraft(buildInitialAction(card));
  }

  async function saveDraft(event) {
    event.preventDefault();
    if (!draft || !constructoraId) return;
    try {
      setSaving(true);
      setError("");
      const created = await createTraceableAction(constructoraId, draft);
      setActions((current) => [created, ...current]);
      setDraft(null);
    } catch (requestError) {
      setError(requestError?.response?.data?.error || "No se pudo crear la acción ambiental.");
    } finally {
      setSaving(false);
    }
  }

  async function updateActionStatus(actionId, nextStatus) {
    const previous = actions;
    setActions((current) => current.map((action) => (action.id === actionId ? { ...action, status: nextStatus } : action)));
    try {
      const updated = await updateTraceableAction(constructoraId, actionId, { status: nextStatus });
      setActions((current) => current.map((action) => (action.id === actionId ? updated : action)));
    } catch (requestError) {
      setActions(previous);
      setError(requestError?.response?.data?.error || "No se pudo actualizar la acción.");
    }
  }

  async function removeAction(actionId) {
    const previous = actions;
    setActions((current) => current.filter((action) => action.id !== actionId));
    try {
      await deleteTraceableAction(constructoraId, actionId);
    } catch (requestError) {
      setActions(previous);
      setError(requestError?.response?.data?.error || "No se pudo eliminar la acción.");
    }
  }

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)] ring-1 ring-white/40">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl bg-emerald-50 p-3 text-emerald-800">
            <Sparkles size={20} />
          </div>
          <div>
            <p className="text-xs font-black uppercase tracking-[0.22em] text-emerald-700">Acciones ambientales trazables</p>
            <h3 className="text-xl font-black text-[var(--text-main)]">Convierte recomendaciones en gestión real</h3>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">
              Cada acción queda guardada en la empresa con responsable, fecha objetivo, estado, evidencia esperada y KPI de seguimiento.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 text-center text-xs font-black text-slate-600">
          <MetricBox label="Total" value={stats.total} />
          <MetricBox label="Activas" value={stats.inProgress} />
          <MetricBox label="Cerradas" value={stats.completed} />
        </div>
      </div>

      {error ? (
        <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-3 text-sm font-bold text-rose-700">
          {error}
        </div>
      ) : null}

      <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-3">
        {cards.slice(0, 3).map((card) => (
          <button
            key={card.id}
            type="button"
            onClick={() => openDraft(card)}
            className="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4 text-left transition hover:-translate-y-0.5 hover:border-emerald-300 hover:bg-emerald-50"
          >
            <div className="flex items-start gap-2">
              <Plus className="mt-0.5 shrink-0 text-emerald-700" size={17} />
              <div>
                <p className="text-sm font-black text-[var(--text-main)]">Crear acción: {card.title}</p>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-[var(--text-muted)]">
                  {card.recommended_action || card.diagnosis}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="mt-5 rounded-2xl border border-dashed border-[var(--border)] bg-[var(--bg-surface)] p-6 text-center text-sm font-bold text-[var(--text-muted)]">
          <Loader2 className="mx-auto mb-2 animate-spin text-emerald-700" size={20} />
          Cargando acciones ambientales...
        </div>
      ) : actions.length ? (
        <div className="mt-5 space-y-3">
          {actions.slice(0, 6).map((action) => (
            <article key={action.id} className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full border px-3 py-1 text-xs font-black ${statusTone(action.status)}`}>
                      {statusLabel(action.status)}
                    </span>
                    <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-bold text-slate-600">
                      {action.source}
                    </span>
                  </div>
                  <h4 className="mt-3 text-base font-black text-[var(--text-main)]">{action.title}</h4>
                  <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">{action.description}</p>
                </div>

                <div className="flex shrink-0 flex-col gap-2 sm:flex-row lg:flex-col">
                  <select
                    value={action.status}
                    onChange={(event) => updateActionStatus(action.id, event.target.value)}
                    className="rounded-2xl border border-[var(--border)] bg-white px-3 py-2 text-xs font-black text-slate-700 outline-none"
                  >
                    {statusOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => removeAction(action.id)}
                    className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-black text-rose-700"
                  >
                    Quitar
                  </button>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <DetailBox icon={<CheckCircle2 size={15} />} label="Responsable" value={action.responsible} />
                <DetailBox icon={<Clock3 size={15} />} label="Fecha objetivo" value={action.dueDate || "Sin fecha"} />
                <DetailBox icon={<Lightbulb size={15} />} label="KPI" value={action.trackingKpi} />
              </div>

              <div className="mt-3 rounded-2xl border border-emerald-100 bg-white px-4 py-3 text-sm leading-6 text-slate-700">
                <strong>Evidencia esperada:</strong> {action.evidence}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="mt-5 rounded-2xl border border-dashed border-[var(--border)] bg-[var(--bg-surface)] p-6 text-center text-sm font-semibold text-[var(--text-muted)]">
          Aún no hay acciones creadas. Convierte una recomendación en acción para empezar seguimiento.
        </div>
      )}

      {draft ? (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/35 px-4 py-6 backdrop-blur-sm">
          <form onSubmit={saveDraft} className="relative max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-[32px] border border-emerald-100 bg-white p-5 shadow-[0_30px_90px_rgba(15,23,42,0.22)] sm:p-6">
            <button
              type="button"
              onClick={() => setDraft(null)}
              className="absolute right-4 top-4 rounded-2xl border border-slate-200 bg-white p-2 text-slate-600 shadow-sm hover:bg-slate-50"
              aria-label="Cerrar acción"
            >
              <X size={18} />
            </button>

            <div className="mb-5 pr-12">
              <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Nueva acción ambiental</p>
              <h3 className="mt-1 text-2xl font-black text-[var(--text-main)]">Convertir recomendación en seguimiento</h3>
              <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
                Ajusta responsable, fecha, evidencia y KPI antes de guardar la acción.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4">
              <Field label="Título">
                <input value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} className={inputClass} />
              </Field>
              <Field label="Descripción">
                <textarea value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} className={`${inputClass} min-h-28 resize-y`} />
              </Field>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Responsable">
                  <input value={draft.responsible} onChange={(event) => setDraft({ ...draft, responsible: event.target.value })} className={inputClass} />
                </Field>
                <Field label="Fecha objetivo">
                  <input type="date" value={draft.dueDate} onChange={(event) => setDraft({ ...draft, dueDate: event.target.value })} className={inputClass} />
                </Field>
              </div>
              <Field label="Evidencia esperada">
                <input value={draft.evidence} onChange={(event) => setDraft({ ...draft, evidence: event.target.value })} className={inputClass} />
              </Field>
              <Field label="KPI de seguimiento">
                <input value={draft.trackingKpi} onChange={(event) => setDraft({ ...draft, trackingKpi: event.target.value })} className={inputClass} />
              </Field>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white shadow-[0_14px_30px_rgba(15,124,109,0.18)] hover:bg-[var(--primary-dark)] disabled:opacity-60"
            >
              {saving ? <Loader2 className="animate-spin" size={17} /> : <CheckCircle2 size={17} />}
              {saving ? "Guardando..." : "Guardar acción trazable"}
            </button>
          </form>
        </div>
      ) : null}
    </section>
  );
}

function MetricBox({ label, value }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3">
      <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
      <p className="text-lg font-black text-[var(--text-main)]">{value}</p>
    </div>
  );
}

function DetailBox({ icon, label, value }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white px-4 py-3">
      <div className="flex items-center gap-2 text-emerald-700">
        {icon}
        <p className="text-[10px] font-black uppercase tracking-wide">{label}</p>
      </div>
      <p className="mt-1 text-xs font-bold text-slate-700">{value}</p>
    </div>
  );
}

function Field({ children, label }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-black uppercase tracking-[0.16em] text-slate-500">{label}</span>
      {children}
    </label>
  );
}

export default TraceableActionsPanel;
