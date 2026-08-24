import { Building2, FileUp } from "lucide-react";
import { ButtonLink } from "@/shared/ui";

export default function ReadyToStartPage() {
  return <main className="mx-auto max-w-5xl"><section className="rounded-3xl border border-emerald-200 bg-gradient-to-br from-white to-emerald-50 p-7 shadow-sm sm:p-10"><p className="text-xs font-black uppercase tracking-widest text-emerald-700">Organización preparada</p><h1 className="mt-3 text-4xl font-black text-slate-950">Aún no hay información operacional</h1><p className="mt-4 max-w-2xl text-lg leading-8 text-slate-600">Crea tu primera obra o incorpora información para comenzar a construir indicadores. Carbono Zero no mostrará resultados ambientales hasta contar con datos reales.</p><div className="mt-8 flex flex-wrap gap-3"><ButtonLink to="/obras" leftIcon={Building2}>Crear primera obra</ButtonLink><ButtonLink to="/datos" variant="secondary" leftIcon={FileUp}>Subir información</ButtonLink></div></section></main>;
}
