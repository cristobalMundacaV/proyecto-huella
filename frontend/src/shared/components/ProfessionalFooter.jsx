import { ShieldCheck } from "lucide-react";

function ProfessionalFooter({
    label = "Carbono Zero",
    description = "Gestión ambiental, trazabilidad documental e inteligencia operativa para empresas.",
}) {
    return (
        <footer className="mt-10 rounded-[28px] border border-emerald-200/70 bg-[linear-gradient(135deg,rgba(15,45,39,0.98),rgba(18,61,52,0.96))] px-5 py-4 text-white shadow-[0_24px_70px_rgba(15,23,42,0.16)]">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                    <div className="rounded-2xl border border-emerald-300/20 bg-white/10 p-2 text-emerald-200">
                        <ShieldCheck size={20} />
                    </div>
                    <div>
                        <p className="text-sm font-black">{label}</p>
                        <p className="text-xs font-semibold text-emerald-100/80">
                            {description}
                        </p>
                    </div>
                </div>

                <p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-100/70">
                    Plataforma de inteligencia ambiental
                </p>
            </div>
        </footer>
    );
}

export default ProfessionalFooter;