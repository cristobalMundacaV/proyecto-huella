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
    color: "#E11D48",
  },
  Materiales: {
    icon: Boxes,
    tone: "warning",
    description: "Carbono incorporado",
    color: "#EA580C",
  },
  Transporte: {
    icon: Route,
    tone: "info",
    description: "Traslados y logística",
    color: "#2563EB",
  },
  Maquinaria: {
    icon: Factory,
    tone: "lime",
    description: "Equipos y faena",
    color: "#65A30D",
  },
  Energia: {
    icon: Zap,
    tone: "violet",
    description: "Electricidad y combustibles",
    color: "#7C3AED",
  },
  Agua: {
    icon: Droplets,
    tone: "cyan",
    description: "Consumo hídrico",
    color: "#0891B2",
  },
  Residuos: {
    icon: Recycle,
    tone: "success",
    description: "Retiro y disposición",
    color: "#059669",
  },
  Otros: {
    icon: Layers3,
    tone: "neutral",
    description: "Registros no clasificados",
    color: "#475569",
  },
};

function EstadoEmisionesTab({ selectedObra }) {
  const registros = selectedObra?.registros_emision || [];
  const totals = buildCategoryEmissionTotals(registros, selectedObra);
  const totalEmissions = Number(totals.Todas || 0);
  const categoryRows = buildCategoryRows(totals, totalEmissions);
  const donutRows = categoryRows.filter((row) => row.category !== "Todas" && row.emissions > 0);

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
            Lectura consolidada de la obra seleccionada. Las categorías se ordenan desde la mayor contribución de emisiones hasta la menor para evidenciar dónde está el foco ambiental real.
          </p>
        </div>
        <div className="rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] px-4 py-3 text-sm font-black text-[#075985]">
          {formatNumber(registros.length, 0)} registros
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {categoryRows.map((row) => {
          const Icon = row.config.icon || Activity;

          return (
            <EmissionCategoryKpi
              key={row.category}
              detail={`${formatNumber(row.share, 1)}% de la obra`}
              icon={<Icon />}
              label={row.category === "Todas" ? "Todas las emisiones" : row.category}
              note={row.config.description}
              tone={row.config.tone}
              value={`${formatNumber(row.emissions, 1)} kg CO2e`}
            />
          );
        })}
      </div>

      <EmissionDonutChart rows={donutRows} totalEmissions={totalEmissions} />
    </section>
  );
}

function buildCategoryRows(totals, totalEmissions) {
  return emissionCategories
    .map((category, index) => {
      const emissions = Number(totals[category] || 0);
      return {
        category,
        config: categoryConfig[category] || categoryConfig.Otros,
        emissions,
        originalIndex: index,
        share: totalEmissions > 0 ? (emissions / totalEmissions) * 100 : 0,
      };
    })
    .sort((left, right) => {
      if (left.category === "Todas") return -1;
      if (right.category === "Todas") return 1;
      return right.emissions - left.emissions || left.originalIndex - right.originalIndex;
    });
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

function EmissionDonutChart({ rows, totalEmissions }) {
  const radius = 78;
  const circumference = 2 * Math.PI * radius;
  const donutRows = rows.reduce((segments, row) => {
    const dash = totalEmissions > 0 ? (row.emissions / totalEmissions) * circumference : 0;
    const previous = segments.at(-1);
    return [...segments, { ...row, dash, offset: previous ? previous.offset + previous.dash : 0 }];
  }, []);
  const mainCategory = rows[0];

  return (
    <section className="mt-6 rounded-3xl border border-[var(--border)] bg-[linear-gradient(135deg,#FFFFFF_0%,#F8FAFC_48%,#ECFDF3_100%)] p-4 shadow-[0_14px_34px_rgba(15,23,42,0.06)] sm:p-6">
      <div className="mb-5 flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-[var(--primary-dark)]">
            Lectura visual
          </p>
          <h3 className="mt-1 text-2xl font-bold text-[var(--text-main)]">
            Participación de emisiones por categoría
          </h3>
          <p className="mt-1 max-w-3xl text-sm font-medium leading-6 text-[var(--text-muted)]">
            El gráfico resume la distribución real de la huella. Cuando una categoría domina la dona, esa categoría debe ser el primer foco operativo.
          </p>
        </div>
        {mainCategory && (
          <div className="rounded-2xl border border-[#FDBA74] bg-[#FFF7ED] px-4 py-3 text-sm font-black text-[#C2410C]">
            Foco principal: {mainCategory.category}
          </div>
        )}
      </div>

      {rows.length ? (
        <div className="grid grid-cols-1 items-center gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
          <div className="relative mx-auto flex h-[300px] w-full max-w-[340px] items-center justify-center">
            <svg viewBox="0 0 220 220" className="h-[280px] w-[280px] -rotate-90 overflow-visible">
              <circle
                cx="110"
                cy="110"
                fill="none"
                r={radius}
                stroke="#E2E8F0"
                strokeWidth="28"
              />
              {donutRows.map((row) => (
                  <circle
                    key={row.category}
                    cx="110"
                    cy="110"
                    fill="none"
                    r={radius}
                    stroke={row.config.color}
                    strokeDasharray={`${row.dash} ${circumference}`}
                    strokeDashoffset={-row.offset}
                    strokeLinecap="butt"
                    strokeWidth="28"
                  />
              ))}
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
              <p className="text-xs font-black uppercase tracking-[0.14em] text-[var(--text-muted)]">
                Total obra
              </p>
              <p className="mt-1 text-2xl font-black text-[var(--text-main)]">
                {formatNumber(totalEmissions, 1)}
              </p>
              <p className="text-sm font-bold text-[var(--text-muted)]">kg CO2e</p>
            </div>
          </div>

          <div className="space-y-3">
            {rows.map((row) => (
              <div
                key={row.category}
                className="rounded-2xl border border-[var(--border)] bg-white/85 p-4 shadow-[0_8px_22px_rgba(15,23,42,0.04)]"
              >
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <span
                      className="h-3.5 w-3.5 rounded-full shadow-[0_0_0_4px_rgba(15,23,42,0.04)]"
                      style={{ backgroundColor: row.config.color }}
                    />
                    <div>
                      <p className="font-black text-[var(--text-main)]">{row.category}</p>
                      <p className="text-xs font-semibold text-[var(--text-muted)]">{row.config.description}</p>
                    </div>
                  </div>
                  <div className="text-left sm:text-right">
                    <p className="font-black text-[#075985]">{formatNumber(row.emissions, 1)} kg CO2e</p>
                    <p className="text-xs font-bold text-[var(--text-muted)]">{formatNumber(row.share, 1)}%</p>
                  </div>
                </div>
                <div className="mt-3 h-2 rounded-full bg-[#E2E8F0]">
                  <div
                    className="h-2 rounded-full"
                    style={{
                      backgroundColor: row.config.color,
                      width: `${Math.max(0, Math.min(100, row.share))}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="rounded-2xl border border-dashed border-[var(--border)] bg-white p-6 text-center text-sm font-semibold text-[var(--text-muted)]">
          Aún no hay emisiones suficientes para construir la distribución por categoría.
        </p>
      )}
    </section>
  );
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
