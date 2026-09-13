import { ArrowRight, Boxes, Gauge, SlidersHorizontal } from "lucide-react";
import { Link, useOutletContext, useParams } from "react-router-dom";

import { SectionHeader, StatusBadge } from "@/shared/ui";

/** Obra-scoped "Configuración" landing — the unified sidebar's
 * Configuración item routes here when a specific obra is selected. Perfil
 * ambiental is obra-scoped and real (`/obras/:id/diagnostico`); ámbitos,
 * factores/metodologías and parámetros remain organization-wide today, so
 * this page links out to them rather than duplicating those screens. */
export default function WorkConfigPage() {
  const { obraId } = useParams();
  const { obra, context } = useOutletContext();
  const diagnosis = context?.diagnostico_obra || {};
  const profileCompleted = diagnosis.estado === "completado";

  const links = [
    { id: "profile", label: "Perfil ambiental", description: "Contexto, cobertura y aplicabilidad ambiental confirmada para esta obra.", path: `/obras/${obraId}/diagnostico`, icon: Gauge, badge: profileCompleted ? "Configurado" : "Pendiente", tone: profileCompleted ? "success" : "warning" },
    { id: "scopes", label: "Ámbitos", description: "Dimensiones ambientales aplicables a la organización.", path: "/administracion/ambiental", icon: Boxes },
    { id: "factors", label: "Factores y metodologías", description: "Referencias y metodologías utilizadas por el cálculo gobernado.", path: "/gobernanza/factores", icon: SlidersHorizontal },
    { id: "parameters", label: "Parámetros", description: "Preferencias de cálculo, importación y presentación.", path: "/administracion/calculo", icon: SlidersHorizontal },
  ];

  return (
    <main className="space-y-6">
      <SectionHeader
        title={`Configuración de ${obra?.nombre || "esta obra"}`}
        description="Perfil ambiental, ámbitos, factores, metodologías y parámetros aplicables a esta obra."
      />

      <div className="grid gap-3 sm:grid-cols-2">
        {links.map((item) => (
          <Link key={item.id} to={item.path} className="group flex items-start gap-3 rounded-[18px] border border-slate-200 bg-slate-50/60 p-4 transition hover:border-emerald-300 hover:bg-white hover:shadow-md">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-emerald-700 shadow-sm"><item.icon aria-hidden="true" size={18} /></span>
            <span className="min-w-0 flex-1">
              <span className="flex items-center gap-2">
                <span className="block font-black text-[var(--text-primary)]">{item.label}</span>
                {item.badge && <StatusBadge tone={item.tone}>{item.badge}</StatusBadge>}
              </span>
              <span className="mt-0.5 block text-xs leading-5 text-[var(--text-muted)]">{item.description}</span>
            </span>
            <ArrowRight aria-hidden="true" className="ml-auto mt-1 shrink-0 text-[var(--text-muted)] transition group-hover:text-emerald-700" size={15} />
          </Link>
        ))}
      </div>
    </main>
  );
}
