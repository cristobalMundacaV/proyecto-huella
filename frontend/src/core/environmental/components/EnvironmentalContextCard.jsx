import { Building2, Factory, ShieldCheck } from "lucide-react";

function EnvironmentalContextCard({ company, matrix }) {
  const rubro = company?.rubro || company?.industria || "Rubro no informado";

  return (
    <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Contexto ambiental activo</p>
          <h2 className="mt-2 text-2xl font-black text-[var(--text-main)]">{company?.nombre || "Empresa activa"}</h2>
          <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">{matrix.purpose}</p>
        </div>

        <div className="grid min-w-0 gap-2 text-sm sm:grid-cols-3 lg:min-w-[420px]">
          <Metric icon={Building2} label="Rubro" value={rubro} />
          <Metric icon={Factory} label="Matriz" value={matrix.label} />
          <Metric icon={ShieldCheck} label="Foco" value="Cumplimiento" />
        </div>
      </div>
    </section>
  );
}

function Metric({ icon: Icon, label, value }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-3">
      <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
        <Icon size={15} />
        {label}
      </div>
      <p className="mt-2 truncate font-black text-[var(--text-main)]" title={value}>
        {value}
      </p>
    </div>
  );
}

export default EnvironmentalContextCard;
