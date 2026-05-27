function KpiCard({ detail, icon, title, tone, value }) {
  const semanticTone = (() => {
    const resolvedTitle = String(title || "").toLowerCase();

    if (typeof tone === "string") {
      return tone;
    }

    if (tone?.background || tone?.border || tone?.color) {
      return tone;
    }

    if (resolvedTitle.includes("riesgo") || resolvedTitle.includes("emisiones actuales") || resolvedTitle.includes("emisiones totales") || resolvedTitle.includes("fuente critica") || resolvedTitle.includes("categorí­a critica")) {
      return "danger";
    }

    if (resolvedTitle.includes("escenario recomendado") || resolvedTitle.includes("información") || resolvedTitle.includes("operativa") || resolvedTitle.includes("intensidad de carbono") || resolvedTitle.includes("etapa prioritaria") || resolvedTitle.includes("modo de importación")) {
      return "info";
    }

    if (resolvedTitle.includes("máximo potencial") || resolvedTitle.includes("reducción") || resolvedTitle.includes("viabilidad") || resolvedTitle.includes("potencial") ) {
      return "success";
    }

    if (resolvedTitle.includes("diésel") || resolvedTitle.includes("concentración") || resolvedTitle.includes("prioritaria") || resolvedTitle.includes("obra critica") || resolvedTitle.includes("fuente prioritaria") || resolvedTitle.includes("perí­odo con mayor emision") || resolvedTitle.includes("modo de importación")) {
      return "warning";
    }

    return "neutral";
  })();

  const toneMap = {
    danger: {
      card: "border-[#FDA29B] bg-[#FEF3F2]",
      icon: "border-[#FDA29B] bg-white text-[#B42318]",
      title: "text-[#64748B]",
      value: "text-[#B42318]",
      detail: "text-[#B42318]",
    },
    warning: {
      card: "border-[#FDBA74] bg-[#FFF7ED]",
      icon: "border-[#FDBA74] bg-white text-[#B45309]",
      title: "text-[#64748B]",
      value: "text-[#B45309]",
      detail: "text-[#B45309]",
    },
    success: {
      card: "border-[#A7F3D0] bg-[#ECFDF3]",
      icon: "border-[#A7F3D0] bg-white text-[#047857]",
      title: "text-[#64748B]",
      value: "text-[#047857]",
      detail: "text-[#047857]",
    },
    info: {
      card: "border-[#BFDBFE] bg-[#EFF6FF]",
      icon: "border-[#BFDBFE] bg-white text-[#1D4ED8]",
      title: "text-[#64748B]",
      value: "text-[#1D4ED8]",
      detail: "text-[#1D4ED8]",
    },
    neutral: {
      card: "border-[#E2E8F0] bg-white",
      icon: "border-[#E2E8F0] bg-[#F8FAFC] text-[#334155]",
      title: "text-[#64748B]",
      value: "text-[#334155]",
      detail: "text-[#64748B]",
    },
  }[semanticTone] || {
    card: "border-[#E2E8F0] bg-white",
    icon: "border-[#E2E8F0] bg-[#F8FAFC] text-[#334155]",
    title: "text-[#64748B]",
    value: "text-[#334155]",
    detail: "text-[#64748B]",
  };

  const toneClasses = toneMap.card;
  const iconClasses = toneMap.icon;
  const titleClasses = toneMap.title;
  const valueClasses = toneMap.value;
  const detailClasses = toneMap.detail;

  return (
    <div className={`rounded-[18px] p-6 shadow-[0_8px_24px_rgba(15,23,42,0.04)] ring-1 ring-white/60 ${toneClasses}`}>
      <div className="mb-4 flex flex-col items-center text-center">
        <div className={`flex h-11 w-11 items-center justify-center rounded-2xl border shadow-[0_8px_24px_rgba(15,23,42,0.04)] ${iconClasses}`}>
          {icon}
        </div>
        <p className={`mt-3 text-sm font-bold ${titleClasses}`}>{title}</p>
      </div>
      <h3 className={`mt-1 text-center text-2xl font-black tracking-tight ${valueClasses}`}>
        {value}
      </h3>
      {detail && (
        <p className={`mt-2 text-center text-sm font-semibold ${detailClasses}`}>
          {detail}
        </p>
      )}
    </div>
  );
}

export default KpiCard;
