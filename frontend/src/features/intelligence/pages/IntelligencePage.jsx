import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowRight, Bot, CheckCircle2, CircleAlert, ClipboardCheck, Lightbulb, ScanSearch, ShieldAlert, Sparkles, TrendingDown, TrendingUp } from "lucide-react";

import PlatformLoader from "@/shared/components/PlatformLoader";
import { getEnvironmentalDomain } from "@/shared/config/environmentalDomains";
import { ButtonLink, EmptyState, ErrorState, KpiCard, Pagination, SectionHeader, StatusBadge } from "@/shared/ui";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { listProblems } from "@/features/mejora/services/improvementApi";
import { problemStatusLabel, problemTone, riskLabel } from "@/features/mejora/utils/improvementFormat";

const PAGE_SIZE = 8;
const CLOSED_STATES = ["cerrada", "resuelta"];
const PROFESSIONAL_STATES = ["escalada", "escalada_profesional", "no_resuelta"];
const isClosed = (value) => CLOSED_STATES.includes(value);
const needsProfessional = (value) => PROFESSIONAL_STATES.includes(value);

const categoryKey = (value) => {
  const key = String(value || "").toLowerCase().normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "").replaceAll(" ", "_").replaceAll("-", "_");
  return key === "hidrica_y_suelo" ? "hidrica_suelo" : key;
};

const categoryInfo = (value) => getEnvironmentalDomain(categoryKey(value)) || {
  label: value || "Sin categoría", icon: CircleAlert, text: "text-slate-600", softBg: "bg-slate-100",
};

const signalIcon = (item, fallback) => {
  const text = `${item.titulo || ""} ${item.descripcion || ""}`.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  if (/aumento|alza|crecimiento|incremento/.test(text)) return TrendingUp;
  if (/caida|disminucion|perdida/.test(text)) return TrendingDown;
  if (/seguimiento|revision|trazabilidad|conciliacion/.test(text)) return ScanSearch;
  if (/riesgo|desvio|incumplimiento|alerta/.test(text)) return ShieldAlert;
  return fallback;
};

const riskInfo = (value) => {
  if (["critico", "alto"].includes(value)) return { card: "border-rose-200 border-l-rose-500 bg-rose-50/35", icon: "bg-rose-100 text-rose-700", signal: "border-rose-200 bg-rose-50 text-rose-700" };
  if (value === "medio") return { card: "border-amber-200 border-l-amber-500 bg-amber-50/35", icon: "bg-amber-100 text-amber-700", signal: "border-amber-200 bg-amber-50 text-amber-700" };
  if (value === "bajo") return { card: "border-sky-200 border-l-sky-500 bg-sky-50/30", icon: "bg-sky-100 text-sky-700", signal: "border-sky-200 bg-sky-50 text-sky-700" };
  return { card: "border-slate-200 border-l-slate-400 bg-white", icon: "bg-slate-100 text-slate-600", signal: "border-slate-200 bg-slate-50 text-slate-600" };
};

const priority = (item) => {
  if (["critico", "alto"].includes(item.nivel_riesgo)) return 1;
  if (needsProfessional(item.estado)) return 2;
  if (item.nivel_riesgo === "medio") return 3;
  if (item.nivel_riesgo === "bajo") return 4;
  return 5;
};

export default function IntelligencePage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const [page, setPage] = useState(1);
  const [state, setState] = useState({ loading: true, rows: [], error: "" });

  const load = useCallback(() => {
    if (!activeOrganizacionId) {
      setState({ loading: false, rows: [], error: "" });
      return;
    }
    setState({ loading: true, rows: [], error: "" });
    listProblems(activeOrganizacionId)
      .then((rows) => setState({ loading: false, rows: Array.isArray(rows) ? rows : [], error: "" }))
      .catch(() => setState({ loading: false, rows: [], error: "No fue posible cargar las prioridades ambientales." }));
  }, [activeOrganizacionId]);

  useEffect(() => { load(); }, [load]);

  const openProblems = useMemo(() => state.rows.filter((item) => !isClosed(item.estado))
    .map((item, index) => ({ item, index }))
    .sort((left, right) => priority(left.item) - priority(right.item) || left.index - right.index)
    .map(({ item }) => item), [state.rows]);

  const datasetKey = openProblems.map((item) => item.id).join(":");
  useEffect(() => { setPage(1); }, [activeOrganizacionId, datasetKey]);

  const summary = useMemo(() => ({
    open: openProblems.length,
    highRisk: openProblems.filter((item) => ["alto", "critico"].includes(item.nivel_riesgo)).length,
    professional: openProblems.filter((item) => needsProfessional(item.estado)).length,
  }), [openProblems]);
  const visibleProblems = openProblems.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  if (state.loading) return <PlatformLoader title="Preparando inteligencia ambiental" description="Estamos organizando problemas, riesgos y necesidades de revisión de la organización." />;

  return <main className="space-y-6">
    <section className="overflow-hidden rounded-[24px] border border-cyan-200 bg-[radial-gradient(circle_at_top_right,rgba(34,211,238,0.18),transparent_42%),linear-gradient(135deg,rgba(236,253,245,0.96),rgba(240,249,255,0.96))] p-5 shadow-[0_12px_34px_rgba(8,145,178,0.08)]">
      <div className="flex items-start gap-4">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-cyan-100 text-cyan-800 ring-1 ring-cyan-200"><Sparkles aria-hidden="true" size={21} /></span>
        <SectionHeader eyebrow="INTELIGENCIA AMBIENTAL" title="Prioridades de gestión" description="Señales construidas a partir de problemas, riesgos y necesidades reales de seguimiento." />
      </div>
    </section>

    {state.error ? <ErrorState description={state.error} onRetry={load} /> : !summary.open ? <EmptyState icon={CheckCircle2} title="Sin prioridades ambientales pendientes" description="No existen problemas abiertos que requieran priorización o seguimiento en este momento." /> : <>
      <section aria-label="Lectura ejecutiva" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <KpiCard align="center" icon={AlertTriangle} label="Problemas abiertos" value={summary.open} helper="requieren seguimiento" status="warning" />
        <KpiCard align="center" icon={ShieldAlert} label="Riesgo alto" value={summary.highRisk} helper="prioridad de revisión" status="danger" />
        <KpiCard align="center" icon={ClipboardCheck} label="Revisión profesional" value={summary.professional} helper="escalados o no resueltos" status="info" />
      </section>

      <section className="space-y-4 rounded-[22px] border border-slate-200 bg-slate-50/70 p-4 shadow-[0_10px_30px_rgba(15,23,42,0.04)] sm:p-5">
        <SectionHeader title="Requiere tu atención" description="Pendientes priorizados según riesgo, seguimiento y necesidad de intervención." />
        <div className="grid gap-3">
          {visibleProblems.map((item) => {
            const category = categoryInfo(item.categoria);
            const CategoryIcon = category.icon;
            const SignalIcon = signalIcon(item, CategoryIcon);
            const risk = riskInfo(item.nivel_riesgo);
            return <article key={item.id} className={`rounded-[18px] border border-l-4 p-4 shadow-[0_8px_24px_rgba(15,23,42,0.045)] ${risk.card}`}>
              <div className="flex items-start gap-3 sm:gap-4">
                <span className={`flex h-10 w-10 shrink-0 items-center justify-center self-center rounded-xl ${risk.icon}`}><SignalIcon aria-hidden="true" size={19} /></span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-3">
                    <h2 className="font-black text-[var(--text-primary)]">{item.titulo || "Problema ambiental"}</h2>
                    <span className="shrink-0"><StatusBadge tone={problemTone(item.estado)}>{problemStatusLabel(item.estado)}</StatusBadge></span>
                  </div>
                  {item.descripcion && <p className="mt-1 line-clamp-2 text-sm leading-5 text-[var(--text-secondary)]">{item.descripcion}</p>}
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs font-bold">
                    <span className={`inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1 ${category.text}`}><CategoryIcon aria-hidden="true" size={14} />Categoría: {category.label}</span>
                    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${risk.signal}`}><ShieldAlert aria-hidden="true" size={14} />Riesgo: {riskLabel(item.nivel_riesgo)}</span>
                    {needsProfessional(item.estado) && <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-violet-50 px-2.5 py-1 text-violet-700"><Bot aria-hidden="true" size={14} />Requiere revisión profesional</span>}
                  </div>
                  <div className="mt-3 flex justify-end">
                    <ButtonLink size="sm" variant="secondary" rightIcon={ArrowRight} to={`/inteligencia/problemas/${item.id}`}>Ver gestión</ButtonLink>
                  </div>
                </div>
              </div>
            </article>;
          })}
        </div>
        <Pagination page={page} totalItems={openProblems.length} pageSize={PAGE_SIZE} onChange={setPage} itemLabel="prioridades" />
      </section>

      <section className="rounded-[20px] border border-cyan-200 bg-[linear-gradient(135deg,rgba(236,254,255,0.9),rgba(240,253,250,0.9))] p-4">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-cyan-100 text-cyan-800"><Bot aria-hidden="true" size={18} /></span>
          <div className="min-w-0 flex-1">
            <h2 className="font-black">Cómo te ayuda la inteligencia</h2>
            <div className="mt-3 grid gap-2 text-sm text-[var(--text-secondary)] md:grid-cols-3">
              <span className="flex items-center gap-2"><Sparkles aria-hidden="true" className="text-cyan-700" size={16} />Organiza contexto y señales.</span>
              <span className="flex items-center gap-2"><Lightbulb aria-hidden="true" className="text-cyan-700" size={16} />Explica restricciones y prioridades.</span>
              <span className="flex items-center gap-2"><ClipboardCheck aria-hidden="true" className="text-cyan-700" size={16} />Prepara alternativas para revisión humana.</span>
            </div>
            <p className="mt-3 border-t border-cyan-200/70 pt-3 text-xs text-[var(--text-muted)]">No modifica cálculos, no inventa factores y no ejecuta decisiones automáticamente.</p>
          </div>
        </div>
      </section>
    </>}
  </main>;
}
