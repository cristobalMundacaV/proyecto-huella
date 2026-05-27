import { Activity, BarChart3, Boxes, FileCheck2, Gauge, Layers3 } from "lucide-react";
import { formatNumber } from "@/shared/utils/formatters";
import {
  constructionCategories,
  getConstructionCategoryLabel,
} from "@/features/obras/utils/constructionEmissionCategories";
import {
  getConstructionWorkDocumentTypeLabel,
} from "@/shared/utils/constructionEvidenceLabels";

const recommendationByCategory = {
  Materiales:
    "Revisa hormigón, acero, áridos y proveedores para evaluar alternativas de menor carbono incorporado.",
  Transporte:
    "Evalúa proveedores más cercanos, consolidación de viajes y reducción de kilómetros recorridos.",
  Maquinaria:
    "Controla ralentí, consumo por equipo y mantención para reducir el impacto operativo.",
  Energia:
    "Revisa uso de generadores, consumo eléctrico y posibilidades de conexión temporal a red.",
  Residuos:
    "Separa residuos valorizables y mejora la trazabilidad de retiro para reducir disposición final.",
  Agua:
    "Monitorea consumo por etapa para detectar desviaciones y mejorar eficiencia.",
  Otros:
    "Clasifica mejor los registros para identificar acciones de reducción concretas.",
};

const topSourceTones = ["danger", "warning", "info", "violet", "success"];
const sourceDonutColors = ["#E11D48", "#EA580C", "#2563EB", "#7C3AED", "#059669", "#0891B2", "#65A30D", "#475569", "#DB2777", "#0F766E"];

function ResumenTab({ balanceData, selectedObra }) {
  const registros = selectedObra.registros_emision || [];
  const documents = selectedObra.evidencias || [];
  const totalEmissions = Number(
    balanceData?.emisiones_generadas_kg_co2e ||
      selectedObra.emisiones_kg_co2e ||
      0
  );
  const declaredSurface = Number(selectedObra.superficie_m2 || 0);
  const carbonIntensity = declaredSurface > 0 ? totalEmissions / declaredSurface : null;
  const registrosWithCategories = registros.map((source) => ({
    ...source,
    categoria_visible: getConstructionCategoryLabel(source.categoria, source.fuente_emision),
  }));
  const categoryDistribution = constructionCategories
    .map((category) => {
      const emissions = registrosWithCategories.reduce(
        (total, source) =>
          source.categoria_visible === category
            ? total + Number(source.emisiones_kg_co2e || 0)
            : total,
        0
      );
      return {
        category,
        emissions,
        pct: totalEmissions > 0 ? (emissions / totalEmissions) * 100 : 0,
      };
    })
    .sort((left, right) => right.emissions - left.emissions);
  const criticalCategory =
    categoryDistribution.find((item) => item.emissions > 0)?.category || "Sin datos";
  const emissionsByStage = Object.values(
    registrosWithCategories.reduce((accumulator, source) => {
      const stage = source.etapa_nombre || selectedObra.etapa_nombre || "Sin etapa";
      const current = accumulator[stage] || { stage, emissions: 0 };
      current.emissions += Number(source.emisiones_kg_co2e || 0);
      accumulator[stage] = current;
      return accumulator;
    }, {})
  ).sort((left, right) => right.emissions - left.emissions);
  const criticalStage = emissionsByStage[0]?.stage || "Sin datos";
  const allSources = Object.values(
    registrosWithCategories.reduce((accumulator, registro) => {
      const source = registro.fuente_emision || "Sin fuente";
      const key = `${source}|${registro.categoria_visible}`;
      const current = accumulator[key] || {
        source,
        category: registro.categoria_visible,
        emissions: 0,
      };
      current.emissions += Number(registro.emisiones_kg_co2e || 0);
      accumulator[key] = current;
      return accumulator;
    }, {})
  ).sort((left, right) => right.emissions - left.emissions);
  const topSources = allSources.slice(0, 5);
  const environmentalStatus = getWorkEnvironmentalStatus({
    categoryDistribution,
    documents,
    totalEmissions,
  });
  const presentDocumentTypes = Array.from(
    new Set(documents.map((evidencia) => getConstructionWorkDocumentTypeLabel(evidencia.tipo_evidencia)))
  );
  const missingDocumentTypes = buildMissingDocumentSuggestions(registrosWithCategories, presentDocumentTypes);
  const traceability = getDocumentTraceability({
    documents,
    missingDocumentTypes,
    registrosWithCategories,
  });
  const operationalRecommendations = buildOperationalRecommendations({
    carbonIntensity,
    criticalCategory,
    criticalStage,
    documents,
    registros,
    topSources,
  });

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
        <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
              Resumen ambiental de obra
            </p>
            <h2 className="mt-1 text-2xl font-bold text-[var(--text-main)]">
              Inteligencia ambiental de construcción
            </h2>
          </div>
          <div className={`rounded-2xl border px-4 py-3 text-sm font-bold ${environmentalStatus.className}`}>
            <p>Estado ambiental de la obra</p>
            <p className="mt-1 text-lg">{environmentalStatus.label}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <WorkSummaryKpi icon={<Gauge />} label="Emisiones de la obra" tone="danger" value={`${formatNumber(totalEmissions, 1)} kg CO2e`} />
          <WorkSummaryKpi icon={<BarChart3 />} label="kg CO2e/m²" tone="info" value={carbonIntensity != null ? `${formatNumber(carbonIntensity, 2)} kg CO2e/m²` : "Pendiente de superficie"} />
          <WorkSummaryKpi icon={<Boxes />} label="Categoría crítica" tone="warning" value={criticalCategory} />
          <WorkSummaryKpi icon={<Layers3 />} label="Etapa crítica" tone="violet" value={criticalStage} />
          <WorkSummaryKpi icon={<Activity />} label="Registros de emisión" tone="neutral" value={formatNumber(registros.length, 0)} />
          <WorkSummaryKpi icon={<FileCheck2 />} label="Evidencias asociadas" tone="success" value={`${formatNumber(documents.length, 0)} evidencias`} />
        </div>
        <p className="mt-4 text-sm font-medium text-[var(--text-muted)]">
          La intensidad relaciona las emisiones registradas con la superficie declarada de la obra seleccionada.
        </p>
      </section>

      <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
        <div className="mb-5 flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.14em] text-[var(--primary-dark)]">
              Fuentes críticas
            </p>
            <h2 className="mt-1 text-2xl font-bold text-[var(--text-main)]">
              Top 5 fuentes de mayor impacto
            </h2>
            <p className="mt-1 max-w-4xl text-sm font-medium leading-6 text-[var(--text-muted)]">
              Estas fuentes concentran el mayor peso de la huella y ayudan a priorizar las primeras decisiones de reducción.
            </p>
          </div>
          <div className="rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] px-4 py-3 text-sm font-black text-[#075985]">
            {formatNumber(topSources.length, 0)} focos
          </div>
        </div>

        {topSources.length ? (
          <>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
              {topSources.map((source, index) => (
                <TopSourceKpi
                  key={`${source.source}-${source.category}`}
                  className={index < 3 ? "xl:col-span-2" : "xl:col-span-3"}
                  emissions={source.emissions}
                  index={index}
                  percentage={totalEmissions > 0 ? (source.emissions / totalEmissions) * 100 : 0}
                  source={source.source}
                  category={source.category}
                  tone={topSourceTones[index] || "neutral"}
                />
              ))}
            </div>
            <SourceDonutChart rows={allSources} totalEmissions={totalEmissions} />
          </>
        ) : (
          <EmptyAnalysis />
        )}
      </section>

      <RecommendationPanel recommendations={operationalRecommendations} />

      <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">Trazabilidad documental</p>
            <h3 className="mt-1 text-xl font-semibold text-[var(--text-main)]">{traceability.label}</h3>
            <p className="mt-2 text-sm text-[var(--text-muted)]">{traceability.description}</p>
          </div>
          <div className={`rounded-2xl border px-4 py-3 text-sm font-bold ${traceability.className}`}>
            Seguimiento interno
          </div>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
            <p className="text-sm font-bold text-[var(--text-main)]">Tipos de evidencias presentes</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {presentDocumentTypes.length ? presentDocumentTypes.map((type) => (
                <span key={type} className="rounded-full border border-[#B9D8D3] bg-[var(--info-bg)] px-3 py-1 text-xs font-bold text-[#075985]">{type}</span>
              )) : <span className="text-sm text-[var(--text-muted)]">Sin evidencias cargadas</span>}
            </div>
          </div>
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
            <p className="text-sm font-bold text-[var(--text-main)]">Evidencias faltantes sugeridas</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {missingDocumentTypes.length ? missingDocumentTypes.map((type) => (
                <span key={type} className="rounded-full border border-[#E1C56F] bg-[var(--warning-bg)] px-3 py-1 text-xs font-bold text-[#7A4F00]">{type}</span>
              )) : <span className="text-sm text-[var(--text-muted)]">No hay faltantes críticos sugeridos</span>}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default ResumenTab;

function WorkSummaryKpi({ icon, label, tone = "neutral", value }) {
  const toneClasses = getWorkSummaryTone(tone);

  return (
    <div className={`premium-card-interactive relative flex min-h-[165px] overflow-hidden rounded-[22px] border p-5 shadow-[0_14px_34px_rgba(15,23,42,0.08)] ring-1 ring-white/75 transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_20px_45px_rgba(15,23,42,0.13)] ${toneClasses.card}`}>
      <div className={`absolute inset-x-6 top-0 h-1.5 rounded-b-full ${toneClasses.accent}`} />
      <div className={`pointer-events-none absolute -right-10 -top-12 h-32 w-32 rounded-full blur-3xl ${toneClasses.glow}`} />
      <div className="relative z-10 flex w-full flex-col items-center text-center">
        <div className={`flex h-11 w-11 items-center justify-center rounded-2xl border shadow-[0_10px_24px_rgba(15,23,42,0.06)] ${toneClasses.icon}`}>{icon}</div>
        <p className={`mt-3 text-[11px] font-black uppercase tracking-[0.12em] ${toneClasses.title}`}>{label}</p>
        <div className="flex flex-1 items-center justify-center py-2">
          <h3 className={`mx-auto max-w-[260px] break-words text-center text-[clamp(1.25rem,2.2vw,1.75rem)] font-black leading-tight ${toneClasses.value}`}>{value || "Sin datos"}</h3>
        </div>
      </div>
    </div>
  );
}

function TopSourceKpi({ category, className = "", emissions, index, percentage, source, tone = "neutral" }) {
  const toneClasses = getWorkSummaryTone(tone);

  return (
    <div className={`premium-card-interactive relative flex min-h-[190px] overflow-hidden rounded-[24px] border p-5 shadow-[0_14px_34px_rgba(15,23,42,0.08)] ring-1 ring-white/75 transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_20px_45px_rgba(15,23,42,0.13)] ${toneClasses.card} ${className}`}>
      <div className={`absolute inset-x-6 top-0 h-1.5 rounded-b-full ${toneClasses.accent}`} />
      <div className={`pointer-events-none absolute -right-10 -top-12 h-32 w-32 rounded-full blur-3xl ${toneClasses.glow}`} />
      <div className="relative z-10 flex w-full flex-col items-center text-center">
        <div className={`inline-flex h-12 min-w-12 items-center justify-center rounded-2xl border px-3 text-lg font-black shadow-[0_10px_24px_rgba(15,23,42,0.06)] ${toneClasses.icon}`}>
          #{index + 1}
        </div>
        <p className={`mt-3 text-[11px] font-black uppercase tracking-[0.12em] ${toneClasses.title}`}>
          {category || "Sin categoría"}
        </p>
        <div className="flex flex-1 flex-col items-center justify-center py-2">
          <h3 className={`max-w-[280px] text-center text-[clamp(1.1rem,1.8vw,1.55rem)] font-black leading-tight ${toneClasses.value}`}>
            {source || "Sin fuente"}
          </h3>
          <p className={`mt-2 text-base font-black ${toneClasses.value}`}>
            {formatNumber(emissions, 1)} kg CO2e
          </p>
        </div>
        <div className="w-full rounded-full bg-white/70 p-1 ring-1 ring-black/5">
          <div className={`h-2 rounded-full ${toneClasses.accent}`} style={{ width: `${Math.max(0, Math.min(100, percentage || 0))}%` }} />
        </div>
        <p className={`mt-2 text-sm font-black ${toneClasses.value}`}>{formatNumber(percentage, 1)}% del total</p>
      </div>
    </div>
  );
}

function RecommendationPanel({ recommendations }) {
  return (
    <section className="rounded-3xl border border-[#A7F3D0] bg-[linear-gradient(135deg,#F0FDF4_0%,#FFFFFF_50%,#ECFDF5_100%)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <p className="text-xs font-black uppercase tracking-[0.14em] text-[var(--primary-dark)]">
        Recomendación principal
      </p>
      <h2 className="mt-1 text-2xl font-bold text-[var(--text-main)]">
        Plan operativo recomendado
      </h2>
      <p className="mt-1 max-w-4xl text-sm font-medium leading-6 text-[var(--text-muted)]">
        El sistema transforma la lectura ambiental en acciones concretas, priorizadas y medibles para reducir emisiones sin frenar la operación.
      </p>

      <div className="mt-5 space-y-3">
        {recommendations.steps.map((item, index) => (
          <article key={item.title} className="rounded-2xl border border-[#BBF7D0] bg-white p-4 shadow-[0_10px_26px_rgba(15,23,42,0.05)]">
            <div className="flex gap-4">
              <div className="flex h-9 min-w-9 items-center justify-center rounded-2xl border border-[#86EFAC] bg-[#ECFDF5] text-sm font-black text-[#047857]">
                {index + 1}
              </div>
              <div>
                <h3 className="text-base font-black text-[var(--text-main)]">{item.title}</h3>
                <p className="mt-1 text-[15px] font-semibold leading-7 text-[#065F46]">{item.description}</p>
              </div>
            </div>
          </article>
        ))}
      </div>

      <div className="mt-5 rounded-2xl border-l-4 border-[#059669] bg-white p-5 shadow-[0_10px_26px_rgba(15,23,42,0.05)]">
        <p className="text-xs font-black uppercase tracking-[0.14em] text-[#047857]">Lectura fuerte</p>
        <p className="mt-2 text-lg font-black leading-8 text-[var(--text-main)]">{recommendations.summary}</p>
      </div>
    </section>
  );
}

function buildOperationalRecommendations({ carbonIntensity, criticalCategory, criticalStage, documents, registros, topSources }) {
  const mainCategory = criticalCategory && criticalCategory !== "Sin datos" ? criticalCategory : "la categoría crítica";
  const mainStage = criticalStage && criticalStage !== "Sin datos" ? criticalStage : "la etapa crítica";
  const mainSource = topSources[0]?.source || "la fuente más emisora";
  const evidenceCount = Math.min(20, registros.length || 20);
  const intensityText = carbonIntensity != null ? `${formatNumber(carbonIntensity, 2)} kg CO2e/m²` : "la intensidad kg CO2e/m²";
  const documentAction = documents.length
    ? "Asegurar que los respaldos existentes estén vinculados a los registros de mayor impacto."
    : "Cargar factura, guía o ficha técnica antes de aprobar nuevos registros críticos.";

  return {
    steps: [
      {
        title: `Priorizar ${mainCategory} en ${mainStage}`,
        description: `Revisar ${mainSource}, proveedores, cantidades y alternativas antes de nuevas compras o avances de obra.`,
      },
      {
        title: "Exigir validación ambiental en compras críticas",
        description: `No aprobar materiales, combustibles o servicios de alto impacto sin factor de emisión, evidencia y origen verificable.`,
      },
      {
        title: "Regularizar evidencias de los registros más emisores",
        description: `Los ${formatNumber(evidenceCount, 0)} registros con mayor kg CO2e deben quedar respaldados con factura, guía, ficha técnica o documento equivalente. ${documentAction}`,
      },
      {
        title: "Controlar intensidad kg CO2e/m² semanalmente",
        description: `Usar ${intensityText} como línea base y medir la reducción contra el avance real de la obra, no solo contra el total acumulado.`,
      },
      {
        title: `Ejecutar piloto en ${mainStage}`,
        description: `Concentrar el primer esfuerzo en la etapa crítica, medir resultados y escalar solo cuando la reducción se mantenga sin afectar la ejecución.`,
      },
    ],
    summary: `La empresa no necesita hacer de todo al mismo tiempo. Necesita intervenir ${mainStage}, controlar ${mainCategory}, exigir evidencia documental y medir reducción por kg CO2e/m². Ese es el camino más realista para bajar emisiones sin romper la operación.`,
  };
}

function SourceDonutChart({ rows, totalEmissions }) {
  const chartRows = rows.filter((row) => Number(row.emissions || 0) > 0);
  const radius = 78;
  const circumference = 2 * Math.PI * radius;
  let accumulated = 0;
  const mainSource = chartRows[0];

  if (!chartRows.length) return null;

  return (
    <section className="mt-6 rounded-3xl border border-[var(--border)] bg-[linear-gradient(135deg,#FFFFFF_0%,#F8FAFC_48%,#EFF6FF_100%)] p-4 shadow-[0_14px_34px_rgba(15,23,42,0.06)] sm:p-6">
      <div className="mb-5 flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-[var(--primary-dark)]">Lectura visual</p>
          <h3 className="mt-1 text-2xl font-bold text-[var(--text-main)]">Participación de emisiones por fuente</h3>
          <p className="mt-1 max-w-3xl text-sm font-medium leading-6 text-[var(--text-muted)]">
            La dona muestra todas las fuentes que generan emisiones. Mientras más grande sea el segmento, mayor es la responsabilidad de esa fuente dentro de la huella de la obra.
          </p>
        </div>
        {mainSource && (
          <div className="rounded-2xl border border-[#FDA4AF] bg-[#FFF1F2] px-4 py-3 text-sm font-black text-[#BE123C]">
            Fuente dominante: {mainSource.source}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 items-center gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
        <div className="relative mx-auto flex h-[300px] w-full max-w-[340px] items-center justify-center">
          <svg viewBox="0 0 220 220" className="h-[280px] w-[280px] -rotate-90 overflow-visible">
            <circle cx="110" cy="110" fill="none" r={radius} stroke="#E2E8F0" strokeWidth="28" />
            {chartRows.map((row, index) => {
              const dash = totalEmissions > 0 ? (row.emissions / totalEmissions) * circumference : 0;
              const segment = (
                <circle
                  key={`${row.source}-${row.category}`}
                  cx="110"
                  cy="110"
                  fill="none"
                  r={radius}
                  stroke={sourceDonutColors[index % sourceDonutColors.length]}
                  strokeDasharray={`${dash} ${circumference}`}
                  strokeDashoffset={-accumulated}
                  strokeLinecap="butt"
                  strokeWidth="28"
                />
              );
              accumulated += dash;
              return segment;
            })}
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            <p className="text-xs font-black uppercase tracking-[0.14em] text-[var(--text-muted)]">Total obra</p>
            <p className="mt-1 text-2xl font-black text-[var(--text-main)]">{formatNumber(totalEmissions, 1)}</p>
            <p className="text-sm font-bold text-[var(--text-muted)]">kg CO2e</p>
          </div>
        </div>

        <div className="max-h-[430px] space-y-3 overflow-y-auto pr-1">
          {chartRows.map((row, index) => {
            const share = totalEmissions > 0 ? (row.emissions / totalEmissions) * 100 : 0;
            const color = sourceDonutColors[index % sourceDonutColors.length];

            return (
              <div key={`${row.source}-${row.category}`} className="rounded-2xl border border-[var(--border)] bg-white/85 p-4 shadow-[0_8px_22px_rgba(15,23,42,0.04)]">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <span className="h-3.5 w-3.5 rounded-full shadow-[0_0_0_4px_rgba(15,23,42,0.04)]" style={{ backgroundColor: color }} />
                    <div>
                      <p className="font-black text-[var(--text-main)]">{row.source}</p>
                      <p className="text-xs font-semibold text-[var(--text-muted)]">{row.category || "Sin categoría"}</p>
                    </div>
                  </div>
                  <div className="text-left sm:text-right">
                    <p className="font-black text-[#075985]">{formatNumber(row.emissions, 1)} kg CO2e</p>
                    <p className="text-xs font-bold text-[var(--text-muted)]">{formatNumber(share, 1)}%</p>
                  </div>
                </div>
                <div className="mt-3 h-2 rounded-full bg-[#E2E8F0]">
                  <div className="h-2 rounded-full" style={{ backgroundColor: color, width: `${Math.max(0, Math.min(100, share))}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function getWorkSummaryTone(tone) {
  const tones = {
    danger: { card: "border-[#FDA4AF] bg-[linear-gradient(135deg,#FFF1F2_0%,#FFFFFF_48%,#FFE4E6_100%)]", icon: "border-[#FDA4AF] bg-white text-[#BE123C]", title: "text-[#64748B]", value: "text-[#BE123C]", accent: "bg-[#E11D48]", glow: "bg-rose-200/70" },
    info: { card: "border-[#93C5FD] bg-[linear-gradient(135deg,#EFF6FF_0%,#FFFFFF_48%,#DBEAFE_100%)]", icon: "border-[#93C5FD] bg-white text-[#1D4ED8]", title: "text-[#64748B]", value: "text-[#1D4ED8]", accent: "bg-[#2563EB]", glow: "bg-blue-200/70" },
    warning: { card: "border-[#FDBA74] bg-[linear-gradient(135deg,#FFF7ED_0%,#FFFFFF_48%,#FFEDD5_100%)]", icon: "border-[#FDBA74] bg-white text-[#C2410C]", title: "text-[#64748B]", value: "text-[#C2410C]", accent: "bg-[#EA580C]", glow: "bg-orange-200/70" },
    violet: { card: "border-[#C4B5FD] bg-[linear-gradient(135deg,#F5F3FF_0%,#FFFFFF_48%,#EDE9FE_100%)]", icon: "border-[#C4B5FD] bg-white text-[#6D28D9]", title: "text-[#64748B]", value: "text-[#6D28D9]", accent: "bg-[#7C3AED]", glow: "bg-violet-200/70" },
    success: { card: "border-[#86EFAC] bg-[linear-gradient(135deg,#ECFDF3_0%,#FFFFFF_48%,#DCFCE7_100%)]", icon: "border-[#86EFAC] bg-white text-[#047857]", title: "text-[#64748B]", value: "text-[#047857]", accent: "bg-[#059669]", glow: "bg-emerald-200/70" },
    neutral: { card: "border-[#CBD5E1] bg-[linear-gradient(135deg,#FFFFFF_0%,#F8FAFC_48%,#E2E8F0_100%)]", icon: "border-[#CBD5E1] bg-white text-[#334155]", title: "text-[#64748B]", value: "text-[#334155]", accent: "bg-[#475569]", glow: "bg-slate-200/70" },
  };

  return tones[tone] || tones.neutral;
}

function getWorkEnvironmentalStatus({ categoryDistribution, documents, totalEmissions }) {
  if (!totalEmissions) return { label: "Sin datos", className: "border-slate-300 bg-slate-100 text-slate-700" };
  const maxShare = Math.max(...categoryDistribution.map((item) => item.pct || 0), 0);
  const activeCategories = categoryDistribution.filter((item) => item.emissions > 0).length;
  if (documents.length > 0 && maxShare <= 50) return { label: "Respaldada", className: "border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]" };
  if (maxShare > 60) return { label: "crítica", className: "border-[#F1B8B8] bg-[var(--danger-bg)] text-[#B42318]" };
  if (activeCategories >= 3) return { label: "Alta trazabilidad", className: "border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]" };
  return { label: "Inicial", className: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]" };
}

function buildMissingDocumentSuggestions(registrosWithCategories, presentDocumentTypes) {
  const suggestions = [];
  const hasCategory = (category) => registrosWithCategories.some((source) => source.categoria_visible === category);
  const hasDocument = (documentType) => presentDocumentTypes.includes(documentType);
  const addMissing = (items) => {
    items.forEach((item) => {
      if (!suggestions.includes(item) && !hasDocument(item)) suggestions.push(item);
    });
  };
  if (hasCategory("Materiales")) addMissing(["Factura de material", "Guía de despacho", "Ficha técnica de material"]);
  if (hasCategory("Transporte")) addMissing(["Guía de despacho", "Evidencia de transporte", "Ticket de pesaje"]);
  if (hasCategory("Maquinaria")) addMissing(["Factura de combustible", "Registro de maquinaria"]);
  if (hasCategory("Energia")) addMissing(["Boleta eléctrica", "Registro de generador"]);
  if (hasCategory("Residuos")) addMissing(["Ticket de pesaje", "Registro de retiro de residuos"]);
  return suggestions.slice(0, 6);
}

function getDocumentTraceability({ documents, missingDocumentTypes, registrosWithCategories }) {
  const validCount = documents.filter((evidencia) => ["validado", "validada"].includes(evidencia.estado_validacion || evidencia.estado_revision)).length;
  const observedCount = documents.filter((evidencia) => ["observada"].includes(evidencia.estado_revision)).length;
  const activeCategories = registrosWithCategories.filter((source) => source.categoria_visible).length;
  if (documents.length === 0) return { label: "Sin respaldo", description: "No hay evidencias asociadas a la obra.", className: "border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-main)]" };
  if (observedCount > 0) return { label: "En revisión", description: "Hay evidencias observadas o pendientes de ajuste.", className: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]" };
  if (missingDocumentTypes.length > 0) return { label: "Inicial", description: "Existe respaldo documental, pero aún faltan evidencias críticas por categoría.", className: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]" };
  if (validCount >= 3 && activeCategories >= 3) return { label: "Alta trazabilidad", description: "La obra tiene evidencias validadas para varias categorías críticas.", className: "border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]" };
  return { label: "Respaldada", description: "La obra cuenta con evidencias validadas para respaldar sus principales fuentes de emisión.", className: "border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]" };
}

function EmptyAnalysis() {
  return (
    <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 text-sm text-[var(--text-muted)]">
      No hay registros de emisión suficientes.
    </p>
  );
}
