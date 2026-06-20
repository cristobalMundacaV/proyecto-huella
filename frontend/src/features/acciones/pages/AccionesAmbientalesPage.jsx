import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Clock3, Leaf, Loader2, Plus, Search, Trash2, X } from "lucide-react";

import EmptyState from "@/shared/components/EmptyState";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import {
  createTraceableAction,
  deleteTraceableAction,
  getTraceableActions,
  updateTraceableAction,
} from "@/features/intelligence/services/traceableActionsApi";

const statusColumns = [
  { value: "pendiente", label: "Pendientes", hint: "Acciones creadas que aún no inician." },
  { value: "en_progreso", label: "En progreso", hint: "Acciones en ejecución operacional." },
  { value: "validacion", label: "En validación", hint: "Esperan evidencia o revisión ambiental." },
  { value: "completada", label: "Completadas", hint: "Acciones cerradas y trazadas." },
];

const inputClass = "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-900 outline-none transition focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100";

function todayPlus(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function emptyDraft() {
  return {
    title: "Nueva acción ambiental",
    description: "",
    responsible: "Equipo ambiental",
    dueDate: todayPlus(7),
    status: "pendiente",
    source: "Gestión ambiental",
    evidence: "Registro operativo y respaldo documental",
    trackingKpi: "avance semanal de acción ambiental",
    sourceCardId: "manual",
    obraCodigo: "",
    loteId: "",
    registroId: "",
    evidenciaId: "",
    metadata: { origin: "manual_actions_board" },
  };
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function statusTone(status) {
  return {
    pendiente: "border-amber-200 bg-amber-50 text-amber-800",
    en_progreso: "border-sky-200 bg-sky-50 text-sky-800",
    validacion: "border-violet-200 bg-violet-50 text-violet-800",
    completada: "border-emerald-200 bg-emerald-50 text-emerald-800",
  }[status] || "border-slate-200 bg-slate-50 text-slate-700";
}

function linkTypeLabel(type) {
  return {
    obra: "Obra",
    lote_forestal: "Lote forestal",
    registro_emision: "Registro crítico",
    evidencia: "Evidencia",
  }[type] || "Vínculo";
}

function AccionesAmbientalesPage() {
  const { activeConstructora, activeConstructoraId } = useConstructoraActiva();
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState(null);

  async function loadActions() {
    if (!activeConstructoraId) return;
    try {
      setLoading(true);
      setError("");
      const data = await getTraceableActions(activeConstructoraId);
      setActions(Array.isArray(data) ? data : []);
    } catch (requestError) {
      setError(requestError?.response?.data?.error || "No se pudieron cargar las acciones ambientales.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setActions([]);
    setDraft(null);
    loadActions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConstructoraId]);

  const filteredActions = useMemo(() => {
    const query = normalizeText(search);
    if (!query) return actions;
    return actions.filter((action) =>
      normalizeText([
        action.title,
        action.description,
        action.responsible,
        action.source,
        action.evidence,
        action.trackingKpi,
        action.linkedTo?.label,
        action.linkedTo?.type,
        action.obraCodigo,
        action.loteId,
        action.registroId,
        action.evidenciaId,
      ].join(" ")).includes(query)
    );
  }, [actions, search]);

  const stats = useMemo(() => {
    const total = actions.length;
    const completed = actions.filter((action) => action.status === "completada").length;
    const active = actions.filter((action) => ["pendiente", "en_progreso", "validacion"].includes(action.status)).length;
    const dueSoon = actions.filter((action) => action.dueDate && action.status !== "completada" && action.dueDate <= todayPlus(3)).length;
    return { total, completed, active, dueSoon };
  }, [actions]);

  async function saveDraft(event) {
    event.preventDefault();
    if (!draft || !activeConstructoraId) return;
    try {
      setSaving(true);
      setError("");
      const created = await createTraceableAction(activeConstructoraId, draft);
      setActions((current) => [created, ...current]);
      setDraft(null);
    } catch (requestError) {
      setError(requestError?.response?.data?.error || "No se pudo crear la acción ambiental.");
    } finally {
      setSaving(false);
    }
  }

  async function updateStatus(actionId, nextStatus) {
    const previous = actions;
    setActions((current) => current.map((action) => (action.id === actionId ? { ...action, status: nextStatus } : action)));
    try {
      const updated = await updateTraceableAction(activeConstructoraId, actionId, { status: nextStatus });
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
      await deleteTraceableAction(activeConstructoraId, actionId);
    } catch (requestError) {
      setActions(previous);
      setError(requestError?.response?.data?.error || "No se pudo eliminar la acción.");
    }
  }

  if (!activeConstructoraId) {
    return (
      <EmptyState
        title="Acciones ambientales"
        description="Selecciona una empresa activa para gestionar acciones ambientales trazables."
      />
    );
  }

  return (
    <main className="mx-auto max-w-7xl space-y-6">
      <section className="overflow-hidden rounded-[32px] border border-emerald-300/40 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.20),transparent_32%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] p-6 shadow-[0_28px_80px_rgba(15,118,110,0.14)] ring-1 ring-white/70">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="rounded-3xl border border-emerald-200 bg-white/80 p-4 text-emerald-800 shadow-sm">
              <CheckCircle2 size={30} />
            </div>
            <div>
              <p className="text-xs font-black uppercase tracking-[0.24em] text-emerald-700">Seguimiento ambiental</p>
              <h1 className="mt-2 text-3xl font-black tracking-tight text-[var(--text-main)] sm:text-4xl">
                Acciones ambientales de {activeConstructora?.nombre || "la empresa"}
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">
                Convierte recomendaciones, hallazgos y compromisos en acciones con responsable, fecha objetivo, evidencia, KPI y vínculo operacional.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setDraft(emptyDraft())}
            className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white shadow-[0_14px_30px_rgba(15,124,109,0.18)] hover:bg-[var(--primary-dark)]"
          >
            <Plus size={18} />
            Nueva acción
          </button>
        </div>
      </section>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm font-bold text-rose-700">
          {error}
        </div>
      ) : null}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard icon={<Leaf size={18} />} label="Total acciones" value={stats.total} />
        <SummaryCard icon={<Clock3 size={18} />} label="Activas" value={stats.active} />
        <SummaryCard icon={<CheckCircle2 size={18} />} label="Completadas" value={stats.completed} />
        <SummaryCard icon={<Clock3 size={18} />} label="Próximas a vencer" value={stats.dueSoon} />
      </section>

      <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)]">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Tablero de gestión</p>
            <h2 className="text-2xl font-black text-[var(--text-main)]">Seguimiento por estado</h2>
            <p className="mt-1 text-sm text-[var(--text-muted)]">
              {filteredActions.length} acciones visibles de {actions.length} registradas.
            </p>
          </div>
          <label className="relative block w-full max-w-md">
            <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar acción, responsable, evidencia, KPI o vínculo"
              className="w-full rounded-2xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-sm text-slate-900 outline-none transition focus:border-emerald-400/60"
            />
          </label>
        </div>

        {loading ? (
          <div className="mt-5 rounded-2xl border border-dashed border-[var(--border)] bg-[var(--bg-surface)] p-8 text-center text-sm font-bold text-[var(--text-muted)]">
            <Loader2 className="mx-auto mb-2 animate-spin text-emerald-700" size={22} />
            Cargando acciones ambientales...
          </div>
        ) : filteredActions.length ? (
          <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-4">
            {statusColumns.map((column) => (
              <ActionColumn
                actions={filteredActions.filter((action) => action.status === column.value)}
                column={column}
                key={column.value}
                onDelete={removeAction}
                onUpdateStatus={updateStatus}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            title="Sin acciones ambientales"
            description="Crea una acción desde Inteligencia o manualmente para comenzar seguimiento."
          />
        )}
      </section>

      {draft ? (
        <ActionModal
          draft={draft}
          onClose={() => setDraft(null)}
          onSave={saveDraft}
          saving={saving}
          setDraft={setDraft}
        />
      ) : null}
    </main>
  );
}

function SummaryCard({ icon, label, value }) {
  return (
    <article className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 text-center shadow-[var(--shadow-card)]">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-200 bg-emerald-50 text-emerald-700">
        {icon}
      </div>
      <p className="mt-3 text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)]">{label}</p>
      <p className="mt-2 text-3xl font-black text-[var(--text-main)]">{value}</p>
    </article>
  );
}

function ActionColumn({ actions, column, onDelete, onUpdateStatus }) {
  return (
    <section className="min-h-[240px] rounded-3xl border border-slate-200 bg-slate-50/80 p-4">
      <div className="mb-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-black text-[var(--text-main)]">{column.label}</h3>
          <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-black text-slate-600">{actions.length}</span>
        </div>
        <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">{column.hint}</p>
      </div>

      <div className="space-y-3">
        {actions.map((action) => (
          <article key={action.id} className="rounded-2xl border border-white bg-white p-4 shadow-[0_10px_26px_rgba(15,23,42,0.05)]">
            <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-black ${statusTone(action.status)}`}>
              {column.label.replace(/s$/, "")}
            </span>
            <h4 className="mt-3 text-sm font-black text-[var(--text-main)]">{action.title}</h4>
            <p className="mt-1 line-clamp-3 text-xs leading-5 text-[var(--text-muted)]">{action.description}</p>
            {action.linkedTo ? (
              <div className="mt-3 rounded-2xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs leading-5 text-emerald-900">
                <strong>Vinculado a {linkTypeLabel(action.linkedTo.type)}:</strong> {action.linkedTo.label}
              </div>
            ) : (
              <div className="mt-3 rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-500">
                Sin vínculo operacional
              </div>
            )}
            <div className="mt-3 space-y-2 text-xs text-slate-600">
              <p><strong>Responsable:</strong> {action.responsible || "Equipo ambiental"}</p>
              <p><strong>Fecha:</strong> {action.dueDate || "Sin fecha"}</p>
              <p><strong>KPI:</strong> {action.trackingKpi || "Sin KPI"}</p>
            </div>
            <div className="mt-4 flex flex-col gap-2">
              <select
                value={action.status}
                onChange={(event) => onUpdateStatus(action.id, event.target.value)}
                className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-black text-slate-700 outline-none"
              >
                {statusColumns.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => onDelete(action.id)}
                className="inline-flex items-center justify-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-black text-rose-700"
              >
                <Trash2 size={14} />
                Quitar
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ActionModal({ draft, onClose, onSave, saving, setDraft }) {
  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/35 px-4 py-6 backdrop-blur-sm">
      <form onSubmit={onSave} className="relative max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-[32px] border border-emerald-100 bg-white p-5 shadow-[0_30px_90px_rgba(15,23,42,0.22)] sm:p-6">
        <button type="button" onClick={onClose} className="absolute right-4 top-4 rounded-2xl border border-slate-200 bg-white p-2 text-slate-600 shadow-sm hover:bg-slate-50" aria-label="Cerrar acción">
          <X size={18} />
        </button>

        <div className="mb-5 pr-12">
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Nueva acción ambiental</p>
          <h3 className="mt-1 text-2xl font-black text-[var(--text-main)]">Seguimiento trazable</h3>
          <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">Crea una acción con responsable, fecha, evidencia, KPI y vínculo operacional.</p>
        </div>

        <div className="grid grid-cols-1 gap-4">
          <Field label="Título"><input className={inputClass} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></Field>
          <Field label="Descripción"><textarea className={`${inputClass} min-h-28 resize-y`} value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></Field>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Responsable"><input className={inputClass} value={draft.responsible} onChange={(event) => setDraft({ ...draft, responsible: event.target.value })} /></Field>
            <Field label="Fecha objetivo"><input className={inputClass} type="date" value={draft.dueDate} onChange={(event) => setDraft({ ...draft, dueDate: event.target.value })} /></Field>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Origen"><input className={inputClass} value={draft.source} onChange={(event) => setDraft({ ...draft, source: event.target.value })} /></Field>
            <Field label="Estado">
              <select className={inputClass} value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}>
                {statusColumns.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </Field>
          </div>

          <section className="rounded-3xl border border-emerald-100 bg-emerald-50/60 p-4">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-700">Vínculo operacional</p>
            <p className="mt-1 text-xs leading-5 text-emerald-900">
              Completa solo el vínculo que corresponda. El backend validará que pertenezca a la empresa activa.
            </p>
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Código de obra"><input className={inputClass} value={draft.obraCodigo} onChange={(event) => setDraft({ ...draft, obraCodigo: event.target.value })} placeholder="Ej: OBRA-001" /></Field>
              <Field label="ID de lote forestal"><input className={inputClass} value={draft.loteId} onChange={(event) => setDraft({ ...draft, loteId: event.target.value })} placeholder="Ej: LOTE-PINO-001" /></Field>
              <Field label="ID registro crítico"><input className={inputClass} value={draft.registroId} onChange={(event) => setDraft({ ...draft, registroId: event.target.value })} placeholder="Ej: 123" /></Field>
              <Field label="ID evidencia"><input className={inputClass} value={draft.evidenciaId} onChange={(event) => setDraft({ ...draft, evidenciaId: event.target.value })} placeholder="Ej: 45" /></Field>
            </div>
          </section>

          <Field label="Evidencia esperada"><input className={inputClass} value={draft.evidence} onChange={(event) => setDraft({ ...draft, evidence: event.target.value })} /></Field>
          <Field label="KPI de seguimiento"><input className={inputClass} value={draft.trackingKpi} onChange={(event) => setDraft({ ...draft, trackingKpi: event.target.value })} /></Field>
        </div>

        <button type="submit" disabled={saving} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white shadow-[0_14px_30px_rgba(15,124,109,0.18)] hover:bg-[var(--primary-dark)] disabled:opacity-60">
          {saving ? <Loader2 className="animate-spin" size={17} /> : <CheckCircle2 size={17} />}
          {saving ? "Guardando..." : "Guardar acción"}
        </button>
      </form>
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

export default AccionesAmbientalesPage;
