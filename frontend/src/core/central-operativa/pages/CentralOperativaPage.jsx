import { useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, ArrowRight, BarChart3, CheckCircle2, ChevronDown, DatabaseZap, FileClock, ShieldCheck, Sparkles, Target } from "lucide-react";

import { useEnvironmentalContext } from "@/domain/environmental";
import CriticalDocumentsPanel from "@/core/environmental/components/CriticalDocumentsPanel";
import DecisionToActionModal from "@/core/environmental/components/DecisionToActionModal";
import EnvironmentalContextCard from "@/core/environmental/components/EnvironmentalContextCard";
import EnvironmentalDecisionPriorityList from "@/core/environmental/components/EnvironmentalDecisionPriorityList";
import EnvironmentalItemGrid from "@/core/environmental/components/EnvironmentalItemGrid";
import EnvironmentalKpiGrid from "@/core/environmental/components/EnvironmentalKpiGrid";
import EnvironmentalRecommendationList from "@/core/environmental/components/EnvironmentalRecommendationList";
import EnvironmentalScenarioList from "@/core/environmental/components/EnvironmentalScenarioList";
import EnvironmentalShell from "@/core/environmental/components/EnvironmentalShell";
import RecommendedActionsPanel from "@/core/environmental/components/RecommendedActionsPanel";
import RegulatoryReadinessPanel from "@/core/environmental/components/RegulatoryReadinessPanel";
import RiskSignalsPanel from "@/core/environmental/components/RiskSignalsPanel";
import { getEnvironmentalComplianceSummary } from "@/features/environmental/services/environmentalComplianceApi";
import { createActionFromDecision, getDecisionActionPreview } from "@/features/environmental/services/environmentalDecisionActionApi";
import { getEnvironmentalDecisionPriorities } from "@/features/environmental/services/environmentalDecisionPriorityApi";
import { getEnvironmentalKpis } from "@/features/environmental/services/environmentalKpiApi";
import { getEnvironmentalRecommendations } from "@/features/environmental/services/environmentalRecommendationApi";
import { getEnvironmentalScenarios } from "@/features/environmental/services/environmentalScenarioApi";

function CentralOperativaPage() {
  const { activeCompany, matrix } = useEnvironmentalContext();
  const [summary, setSummary] = useState(null);
  const [kpis, setKpis] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [scenarios, setScenarios] = useState(null);
  const [decisionPriorities, setDecisionPriorities] = useState(null);
  const [createdDecisionActionIds, setCreatedDecisionActionIds] = useState([]);
  const [actionModalDraft, setActionModalDraft] = useState(null);
  const [actionModalLoading, setActionModalLoading] = useState(false);
  const [actionSaving, setActionSaving] = useState(false);
  const [actionFeedback, setActionFeedback] = useState("");
  const [actionError, setActionError] = useState("");
  const [workingPriorityId, setWorkingPriorityId] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!activeCompany?.constructora_id) return;
    let cancelled = false;
    setLoading(true);
    setCreatedDecisionActionIds([]);
    setActionFeedback("");
    setActionError("");
    Promise.all([
      getEnvironmentalKpis(activeCompany.constructora_id),
      getEnvironmentalComplianceSummary(activeCompany.constructora_id),
      getEnvironmentalRecommendations(activeCompany.constructora_id),
      getEnvironmentalScenarios(activeCompany.constructora_id),
      getEnvironmentalDecisionPriorities(activeCompany.constructora_id),
    ])
      .then(([kpiData, summaryData, recommendationData, scenarioData, decisionPriorityData]) => {
        if (!cancelled) {
          setKpis(kpiData);
          setSummary(summaryData);
          setRecommendations(recommendationData);
          setScenarios(scenarioData);
          setDecisionPriorities(decisionPriorityData);
          setCreatedDecisionActionIds(
            (decisionPriorityData?.priorities || [])
              .filter((priority) => priority.action_created)
              .map((priority) => priority.id),
          );
        }
      })
      .catch(() => {
        if (!cancelled) {
          setKpis(null);
          setSummary(null);
          setRecommendations(null);
          setScenarios(null);
          setDecisionPriorities(null);
          setCreatedDecisionActionIds([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeCompany?.constructora_id]);

  async function openDecisionActionModal(priority) {
    if (!activeCompany?.constructora_id || !priority?.id) return;
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
      const preview = await getDecisionActionPreview(activeCompany.constructora_id, priority.id);
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
      setActionError(requestError.response?.data?.error || "No se pudo preparar la accion ambiental.");
    } finally {
      setActionModalLoading(false);
      setWorkingPriorityId("");
    }
  }

  async function confirmDecisionAction(event) {
    event.preventDefault();
    if (!activeCompany?.constructora_id || !actionModalDraft?.priorityId) return;
    setActionSaving(true);
    setActionError("");
    try {
      const result = await createActionFromDecision(activeCompany.constructora_id, actionModalDraft.priorityId, {
        responsible: actionModalDraft.responsible,
        due_date: actionModalDraft.dueDate,
        required_evidence: actionModalDraft.requiredEvidence,
        notes: actionModalDraft.notes,
      });
      setCreatedDecisionActionIds((current) => Array.from(new Set([...current, actionModalDraft.priorityId])));
      setActionFeedback(result.duplicate ? result.message || "Ya existe una accion abierta asociada a esta decision." : "Accion ambiental creada y enviada a seguimiento.");
      setActionModalDraft(null);
      window.setTimeout(() => setActionFeedback(""), 3200);
    } catch (requestError) {
      setActionError(requestError.response?.data?.error || "No se pudo crear la accion ambiental.");
    } finally {
      setActionSaving(false);
    }
  }

  const priorities = useMemo(() => decisionPriorities?.priorities || [], [decisionPriorities?.priorities]);
  const weeklyPriority = useMemo(() => pickWeeklyPriority(priorities), [priorities]);
  const bestScenario = useMemo(() => pickBestScenario(scenarios?.scenarios || []), [scenarios?.scenarios]);
  const topKpis = useMemo(() => pickTopKpis(kpis?.cards || []), [kpis?.cards]);
  const topSource = kpis?.top_sources?.[0];
  const topCategory = kpis?.top_categories?.[0];
  const mainRisk = getMainRisk(summary, kpis);
  const createdSet = useMemo(() => new Set(createdDecisionActionIds), [createdDecisionActionIds]);
  const weeklyPriorityHasAction = weeklyPriority ? createdSet.has(weeklyPriority.id) || weeklyPriority.action_created : false;

  return (
    <EnvironmentalShell
      eyebrow="Modulo critico"
      title="Central Operativa"
      description="Resumen de cumplimiento ambiental para decidir que datos completar, que riesgos controlar y que acciones ejecutar."
    >
      <EnvironmentalContextCard company={activeCompany} matrix={matrix} />

      <OperationalHero
        company={activeCompany}
        kpis={kpis}
        loading={loading}
        mainRisk={mainRisk}
        onConvertToAction={weeklyPriority ? () => openDecisionActionModal(weeklyPriority) : undefined}
        priority={weeklyPriority}
        priorityHasAction={weeklyPriorityHasAction}
        topCategory={topCategory}
        topSource={topSource}
        working={weeklyPriority ? workingPriorityId === weeklyPriority.id : false}
      />

      {actionFeedback ? (
        <p className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-black text-emerald-800">{actionFeedback}</p>
      ) : null}

      <KpiStrip kpis={topKpis} summary={summary} topSource={topSource} />

      <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <WeeklyPriorityCard
          created={weeklyPriorityHasAction}
          onConvertToAction={weeklyPriority ? () => openDecisionActionModal(weeklyPriority) : undefined}
          priority={weeklyPriority}
          working={weeklyPriority ? workingPriorityId === weeklyPriority.id : false}
        />
        <ExpectedImpactCard scenario={bestScenario} />
      </section>

      {weeklyPriorityHasAction ? (
        <ActionFollowUpCard priority={weeklyPriority} />
      ) : null}

      <section className="grid gap-4 md:grid-cols-4">
        <SummaryCard icon={ShieldCheck} label="Cumplimiento" value={formatSummaryValue(summary?.compliance_pct, "%")} detail={loading ? "Cargando" : "Variables dentro de limite"} tone="emerald" />
        <SummaryCard icon={AlertTriangle} label="Alertas rojas" value={formatSummaryValue(summary?.alertas_rojas)} detail="Incumplimientos abiertos" tone="red" />
        <SummaryCard icon={AlertTriangle} label="Alertas amarillas" value={formatSummaryValue(summary?.alertas_amarillas)} detail="Variables cerca del limite" tone="amber" />
        <SummaryCard icon={FileClock} label="Docs pendientes" value={formatSummaryValue(summary?.documentos_pendientes)} detail="Validacion documental" tone="blue" />
      </section>

      <TechnicalSection title="KPIs completos" subtitle="Indicadores secundarios disponibles para auditoria tecnica.">
        <EnvironmentalKpiGrid kpis={kpis?.cards || []} />
      </TechnicalSection>

      <TechnicalSection title="Todas las decisiones" subtitle="Ranking completo para revisar alternativas y brechas.">
        <EnvironmentalDecisionPriorityList
          createdActionIds={createdDecisionActionIds}
          onConvertToAction={openDecisionActionModal}
          priorities={priorities}
          workingPriorityId={workingPriorityId}
        />
      </TechnicalSection>

      <TechnicalSection title="Escenarios de impacto" subtitle="Simulaciones disponibles sin modificar registros ni crear acciones automaticas.">
        <EnvironmentalScenarioList scenarios={scenarios?.scenarios || []} />
      </TechnicalSection>

      <TechnicalSection title="Recomendaciones tecnicas" subtitle="Diagnostico de soporte para equipos ambientales y operaciones.">
        <EnvironmentalRecommendationList recommendations={recommendations?.recommendations || []} />
      </TechnicalSection>

      {(!!kpis?.data_gaps?.length || !!kpis?.next_actions?.length || !!summary?.critical_alerts?.length) && (
        <TechnicalSection title="Brechas y alertas" subtitle="Datos faltantes, acciones sugeridas y riesgos recientes.">
          <div className="grid gap-4 xl:grid-cols-3">
            {!!kpis?.data_gaps?.length && (
              <PanelBlock title="Datos que faltan" items={kpis.data_gaps} tone="blue" />
            )}
            {!!kpis?.next_actions?.length && (
              <PanelBlock title="Siguientes acciones" items={kpis.next_actions} tone="emerald" />
            )}
            {!!summary?.critical_alerts?.length && (
              <div className="rounded-2xl border border-rose-100 bg-rose-50/70 p-4">
                <h3 className="text-sm font-black text-rose-900">Alertas criticas recientes</h3>
                <div className="mt-3 space-y-3">
                  {summary.critical_alerts.slice(0, 3).map((alert) => (
                    <div key={alert.id} className="rounded-xl border border-rose-100 bg-white/80 p-3">
                      <p className="text-sm font-black text-rose-950">{alert.titulo}</p>
                      <p className="mt-1 line-clamp-2 text-xs leading-5 text-rose-800">{alert.descripcion}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </TechnicalSection>
      )}

      <TechnicalSection title="Matriz del preset" subtitle="Variables, documentos, senales de riesgo y preparacion regulatoria del rubro.">
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-6">
            <EnvironmentalItemGrid
              icon={Activity}
              tone="emerald"
              title="Variables criticas"
              description="Datos operativos requeridos para calculo ambiental, indicadores y trazabilidad."
              items={matrix.criticalVariables}
            />
            <CriticalDocumentsPanel matrix={matrix} />
          </div>

          <div className="space-y-6">
            <RiskSignalsPanel matrix={matrix} />
            <RecommendedActionsPanel matrix={matrix} />
          </div>
        </div>
        <div className="mt-6">
          <RegulatoryReadinessPanel matrix={matrix} />
        </div>
      </TechnicalSection>

      <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
        <div className="flex items-start gap-3">
          <span className="rounded-xl border border-blue-200 bg-blue-50 p-2 text-blue-800">
            <DatabaseZap size={18} />
          </span>
          <div>
            <h2 className="text-lg font-black text-[var(--text-main)]">Trazabilidad prioritaria</h2>
            <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
              Cada registro debe quedar conectado con documento, variable calculable, riesgo controlado y accion de cierre.
            </p>
          </div>
        </div>
      </section>

      {actionModalDraft ? (
        <DecisionToActionModal
          draft={actionModalDraft}
          error={actionError}
          loading={actionModalLoading}
          onClose={() => {
            setActionModalDraft(null);
            setActionError("");
          }}
          onConfirm={confirmDecisionAction}
          saving={actionSaving}
          setDraft={setActionModalDraft}
        />
      ) : null}
    </EnvironmentalShell>
  );
}

function OperationalHero({ company, kpis, loading, mainRisk, onConvertToAction, priority, priorityHasAction, topCategory, topSource, working }) {
  const tone = heroTone(priority, mainRisk);
  const footprint = kpis?.summary?.huella_total_tco2e;
  const focus = topSource || topCategory;

  return (
    <section className={`overflow-hidden rounded-[28px] border p-6 shadow-[0_24px_70px_rgba(15,23,42,0.10)] ${tone.shell}`}>
      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <div>
          <p className={`text-xs font-black uppercase tracking-[0.22em] ${tone.eyebrow}`}>Que esta pasando</p>
          <h1 className="mt-3 max-w-3xl text-3xl font-black leading-tight text-slate-950 sm:text-4xl">
            {priority ? statusHeadline(priority) : loading ? "Calculando estado ambiental de la operacion" : "Sin prioridad ambiental suficiente todavia"}
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-700">
            {company?.nombre || "La empresa"} concentra la decision de esta semana en {priority?.area || "completar datos ambientales"}. {focus ? `${focus.label} concentra ${formatMaybePct(focus.share_pct)} de la huella medida.` : "Aun falta evidencia para identificar un foco critico robusto."}
          </p>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <HeroMetric label="Huella total" value={formatNumber(footprint, "tCO2e")} />
            <HeroMetric label="Foco critico" value={focus?.label || "Requiere datos"} />
            <HeroMetric label="Riesgo principal" value={mainRisk} />
          </div>
        </div>

        <div className="rounded-3xl border border-white/70 bg-white/75 p-5 shadow-[0_18px_45px_rgba(15,23,42,0.08)]">
          <p className={`text-xs font-black uppercase tracking-[0.18em] ${tone.eyebrow}`}>Que hacer ahora</p>
          <h2 className="mt-2 text-2xl font-black text-slate-950">{priority?.title || "Completar evidencia base"}</h2>
          <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-700">{priority?.next_step || "Carga registros, documentos o variables para activar recomendaciones y escenarios confiables."}</p>
          <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-black uppercase tracking-wide text-slate-500">Impacto esperado</p>
            <p className="mt-1 text-sm font-black text-slate-900">{formatPriorityImpact(priority)}</p>
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <DecisionHeroAction created={priorityHasAction} onConvertToAction={onConvertToAction} priority={priority} working={working} />
            <a href="#detalle-tecnico" className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-black text-slate-700 hover:bg-slate-50">
              Ver detalle tecnico <ArrowRight size={16} />
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

function KpiStrip({ kpis = [], summary, topSource }) {
  const cards = [
    ...kpis.map((kpi) => ({
      id: kpi.id,
      label: kpi.label,
      value: kpi.value === null || kpi.value === undefined ? "Requiere datos" : `${formatValue(kpi.value)} ${kpi.unit || ""}`.trim(),
      detail: kpi.reason,
      tone: kpi.status === "missing" ? "amber" : "emerald",
    })),
    {
      id: "foco-critico",
      label: "Foco/material critico",
      value: topSource?.label || "Requiere datos",
      detail: topSource ? `${formatMaybePct(topSource.share_pct)} de la huella medida.` : "Sin fuente dominante calculada.",
      tone: "violet",
    },
    {
      id: "alertas",
      label: "Alertas y documentos",
      value: `${formatSummaryValue(summary?.alertas_rojas)} / ${formatSummaryValue(summary?.documentos_pendientes)}`,
      detail: "Alertas rojas / documentos pendientes.",
      tone: (summary?.alertas_rojas || 0) > 0 ? "rose" : "cyan",
    },
  ].slice(0, 4);

  return (
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => <CompactKpi key={card.id} card={card} />)}
    </section>
  );
}

function WeeklyPriorityCard({ created, onConvertToAction, priority, working }) {
  if (!priority) {
    return (
      <section className="rounded-[28px] border border-amber-200 bg-amber-50 p-6">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-amber-700">Prioridad de esta semana</p>
        <h2 className="mt-2 text-2xl font-black text-amber-950">Completar datos antes de decidir</h2>
        <p className="mt-2 text-sm leading-6 text-amber-900">No hay una decision ambiental priorizada con evidencia suficiente.</p>
      </section>
    );
  }

  return (
    <section className="rounded-[28px] border border-violet-200 bg-violet-50/80 p-6 shadow-[0_18px_45px_rgba(76,29,149,0.08)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-violet-700">Prioridad de esta semana</p>
          <h2 className="mt-2 text-2xl font-black text-violet-950">{priority.title}</h2>
        </div>
        <span className="rounded-full border border-violet-200 bg-white px-3 py-1 text-xs font-black uppercase text-violet-800">score {formatValue(priority.score)}</span>
      </div>
      <p className="mt-3 line-clamp-3 text-sm leading-6 text-violet-900">{priority.why_now}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <MiniFact label="Impacto" value={formatPriorityImpact(priority)} />
        <MiniFact label="Confianza" value={priority.confidence || "sin dato"} />
        <MiniFact label="Esfuerzo" value={priority.effort || "sin dato"} />
      </div>
      <div className="mt-5 rounded-2xl border border-violet-200 bg-white/75 p-4">
        <p className="text-xs font-black uppercase tracking-wide text-violet-700">Siguiente paso</p>
        <p className="mt-1 text-sm font-bold leading-6 text-violet-950">{priority.next_step}</p>
      </div>
      <div className="mt-5">
        <DecisionHeroAction created={created} onConvertToAction={onConvertToAction} priority={priority} working={working} />
      </div>
    </section>
  );
}

function ExpectedImpactCard({ scenario }) {
  return (
    <section className="rounded-[28px] border border-cyan-200 bg-cyan-50/80 p-6 shadow-[0_18px_45px_rgba(8,145,178,0.08)]">
      <p className="text-xs font-black uppercase tracking-[0.18em] text-cyan-700">Impacto esperado</p>
      <h2 className="mt-2 text-2xl font-black text-cyan-950">{scenario?.title || "Escenario pendiente de datos"}</h2>
      <p className="mt-2 line-clamp-3 text-sm leading-6 text-cyan-900">{scenario?.decision_hint || scenario?.reason || "Carga datos base para habilitar simulaciones de reduccion."}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <MiniFact label="kgCO2e" value={formatNumber(scenario?.estimated_reduction_kg_co2e, "kg")} />
        <MiniFact label="tCO2e" value={formatNumber(scenario?.estimated_reduction_tco2e, "t")} />
        <MiniFact label="Reduccion" value={formatNumber(scenario?.estimated_reduction_pct, "%")} />
      </div>
      <span className="mt-5 inline-flex rounded-full border border-cyan-200 bg-white px-3 py-1 text-xs font-black uppercase text-cyan-800">
        {scenario?.status || "requiere datos"}
      </span>
    </section>
  );
}

function ActionFollowUpCard({ priority }) {
  return (
    <section className="rounded-[24px] border border-emerald-200 bg-emerald-50/80 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Accion en seguimiento</p>
          <h2 className="mt-1 text-xl font-black text-emerald-950">{priority?.title || "Decision convertida en accion"}</h2>
          <p className="mt-1 text-sm text-emerald-900">Accion creada y enviada al modulo Acciones para seguimiento, evidencia y cierre ambiental.</p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-sm font-black text-emerald-800">
          <CheckCircle2 size={17} /> En seguimiento
        </span>
      </div>
    </section>
  );
}

function TechnicalSection({ children, subtitle, title }) {
  return (
    <details id={title === "KPIs completos" ? "detalle-tecnico" : undefined} className="group rounded-[24px] border border-slate-200 bg-slate-50/80 p-4 shadow-[0_12px_30px_rgba(15,23,42,0.04)]">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-black text-slate-950">{title}</h2>
          <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
        </div>
        <span className="rounded-2xl border border-slate-200 bg-white p-2 text-slate-600 transition group-open:rotate-180">
          <ChevronDown size={18} />
        </span>
      </summary>
      <div className="mt-5">{children}</div>
    </details>
  );
}

function PanelBlock({ items = [], title, tone }) {
  const toneClass = {
    blue: "border-blue-100 bg-blue-50/70 text-blue-900",
    emerald: "border-emerald-100 bg-emerald-50/70 text-emerald-900",
  }[tone];

  return (
    <div className={`rounded-2xl border p-4 ${toneClass}`}>
      <h3 className="text-sm font-black">{title}</h3>
      <div className="mt-3 space-y-2">
        {items.slice(0, 4).map((item) => (
          <p key={item} className="rounded-xl border border-white/70 bg-white/70 p-3 text-sm font-bold">
            {item}
          </p>
        ))}
      </div>
    </div>
  );
}

function DecisionHeroAction({ created, onConvertToAction, priority, working }) {
  if (created) {
    return (
      <span className="inline-flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-black text-emerald-800">
        <CheckCircle2 size={17} /> Accion creada
      </span>
    );
  }
  if (!priority) return null;
  if (priority.status === "requires_data") return <span className="text-sm font-black text-amber-800">Requiere evidencia antes de accionar</span>;
  if (priority.status === "monitor") return <span className="text-sm font-black text-slate-700">Monitorear antes de accionar</span>;
  return (
    <button type="button" onClick={onConvertToAction} disabled={working} className="inline-flex items-center gap-2 rounded-2xl bg-[var(--primary)] px-4 py-3 text-sm font-black text-white shadow-[0_14px_30px_rgba(15,124,109,0.18)] hover:bg-[var(--primary-dark)] disabled:opacity-60">
      {working ? <Sparkles size={17} /> : <Target size={17} />}
      {working ? "Preparando..." : "Convertir decision en accion"}
    </button>
  );
}

function CompactKpi({ card }) {
  const tone = {
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-900",
    amber: "border-amber-200 bg-amber-50 text-amber-900",
    violet: "border-violet-200 bg-violet-50 text-violet-900",
    rose: "border-rose-200 bg-rose-50 text-rose-900",
    cyan: "border-cyan-200 bg-cyan-50 text-cyan-900",
  }[card.tone] || "border-slate-200 bg-slate-50 text-slate-900";

  return (
    <article className={`rounded-2xl border p-4 ${tone}`}>
      <div className="flex items-center gap-2">
        <BarChart3 size={17} />
        <p className="text-xs font-black uppercase tracking-wide opacity-75">{card.label}</p>
      </div>
      <p className="mt-3 truncate text-2xl font-black">{card.value}</p>
      <p className="mt-1 line-clamp-2 text-xs font-semibold opacity-80">{card.detail}</p>
    </article>
  );
}

function HeroMetric({ label, value }) {
  return (
    <div className="rounded-2xl border border-white/70 bg-white/70 p-4">
      <p className="text-xs font-black uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 line-clamp-2 text-lg font-black text-slate-950">{value}</p>
    </div>
  );
}

function MiniFact({ label, value }) {
  return (
    <div className="rounded-2xl border border-white/70 bg-white/70 p-3">
      <p className="text-xs font-black uppercase tracking-wide opacity-70">{label}</p>
      <p className="mt-1 line-clamp-2 text-sm font-black">{value}</p>
    </div>
  );
}

function formatSummaryValue(value, suffix = "") {
  if (value === null || value === undefined) return "Requiere datos";
  const number = Number(value);
  if (!Number.isFinite(number)) return value;
  return `${new Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 }).format(number)}${suffix}`;
}

function SummaryCard({ icon: Icon, label, value, detail, tone }) {
  const toneClass = {
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-800",
    red: "border-red-200 bg-red-50 text-red-800",
    amber: "border-amber-200 bg-amber-50 text-amber-800",
    blue: "border-blue-200 bg-blue-50 text-blue-800",
  }[tone];

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
      <div className={`inline-flex rounded-xl border p-2 ${toneClass}`}>
        <Icon size={18} />
      </div>
      <p className="mt-4 text-sm font-bold text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 text-3xl font-black text-[var(--text-main)]">{value}</p>
      <p className="mt-1 text-xs font-semibold text-[var(--text-muted)]">{detail}</p>
    </div>
  );
}

function pickWeeklyPriority(priorities = []) {
  return priorities.find((priority) => priority.status === "ready" && !priority.action_created) || priorities[0] || null;
}

function pickBestScenario(scenarios = []) {
  return (
    scenarios
      .filter((scenario) => scenario.status === "available" && scenario.estimated_reduction_kg_co2e !== null && scenario.estimated_reduction_kg_co2e !== undefined)
      .sort((a, b) => Number(b.estimated_reduction_kg_co2e || 0) - Number(a.estimated_reduction_kg_co2e || 0))[0]
    || scenarios.find((scenario) => scenario.status === "partial")
    || scenarios[0]
    || null
  );
}

function pickTopKpis(cards = []) {
  const preferred = ["huella_total_obra", "huella_total_planta", "huella_total_flota", "huella_total_faena", "huella_m2", "huella_m3_madera", "emisiones_por_km", "alertas_ruido", "documentos_pendientes", "docs_faltantes"];
  const byId = new Map(cards.map((card) => [card.id, card]));
  const picked = preferred.map((id) => byId.get(id)).filter(Boolean);
  const fallback = cards.filter((card) => !picked.some((item) => item.id === card.id));
  return [...picked, ...fallback].slice(0, 2);
}

function getMainRisk(summary, kpis) {
  if ((summary?.alertas_rojas || 0) > 0) return "Alertas rojas abiertas";
  if ((summary?.documentos_pendientes || 0) > 0) return "Documentacion pendiente";
  if (kpis?.data_gaps?.length) return "Datos clave incompletos";
  return "Sin riesgo critico visible";
}

function heroTone(priority, mainRisk) {
  if (priority?.priority === "critica" || mainRisk === "Alertas rojas abiertas") {
    return {
      shell: "border-rose-200 bg-[linear-gradient(135deg,rgba(255,241,242,0.98),rgba(255,255,255,0.95))]",
      eyebrow: "text-rose-700",
    };
  }
  if (priority?.status === "requires_data" || mainRisk !== "Sin riesgo critico visible") {
    return {
      shell: "border-amber-200 bg-[linear-gradient(135deg,rgba(255,251,235,0.98),rgba(255,255,255,0.95))]",
      eyebrow: "text-amber-700",
    };
  }
  return {
    shell: "border-emerald-200 bg-[linear-gradient(135deg,rgba(236,253,245,0.98),rgba(240,253,250,0.92))]",
    eyebrow: "text-emerald-700",
  };
}

function statusHeadline(priority) {
  if (priority.priority === "critica") return "Prioridad ambiental critica para resolver ahora";
  if (priority.priority === "alta") return "Prioridad ambiental alta para esta semana";
  if (priority.status === "requires_data") return "Decision importante bloqueada por datos faltantes";
  return "Operacion ambiental en seguimiento activo";
}

function formatPriorityImpact(priority) {
  const impact = priority?.expected_impact || {};
  const parts = [
    impact.kg_co2e !== null && impact.kg_co2e !== undefined ? formatNumber(impact.kg_co2e, "kgCO2e") : "",
    impact.tco2e !== null && impact.tco2e !== undefined ? formatNumber(impact.tco2e, "tCO2e") : "",
    impact.pct !== null && impact.pct !== undefined ? formatNumber(impact.pct, "%") : "",
    impact.risk_reduction ? `riesgo ${impact.risk_reduction}` : "",
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "Requiere datos";
}

function formatMaybePct(value) {
  if (value === null || value === undefined) return "participacion no calculada";
  return `${formatValue(value)}%`;
}

function formatNumber(value, unit) {
  if (value === null || value === undefined) return "Requiere datos";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  return `${formatValue(number)} ${unit}`;
}

function formatValue(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value || "Requiere datos");
  return new Intl.NumberFormat("es-CL", { maximumFractionDigits: 2 }).format(number);
}

export default CentralOperativaPage;
