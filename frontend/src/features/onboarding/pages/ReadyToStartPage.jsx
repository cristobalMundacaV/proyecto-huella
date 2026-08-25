import { Building2, FileUp, Users } from "lucide-react";
import { ButtonLink } from "@/shared/ui";

export default function ReadyToStartPage() {
  return <main className="mx-auto max-w-5xl"><section className="rounded-3xl border border-emerald-200 bg-gradient-to-br from-white to-emerald-50 p-7 shadow-sm sm:p-10"><p className="text-xs font-black uppercase tracking-widest text-emerald-700">Organización preparada</p><h1 className="mt-3 text-4xl font-black text-slate-950">Tu organización está lista</h1><p className="mt-4 max-w-2xl text-lg leading-8 text-slate-600">Ahora puedes comenzar a configurar tu operación y conectar información real. Carbono Zero construirá el estado de tu información a partir de los datos y evidencias que incorpores.</p><div className="mt-8 flex flex-wrap gap-3"><ButtonLink to="/obras?crear=1" leftIcon={Building2}>Crear primera obra</ButtonLink><ButtonLink to="/datos" variant="secondary" leftIcon={FileUp}>Agregar información</ButtonLink><ButtonLink to="/administracion/equipo" variant="secondary" leftIcon={Users}>Configurar equipo</ButtonLink></div></section></main>;
}
