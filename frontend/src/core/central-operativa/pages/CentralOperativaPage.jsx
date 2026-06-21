import { useEffect, useState } from "react";
import { Activity, AlertTriangle, DatabaseZap, FileClock, ShieldCheck } from "lucide-react";

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

  return (
    <EnvironmentalShell
      eyebrow="Modulo critico"
      title="Central Operativa"
      description="Resumen de cumplimiento ambiental para decidir que datos completar, que riesgos controlar y que acciones ejecutar."
    >
      <EnvironmentalContextCard company={activeCompany} matrix={matrix} />

      <EnvironmentalKpiGrid kpis={kpis?.cards || []} />

      <EnvironmentalRecommendationList recommendations={recommendations?.recommendations || []} />

      <EnvironmentalScenarioList scenarios={scenarios?.scenarios || []} />

      {actionFeedback ? (
        <p className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-black text-emerald-800">{actionFeedback}</p>
      ) : null}

      <EnvironmentalDecisionPriorityList
        createdActionIds={createdDecisionActionIds}
        onConvertToAction={openDecisionActionModal}
        priorities={decisionPriorities?.priorities || []}
        workingPriorityId={workingPriorityId}
      />

      <section className="grid gap-4 md:grid-cols-4">
        <SummaryCard icon={ShieldCheck} label="Cumplimiento" value={formatSummaryValue(summary?.compliance_pct, "%")} detail={loading ? "Cargando" : "Variables dentro de limite"} tone="emerald" />
        <SummaryCard icon={AlertTriangle} label="Alertas rojas" value={formatSummaryValue(summary?.alertas_rojas)} detail="Incumplimientos abiertos" tone="red" />
        <SummaryCard icon={AlertTriangle} label="Alertas amarillas" value={formatSummaryValue(summary?.alertas_amarillas)} detail="Variables cerca del limite" tone="amber" />
        <SummaryCard icon={FileClock} label="Docs pendientes" value={formatSummaryValue(summary?.documentos_pendientes)} detail="Validacion documental" tone="blue" />
      </section>

      {!!kpis?.data_gaps?.length && (
        <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
          <h2 className="text-lg font-black text-[var(--text-main)]">Brechas de datos</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {kpis.data_gaps.map((gap) => (
              <p key={gap} className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm font-bold text-slate-700">
                {gap}
              </p>
            ))}
          </div>
        </section>
      )}

      {!!kpis?.next_actions?.length && (
        <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
          <h2 className="text-lg font-black text-[var(--text-main)]">Siguientes acciones</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {kpis.next_actions.map((action) => (
              <p key={action} className="rounded-xl border border-emerald-100 bg-emerald-50/70 p-4 text-sm font-bold text-emerald-800">
                {action}
              </p>
            ))}
          </div>
        </section>
      )}

      {!!summary?.critical_alerts?.length && (
        <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
          <h2 className="text-lg font-black text-[var(--text-main)]">Alertas criticas recientes</h2>
          <div className="mt-4 grid gap-3">
            {summary.critical_alerts.map((alert) => (
              <div key={alert.id} className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="font-black text-[var(--text-main)]">{alert.titulo}</p>
                  <span className={`rounded-full px-3 py-1 text-xs font-black uppercase ${alert.severidad === "rojo" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"}`}>
                    {alert.severidad}
                  </span>
                </div>
                <p className="mt-2 text-sm text-[var(--text-muted)]">{alert.descripcion}</p>
              </div>
            ))}
          </div>
        </section>
      )}

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

      <RegulatoryReadinessPanel matrix={matrix} />

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

export default CentralOperativaPage;
