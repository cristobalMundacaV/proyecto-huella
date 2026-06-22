import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, BrainCircuit, CheckCircle2, Clock3, FlaskConical, Lightbulb, Radar, Route, ShieldCheck, Sparkles, Target, TrendingDown } from "lucide-react";

import DecisionToActionModal from "@/core/environmental/components/DecisionToActionModal";
import EnvironmentalDecisionPriorityList from "@/core/environmental/components/EnvironmentalDecisionPriorityList";
import EnvironmentalRecommendationList from "@/core/environmental/components/EnvironmentalRecommendationList";
import EnvironmentalScenarioList from "@/core/environmental/components/EnvironmentalScenarioList";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { createActionFromDecision, getDecisionActionPreview } from "@/features/environmental/services/environmentalDecisionActionApi";
import { getEnvironmentalDecisionPriorities } from "@/features/environmental/services/environmentalDecisionPriorityApi";
import { getEnvironmentalKpis } from "@/features/environmental/services/environmentalKpiApi";
import { getEnvironmentalRecommendations } from "@/features/environmental/services/environmentalRecommendationApi";
import { getEnvironmentalScenarios } from "@/features/environmental/services/environmentalScenarioApi";
import { getIntelligenceRecommendations } from "@/shared/services/intelligenceApi";
import { formatNumber } from "@/shared/utils/formatters";
import TraceableActionsPanel from "./TraceableActionsPanel";

const scopeOptions = [
  { value: "dashboard", label: "Dashboard" },
  { value: "obra", label: "Obra" },
  { value: "etapas", label: "Etapas" },
  { value: "materiales", label: "Materiales" },
  { value: "maquinaria", label: "Maquinaria" },
  { value: "iot", label: "Sensores IoT" },
  { value: "evidencias", label: "Evidencias" },
];

const intelligenceTabs = [
  { value: "vision", label: "Visión inteligente" },
  { value: "decisiones", label: "Decisiones" },
  { value: "escenarios", label: "Escenarios" },
  { value: "recomendaciones", label: "Recomendaciones" },
  { value: "acciones", label: "Acciones" },
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

function fallbackCards(context = {}, scope = "dashboard") {
  const categoria = context.categoria_critica || context.foco_principal || "la fuente principal";
  const etapa = context.etapa_critica || context.etapa_prioritaria || "la etapa prioritaria";
  const fuente = context.fuente_critica || context.source || "el registro de mayor impacto";
  const isEvidenceScope = scope === "evidencias";
  const isIotScope = scope === "iot";

  return [
    {
      id: "etapa_prioritaria",
      priority: "alta",
      title: "Etapa prioritaria",
      area: etapa,
      diagnosis: `La etapa ${etapa} concentra un foco ambiental que debe revisarse antes de intervenir procesos menores.`,
      stage: etapa,
      source: fuente,
      recommended_action: "Revisar fuentes críticas de esta etapa, validar responsables operacionales y definir una acción de reducción medible antes del siguiente ciclo de control.",
      tracking_kpi: "kg CO2e por etapa y fuente",
    },
    {
      id: "foco_reduccion",
      priority: "alta",
      title: isIotScope ? "Alerta operacional" : "Foco principal de reducción",
      area: categoria,
      diagnosis: isIotScope
        ? "Los sensores deben usarse para detectar desviaciones operacionales antes de que se transformen en consumo o emisión acumulada."
        : `El foco principal está en ${categoria}. Debe convertirse en una acción operacional concreta, no solo en una observación del dashboard.`,
      source: fuente,
      why_it_matters: isIotScope
        ? "Una desviación temprana permite corregir consumo, operación o mantenimiento antes de cerrar el periodo."
        : "Este bloque explica una parte relevante de la huella y puede generar reducciones visibles si se controla por etapa, turno o responsable.",
      recommended_action: isIotScope
        ? "Revisar dispositivos activos, comparar lecturas recientes y definir umbrales de alerta por consumo o actividad."
        : "Separar registros por responsable, validar evidencia y atacar primero la fuente que concentra más kg CO2e.",
      tracking_kpi: isIotScope ? "alertas por dispositivo y consumo anómalo" : "kg CO2e por fuente crítica",
    },
    {
      id: isEvidenceScope ? "trazabilidad_soporte" : "escenario_recomendado",
      priority: "estrategica",
      title: isEvidenceScope ? "Trazabilidad documental" : "Escenario recomendado",
      area: isEvidenceScope ? "Evidencias" : "Gestión",
      diagnosis: isEvidenceScope
        ? "La reducción ambiental necesita respaldo documental suficiente para sostener auditoría, reportes y decisiones internas."
        : "El siguiente paso es convertir el diagnóstico en un escenario de gestión con responsables, evidencia y seguimiento.",
      why_it_matters: isEvidenceScope
        ? "Sin evidencias, la medición pierde fuerza para auditorías, clientes, licitaciones o gestión interna."
        : "Una recomendación sin seguimiento se queda en diagnóstico; el valor está en medir si la acción redujo el impacto real.",
      recommended_action: isEvidenceScope
        ? "Priorizar evidencias faltantes de fuentes críticas y vincular cada respaldo al registro ambiental correspondiente."
        : "Definir una acción semanal, asignar responsable y revisar el KPI de seguimiento en el próximo periodo.",
      tracking_kpi: isEvidenceScope ? "% registros críticos con evidencia" : "avance semanal de acción ambiental",
    },
  ];
}

function ensureThreeCards(rawCards, context, scope) {
  const normalized = Array.isArray(rawCards) ? rawCards.filter(Boolean) : [];
  const selected = [];
  const usedIds = new Set();

  normalized.forEach((card, index) => {
    if (selected.length >= 3) return;
    const safeId = card.id || `motor_card_${index + 1}`;
    if (usedIds.has(safeId)) return;
    selected.push({ ...card, id: safeId });
    usedIds.add(safeId);
  });

  fallbackCards(context, scope).forEach((card) => {
    if (selected.length >= 3) return;
    if (usedIds.has(card.id)) return;
    selected.push(card);
    usedIds.add(card.id);
  });

  return selected.slice(0, 3);
}

function pickReadyPriority(priorities = []) {
  return priorities.find((priority) => priority.status === "ready") || priorities[0] || null;
}

function pickBestScenario(scenarios = []) {
  return (
    scenarios.find((scenario) => scenario.status === "available") ||
    scenarios.find((scenario) => scenario.status === "partial") ||
    scenarios[0] ||
    null
  );
}

function formatImpactValue(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "Requiere datos";
  const number = Number(value);
  if (!Number.isFinite(number)) return value;
  return `${formatNumber(number, 1)}${suffix}`;
}

function buildOperationalInsights({ cards, context, kpis, priorities, scenarios }) {
  const priority = pickReadyPriority(priorities);
  const scenario = pickBestScenario(scenarios);
  const topSource = kpis?.top_sources?.[0];
  const topCategory = kpis?.top_categories?.[0];
  const fallbackCard = cards[0] || {};

  const focusLabel = topSource?.label || topSource?.name || priority?.area || fallbackCard.source || context.fuente_critica || "Fuente crítica";
  const categoryLabel = topCategory?.label || topCategory?.name || context.categoria_critica || priority?.area || "Categoría crítica";
  const stageLabel = priority?.stage || priority?.metadata?.stage || context.etapa_critica || fallbackCard.stage || "Etapa prioritaria";
  const focusImpact = topSource?.kg_co2e || topSource?.emissions_kg_co2e || priority?.expected_impact?.kg_co2e;
  const participation = topSource?.share_pct || topCategory?.share_pct || priority?.expected_impact?.pct;

  return [
    {
      icon: Target,
      tone: "emerald",
      eyebrow: "Alta prioridad",
      title: "Foco principal de reducción",
      badge: categoryLabel,
      description: `El foco principal está en ${categoryLabel}, especialmente en ${focusLabel}.`,
      facts: [
        ["Impacto", formatImpactValue(focusImpact, " kg CO₂e")],
        ["Participación", formatImpactValue(participation, "% del total")],
        ["Fuente", focusLabel],
      ],
      warning: "La mayor presión ambiental está en esta categoría. Conviene revisarla antes de seguir cargando acciones menores.",
      action: priority?.recommended_decision || "Comparar alternativas, revisar especificaciones técnicas y priorizar opciones con menor factor de emisión.",
      kpi: priority?.tracking_kpi || "kg CO₂e por fuente crítica",
    },
    {
      icon: Clock3,
      tone: "blue",
      eyebrow: "Alta prioridad",
      title: "Etapa prioritaria",
      badge: stageLabel,
      description: `La etapa ${stageLabel} concentra el mayor impacto ambiental registrado.`,
      facts: [
        ["Impacto", formatImpactValue(priority?.technical_basis?.match?.(/([0-9.,]+)\s*kg/i)?.[1] || priority?.expected_impact?.kg_co2e, " kg CO₂e")],
        ["Prioridad", priority?.priority || "alta"],
        ["Score", formatImpactValue(priority?.score)],
      ],
      success: `Acción recomendada: ${priority?.next_step || "revisar las fuentes críticas de esta etapa y definir una acción medible."}`,
      kpi: priority?.tracking_kpi || "kg CO₂e por etapa y fuente",
    },
    {
      icon: Route,
      tone: "violet",
      eyebrow: "Estratégica",
      title: "Escenario recomendado",
      badge: scenario?.status === "available" ? "Disponible" : scenario?.status || "En análisis",
      description: scenario?.title || scenario?.name || "Obra controlada con foco en reducción operacional, no solo en reporte de huella.",
      bullets: [
        "Priorizar fuentes que concentran mayor kg CO₂e.",
        "Separar emisiones por obra, etapa y categoría para detectar desviaciones.",
        "Vincular evidencias a registros críticos como respaldo.",
        "Revisar avances semanalmente y cerrar acciones con responsables.",
      ],
      kpi: scenario?.tracking_kpi || "avance semanal de acción ambiental",
    },
  ];
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

function OperationalInsightCard({ insight }) {
  const Icon = insight.icon;
  const tone = {
    emerald: "border-emerald-200 bg-white text-emerald-900",
    blue: "border-blue-200 bg-white text-blue-950",
    violet: "border-violet-200 bg-white text-violet-950",
  }[insight.tone] || "border-slate-200 bg-white text-slate-900";
  const iconTone = {
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-700",
    blue: "border-blue-200 bg-blue-50 text-blue-700",
    violet: "border-violet-200 bg-violet-50 text-violet-700",
  }[insight.tone] || "border-slate-200 bg-slate-50 text-slate-700";

  return (
    <article className={`rounded-[28px] border p-5 shadow-[0_18px_50px_rgba(15,23,42,0.06)] ${tone}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className={`rounded-2xl border p-3 ${iconTone}`}>
            <Icon size={22} />
          </div>
          <div>
            <p className="text-xs font-black uppercase tracking-[0.24em] text-emerald-700">{insight.eyebrow}</p>
            <h3 className="mt-1 text-xl font-black text-[var(--text-main)]">{insight.title}</h3>
          </div>
        </div>
        {insight.badge ? <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-800">{insight.badge}</span> : null}
      </div>

      <p className="mt-4 text-sm leading-6 text-slate-600">{insight.description}</p>

      {insight.facts?.length ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {insight.facts.map(([label, value]) => <Metric key={label} label={label} value={value} />)}
        </div>
      ) : null}

      {insight.warning ? <p className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold leading-6 text-amber-900"><strong>Por qué importa:</strong> {insight.warning}</p> : null}
      {insight.success ? <p className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold leading-6 text-emerald-950">{insight.success}</p> : null}
      {insight.action ? <p className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold leading-6 text-emerald-950"><strong>Acción recomendada:</strong> {insight.action}</p> : null}
      {insight.bullets?.length ? (
        <ul className="mt-4 space-y-3">
          {insight.bullets.map((item) => (
            <li key={item} className="flex gap-2 rounded-2xl bg-emerald-50/70 px-3 py-3 text-sm font-semibold leading-6 text-slate-700">
              <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-700" size={16} />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {insight.kpi ? <p className="mt-4 text-xs font-black uppercase tracking-wide text-slate-500">KPI de seguimiento: {insight.kpi}</p> : null}
    </article>
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
  const [activeTab, setActiveTab] = useState("vision");
  const [data, setData] = useState(null);
  const [operationalData, setOperationalData] = useState({ kpis: null, recommendations: null, scenarios: null, decisions: null });
  const [createdDecisionActionIds, setCreatedDecisionActionIds] = useState([]);
  const [actionModalDraft, setActionModalDraft] = useState(null);
  const [actionModalLoading, setActionModalLoading] = useState(false);
  const [actionSaving, setActionSaving] = useState(false);
  const [actionFeedback, setActionFeedback] = useState("");
  const [actionError, setActionError] = useState("");
  const [workingPriorityId, setWorkingPriorityId] = useState("");
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
        setActionFeedback("");
        const [intelligenceResult, kpiResult, recommendationResult, scenarioResult, decisionResult] = await Promise.allSettled([
          getIntelligenceRecommendations({ constructora_id: activeConstructoraId, iot_hours: 24, scope }),
          getEnvironmentalKpis(activeConstructoraId),
          getEnvironmentalRecommendations(activeConstructoraId),
          getEnvironmentalScenarios(activeConstructoraId),
          getEnvironmentalDecisionPriorities(activeConstructoraId),
        ]);
        if (cancelled) return;
        if (intelligenceResult.status === "fulfilled") setData(intelligenceResult.value);
        else setData(null);
        const decisions = decisionResult.status === "fulfilled" ? decisionResult.value : null;
        setOperationalData({
          kpis: kpiResult.status === "fulfilled" ? kpiResult.value : null,
          recommendations: recommendationResult.status === "fulfilled" ? recommendationResult.value : null,
          scenarios: scenarioResult.status === "fulfilled" ? scenarioResult.value : null,
          decisions,
        });
        setCreatedDecisionActionIds((decisions?.priorities || []).filter((priority) => priority.action_created).map((priority) => priority.id));
        if (intelligenceResult.status === "rejected" && kpiResult.status === "rejected" && decisionResult.status === "rejected") {
          setError("No se pudo cargar la inteligencia ambiental.");
        }
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

  async function openDecisionActionModal(priority) {
    if (!activeConstructoraId || !priority?.id) return;
    setWorkingPriorityId(priority.id);
    setActionModalLoading(true);
    setActionError("");
    setActionFeedback("");
    setActionModalDraft({
      priorityId: priority.id,
      sourcePriority: priority,
      payload: {},
      responsible: "Equipo ambiental",
      dueDate: "",
      requiredEvidence: "",
      notes: "",
    });
    try {
      const preview = await getDecisionActionPreview(activeConstructoraId, priority.id);
      const payload = preview.payload || {};
      setActionModalDraft({
        priorityId: priority.id,
        sourcePriority: preview.source_priority || priority,
        payload,
        responsible: payload.responsible || "Equipo ambiental",
        dueDate: payload.due_date || payload.dueDate || "",
        requiredEvidence: payload.evidence || "",
        notes: "",
      });
    } catch (requestError) {
      setActionError(requestError.response?.data?.error || "No se pudo preparar la acción ambiental.");
    } finally {
      setActionModalLoading(false);
      setWorkingPriorityId("");
    }
  }

  async function confirmDecisionAction(event) {
    event.preventDefault();
    if (!activeConstructoraId || !actionModalDraft?.priorityId) return;
    setActionSaving(true);
    setActionError("");
    try {
      const result = await createActionFromDecision(activeConstructoraId, actionModalDraft.priorityId, {
        responsible: actionModalDraft.responsible,
        due_date: actionModalDraft.dueDate,
        required_evidence: actionModalDraft.requiredEvidence,
        notes: actionModalDraft.notes,
      });
      setCreatedDecisionActionIds((current) => Array.from(new Set([...current, actionModalDraft.priorityId])));
      setActionFeedback(result.duplicate ? result.message || "Ya existe una acción abierta asociada a esta decisión." : "Acción ambiental creada y enviada a seguimiento.");
      setActionModalDraft(null);
      window.setTimeout(() => setActionFeedback(""), 3200);
    } catch (requestError) {
      setActionError(requestError.response?.data?.error || "No se pudo crear la acción ambiental.");
    } finally {
      setActionSaving(false);
    }
  }

  const context = data?.context || {};
  const cards = useMemo(() => ensureThreeCards(normalizeCards(data), context, scope), [data, context, scope]);
  const actions = data?.actions || data?.structured?.actions || [];
  const priorities = operationalData.decisions?.priorities || [];
  const scenarios = operationalData.scenarios?.scenarios || [];
  const recommendations = operationalData.recommendations?.recommendations || [];
  const operationalInsights = useMemo(
    () => buildOperationalInsights({ cards, context, kpis: operationalData.kpis, priorities, scenarios }),
    [cards, context, operationalData.kpis, priorities, scenarios]
  );

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
                Inteligencia de reducción para {activeConstructora?.nombre || "la empresa"}
              </h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">
                Aquí vive el motor de decisión: foco crítico, etapa prioritaria, escenarios, recomendaciones y acciones trazables.
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
          <Metric label="Foco principal" value={operationalInsights[0]?.badge || context.categoria_critica || "Sin datos"} />
          <Metric label="Etapa prioritaria" value={operationalInsights[1]?.badge || context.etapa_critica || "Sin etapa"} />
        </div>
      </div>

      <div className="flex flex-wrap gap-2 rounded-[28px] border border-[var(--border)] bg-white/80 p-2 shadow-sm">
        {intelligenceTabs.map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => setActiveTab(tab.value)}
            className={`rounded-2xl px-4 py-2 text-sm font-black transition ${activeTab === tab.value ? "bg-[var(--primary)] text-white shadow-[0_12px_24px_rgba(15,124,109,0.20)]" : "text-slate-600 hover:bg-emerald-50 hover:text-emerald-800"}`}
          >
            {tab.label}
          </button>
        ))}
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

      {actionFeedback ? <p className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-black text-emerald-800">{actionFeedback}</p> : null}

      {!loading && !error && activeTab === "vision" && (
        <>
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
            {operationalInsights.map((insight) => <OperationalInsightCard key={insight.title} insight={insight} />)}
          </div>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            {cards.map((card) => <RecommendationCard key={card.id} card={card} />)}
          </div>
          <ActionPlan actions={actions} />
        </>
      )}

      {!loading && !error && activeTab === "decisiones" && (
        <EnvironmentalDecisionPriorityList
          createdActionIds={createdDecisionActionIds}
          onConvertToAction={openDecisionActionModal}
          priorities={priorities}
          workingPriorityId={workingPriorityId}
        />
      )}

      {!loading && !error && activeTab === "escenarios" && <EnvironmentalScenarioList scenarios={scenarios} />}
      {!loading && !error && activeTab === "recomendaciones" && <EnvironmentalRecommendationList recommendations={recommendations} />}
      {!loading && !error && activeTab === "acciones" && <TraceableActionsPanel cards={cards} constructoraId={activeConstructoraId} />}

      {actionModalDraft ? (
        <DecisionToActionModal
          draft={actionModalDraft}
          error={actionError}
          loading={actionModalLoading}
          onClose={() => setActionModalDraft(null)}
          onConfirm={confirmDecisionAction}
          saving={actionSaving}
          setDraft={setActionModalDraft}
        />
      ) : null}
    </section>
  );
}

export default IntelligencePanel;
