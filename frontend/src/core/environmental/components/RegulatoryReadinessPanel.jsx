import { ClipboardCheck, Scale } from "lucide-react";

function RegulatoryReadinessPanel({ matrix }) {
  return (
    <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-start gap-3">
        <span className="rounded-xl border border-emerald-200 bg-emerald-50 p-2 text-emerald-800">
          <Scale size={18} />
        </span>
        <div>
          <h2 className="text-lg font-black text-[var(--text-main)]">Preparacion regulatoria</h2>
          <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
            Salidas y normas que deben quedar trazables antes de un reporte formal.
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <ReadinessColumn
          title="Normativa aplicable"
          items={matrix.regulations}
          emptyLabel="Sin normativa definida"
        />
        <ReadinessColumn
          title="Salidas regulatorias"
          items={matrix.regulatoryOutputs}
          emptyLabel="Sin salidas definidas"
        />
      </div>
    </section>
  );
}

function ReadinessColumn({ title, items, emptyLabel }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
      <div className="flex items-center gap-2 text-sm font-black text-[var(--text-main)]">
        <ClipboardCheck size={16} />
        {title}
      </div>
      <ul className="mt-3 space-y-2">
        {(items?.length ? items : [emptyLabel]).map((item) => (
          <li key={item} className="rounded-lg bg-white px-3 py-2 text-sm font-semibold text-[var(--text-muted)]">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default RegulatoryReadinessPanel;
