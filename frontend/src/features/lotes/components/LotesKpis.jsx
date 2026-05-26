import { Activity, AlertTriangle, Boxes, FileText } from "lucide-react";
import { formatNumber } from "@/shared/utils/formatters";

function LotesKpis({ lotes, totalEmisiones, totalEvidencias, obraCritica }) {
  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6 xl:grid-cols-4">
      <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)]">
        <div className="mb-3 flex items-center gap-3">
          <Boxes className="text-[var(--primary-dark)]" size={22} />
          <p className="text-sm font-medium text-[var(--text-muted)]">Total de obras</p>
        </div>
        <p className="mt-2 text-3xl font-bold text-[var(--text-main)]">
          {formatNumber(lotes.length, 0)}
        </p>
      </div>
      <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)]">
        <div className="mb-3 flex items-center gap-3">
          <Activity className="text-[var(--primary-dark)]" size={22} />
          <p className="text-sm font-medium text-[var(--text-muted)]">Emisiones registradas</p>
        </div>
        <p className="mt-2 text-3xl font-bold text-[#075985]">
          {formatNumber(totalEmisiones)} kg CO2e
        </p>
      </div>
      <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)]">
        <div className="mb-3 flex items-center gap-3">
          <FileText className="text-[var(--primary-dark)]" size={22} />
          <p className="text-sm font-medium text-[var(--text-muted)]">Evidencias asociadas</p>
        </div>
        <p className="mt-2 text-3xl font-bold text-[var(--primary-dark)]">
          {formatNumber(totalEvidencias, 0)}
        </p>
      </div>
      <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)]">
        <div className="mb-3 flex items-center gap-3">
          <AlertTriangle className="text-[var(--primary-dark)]" size={22} />
          <p className="text-sm font-medium text-[var(--text-muted)]">Obra crítica</p>
        </div>
        <p className="mt-2 truncate text-3xl font-bold text-[#3F6212]">
          {obraCritica || "Sin datos"}
        </p>
      </div>
    </section>
  );
}

export default LotesKpis;
