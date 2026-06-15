import { useEffect, useMemo, useState } from "react";

import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { getConstructoraDashboard } from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";

function normalizeKpiTitle(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function normalizeText(value) {
  return normalizeKpiTitle(value).trim();
}

function getKpiOrder(title) {
  const resolvedTitle = normalizeKpiTitle(title);

  if (resolvedTitle.includes("emisiones totales")) return "order-1";
  if (resolvedTitle.includes("evidencia respaldada")) return "order-2";
  if (resolvedTitle.includes("intensidad de carbono")) return "order-3";
  if (resolvedTitle.includes("obra critica")) return "order-4";
  if (resolvedTitle.includes("fuente critica")) return "order-5";
  if (resolvedTitle.includes("categoria critica")) return "order-6";

  return "";
}

function isNumericIdentifier(value) {
  return /^\d+(\.\d+)?$/.test(String(value ?? "").trim());
}

function isPendingValue(value) {
  const normalized = normalizeText(value);
  return normalized.includes("pendiente") || normalized.includes("sin datos");
}

function formatEvidencePercentage(value) {
  const numericValue = Number(value);

  if (!Number.isFinite(numericValue)) {
    return "0%";
  }

  return `${formatNumber(Math.max(0, Math.min(100, numericValue)), 0)}%`;
}

function buildEvidenceValue(dashboardData) {
  const coverage = Number(dashboardData?.evidencia_respaldada);
  const evidenceCount = Number(
    dashboardData?.evidencias_count ??
    dashboardData?.total_evidencias ??
    dashboardData?.evidencias_asociadas ??
    0
  );
  const recordsCount = Number(
    dashboardData?.registros_count ??
    dashboardData?.total_registros ??
    (Array.isArray(dashboardData?.datos) ? dashboardData.datos.length : 0)
  );

  if (Number.isFinite(coverage)) {
    return `${formatEvidencePercentage(coverage)} respaldada`;
  }

  if (evidenceCount > 0 && recordsCount > 0) {
    return `${formatEvidencePercentage((evidenceCount / recordsCount) * 100)} respaldada`;
  }

  if (evidenceCount > 0) {
    return `${formatNumber(evidenceCount, 0)} evidencias cargadas`;
  }

  return "0% respaldada";
}

function buildIntensityValue(dashboardData) {
  const backendIntensity = Number(dashboardData?.intensidad_carbono);

  if (Number.isFinite(backendIntensity) && backendIntensity > 0) {
    return `${formatNumber(backendIntensity, 2)} kg CO2e/m²`;
  }

  const totalEmissions = Number(
    dashboardData?.total_emisiones ?? dashboardData?.emisiones_totales ?? 0
  );
  const obras = Array.isArray(dashboardData?.obras) ? dashboardData.obras : [];
  const totalSurface = obras.reduce(
    (total, obra) => total + Number(obra?.superficie_m2 || obra?.superficie || 0),
    0
  );

  if (totalEmissions > 0 && totalSurface > 0) {
    return `${formatNumber(totalEmissions / totalSurface, 2)} kg CO2e/m²`;
  }

  if (totalEmissions > 0) {
    return "Superficie en revisión";
  }

  return "Sin emisiones registradas";
}

function resolveDashboardKpiValue({ dashboardData, isCriticalWorkCard, isEvidenceCard, isIntensityCard, value }) {
  if (isCriticalWorkCard && isNumericIdentifier(value)) {
    return dashboardData?.obra_critica || "";
  }

  if (isEvidenceCard && isPendingValue(value)) {
    return buildEvidenceValue(dashboardData);
  }

  if (isIntensityCard && isPendingValue(value)) {
    return buildIntensityValue(dashboardData);
  }

  return "";
}

function KpiCard({ detail, icon, title, tone, value }) {
  const { activeConstructoraId } = useConstructoraActiva();
  const [resolvedDashboardValue, setResolvedDashboardValue] = useState("");
  const normalizedTitle = useMemo(() => normalizeKpiTitle(title), [title]);
  const isCriticalWorkCard = normalizedTitle.includes("obra critica");
  const isEvidenceCard = normalizedTitle.includes("evidencia respaldada");
  const isIntensityCard = normalizedTitle.includes("intensidad de carbono");
  const shouldResolveFromDashboard =
    (isCriticalWorkCard && isNumericIdentifier(value)) ||
    (isEvidenceCard && isPendingValue(value)) ||
    (isIntensityCard && isPendingValue(value));

  useEffect(() => {
    if (!shouldResolveFromDashboard || !activeConstructoraId) {
      setResolvedDashboardValue("");
      return undefined;
    }

    let isCancelled = false;

    getConstructoraDashboard(activeConstructoraId, { light: "1" })
      .then((dashboardData) => {
        if (isCancelled) return;
        setResolvedDashboardValue(
          resolveDashboardKpiValue({
            dashboardData,
            isCriticalWorkCard,
            isEvidenceCard,
            isIntensityCard,
            value,
          })
        );
      })
      .catch(() => {
        if (!isCancelled) setResolvedDashboardValue("");
      });

    return () => {
      isCancelled = true;
    };
  }, [
    activeConstructoraId,
    isCriticalWorkCard,
    isEvidenceCard,
    isIntensityCard,
    shouldResolveFromDashboard,
    value,
  ]);

  const displayValue = (() => {
    if (resolvedDashboardValue) {
      return resolvedDashboardValue;
    }

    if (isEvidenceCard && typeof value === "number") {
      return `${formatEvidencePercentage(value)} respaldada`;
    }

    if (isEvidenceCard && /^\d+(\.\d+)?$/.test(String(value ?? "").trim())) {
      return `${formatEvidencePercentage(value)} respaldada`;
    }

    return value;
  })();

  const semanticTone = (() => {
    if (typeof tone === "string") {
      return tone;
    }

    if (tone?.background || tone?.border || tone?.color) {
      return tone;
    }

    if (normalizedTitle.includes("emisiones totales") || normalizedTitle.includes("emisiones actuales")) {
      return "danger";
    }

    if (normalizedTitle.includes("evidencia respaldada") || normalizedTitle.includes("maximo potencial") || normalizedTitle.includes("reduccion") || normalizedTitle.includes("viabilidad") || normalizedTitle.includes("potencial")) {
      return "success";
    }

    if (normalizedTitle.includes("intensidad de carbono") || normalizedTitle.includes("escenario recomendado") || normalizedTitle.includes("informacion") || normalizedTitle.includes("operativa") || normalizedTitle.includes("etapa prioritaria")) {
      return "info";
    }

    if (normalizedTitle.includes("obra critica") || normalizedTitle.includes("diesel") || normalizedTitle.includes("concentracion") || normalizedTitle.includes("prioritaria") || normalizedTitle.includes("fuente prioritaria") || normalizedTitle.includes("periodo con mayor emision")) {
      return "warning";
    }

    if (normalizedTitle.includes("riesgo") || normalizedTitle.includes("fuente critica")) {
      return "danger";
    }

    if (normalizedTitle.includes("categoria critica")) {
      return "violet";
    }

    return "neutral";
  })();

  const toneMap = {
    danger: {
      card: "border-[#FDA29B] bg-[linear-gradient(180deg,#FFF1F3,#FFFFFF)] before:bg-[#E11D48]",
      icon: "border-[#FDA29B] bg-white text-[#BE123C]",
      title: "text-[#64748B]",
      value: "text-[#BE123C]",
      detail: "text-[#BE123C]",
    },
    warning: {
      card: "border-[#FDBA74] bg-[linear-gradient(180deg,#FFF7ED,#FFFFFF)] before:bg-[#EA580C]",
      icon: "border-[#FDBA74] bg-white text-[#C2410C]",
      title: "text-[#64748B]",
      value: "text-[#C2410C]",
      detail: "text-[#C2410C]",
    },
    success: {
      card: "border-[#86EFAC] bg-[linear-gradient(180deg,#ECFDF3,#FFFFFF)] before:bg-[#059669]",
      icon: "border-[#86EFAC] bg-white text-[#047857]",
      title: "text-[#64748B]",
      value: "text-[#047857]",
      detail: "text-[#047857]",
    },
    info: {
      card: "border-[#93C5FD] bg-[linear-gradient(180deg,#EFF6FF,#FFFFFF)] before:bg-[#2563EB]",
      icon: "border-[#93C5FD] bg-white text-[#1D4ED8]",
      title: "text-[#64748B]",
      value: "text-[#1D4ED8]",
      detail: "text-[#1D4ED8]",
    },
    violet: {
      card: "border-[#C4B5FD] bg-[linear-gradient(180deg,#F5F3FF,#FFFFFF)] before:bg-[#7C3AED]",
      icon: "border-[#C4B5FD] bg-white text-[#6D28D9]",
      title: "text-[#64748B]",
      value: "text-[#6D28D9]",
      detail: "text-[#6D28D9]",
    },
    neutral: {
      card: "border-[#CBD5E1] bg-[linear-gradient(180deg,#FFFFFF,#F8FAFC)] before:bg-[#475569]",
      icon: "border-[#CBD5E1] bg-[#F8FAFC] text-[#334155]",
      title: "text-[#64748B]",
      value: "text-[#334155]",
      detail: "text-[#64748B]",
    },
  }[semanticTone] || {
    card: "border-[#CBD5E1] bg-[linear-gradient(180deg,#FFFFFF,#F8FAFC)] before:bg-[#475569]",
    icon: "border-[#CBD5E1] bg-[#F8FAFC] text-[#334155]",
    title: "text-[#64748B]",
    value: "text-[#334155]",
    detail: "text-[#64748B]",
  };

  const toneClasses = toneMap.card;
  const iconClasses = toneMap.icon;
  const titleClasses = toneMap.title;
  const valueClasses = toneMap.value;
  const detailClasses = toneMap.detail;
  const orderClass = getKpiOrder(title);

  return (
    <div className={`relative min-h-[10.25rem] overflow-hidden rounded-[24px] border p-6 shadow-[0_18px_45px_rgba(15,23,42,0.08)] ring-1 ring-white/80 before:absolute before:left-6 before:right-6 before:top-0 before:h-1.5 before:rounded-b-full ${toneClasses} ${orderClass}`}>
      <div className="mb-4 flex flex-col items-center text-center">
        <div className={`flex h-14 w-14 items-center justify-center rounded-2xl border shadow-[0_10px_26px_rgba(15,23,42,0.08)] ${iconClasses}`}>
          {icon}
        </div>
        <p className={`mt-3 text-[12px] font-black uppercase tracking-[0.2em] ${titleClasses}`}>{title}</p>
      </div>
      <h3 className={`mx-auto mt-1 max-w-[20rem] break-words text-center text-2xl font-black leading-tight tracking-tight sm:text-[1.75rem] ${valueClasses}`}>
        {displayValue}
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
