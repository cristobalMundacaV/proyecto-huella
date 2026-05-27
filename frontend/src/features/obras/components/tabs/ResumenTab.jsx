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
  const topSources = Object.values(
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
  )
    .sort((left, right) => right.emissions - left.emissions)
    .slice(0, 5);
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
  const mainRecommendation =
    totalEmissions > 0
      ? recommendationByCategory[criticalCategory] || recommendationByCategory.Otros
      : "Agrega registros de emisión para identificar las fuentes críticas de la obra.";

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

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Top fuentes críticas">
          <div className="space-y-3">
            {topSources.length ? (
              topSources.map((source, index) => (
                <div key={`${source.source}-${source.category}`} className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-bold text-[var(--primary-dark)]">#{index + 1} · {source.category}</p>
                      <p className="mt-1 font-semibold text-[var(--text-main)]">{source.source}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-[#075985]">{formatNumber(source.emissions, 1)} kg CO2e</p>
                      <p className="text-xs text-[var(--text-muted)]">{formatNumber(totalEmissions > 0 ? (source.emissions / totalEmissions) * 100 : 0, 1)}%</p>
                    </div>
                  </div>
                </div>
              ))
            ) : <EmptyAnalysis />}
          </div>
        </Panel>

        <Panel title="Recomendación principal">
          <p className="rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] p-4 text-sm font-medium leading-6 text-[var(--primary-dark)]">
            {mainRecommendation}
          </p>
          <div className="mt-3 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4">
            <p className="text-sm font-bold text-[var(--text-main)]">Estado documental / evidencias</p>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              {documents.length ? `Evidencias asociadas: ${formatNumber(documents.length, 0)} evidencias` : "Pendiente de vinculación documental"}
            </p>
          </div>
        </Panel>
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

function Panel({ children, title }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <h2 className="text-xl font-semibold text-[var(--text-main)]">{title}</h2>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function EmptyAnalysis() {
  return (
    <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 text-sm text-[var(--text-muted)]">
      No hay registros de emisión suficientes.
    </p>
  );
}
