import { useEffect, useMemo, useState } from "react";
import { BrainCircuit, CheckCircle2, Clock3, Lightbulb, Radar, Route, Sparkles } from "lucide-react";

import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { getIntelligenceRecommendations } from "@/shared/services/intelligenceApi";
import { formatNumber } from "@/shared/utils/formatters";

const scopeOptions = [
  { value: "dashboard", label: "Dashboard" },
  { value: "obra", label: "Obra" },
  { value: "etapas", label: "Etapas" },
  { value: "materiales", label: "Materiales" },
  { value: "maquinaria", label: "Maquinaria" },
  { value: "iot", label: "Sensores IoT" },
  { value: "evidencias", label: "Evidencias" },
];

function priorityLabel(priority) {
  const labels = {
    alta: "Alta prioridad",
    media: "Prioridad media",
    estrategica: "Estratégica",
  };
  return labels[priority] || "Recomendación";
}

function cardIcon(cardId) {
  if (cardId === "alerta_iot") return <Radar size={20} />;
  if (cardId === "escenario_recomendado") return <Route size={20} />;
  if (cardId === "etapa_prioritaria") return <Clock3 size={20} />;
  if (cardId === "trazabilidad_soporte") return <CheckCircle2 size={20} />;
  return <Lightbulb size={20} />;
}

function normalizeCards(data) {
  return Array.isArray(data?.cards) ? data.cards : data?.structured?.active_cards || [];
}

function RecommendationCard({ card }) {
  const impact = card.impact_kg_co2e != null ? `${formatNumber(card.impact_kg_co2e, 1)} kg CO₂e` : null;
  const share = card.impact_share_pct != null ? `${formatNumber(card.impact_share_pct, 1)}% del total` : null;

  return (
    <article className="group rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)] ring-1 ring-white/40 transition hover:-translate-y-0.5 hover:shadow-[0_24px_60px_rgba(15,23,42,0.12)]">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-3 text-[var(--primary-dark)]">
            {cardIcon(card.id)}
          </div>
          <div>
            <p className="text-xs font-black uppercase tracking-[0.22em] text-emerald-700">{priorityLabel(card.priority)}</p>
            <h3 className="mt-1 text-lg font-black text-[var(--text-main)]">{card.title}</h3>
          </div>
        </div>
        {card.area && <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-800">{card.area}</span>}
      </div>

      <p className="mt-4 text-sm leading-6 text-[var(--text-muted)]">{card.diagnosis || card.target_state}</p>

      {(impact || share || card.stage || card.source || card.critical_device) && (
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {impact && <Metric label="Impacto" value={impact} />}
          {share && <Metric label="Participación" value={share} />}
          {card.stage && <Metric label="Etapa" value={card.stage} />}
          {card.source && <Metric label="Fuente" value={card.source} />}
          {card.critical_device && <Metric label="Dispositivo crítico" value={card.critical_device} />}
        </div>
      )}

      {card.why_it_matters && (
        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
          <strong>Por qué importa:</strong> {card.why_it_matters}
        </div>
      )}

      {card.recommended_action && (
        <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm leading-6 text-emerald-950">
          <strong>Acción recomendada:</strong> {card.recommended_action}
        </div>
      )}

      {Array.isArray(card.how_to_reach_it) && card.how_to_reach_it.length > 0 && (
        <ul className="mt-4 space-y-2 text-sm text-[var(--text-muted)]">
          {card.how_to_reach_it.map((item) => (
            <li key={item} className="flex gap-2 rounded-2xl bg-[var(--bg-surface)] px-3 py-2">
              <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-700" size={16} />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}

      {card.tracking_kpi && <p className="mt-4 text-xs font-bold uppercase tracking-wide text-slate-500">KPI de seguimiento: {card.tracking_kpi}</p>}
    </article>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-3">
      <p className="text-[11px] font-bold uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 text-sm font-black text-[var(--text-main)]">{value}</p>
    </div>
  );
}

function ActionPlan({ actions = [] }) {
  if (!actions.length) return null;

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)] ring-1 ring-white/40">
      <div className="flex items-center gap-3">
        <div className="rounded-2xl bg-emerald-50 p-3 text-emerald-800">
          <Sparkles size={20} />
        </div>
        <div>
          <p className="text-xs font-black uppercase tracking-[0.22em] text-emerald-700">Plan de acción</p>
          <h3 className="text-xl font-black text-[var(--text-main)]">Qué hacer después de leer la huella</h3>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-2">
        {actions.map((action) => (
          <article key={action.id || action.title} className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-black text-[var(--text-main)]">{action.title}</p>
              <span className="rounded-full bg-white px-3 py-1 text-[11px] font-bold uppercase text-slate-600 shadow-sm">{action.horizon}</span>
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">{action.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function IntelligencePanel({ initialScope = "dashboard", compact = false }) {
  const { activeConstructora, activeConstructoraId } = useConstructoraActiva();
  const [scope, setScope] = useState(initialScope);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setScope(initialScope);
  }, [initialScope]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!activeConstructoraId) return;
      try {
        setLoading(true);
        setError("");
        const response = await getIntelligenceRecommendations({
          constructora_id: activeConstructoraId,
          iot_hours: 24,
          scope,
        });
        if (!cancelled) setData(response);
      } catch (requestError) {
        if (!cancelled) setError(requestError.response?.data?.error || "No se pudo cargar la inteligencia ambiental.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [activeConstructoraId, scope]);

  const cards = useMemo(() => normalizeCards(data), [data]);
  const actions = data?.actions || data?.structured?.actions || [];
  const context = data?.context || {};

  if (!activeConstructoraId) {
    return (
      <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 text-center text-[var(--text-muted)]">
        Selecciona una empresa para activar la inteligencia ambiental.
      </div>
    );
  }

  return (
    <section className={compact ? "space-y-4" : "mx-auto max-w-7xl space-y-6"}>
      <div className="overflow-hidden rounded-[32px] border border-emerald-300/40 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.22),transparent_32%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] p-6 shadow-[0_28px_80px_rgba(15,118,110,0.16)] ring-1 ring-white/70">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="rounded-3xl border border-emerald-200 bg-white/80 p-4 text-emerald-800 shadow-sm">
              <BrainCircuit size={28} />
            </div>
            <div>
              <p className="text-xs font-black uppercase tracking-[0.26em] text-emerald-700">Carbono Zero Intelligence</p>
              <h2 className="mt-2 text-2xl font-black tracking-tight text-[var(--text-main)] sm:text-3xl">
                Recomendaciones accionables para {activeConstructora?.nombre || "la empresa"}
              </h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">
                No solo mide la huella: identifica el foco principal, la etapa prioritaria, el escenario recomendado y las acciones que permiten mejorar la gestión ambiental.
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <select
              value={scope}
              onChange={(event) => setScope(event.target.value)}
              className="rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-sm font-bold text-slate-700 shadow-sm outline-none focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100"
            >
              {scopeOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Metric label="Motor activo" value={data?.engine === "ia" ? "IA contratada" : "Motor Carbono Zero"} />
          <Metric label="Foco principal" value={context.categoria_critica || "Sin datos"} />
          <Metric label="Etapa prioritaria" value={context.etapa_critica || "Sin etapa"} />
        </div>
      </div>

      {loading && (
        <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 text-center text-sm font-bold text-[var(--text-muted)]">
          Analizando huella, sensores, etapas y focos críticos...
        </div>
      )}

      {error && (
        <div className="rounded-3xl border border-rose-200 bg-rose-50 p-5 text-sm font-bold text-rose-800">
          {error}
        </div>
      )}

      {!loading && !error && cards.length > 0 && (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          {cards.map((card) => <RecommendationCard key={card.id} card={card} />)}
        </div>
      )}

      {!loading && !error && <ActionPlan actions={actions} />}
    </section>
  );
}

export default IntelligencePanel;
