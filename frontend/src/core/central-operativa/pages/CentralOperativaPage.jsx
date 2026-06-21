import { useEffect, useState } from "react";
import { Activity, AlertTriangle, DatabaseZap, FileClock, ShieldCheck } from "lucide-react";

import { useEnvironmentalContext } from "@/domain/environmental";
import CriticalDocumentsPanel from "@/core/environmental/components/CriticalDocumentsPanel";
import EnvironmentalContextCard from "@/core/environmental/components/EnvironmentalContextCard";
import EnvironmentalItemGrid from "@/core/environmental/components/EnvironmentalItemGrid";
import EnvironmentalKpiGrid from "@/core/environmental/components/EnvironmentalKpiGrid";
import EnvironmentalRecommendationList from "@/core/environmental/components/EnvironmentalRecommendationList";
import EnvironmentalShell from "@/core/environmental/components/EnvironmentalShell";
import RecommendedActionsPanel from "@/core/environmental/components/RecommendedActionsPanel";
import RegulatoryReadinessPanel from "@/core/environmental/components/RegulatoryReadinessPanel";
import RiskSignalsPanel from "@/core/environmental/components/RiskSignalsPanel";
import { getEnvironmentalComplianceSummary } from "@/features/environmental/services/environmentalComplianceApi";
import { getEnvironmentalKpis } from "@/features/environmental/services/environmentalKpiApi";
import { getEnvironmentalRecommendations } from "@/features/environmental/services/environmentalRecommendationApi";

function CentralOperativaPage() {
  const { activeCompany, matrix } = useEnvironmentalContext();
  const [summary, setSummary] = useState(null);
  const [kpis, setKpis] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!activeCompany?.constructora_id) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([
      getEnvironmentalKpis(activeCompany.constructora_id),
      getEnvironmentalComplianceSummary(activeCompany.constructora_id),
      getEnvironmentalRecommendations(activeCompany.constructora_id),
    ])
      .then(([kpiData, summaryData, recommendationData]) => {
        if (!cancelled) {
          setKpis(kpiData);
          setSummary(summaryData);
          setRecommendations(recommendationData);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setKpis(null);
          setSummary(null);
          setRecommendations(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeCompany?.constructora_id]);

  return (
    <EnvironmentalShell
      eyebrow="Modulo critico"
      title="Central Operativa"
      description="Resumen de cumplimiento ambiental para decidir que datos completar, que riesgos controlar y que acciones ejecutar."
    >
      <EnvironmentalContextCard company={activeCompany} matrix={matrix} />

      <EnvironmentalKpiGrid kpis={kpis?.cards || []} />

      <EnvironmentalRecommendationList recommendations={recommendations?.recommendations || []} />

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
