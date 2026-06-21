import { useEffect, useState } from "react";
import { ClipboardCheck, FileCheck2 } from "lucide-react";

import { useEnvironmentalContext } from "@/domain/environmental";
import EnvironmentalContextCard from "@/core/environmental/components/EnvironmentalContextCard";
import EnvironmentalExecutiveReportCard from "@/core/environmental/components/EnvironmentalExecutiveReportCard";
import EnvironmentalShell from "@/core/environmental/components/EnvironmentalShell";
import RegulatoryReadinessPanel from "@/core/environmental/components/RegulatoryReadinessPanel";
import RiskSignalsPanel from "@/core/environmental/components/RiskSignalsPanel";
import {
  getComplianceAlerts,
  getEnvironmentalComplianceSummary,
  getEnvironmentalDocuments,
  getEnvironmentalVariables,
} from "@/features/environmental/services/environmentalComplianceApi";
import { getEnvironmentalExecutiveReport } from "@/features/environmental/services/environmentalExecutiveReportApi";

function ReportesRegulatoriosPage() {
  const { activeCompany, matrix } = useEnvironmentalContext();
  const [summary, setSummary] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [variables, setVariables] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [executiveReport, setExecutiveReport] = useState(null);

  useEffect(() => {
    if (!activeCompany?.constructora_id) return;
    Promise.all([
      getEnvironmentalComplianceSummary(activeCompany.constructora_id),
      getEnvironmentalDocuments(activeCompany.constructora_id),
      getEnvironmentalVariables(activeCompany.constructora_id),
      getComplianceAlerts(activeCompany.constructora_id),
      getEnvironmentalExecutiveReport(activeCompany.constructora_id),
    ])
      .then(([summaryData, documentData, variableData, alertData, executiveReportData]) => {
        setSummary(summaryData);
        setDocuments(documentData);
        setVariables(variableData);
        setAlerts(alertData);
        setExecutiveReport(executiveReportData);
      })
      .catch(() => {
        setSummary(null);
        setDocuments([]);
        setVariables([]);
        setAlerts([]);
        setExecutiveReport(null);
      });
  }, [activeCompany?.constructora_id]);

  return (
    <EnvironmentalShell
      eyebrow="Modulo critico"
      title="Reportes Regulatorios"
      description="Vista de preparacion para reportes ambientales. Muestra salidas esperadas y brechas, sin generar exportaciones."
    >
      <EnvironmentalContextCard company={activeCompany} matrix={matrix} />
      <EnvironmentalExecutiveReportCard report={executiveReport} />

      <section className="grid gap-4 md:grid-cols-4">
        <ReadinessCard title="RETC" documents={documents.length} variables={variables.length} alerts={alerts.filter((item) => item.estado === "abierta").length} />
        <ReadinessCard title="SINADER" documents={documents.filter((item) => String(item.tipo_documento).toLowerCase().includes("resid")).length} variables={variables.filter((item) => String(item.categoria).toLowerCase().includes("resid")).length} alerts={alerts.filter((item) => item.normativa === "SINADER").length} />
        <ReadinessCard title="SIDREP" documents={documents.filter((item) => String(item.nombre).toLowerCase().includes("respel")).length} variables={variables.filter((item) => String(item.variable_id).toLowerCase().includes("respel")).length} alerts={alerts.filter((item) => item.normativa === "SIDREP").length} />
        <ReadinessCard title="RILES" documents={documents.filter((item) => String(item.nombre).toLowerCase().includes("riles")).length} variables={variables.filter((item) => ["ph", "dbo5", "dqo", "sst"].includes(item.variable_id)).length} alerts={alerts.filter((item) => item.normativa === "DS90").length} />
      </section>

      <div className="grid gap-6 xl:grid-cols-[1fr_0.85fr]">
        <RegulatoryReadinessPanel matrix={matrix} />
        <RiskSignalsPanel matrix={matrix} />
      </div>

      <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
        <div className="flex items-start gap-3">
          <span className="rounded-xl border border-emerald-200 bg-emerald-50 p-2 text-emerald-800">
            <ClipboardCheck size={18} />
          </span>
          <div>
            <h2 className="text-lg font-black text-[var(--text-main)]">Criterio de preparacion</h2>
            <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
              Un reporte esta listo cuando cada salida regulatoria tiene documentos validados, variables calculables y alertas abiertas bajo control.
            </p>
            <p className="mt-3 text-sm font-bold text-[var(--text-main)]">
              Estado actual: {summary?.documentos_validados ?? 0} documentos validados, {summary?.total_variables ?? 0} variables y {summary?.alertas_abiertas ?? 0} alertas abiertas.
            </p>
          </div>
        </div>
      </section>
    </EnvironmentalShell>
  );
}

function ReadinessCard({ title, documents, variables, alerts }) {
  const ready = documents > 0 && variables > 0 && alerts === 0;
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-black text-[var(--text-main)]">Preparacion {title}</h2>
        <FileCheck2 className={ready ? "text-emerald-700" : "text-amber-700"} size={20} />
      </div>
      <p className="mt-3 text-2xl font-black text-[var(--text-main)]">{ready ? "Lista" : "En preparacion"}</p>
      <p className="mt-2 text-sm text-[var(--text-muted)]">
        {documents} documentos, {variables} variables, {alerts} alertas asociadas.
      </p>
    </div>
  );
}

export default ReportesRegulatoriosPage;
