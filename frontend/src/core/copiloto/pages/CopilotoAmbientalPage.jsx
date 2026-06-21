import { useEffect, useState } from "react";
import { AlertTriangle, Bot, FileText, MessageSquareText } from "lucide-react";

import { useEnvironmentalContext } from "@/domain/environmental";
import EnvironmentalContextCard from "@/core/environmental/components/EnvironmentalContextCard";
import EnvironmentalShell from "@/core/environmental/components/EnvironmentalShell";
import {
  getComplianceAlerts,
  getEnvironmentalDocuments,
} from "@/features/environmental/services/environmentalComplianceApi";

function CopilotoAmbientalPage() {
  const { activeCompany, matrix } = useEnvironmentalContext();
  const [alerts, setAlerts] = useState([]);
  const [documents, setDocuments] = useState([]);

  useEffect(() => {
    if (!activeCompany?.constructora_id) return;
    Promise.all([
      getComplianceAlerts(activeCompany.constructora_id),
      getEnvironmentalDocuments(activeCompany.constructora_id),
    ])
      .then(([alertData, documentData]) => {
        setAlerts(alertData);
        setDocuments(documentData);
      })
      .catch(() => {
        setAlerts([]);
        setDocuments([]);
      });
  }, [activeCompany?.constructora_id]);

  return (
    <EnvironmentalShell
      eyebrow="Modulo critico"
      title="Copiloto Ambiental"
      description="Shell preparado para un futuro copiloto con datos de empresa, RCA y normativa chilena. No ejecuta llamadas LLM."
    >
      <EnvironmentalContextCard company={activeCompany} matrix={matrix} />

      {(alerts.length > 0 || documents.length > 0) && (
        <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
          <h2 className="text-lg font-black text-[var(--text-main)]">Contexto disponible</h2>
          <div className="mt-4 flex flex-wrap gap-3">
            {documents.slice(0, 4).map((document) => (
              <ContextPill key={`doc-${document.id}`} icon={FileText} label={document.nombre} tone="blue" />
            ))}
            {alerts.slice(0, 4).map((alert) => (
              <ContextPill key={`alert-${alert.id}`} icon={AlertTriangle} label={alert.titulo} tone={alert.severidad === "rojo" ? "red" : "amber"} />
            ))}
          </div>
        </section>
      )}

      <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
        <div className="flex items-start gap-3">
          <span className="rounded-xl border border-blue-200 bg-blue-50 p-2 text-blue-800">
            <Bot size={18} />
          </span>
          <div>
            <h2 className="text-lg font-black text-[var(--text-main)]">Preguntas sugeridas por industria</h2>
            <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
              Consultas iniciales para revisar datos, riesgos, evidencias y acciones antes de activar RAG normativo.
            </p>
          </div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {matrix.copilotQuestions.map((question) => (
            <div key={question} className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
              <div className="flex items-start gap-3">
                <MessageSquareText className="mt-0.5 text-[var(--primary-dark)]" size={18} />
                <p className="text-sm font-bold text-[var(--text-main)]">{question}</p>
              </div>
              <p className="mt-3 text-sm text-[var(--text-muted)]">
                Debe responderse con datos internos, evidencia trazable y referencia normativa aplicable.
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
        <h2 className="text-lg font-black text-[var(--text-main)]">Base requerida para RAG</h2>
        <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
          La respuesta futura debe apoyarse en documentos cargados, variables validadas, obligaciones RCA y regulacion chilena vigente asociada al rubro.
        </p>
      </section>
    </EnvironmentalShell>
  );
}

function ContextPill({ icon: Icon, label, tone }) {
  const toneClass = {
    blue: "border-blue-200 bg-blue-50 text-blue-800",
    amber: "border-amber-200 bg-amber-50 text-amber-800",
    red: "border-red-200 bg-red-50 text-red-800",
  }[tone];
  return (
    <span className={`inline-flex max-w-full items-center gap-2 rounded-full border px-3 py-2 text-sm font-bold ${toneClass}`}>
      <Icon size={15} />
      <span className="truncate">{label}</span>
    </span>
  );
}

export default CopilotoAmbientalPage;
