import {
  AlertTriangle,
  BarChart3,
  Building2,
  Cloud,
  FileText,
  FlaskConical,
  Fuel,
  Landmark,
  Leaf,
  Lightbulb,
  Settings,
  ShieldCheck,
  Sparkles,
  Target,
  Zap,
} from "lucide-react";

const formatNumber = (value, maximumFractionDigits = 2) =>
  new Intl.NumberFormat("es-CL", {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  }).format(Number(value || 0));

const formatTitleCase = (value) =>
  String(value || "")
    .replace(/_/g, " ")
    .trim()
    .split(/\s+/)
    .map((word) => (word ? `${word.charAt(0).toUpperCase()}${word.slice(1).toLowerCase()}` : ""))
    .join(" ");

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const normalizePlanText = (value) =>
  String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

const formatFocusForSentence = (value) => {
  const normalizedValue = normalizePlanText(value);
  if (normalizedValue.includes("diesel") && normalizedValue.includes("combustion") && normalizedValue.includes("movil")) {
    return "la combustión móvil de diésel";
  }
  return value;
};

const formatViabilityForSentence = (value) => String(value || "").trim().toLowerCase();

const isValidExecutiveLabel = (value) => {
  const text = String(value ?? "").trim();
  const normalized = text.toLowerCase();
  return Boolean(text && text !== "0" && normalized !== "null" && normalized !== "undefined" && normalized !== "nan");
};

const getExecutiveLabel = (value, fallback) => (isValidExecutiveLabel(value) ? String(value).trim() : fallback);

const hasValidScenario = (scenario) => Boolean(scenario && Number(scenario.currentTotal) > 0 && Number(scenario.simulatedTotal) > 0 && Number(scenario.reductionPct) > 0);

const formatPercentRange = ({ min, max }) => (min === max ? `${min}%` : `${min}%-${max}%`);

function KpiIcon({ icon: Icon, tone = "teal" }) {
  const tones = {
    teal: "bg-teal-50 text-[#0F766E] border-teal-100",
    green: "bg-emerald-50 text-[#047857] border-emerald-100",
    amber: "bg-amber-50 text-[#B45309] border-amber-100",
    red: "bg-red-50 text-[#B42318] border-red-100",
    blue: "bg-blue-50 text-[#1D4ED8] border-blue-100",
    slate: "bg-slate-50 text-[#334155] border-slate-200",
  };

  return (
    <div className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-full border ${tones[tone] || tones.teal}`}>
      <Icon size={28} strokeWidth={2.2} />
    </div>
  );
}

function ExecutiveKpiCard({ label, value, icon, tone = "slate", description, className = "" }) {
  const toneStyles = {
    teal: { card: "border-[#99F6E4] bg-[#F0FDFA]", value: "text-[#0F766E]" },
    green: { card: "border-[#A7F3D0] bg-[#ECFDF3]", value: "text-[#047857]" },
    amber: { card: "border-[#FDBA74] bg-[#FFF7ED]", value: "text-[#B45309]" },
    red: { card: "border-[#FDA29B] bg-[#FEF3F2]", value: "text-[#B42318]" },
    blue: { card: "border-[#BFDBFE] bg-[#EFF6FF]", value: "text-[#1D4ED8]" },
    slate: { card: "border-[#E2E8F0] bg-white", value: "text-[#334155]" },
  };
  const selectedTone = toneStyles[tone] || toneStyles.slate;

  return (
    <div className={`flex min-h-[7.75rem] min-w-0 flex-col rounded-[18px] border p-4 shadow-[0_8px_24px_rgba(15,23,42,0.04)] transition duration-300 ease-out hover:shadow-[0_10px_28px_rgba(15,23,42,0.05)] sm:p-5 ${selectedTone.card} ${className}`}>
      <div className="flex items-center gap-3">
        <KpiIcon icon={icon} tone={tone} />
        <p className="min-w-0 text-[11px] font-bold uppercase leading-4 tracking-[0.18em] text-[#64748B]">{formatTitleCase(label)}</p>
      </div>
      <div className="flex flex-1 flex-col items-center justify-center pt-3 text-center">
        <p className={`w-full whitespace-normal break-normal text-center text-2xl font-black leading-tight tracking-tight ${selectedTone.value}`}>{value}</p>
        {description ? <p className="mt-2 text-center text-sm leading-6 text-[#64748B]">{description}</p> : null}
      </div>
    </div>
  );
}

function buildProgressiveActionRanges(potentialReduction) {
  const potential = Number(potentialReduction || 0);
  if (!potential || potential <= 0) {
    return {
      quickRange: { min: 3, max: 6 },
      pilotRange: { min: 7, max: 10 },
      structuralRangeLabel: "Pendiente",
    };
  }

  const structuralFloor = Math.max(1, Math.floor(potential));
  let quickMin = clamp(Math.round(potential * 0.25), 1, structuralFloor);
  let quickMax = clamp(Math.round(potential * 0.45), quickMin, structuralFloor);
  if (quickMax <= quickMin && structuralFloor > quickMin) quickMax = quickMin + 1;

  let pilotMin = clamp(Math.round(potential * 0.55), quickMax + 1, structuralFloor);
  let pilotMax = clamp(Math.round(potential * 0.75), pilotMin, structuralFloor);
  if (pilotMin > structuralFloor) pilotMin = structuralFloor;
  if (pilotMax < pilotMin) pilotMax = pilotMin;

  return {
    quickRange: { min: quickMin, max: quickMax },
    pilotRange: { min: pilotMin, max: pilotMax },
    structuralRangeLabel: `${formatNumber(potential, 1)}% proyectado`,
  };
}

function buildStrategicPlan(fuenteCritica, optimizedScenario) {
  const activityLabel = fuenteCritica || optimizedScenario?.targetSource || "la fuente prioritaria";
  const categoryLabel = optimizedScenario?.targetCategory || "la categoría crítica";
  const stageLabel = optimizedScenario?.targetStage || "la etapa prioritaria";
  const sourceKey = normalizePlanText(activityLabel);
  const potentialReduction = Number(optimizedScenario?.reductionPct || 0);
  const optimalActivityReduction = sourceKey === "diesel" ? Number(optimizedScenario?.dieselReduction || 0) : Number(optimizedScenario?.activityReduction || 0);

  let viability = "Alta";
  if (sourceKey.includes("diesel") || sourceKey.includes("hormigon") || sourceKey.includes("acero") || potentialReduction > 18) viability = "Media";
  if (potentialReduction > 32 || optimalActivityReduction >= 38) viability = "Baja";

  const actionRanges = buildProgressiveActionRanges(potentialReduction);
  const recommendedRange = actionRanges.pilotRange;
  const recommendedActions = Array.isArray(optimizedScenario?.recommendedActions) ? optimizedScenario.recommendedActions : [];
  const evidenceNeeded = Array.isArray(optimizedScenario?.evidenceNeeded) ? optimizedScenario.evidenceNeeded : [];
  const operationalNextStep = optimizedScenario?.operationalNextStep || `Validar datos y evidencia de ${activityLabel} antes de ejecutar una intervención.`;
  const principalRecommendation = potentialReduction > 0
    ? `El sistema detecta que ${categoryLabel} es el foco principal y que ${activityLabel} explica una parte relevante de la huella. Se recomienda partir con un piloto medible en ${stageLabel}, buscando una reducción inicial entre ${formatPercentRange(recommendedRange)} antes de escalar cambios estructurales.`
    : `Completar datos y validar factores antes de definir un piloto de reducción para ${activityLabel}.`;
  const optimalReference = potentialReduction > 0
    ? `El máximo potencial proyectado es de ${formatNumber(potentialReduction, 1)}%. Esta cifra debe usarse como referencia estratégica, no como promesa inmediata, porque depende de evidencia, proveedores, operación y validación técnica.`
    : "El máximo potencial proyectado debe tratarse como referencia estratégica de largo plazo, no como acción inmediata.";

  const actionLevels = [
    {
      label: "Acciones rápidas",
      range: formatPercentRange(actionRanges.quickRange),
      tone: "border-[var(--border)] bg-[var(--success-bg)] text-[var(--secondary)]",
      icon: Zap,
      iconTone: "green",
      detail: "Ajustes de bajo esfuerzo: depurar datos, separar fuentes, validar cantidades, asociar evidencia y corregir registros incompletos.",
    },
    {
      label: "Piloto recomendado",
      range: formatPercentRange(actionRanges.pilotRange),
      tone: "border-[#F6D98B] bg-[var(--warning-bg)] text-[#8A5A00]",
      icon: FlaskConical,
      iconTone: "amber",
      detail: "Intervención controlada sobre la fuente crítica. Permite medir impacto real antes de cambiar proveedores, especificaciones, rutas o procesos.",
    },
    {
      label: "Cambio estructural",
      range: actionRanges.structuralRangeLabel,
      tone: "border-[#F1C7C7] bg-[var(--danger-bg)] text-[#9A3412]",
      icon: Building2,
      iconTone: "red",
      detail: "Requiere decisiones de mayor alcance: cambio de proveedor, tecnología, diseño, especificación, logística o modelo operacional.",
    },
  ];

  return { viability, recommendedRange, principalRecommendation, optimalReference, actionLevels, recommendedActions, evidenceNeeded, operationalNextStep, categoryLabel, stageLabel };
}

function ExecutiveSummary({ fuenteCritica, unidadCritica, optimizedScenario, reductionEquivalentKm, riskProfile }) {
  const fuenteCriticaLabel = getExecutiveLabel(fuenteCritica, "Fuente crítica sin datos suficientes");
  const unidadCriticaLabel = getExecutiveLabel(unidadCritica, "Sin etapa suficiente");
  const hasValidOptimizedScenario = hasValidScenario(optimizedScenario);
  const scenarioForPlan = hasValidOptimizedScenario ? optimizedScenario : null;
  const strategicPlan = buildStrategicPlan(fuenteCriticaLabel, scenarioForPlan);
  const recommendedDecision = hasValidOptimizedScenario
    ? strategicPlan.principalRecommendation
    : "Completar registros, asociar etapas y validar factores de emisión antes de definir un porcentaje de reducción. Luego priorizar la fuente crítica detectada con acciones progresivas y medibles.";
  const currentTotal = Number(optimizedScenario?.currentTotal || 0);
  const simulatedTotal = hasValidOptimizedScenario ? Number(optimizedScenario?.simulatedTotal || 0) : 0;
  const avoidedEmissions = Math.max(currentTotal - simulatedTotal, 0);
  const equivalentCarKm = reductionEquivalentKm != null ? reductionEquivalentKm : avoidedEmissions * 4;
  const mediumImpactReductionPct = (strategicPlan.recommendedRange.min + strategicPlan.recommendedRange.max) / 2;
  const mediumImpactEstimatedTotal = Math.max(currentTotal * (1 - mediumImpactReductionPct / 100), 0);
  const estimatedImpact = hasValidOptimizedScenario
    ? `con un potencial proyectado de reducción del ${formatNumber(optimizedScenario.reductionPct, 1)}% en las emisiones totales bajo el escenario máximo.`
    : "Aún no existe un escenario de reducción calculado con datos suficientes.";
  const riskKpiTone = riskProfile.score > 70 ? "red" : riskProfile.score > 30 ? "amber" : "green";
  const viabilityTone = strategicPlan.viability === "Alta" ? "green" : strategicPlan.viability === "Media" ? "amber" : "red";
  const stageConcentrationLabel = getExecutiveLabel(riskProfile.factors.dominantStageLabel, unidadCriticaLabel);
  const stageConcentrationValue = Number(riskProfile.factors.stageConcentration || 0);
  const stageConcentrationDisplay = stageConcentrationValue > 0 ? `${stageConcentrationLabel} · ${formatNumber(stageConcentrationValue, 1)}%` : "Sin datos suficientes";
  const dieselLiters = Number(riskProfile.factors.dieselLiters || 0);
  const dieselDisplay = dieselLiters > 0 ? `${formatNumber(dieselLiters, 1)} litros` : "Sin consumo";
  const footprintPerM2 = Number(riskProfile.factors.footprintPerM2 || 0);
  const footprintPerM2Display = footprintPerM2 > 0 ? `${formatNumber(footprintPerM2, 2)} kgCO₂e/m²` : "Requiere m²";

  return (
    <section className="premium-card slide-up rounded-[20px] border border-[#E2E8F0] bg-[#F8FAFC] p-4 shadow-[0_8px_24px_rgba(15,23,42,0.04)] transition-colors duration-300 ease-out sm:p-6">
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full border border-[#99F6E4] bg-[#F0FDFA] text-[#0F766E] shadow-[0_8px_24px_rgba(15,23,42,0.04)]">
          <Settings size={18} strokeWidth={2.1} />
        </div>
        <p className="inline-flex w-fit items-center gap-2 rounded-full border border-[#99F6E4] bg-[#F0FDFA] px-3 py-1 text-sm font-bold text-[#0F766E] shadow-none transition duration-300 ease-out">Resumen ejecutivo</p>
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(340px,440px)] lg:items-start">
        <div className="max-w-3xl min-w-0">
          <h2 className="text-3xl font-black tracking-tight text-[#0F172A] sm:text-[2.05rem]">
            {hasValidOptimizedScenario ? `Potencial de reduccion del ${formatNumber(optimizedScenario.reductionPct, 1)}% con una reduccion progresiva en ${formatTitleCase(fuenteCriticaLabel)}` : `Priorizar intervención sobre ${fuenteCriticaLabel}`}
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[#64748B]">
            El principal foco de impacto se concentra en {formatFocusForSentence(fuenteCriticaLabel)}, siendo {unidadCriticaLabel} la etapa prioritaria. El nivel de viabilidad es <strong>{formatViabilityForSentence(strategicPlan.viability)}</strong>, {optimizedScenario ? estimatedImpact : "sin calcular."}
          </p>
        </div>

        <div className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-2">
          <ExecutiveKpiCard label="Riesgo" value={riskProfile.label} tone={riskKpiTone} icon={AlertTriangle} description={`Score : ${formatNumber(riskProfile.score, 0)} / 100`} className="h-full" />
          <ExecutiveKpiCard label="Viabilidad operativa" value={strategicPlan.viability} tone={viabilityTone} icon={ShieldCheck} description="Capacidad de ejecutar la mejora sin frenar la obra." className="h-full" />
        </div>
      </div>

      {hasValidOptimizedScenario && (
        <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3">
          <ExecutiveKpiCard label="Emisiones actuales" tone="red" icon={Cloud} value={`${formatNumber(currentTotal, 1)} kg CO2e`} description="Huella observada con los datos disponibles." />
          <ExecutiveKpiCard label="Escenario recomendado" tone="teal" icon={Leaf} value={`${formatNumber(mediumImpactEstimatedTotal, 1)} kg CO2e`} description="Escenario sugerido para reducción progresiva." />
          <ExecutiveKpiCard label="Máximo potencial proyectado" tone="green" icon={BarChart3} value={`${formatNumber(simulatedTotal, 1)} kg CO2e`} description="Referencia de mejora máxima bajo el caso ideal." />
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <ExecutiveKpiCard label="Foco principal" value={fuenteCriticaLabel} tone="slate" icon={Target} />
        <ExecutiveKpiCard label="Etapa prioritaria" value={unidadCriticaLabel} tone="blue" icon={Landmark} />
        <ExecutiveKpiCard label="Diésel consumido" value={dieselDisplay} tone={dieselLiters > 0 ? "amber" : "slate"} icon={Fuel} />
        <ExecutiveKpiCard label="Huella por m²" value={footprintPerM2Display} tone={footprintPerM2 > 0 ? "green" : "slate"} icon={Building2} />
      </div>

      <div className="mt-5 rounded-[20px] border border-[#99F6E4] border-l-4 border-l-[#2DD4BF] bg-[#F0FDFA]/70 p-5 shadow-[0_8px_24px_rgba(15,23,42,0.04)] transition-colors duration-300 ease-out hover:border-[#5EEAD4] hover:border-l-[#14B8A6]">
        <div className="flex items-start gap-4">
          <div className="shrink-0 rounded-full border border-[#99F6E4] bg-white p-3 text-[#0F766E]"><Lightbulb size={22} strokeWidth={2.1} /></div>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#0F766E]">Recomendación principal</p>
            <p className="mt-2 text-sm leading-6 text-[#334155]">{recommendedDecision}</p>
            <p className="mt-2 text-sm leading-6 text-[#334155]">{strategicPlan.optimalReference}</p>
          </div>
        </div>
      </div>

      <SpecificRecommendationPanel strategicPlan={strategicPlan} />

      <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-3">
        {strategicPlan.actionLevels.map((level) => (
          <div key={level.label} className={`rounded-[20px] border p-4 shadow-[0_8px_24px_rgba(15,23,42,0.04)] transition duration-300 ease-out hover:shadow-[0_10px_28px_rgba(15,23,42,0.05)] ${level.tone}`}>
            <div className="flex items-start gap-4">
              <KpiIcon icon={level.icon} tone={level.iconTone} />
              <div className="min-w-0 flex-1">
                <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#64748B]">{level.label}</p>
                <p className="mt-1 text-2xl font-black tracking-tight text-current">{level.range}</p>
                <p className="mt-2 text-sm leading-6 text-current/85 hyphens-auto">{level.detail}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-5 rounded-[20px] border border-[#E2E8F0] bg-white p-4 shadow-[0_8px_24px_rgba(15,23,42,0.04)] transition-[border-color,box-shadow] duration-300 ease-out hover:border-[#99F6E4]">
        <div className="flex items-center gap-3">
          <div className="rounded-full border border-[#E2E8F0] bg-[#F8FAFC] p-2 text-[#334155]"><FileText size={18} strokeWidth={2.1} /></div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#334155]">Factores del score</p>
        </div>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-5">
          <ScoreFactor label="Emisiones totales" value={riskProfile.factors.totalEmissions.label} tone="danger" />
          <ScoreFactor label="Fuente dominante" value={`${riskProfile.factors.dominantSourceLabel || "Sin datos"} · ${formatNumber(riskProfile.factors.dominantSourcePercentage ?? riskProfile.factors.sourceConcentration, 1)}%`} tone="warning" />
          <ScoreFactor label="Etapa dominante" value={stageConcentrationDisplay} tone="info" />
          <ScoreFactor label="Diésel consumido" value={dieselDisplay} tone={dieselLiters > 0 ? "warning" : "neutral"} />
          <ScoreFactor label="Huella por m²" value={footprintPerM2Display} tone={footprintPerM2 > 0 ? "success" : "neutral"} />
        </div>
      </div>

      <p className="mt-5 rounded-2xl border border-[#99F6E4] bg-[#F0FDFA] px-4 py-3 text-sm leading-6 text-[#334155] shadow-[0_8px_24px_rgba(15,23,42,0.04)] transition">
        Carbono Zero recomienda seguir este orden: primero validar la huella total, luego aislar el punto crítico, después confirmar la evidencia de {formatTitleCase(fuenteCriticaLabel)} y finalmente ejecutar un piloto medible en {unidadCriticaLabel}.
        {(optimizedScenario || reductionEquivalentKm != null) && ` Si la hoja de ruta se consolida por etapas, la reducción operativa estimada equivale aproximadamente a ${formatNumber(equivalentCarKm, 0)} km recorridos en auto.`}
      </p>
    </section>
  );
}

function SpecificRecommendationPanel({ strategicPlan }) {
  const actions = strategicPlan.recommendedActions || [];
  const evidence = strategicPlan.evidenceNeeded || [];
  if (!actions.length && !evidence.length) return null;

  return (
    <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-[1.1fr_0.9fr]">
      <section className="rounded-[22px] border border-emerald-200 bg-[linear-gradient(135deg,rgba(236,253,245,0.96),rgba(255,255,255,0.98))] p-5 shadow-[0_12px_30px_rgba(15,118,110,0.08)]">
        <div className="flex items-start gap-3">
          <div className="rounded-full border border-emerald-200 bg-white p-3 text-emerald-700"><Sparkles size={20} /></div>
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.2em] text-emerald-700">Recomendaciones específicas</p>
            <h3 className="mt-1 text-lg font-black text-[#0F172A]">Qué debería hacer la empresa ahora</h3>
          </div>
        </div>
        <div className="mt-4 space-y-2">
          {actions.map((action) => <div key={action} className="rounded-2xl border border-emerald-100 bg-white/80 p-3 text-sm font-semibold leading-6 text-[#334155]">{action}</div>)}
        </div>
      </section>

      <section className="rounded-[22px] border border-sky-200 bg-[linear-gradient(135deg,rgba(239,246,255,0.96),rgba(255,255,255,0.98))] p-5 shadow-[0_12px_30px_rgba(37,99,235,0.06)]">
        <div className="flex items-start gap-3">
          <div className="rounded-full border border-sky-200 bg-white p-3 text-sky-700"><FileText size={20} /></div>
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.2em] text-sky-700">Evidencia necesaria</p>
            <h3 className="mt-1 text-lg font-black text-[#0F172A]">Qué debe respaldar el usuario</h3>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {evidence.map((item) => <span key={item} className="rounded-full border border-sky-200 bg-white px-3 py-1 text-xs font-black text-sky-700">{formatTitleCase(item)}</span>)}
        </div>
        <div className="mt-4 rounded-2xl border border-sky-100 bg-white/80 p-3 text-sm font-semibold leading-6 text-[#334155]">{strategicPlan.operationalNextStep}</div>
      </section>
    </div>
  );
}

function ScoreFactor({ label, value, tone = "neutral", description }) {
  const toneDot = {
    neutral: "bg-[#64748B]",
    warning: "bg-[#B45309]",
    info: "bg-[#1D4ED8]",
    success: "bg-[#047857]",
    danger: "bg-[#B42318]",
  }[tone];

  return (
    <div className="rounded-[18px] border border-[#E2E8F0] bg-white px-4 py-3 text-center shadow-[0_8px_24px_rgba(15,23,42,0.04)] transition hover:border-[#CBD5E1]">
      <div className="flex items-center justify-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${toneDot}`} />
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#64748B]">{label}</p>
      </div>
      <p className="mt-1 break-words text-sm font-extrabold text-current">{value}</p>
      {description ? <p className="mt-1 text-[11px] font-medium leading-4 text-[#64748B]">{description}</p> : null}
    </div>
  );
}

export default ExecutiveSummary;
