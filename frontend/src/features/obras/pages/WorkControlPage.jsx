import { ArrowRight, ClipboardCheck, FileCheck2, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { Link, useOutletContext, useParams } from "react-router-dom";

import { KpiCard, SectionHeader } from "@/shared/ui";

const LINKS = [
  { id: "professionalReview", label: "Revisión profesional", description: "Hallazgos y decisiones formales registradas por personas autorizadas.", path: "/gobernanza/revision", icon: ClipboardCheck },
  { id: "governance", label: "Gobernanza", description: "Vista general de revisiones, discrepancias y expedientes de la organización.", path: "/gobernanza", icon: ShieldCheck },
  { id: "discrepancies", label: "Discrepancias", description: "Diferencias y validaciones pendientes entre fuentes de datos.", path: "/gobernanza/calidad", icon: SlidersHorizontal },
  { id: "dossiers", label: "Expedientes", description: "Antecedentes ambientales preparados para uso formal.", path: "/gobernanza/expedientes", icon: FileCheck2 },
];

/** Obra-scoped "Control" landing — the unified sidebar's Control item routes
 * here when a specific obra is selected, instead of opening a second,
 * separate obra sidebar. It surfaces this obra's own compliance summary
 * (already fetched by `ObraWorkspaceLayout`, no new call) and links out to
 * the existing revisión/gobernanza/discrepancias/expedientes surfaces —
 * those remain organization-wide today (see product report pendientes),
 * so this page is honest about that rather than fabricating a per-obra
 * filter that doesn't exist yet. */
export default function WorkControlPage() {
  const { obraId } = useParams();
  const { compliance, resourceErrors = {} } = useOutletContext();

  return (
    <main className="space-y-6">
      <SectionHeader
        title="Control de esta obra"
        description="Cumplimiento, revisión profesional, gobernanza, discrepancias y expedientes relevantes para esta obra."
      />

      <section className="rounded-[22px] border border-slate-200 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
        <SectionHeader
          title="Cumplimiento"
          description="Estado documental y alertas asociadas exclusivamente a esta obra."
          action={
            <Link className="inline-flex items-center gap-1.5 text-sm font-bold text-[var(--brand-primary)]" to={`/obras/${obraId}/cumplimiento`}>
              Ver cumplimiento <ArrowRight aria-hidden="true" size={15} />
            </Link>
          }
        />

        {resourceErrors.compliance ? (
          <p className="text-sm text-amber-800">El estado de cumplimiento no está disponible.</p>
        ) : compliance ? (
          <div className="grid gap-3 sm:grid-cols-3">
            <KpiCard icon={FileCheck2} label="Documentos" value={compliance.total_documentos} helper={compliance.documentos_validados === null || compliance.documentos_validados === undefined ? "Validación no disponible" : `${compliance.documentos_validados} validados`} />
            <KpiCard icon={ShieldCheck} label="Alertas abiertas" value={compliance.alertas_abiertas} status={compliance.alertas_abiertas ? "warning" : "success"} />
            <KpiCard icon={ShieldCheck} label="Cumplimiento" value={compliance.compliance_pct} unit="%" />
          </div>
        ) : (
          <p className="text-sm text-[var(--text-muted)]">Todavía no existe información suficiente para construir esta lectura.</p>
        )}
      </section>

      <section>
        <SectionHeader
          title="Gobernanza y revisión"
          description="Estas superficies siguen siendo organizacionales; el filtrado por obra es un pendiente documentado."
        />
        <div className="grid gap-3 sm:grid-cols-2">
          {LINKS.map((item) => (
            <Link key={item.id} to={item.path} className="group flex items-start gap-3 rounded-[18px] border border-slate-200 bg-slate-50/60 p-4 transition hover:border-emerald-300 hover:bg-white hover:shadow-md">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-emerald-700 shadow-sm"><item.icon aria-hidden="true" size={18} /></span>
              <span className="min-w-0">
                <span className="block font-black text-[var(--text-primary)]">{item.label}</span>
                <span className="mt-0.5 block text-xs leading-5 text-[var(--text-muted)]">{item.description}</span>
              </span>
              <ArrowRight aria-hidden="true" className="ml-auto mt-1 shrink-0 text-[var(--text-muted)] transition group-hover:text-emerald-700" size={15} />
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
