function KpiCard({ detail, icon, title, tone, value }) {
  const semanticTone = (() => {
    const resolvedTitle = String(title || "").toLowerCase();

    if (typeof tone === "string") {
      return tone;
    }

    if (tone?.background || tone?.border || tone?.color) {
      return tone;
    }

    if (resolvedTitle.includes("riesgo") || resolvedTitle.includes("emisiones actuales") || resolvedTitle.includes("emisiones totales") || resolvedTitle.includes("fuente critica") || resolvedTitle.includes("categorÃ­a critica")) {
      return "danger";
    }

    if (resolvedTitle.includes("escenario recomendado") || resolvedTitle.includes("informaciÃ³n") || resolvedTitle.includes("operativa") || resolvedTitle.includes("intensidad de carbono") || resolvedTitle.includes("etapa prioritaria") || resolvedTitle.includes("modo de importaciÃ³n")) {
      return "info";
    }

    if (resolvedTitle.includes("mÃ¡ximo potencial") || resolvedTitle.includes("reducciÃ³n") || resolvedTitle.includes("viabilidad") || resolvedTitle.includes("potencial") ) {
      return "success";
    }

    if (resolvedTitle.includes("foco principal") || resolvedTitle.includes("diÃ©sel") || resolvedTitle.includes("concentraciÃ³n") || resolvedTitle.includes("prioritaria") || resolvedTitle.includes("obra critica") || resolvedTitle.includes("fuente prioritaria") || resolvedTitle.includes("perÃ­odo con mayor emision") || resolvedTitle.includes("modo de importaciÃ³n")) {
      return "warning";
    }

    return "neutral";
  })();

  const toneMap = {
    danger: {
      card: "border-[var(--kpi-danger-border)] bg-[var(--kpi-danger-bg)]",
      icon: "border-[var(--kpi-danger-border)] bg-white text-[var(--kpi-danger-text)]",
      title: "text-[var(--kpi-neutral-text)]",
      value: "text-[var(--kpi-danger-text)]",
      detail: "text-[var(--kpi-danger-text)]",
    },
    warning: {
      card: "border-[var(--kpi-warning-border)] bg-[var(--kpi-warning-bg)]",
      icon: "border-[var(--kpi-warning-border)] bg-white text-[var(--kpi-warning-text)]",
      title: "text-[var(--kpi-neutral-text)]",
      value: "text-[var(--kpi-warning-text)]",
      detail: "text-[var(--kpi-warning-text)]",
    },
    success: {
      card: "border-[var(--kpi-success-border)] bg-[var(--kpi-success-bg)]",
      icon: "border-[var(--kpi-success-border)] bg-white text-[var(--kpi-success-text)]",
      title: "text-[var(--kpi-neutral-text)]",
      value: "text-[var(--kpi-success-text)]",
      detail: "text-[var(--kpi-success-text)]",
    },
    info: {
      card: "border-[var(--kpi-info-border)] bg-[var(--kpi-info-bg)]",
      icon: "border-[var(--kpi-info-border)] bg-white text-[var(--kpi-info-text)]",
      title: "text-[var(--kpi-neutral-text)]",
      value: "text-[var(--kpi-info-text)]",
      detail: "text-[var(--kpi-info-text)]",
    },
    neutral: {
      card: "border-[var(--kpi-neutral-border)] bg-[var(--kpi-neutral-bg)]",
      icon: "border-[var(--kpi-neutral-border)] bg-white text-[var(--kpi-neutral-text)]",
      title: "text-[var(--kpi-neutral-text)]",
      value: "text-[var(--kpi-dark-text)]",
      detail: "text-[var(--kpi-neutral-text)]",
    },
  }[semanticTone] || {
    card: "border-[var(--kpi-neutral-border)] bg-[var(--kpi-neutral-bg)]",
    icon: "border-[var(--kpi-neutral-border)] bg-white text-[var(--kpi-neutral-text)]",
    title: "text-[var(--kpi-neutral-text)]",
    value: "text-[var(--kpi-dark-text)]",
    detail: "text-[var(--kpi-neutral-text)]",
  };

  const toneClasses = toneMap.card;
  const iconClasses = toneMap.icon;
  const titleClasses = toneMap.title;
  const valueClasses = toneMap.value;
  const detailClasses = toneMap.detail;

  return (
    <div className={`premium-card premium-card-interactive p-6 ring-1 ring-white/60 ${toneClasses}`}>
      <div className="mb-4 flex items-center gap-3">
        <div className={`flex h-11 w-11 items-center justify-center rounded-2xl border shadow-[0_10px_20px_rgba(15,23,42,0.06)] ${iconClasses}`}>
          {icon}
        </div>
        <p className={`text-sm font-bold ${titleClasses}`}>{title}</p>
      </div>
      <h3 className={`mt-1 text-2xl font-black tracking-tight ${valueClasses}`}>
        {value}
      </h3>
      {detail && (
        <p className={`mt-2 text-sm font-semibold ${detailClasses}`}>
          {detail}
        </p>
      )}
    </div>
  );
}

export default KpiCard;
