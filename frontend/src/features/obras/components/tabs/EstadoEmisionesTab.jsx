import {
  Activity,
  Boxes,
  Droplets,
  Factory,
  Gauge,
  Layers3,
  Recycle,
  Route,
  Zap,
} from "lucide-react";

import { formatNumber } from "@/shared/utils/formatters";
import {
  constructionCategories,
  getConstructionCategoryLabel,
} from "@/features/obras/utils/constructionEmissionCategories";

const emissionCategories = ["Todas", ...constructionCategories];

const categoryConfig = {
  Todas: {
    icon: Gauge,
    tone: "danger",
    description: "Huella acumulada de la obra",
  },
  Materiales: {
    icon: Boxes,
    tone: "warning",
    description: "Carbono incorporado",
  },
  Transporte: {
    icon: Route,
    tone: "info",
    description: "Traslados y logística",
  },
  Maquinaria: {
    icon: Factory,
    tone: "lime",
    description: "Equipos y faena",
  },
  Energia: {
    icon: Zap,
    tone: "violet",
    description: "Electricidad y combustibles",
  },
  Agua: {
    icon: Droplets,
    tone: "cyan",
    description: "Consumo hídrico",
  },
  Residuos: {
    icon: Recycle,
    tone: "success",
    description: "Retiro y disposición",
  },
  Otros: {
    icon: Layers3,
    tone: "neutral",
    description: "Registros no clasificados",
  },
};

function EstadoEmisionesTab({ selectedObra }) {
  const registros = selectedObra?.registros_emision || [];
  const totals = buildCategoryEmissionTotals(registros, selectedObra);
  const totalEmissions = Number(totals.Todas || 0);

  return (
    <section className="premium-card premium-card-interactive rounded-3xl bg-[var(--bg-card)] p-4 shadow-[var(--shadow-card)] sm:p-6">
      <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-[var(--primary-dark)]">
            Estado de emisiones
          </p>
          <h2 className="mt-1 text-2xl font-bold text-[var(--text-main)]">
            Distribución ambiental por categoría
          </h2>
          <p className="mt-1 max-w-4xl text-sm font-medium leading-6 text-[var(--text-muted)]">
            Lectura consolidada de la obra seleccionada. Cada KPI resume cuánto aporta una categoría a la huella total para decidir dónde priorizar acciones.
          </p>
        </div>
        <div className="rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] px-4 py-3 text-sm font-black text-[#075985]">
          {formatNumber(registros.length, 0)} registros
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {emissionCategories.map((category) => {
          const emissions = Number(totals[category] || 0);
          const share = totalEmissions > 0 ? (emissions / totalEmissions) * 100 : 0;
          const config = categoryConfig[category] || categoryConfig.Otros;
          const Icon = config.icon || Activity;

          return (
            <EmissionCategoryKpi
              key={category}
              detail={`${formatNumber(share, 1)}% de la obra`}
              icon={<Icon />}
              label={category === "Todas" ? "Todas las emisiones" : category}
              note={config.description}
              tone={config.tone}
              value={`${formatNumber(emissions, 1)} kg CO2e`}
            />
          );
        })}
      </div>
    </section>
  );
}

function buildCategoryEmissionTotals(registros, selectedObra) {
  const totals = emissionCategories.reduce((acc, category) => {
    acc[category] = 0;
    return acc;
  }, {});

  registros.forEach((registro) => {
    const category = getConstructionCategoryLabel(
      registro.categoria,
      registro.fuente_emision
    );
    const normalizedCategory = constructionCategories.includes(category) ? category : "Otros";
    const emissions = Number(registro.emisiones_kg_co2e || registro.emisiones || 0);

    totals[normalizedCategory] += emissions;
    totals.Todas += emissions;
  });

  if (!totals.Todas && selectedObra?.emisiones_kg_co2e) {
    totals.Todas = Number(selectedObra.emisiones_kg_co2e || 0);
  }

  return totals;
}

function EmissionCategoryKpi({ detail, icon, label, note, tone = "neutral", value }) {
  const toneClasses = getEmissionTone(tone);

  return (
    <div className={`premium-card-interactive relative flex min-h-[185px] overflow-hidden rounded-[24px] border p-5 shadow-[0_14px_34px_rgba(15,23,42,0.08)] ring-1 ring-white/75 transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_20px_45px_rgba(15,23,42,0.13)] ${toneClasses.card}`}>
      <div className={`absolute inset-x-6 top-0 h-1.5 rounded-b-full ${toneClasses.accent}`} />
      <div className={`pointer-events-none absolute -right-10 -top-12 h-32 w-32 rounded-full blur-3xl ${toneClasses.glow}`} />
      <div className="relative z-10 flex w-full flex-col items-center text-center">
        <div className={`flex h-11 w-11 items-center justify-center rounded-2xl border shadow-[0_10px_24px_rgba(15,23,42,0.06)] ${toneClasses.icon}`}>
          {icon}
        </div>
        <p className={`mt-3 text-[11px] font-black uppercase tracking-[0.12em] ${toneClasses.title}`}>
          {label}
        </p>
        <div className="flex flex-1 items-center justify-center py-2">
          <h3 className={`mx-auto max-w-[260px] break-words text-center text-[clamp(1.2rem,2vw,1.65rem)] font-black leading-tight ${toneClasses.value}`}>
            {value}
          </h3>
        </div>
        <p className={`text-xs font-bold ${toneClasses.detail}`}>{detail}</p>
        <p className="mt-1 text-[11px] font-semibold text-[var(--text-muted)]">{note}</p>
      </div>
    </div>
  );
}

function getEmissionTone(tone) {
  const tones = {
    danger: {
      card: "border-[#FDA4AF] bg-[linear-gradient(135deg,#FFF1F2_0%,#FFFFFF_48%,#FFE4E6_100%)]",
      icon: "border-[#FDA4AF] bg-white text-[#BE123C]",
      title: "text-[#64748B]",
      value: "text-[#BE123C]",
      detail: "text-[#9F1239]",
      accent: "bg-[#E11D48]",
      glow: "bg-rose-200/70",
    },
    warning: {
      card: "border-[#FDBA74] bg-[linear-gradient(135deg,#FFF7ED_0%,#FFFFFF_48%,#FFEDD5_100%)]",
      icon: "border-[#FDBA74] bg-white text-[#C2410C]",
      title: "text-[#64748B]",
      value: "text-[#C2410C]",
      detail: "text-[#B45309]",
      accent: "bg-[#EA580C]",
      glow: "bg-orange-200/70",
    },
    info: {
      card: "border-[#93C5FD] bg-[linear-gradient(135deg,#EFF6FF_0%,#FFFFFF_48%,#DBEAFE_100%)]",
      icon: "border-[#93C5FD] bg-white text-[#1D4ED8]",
      title: "text-[#64748B]",
      value: "text-[#1D4ED8]",
      detail: "text-[#1D4ED8]",
      accent: "bg-[#2563EB]",
      glow: "bg-blue-200/70",
    },
    lime: {
      card: "border-[#BEF264] bg-[linear-gradient(135deg,#F7FEE7_0%,#FFFFFF_48%,#ECFCCB_100%)]",
      icon: "border-[#BEF264] bg-white text-[#3F6212]",
      title: "text-[#64748B]",
      value: "text-[#3F6212]",
      detail: "text-[#4D7C0F]",
      accent: "bg-[#65A30D]",
      glow: "bg-lime-200/70",
    },
    violet: {
      card: "border-[#C4B5FD] bg-[linear-gradient(135deg,#F5F3FF_0%,#FFFFFF_48%,#EDE9FE_100%)]",
      icon: "border-[#C4B5FD] bg-white text-[#6D28D9]",
      title: "text-[#64748B]",
      value: "text-[#6D28D9]",
      detail: "text-[#6D28D9]",
      accent: "bg-[#7C3AED]",
      glow: "bg-violet-200/70",
    },
    cyan: {
      card: "border-[#67E8F9] bg-[linear-gradient(135deg,#ECFEFF_0%,#FFFFFF_48%,#CFFAFE_100%)]",
      icon: "border-[#67E8F9] bg-white text-[#0E7490]",
      title: "text-[#64748B]",
      value: "text-[#0E7490]",
      detail: "text-[#0E7490]",
      accent: "bg-[#0891B2]",
      glow: "bg-cyan-200/70",
    },
    success: {
      card: "border-[#86EFAC] bg-[linear-gradient(135deg,#ECFDF3_0%,#FFFFFF_48%,#DCFCE7_100%)]",
      icon: "border-[#86EFAC] bg-white text-[#047857]",
      title: "text-[#64748B]",
      value: "text-[#047857]",
      detail: "text-[#047857]",
      accent: "bg-[#059669]",
      glow: "bg-emerald-200/70",
    },
    neutral: {
      card: "border-[#CBD5E1] bg-[linear-gradient(135deg,#FFFFFF_0%,#F8FAFC_48%,#E2E8F0_100%)]",
      icon: "border-[#CBD5E1] bg-white text-[#334155]",
      title: "text-[#64748B]",
      value: "text-[#334155]",
      detail: "text-[#64748B]",
      accent: "bg-[#475569]",
      glow: "bg-slate-200/70",
    },
  };

  return tones[tone] || tones.neutral;
}

export default EstadoEmisionesTab;
