import { Activity, BarChart3, Boxes, Building2 } from "lucide-react";
import { formatNumber } from "@/shared/utils/formatters";

function ObrasKpis({ obras, selectedObra, totalEmisiones }) {
  const obraConMasEmisiones = obras.reduce((topObra, obra) => {
    if (!topObra) {
      return obra;
    }

    return Number(obra.emisiones_kg_co2e || 0) > Number(topObra.emisiones_kg_co2e || 0)
      ? obra
      : topObra;
  }, null);
  const selectedOrTopObra = selectedObra || obraConMasEmisiones || obras[0] || null;
  const selectedEmissions = Number(selectedOrTopObra?.emisiones_kg_co2e || 0);
  const selectedSurface = Number(selectedOrTopObra?.superficie_m2 || 0);
  const selectedIntensity = selectedSurface > 0 ? selectedEmissions / selectedSurface : null;

  return (
    <section className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
      <ObraKpiCard
        icon={<Boxes />}
        label="Total de obras"
        tone="success"
        value={formatNumber(obras.length, 0)}
      />
      <ObraKpiCard
        detail={`${formatNumber(obraConMasEmisiones?.emisiones_kg_co2e || 0, 1)} kg CO2e`}
        icon={<Building2 />}
        label="Obra con más emisiones"
        tone="warning"
        value={obraConMasEmisiones?.nombre || obraConMasEmisiones?.codigo_obra || "Sin datos"}
      />
      <ObraKpiCard
        detail={selectedOrTopObra?.nombre || selectedOrTopObra?.codigo_obra || "Obra seleccionada"}
        icon={<BarChart3 />}
        label="kg CO2e/m²"
        tone="info"
        value={
          selectedIntensity != null
            ? `${formatNumber(selectedIntensity, 2)} kg CO2e/m²`
            : "Sin superficie"
        }
      />
      <ObraKpiCard
        detail={selectedOrTopObra?.nombre || selectedOrTopObra?.codigo_obra || "Obra seleccionada"}
        icon={<Activity />}
        label="Emisiones asociadas a la obra"
        tone="danger"
        value={`${formatNumber(selectedEmissions || totalEmisiones || 0, 1)} kg CO2e`}
      />
    </section>
  );
}

function ObraKpiCard({ detail, icon, label, tone = "neutral", value }) {
  const toneClasses = getObraKpiTone(tone);

  return (
    <div className={`premium-card-interactive relative flex min-h-[220px] overflow-hidden rounded-[26px] border p-6 shadow-[0_18px_45px_rgba(15,23,42,0.10)] ring-1 ring-white/80 transition duration-300 hover:-translate-y-1 hover:shadow-[0_24px_60px_rgba(15,23,42,0.16)] ${toneClasses.card}`}>
      <div className={`absolute inset-x-7 top-0 h-1.5 rounded-b-full ${toneClasses.accent}`} />
      <div className={`pointer-events-none absolute -right-12 -top-12 h-36 w-36 rounded-full blur-3xl ${toneClasses.glow}`} />
      <div className={`pointer-events-none absolute -bottom-14 -left-14 h-32 w-32 rounded-full blur-3xl ${toneClasses.softGlow}`} />

      <div className="relative z-10 flex w-full flex-col items-center text-center">
        <div className={`flex h-14 w-14 items-center justify-center rounded-2xl border shadow-[0_12px_28px_rgba(15,23,42,0.08)] ${toneClasses.icon}`}>
          {icon}
        </div>
        <div className="mt-4 flex min-h-[34px] items-center justify-center">
          <p className={`text-[11px] font-black uppercase tracking-[0.14em] ${toneClasses.title}`}>
            {label}
          </p>
        </div>
        <div className="flex flex-1 items-center justify-center py-3">
          <h3 className={`mx-auto max-w-[290px] break-words text-center text-[clamp(1.55rem,2.5vw,2.25rem)] font-black leading-tight tracking-tight ${toneClasses.value}`}>
            {value || "Sin datos"}
          </h3>
        </div>
        {detail && (
          <p className={`text-center text-sm font-bold ${toneClasses.detail}`}>
            {detail}
          </p>
        )}
      </div>
    </div>
  );
}

function getObraKpiTone(tone) {
  const tones = {
    success: {
      card: "border-[#86EFAC] bg-[linear-gradient(135deg,#ECFDF3_0%,#FFFFFF_48%,#DCFCE7_100%)]",
      icon: "border-[#86EFAC] bg-white text-[#047857]",
      title: "text-[#64748B]",
      value: "text-[#047857]",
      detail: "text-[#047857]",
      accent: "bg-[#059669]",
      glow: "bg-emerald-200/70",
      softGlow: "bg-green-100/70",
    },
    warning: {
      card: "border-[#FDBA74] bg-[linear-gradient(135deg,#FFF7ED_0%,#FFFFFF_48%,#FFEDD5_100%)]",
      icon: "border-[#FDBA74] bg-white text-[#C2410C]",
      title: "text-[#64748B]",
      value: "text-[#C2410C]",
      detail: "text-[#B45309]",
      accent: "bg-[#EA580C]",
      glow: "bg-orange-200/70",
      softGlow: "bg-amber-100/70",
    },
    info: {
      card: "border-[#93C5FD] bg-[linear-gradient(135deg,#EFF6FF_0%,#FFFFFF_48%,#DBEAFE_100%)]",
      icon: "border-[#93C5FD] bg-white text-[#1D4ED8]",
      title: "text-[#64748B]",
      value: "text-[#1D4ED8]",
      detail: "text-[#1D4ED8]",
      accent: "bg-[#2563EB]",
      glow: "bg-blue-200/70",
      softGlow: "bg-sky-100/70",
    },
    danger: {
      card: "border-[#FDA4AF] bg-[linear-gradient(135deg,#FFF1F2_0%,#FFFFFF_46%,#FFE4E6_100%)]",
      icon: "border-[#FDA4AF] bg-white text-[#BE123C]",
      title: "text-[#64748B]",
      value: "text-[#BE123C]",
      detail: "text-[#9F1239]",
      accent: "bg-[#E11D48]",
      glow: "bg-rose-200/70",
      softGlow: "bg-red-100/70",
    },
    neutral: {
      card: "border-[#CBD5E1] bg-[linear-gradient(135deg,#FFFFFF_0%,#F8FAFC_48%,#E2E8F0_100%)]",
      icon: "border-[#CBD5E1] bg-white text-[#334155]",
      title: "text-[#64748B]",
      value: "text-[#334155]",
      detail: "text-[#64748B]",
      accent: "bg-[#475569]",
      glow: "bg-slate-200/70",
      softGlow: "bg-slate-100/70",
    },
  };

  return tones[tone] || tones.neutral;
}

export default ObrasKpis;
